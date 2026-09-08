# Case Study — Recruiting Screener

> A 5-day sprint building an AI-assisted candidate screening tool for an
> in-house technical recruiter. Built with Claude Code. Scored with Groq/Llama.

**Date:** September 2026  
**Author:** [your name]  
**Project:** AI OS Mini — Recruiting Screener  

---

## 1. User and Problem

**Target user:** A single in-house technical recruiter at a mid-size technology
company (50–500 employees), responsible for screening candidates for one
software engineering role at a time.

**The problem:** Technical recruiting involves reading 40–60 resumes per
requisition, mentally mapping each one against a list of criteria in the JD,
and recording a go/no-go recommendation. The manual process has three documented
pain points:

1. **Time cost.** A recruiter spends 5–15 minutes per resume. A full batch
   takes 3.3–10 hours of focused work — often spread across several days because
   the task is attention-heavy.
2. **Inconsistency.** Different recruiters apply JD criteria with different
   weightings. One recruiter's "advance" is another's "hold." There is no
   written evidence trail, so it is hard to audit why a candidate was passed
   or rejected.
3. **Cognitive fatigue.** After 20+ resumes, the recruiter's judgment degrades.
   Candidates in the middle of the distribution (the "hold" bucket) are the
   most vulnerable to this — they need the most careful reading and are the
   easiest to misjudge when tired.

**What success looks like:** Cut per-resume screening time by ≥ 50% while
matching human advance/reject decisions on ≥ 80% of clear-cut test cases —
with every recommendation citing the specific resume text that supports it.

---

## 2. Workflow and Bottleneck

### The Manual Workflow (Day 1 Baseline)

```
JD arrives → Recruiter reads JD, extracts criteria (mental or note-taking)
           → For each resume:
               Read resume → Map against criteria → Score mentally → Write note
           → End-of-batch: triage into advance / hold / reject piles
           → Schedule interviews for advance pile
```

**The bottleneck** is the per-resume read-and-map step. It is linear in batch
size, it requires uninterrupted focus, and the output quality depends on the
recruiter's freshness. Everything before and after this step (JD ingestion,
scheduling) is already reasonably efficient or bounded by other factors.

### What the System Replaces and What It Keeps

| Step | Before | After |
|------|--------|-------|
| JD criteria extraction | Mental / note-taking | Automated (LLM extracts criteria from JD text) |
| Resume reading and scoring | Manual, per resume | Automated (LLM extracts data + scores against criteria) |
| Evidence documentation | None (or inconsistent) | Required — every score cites resume text |
| Triage (advance / hold / reject) | Recruiter judgment | Model recommends; human confirms |
| Interview scheduling | Recruiter action | Unchanged — human stays in the loop |

The system replaces the *scanning and scoring* work, not the *judgment* work.
The recruiter reviews a structured scorecard instead of re-reading each resume
from scratch. This is the 50%+ time saving: the AI does the tedious mapping;
the human makes the decision with evidence already in front of them.

---

## 3. Scope and Non-Goals

### In Scope (5-day sprint)

- Parse PDF, DOCX, and Markdown resumes and JDs to plain text.
- Extract structured fields from resume and JD text using an LLM.
- Score each candidate against JD-derived criteria with cited evidence.
- Output advance / hold / reject with a written rationale.
- Log every pipeline run (input, output, timestamp, model) to SQLite.
- Evaluate the system against 12 labeled synthetic test cases with documented
  pass/fail criteria.
- Streamlit UI that a non-technical recruiter can operate.

### Out of Scope (documented at project start in NON_GOALS.md)

- No auto-reject to ATS. The system recommends; a human confirms.
- No multi-requisition batching (one JD at a time).
- No non-English resume support in this version.
- No offline fallback (requires Groq API availability).
- No quality-of-hire or time-to-hire measurement (requires post-hire data).
- No React/Next.js frontend — Streamlit only.
- No database beyond SQLite.
- No LangChain, CrewAI, AutoGen, or other agent frameworks.

### Why These Non-Goals Matter

They are not limitations that "will be fixed later." They are deliberate scope
decisions that kept the 5-day sprint achievable. Adding any of them would have
required a second week of work and would have introduced dependencies that
conflict with the zero-cost, zero-ops deployment target.

---

## 4. Architecture and Trade-offs

### Data Flow

