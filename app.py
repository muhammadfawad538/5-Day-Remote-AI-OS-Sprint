"""Streamlit UI — entry point for the recruiter.

Phase 3: full working app. Recruiter can paste/upload a JD, upload multiple
resumes, run the pipeline, and review scorecards with evidence. No terminal
or technical knowledge required.
"""

from __future__ import annotations

import io
import os
import time
from pathlib import Path
from typing import Any

import streamlit as st

from config import (
    GROQ_MODEL,
    LOGS_DIR,
    REPO_ROOT,
    SAMPLES_DIR,
    GROQ_API_KEY,
)
from pipeline.logger import log_run, set_model_version
from pipeline.parser import ParseError, parse
from pipeline.extractor import extract_jd, extract_resume
from pipeline.scorer import score_candidate
from pipeline.schemas import Scorecard

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Recruiting Screener",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Recruiting Screener")
st.caption("Upload a job description and resumes to get evidence-based candidate scores.")

# ---------------------------------------------------------------------------
# Sidebar — settings & history
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Settings")
    st.metric("Model", GROQ_MODEL)

    st.header("Run History")
    from pipeline.logger import get_recent_runs
    recent = get_recent_runs(10)
    if recent:
        for run in recent:
            ts = run["timestamp"][:19].replace("T", " ")
            badge = {
                "advance": "🟢",
                "hold": "🟡",
                "reject": "🔴",
            }.get(run["recommendation"] or "", "⚪")
            st.write(f"{badge} **{run['candidate_name'] or '—'}**")
            st.caption(
                f"{ts} | {run['jd_role'] or '—'} | "
                f"{run['overall_score'] or '—'}/100"
            )
    else:
        st.info("No runs yet.")

# ---------------------------------------------------------------------------
# Helper — display a scorecard
# ---------------------------------------------------------------------------

def render_scorecard(scorecard: Scorecard) -> None:
    """Render a single scorecard with evidence per criterion."""
    score = scorecard.overall_score
    if score >= 80:
        color = "#22c55e"
        rec_label = "🟢 ADVANCE"
    elif score >= 50:
        color = "#eab308"
        rec_label = "🟡 HOLD"
    else:
        color = "#ef4444"
        rec_label = "🔴 REJECT"

    c1, c2, c3, c4 = st.columns([1, 2, 2, 2])
    c1.metric("Candidate", scorecard.candidate_name)
    c2.metric("Role", scorecard.jd_role)
    c3.metric("Score", f"{score:.1f}/100")
    c4.markdown(
        f"<div style='font-size:1.1rem;font-weight:600;color:{color};"
        f"margin-top:0.6rem;'>{rec_label}</div>",
        unsafe_allow_html=True,
    )

    st.markdown(f"**Confidence:** {scorecard.confidence or '—'}")
    st.markdown(f"**Rationale:** {scorecard.rationale}")

    with st.expander("Criterion Scores & Evidence"):
        for cs in scorecard.criterion_scores:
            bar_filled = cs.score // 10
            bar_empty = 10 - bar_filled
            bar = "█" * bar_filled + "░" * bar_empty
            st.markdown(f"**[{bar}] {cs.score}/100** — {cs.criterion}")
            if cs.evidence:
                st.markdown(f"> {cs.evidence}")
            if cs.notes:
                st.caption(f"*Note:* {cs.notes}")
            st.divider()


# ---------------------------------------------------------------------------
# Step 1: JD input
# ---------------------------------------------------------------------------

st.header("Step 1 — Job Description")

jd_col_a, jd_col_b = st.columns(2)
with jd_col_a:
    jd_text = st.text_area(
        "Paste JD text here",
        height=250,
        placeholder="Paste the job description text…",
    )
with jd_col_b:
    jd_file = st.file_uploader(
        "Or upload a JD file",
        type=["pdf", "docx", "doc", "txt", "md"],
        help="PDF, DOCX, TXT, or MD",
    )

# Resolve JD text
jd_raw: str | None = None
jd_source = "pasted"
if jd_text.strip():
    jd_raw = jd_text.strip()
elif jd_file is not None:
    # Save to temp and parse
    suffix = Path(jd_file.name).suffix.lower()
    tmp_path = REPO_ROOT / f"_tmp_jd{suffix}"
    with open(tmp_path, "wb") as f:
        f.write(jd_file.getbuffer())
    try:
        jd_raw = parse(tmp_path)
        jd_source = jd_file.name
    except ParseError as exc:
        st.error(f"**Cannot parse JD file:** {exc.reason}")
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass

if jd_raw:
    with st.expander("Preview parsed JD text"):
        st.text(jd_raw[:2000] + ("…" if len(jd_raw) > 2000 else ""))

# ---------------------------------------------------------------------------
# Step 2: Resume upload
# ---------------------------------------------------------------------------

st.header("Step 2 — Resumes")

resume_files = st.file_uploader(
    "Upload one or more resumes",
    type=["pdf", "docx", "doc", "txt", "md"],
    accept_multiple_files=True,
    help="PDF, DOCX, TXT, or MD files",
)

if resume_files:
    st.caption(f"**{len(resume_files)}** file(s) selected:")
    for f in resume_files:
        st.write(f"  • {f.name}")

# ---------------------------------------------------------------------------
# Step 3: Run screening
# ---------------------------------------------------------------------------

st.header("Step 3 — Score Candidates")

run_button = st.button(
    "▶ Run Screening",
    type="primary",
    disabled=(jd_raw is None or not resume_files),
    use_container_width=True,
)

if run_button and jd_raw and resume_files:
    set_model_version(GROQ_MODEL)

    progress = st.progress(0, text="Extracting job description…")
    # Extract JD once — reuse for every resume (saves N-1 API calls)
    try:
        jd = extract_jd(jd_raw)
    except Exception as exc:
        st.error(
            "**Could not extract a valid job description from the input.**\n\n"
            "Make sure you pasted a job description (not a resume) in Step 1. "
            "A JD should describe a role's responsibilities, required skills, and qualifications.\n\n"
            f"Technical detail: {exc}"
        )
        st.stop()

    results: list[dict[str, Any]] = []
    total = len(resume_files)

    for idx, rfile in enumerate(resume_files):
        progress.progress(
            (idx) / total,
            text=f"Processing {idx + 1}/{total}: {rfile.name}…",
        )
        suffix = Path(rfile.name).suffix.lower()
        tmp_path = REPO_ROOT / f"_tmp_resume_{idx}{suffix}"
        try:
            with open(tmp_path, "wb") as f:
                f.write(rfile.getbuffer())

            t0 = time.monotonic()
            resume_raw = parse(tmp_path)

            resume = extract_resume(resume_raw)
            scorecard = score_candidate(jd, resume)
            latency_total = time.monotonic() - t0

            # Log to SQLite
            log_run(
                jd_raw=jd_raw,
                resume_raw=resume_raw,
                scorecard=scorecard,
                latency=latency_total,
                error=None,
            )
            results.append({
                "file": rfile.name,
                "scorecard": scorecard,
                "error": None,
            })

        except ParseError as exc:
            log_run(
                jd_raw=jd_raw,
                resume_raw="",
                scorecard=None,
                latency=0.0,
                error=str(exc),
            )
            results.append({
                "file": rfile.name,
                "scorecard": None,
                "error": f"Parse error: {exc.reason}",
            })

        except Exception as exc:
            log_run(
                jd_raw=jd_raw,
                resume_raw="",
                scorecard=None,
                latency=0.0,
                error=str(exc),
            )
            results.append({
                "file": rfile.name,
                "scorecard": None,
                "error": f"Pipeline error: {exc}",
            })

        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass

    progress.progress(1.0, text="Done!")

    # -------------------------------------------------------------------
    # Step 4: Results
    # -------------------------------------------------------------------

    st.header("Results")

    scored = [r for r in results if r["scorecard"] is not None]
    errored = [r for r in results if r["error"] is not None]

    if scored:
        # Summary table
        table_rows = []
        for r in scored:
            sc = r["scorecard"]
            table_rows.append({
                "File": r["file"],
                "Candidate": sc.candidate_name,
                "Score": f"{sc.overall_score:.1f}/100",
                "Recommendation": sc.recommendation.value.upper(),
                "Confidence": sc.confidence or "—",
            })
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

        # Expandable scorecards
        for r in scored:
            with st.expander(
                f"📄 {r['file']} — {r['scorecard'].candidate_name}",
                expanded=False,
            ):
                render_scorecard(r["scorecard"])

    if errored:
        st.subheader("Errors")
        for r in errored:
            st.error(f"**{r['file']}**: {r['error']}")

    st.success(
        f"Screened **{total}** resume(s): "
        f"{len(scored)} scored, {len(errored)} failed."
    )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.divider()
st.caption(
    "Recruiting Screener — AI-assisted screening. "
    "System recommends; human confirms. "
    f"Model: {GROQ_MODEL}"
)
