"""
Orchestrator agent.

Pulls together:
  - Three MCP tool servers spawned as subprocesses over stdio.
  - Claude as the planner, using the standard tool-use protocol.
  - A human-in-the-loop gate that approves or rejects the drafted email.
  - Structured logging of every step to logs/run.jsonl.

High-level flow:
  1. Boot all 3 MCP servers, collect their tool definitions.
  2. Send the input event + tool definitions to Claude.
  3. While Claude wants to use tools:
        a. For each tool_use block, route to the right MCP server, call it.
        b. If the tool is draft_resolution_email, pause and ask the human y/n
           before marking the draft approved for sending.
        c. Send all tool_results back to Claude in the next turn.
  4. When Claude's stop_reason is not "tool_use", we're done. Return the answer.

Why all 3 MCP servers run as subprocesses (not in-process functions):
  This is the canonical MCP pattern. It matches how Claude Desktop, Claude Code,
  and other real clients call MCP servers. For a customer engineer portfolio,
  the important pattern is tool isolation, auditability, and approval before
  customer-visible action.
"""
from __future__ import annotations

import contextlib
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, MAX_AGENT_TURNS
from src.logging_utils import log_event

ROOT = Path(__file__).resolve().parent.parent

# Each MCP server is a Python module run as a subprocess. The orchestrator
# talks to it over the subprocess's stdin/stdout using the MCP JSON-RPC protocol.
MCP_SERVER_SPECS = [
    ("customer_lookup", ["python", "-m", "mcp_servers.customer_lookup"]),
    ("ticket_create",   ["python", "-m", "mcp_servers.ticket_create"]),
    ("draft_email",     ["python", "-m", "mcp_servers.draft_email"]),
]

SYSTEM_PROMPT = """You are an ops orchestrator for a logistics company's enterprise accounts team.

When a shipment exception event arrives, you handle it end-to-end:
  1. Look up the affected customer via lookup_customer.
  2. Create a support ticket via create_ticket. Set priority based on the customer's tier
     (enterprise = high, mid-market = normal, smb = low) unless the situation is severe,
     in which case escalate.
  3. Draft a resolution email via draft_resolution_email, using the ticket id you just
     created and the customer's primary contact and account manager.
  4. After the email is drafted, your job is done. Summarize what you did in 2-3 sentences.

Do not invent customer details. If lookup fails, report the failure and stop."""


@dataclass
class ToolRoute:
    """Maps a tool name (as Claude knows it) to the MCP session that owns it."""
    server_name: str
    session: ClientSession


async def _connect_all_servers(stack: contextlib.AsyncExitStack) -> tuple[dict[str, ToolRoute], list[dict]]:
    """Spawn all MCP server subprocesses, initialize sessions, return:
        - a routing table {tool_name: ToolRoute}
        - the combined list of tool definitions in Anthropic's tool-use schema
    """
    routes: dict[str, ToolRoute] = {}
    anthropic_tools: list[dict] = []

    for server_name, argv in MCP_SERVER_SPECS:
        log_event("mcp_server_start", server=server_name, argv=argv)

        params = StdioServerParameters(command=argv[0], args=argv[1:], cwd=str(ROOT))
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        tools_resp = await session.list_tools()
        for t in tools_resp.tools:
            routes[t.name] = ToolRoute(server_name=server_name, session=session)
            anthropic_tools.append(
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema,
                }
            )
            log_event("mcp_tool_registered", server=server_name, tool=t.name)

    return routes, anthropic_tools


def _hitl_review(draft: dict[str, Any]) -> tuple[bool, str | None]:
    """Print the draft email and block for y/n approval. Returns (approved, reason)."""
    print("\n" + "=" * 70)
    print("HUMAN-IN-THE-LOOP REVIEW — proposed email")
    print("=" * 70)
    print(f"To:      {draft.get('to')}")
    print(f"Subject: {draft.get('subject')}")
    print("-" * 70)
    print(draft.get("body", ""))
    print("=" * 70)
    while True:
        ans = input("Send this email? [y/n] (or n=<reason> to reject with feedback): ").strip()
        if ans.lower() in {"y", "yes"}:
            return True, None
        if ans.lower().startswith("n"):
            reason = ans[2:].strip() if "=" in ans else None
            return False, reason
        print("  Please answer y or n.")


async def _call_tool_with_hitl(
    routes: dict[str, ToolRoute],
    tool_name: str,
    tool_input: dict[str, Any],
) -> dict[str, Any]:
    """Call a tool via MCP, applying the HITL gate when the tool is draft_resolution_email."""
    route = routes.get(tool_name)
    if route is None:
        return {"error": f"Unknown tool: {tool_name}"}

    t0 = time.time()
    log_event("tool_call_start", server=route.server_name, tool=tool_name, input=tool_input)
    result = await route.session.call_tool(tool_name, tool_input)
    latency_ms = int((time.time() - t0) * 1000)

    # MCP tool results come back as a list of content blocks. FastMCP returns the
    # tool's return value as a single JSON-encoded text block; unwrap it.
    result_payload: dict[str, Any]
    if result.content and result.content[0].type == "text":
        import json
        try:
            result_payload = json.loads(result.content[0].text)
        except json.JSONDecodeError:
            result_payload = {"raw": result.content[0].text}
    else:
        result_payload = {"error": "Empty tool result"}

    log_event(
        "tool_call_done",
        server=route.server_name,
        tool=tool_name,
        latency_ms=latency_ms,
        result=result_payload,
    )

    # HITL gate fires on the customer-facing draft. A production version would
    # call a separate send_email tool only after this approval.
    if tool_name == "draft_resolution_email" and "error" not in result_payload:
        approved, reason = _hitl_review(result_payload)
        log_event("hitl_decision", approved=approved, reason=reason)
        if approved:
            result_payload["_status"] = "approved_by_human"
            result_payload["_action"] = "ready_for_send_email_tool"
        else:
            result_payload["_status"] = "rejected_by_human"
            result_payload["_action"] = "send_email_tool_not_called"
            result_payload["_rejection_reason"] = reason or "no reason given"

    return result_payload


async def run_agent(event: str) -> str:
    """Run the agent loop for one input event. Returns Claude's final summary."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY missing. Copy .env.example to .env and fill it in.")

    log_event("run_start", event=event, model=ANTHROPIC_MODEL)

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    async with contextlib.AsyncExitStack() as stack:
        routes, tools = await _connect_all_servers(stack)

        # The conversation history we hand to Claude. We append assistant + user turns
        # to it as the loop progresses; this is the standard tool-use pattern.
        messages: list[dict] = [{"role": "user", "content": event}]

        for turn in range(MAX_AGENT_TURNS):
            log_event("claude_turn_start", turn=turn)
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
            log_event(
                "claude_turn_done",
                turn=turn,
                stop_reason=response.stop_reason,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            # Add the assistant's full response (text + tool_use blocks) to history.
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                # Agent is done — extract the final text.
                final = "".join(b.text for b in response.content if b.type == "text").strip()
                log_event("run_done", final=final, turns=turn + 1)
                return final

            # Execute every tool_use block Claude requested, build the matching
            # tool_result blocks for the next user turn.
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                import json
                result = await _call_tool_with_hitl(routes, block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )

            messages.append({"role": "user", "content": tool_results})

        log_event("run_aborted", reason="max_turns_exceeded")
        return f"Agent exceeded {MAX_AGENT_TURNS} turns without finishing. Check logs/run.jsonl."