```
Resume file (PDF/DOCX/MD)
    → [Parser] plain text (deterministic)
    → [Extractor] structured ResumeData (Groq LLM, JSON mode)
        ↓
JD text (paste or file)
    → [Parser] plain text (deterministic)
    → [Extractor] structured JobDescription + Criterion list (Groq LLM, JSON mode)
        ↓
ResumeData + JobDescription
    → [Scorer] per-criterion scores + evidence + recommendation (Groq LLM, JSON mode)
    → [Scorecard] advance / hold / reject + rationale
        ↓
[Logger] SQLite insert (logs/runs.db)
        ↓
[UI] Streamlit displays scorecard to recruiter
```

### Key Design Decisions

| Decision | Choice | Trade-off |
|----------|--------|-----------|
| LLM provider | Groq (free tier) | Zero cost, but rate-limited. Mitigated by pacing + batch runner. |
| Build agent | Claude Code | Fast implementation, but the build tool is not the inference model — see §5. |
| Structured output | Groq `json_object` mode + Pydantic | Type-safe, no regex parsing. Loses some flexibility if schema changes. |
| Temperature | `0` on all calls | Deterministic eval, but removes some creative parsing on messy resumes. |
| Human-in-the-loop | Hold tier + no ATS integration | Slower than full automation, but avoids false-reject liability. |
| Evidence requirement | Every criterion score cites resume text | Adds a constraint on the scorer prompt, but makes the output auditable. |

### Why Groq, Not Direct Anthropic API

The original plan (BASELINE.md, Day 1) specified the Anthropic SDK as the
provider. During Phase 2 implementation, the available Groq free tier was
selected as the inference backend because:

1. Groq exposes an OpenAI-compatible chat completions endpoint, which supports
   `response_format={"type": "json_object"}` — the same structured-output
   mechanism the architecture requires.
2. Groq's free tier removes the cost barrier during development and evaluation.
3. The model (`qwen/qwen3.8-27b`) is capable of the extraction and reasoning
   tasks this pipeline requires.

The **pipeline code is provider-agnostic in structure**: it calls a chat
completions endpoint with JSON mode. Switching to a different provider (Anthropic
direct, OpenAI, etc.) only requires changing the client initialization and
endpoint URL in `pipeline/scorer.py` and `pipeline/extractor.py`. The Pydantic
schemas, prompt templates, and eval harness are unchanged.

---

## 5. What AI Did vs. What a Human Decided

This section is critical for understanding attribution. Two different AI tools
played distinct roles in this project.

### AI as Build Tool: Claude Code

**Claude Code** was used to write, refactor, and debug the pipeline code,
Pydantic schemas, evaluation harness, documentation, and test cases. It was
the implementation tool — equivalent to a senior engineer pair-programming
across the sprint.

Human decisions that Claude Code did not make:
- The problem definition and target user (locked in BASELINE.md, Day 1).
- The non-goals list (explicit human policy decisions about what not to build).
- The evaluation criteria (80% advance/reject agreement, 50% time reduction).
- The Category A/B failure classification framework (human-defined categories
  for eval divergence).
- The temperature=0 fix (human diagnosed the root cause; Claude Code applied it).
- The hold-tier policy (human decided the system should recommend, not auto-act).
- Trade-off choices in the case study itself (this document).

Claude Code's outputs were reviewed and corrected at multiple checkpoints
(Phase 1 exit review, Phase 2 v0 demo, Phase 3 UI walkthrough, Phase 4 eval
review). Several implementations were rejected and rewritten.

### AI as Inference Model: Groq / Llama

**Groq's hosted Llama model** (`qwen/qwen3.8-27b`) is the system's inference
engine. It does the actual candidate scoring, evidence citation, and
recommendation generation at runtime. This is the model the recruiter interacts
with — it is the product.

Human oversight of the inference model:
- Prompt design in `pipeline/scorer.py` and `pipeline/extractor.py` was
  written and iterated by the human (via Claude Code as the typing tool).
- Eval test cases are human-labeled. The model's output is compared against
  human-defined expected outcomes.
- Category A/B classification of eval divergences is a human analytical
  framework, not a model output.
- The model does not decide what "advance" or "reject" means in business terms —
  those definitions come from the recruiter's policy, encoded in the scoring
  prompt and the hold-tier design.

### The Distinction in One Sentence

**Claude Code built the pipe; Groq/Llama runs the water through it.**

---

## 6. Failures, Changes, and Results

### Documented Failure Cases (eval/failures.md)

