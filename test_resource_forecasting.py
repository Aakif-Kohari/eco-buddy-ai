"""Tests for the Sustainability Resource Consumption Forecasting Engine (#1297)."""

from __future__ import annotations

import datetime as dt
import json

import pytest

import resource_forecasting as rf


BASE = dt.datetime(2026, 1, 1)


def row(idx, days, distance=100, electricity=300, flights=1, footprint=500, score=70):
    stamp = (BASE + dt.timedelta(days=days)).isoformat()
    return (idx, stamp, stamp, "Car", distance, electricity, "Balanced", flights, footprint, score)


def rows(count=8):
    return [
        row(i + 1, i * 30, 100 + i * 10, 300 + i * 5, 1 + (i % 2), 500 - i * 12)
        for i in range(count)
    ]


def test_normalize_assessment_tuple():
    observation = rf.normalize_assessment(row(7, 30, 123, 321, 2, 456, 88))
    assert observation.assessment_id == 7
    assert observation.distance_km == 123
    assert observation.electricity_kwh == 321
    assert observation.flights == 2
    assert observation.footprint_kg_co2e == 456
    assert observation.eco_score == 88


def test_normalize_mapping():
    observation = rf.normalize_assessment({
        "id": 3,
        "date": "2026-02-01T00:00:00",
        "distance": 44,
        "electricity": 55,
        "flights": 0,
        "footprint": 77,
        "eco_score": 91,
    })
    assert observation.assessment_id == 3
    assert observation.distance_km == 44
    assert observation.electricity_kwh == 55


def test_normalize_deduplicates_and_sorts():
    source = [row(2, 60), row(1, 0), row(2, 60, 999)]
    result = rf.normalize_assessments(source)
    assert [item.assessment_id for item in result] == [1, 2]
    assert result[-1].distance_km == 100


def test_invalid_timestamp_is_rejected():
    bad = list(row(1, 0))
    bad[1] = "not-a-date"
    with pytest.raises(rf.ForecastValidationError):
        rf.normalize_assessment(tuple(bad))


def test_non_finite_values_are_rejected():
    bad = list(row(1, 0))
    bad[4] = float("nan")
    with pytest.raises(rf.ForecastValidationError):
        rf.normalize_assessment(tuple(bad))


def test_negative_resource_is_rejected_during_series_creation():
    observations = [rf.normalize_assessment(row(1, 0, distance=-2))]
    with pytest.raises(rf.ForecastValidationError):
        rf.resource_series(observations, rf.RESOURCE_DISTANCE)


def test_available_resource_counts():
    observations = rf.normalize_assessments(rows(4))
    counts = rf.available_resources(observations)
    assert counts[rf.RESOURCE_DISTANCE] == 4
    assert counts[rf.RESOURCE_ELECTRICITY] == 4
    assert counts[rf.RESOURCE_FLIGHTS] == 4
    assert counts[rf.RESOURCE_FOOTPRINT] == 4


def test_data_quality_changes_with_history_size():
    observations = rf.normalize_assessments(rows(2))
    quality = rf.describe_data_quality(observations, rf.RESOURCE_DISTANCE)
    assert quality["quality"] == "low"
    observations = rf.normalize_assessments(rows(8))
    assert rf.describe_data_quality(observations, rf.RESOURCE_DISTANCE)["quality"] == "high"


def test_linear_forecast_follows_upward_trend():
    series = [(BASE + dt.timedelta(days=i * 30), 100 + i * 10) for i in range(5)]
    values, residual = rf.linear_forecast(series, 3)
    assert values[0] > 140
    assert values[-1] > values[0]
    assert residual is not None


def test_linear_forecast_requires_two_points():
    with pytest.raises(rf.ForecastUnavailableError):
        rf.linear_forecast([(BASE, 100)], 2)


def test_linear_forecast_rejects_same_dates():
    series = [(BASE, 100), (BASE, 120)]
    with pytest.raises(rf.ForecastUnavailableError):
        rf.linear_forecast(series, 2)


def test_moving_average_is_recursive_and_non_negative():
    series = [(BASE + dt.timedelta(days=i), value) for i, value in enumerate([10, 20, 30])]
    values, _ = rf.moving_average_forecast(series, 3, window=2)
    assert values == [25, 27.5, 26.25]
    assert all(value >= 0 for value in values)


def test_exponential_smoothing_responds_to_latest_values():
    series = [(BASE + dt.timedelta(days=i), value) for i, value in enumerate([10, 10, 100])]
    values, _ = rf.exponential_forecast(series, 2, alpha=0.5)
    assert values == [55.0, 55.0]


def test_forecast_dispatch_rejects_unknown_method():
    with pytest.raises(rf.ForecastValidationError):
        rf.forecast_values([(BASE, 1), (BASE + dt.timedelta(days=1), 2)], 2, "unknown")


def test_horizon_validation():
    assert rf.validate_horizon(4) == 4
    with pytest.raises(rf.ForecastValidationError):
        rf.validate_horizon(0)
    with pytest.raises(rf.ForecastValidationError):
        rf.validate_horizon(rf.MAX_HORIZON + 1)


