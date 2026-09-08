# Baseline — Manual Recruiting Screening

This document records the current (manual) screening process metrics, the specific
success metrics we are targeting, and the assumptions behind those targets.

> **Note on data:** All test cases use fictional candidates, fictional JDs, and
> fictional companies. This represents a plausible mid-size tech-company hiring
> scenario — not real employer or candidate data. The synthetic data is clearly
> labeled as such in `eval/test_cases.json`.

---

## Scenario Definition

**Target user:** A single in-house technical recruiter at a mid-size company
(50–500 employees), screening candidates for one specific role at a time.

**Typical batch size:** 40–60 resumes per requisition, designed to support
30–80 without structural changes.

**JD input modes:**
1. **Primary:** Recruiter pastes JD text directly into the app.
2. **Secondary:** Recruiter uploads JD as a PDF or DOCX file.

**Current workflow:** Recruiter reads each resume, mentally maps it against the
JD criteria, and enters a short note with a go/no-go recommendation into an
ATS or spreadsheet. No written evidence, no consistent scoring rubric.

---

## Current-State Metrics (Estimated)

| Metric | Estimate | Rationale |
|--------|----------|-----------|
| Time per resume screened | 5–15 minutes | Typical recruiter estimate for tech roles |
| Primary batch size | 40–60 resumes | Mid-size company, one requisition at a time |
| Supported batch range | 30–80 resumes | Design ceiling without async / queue changes |
| Time to screen a full batch (40 resumes) | 3.3–10 hours | Directly scales with per-resume time |
| Turnaround from JD to interview invites | 5–10 business days | Estimated; screening is one component |
| Inter-recruiter pass-rate variance | 15–30% | Industry observation; needs validation |

---

## Success Metrics for This System

### Primary Metric: Time Efficiency
> **Cut per-resume screening time by ≥ 50%.**

- **Measured as:** average seconds per resume from JD + resume input to final scorecard ready for recruiter review.
- **Baseline comparison:** manual time per resume (5–15 min).
- **Target:** ≤ 3 min/resume. Note: this is "AI-assisted" time — the recruiter still reviews each scorecard before confirming any decision. The time saving comes from the AI doing the scanning and scoring work, not from skipping human review.

### Secondary Metric: Decision Agreement (Clear-Cut Cases Only)
> **On advance/reject cases — the AI recommendation matches the human label on ≥ 80% of test cases.**

- **Scope:** This 80% bar applies **only** to test cases where the expected outcome is clearly `advance` or clearly `reject` — i.e., candidates with an unambiguous fit or mismatch against the JD.
- **Hold cases are excluded from this metric.** `hold` is the system's honest admission that the evidence is ambiguous; forcing hold cases into an agreement metric would push the model toward false confidence.
- **Measured as:** exact match on `advance / reject` vs. `expected_outcome` for those specific test cases.
- **Reported alongside:** precision, recall, and accuracy from `eval/run_eval.py` — broken out by category (advance, hold, reject) so the recruiter can see where the system is strong vs. uncertain.

### Tertiary Metric: Consistency
> **Inter-run variance on the same input is 0%** (deterministic given same model version).

- **Measured as:** re-running the same 3 test cases twice; scores must be identical.
- **Rationale:** inconsistent outputs erode recruiter trust. The pipeline (parser + LLM calls) must be deterministic for the same inputs.

---

## Test Case Distribution

The test cases in `eval/test_cases.json` are distributed as:

| Category | Count | Agreement Metric |
|----------|-------|-----------------|
| Strong advance (clear match) | 3 | Included in 80% bar |
| Clear reject (clear mismatch) | 3 | Included in 80% bar |
| Marginal / hold | 3 | Excluded from 80% bar (reported separately) |
| Edge case: career gap / non-linear path | 2 | Excluded; system may output hold |
| Failure scenario: unreadable file | 1 | Measured separately (ParseError correctness) |

**Total: 12 test cases**, all synthetic and clearly labeled.

---

## What We Are NOT Measuring (for now)

| Not Measuring | Why |
|--------------|-----|
| Time-to-hire impact | Too many downstream factors; out of scope for 5-day sprint |
| Quality of hire (post-hire performance) | Not available in 5 days |
| Recruiter satisfaction / NPS | No formal user research planned |
| Cost savings | Requires salary/hour data we don't have |
| Hold-case agreement rate | Hold means "needs human judgment" — forcing agreement here defeats the purpose |

---

## Assumptions

1. **All test-case JDs and resumes are in English.** Non-English support is a future iteration.
2. **Resumes are text-readable PDFs or DOCX.** Scanned/image-only PDFs surface a `ParseError` and are flagged for human handling.
3. **JD criteria are extractable from text.** Extremely poorly written JDs with no discernible requirements surface a low-confidence flag.
4. **The Anthropic API is available and responsive.** No offline fallback is planned.
5. **One recruiter, one role at a time.** Multi-requisition batching is future work.
6. **Synthetic test data represents a plausible tech-company hiring scenario.** It is not real employer or candidate data. This caveat is carried into `CASE_STUDY.md`.

---

## Answers to Open Questions (Locked)

| Question | Answer |
|----------|--------|
| Targets | 50% time reduction; 80% advance/reject agreement only |
| Real vs. synthetic data | Synthetic — clearly labeled, plausible tech-company scenario |
| Primary user | Single in-house technical recruiter, 50–500 employee company |
| Batch size | 40–60 primary target; 30–80 supported range |
| JD input | Text paste (primary) + PDF/DOCX upload (secondary) |
| Model | claude-sonnet-4-20250514 (configurable via .env) |
