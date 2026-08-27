"""Tests for test coverage reporting and quality gates."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from scripts.check_coverage import (
    check_coverage_gates,
    DEFAULT_TOTAL_THRESHOLD,
    DEFAULT_BRANCH_THRESHOLD,
    CRITICAL_MODULES_THRESHOLDS,
)


def test_coverage_gate_passes_when_above_threshold():
    sample_coverage = {
        "totals": {
            "percent_covered": 88.5,
            "covered_branches": 80,
            "num_branches": 100,
        },
        "files": {
            "database_connection.py": {
                "summary": {"percent_covered": 92.0}
            },
            "database_integrity.py": {
                "summary": {"percent_covered": 89.0}
            },
        },
    }

    passed, violations = check_coverage_gates(
        sample_coverage,
        total_threshold=80.0,
        branch_threshold=70.0,
    )
    assert passed is True
    assert len(violations) == 0


def test_coverage_gate_fails_when_total_coverage_below_threshold():
    sample_coverage = {
        "totals": {
            "percent_covered": 65.0,
            "covered_branches": 60,
            "num_branches": 100,
        },
        "files": {},
    }

    passed, violations = check_coverage_gates(
        sample_coverage,
        total_threshold=80.0,
    )
    assert passed is False
    assert any("Total coverage 65.00%" in v for v in violations)


def test_coverage_gate_fails_when_branch_coverage_below_threshold():
    sample_coverage = {
        "totals": {
            "percent_covered": 85.0,
            "covered_branches": 50,
            "num_branches": 100,
        },
        "files": {},
    }

    passed, violations = check_coverage_gates(
        sample_coverage,
        total_threshold=80.0,
        branch_threshold=70.0,
    )
    assert passed is False
    assert any("Branch coverage 50.00%" in v for v in violations)


def test_coverage_gate_fails_when_critical_module_below_threshold():
    sample_coverage = {
        "totals": {
            "percent_covered": 85.0,
            "covered_branches": 80,
            "num_branches": 100,
        },
        "files": {
            "database_connection.py": {
                "summary": {"percent_covered": 72.0}
            }
        },
    }

    passed, violations = check_coverage_gates(
        sample_coverage,
        total_threshold=80.0,
        module_thresholds={"database_connection": 85.0},
    )
    assert passed is False
    assert any("Critical module 'database_connection' coverage 72.00%" in v for v in violations)
