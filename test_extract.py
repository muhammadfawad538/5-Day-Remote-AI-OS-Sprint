"""Test extraction only, with full error capture."""
from __future__ import annotations
import traceback
from pipeline.parser import parse
from pipeline.extractor import extract_jd, extract_resume
from config import SAMPLES_DIR

OUT = "E:/must-assesment/scorecard_result.txt"

def log(msg):
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

with open(OUT, "w") as f:
    pass

try:
    jd_raw = parse(SAMPLES_DIR / "jd_senior_backend_engineer.txt")
    log(f"JD parsed: {len(jd_raw)} chars")

    resume_raw = parse(SAMPLES_DIR / "resume_candidate_strong.md")
    log(f"Resume parsed: {len(resume_raw)} chars")

    log("Calling extract_jd...")
    jd = extract_jd(jd_raw)
    log(f"JD extracted: {jd.role_title}")

    log("Calling extract_resume...")
    resume = extract_resume(resume_raw)
    log(f"Resume extracted: {resume.full_name}")

    log("ALL DONE")
except Exception as e:
    log(f"ERROR: {type(e).__name__}: {e}")
    log(traceback.format_exc())
