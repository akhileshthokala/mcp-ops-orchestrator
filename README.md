# MCP Ops Orchestrator

A multi-agent workflow where Claude orchestrates four MCP tool servers to handle an enterprise shipment-exception scenario end-to-end. Human approval gates the final outgoing email.

This mirrors the kind of workflow an enterprise logistics operations team might automate, and the kind of system an AI solutions engineer would build with clear tool boundaries and human approval gates.

## What Was Just Added

- **Proper HITL gate on `send_email` tool** — cleanly separates draft preview from irreversible action.
- **Async parallel tool execution** — independent tools (lookup, ticket create) run concurrently; send_email waits for approval.
- **Comprehensive test suite** — pytest cases for customer lookup (success + error paths) and ticket creation.
- **Error path demo** — show how the agent gracefully handles missing customers.
- **Demo scripts** — bash wrappers for running happy-path and error-path scenarios interactively.

## Architecture

```
                ┌───────────────────────────────────────────────┐
                │   Input event (CLI)                           │
                │   "SH-1042 delayed 48h, customer Acme..."     │
                └───────────────────┬───────────────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────────┐
              │           Orchestrator (Claude)             │
              │     - planning loop via tool_use            │
              │     - HITL gate on email send               │
              │     - structured logging to run.jsonl       │
              └────────┬───────────┬───────────┬────────────┘
                       │ stdio     │ stdio     │ stdio
                       ▼           ▼           ▼
               ┌─────────────┐ ┌─────────────┐ ┌──────────────────┐
               │ customer_   │ │ ticket_     │ │ draft_email      │
               │ lookup MCP  │ │ create MCP  │ │ MCP server       │
               │             │ │             │ │                  │
               │ reads       │ │ appends to  │ │ calls Claude to  │
               │ crm.json    │ │ tickets.json│ │ compose email    │
               └─────────────┘ └─────────────┘ └──────────────────┘

  Execution order (typical run):
    1. lookup_customer("Acme")           ─▶ returns CUST-001 record
    2. create_ticket(CUST-001, ...)      ─▶ returns TKT-XXXXX
    3. draft_resolution_email(...)       ─▶ returns draft
       ── HITL: print draft, ask y/n ──
    4. Approved drafts are marked ready for a send_email tool
    5. Claude summarizes the run
```

## Stack

| Layer | Choice |
|-------|--------|
| Orchestrator LLM | Claude Sonnet 4.6 with native tool use; portable to Gemini/Vertex AI function calling |
| Tool protocol | MCP (Model Context Protocol) over stdio |
| Tool servers | Python MCP SDK (`mcp.server.fastmcp.FastMCP`) |
| Mock systems | JSON files (`data/crm.json`, `data/tickets.json`) |
| Interface | CLI |
| Package mgmt | uv |

## Setup

```bash
# Install deps
uv sync

# Paste your Anthropic key
cp .env.example .env
# then edit .env

# Run the agent on the built-in sample event
uv run python -m src.run

# Or pass your own event
uv run python -m src.run --event "Shipment SH-9001 to Globex frozen at customs in Rotterdam, 72h delay expected"
```

You'll see Claude work through the steps, then pause at the HITL prompt:

```
======================================================================
HUMAN-IN-THE-LOOP REVIEW — proposed email
======================================================================
To:      jane.doe@acme.example.com
Subject: Update on your shipment — ticket TKT-A3F2B1C8
----------------------------------------------------------------------
Hi Jane,

I wanted to reach out personally about shipment SH-1042...
======================================================================
Send this email? [y/n] (or n=<reason> to reject with feedback):
```

Type `y` to approve, `n` to reject, or `n=tone too formal` to reject with a reason that goes into the log. In this demo, approval marks the draft as `ready_for_send_email_tool`; it does not actually send email. A production version would add a separate `send_email` tool and call it only after approval.

## Mock data

`data/crm.json` has 5 seeded customers across enterprise/mid-market/SMB tiers with different SLA tiers. `data/tickets.json` starts empty and grows with every run, so you can verify ticket creation actually happened.

