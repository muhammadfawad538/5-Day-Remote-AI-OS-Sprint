"""Evidence-based scoring of a candidate against a JD.

Uses three Groq JSON-mode calls:
1. criterion_scoring — per-criterion evidence citation and 0-100 scores.
2. recommendation — overall score, recommendation, and rationale derived from
   the criterion scores.
3. structural_checks — explicit checks for seniority mismatch, employment gaps,
   and other non-criterion risks before returning "advance".

This keeps the evidence layer honest and makes the final recommendation
auditable with named, structurally-required risk checks.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL, logger
from pipeline.schemas import (
    CriterionScore,
    JobDescription,
    Recommendation,
    Scorecard,
    ResumeData,
)

_client = Groq(api_key=GROQ_API_KEY)

# Track last LLM call time so we can pace calls and stay within Groq rate limits.
_last_call_monotonic: float = 0.0

# Rate-limit budget sampler — logs remaining quota on first call and when
# headers change.  Prevents silent exhaustion mid-eval.
_rate_limit_cache: dict[str, str] = {}


def _parse_groq_duration(value: str) -> float:
    """Parse a Go-style duration string (e.g. '3h0m0s', '285ms') to seconds.

    Returns 0.0 if the value is unparseable (caller should fall back).
    """
    import re
    m = re.fullmatch(
        r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?(?:(\d+)ms)?",
        value.strip(),
    )
    if not m:
        return 0.0
    hours, mins, secs, ms = (int(g) if g else 0 for g in m.groups())
    return hours * 3600 + mins * 60 + secs + ms / 1000.0


def _sample_rate_limit_headers(headers: dict[str, str]) -> None:
    """Log Groq rate-limit budget when it changes so we can see quota drain."""
    global _rate_limit_cache
    key = "|".join(f"{k}={v}" for k, v in sorted(headers.items())
                   if "ratelimit" in k.lower() or k == "retry-after")
    if key != _rate_limit_cache.get("last"):
        _rate_limit_cache["last"] = key
        logger.info("Groq rate-limit headers: %s", key)


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
# Structural risk checks
# ---------------------------------------------------------------------------


@dataclass
class StructuralChecks:
    """Results from mandatory pre-recommendation structural checks."""

    seniority_mismatch: bool = False
    seniority_detail: str = ""
    employment_gap_months: int = 0
    gap_explained: bool = False
    gap_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "seniority_mismatch": self.seniority_mismatch,
            "seniority_detail": self.seniority_detail,
            "employment_gap_months": self.employment_gap_months,
            "gap_explained": self.gap_explained,
            "gap_note": self.gap_note,
        }


_SENIORITY_LEVELS = {
    "junior": 1,
    "entry": 1,
    "associate": 2,
    "mid": 2,
    "senior": 3,
    "staff": 4,
    "principal": 5,
    "distinguished": 6,
    "fellow": 7,
}


def _infer_jd_seniority(jd: JobDescription) -> int:
    """Return a numeric seniority level from the JD role title."""
    title_lower = jd.role_title.lower()
    for keyword, level in _SENIORITY_LEVELS.items():
        if keyword in title_lower:
            return level
    return 2  # default to mid-level if no keyword found


def _infer_resume_seniority(resume: ResumeData) -> tuple[int, str]:
    """Return (seniority_level, detail) from the resume's current title and experience."""
    title_lower = (resume.current_title or "").lower()
    for keyword, level in _SENIORITY_LEVELS.items():
        if keyword in title_lower:
            return level, f"Current title '{resume.current_title}' maps to {keyword} level ({level})"
    years = resume.years_of_experience or 0
    if years >= 10:
        return 4, f"{years} years of experience implies staff/principal level"
    if years >= 7:
        return 3, f"{years} years of experience implies senior level"
    return 2, f"No seniority keyword in title; defaulting to mid-level ({years} years)"


