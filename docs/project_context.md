# CLAUDE.md — Project Context for Claude Code

## Project
**Recruiting Screener** — an AI system that takes a job description + a batch of resumes,
extracts structured candidate data, scores each candidate against JD-derived criteria with
cited evidence, and outputs a recommendation (advance / hold / reject) — so a non-technical
recruiter can screen candidates faster and more consistently than manual review.

This is a 5-day sprint project ("AI OS Mini"). It must be:
- Real and usable by someone other than the developer
- Evaluated against a manual/baseline process with a labeled test set
- Explainable: clear pipeline stages, no black-box scoring

## Tech Stack (do not deviate without discussion)
- Python 3.11+
- Groq SDK (`groq`) — raw SDK, **no LangChain/CrewAI/agentic frameworks**.
  Uses Groq's OpenAI-compatible chat completions endpoint with JSON-mode
  (`response_format={"type": "json_object"}`) for structured extraction/scoring.
  Model: `qwen/qwen3.8-27b` (configurable via `GROQ_MODEL`).
  **Note:** Groq free-tier has rate limits (RPM/TPM). This is a documented
  trade-off for zero-cost inference during development; see eval harness pacing
  and retry-with-backoff logic for mitigation.
- `pydantic` for all structured data contracts (resume schema, criteria schema, scorecard schema)
- `pdfplumber` / `pymupdf` for PDF parsing, `python-docx` for Word files
- `sqlite3` (or `sqlmodel`) for run logging / eval history
- `streamlit` for the UI (non-developer facing)
- `python-dotenv` for config/secrets — never hardcode API keys
- `pytest` or a plain script for the eval harness

## Repo Structure
```
recruiting-screener/
├── app.py                # Streamlit UI — entry point for the recruiter
├── pipeline/
│   ├── parser.py         # resume/JD file -> plain text
│   ├── extractor.py      # text -> structured fields (pydantic models)
│   ├── scorer.py         # criteria matching + evidence citation + recommendation
│   └── schemas.py        # all pydantic models live here
├── eval/
│   ├── test_cases.json   # 8-12 labeled test cases (resume, JD, expected outcome)
│   └── run_eval.py       # runs pipeline against test_cases.json, reports pass/fail + metrics
├── data/samples/         # anonymized or synthetic sample resumes/JDs for demo & testing
├── logs/                 # sqlite db + run logs (gitignored)
├── .env.example
├── requirements.txt
└── README.md
```

## Architecture Principles
1. **Separate concerns strictly**: parsing (deterministic code) is never mixed with LLM calls.
   Parse to clean text first, THEN send to Claude.
2. **Every LLM call has a strict pydantic schema for its output.** No free-text parsing of
   Claude's responses with regex. Use tool use / structured output enforcement.
3. **Evidence-based scoring only.** Every criterion score must cite the specific resume text
   that supports it. No unexplained numeric scores.
4. **Human stays in the loop.** The system recommends; it never auto-rejects a candidate
   without a human seeing the rationale first.
5. **Every run is logged** (input, output, timestamp, model version) to sqlite — this is
   required for the Day 4 evaluation package and Day 5 case study metrics.
6. **Fail loudly and specifically.** If parsing fails or a resume is unreadable, surface a
   clear error to the recruiter — never silently skip or guess.

## Coding Conventions
- Type hints everywhere; pydantic models for all cross-boundary data.
- Small, single-responsibility functions — each pipeline stage should be independently testable.
- No hardcoded API keys, file paths, or model names — pull from `.env` / a config module.
- Write docstrings that explain *why*, not just what (I'll reuse these for the case study).

## Current Phase
We are on **Day 1: Discover, Map, and Baseline**. Do NOT build the full pipeline yet unless
explicitly asked. Focus on: workflow mapping, baseline measurement scripts/notes, and
drafting the 8–12 test cases in `eval/test_cases.json`.

## What NOT to do
- Don't introduce LangChain, CrewAI, AutoGen, or any agent framework.
- Don't add a database beyond SQLite.
- Don't build a React/Next.js frontend — Streamlit only, to keep Day 3 scope realistic.
- Don't over-engineer the eval harness — plain Python + JSON test cases is sufficient.
