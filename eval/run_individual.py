"""Run all 12 eval cases one at a time with 90s gaps, in-process."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.run_eval import load_test_cases, run_test_case, save_results, compute_metrics, print_results

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "eval"
CASES_PATH = RESULTS_DIR / "test_cases.json"
FULL_OUTPUT = RESULTS_DIR / "results_full.json"
GAP = 90

CASES = load_test_cases(CASES_PATH)


def main() -> None:
    all_results = []
    for i, case in enumerate(CASES):
        if i > 0:
            print(f"\nWaiting {GAP}s before next case...")
            time.sleep(GAP)
        print(f"\n[{i+1}/12] {case['id']}: {case['description'][:60]}...")
        try:
            r = run_test_case(case, "qwen/qwen3.8-27b")
            all_results.append(r)
            ev = f"{r.evidence_score:.0%}" if r.evidence_score is not None else "  -  "
            print(f"  -> {r.actual_outcome} | {r.recommendation_result} | ev={ev} | pass={r.overall_pass}")
            if r.error:
                print(f"     ERROR: {r.error[:120]}")
        except Exception as exc:
            print(f"  FATAL: {exc}")

    metrics = compute_metrics(all_results)
    print_results(all_results, metrics)
    save_results(all_results, metrics, FULL_OUTPUT)
    print(f"\nSaved {len(all_results)} results to {FULL_OUTPUT}")


if __name__ == "__main__":
    main()
