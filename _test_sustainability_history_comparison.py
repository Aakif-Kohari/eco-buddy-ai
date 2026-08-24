from datetime import datetime, timezone, timedelta
import json

import pytest

from sustainability_history_comparison import (
    AssessmentRecord,
    build_change_attribution,
    build_history_timeline,
    compare_assessments,
    compare_history_endpoints,
    compare_selected_ids,
    export_comparison_csv,
    export_comparison_json,
    export_history_json,
    export_markdown_report,
    find_biggest_changes,
    history_quality_flags,
    normalize_assessment,
    normalize_history,
    percentage_change,
    rolling_average,
    summarize_history,
    trend_direction,
    validate_comparison,
)

NOW = datetime(2026, 8, 23, 12, tzinfo=timezone.utc)


def record(id=1, days=0, footprint=1000, score=60, distance=20, electricity=300, flights=2, transport="Car", diet="Non-Vegetarian", factor_version="static-v1"):
    return {
        "id": id,
        "user_id": 1,
        "date": (NOW + timedelta(days=days)).isoformat(),
        "created_at": (NOW + timedelta(days=days)).isoformat(),
        "transport": transport,
        "distance": distance,
        "electricity": electricity,
        "diet": diet,
        "flights": flights,
        "footprint": footprint,
        "eco_score": score,
        "factor_version": factor_version,
    }


def test_percentage_change_zero():
    assert percentage_change(0, 0) == 0
    assert percentage_change(0, 10) is None


def test_normalize_preferred_tuple_shape():
    row = (1, NOW.isoformat(), "Car", NOW.isoformat(), 20, 300, "Vegetarian", 1, 800, 75, "static-v1")
    item = normalize_assessment(row)
    assert item.id == 1
    assert item.transport == "Car"
    assert item.factor_version == "static-v1"


def test_normalize_legacy_tuple_shape():
    row = (1, NOW.isoformat(), NOW.isoformat(), "Car", 20, 300, "Vegetarian", 1, 800, 75)
    item = normalize_assessment(row)
    assert item.id == 1
    assert item.footprint == 800


def test_history_sorted_and_deduplicated():
    rows = [record(2, 1), record(1, 0), record(1, 0)]
    history = normalize_history(rows)
    assert [item.id for item in history] == [1, 2]


def test_compare_same_factor_version():
    comparison = compare_assessments(record(1, 0, 1000), record(2, 10, 800, score=70, distance=10, electricity=200, flights=1))
    assert comparison.footprint_change.absolute_change == -200
    assert comparison.methodology_changed is False
    assert comparison.attribution.factor_change_kg == 0
    assert comparison.attribution.behaviour_change_kg == comparison.attribution.total_change_kg


def test_compare_factor_version_change():
    comparison = compare_assessments(record(1, 0, 1000, factor_version="static-v1"), record(2, 10, 800, factor_version="static-v2"))
    assert comparison.methodology_changed is True
    assert comparison.attribution.factor_impact.from_version == "static-v1"
    assert comparison.attribution.factor_impact.to_version == "static-v2"
    assert comparison.methodology_warning


def test_category_attribution_contains_all_categories():
    comparison = compare_assessments(record(1, 0), record(2, 10, 800, distance=10, electricity=200, flights=1))
    assert {item.category for item in comparison.attribution.category_attributions} == {"Transport", "Electricity", "Diet", "Flights"}


def test_attribution_reconstructs_change_for_same_factors():
    comparison = compare_assessments(record(1, 0, 1000), record(2, 10, 800, distance=10, electricity=200, flights=1))
    assert abs(comparison.attribution.behaviour_change_kg - comparison.attribution.total_change_kg) < 0.01


def test_compare_endpoints():
    comparison = compare_history_endpoints([record(2, 2, 700), record(1, 0, 1000)])
    assert comparison.before.id == 1
    assert comparison.after.id == 2


def test_compare_selected_ids():
    comparison = compare_selected_ids([record(1, 0), record(2, 1, 900)], 1, 2)
    assert comparison.before.id == 1
    assert comparison.after.id == 2


def test_compare_selected_missing_id():
    with pytest.raises(KeyError):
        compare_selected_ids([record(1)], 1, 9)


def test_timeline_monthly():
    timeline = build_history_timeline([record(1, 0), record(2, 10), record(3, 40)], "monthly")
    assert len(timeline) >= 2
    assert all(point.assessments >= 1 for point in timeline)


def test_timeline_quarterly():
    timeline = build_history_timeline([record(1, 0), record(2, 40)], "quarterly")
    assert timeline


def test_timeline_yearly():
    timeline = build_history_timeline([record(1, 0), record(2, 40)], "yearly")
    assert timeline


def test_invalid_period():
    with pytest.raises(ValueError):
        build_history_timeline([record(1)], "weekly")


def test_summary():
    summary = summarize_history([record(1, 0, 1000, score=60), record(2, 10, 800, score=75)])
    assert summary.count == 2
    assert summary.footprint_change_kg == -200
    assert summary.score_change == 15


def test_summary_mixed_versions_warns():
    summary = summarize_history([record(1, 0, factor_version="static-v1"), record(2, 10, factor_version="static-v2")])
    assert summary.comparable is False
    assert summary.warnings


def test_trend_direction():
    assert trend_direction([record(1, 0, 1000), record(2, 1, 800)]) == "decreasing"
    assert trend_direction([record(1, 0, 800), record(2, 1, 1000)]) == "increasing"
    assert trend_direction([record(1)]) == "insufficient_data"


def test_rolling_average():
    values = rolling_average([record(1, 0, 1000), record(2, 1, 800), record(3, 2, 600)], 2)
    assert values[-1]["rolling_average"] == 700


def test_biggest_changes():
    changes = find_biggest_changes([record(1, 0, 1000), record(2, 1, 900), record(3, 2, 500)], 1)
    assert len(changes) == 1
    assert abs(changes[0].footprint_change.absolute_change) == 400


def test_quality_flags():
    assert "mixed_factor_versions" in history_quality_flags([record(1), record(2, 1, factor_version="static-v2")])
    assert "single_assessment" in history_quality_flags([record(1)])


def test_validate_comparison():
    comparison = compare_assessments(record(1), record(2, 1, 900))
    assert validate_comparison(comparison) == []


def test_export_json_is_valid():
    comparison = compare_assessments(record(1), record(2, 1, 900))
    payload = json.loads(export_comparison_json(comparison))
    assert payload["schema_version"] == "1.0"
    assert "comparison" in payload


def test_export_csv_has_rows():
    comparison = compare_assessments(record(1), record(2, 1, 900))
    text = export_comparison_csv(comparison)
    assert "Annual footprint" in text
    assert "Factor/methodology effect" in text


def test_export_markdown():
    comparison = compare_assessments(record(1), record(2, 1, 900))
    text = export_markdown_report(comparison)
    assert "Sustainability History Comparison" in text
    assert "Change attribution" in text


def test_export_history_json():
    payload = json.loads(export_history_json([record(1), record(2, 1, 900)]))
    assert payload["schema_version"] == "1.0"
    assert len(payload["assessments"]) == 2


def test_record_inputs_are_stable():
    item = normalize_assessment(record())
    assert item.inputs() == {"transport": "Car", "distance": 20.0, "electricity": 300.0, "diet": "Non-Vegetarian", "flights": 2}


def test_negative_input_is_clamped():
    item = normalize_assessment(record(distance=-10, electricity=-5, flights=-1))
    assert item.distance == 0
    assert item.electricity == 0
    assert item.flights == 0
