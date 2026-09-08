"""Configuration loaded from environment variables.

All secrets and tunables flow through here. Never hardcode values in pipeline code.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Required
# ---------------------------------------------------------------------------

GROQ_API_KEY: str = os.environ["GROQ_API_KEY"]
"""Must be set in .env. No default — fail loudly if missing."""

# ---------------------------------------------------------------------------
# Tunables (all have safe defaults)
# ---------------------------------------------------------------------------

GROQ_MODEL: str = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
EVAL_INTER_CASE_DELAY: float = float(os.environ.get("EVAL_INTER_CASE_DELAY", "5.0"))
"""Seconds to pause between eval cases (default 5s) to stay within Groq free-tier RPM."""
EVAL_INTER_CALL_DELAY: float = float(os.environ.get("EVAL_INTER_CALL_DELAY", "1.0"))
"""Seconds to pause between consecutive LLM calls within a single case."""

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parent
DATA_DIR: Path = REPO_ROOT / "data"
SAMPLES_DIR: Path = DATA_DIR / "samples"
LOGS_DIR: Path = REPO_ROOT / "logs"

# Ensure directories exist
for _dir in (DATA_DIR, SAMPLES_DIR, LOGS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("recruiting_screener")