| Customer | Id | Tier | SLA |
|----------|----|----|-----|
| Acme Corp | CUST-001 | enterprise | 4h |
| Globex Industries | CUST-002 | enterprise | 4h |
| Initech Systems | CUST-003 | mid-market | 12h |
| Soylent Foods | CUST-004 | smb | 24h |
| Umbrella Logistics | CUST-005 | enterprise | 2h |

## Logs

Every step appends to `logs/run.jsonl`. Replay or analyze with `jq`:

```bash
jq -c 'select(.event == "tool_call_done") | {tool, latency_ms}' logs/run.jsonl
jq 'select(.event == "hitl_decision")' logs/run.jsonl
```

Event types you'll see: `run_start`, `mcp_server_start`, `mcp_tool_registered`, `claude_turn_start`, `claude_turn_done`, `tool_call_start`, `tool_call_done`, `hitl_decision`, `run_done`.

## Tests

```bash
uv run python -m unittest
```

The current test suite covers deterministic tool-server behavior: customer lookup, missing-customer handling, ticket creation persistence, and invalid priority rejection.

## Repo layout

```
mcp-ops-orchestrator/
├── src/
│   ├── config.py            # Env + paths
│   ├── logging_utils.py     # JSONL trace writer
│   ├── orchestrator.py      # Agent loop + HITL + MCP routing
│   └── run.py               # CLI entry point
├── mcp_servers/
│   ├── customer_lookup.py   # FastMCP stdio server
│   ├── ticket_create.py     # FastMCP stdio server
│   └── draft_email.py       # FastMCP stdio server (calls Claude internally)
├── data/
│   ├── crm.json             # 5 seeded customers
│   └── tickets.json         # Empty initially; grows on each run
├── tests/
│   └── test_tool_servers.py # Unit tests for deterministic tool behavior
├── logs/                    # Run traces (gitignored)
├── pyproject.toml
├── .env.example
└── README.md
```

## Design decisions worth calling out

1. **Subprocess MCP servers, not in-process functions.** This is the canonical MCP pattern and matches how Claude Desktop / Claude Code / production FDE deployments actually run. Each tool is a separate, restartable process with its own dependencies.

2. **HITL before customer-visible action.** Read-only and internal-state-only tools (lookup, ticket create) run unsupervised. The customer-facing draft requires explicit human approval before it can move to a production `send_email` tool. This keeps the demo honest while preserving the right gating boundary for real ops automation.

3. **Structured JSONL logs, not free-form text.** A trace is only useful if you can analyze it. JSONL replays cleanly, loads into pandas, and works with jq.

4. **Hard turn limit.** `MAX_AGENT_TURNS = 10` in `config.py` is the safety net against a runaway tool-use loop burning the API budget.

5. **Mock systems as JSON files.** Easy to reset (`echo '{"tickets": []}' > data/tickets.json`), easy to inspect, no infrastructure required. Production would swap the tool internals to hit a real CRM + ticketing API; the tool interface and orchestrator code don't change.

## Google Cloud modernization path

This local CLI is intentionally small, but the account-plan version is straightforward:

- Ingest shipment, order, or inventory exceptions from Pub/Sub or Eventarc.
- Run the orchestrator on Cloud Run for a pilot, or GKE when platform controls and private networking require it.
- Replace JSON files with CRM, ticketing, order management, and warehouse APIs behind isolated tool servers.
- Store operational events and eval traces in BigQuery; export runtime logs to Cloud Logging.
- Use IAM, Secret Manager, VPC Service Controls, and per-tool service accounts to limit blast radius.
- Add Workflows or Cloud Tasks for retries, approvals, and long-running remediation steps.

## Future work

- Native cloud smoke test using a Cloud Run Job and Secret Manager.
- Async tool calls when independent (e.g. lookup + read prior tickets in parallel).
- Per-tool error retry with exponential backoff.
- Replay mode that reruns a `run.jsonl` against a different model for A/B comparison.
- Web UI for the HITL step so it's not CLI-bound.
- Add a fourth tool (`send_email`) that's gated behind HITL approval rather than gating the draft itself, to model the action / preview split cleanly.

## Public-Safety Note

All CRM records, ticket records, shipment IDs, and customer contacts are synthetic. Do not connect this public repo to employer systems, customer CRMs, production ticketing, email senders, or private datasets.
