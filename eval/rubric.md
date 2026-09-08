# Evaluation Rubric — Recruiting Screener

This rubric defines exactly how test cases are scored as pass / fail /
partial. It will be implemented in `eval/run_eval.py` in Phase 4.

---

## Overview

Each test case in `eval/test_cases.json` has:
- `expected_outcome`: `advance`, `hold`, `reject`, or `parse_error`
- `expected_key_evidence`: list of strings — specific evidence the system should cite
- `expected_error` (failure cases only): expected error message substring

The eval harness runs the full pipeline and compares actual output against
these expectations.

---

## Scoring Dimensions

### Dimension 1: Recommendation Accuracy

| Expected | Actual | Result | Points |
|----------|--------|--------|--------|
| advance | advance | **Pass** | 1.0 |
| advance | hold | Partial | 0.5 |
| advance | reject | Fail | 0.0 |
| hold | hold | **Pass** | 1.0 |
| hold | advance | Partial | 0.5 |
| hold | reject | Partial | 0.5 |
| reject | reject | **Pass** | 1.0 |
| reject | hold | Partial | 0.5 |
| reject | advance | Fail | 0.0 |
| parse_error | parse_error | **Pass** | 1.0 |
| parse_error | any other result | Fail | 0.0 |

**Primary metric:** accuracy on advance + reject cases only (excluded: hold
and parse_error). Target: ≥ 80%.

### Dimension 2: Evidence Quality

For each `expected_key_evidence` item, check whether any `CriterionScore.evidence`
field in the actual scorecard contains a meaningful substring match.

- **Full match:** evidence text closely reflects the expected key evidence → 1.0
- **Partial match:** evidence touches the same topic but misses specifics → 0.5
- **No match:** no criterion cites relevant evidence → 0.0

Evidence score = (sum of matches) / (number of expected_key_evidence items).

**Threshold:** evidence score ≥ 0.6 is considered passing for that test case.

### Dimension 3: Parse Error Correctness (failure cases only)

For `expected_outcome: "parse_error"`:
- The pipeline must raise a `ParseError` (not a generic exception).
- The error message must contain the `expected_error` substring.
- Pass: both conditions met. Fail: either condition fails.

---

## Overall Pass/Fail for a Test Case

A test case passes if:
1. Recommendation is exact match (advance/reject cases) OR partial match (hold
   cases) OR exact parse_error match, **AND**
2. Evidence score ≥ 0.6 (or not applicable for parse_error cases)

---

## Batch-Level Metrics (reported by run_eval.py)

| Metric | Formula |
|--------|---------|
| Accuracy | exact_matches / total_test_cases |
| Primary accuracy | exact_matches on advance+reject / advance+reject count |
| Partial credit rate | partial_matches / total_test_cases |
| Evidence score (avg) | mean of per-case evidence scores |
| Pass rate | passing_cases / total_test_cases |
| Parse error rate | correct_parse_errors / parse_error_cases |

---

## Consistency Check (Tertiary Metric)

Run 3 randomly selected test cases twice. Compare criterion scores and overall
score. All values must be identical between runs for consistency to pass.

---

## Reporting

The eval harness outputs:
1. A table with one row per test case: id, expected, actual, recommendation_result,
   evidence_score, overall_pass.
2. Batch-level summary metrics.
3. A breakdown by category (advance, hold, reject, edge, failure).
4. Comparison against Day 1 baseline (from BASELINE.md).
