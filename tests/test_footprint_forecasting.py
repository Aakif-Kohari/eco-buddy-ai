"""Tests for the Footprint Trend Forecasting Engine.

Covers linear regression, trend analysis, seasonal patterns, anomaly
detection, forecasting, milestone prediction, and trajectory assessment.
"""

from __future__ import annotations

import math
import pytest

from footprint_forecasting import (
    TrendPoint,
    TrendResult,
    SeasonalPattern,
    Anomaly,
    ForecastResult,
    MilestonePrediction,
    ForecastReport,
    parse_assessment_rows,
    analyse_trend,
    detect_seasonal_pattern,
    detect_anomalies,
    project_forecast,
    predict_milestones,
    assess_trajectory,
    build_forecast_report,
    _linear_regression,
    _timestamp_to_days,
    _parse_month,
    trend_arrow,
    severity_color,
    confidence_color,
    format_months,
)


# ── Fixture data ─────────────────────────────────────────────────────────────

def _make_points(n: int = 10, base_kg: float = 5000.0, monthly_change: float = -100.0) -> list[TrendPoint]:
    """Generate synthetic assessment points with a linear trend."""
    from datetime import datetime, timedelta
    points = []
    start = datetime(2024, 1, 1)
    for i in range(n):
        dt = start + timedelta(days=i * 30)
        kg = base_kg + monthly_change * (i * 30 / 30.44)
        points.append(TrendPoint(
            timestamp=dt.strftime("%Y-%m-%d %H:%M:%S"),
            footprint_kg=round(max(0, kg), 1),
            eco_score=max(0, min(100, int(50 + i * 2))),
        ))
    return points


def _make_rows(n: int = 10, base_kg: float = 5000.0) -> list[tuple]:
    """Generate synthetic raw database rows."""
    from datetime import datetime, timedelta
    rows = []
    start = datetime(2024, 1, 1)
    for i in range(n):
        dt = start + timedelta(days=i * 30)
        kg = base_kg - 50 * i
        rows.append((
            i + 1,                          # id
            dt.strftime("%Y-%m-%d"),        # date
            dt.strftime("%Y-%m-%d %H:%M:%S"),  # created_at
            "Car",                          # transport
            10.0,                           # distance
            200.0,                          # electricity
            "Vegetarian",                   # diet
            1,                              # flights
            round(max(0, kg), 1),           # footprint
            max(0, min(100, 50 + i * 3)),   # eco_score
        ))
    return rows


# ── _linear_regression ──────────────────────────────────────────────────────

class TestLinearRegression:
    def test_perfect_linear(self):
        xs = [0, 1, 2, 3, 4]
        ys = [10, 20, 30, 40, 50]
        slope, intercept, r2 = _linear_regression(xs, ys)
        assert slope == pytest.approx(10.0)
        assert intercept == pytest.approx(10.0)
        assert r2 == pytest.approx(1.0, abs=0.01)

    def test_single_point(self):
        slope, intercept, r2 = _linear_regression([5], [10])
        assert slope == 0.0
        assert intercept == 10.0

    def test_empty_data(self):
        slope, intercept, r2 = _linear_regression([], [])
        assert slope == 0.0

    def test_noisy_data(self):
        import random
        random.seed(42)
        xs = list(range(20))
        ys = [2 * x + 5 + random.uniform(-0.5, 0.5) for x in xs]
        slope, intercept, r2 = _linear_regression(xs, ys)
        assert slope == pytest.approx(2.0, abs=0.2)
        assert r2 > 0.95

    def test_horizontal_line(self):
        xs = [0, 1, 2, 3]
        ys = [5, 5, 5, 5]
        slope, intercept, r2 = _linear_regression(xs, ys)
        assert slope == pytest.approx(0.0)
        assert intercept == pytest.approx(5.0)


# ── _timestamp_to_days / _parse_month ───────────────────────────────────────

class TestTimestampHelpers:
    def test_timestamp_to_days(self):
        days = _timestamp_to_days("2024-01-01 00:00:00")
        assert days > 0

    def test_timestamp_to_days_iso(self):
        days = _timestamp_to_days("2024-06-15T12:00:00")
        assert days > 0

    def test_parse_month(self):
        assert _parse_month("2024-03-15 10:00:00") == 3
        assert _parse_month("2024-12-25") == 12

    def test_invalid_timestamp(self):
        assert _timestamp_to_days("not-a-date") == 0.0
        assert _parse_month("bad") == 1


