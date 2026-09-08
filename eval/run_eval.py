"""Evaluation harness for the recruiting-screener pipeline.

Runs all test cases from eval/test_cases.json through the full pipeline,
compares actual output against expected outcomes, and reports pass/fail
plus precision/recall/accuracy metrics against the Day 1 baseline.

Usage:
    python eval/run_eval.py                  # run all test cases
    python eval/run_eval.py --case TC-01     # run a single case
    python eval/run_eval.py --limit 6        # run first 6 cases
    python eval/run_eval.py --output results.json  # save results to file
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from config import EVAL_INTER_CASE_DELAY, EVAL_INTER_CALL_DELAY
from pipeline.extractor import extract_jd, extract_resume
from pipeline.logger import log_run, set_model_version
from pipeline.parser import ParseError, parse
from pipeline.scorer import score_candidate
from pipeline.schemas import Recommendation

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_PATH = REPO_ROOT / "eval" / "test_cases.json"
RESULTS_PATH = REPO_ROOT / "eval" / "results.json"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TestResult:
    """Result for a single test case."""

    case_id: str
    category: str
    description: str
    expected_outcome: str
    actual_outcome: str | None
    recommendation_result: str  # pass / partial / fail / error
    evidence_score: float | None
    overall_pass: bool
    error: str | None = None
    latency_seconds: float = 0.0
    criterion_scores: list[dict] = field(default_factory=list)


@dataclass
class BatchMetrics:
    """Aggregate metrics across all test cases."""

    total: int
    exact_matches: int
    partial_matches: int
    failures: int
    accuracy: float
    partial_rate: float
    fail_rate: float
    primary_accuracy: float  # advance+reject only
    primary_total: int
    primary_exact: int
    evidence_avg: float | None
    parse_error_correct: int
    parse_error_total: int
    timeout_total: int
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Recommendation comparison
# ---------------------------------------------------------------------------


def compare_recommendations(expected: str, actual: str) -> str:
    """Compare expected vs actual recommendation.

    Returns 'pass', 'partial', or 'fail' per the eval rubric.
    """
    if expected == actual:
        return "pass"

    # Partial matches
    partial_map = {
        ("advance", "hold"): True,
        ("advance", "reject"): False,
        ("hold", "advance"): True,
        ("hold", "reject"): True,
        ("reject", "hold"): True,
        ("reject", "advance"): False,
    }
    is_partial = partial_map.get((expected, actual), False)
    return "partial" if is_partial else "fail"


# ---------------------------------------------------------------------------
# Evidence scoring
# ---------------------------------------------------------------------------


def score_evidence(expected_key_evidence: list[str], criterion_scores: list[Any]) -> float:
    """Check how many expected evidence items appear in actual criterion scores.

    Uses substring/partial matching: each expected item is broken into
    meaningful phrases (>3 chars), and the item counts as a match if any
    phrase appears in the actual evidence text.  This tolerates paraphrasing
    by the model while still requiring the right topic to be cited.
    """
    if not expected_key_evidence:
        return 1.0  # no evidence required

    if not criterion_scores:
        return 0.0

    # Build a single blob of all evidence text from the scorecard
    actual_evidence_blob = " ".join(
        (cs.evidence or "").lower() for cs in criterion_scores
    )

    matches = 0
    for expected_item in expected_key_evidence:
        # Break into meaningful phrases (>3 chars) for partial matching
        phrases = [p.lower() for p in expected_item.split() if len(p) > 3]
        if not phrases:
            matches += 1  # trivial match
            continue
        # Count how many phrases appear in the evidence blob
        found = sum(1 for p in phrases if p in actual_evidence_blob)
        # Match if at least half the phrases are present
        if found >= max(1, len(phrases) // 2):
            matches += 1

    return matches / len(expected_key_evidence)


# ---------------------------------------------------------------------------
# Pipeline runner (single test case)
# ---------------------------------------------------------------------------


# Global JD cache to avoid redundant API calls
_jd_cache: dict[str, Any] = {}


def _get_jd(jd_raw: str, jd_path: Path) -> Any:
    """Extract JD with caching — multiple test cases often share the same JD."""
    cache_key = str(jd_path)
    if cache_key not in _jd_cache:
        _jd_cache[cache_key] = extract_jd(jd_raw)
    return _jd_cache[cache_key]


def run_test_case(
    case: dict[str, Any],
    model_version: str,
) -> TestResult:
    """Run one test case through the full pipeline.

    Returns a TestResult with all scoring details.
    """
    case_id = case["id"]
    category = case["category"]
    description = case["description"]
    expected_outcome = case["expected_outcome"]
    expected_key_evidence = case.get("expected_key_evidence", [])
    expected_error = case.get("expected_error")

    jd_path = REPO_ROOT / case["jd_file"]
    resume_path = REPO_ROOT / case["resume_file"]

    latency = 0.0
    actual_outcome = None
    rec_result = "fail"
    evidence_score = None
    overall_pass = False
    error_msg = None
    criterion_scores = []

    try:
        t0 = time.monotonic()

        # Parse JD (same for all cases — some share a JD)
        jd_raw = parse(jd_path)

        # Parse resume
        resume_raw = parse(resume_path)

        # Extract structured data (JD cached across cases sharing the same JD file)
        jd = _get_jd(jd_raw, jd_path)
        resume = extract_resume(resume_raw)

        # Score
        scorecard = score_candidate(jd, resume)

        latency = time.monotonic() - t0

        actual_outcome = scorecard.recommendation.value
        rec_result = compare_recommendations(expected_outcome, actual_outcome)
        criterion_scores = [
            {"criterion": cs.criterion, "score": cs.score, "evidence": cs.evidence}
            for cs in scorecard.criterion_scores
        ]

        # Evidence scoring (skip for parse_error cases)
        if expected_outcome != "parse_error":
            evidence_score = score_evidence(expected_key_evidence, scorecard.criterion_scores)

        # Overall pass: recommendation exact/partial + evidence threshold
        if expected_outcome == "parse_error":
            overall_pass = False  # handled separately
        else:
            rec_ok = rec_result in ("pass", "partial")
            ev_ok = evidence_score is None or evidence_score >= 0.6
            overall_pass = rec_ok and ev_ok

        # Log successful run
        log_run(
            jd_raw=jd_raw,
            resume_raw=resume_raw,
            scorecard=scorecard,
            latency=latency,
            error=None,
        )

    except ParseError as exc:
        latency = time.monotonic() - t0
        actual_outcome = "parse_error"
        error_msg = str(exc)

        if expected_outcome == "parse_error":
            rec_result = "pass" if (expected_error and expected_error.lower() in exc.reason.lower()) else "fail"
            evidence_score = 1.0 if rec_result == "pass" else 0.0
            overall_pass = rec_result == "pass"
        else:
            rec_result = "fail"
            overall_pass = False

        log_run(
            jd_raw="",
            resume_raw="",
            scorecard=None,
            latency=latency,
            error=str(exc),
        )

    except Exception as exc:
        latency = time.monotonic() - t0
        err_str = str(exc)
        err_type = type(exc).__name__

        # Classify error type for accurate reporting
        is_timeout = (
            err_type in ("APITimeoutError", "TimeoutError")
            or "timeout" in err_str.lower()
        )
        actual_outcome = "timeout_error" if is_timeout else "error"
        error_msg = err_str
        rec_result = "fail"
        overall_pass = False

        log_run(
            jd_raw="",
            resume_raw="",
            scorecard=None,
            latency=latency,
            error=err_str,
        )

    return TestResult(
        case_id=case_id,
        category=category,
        description=description,
        expected_outcome=expected_outcome,
        actual_outcome=actual_outcome or "error",
        recommendation_result=rec_result,
        evidence_score=evidence_score,
        overall_pass=overall_pass,
        error=error_msg,
        latency_seconds=round(latency, 2),
        criterion_scores=criterion_scores,
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def compute_metrics(results: list[TestResult]) -> BatchMetrics:
    """Compute aggregate metrics from test results."""
    total = len(results)
    exact_matches = sum(1 for r in results if r.recommendation_result == "pass")
    partial_matches = sum(1 for r in results if r.recommendation_result == "partial")
    failures = sum(1 for r in results if r.recommendation_result == "fail")
    passes = sum(1 for r in results if r.overall_pass)

    accuracy = exact_matches / total if total > 0 else 0.0
    partial_rate = partial_matches / total if total > 0 else 0.0
    fail_rate = failures / total if total > 0 else 0.0

    # Primary accuracy: advance + reject cases only
    primary_cases = [r for r in results if r.expected_outcome in ("advance", "reject")]
    primary_total = len(primary_cases)
    primary_exact = sum(1 for r in primary_cases if r.recommendation_result == "pass")
    primary_accuracy = primary_exact / primary_total if primary_total > 0 else 0.0

    # Evidence average (exclude None and parse_error cases)
    evidence_scores = [r.evidence_score for r in results if r.evidence_score is not None]
    evidence_avg = sum(evidence_scores) / len(evidence_scores) if evidence_scores else None

    # Parse error correctness
    parse_error_cases = [r for r in results if r.expected_outcome == "parse_error"]
    parse_error_total = len(parse_error_cases)
    parse_error_correct = sum(1 for r in parse_error_cases if r.actual_outcome == "parse_error" and r.overall_pass)

    # Timeout error tracking (distinct from parse_error)
    timeout_cases = [r for r in results if r.actual_outcome == "timeout_error"]
    timeout_total = len(timeout_cases)

    # By category
    by_category: dict[str, dict[str, int]] = {}
    for r in results:
        cat = r.category
        if cat not in by_category:
            by_category[cat] = {"total": 0, "pass": 0, "partial": 0, "fail": 0}
        by_category[cat]["total"] += 1
        by_category[cat][r.recommendation_result] += 1

    return BatchMetrics(
        total=total,
        exact_matches=exact_matches,
        partial_matches=partial_matches,
        failures=failures,
        accuracy=round(accuracy, 4),
        partial_rate=round(partial_rate, 4),
        fail_rate=round(fail_rate, 4),
        primary_accuracy=round(primary_accuracy, 4),
        primary_total=primary_total,
        primary_exact=primary_exact,
        evidence_avg=round(evidence_avg, 4) if evidence_avg is not None else None,
        parse_error_correct=parse_error_correct,
        parse_error_total=parse_error_total,
        timeout_total=timeout_total,
        by_category=by_category,
    )


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def print_results(results: list[TestResult], metrics: BatchMetrics) -> None:
    """Print human-readable eval results to stdout."""

    # Header
    print("=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print()

    # Per-case table
    print(f"{'ID':<8} {'Expected':<12} {'Actual':<12} {'Result':<10} {'Evidence':<10} {'Pass':<6}")
    print("-" * 70)
    for r in results:
        ev_str = f"{r.evidence_score:.0%}" if r.evidence_score is not None else "  —  "
        pass_str = "YES" if r.overall_pass else "no"
        print(
            f"{r.case_id:<8} {r.expected_outcome:<12} {r.actual_outcome:<12} "
            f"{r.recommendation_result:<10} {ev_str:<10} {pass_str:<6}"
        )

    print()
    print("-" * 70)
    print("BATCH METRICS")
    print("-" * 70)
    print(f"  Total cases:        {metrics.total}")
    print(f"  Exact matches:      {metrics.exact_matches}")
    print(f"  Partial matches:    {metrics.partial_matches}")
    print(f"  Failures:           {metrics.failures}")
    print(f"  Accuracy:           {metrics.accuracy:.1%}")
    print(f"  Partial rate:       {metrics.partial_rate:.1%}")
    print(f"  Fail rate:          {metrics.fail_rate:.1%}")
    print()
    print(f"  Primary accuracy (advance+reject only):")
    print(f"    Scope:            {metrics.primary_total} cases")
    print(f"    Exact matches:    {metrics.primary_exact}")
    print(f"    Accuracy:         {metrics.primary_accuracy:.1%}")
    print(f"    Target:           >= 80%")
    target_met = "YES" if metrics.primary_accuracy >= 0.80 else "no"
    print(f"    Target met:       {target_met}")
    print()
    if metrics.evidence_avg is not None:
        print(f"  Avg evidence score: {metrics.evidence_avg:.1%}")
    print(f"  Parse errors correct: {metrics.parse_error_correct}/{metrics.parse_error_total}")
    print()

    # By category
    print("-" * 70)
    print("BY CATEGORY")
    print("-" * 70)
    for cat, counts in metrics.by_category.items():
        print(f"  {cat}: {counts['total']} cases — "
              f"pass={counts['pass']}, partial={counts['partial']}, fail={counts['fail']}")
    print()

    # Overall verdict
    overall_pass_rate = sum(1 for r in results if r.overall_pass) / len(results) if results else 0
    print(f"  Overall pass rate:  {overall_pass_rate:.1%}")
    print("=" * 70)


def save_results(results: list[TestResult], metrics: BatchMetrics, path: Path) -> None:
    """Save results to a JSON file."""
    data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": [asdict(r) for r in results],
        "metrics": asdict(metrics),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\nResults saved to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_test_cases(path: Path) -> list[dict[str, Any]]:
    """Load test cases from JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["test_cases"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run eval harness")
    parser.add_argument("--case", type=str, help="Run a single test case by ID (e.g. TC-01)")
    parser.add_argument("--limit", type=int, help="Run first N test cases")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N test cases (for batching)")
    parser.add_argument("--output", type=str, help="Save results to JSON file")
    parser.add_argument("--cases", type=str, help="Path to test_cases.json (default: eval/test_cases.json)")
    parser.add_argument("--delay", type=float, default=EVAL_INTER_CASE_DELAY, help="Seconds to wait between cases (default: from config)")
    parser.add_argument("--call-delay", type=float, default=EVAL_INTER_CALL_DELAY, help="Seconds to wait between LLM calls within a case (default: from config)")
    args = parser.parse_args()

    cases_path = Path(args.cases) if args.cases else TEST_CASES_PATH
    all_cases = load_test_cases(cases_path)

    # Filter
    if args.case:
        cases = [c for c in all_cases if c["id"] == args.case]
        if not cases:
            print(f"Test case '{args.case}' not found.")
            sys.exit(1)
    elif args.limit:
        cases = all_cases[args.offset : args.offset + args.limit]
    else:
        cases = all_cases[args.offset :]

    print(f"Running {len(cases)} test case(s) from {cases_path.name}")
    print()

    set_model_version("qwen/qwen3.8-27b")

    results: list[TestResult] = []
    for i, case in enumerate(cases):
        print(f"[{i + 1}/{len(cases)}] {case['id']}: {case['description'][:60]}...")
        if i > 0:
            time.sleep(args.delay)
        try:
            result = run_test_case(case, "qwen/qwen3.8-27b")
        except Exception as exc:
            print(f"  FATAL: {exc}")
            result = TestResult(
                case_id=case["id"],
                category=case["category"],
                description=case["description"],
                expected_outcome=case["expected_outcome"],
                actual_outcome="error",
                recommendation_result="fail",
                evidence_score=0.0,
                overall_pass=False,
                error=str(exc),
            )
        status = "PASS" if result.overall_pass else "FAIL"
        print(f"  -> {result.actual_outcome} | {result.recommendation_result} | {status}")
        if result.error:
            print(f"  ERROR: {result.error[:120]}")
        results.append(result)

    metrics = compute_metrics(results)
    print_results(results, metrics)

    output_path = (REPO_ROOT / args.output) if args.output else RESULTS_PATH
    save_results(results, metrics, output_path)
    print(f"\nSaved {len(results)} results to {output_path}")


if __name__ == "__main__":
    main()
