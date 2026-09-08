# AI Collaboration Note

This document records which AI tools were used during this project, what they
were asked to do, how their outputs were verified, what was rejected or
corrected, and which decisions were made by the human developer — not the AI.

---

## AI Tools Used

| Tool | Role | When Used |
|------|------|-----------|
| **Claude Code** (Anthropic) | Build agent — wrote code, schemas, tests, docs | Throughout all 5 phases |
| **Groq / qwen/qwen3.8-27b** | Inference model — scores candidates at runtime | Phase 2 onward (pipeline runtime) |

These are two distinct roles. Claude Code was the **implementation tool**;
Groq/Llama is the **product's inference engine**. The distinction matters for
attribution, liability, and evaluation. See §3 for details.

---

## Phase-by-Phase Summary

### Phase 1: Discover, Map, and Baseline

**Human-authored (with Claude Code as a typing/review assistant):**
- Problem definition and target user profile (recruiter, mid-size company).
- Baseline metrics (5–15 min per resume, 40–60 per batch).
- Success metrics: 50% time reduction, 80% advance/reject agreement on
  clear-cut cases only.
- 12 synthetic test cases with expected outcomes and key evidence anchors.
- NON_GOALS.md — explicit policy decisions about what not to build.

**Claude Code contributed:**
- Drafted WORKFLOW_MAP.md from human-described workflow.
- Drafted BASELINE.md structure and tables from human-provided numbers.
- Drafted test_cases.json structure; human reviewed and edited every case.
- Drafted NON_GOALS.md; human revised and approved.

**Verification:** Human read every draft, edited inline, and approved the
Phase 1 exit criteria before proceeding.

---

### Phase 2: Design and Ship v0

**Human-authored:**
- ARCHITECTURE.md data flow diagram and design rationale.
- Pydantic schemas in `pipeline/schemas.py` — field names, types, and
  constraints are human-designed.
- Prompt templates in `extractor.py` and `scorer.py` — human wrote the
  instructions that shape LLM behavior.
- Scoring rubric in `eval/rubric.md`.

**Claude Code contributed:**
- Implemented the parser, extractor, scorer, and logger from human-designed
  schemas and prompts.
- Wrote the demo script (`demo_v0.py`).
- Ran the v0 demo and surfaced the output for human review.

**Verification:** Human ran `python demo_v0.py` and read the scorecard output.
The output confirmed the end-to-end chain worked before Phase 3 began.

**Rejected outputs:**
- Initial scorer prompt produced weak evidence citations. Human rewrote the
  prompt template in `scorer.py` to require explicit "Evidence:" fields per
  criterion.
- Initial parser did not handle DOCX files. Human specified the requirement;
  Claude Code added `python-docx` support.

---

### Phase 3: Build the Working Core

**Human-authored:**
- Streamlit UI layout and user flow decisions.
- SQLite schema design in `pipeline/logger.py`.
- Error message design — human specified that every failure must surface a
  clear message, never silently skip.

**Claude Code contributed:**
- Full `app.py` implementation from human-specified layout.
- Hardened parser with error handling for malformed PDFs and empty files.
- JD caching in `eval/run_eval.py` to avoid redundant API calls.
- Rate-limit pacing logic and inter-call delays.

**Verification:** Human opened `app.py` in Streamlit, uploaded a JD and a
resume, and confirmed a scorecard appeared without any terminal interaction.

**Rejected outputs:**
- Initial app layout had the scorecard buried in an expander. Human requested
  it be visible by default. Claude Code restructured the layout.
- Initial eval runner had no retry logic. Human specified the need; Claude Code
  added the batch runner (`run_batches.py`) with 429 handling.

---

### Phase 4: Evaluate, Break, and Harden

**Human-authored:**
- The Category A/B failure classification framework in `eval/failures.md`.
  This is the most analytically rigorous part of the evaluation — it is a
  human-designed analytical framework, not a model output.
- The regression table and before/after metrics.
- The root-cause diagnosis of the non-determinism issue (temperature not set
  to 0).

**Claude Code contributed:**
- Wrote `eval/run_eval.py` from human-specified comparison logic.
- Implemented the evidence scorer (`score_evidence`) with substring matching.
- Applied the `temperature=0` fix across both `extractor.py` and `scorer.py`
  after human identified the root cause.
- Wrote `eval/failures.md` from human's Category A/B analysis.

**Verification:** Human reviewed the regression table, confirmed the numbers
matched the console output from eval runs, and approved the Phase 4 exit.

**Rejected outputs:**
- First eval run had TC-04 as a timeout error. Human investigated and found
  the Groq API was returning timeouts under load. Claude Code added inter-case
  pacing, which resolved it.
