"""
Unit tests for Avoided Emissions Tracker and Remote Work Calculator.
"""

import pytest
from avoided_emissions_tracker import AvoidedEmissionsTracker
from remote_work_calculator import RemoteWorkCalculator


def test_tracker_log_activity():
    tracker = AvoidedEmissionsTracker()
    record = tracker.log_avoided_activity(
        activity_type="test_activity",
        quantity=10,
        baseline_factor=5.0,
        alternative_factor=2.0,
    )

    assert record["baseline_kg"] == 50.0
    assert record["alternative_kg"] == 20.0
    assert record["avoided_kg"] == 30.0
    assert tracker.total_avoided_kg == 30.0


def test_tracker_summary():
    tracker = AvoidedEmissionsTracker()
    tracker.log_avoided_activity("type_a", 10, 5.0, 2.0)  # 30 avoided
    tracker.log_avoided_activity("type_a", 5, 5.0, 2.0)  # 15 avoided
    tracker.log_avoided_activity("type_b", 10, 4.0, 1.0)  # 30 avoided

    summary = tracker.get_summary()
    assert summary["total_avoided_kg"] == 75.0
    assert summary["breakdown_by_type"]["type_a"] == 45.0
    assert summary["breakdown_by_type"]["type_b"] == 30.0
    assert summary["activity_count"] == 3


def test_remote_work_calculator_ice_car():
    calculator = RemoteWorkCalculator()
    result = calculator.calculate_remote_work_savings(
        days_per_week=3,
        weeks_per_year=48,
        commute_distance_km=20,
        vehicle_type="ice_car",
    )

    # Baseline per day: (40km * 0.192) + 15 = 7.68 + 15 = 22.68
    # Alternative per day: 4.0
    # Avoided per day: 18.68
    # Total days: 144
    # Total avoided: 144 * 18.68 = 2689.92

    assert result["days_per_year"] == 144
    assert result["baseline_per_day_kg"] == 22.68
    assert result["alternative_per_day_kg"] == 4.0
    assert abs(result["annual_avoided_kg"] - 2689.92) < 0.1


def test_remote_work_calculator_ev():
    calculator = RemoteWorkCalculator()
    result = calculator.calculate_remote_work_savings(
        days_per_week=3, weeks_per_year=48, commute_distance_km=20, vehicle_type="ev"
    )

    # Baseline per day: (40km * 0.053) + 15 = 2.12 + 15 = 17.12
    # Avoided per day: 17.12 - 4.0 = 13.12
    # Total avoided: 144 * 13.12 = 1889.28

    assert abs(result["annual_avoided_kg"] - 1889.28) < 0.1
