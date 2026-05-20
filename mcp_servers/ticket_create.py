"""
MCP server: ticket_create.

Exposes one tool, `create_ticket`, that appends a new ticket record to
data/tickets.json and returns the ticket id. Simulates writing to a ticketing
system like Zendesk or ServiceNow.

Run standalone (for testing):
    uv run python -m mcp_servers.ticket_create
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
TICKETS_PATH = ROOT / "data" / "tickets.json"

mcp = FastMCP("ticket_create")


def _load() -> dict:
    with open(TICKETS_PATH) as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(TICKETS_PATH, "w") as f:
        json.dump(data, f, indent=2)


@mcp.tool()
def create_ticket(
    customer_id: str,
    subject: str,
    body: str,
    priority: str = "normal",
) -> dict:
    """Create a support ticket for a customer.

    Args:
        customer_id: The CRM customer id (e.g. "CUST-001").
        subject: Short summary of the issue.
        body: Detailed description of the issue and any context the agent collected.
        priority: One of "low", "normal", "high", "urgent". Defaults to "normal".

    Returns:
        The newly created ticket record including the assigned ticket id.
    """
    if priority not in {"low", "normal", "high", "urgent"}:
        return {"error": f"Invalid priority '{priority}'. Use low|normal|high|urgent."}

    ticket = {
        "ticket_id": f"TKT-{uuid.uuid4().hex[:8].upper()}",
        "customer_id": customer_id,
        "subject": subject,
        "body": body,
        "priority": priority,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    data = _load()
    data["tickets"].append(ticket)
    _save(data)

    return ticket


if __name__ == "__main__":
    mcp.run(transport="stdio")
