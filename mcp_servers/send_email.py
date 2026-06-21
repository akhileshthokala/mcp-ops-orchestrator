"""
MCP server: send_email.

Exposes one tool, `send_email`, that simulates sending a customer-facing email
to an actual external system. This is the irreversible action that requires HITL
approval in the orchestrator.

Run standalone (for testing):
    uv run python -m mcp_servers.send_email
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
SENT_EMAILS_PATH = ROOT / "data" / "sent_emails.json"

mcp = FastMCP("send_email")


def _load_sent() -> dict:
    if not SENT_EMAILS_PATH.exists():
        return {"emails": []}
    with open(SENT_EMAILS_PATH) as f:
        return json.load(f)


def _save_sent(data: dict) -> None:
    SENT_EMAILS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SENT_EMAILS_PATH, "w") as f:
        json.dump(data, f, indent=2)


@mcp.tool()
def send_email(
    to: str,
    subject: str,
    body: str,
) -> dict:
    """Send a customer-facing email (irreversible action).

    This tool should only be called after human approval of the draft.
    It records the email as sent in the system and returns confirmation.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body text.

    Returns:
        Confirmation dict with timestamp and delivery status.
    """
    email_record = {
        "to": to,
        "subject": subject,
        "body": body,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "status": "delivered",
    }

    data = _load_sent()
    data["emails"].append(email_record)
    _save_sent(data)

    return {
        "status": "sent",
        "to": to,
        "subject": subject,
        "sent_at": email_record["sent_at"],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
