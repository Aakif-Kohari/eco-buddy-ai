from datetime import datetime, timedelta
import json

import pytest

from sustainability_trends import (
    AssessmentRecord,
    TrendValidationError,
    available_categories,
    available_periods,
    benchmark_label,
    build_benchmark,
    build_period_snapshot,
    build_trend_summary,
    calculate_average_footprint,
    calculate_category_trend,
    calculate_category_trends,
    calculate_change,
    calculate_consistency_score,
    calculate_current_percentile,
    calculate_improvement_rate,
    calculate_maximum_footprint,
    calculate_median_footprint,
    calculate_minimum_footprint,
    calculate_moving_average,
    calculate_percentage_change,
    calculate_period_over_period,
    calculate_trend,
    classify_direction,
    compare_named_periods,
    compare_periods,
    detect_significant_changes,
    describe_trend,
    filter_by_period,
    find_best_assessment,
    find_worst_assessment,
    normalize_assessment,
    normalize_assessments,
    serialize_assessments,
    serialize_summary,
    validate_period,
)


BASE = datetime(2026, 1, 1)


def record(index, footprint, *, days=None, eco_score=70, categories=None):
    return {
        "id": index,
        "user_id": 1,
        "date": BASE + timedelta(days=index if days is None else days),
        "created_at": BASE + timedelta(days=index if days is None else days),
        "transport": "Car",
        "distance": 1000 + index,
        "electricity": 200 + index,
        "diet": "Mixed",
        "flights": index,
        "footprint": footprint,
        "eco_score": eco_score,
        "trip_id": None,
        "factor_version": "static-v1",
        "categories": categories or {},
    }


def test_normalize_mapping():
    item = normalize_assessment(record(1, 4000))
    assert item.id == 1
    assert item.footprint == 4000
    assert item.date == BASE + timedelta(days=1)


def test_normalize_repository_tuple():
    values = [3, 1, "2026-01-04", "2026-01-04", "Bus", 500, 100, "Vegetarian", 0, 3200, 82, None, "static-v1"]
    item = normalize_assessment(values)
    assert item.id == 3
    assert item.footprint == 3200
    assert item.factor_version == "static-v1"


def test_normalize_rejects_short_tuple():
    with pytest.raises(TrendValidationError):
        normalize_assessment([1, 2, 3])


def test_normalize_rejects_invalid_date():
    bad = record(1, 4000)
    bad["date"] = "not-a-date"
    with pytest.raises(TrendValidationError):
        normalize_assessment(bad)


def test_normalize_rejects_negative_footprint():
    bad = record(1, -1)
    with pytest.raises(TrendValidationError):
        normalize_assessment(bad)


def test_normalize_rejects_nan():
    bad = record(1, float("nan"))
    with pytest.raises(TrendValidationError):
        normalize_assessment(bad)


def test_normalize_assessments_sorts_and_deduplicates():
    values = [record(2, 3500), record(1, 4000), record(1, 4100)]
    result = normalize_assessments(values)
    assert [item.id for item in result] == [1, 2]
    assert [item.footprint for item in result] == [4000, 3500]


def test_average():
    records = normalize_assessments([record(1, 4000), record(2, 3000), record(3, 3500)])
    assert calculate_average_footprint(records) == pytest.approx(3500)


def test_median():
    records = normalize_assessments([record(1, 4000), record(2, 3000), record(3, 3500)])
    assert calculate_median_footprint(records) == pytest.approx(3500)


def test_minimum():
    records = normalize_assessments([record(1, 4000), record(2, 3000), record(3, 3500)])
    assert calculate_minimum_footprint(records) == 3000


def test_maximum():
    records = normalize_assessments([record(1, 4000), record(2, 3000), record(3, 3500)])
    assert calculate_maximum_footprint(records) == 4000


def test_empty_aggregates():
    assert calculate_average_footprint([]) is None
    assert calculate_median_footprint([]) is None
    assert calculate_minimum_footprint([]) is None
    assert calculate_maximum_footprint([]) is None


def test_change():
    assert calculate_change(4000, 3500) == -500
    assert calculate_change(None, 3500) is None


