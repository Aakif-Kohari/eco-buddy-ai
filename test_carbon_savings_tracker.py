"""
Tests for the Carbon Savings Tracker Engine
"""

import pytest

from src.utils.carbon_savings_tracker import (
    calculate_baseline_footprint, compute_savings_history, compute_streak,
    check_milestones, next_milestone, compute_savings_equivalents,
    compute_monthly_savings_rate, generate_savings_report,
    MILESTONES, STREAK_THRESHOLDS,
)

SAMPLE_ASSESSMENTS = [
    {"date": "2024-01-15", "footprint": 5000.0},
    {"date": "2024-02-15", "footprint": 4700.0},
    {"date": "2024-03-15", "footprint": 4400.0},
    {"date": "2024-04-15", "footprint": 4200.0},
    {"date": "2024-05-15", "footprint": 3900.0},
    {"date": "2024-06-15", "footprint": 3600.0},
]


# ── calculate_baseline_footprint Tests ───────────────────────────────────────

class TestCalculateBaselineFootprint:
    def test_car_vegetarian(self):
        fp = calculate_baseline_footprint("Car", 10.0, 200.0, "Vegetarian", 0)
        # Transport: 0.19 * 10 * 365 = 693.5
        # Electricity: 200 * 0.82 * 12 = 1968.0
        # Diet: 950
        # Flights: 0
        expected = round(693.5 + 1968.0 + 950.0, 2)
        assert abs(fp - expected) < 0.1

    def test_bike_vegetarian_zero_transport(self):
        fp = calculate_baseline_footprint("Bike", 20.0, 100.0, "Vegetarian", 0)
        assert fp == round(0 + 100 * 0.82 * 12 + 950, 2)

    def test_flights_add_to_total(self):
        fp0 = calculate_baseline_footprint("Walking", 5.0, 150.0, "Vegan", 0)
        fp2 = calculate_baseline_footprint("Walking", 5.0, 150.0, "Vegan", 2)
        assert fp2 > fp0

    def test_non_vegetarian_higher_than_vegetarian(self):
        fp_nv = calculate_baseline_footprint("Car", 10.0, 200.0, "Non-Vegetarian", 1)
        fp_v = calculate_baseline_footprint("Car", 10.0, 200.0, "Vegetarian", 1)
        assert fp_nv > fp_v

    def test_zero_distance(self):
        fp = calculate_baseline_footprint("Car", 0.0, 0.0, "Vegetarian", 0)
        assert fp == 950.0  # Only diet

    def test_returns_float(self):
        fp = calculate_baseline_footprint("Car", 10.0, 200.0, "Vegetarian", 1)
        assert isinstance(fp, float)


# ── compute_savings_history Tests ────────────────────────────────────────────

class TestComputeSavingsHistory:
    def test_empty_assessments(self):
        assert compute_savings_history([]) == []

    def test_returns_correct_count(self):
        records = compute_savings_history(SAMPLE_ASSESSMENTS)
        assert len(records) == len(SAMPLE_ASSESSMENTS)

    def test_baseline_auto_detected(self):
        records = compute_savings_history(SAMPLE_ASSESSMENTS)
        assert records[0]["baseline_kg"] == 5000.0  # First assessment footprint

    def test_baseline_manual(self):
        records = compute_savings_history(SAMPLE_ASSESSMENTS, baseline_kg=6000.0)
        assert records[0]["baseline_kg"] == 6000.0
        assert records[0]["savings_kg"] == 1000.0  # 6000 - 5000

    def test_cumulative_increases(self):
        records = compute_savings_history(SAMPLE_ASSESSMENTS)
        cumulatives = [r["cumulative_savings_kg"] for r in records]
        # Each should be >= previous (since footprints are decreasing)
        for i in range(1, len(cumulatives)):
            assert cumulatives[i] >= cumulatives[i - 1]

    def test_sorted_by_date(self):
        records = compute_savings_history(SAMPLE_ASSESSMENTS)
        dates = [r["date"] for r in records]
        assert dates == sorted(dates)

    def test_first_record_savings(self):
        records = compute_savings_history(SAMPLE_ASSESSMENTS)
        assert records[0]["savings_kg"] == 0.0  # Baseline = first footprint

    def test_final_cumulative(self):
        records = compute_savings_history(SAMPLE_ASSESSMENTS)
        expected = 5000.0 - 3600.0  # baseline - last
        assert abs(records[-1]["cumulative_savings_kg"] - expected) < 0.1


