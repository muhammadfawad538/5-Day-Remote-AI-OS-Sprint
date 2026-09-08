# Recruiting Screener — Phase 5 README

> AI-assisted candidate screening — explainable, evidence-based, human-in-the-loop.
> Built as a 5-day sprint by [your name]. Scoring model: **Groq/Llama**. Build tool: **Claude Code**.

---

## What This Is

Recruiting Screener takes a job description and one or more resumes, extracts
structured candidate data, scores each candidate against the JD's criteria with
cited evidence, and outputs an **advance / hold / reject** recommendation — so
a non-technical recruiter can screen candidates faster and more consistently
than manual review.

The system **never auto-rejects** a candidate without surfacing the rationale
to a human first. Every score cites the specific resume text that supports it.

---

## Prerequisites

- Python 3.11 or later
- A **Groq API key** (free tier is sufficient for development)
  — sign up at https://console.groq.com
- No GPU or special hardware required

---

## Setup (3 Steps)

### 1. Clone and create a virtual environment

```bash
git clone git@github.com:muhammadfawad538/5-Day-Remote-AI-OS-Sprint.git
cd 5-Day-Remote-AI-OS-Sprint
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your API key

```bash
cp .env.example .env
# Edit .env and paste your Groq API key:
# GROQ_API_KEY=gsk_your_key_here
# GROQ_MODEL=qwen/qwen3.8-27b   # default; change if you have a different Groq model
```

> **`.env` is gitignored.** Never commit secrets. `.env.example` shows the
> required keys without real values.

---

## Run the App

```bash
streamlit run app.py
```

A browser window opens at `http://localhost:8501`. You can now:

1. **Paste or upload a Job Description** (text, PDF, or DOCX).
2. **Upload one or more resumes** (PDF, DOCX, or Markdown).
3. Click **"Score Candidates"** to run the pipeline.
4. Review the scorecard table — each criterion shows a 0–100 score and
   the exact resume text that supports it.
5. Read the overall recommendation and rationale before making any hiring decision.

---

## Run the Evaluation Harness

```bash
python eval/run_eval.py
```

This runs all 12 labeled test cases and prints a pass/fail summary plus
precision/recall/accuracy metrics.

```bash
python eval/run_eval.py --case TC-01        # single test case
python eval/run_eval.py --limit 6           # first 6 cases only
python eval/run_eval.py --output results.json  # save results
```

### Rate-limit note for full eval runs

The Groq free-tier has a tokens-per-day cap (200k tokens/day on the free plan).
A full 12-case run can exceed that cap mid-batch and return HTTP 429 errors.
The SDK retries automatically with backoff, but sustained exhaustion will stop
the run. For a reliable full eval, use the batched runner which spaces cases
across multiple sessions:

```bash
python eval/run_batches.py
```

This splits 12 cases into 3 batches of 4 with 90-second inter-batch waits.
If you need to re-run specific cases individually (e.g. to debug one failure),
use `eval/run_individual.py` — it processes one case at a time with a 90-second
gap between cases, which is the most reliable path under rate limits.

```bash
python eval/run_individual.py
```

For the authoritative case-level outcomes and the before/after regression table,
see `eval/failures.md`. The file `eval/results_full.json` contains the most
recent completed eval run (may be partial if rate limits interrupted it).

---

## Project Structure

```
├── app.py                    # Streamlit UI — recruiter entry point
├── config.py                 # Environment config, tunables, path constants
├── requirements.txt          # Python dependencies
├── .env.example              # API key template (copy to .env)
├── .gitignore                # ensures .env and logs/ stay out of git
│
├── pipeline/
│   ├── schemas.py            # Pydantic models: ResumeData, JobDescription,
│   │                         # CriterionScore, Scorecard, Recommendation
│   ├── parser.py             # PDF/DOCX/MD → plain text (deterministic)
│   ├── extractor.py          # text → structured fields (Groq JSON-mode)
│   ├── scorer.py             # evidence-based scoring + recommendation (Groq)
│   └── logger.py             # SQLite run logging (logs/runs.db)
│
├── eval/
│   ├── test_cases.json       # 12 labeled synthetic test cases
│   ├── rubric.md             # eval pass/fail criteria
│   ├── run_eval.py           # eval harness (single run)
│   ├── run_batches.py        # batched eval (3 × 4, handles 429s)
│   ├── failures.md           # documented failure cases & root-cause analysis
│   └── results_full.json     # latest eval results
│
├── data/samples/             # 3 JDs + 9 synthetic resumes (including an
│                             # image-only PDF to exercise the parse-error path)
│
├── logs/                     # SQLite run log (gitignored)
│
├── WORKFLOW_MAP.md           # manual recruiting workflow mapped to system
├── BASELINE.md               # Day 1 baseline metrics and targets
├── NON_GOALS.md              # explicit out-of-scope list
├── ARCHITECTURE.md           # data flow, schemas, design decisions
├── RUNBOOK.md                # operator / maintainer instructions
├── CASE_STUDY.md             # full project write-up
├── AI_COLLABORATION_NOTE.md  # what was AI-built vs. human-decided
├── FEEDBACK.md               # proxy-user feedback and changes made in response
└── docs/
    └── project_context.md    # project instructions and constraints
```

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| LLM provider | **Groq** (`qwen/qwen3.8-27b`) | Free-tier inference; low latency; JSON-mode support |
| Build agent | **Claude Code** (Anthropic) | CLI agent that wrote the pipeline code; not the inference model |
| Structured output | **Pydantic** + Groq `json_object` mode | Type-safe contracts; no regex parsing |
| PDF parsing | **pdfplumber** / **pymupdf** | Deterministic text extraction |
| Word parsing | **python-docx** | Deterministic text extraction |
| Storage | **SQLite** via **sqlmodel** | Zero-config run logging |
| UI | **Streamlit** | Non-developer-facing; no frontend framework needed |
| Eval | Plain Python + JSON | No agent frameworks; explicit pass/fail logic |

**What is explicitly NOT used:** LangChain, CrewAI, AutoGen, React, Next.js,
any cloud database.

---

## Key Design Decisions

### Scoring model vs. build tool

**Groq/Llama** is the inference model that actually scores candidates.
**Claude Code** is the build tool that wrote the pipeline code, tests, and
documentation. These are separate roles — the case study and this README
make that distinction explicit so it is not blurred.

### Temperature = 0 for reproducibility

All Groq LLM calls use `temperature=0` to eliminate run-to-run variance on
boundary cases. See `eval/failures.md` for the full before/after regression
table and the Category A/B failure framing.

### Human stays in the loop

The system **recommends**; it never sends an auto-reject to an ATS. The "hold"
tier exists precisely because some candidates are genuinely ambiguous — both a
human reviewer and the model can be correct from different perspectives.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `GROQ_API_KEY not found` | `.env` missing or key blank | Run `cp .env.example .env` and paste your key |
| `429 Too Many Requests` | Hit Groq free-tier RPM | Wait 60s; `run_batches.py` handles this with retries |
| `PDFParseError: no extractable text` | Resume is a scanned image | Flag for OCR; the pipeline surfaces the error clearly |
| App won't start | Port 8501 in use | `streamlit run app.py --server.port 8502` |
| Eval case fails with `timeout_error` | Network / Groq outage | Retry; see `RUNBOOK.md` for timeout escalation |

For full operator instructions, see **RUNBOOK.md**.

---

## License

MIT (or your preferred license) — add a `LICENSE` file if distributing.