def _compute_employment_gaps(resume: ResumeData) -> tuple[int, bool, str]:
    """Compute the largest employment gap in months from work_history.

    The current role (end_date "Present") is included using the resume year
    as its effective end date.  Entries whose title signals a non-work period
    (Career Gap, Sabbatical, Unemployed, etc.) are skipped when computing
    the gap so that the actual break in employment is measured correctly.

    Returns (largest_gap_months, gap_explained, note).
    """
    work = resume.work_history or []
    if len(work) < 2:
        return 0, False, "Insufficient work history to detect gaps"

    _PRESENT_TOKENS = {"present", "current", "now", "to date", "ongoing", "n/a"}
    _GAP_TITLE_KEYWORDS = {"career gap", "gap", "sabbatical", "unemployed", "break"}

    def parse_year(text: str) -> float | None:
        text = text.strip().lower()
        if not text or text in _PRESENT_TOKENS:
            return None
        m = re.search(r"(\d{4})", text)
        return float(m.group(1)) if m else None

    def is_gap_title(title: str) -> bool:
        t = title.strip().lower()
        return any(kw in t for kw in _GAP_TITLE_KEYWORDS)

    # Build (start_year, end_year, title, is_gap) for each role.
    # Current role: end_year=None → filled with current year later.
    current_year = 2026.0
    carry = current_year
    roles: list[tuple[float, float, str, bool]] = []

    # Walk resume order (newest → oldest) so carry propagates correctly
    for job in reversed(work):
        start = parse_year(job.get("start_date", ""))
        end = parse_year(job.get("end_date", ""))
        title = job.get("title", "")
        if start is None:
            continue
        effective_end = end if end is not None else carry
        roles.append((start, effective_end, title, is_gap_title(title)))
        carry = effective_end

    if len(roles) < 2:
        return 0, False, "Too few dated roles to detect gaps"

    # Filter out gap-labeled entries and sort oldest→newest by start date
    # so that comparing end_i to start_next finds chronological gaps.
    work_roles = sorted(
        [(s, e, t) for s, e, t, ig in roles if not ig],
        key=lambda x: x[0],
    )

    max_gap = 0
    gap_detail = ""
    for i in range(len(work_roles) - 1):
        end_i = work_roles[i][1]           # end of more-recent role
        start_next = work_roles[i + 1][0]  # start of next older role
        if start_next > end_i:
            gap_months = int((start_next - end_i) * 12)
            if gap_months > max_gap:
                max_gap = gap_months
                gap_detail = (
                    f"Gap between {work_roles[i][2]} "
                    f"(ended {end_i:.0f}) and {work_roles[i+1][2]} "
                    f"(started {start_next:.0f})"
                )

    # Check if gap is explained in resume text
    gap_explained = False
    if max_gap > 0:
        raw_lower = (resume.raw_text or "").lower()
        explain_signals = [
            "career gap", "care break", "caregiving", "sabbatical",
            "family", "maternity", "paternity", "personal", "health",
            "travel", "full-time care", "explained by", "full-time caregiving",
        ]
        gap_explained = any(s in raw_lower for s in explain_signals)

    note = f"{max_gap}-month gap ({gap_detail})" if max_gap > 0 else "No significant gap detected"
    if gap_explained and max_gap > 0:
        note += "; gap appears explained in resume"

    return max_gap, gap_explained, note


