"""
EcoBuddy AI – Benchmark Regression Comparator
Usage: python3 -m benchmarks.compare_benchmarks <current_report.json> <baseline_report.json> [--threshold 20]
Exits with code 1 if any benchmark's mean_ms regressed beyond the threshold (%).
"""
import argparse
import json
import os
import sys


def load_benchmarks(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        lookup = {}
        for suite in data.get("suites", []):
            for b in suite.get("benchmarks", []):
                lookup[f"{suite['suite']}::{b['name']}"] = b.get("mean_ms", 0)
        return lookup
    except Exception as e:
        print(f"Error loading benchmark report '{path}': {e}")
        return None


def main(argv=None):
    p = argparse.ArgumentParser(description="Compare benchmark runs for regressions")
    p.add_argument("current", help="Path to current benchmark_report.json")
    p.add_argument("baseline", help="Path to baseline benchmark_report.json")
    p.add_argument("--threshold", type=float, default=20.0, help="Allowed regression percent")
    args = p.parse_args(argv)

    current = load_benchmarks(args.current)
    if current is None:
        print(f"Error: Current benchmark report file '{args.current}' not found or invalid.")
        return 1

    baseline = load_benchmarks(args.baseline)
    if baseline is None:
        print(f"Warning: Baseline report file '{args.baseline}' not found. Skipping baseline regression check.")
        return 0

    regressions = []
    for name, base_ms in baseline.items():
        if name not in current or base_ms <= 0:
            continue
        curr_ms = current[name]
        pct_change = ((curr_ms - base_ms) / base_ms) * 100
        status = "REGRESSION" if pct_change > args.threshold else "OK"
        print(f"[{status}] {name}: {base_ms:.2f}ms -> {curr_ms:.2f}ms ({pct_change:+.1f}%)")
        if pct_change > args.threshold:
            regressions.append((name, pct_change))

    if regressions:
        print(f"\n{len(regressions)} benchmark(s) regressed beyond {args.threshold}% threshold.")
        return 1

    print("\nNo performance regressions detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())