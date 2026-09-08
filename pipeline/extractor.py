"""Extract structured data from plain text using the Groq SDK.

Uses Groq's OpenAI-compatible chat completions endpoint with JSON-mode
(response_format={"type": "json_object"}) to enforce structured output.
This is more reliable on free-tier Groq than function calling, which has
strict token-per-minute limits that tool schemas exceed.

Architecture:
- extract_jd()   — one JSON-mode call: JD text -> JobDescription
- extract_resume() — one JSON-mode call: resume text -> ResumeData
"""

from __future__ import annotations

import json
import time
from typing import Any

from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL, logger
from pipeline.schemas import JobDescription, ResumeData

# ---------------------------------------------------------------------------
# Shared Groq client
# ---------------------------------------------------------------------------

_client = Groq(api_key=GROQ_API_KEY)

# Track last LLM call time so we can pace calls and stay within Groq rate limits.
_last_call_monotonic: float = 0.0


def _pace_calls() -> None:
    """Sleep if needed to respect EVAL_INTER_CALL_DELAY between consecutive LLM calls."""
    global _last_call_monotonic
    from config import EVAL_INTER_CALL_DELAY
    now = time.monotonic()
    elapsed = now - _last_call_monotonic
    if elapsed < EVAL_INTER_CALL_DELAY:
        time.sleep(EVAL_INTER_CALL_DELAY - elapsed)
    _last_call_monotonic = time.monotonic()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_mode_call(system_prompt: str, user_prompt: str, max_tokens: int,
                    max_retries: int = 3) -> dict[str, Any]:
    """Make a Groq call with JSON mode, retrying on rate-limit and timeout errors.

    Uses exponential backoff (1s, 2s, 4s) between retries.  Paces consecutive
    calls to respect EVAL_INTER_CALL_DELAY and avoid Groq free-tier rate limits.
    """
    _pace_calls()
    t0 = time.monotonic()
    last_err: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = _client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=max_tokens,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            elapsed = time.monotonic() - t0
            logger.info("Groq call completed in %.2fs (attempt %d)", elapsed, attempt)

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Groq returned empty response")
            return json.loads(content)

        except Exception as exc:
            last_err = exc
            err_type = type(exc).__name__
            is_retryable = (
                err_type in ("RateLimitError", "APITimeoutError", "InternalServerError")
                or "429" in str(exc)
                or "timeout" in str(exc).lower()
            )
            if not is_retryable or attempt == max_retries:
                raise

            wait = 2 ** (attempt - 1)
            logger.warning(
                "Groq call failed (attempt %d/%d): %s — retrying in %ds",
                attempt, max_retries, exc, wait,
            )
            time.sleep(wait)

    raise RuntimeError(f"Groq call failed after {max_retries} attempts") from last_err


# ---------------------------------------------------------------------------
# JD Extraction
# ---------------------------------------------------------------------------

_JD_SYSTEM_PROMPT = (
    "You are a structured data extractor. Given a job description, return a JSON "
    "object matching this exact schema. Use null for missing fields. Arrays must be "
    "JSON arrays of strings. Do not include any text outside the JSON object."
)
_JD_USER_TEMPLATE = (
    "Extract structured json fields from this job description. "
    "Be thorough — list every must-have skill, every nice-to-have, and every "
    "education requirement. Return valid JSON only.\n\n"
    "Schema:\n"
    "  role_title: string (required)\n"
    "  company: string | null\n"
    "  department: string | null\n"
    "  employment_type: string | null\n"
    "  location: string | null\n"
    "  must_have_skills: string[]\n"
    "  nice_to_have_skills: string[]\n"
    "  min_years_experience: number | null\n"
    "  education_requirements: string[]\n"
    "  key_responsibilities: string[]\n\n"
    "Job description:\n{raw_text}"
)


def extract_jd(raw_text: str) -> JobDescription:
    """Parse raw JD text into a structured JobDescription via Groq JSON mode.

    Args:
        raw_text: Plain text of the job description.

    Returns:
        JobDescription populated from the LLM's JSON response.

    Raises:
        ValueError: if the response is not valid JSON matching the schema.
    """
    logger.info("Extracting JD structure from %d characters", len(raw_text))

    data = _json_mode_call(
        system_prompt=_JD_SYSTEM_PROMPT,
        user_prompt=_JD_USER_TEMPLATE.format(raw_text=raw_text),
        max_tokens=512,
    )
    data["raw_text"] = raw_text
    return JobDescription(**data)


# ---------------------------------------------------------------------------
# Resume Extraction
# ---------------------------------------------------------------------------

_RESUME_SYSTEM_PROMPT = (
    "You are a structured data extractor. Given a resume, return a JSON "
    "object matching this exact schema. Use null for missing fields. Arrays must be "
    "JSON arrays. Do not include any text outside the JSON object."
)
_RESUME_USER_TEMPLATE = (
    "Extract structured json fields from this resume. "
    "Be thorough — list every job, every skill, every education entry. "
    "Leave fields null if genuinely not present; do not invent. Return valid JSON only.\n\n"
    "Schema:\n"
    "  full_name: string (required)\n"
    "  email: string | null\n"
    "  phone: string | null\n"
    "  location: string | null\n"
    "  linkedin_url: string | null\n"
    "  years_of_experience: number | null\n"
    "  current_title: string | null\n"
    "  current_company: string | null\n"
    "  work_history: array of objects with keys: title, company, start_date, end_date, description\n"
    "  education: array of objects with keys: degree, institution, year, field_of_study\n"
    "  skills: string[]\n"
    "  certifications: string[]\n"
    "  notable_achievements: string[]\n\n"
    "Resume:\n{raw_text}"
)


def extract_resume(raw_text: str) -> ResumeData:
    """Parse raw resume text into structured ResumeData via Groq JSON mode.

    Args:
        raw_text: Plain text of the resume.

    Returns:
        ResumeData populated from the LLM's JSON response.

    Raises:
        ValueError: if the response is not valid JSON matching the schema.
    """
    logger.info("Extracting resume structure from %d characters", len(raw_text))

    data = _json_mode_call(
        system_prompt=_RESUME_SYSTEM_PROMPT,
        user_prompt=_RESUME_USER_TEMPLATE.format(raw_text=raw_text),
        max_tokens=512,
    )
    data["raw_text"] = raw_text
    return ResumeData(**data)