def test_percentage_change():
    assert calculate_percentage_change(4000, 3500) == pytest.approx(-12.5)
    assert calculate_percentage_change(0, 0) == 0
    assert calculate_percentage_change(0, 100) is None


def test_direction_improving():
    assert classify_direction(-12) == "IMPROVING"


def test_direction_worsening():
    assert classify_direction(12) == "WORSENING"


def test_direction_stable():
    assert classify_direction(1.5) == "STABLE"


def test_direction_insufficient():
    assert classify_direction(None) == "INSUFFICIENT_DATA"


def test_calculate_trend():
    records = normalize_assessments([record(1, 4000), record(2, 3600), record(3, 3000)])
    trend = calculate_trend(records)
    assert trend.starting_footprint == 4000
    assert trend.ending_footprint == 3000
    assert trend.absolute_change == -1000
    assert trend.percentage_change == pytest.approx(-25)
    assert trend.direction == "IMPROVING"
    assert trend.assessment_count == 3


def test_calculate_trend_empty():
    trend = calculate_trend([])
    assert trend.direction == "INSUFFICIENT_DATA"
    assert trend.assessment_count == 0


def test_filter_all_time():
    records = normalize_assessments([record(1, 4000), record(2, 3000)])
    assert len(filter_by_period(records, "All time")) == 2


def test_filter_recent_period():
    now = BASE + timedelta(days=100)
    records = normalize_assessments([record(1, 4000, days=20), record(2, 3000, days=95)])
    filtered = filter_by_period(records, "30 days", as_of=now)
    assert [item.id for item in filtered] == [2]


def test_invalid_period():
    with pytest.raises(ValueError):
        filter_by_period([], "bad")


def test_moving_average_window_three():
    records = normalize_assessments([record(1, 4000), record(2, 3000), record(3, 3500), record(4, 2500)])
    values = calculate_moving_average(records, 3)
    assert values[:2] == [None, None]
    assert values[2] == pytest.approx(3500)
    assert values[3] == pytest.approx(3000)


def test_moving_average_window_one():
    records = normalize_assessments([record(1, 4000)])
    assert calculate_moving_average(records, 1) == [4000]


def test_moving_average_invalid_window():
    with pytest.raises(ValueError):
        calculate_moving_average([], 0)


def test_current_percentile():
    records = normalize_assessments([record(1, 1000), record(2, 2000), record(3, 3000)])
    assert calculate_current_percentile(records) == pytest.approx(100)


def test_benchmark():
    records = normalize_assessments([record(1, 4000), record(2, 2500), record(3, 3000)])
    benchmark = build_benchmark(records)
    assert benchmark.current_footprint == 3000
    assert benchmark.best_footprint == 2500
    assert benchmark.worst_footprint == 4000
    assert benchmark.best_assessment_id == 2
    assert benchmark.worst_assessment_id == 1
    assert benchmark.assessment_count == 3


def test_benchmark_empty():
    benchmark = build_benchmark([])
    assert benchmark.current_footprint is None
    assert benchmark.assessment_count == 0


def test_best_and_worst():
    records = normalize_assessments([record(1, 4000), record(2, 2500), record(3, 3000)])
    assert find_best_assessment(records).id == 2
    assert find_worst_assessment(records).id == 1


def test_significant_changes():
    records = normalize_assessments([record(1, 4000), record(2, 3000), record(3, 2950)])
    changes = detect_significant_changes(records, threshold_percent=10)
    assert len(changes) == 1
    assert changes[0].assessment_id == 2
    assert changes[0].direction == "IMPROVING"


def test_no_significant_changes():
    records = normalize_assessments([record(1, 4000), record(2, 3900)])
    assert detect_significant_changes(records, threshold_percent=10) == []


def test_negative_threshold_rejected():
    with pytest.raises(ValueError):
        detect_significant_changes([], threshold_percent=-1)


def test_period_comparison():
    first = normalize_assessments([record(1, 4000), record(2, 4200)])
    second = normalize_assessments([record(3, 3000), record(4, 3200)])
    comparison = compare_periods(first, second)
    assert comparison.first_average == 4100
    assert comparison.second_average == 3100
    assert comparison.absolute_change == -1000
    assert comparison.direction == "IMPROVING"


