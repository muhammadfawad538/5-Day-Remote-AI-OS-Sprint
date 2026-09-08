"""Run v0 demo and save scorecard to a file (bypasses terminal truncation)."""
from __future__ import annotations

import time
from pipeline.parser import parse
from pipeline.extractor import extract_jd, extract_resume
from pipeline.scorer import score_candidate
from config import SAMPLES_DIR

JD_FILE = SAMPLES_DIR / "jd_senior_backend_engineer.txt"
RESUME_FILE = SAMPLES_DIR / "resume_candidate_strong.md"

jd_raw = parse(JD_FILE)
resume_raw = parse(RESUME_FILE)
jd = extract_jd(jd_raw)
resume = extract_resume(resume_raw)
scorecard = score_candidate(jd, resume)

lines = []
lines.append("=" * 60)
lines.append("SCORECARD")
lines.append("=" * 60)
lines.append(f"  Candidate:  {scorecard.candidate_name}")
lines.append(f"  Role:       {scorecard.jd_role}")
lines.append(f"  Overall:    {scorecard.overall_score:.1f}/100")
lines.append(f"  Confidence: {scorecard.confidence}")
lines.append("")
lines.append(f"  Recommendation: {scorecard.recommendation.value.upper()}")
lines.append("")
lines.append("  Rationale:")
for line in scorecard.rationale.split("\n"):
    lines.append(f"    {line}")
lines.append("")
lines.append("  Criterion Scores:")
for cs in scorecard.criterion_scores:
    bar = chr(9608) * (cs.score // 10) + chr(9617) * (10 - cs.score // 10)
    lines.append(f"    [{bar}] {cs.score:3d}/100  {cs.criterion}")
    evidence = cs.evidence[:150] + "..." if len(cs.evidence) > 150 else cs.evidence
    lines.append(f"           Evidence: \"{evidence}\"")
lines.append("")
lines.append("=" * 60)
lines.append(f"Phase 2 v0 demo complete. Result: {scorecard.recommendation.value.upper()}")

output = "\n".join(lines)
print(output)
with open("E:/must-assesment/scorecard_result.txt", "w", encoding="utf-8") as f:
    f.write(output)