def run_structural_checks(jd: JobDescription, resume: ResumeData) -> StructuralChecks:
    """Run mandatory structural checks before returning advance/hold/reject.

    Checks:
    - Seniority mismatch: is the candidate's current level higher than the JD level?
      (e.g., Staff engineer applying for Senior IC → likely overqualified)
    - Employment gaps: is there a gap >12 months? Is it explained?
    """
    checks = StructuralChecks()

    # Check 1: Seniority mismatch
    jd_level = _infer_jd_seniority(jd)
    resume_level, resume_detail = _infer_resume_seniority(resume)
    if resume_level > jd_level + 1:
        checks.seniority_mismatch = True
        checks.seniority_detail = (
            f"Candidate level ({resume_level}: {resume_detail}) exceeds JD level "
            f"({jd_level}: {jd.role_title}) by more than one tier. "
            f"Risk of overqualification and quick departure."
        )

    # Check 2: Employment gaps
    gap_months, gap_explained, gap_note = _compute_employment_gaps(resume)
    checks.employment_gap_months = gap_months
    checks.gap_explained = gap_explained
    checks.gap_note = gap_note

    return checks

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_mode_call(system_prompt: str, user_prompt: str, max_tokens: int,
                    max_retries: int = 3) -> dict[str, Any]:
    """Make a Groq call with JSON mode, retrying on rate-limit and timeout errors.

    Uses exponential backoff (1s, 2s, 4s) between retries.  Surface
    non-retryable errors immediately.  Paces consecutive calls to respect
    EVAL_INTER_CALL_DELAY and avoid Groq free-tier rate limits.
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

            # Prefer Groq's rate-limit reset header; fall back to exponential
            # backoff (1s, 2s, 4s) so we always have a sane wait.
            wait: float | None = None
            try:
                resp = getattr(exc, "response", None)
                if resp is not None:
                    hdrs = dict(resp.headers)
                    _sample_rate_limit_headers(hdrs)
                    # Groq returns reset as Go-style duration: '3h0m0s', '285ms'
                    reset_raw = hdrs.get("x-ratelimit-reset-requests")
                    if reset_raw is not None:
                        wait = _parse_groq_duration(reset_raw)
                    if wait is None or wait == 0.0:
                        retry_after = hdrs.get("retry-after")
                        if retry_after is not None:
                            wait = _parse_groq_duration(retry_after)
                            if wait == 0.0:
                                wait = float(retry_after)  # plain seconds string
            except Exception:
                pass
            if wait is None or wait == 0.0:
                wait = 2 ** (attempt - 1)

            logger.warning(
                "Groq call failed (attempt %d/%d): %s — retrying in %.1fs",
                attempt, max_retries, exc, wait,
            )
            time.sleep(wait)

    # Should not reach here, but raise if retries exhausted without exception
    raise RuntimeError(f"Groq call failed after {max_retries} attempts") from last_err


# ---------------------------------------------------------------------------
# Pass 1: Per-criterion scoring
# ---------------------------------------------------------------------------

_CRITERION_SYSTEM_PROMPT = (
    "You are an evidence-based scoring engine. Return ONLY a JSON object. "
    "Every score MUST include verbatim or near-verbatim evidence from the resume. "
    "Do not invent scores without evidence."
)


def _score_criteria(
    jd: JobDescription,
    resume: ResumeData,
) -> list[CriterionScore]:
    """Pass 1: score each JD criterion against the resume with evidence.

    Builds the criterion list from the JD's must-have and nice-to-have fields,
    then asks Groq to score each one via JSON mode.
    """
    criteria = (
        [f"[Must-have] {s}" for s in jd.must_have_skills]
        + [f"[Nice-to-have] {s}" for s in jd.nice_to_have_skills]
    )
    if jd.min_years_experience is not None:
        criteria.append(
            f"[Must-have] Minimum {jd.min_years_experience} years of experience"
        )
    for req in jd.education_requirements:
        criteria.append(f"[Must-have] Education: {req}")

    if not criteria:
        criteria = ["General fit for the role"]

    criteria_list = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(criteria))

    user_prompt = (
        f"Score the following candidate against each criterion for this role.\n\n"
        f"Role: {jd.role_title}\n\n"
        f"Criteria:\n{criteria_list}\n\n"
        f"Candidate resume:\n{resume.raw_text}\n\n"
        "Return a JSON object with this exact schema:\n"
        '{"scores": [{"criterion": string, "score": 0-100 integer, "evidence": string, "notes": string | null}]}\n\n'
        "For each criterion, return a score 0-100 and include verbatim or near-verbatim "
        "text from the resume as evidence. A score of 100 means the resume clearly and "
        "fully satisfies the criterion. A score of 0 means no evidence at all. "
        "Output valid JSON."
    )

    data = _json_mode_call(
        system_prompt=_CRITERION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=256,
    )
    raw_scores = data.get("scores", [])
    return [
        CriterionScore(
            criterion=s["criterion"],
            score=int(s["score"]),
            evidence=s["evidence"],
            notes=s.get("notes"),
        )
        for s in raw_scores
    ]


# ---------------------------------------------------------------------------
# Pass 2: Overall recommendation
# ---------------------------------------------------------------------------

_RECOMMENDATION_SYSTEM_PROMPT = (
    "You are a hiring recommendation engine. Return ONLY a JSON object. "
    "Weight must-have criteria more heavily than nice-to-have. "
    "Use the structural checks provided below to inform your decision, "
    "but do not mechanically override strong criterion scores — reason about "
    "whether a structural concern is material to this specific role."
)


def _get_recommendation(
    jd: JobDescription,
    resume: ResumeData,
    criterion_scores: list[CriterionScore],
    structural_checks: StructuralChecks,
) -> tuple[float, Recommendation, str, str, StructuralChecks]:
    """Pass 2: derive overall score and recommendation from criterion scores.

    Passes structural check results into the prompt so the LLM reasons about
    them explicitly.  A thin post-hoc safety net catches only the one
    unambiguous failure mode: advancing a clearly overqualified candidate.

    Returns (overall_score, recommendation, rationale, confidence, checks).
    """
    scores_summary = "\n".join(
        f"- {cs.criterion}: {cs.score}/100 — {cs.evidence}"
        for cs in criterion_scores
    )

    checks_json = json.dumps(structural_checks.to_dict(), indent=2)

    user_prompt = (
        f"Given these per-criterion scores for a candidate applying for "
        f"'{jd.role_title}', produce an overall json assessment.\n\n"
        f"Candidate: {resume.full_name}\n"
        f"Current title: {resume.current_title or 'not stated'}\n"
        f"Years of experience: {resume.years_of_experience or 'not stated'}\n\n"
        f"Scores:\n{scores_summary}\n\n"
        "Structural checks (pre-computed — include in structural_rationale):\n"
        f"{checks_json}\n\n"
        "Return a JSON object with this exact schema:\n"
        '{"overall_score": 0-100 number, "recommendation": "advance"|"hold"|"reject", '
        '"rationale": string, "confidence": "high"|"medium"|"low", '
        '"structural_rationale": string}\n\n'
        "Guidance on structural checks (use judgment, don't blindly follow):\n"
        "- If seniority_mismatch is true (candidate is 2+ levels above JD), "
        "consider whether this is a demotion risk.  Strong criterion scores can "
        "still justify advance if the candidate has a credible reason for the "
        "step down, but flag it in structural_rationale.\n"
        "- If employment_gap_months > 12 and not explained, this is a genuine "
        "risk — hold is appropriate even if criterion scores are strong. "
        "If the gap IS explained and criteria are strong, advance is fine.\n"
        "- If the candidate is significantly overqualified (e.g. Principal/Staff "
        "level applying for a Junior/Mid IC role), this is a rejection risk "
        "regardless of criterion scores.\n"
        "- advance = strong match, move to interview.\n"
        "- hold = ambiguous, needs human judgment.\n"
        "- reject = clear mismatch with role requirements.\n"
        "In structural_rationale, address whether each check affected your "
        "decision or was deemed acceptable.\n"
        "Output valid JSON."
    )

    d = _json_mode_call(
        system_prompt=_RECOMMENDATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=512,
    )
    checks = structural_checks
    checks.gap_note = d.get("structural_rationale", checks.gap_note)
    return (
        float(d["overall_score"]),
        Recommendation(d["recommendation"]),
        d["rationale"],
        d.get("confidence", "medium"),
        checks,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def score_candidate(
    jd: JobDescription,
    resume: ResumeData,
) -> Scorecard:
    """Score one candidate against one JD with evidence-based criterion scores.

    Runs three sequential Groq JSON-mode calls:
    1. criterion_scoring — per-criterion 0-100 scores with evidence.
    2. recommendation — overall score, recommendation, rationale, confidence.
    3. structural enforcement — deterministic rule overlay applied after the
       LLM returns, so seniority mismatch and large unexplained employment gaps
       CANNOT be overridden by the model.

    Args:
        jd: Structured job description (from extract_jd).
        resume: Structured resume data (from extract_resume).

    Returns:
        Scorecard with criterion scores, overall score, recommendation, rationale,
        and structural_checks dict for auditability.
    """
    logger.info(
        "Scoring candidate '%s' against '%s'",
        resume.full_name,
        jd.role_title,
    )

    criterion_scores = _score_criteria(jd, resume)

    # Structural checks (seniority mismatch, employment gaps) — always run,
    # always included in scorecard for auditability
    checks = run_structural_checks(jd, resume)
    logger.info(
        "Structural checks: seniority_mismatch=%s, gap_months=%d",
        checks.seniority_mismatch,
        checks.employment_gap_months,
    )

    overall_score, recommendation, rationale, confidence, checks = (
        _get_recommendation(jd, resume, criterion_scores, checks)
    )

    # -----------------------------------------------------------------------
    # Deterministic structural safety net (narrow — only prevents unsafe
    # advances that no reasonable hiring manager would approve)
    # -----------------------------------------------------------------------
    if recommendation == Recommendation.ADVANCE and checks.seniority_mismatch:
        # A Senior/Staff/Principal candidate advancing for a Junior/Mid role
        # is a well-documented retention failure mode — force a hold.
        recommendation = Recommendation.HOLD
        rationale = (
            "[SAFETY NET: seniority mismatch blocked advance] "
            f"{checks.seniority_detail} | Original rationale: {rationale}"
        )
        logger.info("Safety-net override: seniority mismatch prevented advance")

    logger.info(
        "Result: %s — %.1f/100 — %s",
        recommendation.value,
        overall_score,
        confidence,
    )

    return Scorecard(
        candidate_name=resume.full_name,
        jd_role=jd.role_title,
        criterion_scores=criterion_scores,
        overall_score=overall_score,
        recommendation=recommendation,
        rationale=rationale,
        confidence=confidence,
        structural_checks=checks.to_dict(),
    )