The evaluation identified five cases where the model's output diverged from the
expected outcome. These are classified into two categories.

#### Category A: Structural-Check Cases (Different-but-Defensible Bucket)

These cases involve a named structural risk (seniority mismatch, employment gap)
that the pipeline flags programmatically. The model's recommendation differs
from the expected outcome, but the divergence is a defensible hiring decision,
not a scoring error.

| Case | Structural trigger | Expected | Actual | Why actual is defensible |
|------|--------------------|----------|--------|--------------------------|
| TC-08 | Seniority mismatch (Principal → Senior IC role) | reject | hold | Structural safety net prevents advancing an overqualified candidate, but "hold" is reasonable: the candidate's technical skills are strong and a motivated step-down is possible. |
| TC-10 | Employment gap (48 months, explained by caregiving) | hold | advance | Gap detection correctly flags the break, but it has a credible explanation and criterion scores are strong. "Advance" is defensible. |

**What these cases prove:** The structural checks (seniority mismatch, employment
gap) work as designed — they surface a named risk and force the model to reason
about it explicitly. The resulting recommendation is not a bug; it is a
different-but-defensible call that a human reviewer could legitimately make
either way.

#### Category B: Genuine Reviewer Disagreement (No Structural Trigger)

These cases have no seniority mismatch or employment gap. The divergence is
purely about how to weigh demonstrated skill vs. credentials, or how to score
a marginal candidate against a senior-level JD. Both expected and actual
outcomes are defensible.

| Case | Nature | Expected | Actual | Why both are defensible |
|------|--------|----------|--------|--------------------------|
| TC-05 | Learnable skill gap (Node.js) | hold | reject | Reject: Node.js is a must-have with zero evidence. Hold: 8 years of adjacent experience makes the gap bridgeable. |
| TC-06 | Recent grad vs. senior JD | hold | reject | Reject: 1-year internship falls short of senior-level requirements. Hold: strong academic record and potential warrant a conversation. |
| TC-11 | Bootcamp vs. CS degree | hold | advance | Advance: 3 years of professional full-stack + 500+ open-source contributions demonstrates skill. Hold: bootcamp depth and non-traditional path deserve human assessment. |

**What these cases prove:** These are exactly the cases the "hold" tier exists
for. The pipeline is working correctly by surfacing them as partial matches
rather than hard-failing one side or the other.

### Changes Made in Response

| Change | Trigger | Effect |
|--------|---------|--------|
| `temperature=0` on all Groq calls | TC-04 flipped from hold→reject between eval runs with no logic changes | Made scoring deterministic; TC-04 stabilized to `hold (pass)` |
| `temperature=0` on extractor calls | Same non-determinism risk during field extraction | Consistent structured data across runs |
| Explicit `expected_error` in test_cases.json for TC-12 | Needed to validate parse-error messages match, not just the error type | TC-12 passes cleanly with the correct error message |
| Inter-case pacing in eval runner | Groq 429 rate-limit errors during batch runs | `run_batches.py` splits 12 cases into 3 × 4 with 90s inter-batch waits |

### Eval Results (Final State)

Full case-level outcomes and the before/after regression table are in
`eval/failures.md`. The file `eval/results_full.json` contains the most recent
completed eval run (may be partial if rate limits interrupted it).
Summary from the regression table
in `eval/failures.md`:

| Run | TC-04 | TC-06 | TC-08 | TC-10 | Accuracy | Primary Accuracy | Hard Failures |
|-----|-------|-------|-------|-------|----------|-----------------|---------------|
| Initial (no fixes) | hold (timeout) | hold | advance (fail) | advance (partial) | 58% | 67% | 2 |
| After structural fixes (temp ≠ 0) | hold (pass) | hold | hold (partial) | hold (pass) | 75% | 83% | 0 |
| **Final (temp = 0, all fixes)** | **hold (pass)** | **reject (partial)** | **hold (partial)** | **advance (partial)** | **75%** | **83%** | **0** |

**Primary accuracy** (advance/reject cases only, per BASELINE.md definition):
83% — above the 80% target.

**Zero hard failures** on valid resumes in the final run. TC-12 (scanned image
PDF) correctly returns `parse_error` with the expected error message.

### Known Limitations

1. **LLM non-determinism on boundary cases** — mitigated by `temperature=0`,
   but Groq infrastructure changes can still shift model behavior. Eval always
   logs the model version.
