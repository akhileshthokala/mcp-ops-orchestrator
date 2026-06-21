#!/bin/bash

# Demo script showing error handling when customer lookup fails.
# This demonstrates the fallback behavior when a customer is not found.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  MCP Ops Orchestrator — Error Path Demo                       ║"
echo "║  (Customer Not Found)                                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

EVENT="Shipment SH-5000 for an unknown customer 'SuperTech Industries' is delayed 36 hours due to customs hold in Singapore."

echo "Event (intentionally referencing unknown customer):"
echo "  $EVENT"
echo ""
echo "Expected behavior:"
echo "  - Agent calls lookup_customer('SuperTech Industries')"
echo "  - Lookup fails with 'No customer found' error"
echo "  - Agent reports failure and stops (as per system prompt)"
echo "  - No ticket created, no email drafted"
echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

uv run python -m src.run --event "$EVENT"

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""
echo "Check the logs to verify error handling:"
echo "  jq 'select(.event == \"tool_call_done\" and .tool == \"lookup_customer\")' logs/run.jsonl"
echo ""