def test_alpha_validation():
    assert rf.validate_alpha(0.5) == 0.5
    with pytest.raises(rf.ForecastValidationError):
        rf.validate_alpha(0)


def test_forecast_dates_use_median_gap():
    series = [(BASE, 1), (BASE + dt.timedelta(days=30), 2), (BASE + dt.timedelta(days=60), 3)]
    dates = rf.forecast_dates(series, 2)
    assert dates == [BASE + dt.timedelta(days=90), BASE + dt.timedelta(days=120)]


def test_build_result_contains_uncertainty_for_sufficient_history():
    observations = rf.normalize_assessments(rows(8))
    result = rf.build_forecast_result(observations, rf.RESOURCE_DISTANCE, 4)
    assert result.data_points == 8
    assert result.residual_std is not None
    assert len(result.forecast) == 4
    assert result.forecast[-1].upper is not None


def test_short_history_omits_uncertainty_band():
    observations = rf.normalize_assessments(rows(2))
    result = rf.build_forecast_result(observations, rf.RESOURCE_DISTANCE, 2)
    assert result.quality == "low"
    assert result.residual_std is None
    assert result.forecast[0].lower is None


def test_missing_resource_is_reported_not_fabricated():
    observations = [rf.normalize_assessment(row(i, i * 30, electricity=None)) for i in range(1, 4)]
    results, unavailable = rf.forecast_all_resources(observations, 2)
    assert rf.RESOURCE_ELECTRICITY not in [item.resource for item in results]
    assert rf.RESOURCE_ELECTRICITY in unavailable


def test_report_contains_all_available_resources():
    observations = rf.normalize_assessments(rows(5))
    report = rf.build_forecast_report(42, observations, 3)
    assert report.user_id == 42
    assert len(report.results) == 4
    assert report.engine_version == rf.ENGINE_VERSION


def test_report_serializes_to_valid_json():
    observations = rf.normalize_assessments(rows(5))
    report = rf.build_forecast_report(42, observations, 3)
    payload = rf.serialize_report(report)
    parsed = json.loads(payload)
    assert parsed["user_id"] == 42
    assert parsed["results"]
    assert parsed["engine_version"] == rf.ENGINE_VERSION


def test_compare_forecasts_requires_same_resource():
    observations = rf.normalize_assessments(rows(8))
    a = rf.build_forecast_result(observations, rf.RESOURCE_DISTANCE, 3, rf.METHOD_LINEAR)
    b = rf.build_forecast_result(observations, rf.RESOURCE_DISTANCE, 3, rf.METHOD_MOVING_AVERAGE)
    comparison = rf.compare_forecasts([a, b])
    assert comparison.resource == rf.RESOURCE_DISTANCE
    assert comparison.spread >= 0


def test_compare_forecasts_rejects_mixed_resources():
    observations = rf.normalize_assessments(rows(8))
    a = rf.build_forecast_result(observations, rf.RESOURCE_DISTANCE, 3)
    b = rf.build_forecast_result(observations, rf.RESOURCE_ELECTRICITY, 3)
    with pytest.raises(rf.ForecastValidationError):
        rf.compare_forecasts([a, b])


def test_scenario_multiplier_does_not_change_original():
    observations = rf.normalize_assessments(rows(6))
    original = rf.build_forecast_result(observations, rf.RESOURCE_DISTANCE, 3)
    scenario = rf.generate_scenario(original, 0.8)
    assert scenario.end_value == pytest.approx(original.end_value * 0.8)
    assert original.end_value != scenario.end_value
    assert original.baseline != scenario.baseline


def test_scenario_rejects_negative_multiplier():
    observations = rf.normalize_assessments(rows(5))
    result = rf.build_forecast_result(observations, rf.RESOURCE_DISTANCE, 2)
    with pytest.raises(rf.ForecastValidationError):
        rf.generate_scenario(result, -0.1)


def test_trend_direction():
    observations = rf.normalize_assessments(rows(6))
    result = rf.build_forecast_result(observations, rf.RESOURCE_DISTANCE, 3)
    assert rf.trend_direction(result) == "increasing"


def test_format_change_is_user_readable():
    observations = rf.normalize_assessments(rows(6))
    result = rf.build_forecast_result(observations, rf.RESOURCE_DISTANCE, 3)
    text = rf.format_change(result)
    assert "km" in text
    assert "%" in text


def test_explanation_mentions_method_and_points():
    observations = rf.normalize_assessments(rows(5))
    result = rf.build_forecast_result(observations, rf.RESOURCE_DISTANCE, 2)
    explanation = rf.explain_forecast(result)
    assert any("Method:" in line for line in explanation)
    assert any("observations" in line for line in explanation)


def test_forecast_from_rows_is_integration_wrapper():
    report = rf.forecast_from_rows(7, rows(5), horizon=2, method=rf.METHOD_MOVING_AVERAGE)
    assert report.user_id == 7
    assert report.method == rf.METHOD_MOVING_AVERAGE
    assert report.results