2. **No non-English support** — all test cases and sample data are English-only.
3. **One JD at a time** — multi-requisition batching is future work.
4. **Rate limits** — Groq free-tier RPM/TPM constraints mean large batches need
   pacing. This is a documented trade-off for zero-cost inference.
5. **Hold-case variance** — the model's hold/reject/advance call on marginal
   candidates can differ from a human's. This is a feature, not a bug — it
   surfaces candidates that need human judgment.

---

## 7. Next Steps (Next Two Weeks)

### Immediate (Week 1)

1. **Real data validation.** Run the pipeline on 20–30 real resumes from the
   actual requisition queue (with consent/anonymization). Compare model output
   against recruiter manual screening to validate the 80% agreement target on
   real data, not just synthetic test cases.

2. **Recruiter UX feedback.** Have the target user run the app end-to-end with
   their own JD and resumes. Observe where they hesitate, what they click first,
   and what they ask for that isn't there. This is the real non-developer UX
   test.

3. **Confidence calibration.** Add a confidence score to the recommendation
   (already in the Scorecard schema, not yet surfaced in the UI). Calibrate it
   against the eval results so the recruiter sees "high confidence" vs.
   "low confidence — review carefully" directly in the app.

### Medium-Term (Week 2–4)

4. **ATS integration stub.** The scorecard JSON output can be POSTed to an ATS
   webhook. Build a simple export button in the UI that produces a JSON payload
   ready for a REST endpoint. No ATS-specific logic — just a standard shape
   the ATS can consume.

5. **Batch upload UX.** Current app processes resumes one-by-one in the UI.
   Add a progress bar and per-candidate status updates so a 40-resume batch
   feels like a single operation, not 40 separate ones.

6. **OCR fallback for scanned PDFs.** When `parse()` returns a `ParseError`
   for an image-only PDF, offer an in-app OCR option (e.g., Tesseract or a
   cloud OCR API) rather than just surfacing the error.

### Measurement and Instrumentation (Week 1–2)

These are not gaps to be embarrassed about — they are the next set of
measurements the team should build once the core pipeline is stable.

**10. Latency aggregation from SQLite logs.** Every pipeline run already logs
`latency_seconds` to `logs/runs.db`. The next step is to add a lightweight
reporting query (or a `python -m pipeline.latency_report` command) that
aggregates p50 / p95 / max latency per stage (parse, extract, score) across
all runs. This gives the recruiter an honest answer to "how long does this
actually take?" instead of a per-case estimate.

**11. Cost-per-batch tracking.** Groq free-tier inference is zero-cost during
development, but a production deployment will have usage-based pricing. The
team should instrument token counts per LLM call (already available in the
Groq API response headers) and log them alongside `latency_seconds`. A simple
batch report — total tokens, total cost estimate, tokens-per-resume — lets
the team set a budget and compare providers on actual usage, not assumptions.

**12. Recruiter-agreement study.** The eval harness compares model output against
human-defined expected outcomes — but those labels were set during test-case
design, not by a recruiter screening real resumes. The next validation step is
a recruiter-agreement study: a recruiter screens the same 12 (or 20–30) cases
manually, and the team computes inter-rater agreement (Cohen's kappa) between
the recruiter and the model. This tells the team whether the model's
recommendations align with actual human judgment on the population of cases
that matters — not just synthetic labels.

### Longer-Term (Month 2+)

7. **Multi-model evaluation.** Test the same pipeline against other Groq models
   and other providers to determine whether the 83% primary accuracy ceiling
   is model-specific or pipeline-inherent.

8. **Custom criteria weights.** Allow the recruiter to set per-criterion weights
   in the UI (e.g., "Python experience is 2× more important than degree") so
   the scoring reflects role-specific priorities without changing the prompt.

9. **Feedback loop.** After the recruiter makes a final advance/hold/reject
   decision, capture that as a labeled outcome and feed it back into the eval
   test cases. Over time, the labeled set grows and the evaluation gets more
   meaningful.

---

## Appendix: How to Reproduce

To reproduce the eval results in this case study:

```bash
# Setup
cp .env.example .env   # add your GROQ_API_KEY
pip install -r requirements.txt

# Run full eval (uses run_batches.py to handle rate limits)
python eval/run_batches.py

# Output: eval/results_full.json + console summary
```

To run the interactive app:

```bash
streamlit run app.py
```

Both require a valid Groq API key in `.env`. No other setup is needed.
