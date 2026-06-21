#!/bin/bash

# Demo script showing the orchestrator in action.
# Requires: uv, python3.11+, ANTHROPIC_API_KEY in .env
#
# Usage:
#   bash scripts/demo.sh          # Uses sample event
#   bash scripts/demo.sh "Custom event text here"

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

EVENT="${1:-Shipment SH-1042 destined for Acme Corp has been delayed by 48 hours due to port congestion in Long Beach. Original ETA was tomorrow; revised ETA is Thursday at 4pm PT. This is an enterprise account with a 4-hour SLA on incident response.}"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  MCP Ops Orchestrator — Live Demo                             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Event:"
echo "  $EVENT"
echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

uv run python -m src.run --event "$EVENT"

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""
echo "Demo complete. Logs written to logs/run.jsonl"
echo ""
echo "Inspect the trace:"
echo "  jq . logs/run.jsonl | less"
echo "  jq 'select(.event == \"hitl_decision\")' logs/run.jsonl"
echo "  jq 'select(.event == \"tool_call_done\") | {tool, latency_ms}' logs/run.jsonl"
echo ""