# ── compute_streak Tests ─────────────────────────────────────────────────────

class TestComputeStreak:
    def test_all_positive_savings(self):
        records = compute_savings_history(SAMPLE_ASSESSMENTS)
        streak = compute_streak(records)
        assert streak["current_streak_months"] == len(SAMPLE_ASSESSMENTS) - 1

    def test_broken_streak(self):
        assessments = [
            {"date": "2024-01", "footprint": 3000.0},
            {"date": "2024-02", "footprint": 4000.0},  # above baseline
            {"date": "2024-03", "footprint": 2500.0},
        ]
        records = compute_savings_history(assessments)
        streak = compute_streak(records)
        assert streak["current_streak_months"] == 1  # Only the last one

    def test_empty_records(self):
        assert compute_streak([])["current_streak_months"] == 0

    def test_single_record(self):
        records = compute_savings_history([{"date": "2024-01", "footprint": 4000.0}])
        streak = compute_streak(records)
        assert streak["current_streak_months"] == 0  # No savings (baseline = footprint)

    def test_tier_assignment(self):
        records = [{"date": f"2024-0{i}", "footprint": 3000.0, "baseline_kg": 5000.0,
                    "savings_kg": 2000.0, "cumulative_savings_kg": 2000.0 * i}
                   for i in range(1, 5)]
        streak = compute_streak(records)
        assert streak["streak_tier"] != "none"

    def test_longest_vs_current(self):
        assessments = [
            {"date": "2024-01", "footprint": 3000.0},
            {"date": "2024-02", "footprint": 4000.0},  # break
            {"date": "2024-03", "footprint": 2500.0},
            {"date": "2024-04", "footprint": 2400.0},
        ]
        records = compute_savings_history(assessments)
        streak = compute_streak(records)
        assert streak["longest_streak_months"] >= streak["current_streak_months"]


# ── check_milestones Tests ───────────────────────────────────────────────────

class TestCheckMilestones:
    def test_no_milestones(self):
        assert check_milestones(50.0) == []

    def test_all_milestones(self):
        achieved = check_milestones(50000.0)
        assert len(achieved) == len(MILESTONES)

    def test_first_milestone(self):
        achieved = check_milestones(100.0)
        assert len(achieved) >= 1
        assert achieved[0]["badge"] == "🌱 Seedling Saver"

    def test_exactly_at_threshold(self):
        achieved = check_milestones(500.0)
        badges = [m["badge"] for m in achieved]
        assert "🌿 Green Guardian" in badges

    def test_result_structure(self):
        achieved = check_milestones(1000.0)
        for m in achieved:
            assert "badge" in m and "message" in m and "kg_threshold" in m


# ── next_milestone Tests ─────────────────────────────────────────────────────

class TestNextMilestone:
    def test_returns_next_unreached(self):
        result = next_milestone(200.0)
        assert result is not None
        assert result["threshold_kg"] > 200.0

    def test_returns_none_when_all_reached(self):
        assert next_milestone(100000.0) is None

    def test_progress_pct(self):
        result = next_milestone(250.0)
        assert result["progress_pct"] == 25.0  # 250/1000

    def test_remaining_kg(self):
        result = next_milestone(800.0)
        assert result["remaining_kg"] == 200.0  # 1000 - 800

    def test_zero_savings(self):
        result = next_milestone(0.0)
        assert result["threshold_kg"] == 100.0


# ── compute_savings_equivalents Tests ────────────────────────────────────────

class TestComputeSavingsEquivalents:
    def test_returns_all_equivalents(self):
        eqs = compute_savings_equivalents(1000.0)
        assert len(eqs) == 5

    def test_values_positive(self):
        eqs = compute_savings_equivalents(1000.0)
        for eq in eqs:
            assert eq["value"] >= 0

    def test_result_structure(self):
        eqs = compute_savings_equivalents(500.0)
        for eq in eqs:
            assert {"label", "value", "unit", "icon"}.issubset(eq.keys())

    def test_zero_savings(self):
        eqs = compute_savings_equivalents(0.0)
        assert all(eq["value"] == 0 for eq in eqs)