# ── parse_assessment_rows ───────────────────────────────────────────────────

class TestParseAssessmentRows:
    def test_basic_parsing(self):
        rows = _make_rows(5)
        points = parse_assessment_rows(rows)
        assert len(points) == 5
        assert points[0].footprint_kg > 0

    def test_sorted_by_timestamp(self):
        rows = _make_rows(5)
        points = parse_assessment_rows(rows)
        for i in range(len(points) - 1):
            assert points[i].timestamp <= points[i + 1].timestamp

    def test_empty_rows(self):
        assert parse_assessment_rows([]) == []

    def test_invalid_rows_skipped(self):
        rows = [
            ("bad", "data", None),
            (1, "2024-01-01", "2024-01-01 00:00:00", None, None, None, None, None, 1000.0, 50),
        ]
        points = parse_assessment_rows(rows)
        assert len(points) == 1

    def test_zero_footprint_skipped(self):
        rows = [(1, "2024-01-01", "2024-01-01 00:00:00", "Car", 10, 200, "Veg", 0, 0.0, 50)]
        points = parse_assessment_rows(rows)
        assert len(points) == 0

    def test_none_footprint_skipped(self):
        rows = [(1, "2024-01-01", "2024-01-01 00:00:00", "Car", 10, 200, "Veg", 0, None, 50)]
        points = parse_assessment_rows(rows)
        assert len(points) == 0


# ── analyse_trend ────────────────────────────────────────────────────────────

class TestAnalyseTrend:
    def test_improving_trend(self):
        points = _make_points(12, base_kg=5000, monthly_change=-200)
        result = analyse_trend(points)
        assert result.direction == "improving"
        assert result.slope_kg_per_month < 0

    def test_worsening_trend(self):
        points = _make_points(12, base_kg=3000, monthly_change=300)
        result = analyse_trend(points)
        assert result.direction == "worsening"
        assert result.slope_kg_per_month > 0

    def test_stable_trend(self):
        points = _make_points(12, base_kg=5000, monthly_change=0)
        result = analyse_trend(points)
        assert result.direction == "stable"

    def test_insufficient_data(self):
        points = [TrendPoint("2024-01-01", 5000.0, 50)]
        result = analyse_trend(points)
        assert result.confidence == "low"
        assert "Insufficient" in result.summary

    def test_high_confidence_with_enough_data(self):
        points = _make_points(10, base_kg=5000, monthly_change=-150)
        result = analyse_trend(points)
        assert result.confidence in ("medium", "high")
        assert result.r_squared > 0.5

    def test_r_squared_bounded(self):
        points = _make_points(8)
        result = analyse_trend(points)
        assert 0.0 <= result.r_squared <= 1.0

    def test_slope_per_month_conversion(self):
        points = _make_points(5, base_kg=5000, monthly_change=-100)
        result = analyse_trend(points)
        assert result.slope_kg_per_month != 0.0


# ── detect_seasonal_pattern ─────────────────────────────────────────────────

class TestDetectSeasonalPattern:
    def test_insufficient_data_returns_none(self):
        points = _make_points(3)
        assert detect_seasonal_pattern(points) is None

    def test_all_same_month_returns_none(self):
        from datetime import datetime, timedelta
        points = [
            TrendPoint(f"2024-01-{d:02d} 10:00:00", 5000 + i * 100, 50)
            for i, d in enumerate(range(1, 15))
        ]
        assert detect_seasonal_pattern(points) is None

    def test_seasonal_pattern_detected(self):
        # Create data with clear seasonal pattern
        from datetime import datetime, timedelta
        points = []
        for year in range(2):
            for month in range(1, 13):
                # Higher in summer, lower in winter
                base = 5000 + 1000 * math.sin((month - 1) * math.pi / 6)
                dt = datetime(2023 + year, month, 15)
                points.append(TrendPoint(
                    timestamp=dt.strftime("%Y-%m-%d %H:%M:%S"),
                    footprint_kg=round(base, 1), eco_score=50,
                ))
        result = detect_seasonal_pattern(points)
        assert result is not None
        assert result.peak_month  # Non-empty
        assert result.trough_month  # Non-empty
        assert result.amplitude_kg > 0


