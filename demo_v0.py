#!/usr/bin/env python3
"""Phase 2 v0 demo — run one resume through the full pipeline.

Usage:
    python demo_v0.py

Prints a formatted scorecard to stdout. This is the proof that the end-to-end
chain works: JD text -> extract_jd -> extract_resume -> score_candidate -> Scorecard.
"""

from __future__ import annotations

import time

from config import SAMPLES_DIR, logger
from pipeline.extractor import extract_jd, extract_resume
from pipeline.parser import parse
from pipeline.scorer import score_candidate

# Hardcoded sample files for v0 (one JD + one resume)
JD_FILE = SAMPLES_DIR / "jd_senior_backend_engineer.txt"
RESUME_FILE = SAMPLES_DIR / "resume_candidate_strong.md"


def main() -> None:
    print("=" * 60)
    print("RECRUITING SCREENER — Phase 2 v0 Demo")
    print("=" * 60)

    # Step 1: Parse JD
    print(f"\n[1/4] Parsing JD: {JD_FILE.name}")
    t0 = time.monotonic()
    jd_raw = parse(JD_FILE)
    print(f"      Extracted {len(jd_raw)} characters in {time.monotonic() - t0:.2f}s")

    # Step 2: Parse resume
    print(f"[2/4] Parsing resume: {RESUME_FILE.name}")
    t0 = time.monotonic()
    resume_raw = parse(RESUME_FILE)
    print(f"      Extracted {len(resume_raw)} characters in {time.monotonic() - t0:.2f}s")

    # Step 3: Extract structured data
    print("[3/4] Extracting structured fields via Claude tool use...")
    t0 = time.monotonic()
    jd = extract_jd(jd_raw)
    resume = extract_resume(resume_raw)
    print(f"      JD: {jd.role_title} @ {jd.company or 'N/A'}")
    print(f"      Resume: {resume.full_name}, {resume.current_title or 'N/A'}")
    print(f"      Extraction completed in {time.monotonic() - t0:.2f}s")

    # Step 4: Score
    print("[4/4] Scoring candidate...")
    t0 = time.monotonic()
    scorecard = score_candidate(jd, resume)
    print(f"      Scoring completed in {time.monotonic() - t0:.2f}s")

    # Print the scorecard
    print()
    print("=" * 60)
    print("SCORECARD")
    print("=" * 60)
    print(f"  Candidate:  {scorecard.candidate_name}")
    print(f"  Role:       {scorecard.jd_role}")
    print(f"  Overall:    {scorecard.overall_score:.1f}/100")
    print(f"  Confidence: {scorecard.confidence}")
    print()
    print(f"  Recommendation: {scorecard.recommendation.value.upper()}")
    print()
    print("  Rationale:")
    for line in scorecard.rationale.split("\n"):
        print(f"    {line}")
    print()
    print("  Criterion Scores:")
    for cs in scorecard.criterion_scores:
        bar = "█" * (cs.score // 10) + "░" * (10 - cs.score // 10)
        print(f"    [{bar}] {cs.score:3d}/100  {cs.criterion}")
        print(f"           Evidence: \"{cs.evidence[:120]}{'...' if len(cs.evidence) > 120 else ''}\"")
    print()
    print("=" * 60)
    print("Phase 2 v0 demo complete.")


if __name__ == "__main__":
    main()
