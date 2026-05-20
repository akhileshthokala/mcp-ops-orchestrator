"""
CLI entry point.

Examples:
    uv run python -m src.run --event "Shipment SH-1042 to Acme Corp delayed 48h due to port congestion"
    uv run python -m src.run   # uses a built-in sample event

Use Ctrl-C to abort at any point (including the HITL prompt).
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from src.orchestrator import run_agent

SAMPLE_EVENT = (
    "Shipment SH-1042 destined for Acme Corp has been delayed by 48 hours due to "
    "port congestion in Long Beach. Original ETA was tomorrow; revised ETA is "
    "Thursday at 4pm PT. This is an enterprise account with a 4-hour SLA on incident response."
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the MCP ops orchestrator on a shipment exception event.")
    p.add_argument(
        "--event",
        type=str,
        default=SAMPLE_EVENT,
        help="The exception event to process (defaults to a built-in sample)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    print(f"\n>>> Event: {args.event}\n")
    final = asyncio.run(run_agent(args.event))

    print("\n" + "=" * 70)
    print("AGENT SUMMARY")
    print("=" * 70)
    print(final)
    print()
    print("Full trace written to logs/run.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