def test_named_period_comparison():
    now = BASE + timedelta(days=100)
    records = normalize_assessments([record(1, 5000, days=10), record(2, 4000, days=90)])
    result = compare_named_periods(records, "1 year", "30 days", as_of=now)
    assert result.first_count == 2
    assert result.second_count == 1


def test_period_over_period():
    now = BASE + timedelta(days=100)
    records = normalize_assessments([
        record(1, 5000, days=20),
        record(2, 4500, days=50),
        record(3, 4000, days=80),
        record(4, 3500, days=95),
    ])
    result = calculate_period_over_period(records, days=30, as_of=now)
    assert result.second_count == 2
    assert result.first_count == 1


def test_period_over_period_invalid_days():
    with pytest.raises(ValueError):
        calculate_period_over_period([], days=0)


def test_category_trend():
    records = normalize_assessments([
        record(1, 4000, categories={"transportation": 1800}),
        record(2, 3500, categories={"transportation": 1500}),
    ])
    trend = calculate_category_trend(records, "transportation")
    assert trend.absolute_change == -300
    assert trend.direction == "IMPROVING"


def test_category_trend_missing():
    records = normalize_assessments([record(1, 4000), record(2, 3500)])
    trend = calculate_category_trend(records, "transportation")
    assert trend.direction == "INSUFFICIENT_DATA"
    assert trend.assessment_count == 0


def test_category_trends():
    records = normalize_assessments([
        record(1, 4000, categories={"transportation": 1800, "energy": 900}),
        record(2, 3500, categories={"transportation": 1500, "energy": 950}),
    ])
    trends = calculate_category_trends(records)
    assert [item.category for item in trends] == ["energy", "transportation"]


def test_available_categories():
    records = normalize_assessments([record(1, 4000, categories={"energy": 100, "food": 200})])
    assert available_categories(records) == ("energy", "food")


def test_summary():
    records = [
        record(1, 4000, categories={"transportation": 1800}),
        record(2, 3600, categories={"transportation": 1600}),
        record(3, 3000, categories={"transportation": 1400}),
    ]
    summary = build_trend_summary(records, moving_average_window=2)
    assert summary.overall.direction == "IMPROVING"
    assert summary.benchmark.best_footprint == 3000
    assert summary.most_improved_category.category == "transportation"
    assert len(summary.moving_average) == 3


def test_summary_empty():
    summary = build_trend_summary([])
    assert summary.overall.direction == "INSUFFICIENT_DATA"
    assert summary.benchmark.assessment_count == 0


def test_build_period_snapshot():
    records = [record(1, 4000), record(2, 3500)]
    snapshot = build_period_snapshot(records, period="All time")
    assert snapshot.assessment_count == 2


def test_consistency_single_assessment():
    records = normalize_assessments([record(1, 4000)])
    assert calculate_consistency_score(records) == 100


def test_consistency_multiple_assessments():
    records = normalize_assessments([record(1, 4000), record(2, 4000)])
    assert calculate_consistency_score(records) == 100


def test_consistency_empty():
    assert calculate_consistency_score([]) is None


def test_improvement_rate():
    records = normalize_assessments([record(1, 4000, days=0), record(2, 3000, days=10)])
    assert calculate_improvement_rate(records) == pytest.approx(-100)


def test_improvement_rate_requires_two():
    assert calculate_improvement_rate(normalize_assessments([record(1, 4000)])) is None


def test_describe_improving():
    trend = calculate_trend(normalize_assessments([record(1, 4000), record(2, 3000)]))
    assert "decreasing" in describe_trend(trend)


def test_benchmark_label():
    benchmark = build_benchmark(normalize_assessments([record(1, 4000), record(2, 3000)]))
    assert "Below" in benchmark_label(benchmark)


def test_serialize_summary_is_json():
    summary = build_trend_summary([record(1, 4000), record(2, 3000)])
    encoded = serialize_summary(summary)
    parsed = json.loads(encoded)
    assert parsed["overall"]["direction"] == "IMPROVING"


