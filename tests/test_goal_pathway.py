"""Tests for the Sustainability Goal Progress and Reduction Pathway Analyzer."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.utils.goal_pathway import (
    STATUS_ACHIEVED,
    STATUS_AHEAD,
    STATUS_AT_RISK,
    STATUS_INSUFFICIENT_DATA,
    STATUS_OFF_TRACK,
    STATUS_ON_TRACK,
    GoalPathwayValidationError,
    PathwayConfig,
    analyze_goal_pathway,
    best_improvement,
    build_chart_rows,
    build_projection,
    build_snapshots,
    calculate_category_progress,
    calculate_progress,
    classify_goal_status,
    compare_periods,
    deserialize_pathway,
    detect_significant_progress_change,
    expected_footprint_at,
    generate_milestones,
    generate_pathway,
    human_status_message,
    largest_regression,
    latest_assessment,
    normalize_assessments,
    normalize_goal,
    observed_reduction_pace,
    pathway_id,
    project_final_footprint,
    project_target_date,
    rank_categories,
    reduction_percent,
    required_monthly_reduction,
    serialize_pathway,
    target_date_at_current_pace,
    total_required_reduction,
    validate_pathway_config,
    VALID_STATUSES,
)


def goal():
    return {
        "id": 7,
        "user_id": 11,
        "baseline_kg": 5000,
        "target_kg": 3500,
        "start_date": date(2026, 1, 1),
        "target_date": date(2027, 1, 1),
        "status": "active",
    }


def assessments():
    return [
        {"id": 1, "date": "2026-01-01", "footprint": 5000, "categories": {"Transportation": 2000, "Electricity": 1500, "Diet": 1000, "Flights": 500}},
        {"id": 2, "date": "2026-04-01", "footprint": 4600, "categories": {"Transportation": 1750, "Electricity": 1400, "Diet": 950, "Flights": 500}},
        {"id": 3, "date": "2026-07-01", "footprint": 4200, "categories": {"Transportation": 1500, "Electricity": 1300, "Diet": 900, "Flights": 500}},
    ]


def test_normalize_goal():
    result = normalize_goal(goal())
    assert result["baseline_kg"] == 5000
    assert result["target_kg"] == 3500
    assert result["start_date"] == date(2026, 1, 1)


def test_normalize_goal_rejects_non_reduction():
    bad = goal()
    bad["target_kg"] = 5000
    with pytest.raises(GoalPathwayValidationError):
        normalize_goal(bad)


def test_normalize_goal_rejects_invalid_dates():
    bad = goal()
    bad["target_date"] = bad["start_date"]
    with pytest.raises(GoalPathwayValidationError):
        normalize_goal(bad)


def test_total_required_reduction():
    assert total_required_reduction(goal()) == 1500


def test_reduction_percent():
    assert reduction_percent(goal()) == 30


def test_required_monthly_reduction():
    value = required_monthly_reduction(goal())
    assert 120 < value < 130


def test_expected_pathway_before_start():
    assert expected_footprint_at(goal(), date(2025, 12, 1)) == 5000


def test_expected_pathway_at_target():
    assert expected_footprint_at(goal(), date(2027, 1, 1)) == 3500


def test_expected_pathway_midpoint():
    value = expected_footprint_at(goal(), date(2026, 7, 2))
    assert 4200 < value < 4300


def test_normalize_assessments_dicts():
    records = normalize_assessments(assessments())
    assert len(records) == 3
    assert records[0]["date"] == date(2026, 1, 1)


def test_normalize_legacy_tuple():
    row = (1, "2026-01-01", "car", 10000, 300, "mixed", 2, 5000, 70)
    records = normalize_assessments([row])
    assert records[0]["footprint"] == 5000


def test_invalid_assessment_rows_are_skipped():
    rows = [{"id": 1, "date": "not-a-date", "footprint": 5000}, {"date": "2026-01-01", "footprint": 5000}]
    assert len(normalize_assessments(rows)) == 1


def test_latest_assessment():
    assert latest_assessment(assessments())["footprint"] == 4200


def test_observed_pace_is_positive_for_reduction():
    pace = observed_reduction_pace(assessments())
    assert pace > 100


def test_observed_pace_requires_two_records():
    assert observed_reduction_pace(assessments()[:1]) == 0


def test_calculate_progress():
    result = calculate_progress(goal(), assessments(), date(2026, 7, 1))
    assert result["current_kg"] == 4200
    assert result["remaining_kg"] == 700
    assert result["percent_complete"] == 53.33
    assert result["record_count"] == 3


def test_progress_without_data_uses_baseline():
    result = calculate_progress(goal(), [], date(2026, 2, 1))
    assert result["current_kg"] == 5000
    assert result["has_data"] is False
    assert result["percent_complete"] == 0


def test_status_insufficient_data():
    result = calculate_progress(goal(), [], date(2026, 2, 1))
    status = classify_goal_status(goal(), result)
    assert status.code == STATUS_INSUFFICIENT_DATA


def test_status_achieved():
    rows = assessments() + [{"id": 4, "date": "2026-10-01", "footprint": 3400}]
    result = calculate_progress(goal(), rows, date(2026, 10, 1))
    assert classify_goal_status(goal(), result).code == STATUS_ACHIEVED


def test_status_ahead():
    rows = [{"date": "2026-01-01", "footprint": 5000}, {"date": "2026-07-01", "footprint": 3700}]
    result = calculate_progress(goal(), rows, date(2026, 7, 1))
    assert classify_goal_status(goal(), result).code == STATUS_AHEAD


def test_status_on_track():
    rows = [{"date": "2026-01-01", "footprint": 5000}, {"date": "2026-07-01", "footprint": 4250}]
    result = calculate_progress(goal(), rows, date(2026, 7, 1))
    assert classify_goal_status(goal(), result).code == STATUS_ON_TRACK


def test_status_at_risk():
    rows = [{"date": "2026-01-01", "footprint": 5000}, {"date": "2026-07-01", "footprint": 4550}]
    result = calculate_progress(goal(), rows, date(2026, 7, 1))
    assert classify_goal_status(goal(), result).code == STATUS_AT_RISK


def test_status_off_track():
    rows = [{"date": "2026-01-01", "footprint": 5000}, {"date": "2026-07-01", "footprint": 4900}]
    result = calculate_progress(goal(), rows, date(2026, 7, 1))
    assert classify_goal_status(goal(), result).code == STATUS_OFF_TRACK


def test_project_final_footprint():
    projected = project_final_footprint(goal(), assessments(), date(2026, 7, 1))
    assert projected < 4200
    assert projected >= 0


def test_project_target_date():
    target = project_target_date(goal(), assessments(), date(2026, 7, 1))
    assert target is not None
    assert target < date(2027, 1, 1)


def test_project_target_date_unavailable_when_pace_nonpositive():
    rows = [{"date": "2026-01-01", "footprint": 5000}, {"date": "2026-06-01", "footprint": 5100}]
    assert project_target_date(goal(), rows, date(2026, 6, 1)) is None


def test_build_projection():
    projection = build_projection(goal(), assessments(), date(2026, 7, 1))
    assert projection.target_kg == 3500
    assert projection.projected_final_kg < 4200
    assert projection.observed_pace_kg_per_month > 0


def test_generate_pathway_has_exact_anchors():
    pathway = generate_pathway(goal())
    assert pathway[0]["date"] == date(2026, 1, 1)
    assert pathway[0]["target_kg"] == 5000
    assert pathway[-1]["date"] == date(2027, 1, 1)
    assert pathway[-1]["target_kg"] == 3500


def test_generate_pathway_custom_points():
    pathway = generate_pathway(goal(), points=5)
    assert len(pathway) == 5
    assert pathway[2]["fraction"] == 0.5


def test_milestones_are_ordered():
    milestones = generate_milestones(goal(), assessments())
    assert [m.percent for m in milestones] == [10, 25, 50, 75, 90, 100]
    assert milestones[-1].target_kg == 3500


def test_milestone_completion_uses_assessments():
    milestones = generate_milestones(goal(), assessments())
    assert milestones[0].completed is True
    assert milestones[-1].completed is False


def test_milestone_invalid_percentage():
    with pytest.raises(GoalPathwayValidationError):
        generate_milestones(goal(), assessments(), percentages=[101])


def test_category_progress():
    result = calculate_category_progress(goal(), assessments())
    by_name = {item.category: item for item in result}
    assert by_name["Transportation"].absolute_change_kg == -500
    assert by_name["Electricity"].absolute_change_kg == -200
    assert by_name["Diet"].direction == "IMPROVING"


def test_category_progress_missing_data_does_not_invent_values():
    rows = [
        {"date": "2026-01-01", "footprint": 5000, "categories": {"Transportation": 2000}},
        {"date": "2026-07-01", "footprint": 4200, "categories": {"Electricity": 1300}},
    ]
    result = calculate_category_progress(goal(), rows)
    assert any(item.data_available is False for item in result)


def test_build_snapshots():
    snapshots = build_snapshots(goal(), assessments())
    assert len(snapshots) == 3
    assert snapshots[0].expected_kg == 5000


def test_significant_change():
    result = detect_significant_progress_change(5000, 4500, threshold_pct=5)
    assert result["significant"] is True
    assert result["direction"] == "IMPROVEMENT"
    assert result["change_pct"] == -10


def test_insignificant_change():
    result = detect_significant_progress_change(5000, 4900, threshold_pct=5)
    assert result["significant"] is False


def test_compare_periods():
    result = compare_periods(
        assessments(), date(2026, 1, 1), date(2026, 4, 1),
        date(2026, 4, 2), date(2026, 7, 2),
    )
    assert result["available"] is True
    assert result["direction"] == "IMPROVEMENT"


def test_compare_periods_without_data():
    result = compare_periods(assessments(), date(2025, 1, 1), date(2025, 2, 1), date(2026, 4, 1), date(2026, 5, 1))
    assert result["available"] is False


def test_full_analysis():
    analysis = analyze_goal_pathway(goal(), assessments(), date(2026, 7, 1))
    assert analysis.status.code in {STATUS_AHEAD, STATUS_ON_TRACK, STATUS_ACHIEVED}
    assert analysis.progress["current_kg"] == 4200
    assert len(analysis.milestones) == 6
    assert len(analysis.snapshots) == 3


def test_full_analysis_has_no_mutation():
    original = goal()
    snapshot = dict(original)
    analyze_goal_pathway(original, assessments(), date(2026, 7, 1))
    assert original == snapshot


def test_full_analysis_warning_for_shortfall():
    rows = [{"date": "2026-01-01", "footprint": 5000}, {"date": "2026-07-01", "footprint": 4950}]
    analysis = analyze_goal_pathway(goal(), rows, date(2026, 7, 1))
    assert analysis.projection.projected_shortfall_kg > 0
    assert analysis.warnings


def test_weekly_summary_shape():
    analysis = analyze_goal_pathway(goal(), assessments(), date(2026, 7, 1))
    summary = analysis.to_dict()
    assert "projection" in summary
    assert "milestones" in summary
    assert "category_progress" in summary


def test_serialize_roundtrip_payload():
    analysis = analyze_goal_pathway(goal(), assessments(), date(2026, 7, 1))
    payload = serialize_pathway(analysis)
    restored = deserialize_pathway(payload)
    assert restored["goal_id"] == 7
    assert restored["start_date"] == "2026-01-01"


def test_pathway_id_is_stable():
    analysis = analyze_goal_pathway(goal(), assessments(), date(2026, 7, 1))
    assert pathway_id(goal(), analysis) == pathway_id(goal(), analysis)


def test_rank_categories():
    items = calculate_category_progress(goal(), assessments())
    ranked = rank_categories(items)
    assert abs(ranked[0].absolute_change_kg) >= abs(ranked[-1].absolute_change_kg)


def test_best_improvement():
    items = calculate_category_progress(goal(), assessments())
    assert best_improvement(items).category == "Transportation"


def test_largest_regression():
    rows = [
        {"date": "2026-01-01", "footprint": 5000, "categories": {"Transportation": 2000, "Electricity": 1500}},
        {"date": "2026-07-01", "footprint": 4500, "categories": {"Transportation": 1800, "Electricity": 1700}},
    ]
    items = calculate_category_progress(goal(), rows)
    assert largest_regression(items).category == "Electricity"


def test_human_status_message():
    analysis = analyze_goal_pathway(goal(), assessments(), date(2026, 7, 1))
    assert "kg" in human_status_message(analysis)


def test_target_date_at_current_pace():
    result = target_date_at_current_pace(goal(), assessments(), date(2026, 7, 1))
    assert result["available"] is True
    assert result["projected_date"] < date(2027, 1, 1)


def test_chart_rows_are_sorted():
    analysis = analyze_goal_pathway(goal(), assessments(), date(2026, 7, 1))
    rows = build_chart_rows(analysis)
    assert rows == sorted(rows, key=lambda row: row["date"])


def test_custom_status_thresholds():
    config = PathwayConfig(ahead_ratio=-0.10, on_track_ratio=0.10, at_risk_ratio=0.30)
    validate_pathway_config(config)
    progress = calculate_progress(goal(), assessments(), date(2026, 7, 1))
    status = classify_goal_status(goal(), progress, config)
    assert status.code in VALID_STATUSES


def test_invalid_threshold_configuration():
    config = PathwayConfig(ahead_ratio=0.2, on_track_ratio=0.1, at_risk_ratio=0.3)
    with pytest.raises(GoalPathwayValidationError):
        validate_pathway_config(config)


def test_empty_milestone_configuration():
    config = PathwayConfig(milestone_percents=())
    with pytest.raises(GoalPathwayValidationError):
        validate_pathway_config(config)


def test_negative_significant_threshold_rejected():
    config = PathwayConfig(significant_change_pct=-1)
    with pytest.raises(GoalPathwayValidationError):
        validate_pathway_config(config)


def test_nan_assessment_is_ignored():
    rows = [{"date": "2026-01-01", "footprint": float("nan")}, {"date": "2026-02-01", "footprint": 4900}]
    assert len(normalize_assessments(rows)) == 1


def test_duplicate_dates_have_deterministic_order():
    rows = [
        {"id": 2, "date": "2026-01-01", "footprint": 4900},
        {"id": 1, "date": "2026-01-01", "footprint": 5000},
    ]
    result = normalize_assessments(rows)
    assert [item["id"] for item in result] == [1, 2]