# ── detect_anomalies ────────────────────────────────────────────────────────

class TestDetectAnomalies:
    def test_no_anomalies_in平稳_data(self):
        points = _make_points(20, base_kg=5000, monthly_change=0)
        anomalies = detect_anomalies(points)
        assert len(anomalies) == 0

    def test_spike_detected(self):
        points = _make_points(15, base_kg=5000, monthly_change=0)
        # Insert a spike
        points[10] = TrendPoint(points[10].timestamp, 9000.0, 20)
        anomalies = detect_anomalies(points)
        assert len(anomalies) >= 1
        spike = [a for a in anomalies if a.direction == "spike"]
        assert len(spike) >= 1

    def test_dip_detected(self):
        points = _make_points(15, base_kg=5000, monthly_change=0)
        points[10] = TrendPoint(points[10].timestamp, 1000.0, 80)
        anomalies = detect_anomalies(points)
        dips = [a for a in anomalies if a.direction == "dip"]
        assert len(dips) >= 1

    def test_insufficient_data(self):
        points = _make_points(3)
        anomalies = detect_anomalies(points)
        assert len(anomalies) == 0

    def test_anomaly_has_all_fields(self):
        points = _make_points(15, base_kg=5000, monthly_change=0)
        points[7] = TrendPoint(points[7].timestamp, 9500.0, 10)
        anomalies = detect_anomalies(points)
        if anomalies:
            a = anomalies[0]
            assert a.timestamp
            assert a.severity in ("mild", "moderate", "severe")
            assert a.direction in ("spike", "dip")

    def test_threshold_adjusts_sensitivity(self):
        points = _make_points(15, base_kg=5000, monthly_change=0)
        points[10] = TrendPoint(points[10].timestamp, 7000.0, 30)
        strict = detect_anomalies(points, threshold_std=1.0)
        loose = detect_anomalies(points, threshold_std=3.0)
        assert len(strict) >= len(loose)


# ── project_forecast ─────────────────────────────────────────────────────────

class TestProjectForecast:
    def test_returns_correct_number_of_forecasts(self):
        points = _make_points(10)
        forecasts = project_forecast(points, months_ahead=[3, 6, 12])
        assert len(forecasts) == 3

    def test_decreasing_trend_projects_lower(self):
        points = _make_points(10, base_kg=5000, monthly_change=-200)
        forecasts = project_forecast(points)
        assert forecasts[0].predicted_kg < 5000
        # Later forecasts should be even lower
        assert forecasts[-1].predicted_kg <= forecasts[0].predicted_kg

    def test_increasing_trend_projects_higher(self):
        points = _make_points(10, base_kg=3000, monthly_change=200)
        forecasts = project_forecast(points)
        assert forecasts[0].predicted_kg > 3000

    def test_confidence_interval_widens(self):
        points = _make_points(10)
        forecasts = project_forecast(points)
        for i in range(1, len(forecasts)):
            ci_prev = forecasts[i-1].confidence_high_kg - forecasts[i-1].confidence_low_kg
            ci_curr = forecasts[i].confidence_high_kg - forecasts[i].confidence_low_kg
            assert ci_curr >= ci_prev

    def test_insufficient_data(self):
        forecasts = project_forecast([TrendPoint("2024-01-01", 5000, 50)])
        assert all(f.trend_basis == "insufficient_data" for f in forecasts)

    def test_forecast_never_negative(self):
        points = _make_points(10, base_kg=500, monthly_change=-100)
        forecasts = project_forecast(points)
        for f in forecasts:
            assert f.predicted_kg >= 0


# ── predict_milestones ──────────────────────────────────────────────────────