def test_serialize_assessments_is_json():
    records = normalize_assessments([record(1, 4000)])
    parsed = json.loads(serialize_assessments(records))
    assert parsed[0]["footprint"] == 4000


def test_available_periods():
    assert "All time" in available_periods()
    assert "30 days" in available_periods()


def test_validate_period():
    assert validate_period("90 days") == "90 days"


def test_validate_period_rejects_unknown():
    with pytest.raises(ValueError):
        validate_period("forever")


def test_zero_baseline_direction():
    records = normalize_assessments([record(1, 0), record(2, 100)])
    trend = calculate_trend(records)
    assert trend.direction == "INSUFFICIENT_DATA"


def test_equal_values_are_stable():
    records = normalize_assessments([record(1, 4000), record(2, 4000)])
    trend = calculate_trend(records)
    assert trend.direction == "STABLE"


def test_custom_stable_threshold():
    records = normalize_assessments([record(1, 4000), record(2, 3500)])
    trend = calculate_trend(records, stable_threshold=20)
    assert trend.direction == "STABLE"


def test_custom_significant_threshold():
    records = normalize_assessments([record(1, 4000), record(2, 3900)])
    changes = detect_significant_changes(records, threshold_percent=2)
    assert len(changes) == 1


def test_category_sorting_is_deterministic():
    records = normalize_assessments([
        record(1, 4000, categories={"z": 200, "a": 100}),
        record(2, 3900, categories={"z": 150, "a": 90}),
    ])
    first = calculate_category_trends(records)
    second = calculate_category_trends(records)
    assert [item.category for item in first] == [item.category for item in second]
    assert [item.absolute_change for item in first] == [item.absolute_change for item in second]


def test_duplicate_ids_do_not_change_benchmark():
    values = [record(1, 4000), record(1, 1000), record(2, 3000)]
    result = normalize_assessments(values)
    assert [item.id for item in result] == [1, 2]
    assert result[0].footprint == 4000


def test_input_history_is_not_mutated():
    raw = [record(2, 3000), record(1, 4000)]
    original_ids = [item["id"] for item in raw]
    normalize_assessments(raw)
    assert [item["id"] for item in raw] == original_ids


def test_categories_can_be_supplied_explicitly():
    records = normalize_assessments([record(1, 4000, categories={"energy": 900})])
    trends = calculate_category_trends(records, categories=["energy", "transportation"])
    assert len(trends) == 2
    assert trends[1].direction == "INSUFFICIENT_DATA"


def test_latest_id_is_stable_when_dates_match():
    first = record(2, 3500)
    second = record(1, 4000)
    same_date = BASE + timedelta(days=5)
    first["date"] = same_date
    second["date"] = same_date
    records = normalize_assessments([first, second])
    assert [item.id for item in records] == [1, 2]
    assert calculate_trend(records).latest_assessment_id == 2


def test_worst_and_best_tie_break_by_date_then_id():
    first = record(1, 3000, days=2)
    second = record(2, 3000, days=1)
    records = normalize_assessments([first, second])
    assert find_best_assessment(records).id == 2
    assert find_worst_assessment(records).id == 1


def test_eco_score_is_preserved():
    item = normalize_assessment(record(1, 4000, eco_score=88))
    assert item.eco_score == 88


def test_factor_version_is_preserved():
    item = normalize_assessment(record(1, 4000))
    assert item.factor_version == "static-v1"


def test_summary_serialization_is_deterministic():
    records = [record(1, 4000), record(2, 3000)]
    assert serialize_summary(build_trend_summary(records)) == serialize_summary(build_trend_summary(records))


def test_large_history():
    records = [record(i, 5000 - i * 5) for i in range(1, 101)]
    summary = build_trend_summary(records, moving_average_window=5)
    assert summary.overall.assessment_count == 100
    assert len(summary.moving_average) == 100


def test_missing_eco_score_does_not_break_trend():
    raw = record(1, 4000, eco_score=None)
    item = normalize_assessment(raw)
    assert item.eco_score is None


def test_category_negative_values_are_allowed_for_custom_trace_data():
    raw = record(1, 4000, categories={"net": -10})
    item = normalize_assessment(raw)
    assert item.categories["net"] == -10
