"""Run v0 demo — output to file, with error tracing."""
from __future__ import annotations

import time
import traceback
from pipeline.parser import parse
from pipeline.extractor import extract_jd, extract_resume
from pipeline.scorer import score_candidate
from config import SAMPLES_DIR

OUT = "E:/must-assesment/scorecard_result.txt"

def log(msg: str) -> None:
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("")

try:
    log("=" * 60)
    log("RECRUITING SCREENER — Phase 2 v0 Demo")
    log("=" * 60)

    JD_FILE = SAMPLES_DIR / "jd_senior_backend_engineer.txt"
    RESUME_FILE = SAMPLES_DIR / "resume_candidate_strong.md"

    log(f"\n[1/4] Parsing JD: {JD_FILE.name}")
    t0 = time.monotonic()
    jd_raw = parse(JD_FILE)
    log(f"      Extracted {len(jd_raw)} chars in {time.monotonic()-t0:.2f}s")

    time.sleep(3)

    log(f"[2/4] Parsing resume: {RESUME_FILE.name}")
    t0 = time.monotonic()
    resume_raw = parse(RESUME_FILE)
    log(f"      Extracted {len(resume_raw)} chars in {time.monotonic()-t0:.2f}s")

    time.sleep(3)

    log("[3/4] Extracting structured fields via Groq function calling...")
    t0 = time.monotonic()
    jd = extract_jd(jd_raw)
    log(f"      JD extraction OK: {jd.role_title}")

    resume = extract_resume(resume_raw)
    log(f"      Resume extraction OK: {resume.full_name}")
    log(f"      Extraction done in {time.monotonic()-t0:.2f}s")

    time.sleep(5)

    log("[4/4] Scoring candidate...")
    t0 = time.monotonic()
    scorecard = score_candidate(jd, resume)
    log(f"      Scoring done in {time.monotonic()-t0:.2f}s")

    log("")
    log("=" * 60)
    log("SCORECARD")
    log("=" * 60)
    log(f"  Candidate:  {scorecard.candidate_name}")
    log(f"  Role:       {scorecard.jd_role}")
    log(f"  Overall:    {scorecard.overall_score:.1f}/100")
    log(f"  Confidence: {scorecard.confidence}")
    log(f"  Recommendation: {scorecard.recommendation.value.upper()}")
    log("")
    log("  Rationale:")
    for line in scorecard.rationale.split("\n"):
        log(f"    {line}")
    log("")
    log("  Criterion Scores:")
    for cs in scorecard.criterion_scores:
        bar = chr(9608) * (cs.score // 10) + chr(9617) * (10 - cs.score // 10)
        log(f"    [{bar}] {cs.score:3d}/100  {cs.criterion}")
        ev = cs.evidence[:150] + "..." if len(cs.evidence) > 150 else cs.evidence
        log(f"           Evidence: \"{ev}\"")
    log("")
    log("=" * 60)
    log(f"Phase 2 v0 demo complete. Result: {scorecard.recommendation.value.upper()}")

except Exception as e:
    log("")
    log("=" * 60)
    log("ERROR")
    log("=" * 60)
    log(f"Exception: {type(e).__name__}: {e}")
    log("")
    log("Traceback:")
    for line in traceback.format_exc().split("\n"):
        log(f"  {line}")
    log("")
    log("=" * 60)
