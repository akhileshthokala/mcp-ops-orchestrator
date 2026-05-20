"""
MCP server: draft_email.

Exposes one tool, `draft_resolution_email`, that uses Claude to compose a
customer-facing email about a shipment exception. The orchestrator gates
"sending" behind a human-in-the-loop approval step.

Run standalone (for testing):
    uv run python -m mcp_servers.draft_email
"""
from __future__ import annotations

import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Each MCP server loads its own env, since it runs in its own subprocess and
# doesn't inherit the orchestrator's loaded variables automatically.
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

mcp = FastMCP("draft_email")


SYSTEM_PROMPT = """You are a senior customer success manager at a logistics company.

You write concise, empathetic, action-oriented emails to enterprise customers when shipments are delayed or disrupted. Your emails:
  - Acknowledge the impact specifically (don't be generic).
  - State what happened in one or two sentences.
  - Lay out the concrete next steps with timing.
  - Reference the support ticket id.
  - Close with a direct line to a real human.
  - Are no more than 150 words. No subject line throat-clearing."""


@mcp.tool()
def draft_resolution_email(
    customer_name: str,
    customer_contact: str,
    customer_email: str,
    situation: str,
    ticket_id: str,
    account_manager: str,
) -> dict:
    """Draft a customer-facing resolution email for a shipment exception.

    Args:
        customer_name: The customer company name.
        customer_contact: The primary contact's name at the customer.
        customer_email: The recipient email address.
        situation: One-paragraph description of what happened and current status.
        ticket_id: The support ticket id to reference in the email.
        account_manager: The internal account manager's name to use as signoff.

    Returns:
        A dict with `to`, `subject`, and `body` ready for human review before sending.
    """
    if not ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY not set in the draft_email subprocess environment."}

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    user_prompt = (
        f"Customer: {customer_name}\n"
        f"Primary contact: {customer_contact}\n"
        f"Situation: {situation}\n"
        f"Support ticket: {ticket_id}\n"
        f"Sign off as: {account_manager}\n\n"
        "Write the email body only. No 'Subject:' line, no preamble. Just the email."
    )

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    body = "".join(b.text for b in response.content if b.type == "text").strip()

    return {
        "to": customer_email,
        "subject": f"Update on your shipment — ticket {ticket_id}",
        "body": body,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