class TestPredictMilestones:
    def test_already_achieved(self):
        points = _make_points(10, base_kg=2000, monthly_change=0)
        milestones = predict_milestones(points, targets=[3000.0])
        assert milestones[0].achievable is True
        assert milestones[0].months_to_reach == 0.0

    def test_will_reach_target(self):
        points = _make_points(10, base_kg=5000, monthly_change=-200)
        milestones = predict_milestones(points, targets=[3000.0])
        assert milestones[0].achievable is True
        assert milestones[0].months_to_reach is not None
        assert milestones[0].months_to_reach > 0

    def test_wont_reach_flat_trend(self):
        points = _make_points(10, base_kg=5000, monthly_change=0)
        milestones = predict_milestones(points, targets=[3000.0])
        assert milestones[0].achievable is False

    def test_insufficient_data(self):
        points = [TrendPoint("2024-01-01", 5000, 50)]
        milestones = predict_milestones(points)
        assert all(not m.achievable for m in milestones)

    def test_multiple_targets(self):
        points = _make_points(10, base_kg=5000, monthly_change=-300)
        milestones = predict_milestones(points, targets=[4000, 3000, 2000])
        assert len(milestones) == 3

    def test_milestone_has_date(self):
        points = _make_points(10, base_kg=5000, monthly_change=-200)
        milestones = predict_milestones(points, targets=[3000.0])
        m = milestones[0]
        if m.achievable and m.months_to_reach and m.months_to_reach > 0:
            assert m.date_reached  # Non-empty


# ── assess_trajectory ───────────────────────────────────────────────────────

class TestAssessTrajectory:
    def test_on_track(self):
        points = _make_points(5, base_kg=2000, monthly_change=0)
        result = assess_trajectory(points, target_kg=2700)
        assert result["status"] == "on_track"

    def test_close(self):
        points = _make_points(5, base_kg=3000, monthly_change=0)
        result = assess_trajectory(points, target_kg=2700)
        assert result["status"] == "close"

    def test_behind(self):
        points = _make_points(5, base_kg=4000, monthly_change=0)
        result = assess_trajectory(points, target_kg=2700)
        assert result["status"] == "behind"

    def test_far_behind(self):
        points = _make_points(5, base_kg=8000, monthly_change=0)
        result = assess_trajectory(points, target_kg=2700)
        assert result["status"] == "far_behind"

    def test_no_data(self):
        result = assess_trajectory([], target_kg=2700)
        assert result["status"] == "no_data"

    def test_has_monthly_change(self):
        points = _make_points(5, base_kg=5000, monthly_change=-100)
        result = assess_trajectory(points, target_kg=2700)
        assert result["avg_monthly_change_kg"] is not None


# ── build_forecast_report ───────────────────────────────────────────────────

class TestBuildForecastReport:
    def test_returns_forecast_report(self):
        rows = _make_rows(10)
        report = build_forecast_report(rows)
        assert isinstance(report, ForecastReport)

    def test_populated_report(self):
        rows = _make_rows(12)
        report = build_forecast_report(rows)
        assert report.data_points == 12
        assert report.trend.direction in ("improving", "worsening", "stable")
        assert len(report.forecasts) == 4  # default [3,6,12,24]
        assert len(report.milestones) == 5  # default targets
        assert report.generated_at

    def test_empty_report(self):
        report = build_forecast_report([])
        assert report.data_points == 0
        assert len(report.forecasts) == 0

    def test_report_has_date_range(self):
        rows = _make_rows(5)
        report = build_forecast_report(rows)
        assert report.date_range[0]  # Non-empty
        assert report.date_range[1]  # Non-empty


# ── Utility helpers ─────────────────────────────────────────────────────────

class TestUtilityHelpers:
    def test_trend_arrow(self):
        assert trend_arrow("improving") == "📉"
        assert trend_arrow("worsening") == "📈"
        assert trend_arrow("stable") == "➡️"
        assert trend_arrow("unknown") == "❓"

    def test_severity_color(self):
        assert severity_color("mild") == "#f59e0b"
        assert severity_color("moderate") == "#f97316"
        assert severity_color("severe") == "#ef4444"

    def test_confidence_color(self):
        assert confidence_color("high") == "#22c55e"
        assert confidence_color("medium") == "#eab308"
        assert confidence_color("low") == "#ef4444"

    def test_format_months_none(self):
        assert format_months(None) == "Unknown"

    def test_format_months_zero(self):
        assert format_months(0) == "Now"

    def test_format_months_days(self):
        assert "days" in format_months(0.5)

    def test_format_months_years(self):
        assert "years" in format_months(24)
