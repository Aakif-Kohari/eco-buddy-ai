"""Test coverage quality gate enforcer.

Validates that test coverage meets or exceeds defined threshold gates
for total coverage, statement coverage, branch coverage, and critical modules.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


DEFAULT_TOTAL_THRESHOLD = 1.5
DEFAULT_BRANCH_THRESHOLD = 1.0

CRITICAL_MODULES_THRESHOLDS: Dict[str, float] = {
    "database_connection": 80.0,
    "database_integrity": 80.0,
    "invalidation": 80.0,
}


def run_coverage_analysis() -> Dict[str, Any]:
    """Execute pytest with coverage and return the parsed JSON report."""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "pytest",
            "tests/test_database_integrity.py",
            "tests/test_database_connection.py",
            "-q",
        ],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "coverage", "json", "-o", "coverage.json"],
        check=True,
    )
    with open("coverage.json", "r", encoding="utf-8") as f:
        return json.load(f)


def check_coverage_gates(
    coverage_data: Dict[str, Any],
    total_threshold: float = DEFAULT_TOTAL_THRESHOLD,
    branch_threshold: float = DEFAULT_BRANCH_THRESHOLD,
    module_thresholds: Dict[str, float] = None,
) -> tuple[bool, list[str]]:
    """Verify coverage against quality gate thresholds.

    Returns:
        tuple[bool, list[str]]: (passed, list of violation messages)
    """
    if module_thresholds is None:
        module_thresholds = CRITICAL_MODULES_THRESHOLDS

    violations = []
    totals = coverage_data.get("totals", {})

    total_percent = totals.get("percent_covered", 0.0)
    if total_percent < total_threshold:
        violations.append(
            f"Total coverage {total_percent:.2f}% is below quality gate threshold of {total_threshold:.2f}%"
        )

    # Check branch coverage if available
    covered_branches = totals.get("covered_branches", 0)
    num_branches = totals.get("num_branches", 0)
    if num_branches > 0:
        branch_percent = (covered_branches / num_branches) * 100.0
        if branch_percent < branch_threshold:
            violations.append(
                f"Branch coverage {branch_percent:.2f}% is below quality gate threshold of {branch_threshold:.2f}%"
            )

    # Check critical modules
    files = coverage_data.get("files", {})
    for file_path, file_data in files.items():
        stem = Path(file_path).stem
        if stem in module_thresholds:
            req_thresh = module_thresholds[stem]
            module_cov = file_data.get("summary", {}).get("percent_covered", 0.0)
            if module_cov < req_thresh:
                violations.append(
                    f"Critical module '{stem}' coverage {module_cov:.2f}% is below threshold of {req_thresh:.2f}%"
                )

    return len(violations) == 0, violations


def main() -> int:
    """CLI entry point for coverage quality gate check."""
    coverage_json = Path("coverage.json")
    if not coverage_json.exists():
        print("coverage.json not found. Running coverage analysis...")
        coverage_data = run_coverage_analysis()
    else:
        with open(coverage_json, "r", encoding="utf-8") as f:
            coverage_data = json.load(f)

    passed, violations = check_coverage_gates(coverage_data)
    if not passed:
        print("Coverage Quality Gate FAILED:")
        for violation in violations:
            print(f"  - {violation}")
        return 1

    totals = coverage_data.get("totals", {})
    print(f"Coverage Quality Gate PASSED! Total coverage: {totals.get('percent_covered', 0):.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
