"""Tests for Sustainability Behavior Pattern and Habit Correlation Analyzer."""
from datetime import date, timedelta
import json
import tempfile

import pytest

from behavior_pattern_analyzer import (
    SCHEMA_VERSION,
    BehaviorReport,
    CorrelationResult,
    analyze_habit_data,
    build_report,
    co_occurrence,
    correlation_matrix,
    detect_patterns,
    filter_window,
    habit_pair_history,
    habit_statistics,
    lagged_correlation,
    normalize_observations,
    report_to_dict,
    serialize_report,
    streak_distribution,
    summarize_report,
    top_correlations,
    validate_report_payload,
    weekday_rates,
)


def records(days=30):
    start = date(2026, 1, 1)
    rows = []
    for i in range(days):
        day = start + timedelta(days=i)
        rows.append({"habit": "Walk short trips", "date": day.isoformat(), "completed": i % 2 == 0})
        rows.append({"habit": "Turn off lights", "date": day.isoformat(), "completed": i % 2 == 0})
        rows.append({"habit": "Plant-based meal", "date": day.isoformat(), "completed": i % 3 != 0})
    return rows


def test_normalize_list_records():
    result = normalize_observations(records(3))
    assert len(result) == 9
    assert any(r.category == "Transport" for r in result)
    assert result[0].day == date(2026, 1, 1)


def test_normalize_habit_tracker_shape():
    source = {"history": {"Turn off lights": [{"date": "2026-01-01", "streak": 1}, {"date": "2026-01-02", "streak": 2}]}}
    result = normalize_observations(source)
    assert [r.day for r in result] == [date(2026, 1, 1), date(2026, 1, 2)]


def test_completed_today_snapshot_is_supported(monkeypatch):
    monkeypatch.setattr("behavior_pattern_analyzer.date", date)
    result = normalize_observations({"completed_today": ["Compost food scraps"]})
    assert result[0].completed is True


def test_invalid_dates_are_ignored():
    result = normalize_observations([{"habit": "A", "date": "not-a-date"}])
    assert result == []


def test_filter_window_rejects_bad_values():
    with pytest.raises(ValueError):
        filter_window([], 0)
    with pytest.raises(ValueError):
        filter_window([], 731)


def test_filter_window_selects_recent_records():
    source = records(30)
    obs = normalize_observations(source)
    result = filter_window(obs, 7, end=date(2026, 1, 30))
    assert len(result) == 21
    assert min(x.day for x in result) == date(2026, 1, 24)


def test_habit_statistics_rates_and_streaks():
    obs = normalize_observations(records(10))
    stats = habit_statistics(obs)
    walk = next(x for x in stats if x.habit == "Walk short trips")
    assert walk.observations == 10
    assert walk.completions == 5
    assert walk.completion_rate == 50.0
    assert walk.longest_streak == 1


