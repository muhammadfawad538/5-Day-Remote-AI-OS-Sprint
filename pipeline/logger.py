"""SQLite logging for pipeline runs.

Every pipeline execution (one JD + one or more resumes) is logged to
`logs/runs.db` with input hash, output summary, timestamp, model version,
and latency. This supports the Day 4 eval harness and Day 5 case study metrics.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import LOGS_DIR

DB_PATH: Path = LOGS_DIR / "runs.db"

_MODEL_VERSION: str | None = None


def set_model_version(version: str) -> None:
    global _MODEL_VERSION
    _MODEL_VERSION = version


def get_model_version() -> str:
    return _MODEL_VERSION or "unknown"


def _init_db() -> None:
    """Create the runs table if it doesn't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT NOT NULL,
                model_version   TEXT NOT NULL,
                jd_hash         TEXT NOT NULL,
                resume_hash     TEXT NOT NULL,
                candidate_name  TEXT,
                jd_role         TEXT,
                recommendation  TEXT,
                overall_score   REAL,
                confidence      TEXT,
                criterion_count INTEGER,
                latency_seconds REAL,
                error           TEXT,
                output_json     TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON runs(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_recommendation ON runs(recommendation)
        """)
        conn.commit()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def log_run(
    jd_raw: str,
    resume_raw: str,
    scorecard: Any | None,
    latency: float,
    error: str | None = None,
) -> int:
    """Log a single pipeline run to SQLite.

    Args:
        jd_raw: Raw JD text (hashed for dedup).
        resume_raw: Raw resume text (hashed for dedup).
        scorecard: Scorecard instance or None on error.
        latency: Total pipeline latency in seconds.
        error: Error message if the run failed, else None.

    Returns:
        The auto-incremented run_id.
    """
    _init_db()

    jd_hash = _hash_text(jd_raw)
    resume_hash = _hash_text(resume_raw)
    timestamp = datetime.now(timezone.utc).isoformat()

    candidate_name = None
    jd_role = None
    recommendation = None
    overall_score = None
    confidence = None
    criterion_count = 0
    output_json = None

    if scorecard is not None:
        candidate_name = scorecard.candidate_name
        jd_role = scorecard.jd_role
        recommendation = scorecard.recommendation.value
        overall_score = scorecard.overall_score
        confidence = scorecard.confidence
        criterion_count = len(scorecard.criterion_scores)
        output_json = json.dumps(scorecard.model_dump(), default=str)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO runs
                (timestamp, model_version, jd_hash, resume_hash,
                 candidate_name, jd_role, recommendation,
                 overall_score, confidence, criterion_count,
                 latency_seconds, error, output_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                get_model_version(),
                jd_hash,
                resume_hash,
                candidate_name,
                jd_role,
                recommendation,
                overall_score,
                confidence,
                criterion_count,
                latency,
                error,
                output_json,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_recent_runs(limit: int = 50) -> list[dict[str, Any]]:
    """Return recent runs as dicts (no PII beyond what's in scorecard)."""
    _init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY run_id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
