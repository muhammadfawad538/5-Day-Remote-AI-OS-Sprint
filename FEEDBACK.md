# Proxy User Feedback — Phase 3 and Phase 4

This document records what was observed when the developer used the Streamlit app
as a proxy for the target user (in-house technical recruiter), and what changed
in response. All observations are drawn from actual testing during Phase 3 UI
validation and Phase 4 eval review.

---

## Phase 3 — Proxy User Session

**What I observed:**

1. **App loaded and ran without terminal work.** I opened `streamlit run app.py`,
   pasted a JD into the text area, uploaded three resumes, clicked Score Candidates,
   and got a results table. No command-line interaction was needed after launch.

2. **Scorecards displayed correctly.** Each candidate row showed a recommendation
   badge (advance / hold / reject), an overall score, and a rationale paragraph.
   Clicking into a candidate revealed per-criterion scores with the exact resume
   text cited as evidence beneath each one.

3. **Hold-tier candidates were clearly flagged.** Marginal candidates received a
   yellow hold badge rather than being force-classified as advance or reject. This
   matched the intended design: the model should surface ambiguity, not hide it.

4. **Parse errors surfaced clearly.** When I uploaded the scanned-image PDF
   (`resume_candidate_scanned_image.pdf`), the app returned a ParseError with a
   readable message ("PDF contained no extractable text") rather than crashing or
   silently skipping the file.

**What changed in response:**

- **Scorecard visibility.** The initial app layout buried the criterion scores and
  evidence citations inside a collapsible expander. During testing, I found myself
  clicking into every candidate just to see the evidence — which defeated the
  purpose of showing it. I restructured the layout so the scorecard is visible by
  default. Evidence citations are now the first thing the recruiter sees, not
  something they have to expand.

- **Evidence citation enforcement.** The first version of the scorer prompt
  produced overall scores with a short rationale paragraph but weak per-criterion
  evidence citations — sometimes paraphrastic, sometimes missing entirely. I
  rewrote the scorer prompt to require explicit "Evidence:" fields per criterion,
  with verbatim resume text. This made the evidence layer auditable and is the
  core feature the demo highlights.

- **Eval runner retry logic.** During the first full eval attempt, multiple test
  cases failed with HTTP 429 rate-limit errors from the Groq free-tier API. The
  eval runner had no retry logic and no inter-case pacing, so a single 429 would
  stop the run. I specified the requirement for paced retries and batched
  execution; Claude Code implemented `run_batches.py` (3 batches of 4, with
  90-second inter-batch waits) and added inter-call delays within the eval
  runner. Subsequent runs completed successfully with SDK-level backoff handling
  individual 429s.

---

## Phase 4 — Eval Review

**What I observed:**

1. **TC-08 and TC-10 exposed a missing structural safety net.** The model advanced
   an overqualified candidate (TC-08, Principal-level engineer applying for Senior
   IC role) and a candidate with a 48-month employment gap (TC-10) without flagging
   either as a structural risk. The scores were technically defensible, but the
   recruiter would want to see those risks called out explicitly — not buried in
   the criterion scores.

2. **TC-12's error type was wrong.** The scanned-image PDF returned a
   `timeout_error` instead of the expected `parse_error`. This means the parser
   is slow enough on image PDFs that it exhausts the request timeout before
   reaching the path that raises a ParseError. Scanned PDFs will consistently
   misclassify as timeouts rather than surfacing as unreadable files.

**What changed in response:**

- **Structural checks added to the scorer.** I added a third Groq LLM call in
  `pipeline/scorer.py` that runs explicit checks for seniority mismatch and
  employment gaps before returning "advance." This is now a named, programmatic
  step in the scoring pipeline — not an implicit part of the criterion scores.
  TC-08 and TC-10 now correctly surface these risks. The scores and evidence
  citations remain unchanged; the structural check is an additional signal that
  forces the model to reason about non-criterion risks explicitly.

- **temperature=0 on all LLM calls.** During eval, I noticed TC-04 flipping
  between `hold` and `reject` across runs with no scoring-logic changes. I
  diagnosed the root cause (Groq's default non-zero temperature introducing
  run-to-run variance on marginal cases) and instructed the fix. Claude Code
  applied `temperature=0` to every Groq call in both `extractor.py` and
  `scorer.py`. This made scoring deterministic and stabilized the eval results.

- **TC-12 documented as a known limitation.** The timeout vs. parse_error
  misclassification is documented in `eval/failures.md` as a real classification
  issue (scanned PDFs hit the request timeout before the parse_error path), not
  a one-off fluke. No code fix was applied — the parser behavior is a
  deeper issue that requires more runway than was available.

---

## Summary of Changes by Phase

| Phase | Observation | Change Made |
|-------|-------------|-------------|
| 3 | Scorecard buried in expander | Restructured layout — evidence visible by default |
| 3 | Weak evidence citations in scorer output | Rewrote scorer prompt to require verbatim "Evidence:" per criterion |
| 3 | Eval runner failed on 429 rate limits | Added `run_batches.py` with inter-batch waits and SDK retry backoff |
| 4 | Model advanced overqualified / gapped candidates without flagging risks | Added structural_checks step (seniority mismatch, employment gap) before returning "advance" |
| 4 | Non-deterministic eval results on marginal cases | Applied `temperature=0` to all Groq calls |
| 4 | Scanned PDFs misclassified as timeout instead of parse_error | Documented as known limitation in `eval/failures.md` |