- Initial comparison logic treated hold/reject as "partial" and advance/hold
  as "partial" — human reviewed and confirmed this matches the evaluation
  philosophy (hold means ambiguous, so it is partially correct either way).

---

### Phase 5: Handoff and Present

**Human-authored:**
- This case study structure and all narrative content.
- DEMO_SCRIPT.md outline (what to show and say in the recording).
- The "what AI did vs. human decided" framework itself.

**Claude Code contributed:**
- All five Phase 5 deliverables (README, RUNBOOK, CASE_STUDY, AI_COLLABORATION_NOTE,
  DEMO_SCRIPT).
- Final cleanup: created `.gitignore`, verified `.env` is excluded, confirmed
  `requirements.txt` is accurate.

**Verification:** Human reviewed all Phase 5 documents before submission.

---

## What Was Rejected or Corrected

Across all phases, the following outputs were rejected or required significant
revision:

| Phase | Output | What was wrong | What changed |
|-------|--------|----------------|--------------|
| 1 | test_cases.json initial draft | Some cases had vague expected_key_evidence | Human tightened evidence anchors to distinctive resume phrases |
| 2 | Initial scorer prompt | Evidence citations were weak / paraphrastic | Human rewrote prompt to require verbatim citations with "Evidence:" prefix |
| 3 | App layout | Scorecard hidden in expander | Human restructured to visible-by-default layout |
| 3 | Eval runner | No retry on 429/timeout | Human specified requirement; Claude Code added batch runner |
| 4 | Initial comparison logic | Hold/reject treated inconsistently | Human specified the partial-match map; Claude Code implemented it |
| 4 | First eval run | TC-04 timed out; TC-08 produced unexpected advance | Root cause was rate limits + no temperature=0; both fixed |
| 5 | README initial draft | Mentioned "Anthropic API" as provider | Corrected to reflect Groq as the actual inference backend |

---

## Human Decision Points Where AI Was Overridden or Set Aside

These are moments where Claude Code suggested one path and the human chose a
different one. They are listed explicitly because they reveal where human
judgment shaped the final system.

1. **Provider choice (Phase 2):** Claude Code initially wrote the pipeline
   against the Anthropic SDK (as specified in CLAUDE.md). The human decided
   to switch to Groq mid-Phase 2 because the Groq free tier made development
   and evaluation zero-cost. This required refactoring the client calls but
   did not change the schemas or prompt logic.

2. **Temperature policy (Phase 4):** Claude Code's initial Groq calls did not
   set `temperature=0`. The human noticed non-determinism in eval results,
   diagnosed the root cause, and instructed the fix. Claude Code applied it
   across both files.

3. **Category A/B framework (Phase 4):** Claude Code initially wrote
   `eval/failures.md` as a flat list of "deviations." The human introduced
   the Category A/B distinction — a structural, analytical framework that
   turns eval divergences into evidence about system behavior rather than
   just a list of failures. This is the single most important evaluation
   artifact in the project.

4. **Evidence citation design (Phase 2):** Claude Code's first scorer
   implementation produced overall scores with a short rationale paragraph.
   The human required per-criterion evidence citations — a constraint that
   shaped the entire Scorecard schema and the scorer prompt.

5. **Hold-tier policy (Phase 1, locked):** The human decided early that the
   system would recommend, not auto-act. This is a policy decision, not a
   technical one, and it was made before any code was written. Claude Code
   implemented it faithfully throughout.

---

## Verification Practices

- **Every Phase exit required human review** before the next phase began.
- **Eval results were read, not just generated.** The human inspected
  `eval/results_full.json` and the regression table in `failures.md` to
  confirm the numbers matched the console output.
- **Test case labels were human-verified.** All 12 test cases in
  `test_cases.json` are explicitly labeled `synthetic` and use fictional
  candidates, JDs, and companies. No real personal data is included.
- **The case study was self-tested.** Before submission, the human followed
  the README from a cold clone to confirm a stranger could set it up
  without assistance.

---

## Summary

Claude Code was an efficient and capable build tool. It wrote code, schemas,
tests, and documentation faster than manual typing would allow. But every
architectural decision, policy constraint, evaluation criterion, and
corrective action in this project was made by the human. The AI's outputs
were reviewed, revised, and approved at every phase boundary.

The most important human contributions were:
1. Defining the problem and its boundaries (Phases 1 and NON_GOALS.md).
2. Designing the evaluation framework (Category A/B, primary accuracy metric).
3. Diagnosing the temperature non-determinism issue (Phase 4).
4. Setting the hold-tier policy and evidence-citation requirement (Phase 1–2).
5. Writing and approving every word of this case study (Phase 5).