# ── compute_monthly_savings_rate Tests ───────────────────────────────────────

class TestComputeMonthlySavingsRate:
    def test_empty_records(self):
        result = compute_monthly_savings_rate([])
        assert result["trend"] == "insufficient_data"

    def test_positive_rate(self):
        records = compute_savings_history(SAMPLE_ASSESSMENTS)
        result = compute_monthly_savings_rate(records)
        assert result["avg_monthly_savings_kg"] > 0

    def test_projection(self):
        records = compute_savings_history(SAMPLE_ASSESSMENTS)
        result = compute_monthly_savings_rate(records)
        assert result["projection_12m_kg"] == result["avg_monthly_savings_kg"] * 12

    def test_trend_detection(self):
        # Improving trend
        records = compute_savings_history([
            {"date": f"2024-0{i}", "footprint": 5000.0 - i * 300} for i in range(1, 7)
        ])
        result = compute_monthly_savings_rate(records)
        assert result["trend"] in ("improving", "stable", "declining")

    def test_single_record(self):
        result = compute_monthly_savings_rate([{"date": "2024-01", "footprint": 4000.0, "savings_kg": 0}])
        assert result["total_months"] == 1


# ── generate_savings_report Tests ────────────────────────────────────────────

class TestGenerateSavingsReport:
    def test_all_keys_present(self):
        report = generate_savings_report(SAMPLE_ASSESSMENTS)
        expected = {"records", "baseline_kg", "current_footprint_kg", "total_savings_kg",
                    "savings_pct", "streak", "milestones_achieved", "next_milestone",
                    "equivalents", "monthly_rate", "region", "generated_at"}
        assert expected.issubset(report.keys())

    def test_total_savings(self):
        report = generate_savings_report(SAMPLE_ASSESSMENTS)
        assert report["total_savings_kg"] == 5000.0 - 3600.0

    def test_savings_pct(self):
        report = generate_savings_report(SAMPLE_ASSESSMENTS)
        expected_pct = (5000.0 - 3600.0) / 5000.0 * 100
        assert abs(report["savings_pct"] - expected_pct) < 0.1

    def test_with_custom_baseline(self):
        report = generate_savings_report(SAMPLE_ASSESSMENTS, baseline_kg=6000.0)
        assert report["baseline_kg"] == 6000.0
        assert report["total_savings_kg"] == 6000.0 - 3600.0

    def test_empty_assessments(self):
        report = generate_savings_report([])
        assert "summary" in report

    def test_records_match_input(self):
        report = generate_savings_report(SAMPLE_ASSESSMENTS)
        assert len(report["records"]) == len(SAMPLE_ASSESSMENTS)


# ── Edge Cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_all_same_footprint(self):
        same = [{"date": f"2024-0{i}", "footprint": 4000.0} for i in range(1, 7)]
        report = generate_savings_report(same)
        assert report["total_savings_kg"] == 0.0
        assert report["savings_pct"] == 0.0

    def test_single_assessment(self):
        report = generate_savings_report([{"date": "2024-01", "footprint": 3000.0}])
        assert report["total_savings_kg"] == 0.0

    def test_very_large_savings(self):
        assessments = [{"date": "2024-01", "footprint": 50000.0},
                       {"date": "2024-06", "footprint": 1000.0}]
        report = generate_savings_report(assessments)
        assert report["total_savings_kg"] == 49000.0

    def test_baseline_zero(self):
        report = generate_savings_report([{"date": "2024-01", "footprint": 0.0}])
        assert report["total_savings_kg"] == 0.0
        assert report["savings_pct"] == 0.0

    def test_milestones_with_high_savings(self):
        report = generate_savings_report([
            {"date": "2024-01", "footprint": 20000.0},
            {"date": "2024-06", "footprint": 5000.0},
        ])
        assert len(report["milestones_achieved"]) > 0

    def test_next_milestone_at_exact_threshold(self):
        assert next_milestone(100.0)["threshold_kg"] == 500.0
        assert next_milestone(500.0)["threshold_kg"] == 1000.0
