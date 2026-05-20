"""Central config. Reads from .env so secrets never live in code."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Project root — everything below resolves relative to this.
ROOT = Path(__file__).resolve().parent.parent

# Mock data files (act as our CRM and ticketing systems).
CRM_PATH = ROOT / "data" / "crm.json"
TICKETS_PATH = ROOT / "data" / "tickets.json"

# Where the orchestrator writes the structured trace.
LOG_PATH = ROOT / "logs" / "run.jsonl"

# Maximum agent loop iterations (safety net so a runaway agent can't burn tokens forever).
MAX_AGENT_TURNS = 10
