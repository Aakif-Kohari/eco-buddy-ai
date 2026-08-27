"""
Tests for pledge_impact_engine
================================
Covers weekly impact aggregation, trend analysis, prediction,
milestone tracking, insight generation, category breakdowns,
comparison reports, and full impact report generation.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
from datetime import datetime, timedelta

import pytest


# ── Test database setup ──────────────────────────────────────────────

TEST_DB = "test_impact.db"


@pytest.fixture(autouse=True)
def _setup_test_db(tmp_path, monkeypatch):
    """Use a temp SQLite DB for every test."""
    db_path = str(tmp_path / TEST_DB)
    monkeypatch.setattr("src.utils.green_pledge_tracker.DB_NAME", db_path)
    monkeypatch.setattr("src.community.pledge_leaderboard.DB_NAME", db_path)
    monkeypatch.setattr("src.community.pledge_impact_engine.DB_NAME", db_path)
    monkeypatch.setattr("src.core.database_connection.database_connection", lambda name: _ctx(name))
    yield db_path


class _ctx:
    def __init__(self, name):
        self._conn = sqlite3.connect(name)
        self._conn.row_factory = sqlite3.Row
    def __enter__(self):
        return self._conn
    def __exit__(self, *a):
        self._conn.close()


@pytest.fixture
def _init_tables(_setup_test_db):
    """Create all required tables."""
    from green_pledge_tracker import init_pledge_tables
    from pledge_leaderboard import init_leaderboard_tables
    from pledge_impact_engine import init_impact_tables
    init_pledge_tables()
    init_leaderboard_tables()
    init_impact_tables()


def _seed_completed_pledges(user_id: int, count: int, weeks_back: int = 4):
    """Seed completed pledges for testing."""
    from green_pledge_tracker import create_pledge, checkin_pledge, current_week_start
    templates = [
        "energy_no_standby", "energy_cold_wash", "transport_bike_week",
        "diet_meatless_week", "waste_no_plastic", "water_5min_shower",
    ]
    for i in range(count):
        offset = i // 2  # spread across weeks
        ws = (datetime.now() - timedelta(weeks=offset)).strftime("%Y-%m-%d")
        monday = datetime.strptime(ws, "%Y-%m-%d") - timedelta(days=datetime.strptime(ws, "%Y-%m-%d").weekday())
        ws = monday.strftime("%Y-%m-%d")
        tpl_id = templates[i % len(templates)]
        pledge = create_pledge(user_id=user_id, template_id=tpl_id, week=ws)
        if pledge:
            for day_offset in range(7):
                day = (monday + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                checkin_pledge(user_id=user_id, pledge_id=pledge.pledge_id, day_date=day)


# ── Weekly Impact tests ──────────────────────────────────────────────

class TestWeeklyImpacts:
    """Tests for weekly impact aggregation."""

    def test_empty_weekly_impacts(self, _init_tables):
        from pledge_impact_engine import get_weekly_impacts
        impacts = get_weekly_impacts(user_id=999, weeks=4)
        assert isinstance(impacts, list)
        assert len(impacts) == 4

    def test_weekly_impacts_with_data(self, _init_tables):
        from pledge_impact_engine import get_weekly_impacts
        _seed_completed_pledges(user_id=1, count=4)
        impacts = get_weekly_impacts(user_id=1, weeks=8)
        active = [w for w in impacts if w.pledges_enrolled > 0]
        assert len(active) > 0

    def test_weekly_impact_fields(self, _init_tables):
        from pledge_impact_engine import get_weekly_impacts
        _seed_completed_pledges(user_id=2, count=2)
        impacts = get_weekly_impacts(user_id=2, weeks=4)
        for w in impacts:
            assert hasattr(w, "week_start")
            assert hasattr(w, "co2_saved_kg")
            assert hasattr(w, "xp_earned")
            assert hasattr(w, "categories_touched")
            assert hasattr(w, "difficulty_mix")


# ── Trend Analysis tests ─────────────────────────────────────────────

class TestTrendAnalysis:
    """Tests for trend analysis."""

    def test_insufficient_data(self, _init_tables):
        from pledge_impact_engine import analyse_trend, TrendDirection
        trend = analyse_trend(user_id=999)
        assert trend.direction == TrendDirection.INSUFFICIENT

    def test_trend_with_data(self, _init_tables):
        from pledge_impact_engine import analyse_trend
        _seed_completed_pledges(user_id=3, count=6)
        trend = analyse_trend(user_id=3)
        assert trend.direction in ("improving", "stable", "declining", "insufficient_data")
        assert 0.0 <= trend.confidence <= 1.0
        assert isinstance(trend.moving_average, list)
        assert isinstance(trend.forecast, list)
        assert len(trend.forecast) == 12

    def test_trend_forecast_has_future_weeks(self, _init_tables):
        from pledge_impact_engine import analyse_trend
        _seed_completed_pledges(user_id=4, count=4)
        trend = analyse_trend(user_id=4)
        for fc in trend.forecast:
            assert "week_offset" in fc
            assert "predicted_co2_kg" in fc
            assert fc["predicted_co2_kg"] >= 0

    def test_moving_average_length(self, _init_tables):
        from pledge_impact_engine import analyse_trend
        _seed_completed_pledges(user_id=5, count=6)
        trend = analyse_trend(user_id=5, weeks=8)
        if trend.moving_average:
            assert len(trend.moving_average) <= 8


# ── Prediction tests ─────────────────────────────────────────────────

class TestPrediction:
    """Tests for impact prediction."""

    def test_empty_prediction(self, _init_tables):
        from pledge_impact_engine import predict_future_impact
        pred = predict_future_impact(user_id=999)
        assert pred.predicted_co2_12w == 0.0
        assert pred.predicted_xp_12w == 0

    def test_prediction_with_data(self, _init_tables):
        from pledge_impact_engine import predict_future_impact
        _seed_completed_pledges(user_id=6, count=6)
        pred = predict_future_impact(user_id=6)
        assert pred.predicted_co2_12w > 0
        assert pred.predicted_xp_12w > 0
        assert pred.predicted_pledges_12w > 0

    def test_prediction_scenarios(self, _init_tables):
        from pledge_impact_engine import predict_future_impact
        _seed_completed_pledges(user_id=7, count=4)
        pred = predict_future_impact(user_id=7)
        assert "co2_kg" in pred.scenario_better
        assert "co2_kg" in pred.scenario_worse
        assert pred.scenario_better["co2_kg"] >= pred.scenario_worse["co2_kg"]

    def test_prediction_confidence_interval(self, _init_tables):
        from pledge_impact_engine import predict_future_impact
        _seed_completed_pledges(user_id=8, count=4)
        pred = predict_future_impact(user_id=8)
        assert "lower" in pred.confidence_interval
        assert "upper" in pred.confidence_interval
        assert pred.confidence_interval["lower"] <= pred.confidence_interval["upper"]


# ── Milestone tests ──────────────────────────────────────────────────

class TestMilestones:
    """Tests for milestone tracking."""

    def test_milestones_empty_user(self, _init_tables):
        from pledge_impact_engine import check_milestones
        milestones = check_milestones(user_id=999)
        assert isinstance(milestones, list)
        assert len(milestones) > 0
        # No milestones achieved for empty user
        achieved = [m for m in milestones if m.achieved]
        assert len(achieved) == 0

    def test_first_pledge_milestone(self, _init_tables):
        from pledge_impact_engine import check_milestones
        _seed_completed_pledges(user_id=10, count=1)
        milestones = check_milestones(user_id=10)
        achieved = [m for m in milestones if m.achieved]
        assert len(achieved) >= 1
        types = {m.milestone_type for m in achieved}
        assert "first_pledge" in types

    def test_co2_milestones(self, _init_tables):
        from pledge_impact_engine import check_milestones
        _seed_completed_pledges(user_id=11, count=6)
        milestones = check_milestones(user_id=11)
        achieved = [m for m in milestones if m.achieved]
        types = {m.milestone_type for m in achieved}
        assert "first_pledge" in types
        assert "perfect_week" in types

    def test_get_user_milestones(self, _init_tables):
        from pledge_impact_engine import check_milestones, get_user_milestones
        _seed_completed_pledges(user_id=12, count=1)
        check_milestones(user_id=12)
        history = get_user_milestones(user_id=12)
        assert len(history) >= 1
        assert "title" in history[0]
        assert "achieved_at" in history[0]


# ── Insight tests ────────────────────────────────────────────────────

class TestInsights:
    """Tests for insight generation."""

    def test_insights_for_empty_user(self, _init_tables):
        from pledge_impact_engine import generate_insights
        insights = generate_insights(user_id=999)
        assert isinstance(insights, list)
        assert len(insights) > 0  # should still generate some insights

    def test_insight_fields(self, _init_tables):
        from pledge_impact_engine import generate_insights
        insights = generate_insights(user_id=999)
        for i in insights:
            assert i.insight_id
            assert i.category in ("streak", "category", "difficulty", "consistency",
                                   "impact", "social", "opportunity", "milestone")
            assert i.priority in ("low", "medium", "high", "celebration")
            assert i.title
            assert i.body

    def test_insights_with_completed_pledges(self, _init_tables):
        from pledge_impact_engine import generate_insights
        _seed_completed_pledges(user_id=13, count=6)
        insights = generate_insights(user_id=13)
        assert len(insights) > 0

    def test_social_insight_for_no_group(self, _init_tables):
        from pledge_impact_engine import generate_insights
        insights = generate_insights(user_id=14)
        social = [i for i in insights if i.category == "social"]
        assert len(social) > 0  # should suggest joining a group


# ── Category Breakdown tests ─────────────────────────────────────────

class TestCategoryBreakdown:
    """Tests for category breakdown."""

    def test_empty_breakdown(self, _init_tables):
        from pledge_impact_engine import get_category_breakdown
        breakdown = get_category_breakdown(user_id=999)
        assert isinstance(breakdown, list)
        assert len(breakdown) > 0  # returns all categories even if empty

    def test_breakdown_with_data(self, _init_tables):
        from pledge_impact_engine import get_category_breakdown
        _seed_completed_pledges(user_id=15, count=4)
        breakdown = get_category_breakdown(user_id=15)
        active = [cb for cb in breakdown if cb.total_enrolled > 0]
        assert len(active) > 0
        for cb in active:
            assert cb.completion_rate >= 0
            assert cb.co2_saved_kg >= 0
            assert cb.label

    def test_breakdown_fields(self, _init_tables):
        from pledge_impact_engine import get_category_breakdown
        breakdown = get_category_breakdown(user_id=999)
        for cb in breakdown:
            assert hasattr(cb, "category")
            assert hasattr(cb, "label")
            assert hasattr(cb, "color")
            assert hasattr(cb, "completion_rate")
            assert hasattr(cb, "favorite_pledge")


# ── Comparison Report tests ──────────────────────────────────────────

class TestComparisonReport:
    """Tests for community comparison reports."""

    def test_comparison_empty(self, _init_tables):
        from pledge_impact_engine import generate_comparison_report
        report = generate_comparison_report(user_id=999)
        assert report is not None
        assert isinstance(src.reporting.report.strengths, list)
        assert isinstance(src.reporting.report.improvement_areas, list)

    def test_comparison_with_data(self, _init_tables):
        from pledge_impact_engine import generate_comparison_report
        _seed_completed_pledges(user_id=16, count=4)
        report = generate_comparison_report(user_id=16)
        assert src.reporting.report.percentile_rank >= 0
        assert isinstance(src.reporting.report.vs_community, dict)

    def test_comparison_has_category_data(self, _init_tables):
        from pledge_impact_engine import generate_comparison_report
        report = generate_comparison_report(user_id=999)
        assert isinstance(src.reporting.report.category_comparison, list)


# ── Full Report tests ────────────────────────────────────────────────

class TestFullReport:
    """Tests for full impact report generation."""

    def test_generate_report_empty(self, _init_tables):
        from pledge_impact_engine import generate_full_report
        report = generate_full_report(user_id=999, period_weeks=4)
        assert report is not None
        assert src.reporting.report.user_id == 999
        assert src.reporting.report.period_weeks == 4
        assert src.reporting.report.generated_at
        assert isinstance(src.reporting.report.weekly_data, list)

    def test_generate_report_with_data(self, _init_tables):
        from pledge_impact_engine import generate_full_report
        _seed_completed_pledges(user_id=17, count=6)
        report = generate_full_report(user_id=17, period_weeks=8)
        assert src.reporting.report.total_pledges_completed > 0
        assert src.reporting.report.total_co2_saved_kg > 0
        assert src.reporting.report.trend is not None
        assert src.reporting.report.prediction is not None
        assert len(src.reporting.report.insights) > 0
        assert len(src.reporting.report.milestones) > 0
        assert len(src.reporting.report.weekly_data) == 8

    def test_report_best_worst_week(self, _init_tables):
        from pledge_impact_engine import generate_full_report
        _seed_completed_pledges(user_id=18, count=4)
        report = generate_full_report(user_id=18, period_weeks=4)
        if src.reporting.report.total_pledges_completed > 0:
            assert src.reporting.report.best_week is not None
            assert src.reporting.report.worst_week is not None

    def test_report_persists_to_history(self, _init_tables):
        from pledge_impact_engine import generate_full_report, get_report_history
        generate_full_report(user_id=19, period_weeks=4)
        history = get_report_history(user_id=19)
        assert len(history) >= 1
        assert "total_co2_saved_kg" in history[0]

    def test_export_report_json(self, _init_tables):
        from pledge_impact_engine import export_report_json
        json_str = export_report_json(user_id=999, period_weeks=4)
        data = json.loads(json_str)
        assert "user_id" in data
        assert "weekly_data" in data
        assert "milestones" in data
        assert "insights" in data


# ── Utility tests ────────────────────────────────────────────────────

class TestUtilities:
    """Tests for utility and helper functions."""

    def test_moving_average(self, _init_tables):
        from pledge_impact_engine import _moving_average
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        ma = _moving_average(values, 3)
        assert len(ma) == 3
        assert ma[0] == pytest.approx(2.0)
        assert ma[1] == pytest.approx(3.0)
        assert ma[2] == pytest.approx(4.0)

    def test_moving_average_short_input(self, _init_tables):
        from pledge_impact_engine import _moving_average
        values = [1.0, 2.0]
        ma = _moving_average(values, 3)
        assert ma == [1.0, 2.0]

    def test_impact_report_to_dict(self, _init_tables):
        from pledge_impact_engine import generate_full_report, impact_report_to_dict
        report = generate_full_report(user_id=999, period_weeks=4)
        d = impact_report_to_dict(report)
        assert isinstance(d, dict)
        assert "user_id" in d
        assert "weekly_data" in d

    def test_milestone_definitions_complete(self, _init_tables):
        from pledge_impact_engine import MILESTONE_DEFINITIONS, MilestoneType
        for mtype in MilestoneType:
            assert mtype.value in MILESTONE_DEFINITIONS
            defn = MILESTONE_DEFINITIONS[mtype]
            assert "title" in defn
            assert "description" in defn
            assert "xp_bonus" in defn
            assert defn["xp_bonus"] > 0


# ── Integration test ─────────────────────────────────────────────────

class TestIntegration:
    """Integration tests combining multiple engine components."""

    def test_full_workflow(self, _init_tables):
        """Test a complete user journey: enrol → complete → analyse → src.reporting.report."""
        from green_pledge_tracker import create_pledge, checkin_pledge, current_week_start
        from pledge_impact_engine import (
            get_weekly_impacts,
            analyse_trend,
            predict_future_impact,
            check_milestones,
            generate_insights,
            get_category_breakdown,
            generate_full_report,
        )

        user_id = 42

        # Enrol and complete pledges
        templates = ["energy_no_standby", "transport_bike_week", "diet_meatless_week"]
        for tpl_id in templates:
            pledge = create_pledge(user_id=user_id, template_id=tpl_id)
            if pledge:
                for d in range(7):
                    day = (datetime.strptime(current_week_start(), "%Y-%m-%d") + timedelta(days=d)).strftime("%Y-%m-%d")
                    checkin_pledge(user_id=user_id, pledge_id=pledge.pledge_id, day_date=day)

        # Analyse
        weekly = get_weekly_impacts(user_id, weeks=4)
        assert len(weekly) == 4

        trend = analyse_trend(user_id)
        assert trend.direction in ("improving", "stable", "declining", "insufficient_data")

        prediction = predict_future_impact(user_id)
        assert prediction.predicted_co2_12w >= 0

        milestones = check_milestones(user_id)
        achieved = [m for m in milestones if m.achieved]
        assert len(achieved) > 0

        insights = generate_insights(user_id)
        assert len(insights) > 0

        cats = get_category_breakdown(user_id)
        active = [cb for cb in cats if cb.total_enrolled > 0]
        assert len(active) > 0

        report = generate_full_report(user_id, period_weeks=4)
        assert src.reporting.report.total_pledges_completed > 0
        assert src.reporting.report.total_co2_saved_kg > 0
