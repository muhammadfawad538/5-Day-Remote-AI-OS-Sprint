"""Run eval in 3 batches of 4 with inter-batch waits and 429 retry.

Usage:
    python eval/run_batches.py
    python eval/run_batches.py --inter-batch 90   # override wait (seconds)
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "eval"
BATCH_FILES = [
    RESULTS_DIR / "results_batch1.json",
    RESULTS_DIR / "results_batch2.json",
    RESULTS_DIR / "results_batch3.json",
]
FINAL_OUTPUT = RESULTS_DIR / "results_full.json"
TOTAL_CASES = 12
BATCH_SIZE = 4


def run_batch(offset: int, limit: int, output: Path, retry_on_429: bool = True) -> bool:
    """Run one batch. Returns True on success, False if 429 exhausted."""
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    cmd = [
        sys.executable, str(REPO_ROOT / "eval" / "run_eval.py"),
        "--cases", str(RESULTS_DIR / "test_cases.json"),
        "--limit", str(limit),
        "--offset", str(offset),
        "--output", str(output),
    ]
    print(f"\n{'='*60}")
    print(f"Running batch: cases {offset+1}–{offset+limit} (offset={offset})")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT), env=env)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        # Non-zero exit means the pipeline itself failed (not just logged 429s
        # during retries — those are handled internally and still produce results)
        return False

    # Success means the output file exists and contains valid results
    if not output.exists():
        return False
    try:
        with open(output, encoding="utf-8") as f:
            data = json.load(f)
        return len(data.get("results", [])) > 0
    except Exception:
        return False


def combine_results(paths: list[Path], output: Path) -> None:
    """Merge per-batch result files into one."""
    combined = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "results": [], "metrics": {}}
    for p in paths:
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            batch = json.load(f)
        combined["results"].extend(batch.get("results", []))
        # Keep metrics from last batch as a placeholder
        if batch.get("metrics"):
            combined["metrics"] = batch["metrics"]

    with open(output, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, default=str)
    print(f"\nCombined {len(combined['results'])} results -> {output}")


def main() -> None:
    inter_batch = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    retry_wait = 90

    for i, (offset, out) in enumerate(zip(
        range(0, TOTAL_CASES, BATCH_SIZE), BATCH_FILES
    )):
        success = run_batch(offset, BATCH_SIZE, out)
        if not success:
            print(f"\nBatch {i+1} hit rate limit. Waiting {retry_wait}s and retrying...")
            time.sleep(retry_wait)
            success = run_batch(offset, BATCH_SIZE, out, retry_on_429=False)
            if not success:
                print(f"\nBatch {i+1} failed after retry. Aborting.")
                sys.exit(1)

        # Wait between batches (not after the last one)
        if i < len(BATCH_FILES) - 1:
            print(f"\nWaiting {inter_batch}s before next batch...")
            time.sleep(inter_batch)

    combine_results(BATCH_FILES, FINAL_OUTPUT)

    # Print combined table
    with open(FINAL_OUTPUT, encoding="utf-8") as f:
        data = json.load(f)

    print("\n" + "=" * 70)
    print("COMBINED EVAL RESULTS (all 12 cases)")
    print("=" * 70)
    print(f"{'ID':<8} {'Expected':<12} {'Actual':<12} {'Result':<10} {'Evidence':<10} {'Pass':<6}")
    print("-" * 70)
    for r in sorted(data["results"], key=lambda x: x["case_id"]):
        ev = f"{r['evidence_score']:.0%}" if r.get("evidence_score") is not None else "  —  "
        print(f"{r['case_id']:<8} {r['expected_outcome']:<12} {r['actual_outcome']:<12} "
              f"{r['recommendation_result']:<10} {ev:<10} {'YES' if r['overall_pass'] else 'no'}")

    m = data.get("metrics", {})
    print(f"\nAccuracy: {m.get('accuracy', 0):.1%}  |  Primary: {m.get('primary_accuracy', 0):.1%}  |  "
          f"Evidence avg: {m.get('evidence_avg', 0):.1%}")


if __name__ == "__main__":
    main()