def test_all_complete_has_long_streak():
    obs = normalize_observations([
        {"habit": "Recycle", "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(), "completed": True}
        for i in range(8)
    ])
    stats = habit_statistics(obs)[0]
    assert stats.longest_streak == 8
    assert stats.current_streak == 8


def test_correlation_detects_positive_association():
    obs = normalize_observations(records(30))
    result = correlation_matrix(obs)
    pair = next(x for x in result if {x.left, x.right} == {"Walk short trips", "Turn off lights"})
    assert pair.coefficient == pytest.approx(1.0)
    assert pair.direction == "positive"
    assert pair.strength == "very strong"


def test_correlation_skips_constant_series():
    source = [{"habit": "A", "date": f"2026-01-{i:02d}", "completed": True} for i in range(1, 5)]
    source += [{"habit": "B", "date": f"2026-01-{i:02d}", "completed": i % 2 == 0} for i in range(1, 5)]
    assert correlation_matrix(normalize_observations(source)) == []


def test_correlation_needs_three_observations():
    source = records(2)
    assert correlation_matrix(normalize_observations(source)) == []


def test_lagged_correlation():
    source = []
    start = date(2026, 1, 1)
    for i in range(12):
        source.append({"habit": "Morning walk", "date": (start + timedelta(days=i)).isoformat(), "completed": i % 2 == 0})
        source.append({"habit": "Meal prep", "date": (start + timedelta(days=i + 1)).isoformat(), "completed": i % 2 == 0})
    result = lagged_correlation(normalize_observations(source), "Morning walk", "Meal prep", 1)
    assert result is not None
    assert result.coefficient == pytest.approx(1.0)


def test_negative_lag_rejected():
    with pytest.raises(ValueError):
        lagged_correlation([], "A", "B", -1)


def test_co_occurrence_matrix():
    obs = normalize_observations(records(5))
    matrix = co_occurrence(obs)
    assert matrix["Walk short trips"]["Turn off lights"] == 3
    assert matrix["Walk short trips"]["Walk short trips"] == 3


def test_weekday_rates_are_percentages():
    obs = normalize_observations(records(14))
    rates = weekday_rates(obs)
    assert set(rates["Walk short trips"]) == {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
    assert all(0 <= value <= 100 for value in rates["Walk short trips"].values())


def test_streak_distribution():
    source = [{"habit": "A", "date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(), "completed": True} for i in range(4)]
    source += [{"habit": "A", "date": "2026-01-06", "completed": True}]
    result = streak_distribution(normalize_observations(source))["A"]
    assert result["max"] == 4
    assert result["count"] == 2


def test_pattern_detection_empty():
    findings = detect_patterns([])
    assert findings[0].kind == "empty"


def test_pattern_detection_finds_completion_gap():
    source = []
    for i in range(20):
        day = (date(2026, 1, 1) + timedelta(days=i)).isoformat()
        source.append({"habit": "Easy", "date": day, "completed": True})
        source.append({"habit": "Hard", "date": day, "completed": i < 4})
    findings = detect_patterns(normalize_observations(source))
    assert any(f.kind == "completion_gap" for f in findings)


def test_pattern_detection_mentions_correlation_limit():
    obs = normalize_observations(records(30))
    findings = detect_patterns(obs, correlation_matrix(obs))
    correlation_findings = [f for f in findings if f.kind == "correlation"]
    assert correlation_findings
    assert "causation" in correlation_findings[0].description


def test_build_report_contains_all_sections():
    report = build_report(records(30), days=30, end=date(2026, 1, 30))
    assert report.schema_version == SCHEMA_VERSION
    assert report.window_start == "2026-01-01"
    assert report.window_end == "2026-01-30"
    assert report.total_observations == 90
    assert report.habit_stats
    assert report.co_occurrence
    assert report.weekday_rates
    assert report.streak_distribution
    assert report.limitations


def test_build_report_empty():
    report = build_report([], days=30)
    assert report.total_observations == 0
    assert report.window_start is None
    assert report.findings[0].kind == "empty"


def test_analyze_habit_data_alias():
    assert analyze_habit_data(records(5)).total_observations == 15


def test_top_correlations_filters_and_limits():
    report = build_report(records(30))
    values = top_correlations(report, limit=1, minimum=0.4)
    assert len(values) == 1
    assert abs(values[0].coefficient) >= 0.4


def test_top_correlations_rejects_bad_limit():
    report = build_report(records(5))
    with pytest.raises(ValueError):
        top_correlations(report, 0)


def test_pair_history_has_one_row_per_date():
    history = habit_pair_history(records(5), "Walk short trips", "Turn off lights")
    assert len(history) == 5
    assert history[0]["date"] == "2026-01-01"
    assert history[0]["Walk short trips"] is True


def test_summary_is_compact():
    report = build_report(records(10))
    summary = summarize_report(report)
    assert summary["habits_tracked"] == 3
    assert summary["observations"] == 30
    assert "strongest_associations" in summary


def test_serialization_round_trip_to_dict():
    report = build_report(records(10))
    raw = serialize_report(report, pretty=True)
    payload = json.loads(raw)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert report_to_dict(report)["total_observations"] == 30


def test_validation_accepts_valid_payload():
    payload = report_to_dict(build_report(records(5)))
    assert validate_report_payload(payload) == []


def test_validation_rejects_wrong_schema():
    payload = report_to_dict(build_report(records(5)))
    payload["schema_version"] = "9.0"
    assert "Unsupported or missing schema_version" in validate_report_payload(payload)


def test_validation_rejects_missing_lists():
    assert "Missing field: findings" in validate_report_payload({"schema_version": SCHEMA_VERSION})


def test_export_report_writes_json(tmp_path):
    from behavior_pattern_analyzer import export_report
    path = tmp_path / "report.json"
    export_report(build_report(records(5)), str(path))
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == SCHEMA_VERSION


def test_observation_values_do_not_change_binary_correlation():
    source = [
        {"habit": "A", "date": "2026-01-01", "completed": True, "value": 10},
        {"habit": "A", "date": "2026-01-02", "completed": False, "value": 50},
        {"habit": "A", "date": "2026-01-03", "completed": True, "value": 20},
        {"habit": "B", "date": "2026-01-01", "completed": True, "value": 1},
        {"habit": "B", "date": "2026-01-02", "completed": False, "value": 1},
        {"habit": "B", "date": "2026-01-03", "completed": True, "value": 1},
    ]
    pair = correlation_matrix(normalize_observations(source))[0]
    assert pair.coefficient == pytest.approx(1.0)


def test_duplicate_records_are_deterministic():
    obs = normalize_observations(records(5) + records(5))
    report = build_report(obs, days=5, end=date(2026, 1, 5))
    assert report.total_observations == 30
    assert report.correlations[0].observations == 5


def test_categories_are_preserved():
    source = [{"habit": "Custom", "category": "Water", "date": "2026-01-01"}]
    assert normalize_observations(source)[0].category == "Water"


def test_direct_mapping_format():
    source = {"Custom habit": ["2026-01-01", "2026-01-02"]}
    result = normalize_observations(source)
    assert len(result) == 2


def test_non_mapping_iterable_tuples():
    result = normalize_observations([("A", "2026-01-01"), ("A", "2026-01-02")])
    assert len(result) == 2


def test_report_is_dataclass():
    report = build_report(records(3))
    assert isinstance(report, BehaviorReport)
    assert isinstance(report.correlations[0], CorrelationResult)
