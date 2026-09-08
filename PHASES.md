# PHASES.md — Execution Roadmap for Claude Code

Read this alongside CLAUDE.md. This file defines the 5 phases of the build. Work through
them **in order**. At the end of each phase, STOP, summarize what you built, list any open
questions/assumptions you made, and wait for my explicit "go ahead to Phase X" before
continuing. Do not skip ahead or start a later phase's work early, even if it seems efficient.

---

## Phase 1 — Discover, Map, and Baseline
**Goal:** Define the problem precisely enough to build and evaluate against.

Do:
- Scaffold the full repo structure from CLAUDE.md (empty stub files, docstrings only —
  no real pipeline logic yet).
- requirements.txt, .env.example fully populated.
- Create `WORKFLOW_MAP.md`: trigger -> input -> judgment -> tool -> approval -> output ->
  exception, for the manual recruiting screening workflow. Ask me questions inline if you
  need real details (target user, resume volume/day, JD source format, current turnaround
  time) rather than guessing.
- Create `BASELINE.md`: manual time-per-resume, batch size, error/inconsistency patterns,
  and the specific success metric we're targeting (e.g. "cut screening time by X% while
  matching human pass/fail decisions Y% of the time").
- Create `eval/test_cases.json` with 8-12 REAL (or clearly-labeled synthetic) test cases:
  mix of representative, edge, and failure scenarios, each with expected_outcome and
  expected_key_evidence.
- Write `NON_GOALS.md`: explicitly state what this system will NOT do in 5 days.

**Phase 1 exit criteria:** I can read WORKFLOW_MAP.md, BASELINE.md, NON_GOALS.md and
test_cases.json and confirm the problem is scoped correctly before any code is written.

---

## Phase 2 — Design the System and Ship v0
**Goal:** A thin, working, end-to-end slice for ONE real input.

Do:
- Write `ARCHITECTURE.md`: data flow diagram (as text/mermaid), input/output schemas
  (reference pydantic models), model/tool/storage/interface choices with rationale, and
  explicit human-approval points.
- Implement `pipeline/schemas.py` fully (pydantic models for ResumeData, Criterion,
  Scorecard, Recommendation).
- Implement a minimal `pipeline/parser.py` (PDF/docx -> text) — happy path only.
- Implement a minimal `pipeline/extractor.py` and `pipeline/scorer.py` using the raw
  Anthropic SDK with tool use / structured output — happy path only, one hardcoded
  sample resume + JD from data/samples/.
- Write `eval/rubric.md`: the pass/fail evaluation rubric and scoring logic you'll use
  in Phase 4.
- Prove v0 works by running one real resume through the full chain and printing the
  final scorecard.

**Phase 2 exit criteria:** One real input moves through parser -> extractor -> scorer ->
output successfully. Show me the output.

---

## Phase 3 — Build the Working Core
**Goal:** A complete, usable core flow a non-developer could run.

Do:
- Harden parser.py/extractor.py/scorer.py: input validation, structured error messages,
  handle malformed/unreadable files gracefully.
- Add at least 2 real integrations/tool-use points (e.g. structured tool-call for
  criteria extraction AND a separate tool-call for evidence-based scoring — or a real
  file-storage/JD-source integration if applicable).
- Build `app.py` (Streamlit): upload JD + resume(s), see results table, view evidence
  per candidate, no technical knowledge required to operate.
- Wire up SQLite logging (logs/runs.db) for every pipeline run: input hash, output,
  timestamp, model, latency.
- Run the FULL pipeline via app.py with a proxy user (this can be me) instead of just
  you running scripts directly.

**Phase 3 exit criteria:** I can open the Streamlit app myself, upload a resume + JD,
and get a result — without you touching the terminal for me.

---

## Phase 4 — Evaluate, Break, and Harden
**Goal:** Prove reliability with evidence, not vibes.

Do:
- Build `eval/run_eval.py`: runs all 8-12 test cases through the pipeline, compares
  actual vs expected_outcome, outputs pass/fail + precision/recall/accuracy vs the
  labeled set, and compares against the Day 1 manual baseline.
- Deliberately break the system: malformed PDFs, contradictory JDs, resumes with no
  matching info, non-English resumes, adversarial/keyword-stuffed resumes — document
  at least 3 concrete failure cases with root-cause analysis in `eval/failures.md`.
- Add the necessary fixes: retries, fallback prompts, confidence scores, or explicit
  "needs human review" flags — whichever the failure analysis justifies.
- Re-run eval after fixes and record before/after results in `eval/regression_results.md`.
- Note any feedback from me (as proxy user) from Phase 3 testing and what you changed
  in response.

**Phase 4 exit criteria:** I can see a clear before/after eval table and understand
exactly where the system is strong vs weak.

---

## Phase 5 — Handoff, Prove Value, and Present
**Goal:** Someone else could pick this up and run it without you.

Do:
- Write final `README.md`: one-command or 3-step setup, prerequisites, how to run.
- Write `RUNBOOK.md`: operator instructions — how to add new test cases, rotate API
  keys, read logs, troubleshoot common errors.
- Write `CASE_STUDY.md` covering: user & problem, workflow & bottleneck, scope/non-goals,
  architecture & trade-offs, what was delegated to AI vs human judgment retained,
  failures/changes/results/limitations, and a next-two-week iteration plan.
- Write `AI_COLLABORATION_NOTE.md`: which AI tools were used and for what, how outputs
  were verified, what was rejected/corrected, and which decisions were made by you
  (the human), not the AI.
- Prepare a demo script/outline in `DEMO_SCRIPT.md` for the 5-minute screen recording
  (I will record the video myself, but I want your outline of what to show and say).
- Final cleanup pass: remove dead code, confirm .env is gitignored, confirm
  requirements.txt is accurate, confirm secrets are not anywhere in the repo.

**Phase 5 exit criteria:** A stranger could clone this repo, follow README.md, and get
a working demo without contacting either of us.

---

## Ground Rules for All Phases
- Always check CLAUDE.md constraints before making a technical choice (no agent
  frameworks, Streamlit only, SQLite only, etc.).
- When something is ambiguous, ask me rather than assuming — but propose a reasonable
  default alongside the question so I can just say "yes, go with that."
- Never invent data or claim a test passed without actually running it.
- If you find yourself wanting to start Phase N+1 work while still in Phase N, stop and
  flag it to me instead of just doing it.
