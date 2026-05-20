"""
MCP server: customer_lookup.

Exposes one tool, `lookup_customer`, that reads from data/crm.json and returns
a customer's account record. Supports lookup by name (case-insensitive partial
match) or by customer id.

Run standalone (for testing):
    uv run python -m mcp_servers.customer_lookup

The orchestrator spawns this as a subprocess and talks to it over stdio.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Resolve project root regardless of where this is launched from.
ROOT = Path(__file__).resolve().parent.parent
CRM_PATH = ROOT / "data" / "crm.json"

mcp = FastMCP("customer_lookup")


def _load_customers() -> list[dict]:
    with open(CRM_PATH) as f:
        return json.load(f)["customers"]


@mcp.tool()
def lookup_customer(query: str) -> dict:
    """Look up a customer by name (partial, case-insensitive) or by customer id.

    Args:
        query: The customer name or id to search for. Examples: "Acme", "CUST-001".

    Returns:
        The full customer record, or an error message if no match is found.
    """
    customers = _load_customers()
    q = query.strip().lower()

    # Try exact id match first.
    for c in customers:
        if c["id"].lower() == q:
            return c

    # Fall back to substring name match.
    matches = [c for c in customers if q in c["name"].lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return {
            "error": f"Multiple customers match '{query}': {[m['name'] for m in matches]}. Be more specific."
        }
    return {"error": f"No customer found matching '{query}'."}


if __name__ == "__main__":
    # stdio transport: server reads JSON-RPC from stdin, writes to stdout.
    mcp.run(transport="stdio")
