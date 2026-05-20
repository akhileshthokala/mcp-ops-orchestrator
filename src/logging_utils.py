"""
Structured logging.

Every notable event in the agent loop appends one JSON line to logs/run.jsonl.
This gives you a full replayable trace of:
  - the input event
  - every Claude turn
  - every tool call (name, args, result, latency)
  - the HITL decision
  - the final outcome

JSONL is chosen over plain log lines because it's trivially grep-able and
loadable into pandas/jq for later analysis.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import LOG_PATH


def _open_log() -> Path:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    return LOG_PATH


def log_event(event_type: str, **fields: Any) -> None:
    """Append one JSON line describing an event in the agent loop."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **fields,
    }
    path = _open_log()
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")
