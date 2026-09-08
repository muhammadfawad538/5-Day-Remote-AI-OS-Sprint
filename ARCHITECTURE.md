# Architecture — Recruiting Screener v0

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RECRUITER (Streamlit UI)                     │
│  Input: pasted JD text OR uploaded JD file + resume file(s)         │
└──────────────┬────────────────────────────────┬─────────────────────┘
               │                                │
               ▼                                ▼
    ┌──────────────────┐          ┌──────────────────────┐
    │  parser.py       │          │  text input (paste)  │
    │  file -> text    │          │  -> raw_text directly │
    └────────┬─────────┘          └──────────┬───────────┘
             │ raw_text                      │ raw_text
             ▼                               │
    ┌────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────┐
│  extractor.py                                         │
│  Pass 1: extract_jd(raw_text) -> JobDescription       │
│  Pass 2: extract_resume(raw_text) -> ResumeData       │
│  (Each is one Groq function call)                     │
└──────────────────────┬────────────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────────────┐
│  scorer.py                                            │
│  Pass 3: criterion_scoring (JD + resume -> scores)    │
│  Pass 4: recommendation (scores -> overall assessment)│
│  (Each is one Groq function call)                     │
└──────────────────────┬────────────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────────────┐
│  Scorecard                                            │
│  candidate_name, jd_role, criterion_scores[],         │
│  overall_score, recommendation, rationale, confidence  │
└──────────────────────┬────────────────────────────────┘
                       │
                       ▼
                  Recruiter review
                  (human-in-the-loop)
                       │
                       ▼
                  Final decision
```

---

## Components

### `config.py`
Loads `GROQ_API_KEY`, `GROQ_MODEL`, `LOG_LEVEL` from `.env`.
Defines repo-rooted paths. Logging configured here.

### `pipeline/parser.py` *(deterministic — no LLM)*
- **Responsibility:** PDF/DOCX -> plain text.
- **Input:** file path.
- **Output:** clean UTF-8 string.
- **Error mode:** raises `ParseError` with specific reason.

### `pipeline/extractor.py` *(LLM — two tool calls)*
- **Responsibility:** raw text -> structured `JobDescription` + `ResumeData`.
- **Input:** raw text strings (from parser or paste).
- **Output:** Pydantic models.
- **Tool calls:**
  1. `extract_jd` tool: JD text -> JobDescription fields.
  2. `extract_resume` tool: resume text -> ResumeData fields.
- **Error mode:** raises `ValueError` if tool call not returned.

### `pipeline/scorer.py` *(LLM — two tool calls)*
- **Responsibility:** JD + ResumeData -> `Scorecard`.
- **Input:** `JobDescription`, `ResumeData`.
- **Tool calls:**
  3. `criterion_scoring` tool: per-criterion 0-100 scores with evidence.
  4. `recommendation` tool: overall score + recommendation + rationale.
- **Error mode:** raises `ValueError` if tool call not returned.

### `pipeline/schemas.py`
All Pydantic models: `JobDescription`, `ResumeData`, `CriterionScore`,
`Scorecard`, `Recommendation` enum.

### `app.py` *(Streamlit — Phase 3)*
Recruiter-facing UI. Upload/paste JD, upload resumes, view scorecards.

### `eval/run_eval.py` *(Phase 4)*
Loads `test_cases.json`, runs pipeline, compares to expected, outputs metrics.

---

## Tool Definitions (Groq Function Calling)

All tool definitions are inline dictionaries matching the Pydantic schemas.
They are defined in `extractor.py` and `scorer.py` as module-level constants
so they're visible in one place.

Why separate tool calls per stage:
- **Extractor tools** focus on data extraction (no scoring).
- **Scoring tool** is a different cognitive task (judgment + weighting).
- Separation lets us debug extraction quality independently from scoring quality.

---

## Human-in-the-Loop Points

| Point | What the human does |
|-------|-------------------|
| JD input | Recruiter provides JD (paste or upload). System does not auto-source JDs. |
| Criteria review | Recruiter can see extracted JD criteria before screening begins. |
| Scorecard review | Recruiter reviews each scorecard before confirming advance/hold/reject. |
| Final decision | System recommends; human confirms or overrides. |

---

## Storage

- **SQLite (sqlmodel):** run logs in `logs/runs.db` — input hash, output,
  timestamp, model version, latency. Wired up in Phase 3.
- **No other database.** All pipeline state is in-memory between stages.

---

## Error Handling Strategy

| Error | Source | Handling |
|-------|--------|---------|
| File not found / wrong format | parser.py | `ParseError` surfaced to recruiter with actionable message |
| Unreadable PDF (scanned image) | parser.py | `ParseError` with "OCR needed" message; recruiter provides text version |
| LLM returns text instead of tool call | extractor/scorer | `ValueError` with diagnostic; surfaces as "extraction failed" to recruiter |
| LLM API error / timeout | Any LLM call | Propagated; Streamlit shows error and allows retry |
| Missing API key | config.py | Fails at import with clear message |

---

## Model Choice

- **Model:** `qwen/qwen3.8-27b` (configurable via `.env`).
- **Rationale:** Qwen3 8B is the best model on this Groq account that
  supports function calling — required for structured extraction and scoring.
  It handles the evidence-citation and reasoning tasks this pipeline needs.
  (Note: the original Llama 3.3 70B target is unavailable on this account;
  if access is granted, swap it back via the GROQ_MODEL env var.)
- **No prompt caching for v0.** Will consider in Phase 4 if latency is an issue.

---

## What v0 Proves

Running `python demo_v0.py` proves:
1. `parser.py` extracts text from a real file.
2. `extract_jd()` returns a valid `JobDescription` via tool use.
3. `extract_resume()` returns a valid `ResumeData` via tool use.
4. `score_candidate()` returns a valid `Scorecard` with evidence.
5. The full chain works without manual intervention.
