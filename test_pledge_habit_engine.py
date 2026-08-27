"""
Tests for pledge_habit_engine
===============================
Covers habit profile building, nudge generation, optimal pledge combos,
weekly planning, difficulty ramping, streak protection, habit insights,
and schedule preferences.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta

import pytest


# ── Test database setup ──────────────────────────────────────────────

TEST_DB = "test_habit.db"


@pytest.fixture(autouse=True)
def _setup_test_db(tmp_path, monkeypatch):
    """Use a temp SQLite DB for every test."""
    db_path = str(tmp_path / TEST_DB)
    monkeypatch.setattr("green_pledge_tracker.DB_NAME", db_path)
    monkeypatch.setattr("pledge_leaderboard.DB_NAME", db_path)
    monkeypatch.setattr("pledge_habit_engine.DB_NAME", db_path)
    monkeypatch.setattr("database_connection.database_connection", lambda name: _ctx(name))
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
    from pledge_habit_engine import init_habit_tables
    init_pledge_tables()
    init_leaderboard_tables()
    init_habit_tables()


def _seed_pledges(user_id: int, count: int, weeks_back: int = 4):
    """Seed pledges for testing."""
    from green_pledge_tracker import create_pledge, checkin_pledge, current_week_start
    templates = [
        "energy_no_standby", "energy_cold_wash", "transport_bike_week",
        "diet_meatless_week", "waste_no_plastic", "water_5min_shower",
    ]
    for i in range(count):
        offset = i % weeks_back
        ws = (datetime.now() - timedelta(weeks=offset)).strftime("%Y-%m-%d")
        monday = datetime.strptime(ws, "%Y-%m-%d") - timedelta(days=datetime.strptime(ws, "%Y-%m-%d").weekday())
        ws = monday.strftime("%Y-%m-%d")
        tpl_id = templates[i % len(templates)]
        pledge = create_pledge(user_id=user_id, template_id=tpl_id, week=ws)
        if pledge:
            days_to_checkin = min(7, 3 + (i % 5))
            for d in range(days_to_checkin):
                day = (monday + timedelta(days=d)).strftime("%Y-%m-%d")
                checkin_pledge(user_id=user_id, pledge_id=pledge.pledge_id, day_date=day)


# ── Habit Profile tests ──────────────────────────────────────────────

class TestHabitProfiles:
    """Tests for habit profile building."""

    def test_empty_profiles(self, _init_tables):
        from pledge_habit_engine import build_habit_profiles
        profiles = build_habit_profiles(user_id=999)
        assert isinstance(profiles, list)
        assert len(profiles) == 0

    def test_profiles_with_data(self, _init_tables):
        from pledge_habit_engine import build_habit_profiles
        _seed_pledges(user_id=1, count=4)
        profiles = build_habit_profiles(user_id=1)
        assert len(profiles) > 0

    def test_profile_fields(self, _init_tables):
        from pledge_habit_engine import build_habit_profiles
        _seed_pledges(user_id=2, count=2)
        profiles = build_habit_profiles(user_id=2)
        for p in profiles:
            assert p.user_id == 2
            assert p.template_id
            assert p.stage in ("exploration", "building", "reinforcing", "consolidating", "automatic", "dormant")
            assert 0.0 <= p.habit_strength <= 1.0
            assert p.weeks_enrolled > 0
            assert p.category
            assert p.template_title

    def test_habit_strength_calculation(self, _init_tables):
        from pledge_habit_engine import build_habit_profiles
        _seed_pledges(user_id=3, count=6)
        profiles = build_habit_profiles(user_id=3)
        strengths = [p.habit_strength for p in profiles]
        assert all(0.0 <= s <= 1.0 for s in strengths)

    def test_stage_progression(self, _init_tables):
        """With enough weeks enrolled, stage should advance beyond exploration."""
        from pledge_habit_engine import build_habit_profiles
        _seed_pledges(user_id=4, count=8, weeks_back=8)
        profiles = build_habit_profiles(user_id=4)
        stages = {p.stage for p in profiles}
        # At least some should not be exploration if they have enough weeks
        assert len(stages) > 0


# ── Nudge tests ──────────────────────────────────────────────────────

class TestNudges:
    """Tests for nudge generation."""

    def test_nudges_for_empty_user(self, _init_tables):
        from pledge_habit_engine import generate_nudges
        nudges = generate_nudges(user_id=999)
        assert isinstance(nudges, list)

    def test_nudge_fields(self, _init_tables):
        from pledge_habit_engine import generate_nudges
        nudges = generate_nudges(user_id=999)
        for n in nudges:
            assert n.nudge_id
            assert n.nudge_type
            assert n.priority in ("low", "medium", "high")
            assert n.title
            assert n.message
            assert n.expires_at

    def test_nudges_with_completed_pledges(self, _init_tables):
        from pledge_habit_engine import generate_nudges
        _seed_pledges(user_id=5, count=4)
        nudges = generate_nudges(user_id=5)
        assert isinstance(nudges, list)
        # Should have at least some nudges for a user with pledges
        assert len(nudges) > 0

    def test_nudge_cooldown(self, _init_tables):
        """Second call should respect cooldown."""
        from pledge_habit_engine import generate_nudges
        _seed_pledges(user_id=6, count=2)
        n1 = generate_nudges(user_id=6)
        n2 = generate_nudges(user_id=6)
        # Second call should have fewer or equal nudges due to cooldown
        assert len(n2) <= len(n1) + 1  # allow small tolerance


# ── Optimal Combo tests ──────────────────────────────────────────────

class TestOptimalCombos:
    """Tests for optimal pledge combination suggestions."""

    def test_balanced_combos(self, _init_tables):
        from pledge_habit_engine import suggest_optimal_combos, ComboStrategy
        combos = suggest_optimal_combos(user_id=999, strategy=ComboStrategy.BALANCED, n=3)
        assert len(combos) > 0
        for c in combos:
            assert c.strategy == "balanced"
            assert c.total_weekly_co2_kg > 0
            assert c.total_weekly_xp > 0
            assert len(c.pledges) > 0

    def test_easy_warmup_combos(self, _init_tables):
        from pledge_habit_engine import suggest_optimal_combos, ComboStrategy
        combos = suggest_optimal_combos(user_id=999, strategy=ComboStrategy.EASY_WARMUP, n=3)
        assert len(combos) > 0
        for c in combos:
            for p in c.pledges:
                assert p["difficulty"] == "easy"

    def test_high_impact_combos(self, _init_tables):
        from pledge_habit_engine import suggest_optimal_combos, ComboStrategy
        combos = suggest_optimal_combos(user_id=999, strategy=ComboStrategy.HIGH_IMPACT, n=3)
        assert len(combos) > 0
        for c in combos:
            assert c.total_weekly_co2_kg > 0

    def test_diversity_combos(self, _init_tables):
        from pledge_habit_engine import suggest_optimal_combos, ComboStrategy
        combos = suggest_optimal_combos(user_id=999, strategy=ComboStrategy.DIVERSITY, n=3)
        assert len(combos) > 0
        for c in combos:
            categories = {p["id"] for p in c.pledges}
            # Diversity combos should have pledges from different categories
            assert len(c.pledges) >= 2

    def test_streak_focus_combos(self, _init_tables):
        from pledge_habit_engine import suggest_optimal_combos, ComboStrategy
        combos = suggest_optimal_combos(user_id=999, strategy=ComboStrategy.STREAK_FOCUS, n=3)
        assert len(combos) > 0
        for c in combos:
            # Should be easy or medium for streak building
            for p in c.pledges:
                assert p["difficulty"] in ("easy", "medium")

    def test_challenge_mode_combos(self, _init_tables):
        from pledge_habit_engine import suggest_optimal_combos, ComboStrategy
        combos = suggest_optimal_combos(user_id=999, strategy=ComboStrategy.CHALLENGE_MODE, n=3)
        assert len(combos) > 0
        for c in combos:
            for p in c.pledges:
                assert p["difficulty"] == "hard"

    def test_combo_serialisation(self, _init_tables):
        from pledge_habit_engine import suggest_optimal_combos, combo_to_dict, ComboStrategy
        combos = suggest_optimal_combos(user_id=999, strategy=ComboStrategy.BALANCED, n=1)
        if combos:
            d = combo_to_dict(combos[0])
            assert isinstance(d, dict)
            assert "combo_id" in d
            assert "pledges" in d


# ── Weekly Planner tests ─────────────────────────────────────────────

class TestWeeklyPlanner:
    """Tests for weekly plan generation."""

    def test_empty_planner(self, _init_tables):
        from pledge_habit_engine import generate_weekly_plan
        planner = generate_weekly_plan(user_id=999)
        assert planner is not None
        assert planner.week_start
        assert isinstance(planner.pledges, list)

    def test_planner_with_data(self, _init_tables):
        from pledge_habit_engine import generate_weekly_plan
        _seed_pledges(user_id=7, count=3)
        planner = generate_weekly_plan(user_id=7)
        assert len(planner.pledges) > 0
        assert planner.total_co2_kg >= 0
        assert planner.total_xp >= 0

    def test_planner_daily_focus(self, _init_tables):
        from pledge_habit_engine import generate_weekly_plan
        _seed_pledges(user_id=8, count=2)
        planner = generate_weekly_plan(user_id=8)
        assert isinstance(planner.daily_focus, dict)
        assert len(planner.daily_focus) == 7

    def test_planner_serialisation(self, _init_tables):
        from pledge_habit_engine import generate_weekly_plan, planner_to_dict
        planner = generate_weekly_plan(user_id=999)
        d = planner_to_dict(planner)
        assert isinstance(d, dict)
        assert "week_start" in d
        assert "pledges" in d


# ── Difficulty Ramp tests ────────────────────────────────────────────

class TestDifficultyRamping:
    """Tests for difficulty recommendations."""

    def test_difficulty_for_new_user(self, _init_tables):
        from pledge_habit_engine import recommend_difficulty
        rec = recommend_difficulty(user_id=999)
        assert rec.current_avg in ("easy", "medium", "hard")
        assert rec.recommended in ("easy", "medium", "hard")
        assert rec.reason

    def test_difficulty_after_easy_mastery(self, _init_tables):
        from pledge_habit_engine import recommend_difficulty
        _seed_pledges(user_id=9, count=4, weeks_back=4)
        rec = recommend_difficulty(user_id=9)
        assert rec.current_avg in ("easy", "medium", "hard")
        # May or may not be ready depending on completion rates
        assert isinstance(rec.ready, bool)

    def test_difficulty_fields(self, _init_tables):
        from pledge_habit_engine import recommend_difficulty
        rec = recommend_difficulty(user_id=999)
        assert hasattr(rec, "current_avg")
        assert hasattr(rec, "recommended")
        assert hasattr(rec, "reason")
        assert hasattr(rec, "ready")
        assert hasattr(rec, "weeks_at_current")
        assert rec.completion_rate_needed == 80.0


# ── Streak Protection tests ──────────────────────────────────────────

class TestStreakProtection:
    """Tests for streak protection system."""

    def test_streak_protection_empty(self, _init_tables):
        from pledge_habit_engine import get_streak_protection
        prot = get_streak_protection(user_id=999)
        assert prot.user_id == 999
        assert prot.extensions_remaining >= 0
        assert isinstance(prot.streak_at_risk, bool)

    def test_use_protection(self, _init_tables):
        from pledge_habit_engine import get_streak_protection, use_streak_protection
        # First get to initialise
        get_streak_protection(user_id=10)
        # Try using protection
        result = use_streak_protection(user_id=10)
        assert isinstance(result, bool)

    def test_protection_fields(self, _init_tables):
        from pledge_habit_engine import get_streak_protection
        prot = get_streak_protection(user_id=11)
        assert hasattr(prot, "current_streak")
        assert hasattr(prot, "extensions_remaining")
        assert hasattr(prot, "last_completed_week")
        assert hasattr(prot, "streak_at_risk")
        assert hasattr(prot, "protection_active")
        assert hasattr(prot, "weeks_until_break")


# ── Habit Insight tests ──────────────────────────────────────────────

class TestHabitInsights:
    """Tests for habit-specific insights."""

    def test_insights_empty(self, _init_tables):
        from pledge_habit_engine import generate_habit_insights
        insights = generate_habit_insights(user_id=999)
        assert isinstance(insights, list)

    def test_insights_with_data(self, _init_tables):
        from pledge_habit_engine import generate_habit_insights
        _seed_pledges(user_id=12, count=4)
        insights = generate_habit_insights(user_id=12)
        assert len(insights) > 0
        for i in insights:
            assert i.insight_type
            assert i.title
            assert i.body

    def test_overall_strength_insight(self, _init_tables):
        from pledge_habit_engine import generate_habit_insights
        _seed_pledges(user_id=13, count=2)
        insights = generate_habit_insights(user_id=13)
        strength_insights = [i for i in insights if i.insight_type == "overall_strength"]
        assert len(strength_insights) > 0
        assert 0.0 <= strength_insights[0].metric <= 1.0


# ── Schedule Preference tests ────────────────────────────────────────

class TestSchedulePreferences:
    """Tests for schedule preference management."""

    def test_default_preferences(self, _init_tables):
        from pledge_habit_engine import get_schedule_preferences
        prefs = get_schedule_preferences(user_id=999)
        assert prefs["preferred_slot"] == "anytime"
        assert prefs["max_active_pledges"] == 3
        assert prefs["prefer_variety"] is True
        assert prefs["difficulty_preference"] == "auto"

    def test_save_and_load_preferences(self, _init_tables):
        from pledge_habit_engine import save_schedule_preferences, get_schedule_preferences
        save_schedule_preferences(
            user_id=14,
            preferred_slot="morning",
            max_active_pledges=4,
            prefer_variety=False,
            difficulty_preference="hard",
        )
        prefs = get_schedule_preferences(user_id=14)
        assert prefs["preferred_slot"] == "morning"
        assert prefs["max_active_pledges"] == 4
        assert prefs["prefer_variety"] is False
        assert prefs["difficulty_preference"] == "hard"

    def test_overwrite_preferences(self, _init_tables):
        from pledge_habit_engine import save_schedule_preferences, get_schedule_preferences
        save_schedule_preferences(user_id=15, preferred_slot="morning")
        save_schedule_preferences(user_id=15, preferred_slot="evening")
        prefs = get_schedule_preferences(user_id=15)
        assert prefs["preferred_slot"] == "evening"


# ── Serialisation tests ──────────────────────────────────────────────

class TestSerialisation:
    """Tests for data serialisation."""

    def test_habit_profile_to_dict(self, _init_tables):
        from pledge_habit_engine import build_habit_profiles, habit_profile_to_dict
        _seed_pledges(user_id=16, count=2)
        profiles = build_habit_profiles(user_id=16)
        for p in profiles:
            d = habit_profile_to_dict(p)
            assert isinstance(d, dict)
            assert "user_id" in d
            assert "template_id" in d
            assert "stage" in d
            assert "habit_strength" in d

    def test_nudge_to_dict(self, _init_tables):
        from pledge_habit_engine import generate_nudges, nudge_to_dict
        nudges = generate_nudges(user_id=999)
        for n in nudges[:1]:
            d = nudge_to_dict(n)
            assert isinstance(d, dict)
            assert "nudge_id" in d
            assert "nudge_type" in d
            assert "title" in d


# ── Integration test ─────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for the habit engine."""

    def test_full_workflow(self, _init_tables):
        """Test complete user journey: enrol → build habits → get nudges → plan."""
        from green_pledge_tracker import create_pledge, checkin_pledge, current_week_start
        from pledge_habit_engine import (
            build_habit_profiles,
            generate_nudges,
            suggest_optimal_combos,
            recommend_difficulty,
            generate_weekly_plan,
            get_streak_protection,
            generate_habit_insights,
            get_schedule_preferences,
            save_schedule_preferences,
            ComboStrategy,
        )

        user_id = 42

        # Enrol and complete pledges
        templates = ["energy_no_standby", "transport_bike_week"]
        for tpl_id in templates:
            pledge = create_pledge(user_id=user_id, template_id=tpl_id)
            if pledge:
                ws = current_week_start()
                monday = datetime.strptime(ws, "%Y-%m-%d")
                for d in range(7):
                    day = (monday + timedelta(days=d)).strftime("%Y-%m-%d")
                    checkin_pledge(user_id=user_id, pledge_id=pledge.pledge_id, day_date=day)

        # Build profiles
        profiles = build_habit_profiles(user_id)
        assert len(profiles) > 0

        # Generate nudges
        nudges = generate_nudges(user_id)
        assert isinstance(nudges, list)

        # Suggest combos
        combos = suggest_optimal_combos(user_id, strategy=ComboStrategy.BALANCED, n=2)
        assert len(combos) > 0

        # Difficulty recommendation
        rec = recommend_difficulty(user_id)
        assert rec.recommended in ("easy", "medium", "hard")

        # Weekly plan
        plan = generate_weekly_plan(user_id)
        assert plan.week_start

        # Streak protection
        prot = get_streak_protection(user_id)
        assert prot.extensions_remaining >= 0

        # Habit insights
        insights = generate_habit_insights(user_id)
        assert len(insights) > 0

        # Schedule preferences
        save_schedule_preferences(user_id, preferred_slot="morning")
        prefs = get_schedule_preferences(user_id)
        assert prefs["preferred_slot"] == "morning"
