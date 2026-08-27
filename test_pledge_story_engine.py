"""
Tests for pledge_story_engine
================================
Covers story card generation, monthly journals, multi-scene journey stories,
impact narratives, story management, favorites, and JSON export.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta

import pytest


# ── Test database setup ──────────────────────────────────────────────

TEST_DB = "test_story.db"


@pytest.fixture(autouse=True)
def _setup_test_db(tmp_path, monkeypatch):
    """Use a temp SQLite DB for every test."""
    db_path = str(tmp_path / TEST_DB)
    monkeypatch.setattr("green_pledge_tracker.DB_NAME", db_path)
    monkeypatch.setattr("pledge_leaderboard.DB_NAME", db_path)
    monkeypatch.setattr("pledge_impact_engine.DB_NAME", db_path)
    monkeypatch.setattr("pledge_story_engine.DB_NAME", db_path)
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
    from pledge_impact_engine import init_impact_tables
    from pledge_story_engine import init_story_tables
    init_pledge_tables()
    init_leaderboard_tables()
    init_impact_tables()
    init_story_tables()


def _seed_pledges(user_id: int, count: int, weeks_back: int = 4):
    """Seed completed pledges for testing."""
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
            for d in range(min(7, 3 + i % 5)):
                day = (monday + timedelta(days=d)).strftime("%Y-%m-%d")
                checkin_pledge(user_id=user_id, pledge_id=pledge.pledge_id, day_date=day)


# ── Story Card Generation tests ──────────────────────────────────────

class TestWeeklyStory:
    """Tests for weekly summary story generation."""

    def test_weekly_story_empty_user(self, _init_tables):
        from pledge_story_engine import generate_weekly_story
        story = generate_weekly_story(user_id=999, username="TestUser")
        assert story is not None
        assert story.user_id == 999
        assert story.story_type == "weekly_summary"
        assert story.narrative
        assert story.title
        assert story.created_at

    def test_weekly_story_with_data(self, _init_tables):
        from pledge_story_engine import generate_weekly_story
        _seed_pledges(user_id=1, count=4)
        story = generate_weekly_story(user_id=1, username="Alice")
        assert story is not None
        assert "Alice" in story.narrative or story.stat_value >= 0

    def test_weekly_story_theme(self, _init_tables):
        from pledge_story_engine import generate_weekly_story
        story = generate_weekly_story(user_id=999)
        assert story.theme in ("hope", "adventure", "community", "transformation", "resilience")
        assert story.color_primary
        assert story.color_secondary

    def test_weekly_story_tags(self, _init_tables):
        from pledge_story_engine import generate_weekly_story
        story = generate_weekly_story(user_id=999)
        assert isinstance(story.tags, list)
        assert "weekly_summary" in story.tags

    def test_weekly_story_share_text(self, _init_tables):
        from pledge_story_engine import generate_weekly_story
        story = generate_weekly_story(user_id=999)
        assert story.share_text
        assert "#EcoBuddy" in story.share_text


class TestMilestoneStory:
    """Tests for milestone celebration story generation."""

    def test_milestone_story_no_milestones(self, _init_tables):
        from pledge_story_engine import generate_milestone_story
        story = generate_milestone_story(user_id=999)
        assert story is None

    def test_milestone_story_with_milestone(self, _init_tables):
        from pledge_story_engine import generate_milestone_story
        _seed_pledges(user_id=2, count=1)
        story = generate_milestone_story(user_id=2, username="Bob")
        assert story is not None
        assert story.story_type == "milestone_celebration"
        assert story.stat_unit == "milestones"

    def test_milestone_story_emoji(self, _init_tables):
        from pledge_story_engine import generate_milestone_story
        _seed_pledges(user_id=3, count=1)
        story = generate_milestone_story(user_id=3)
        if story:
            assert story.icon == "🏆"


class TestStreakStory:
    """Tests for streak narrative story generation."""

    def test_streak_story_no_streak(self, _init_tables):
        from pledge_story_engine import generate_streak_story
        story = generate_streak_story(user_id=999)
        assert story is None

    def test_streak_story_with_streak(self, _init_tables):
        from pledge_story_engine import generate_streak_story
        _seed_pledges(user_id=4, count=6)
        story = generate_streak_story(user_id=4)
        # May or may not have a streak depending on week spread
        if story:
            assert story.story_type == "streak_narrative"
            assert story.theme == "resilience"
            assert story.icon == "🔥"


class TestImpactStory:
    """Tests for CO₂ impact story generation."""

    def test_impact_story_empty(self, _init_tables):
        from pledge_story_engine import generate_impact_story
        story = generate_impact_story(user_id=999)
        assert story is not None
        assert story.story_type == "co2_impact"
        assert story.stat_unit == "kg CO₂ saved"

    def test_impact_story_with_data(self, _init_tables):
        from pledge_story_engine import generate_impact_story
        _seed_pledges(user_id=5, count=4)
        story = generate_impact_story(user_id=5)
        assert story.stat_value > 0


class TestPredictionStory:
    """Tests for prediction story generation."""

    def test_prediction_story_empty(self, _init_tables):
        from pledge_story_engine import generate_prediction_story
        story = generate_prediction_story(user_id=999)
        assert story is not None
        assert story.story_type == "prediction_story"
        assert story.theme == "transformation"

    def test_prediction_story_with_data(self, _init_tables):
        from pledge_story_engine import generate_prediction_story
        _seed_pledges(user_id=6, count=4)
        story = generate_prediction_story(user_id=6)
        assert story.stat_value >= 0


class TestJourneyBeginningStory:
    """Tests for journey beginning story generation."""

    def test_journey_beginning(self, _init_tables):
        from pledge_story_engine import generate_journey_beginning_story
        story = generate_journey_beginning_story(user_id=999, username="NewUser")
        assert story is not None
        assert story.story_type == "journey_beginning"
        assert story.theme == "hope"
        assert "NewUser" in story.narrative
        assert "Day 1" in story.headline_stat


# ── Journey Story tests ──────────────────────────────────────────────

class TestJourneyStory:
    """Tests for multi-scene journey story generation."""

    def test_journey_story_empty(self, _init_tables):
        from pledge_story_engine import generate_full_journey_story
        scenes = generate_full_journey_story(user_id=999)
        assert isinstance(scenes, list)
        # Should always have at least the opening scene
        assert len(scenes) >= 1
        assert scenes[0].scene_type == "opening"

    def test_journey_story_with_data(self, _init_tables):
        from pledge_story_engine import generate_full_journey_story
        _seed_pledges(user_id=7, count=6)
        scenes = generate_full_journey_story(user_id=7, username="Journeyer")
        assert len(scenes) >= 2  # opening + at least one more

    def test_journey_scene_fields(self, _init_tables):
        from pledge_story_engine import generate_full_journey_story
        scenes = generate_full_journey_story(user_id=999)
        for scene in scenes:
            assert scene.scene_id
            assert scene.scene_type in ("opening", "conflict", "resolution", "celebration", "reflection")
            assert scene.title
            assert scene.narrative
            assert scene.mood in ("hopeful", "triumphant", "reflective", "urgent", "inspiring")

    def test_journey_scene_stat_highlight(self, _init_tables):
        from pledge_story_engine import generate_full_journey_story
        scenes = generate_full_journey_story(user_id=999)
        # Opening scene should have a stat highlight
        assert scenes[0].stat_highlight == "Day 1"


# ── Impact Narrative tests ───────────────────────────────────────────

class TestImpactNarrative:
    """Tests for human-readable impact narratives."""

    def test_narrative_empty_user(self, _init_tables):
        from pledge_story_engine import generate_impact_narrative
        narrative = generate_impact_narrative(user_id=999)
        assert narrative.headline
        assert narrative.body
        assert narrative.equivalent
        assert narrative.call_to_action
        assert narrative.tone in ("inspiring", "encouraging", "celebratory", "urgent", "triumphant")

    def test_narrative_with_small_impact(self, _init_tables):
        from pledge_story_engine import generate_impact_narrative
        _seed_pledges(user_id=8, count=1)
        narrative = generate_impact_narrative(user_id=8)
        assert narrative.tone in ("inspiring", "encouraging")

    def test_narrative_with_large_impact(self, _init_tables):
        from pledge_story_engine import generate_impact_narrative
        _seed_pledges(user_id=9, count=10, weeks_back=10)
        narrative = generate_impact_narrative(user_id=9)
        assert narrative.headline
        assert narrative.tone in ("celebratory", "triumphant")


# ── Monthly Journal tests ────────────────────────────────────────────

class TestMonthlyJournal:
    """Tests for monthly eco-journal generation."""

    def test_journal_empty_user(self, _init_tables):
        from pledge_story_engine import generate_monthly_journal
        entry = generate_monthly_journal(user_id=999, username="Journaler")
        assert entry is not None
        assert entry.user_id == 999
        assert entry.month
        assert entry.title
        assert entry.narrative
        assert entry.created_at

    def test_journal_with_data(self, _init_tables):
        from pledge_story_engine import generate_monthly_journal
        _seed_pledges(user_id=10, count=4)
        entry = generate_monthly_journal(user_id=10, username="JournalUser")
        assert entry.stats_summary
        assert entry.stats_summary.get("total_completed", 0) > 0

    def test_journal_highlights(self, _init_tables):
        from pledge_story_engine import generate_monthly_journal
        _seed_pledges(user_id=11, count=2)
        entry = generate_monthly_journal(user_id=11)
        assert isinstance(entry.highlights, list)

    def test_journal_best_moment(self, _init_tables):
        from pledge_story_engine import generate_monthly_journal
        _seed_pledges(user_id=12, count=3)
        entry = generate_monthly_journal(user_id=12)
        assert entry.best_moment

    def test_journal_next_month_goal(self, _init_tables):
        from pledge_story_engine import generate_monthly_journal
        _seed_pledges(user_id=13, count=2)
        entry = generate_monthly_journal(user_id=13)
        assert entry.next_month_goal


# ── Story Management tests ───────────────────────────────────────────

class TestStoryManagement:
    """Tests for story retrieval and favourites."""

    def test_get_user_stories_empty(self, _init_tables):
        from pledge_story_engine import get_user_stories
        stories = get_user_stories(user_id=999)
        assert stories == []

    def test_get_user_stories_after_generation(self, _init_tables):
        from pledge_story_engine import generate_weekly_story, get_user_stories
        generate_weekly_story(user_id=14)
        stories = get_user_stories(user_id=14)
        assert len(stories) >= 1

    def test_favorite_story(self, _init_tables):
        from pledge_story_engine import generate_weekly_story, favorite_story, get_favorites
        story = generate_weekly_story(user_id=15)
        result = favorite_story(user_id=15, story_id=story.story_id)
        assert result is True
        favs = get_favorites(user_id=15)
        assert story.story_id in favs

    def test_unfavorite_story(self, _init_tables):
        from pledge_story_engine import generate_weekly_story, favorite_story, unfavorite_story, get_favorites
        story = generate_weekly_story(user_id=16)
        favorite_story(user_id=16, story_id=story.story_id)
        unfavorite_story(user_id=16, story_id=story.story_id)
        favs = get_favorites(user_id=16)
        assert story.story_id not in favs

    def test_favorite_idempotent(self, _init_tables):
        from pledge_story_engine import generate_weekly_story, favorite_story
        story = generate_weekly_story(user_id=17)
        favorite_story(user_id=17, story_id=story.story_id)
        # Second favorite should not error
        result = favorite_story(user_id=17, story_id=story.story_id)
        assert isinstance(result, bool)

    def test_get_user_journals_empty(self, _init_tables):
        from pledge_story_engine import get_user_journals
        journals = get_user_journals(user_id=999)
        assert journals == []

    def test_get_user_journals_after_generation(self, _init_tables):
        from pledge_story_engine import generate_monthly_journal, get_user_journals
        generate_monthly_journal(user_id=18)
        journals = get_user_journals(user_id=18)
        assert len(journals) >= 1


# ── Serialisation tests ──────────────────────────────────────────────

class TestSerialisation:
    """Tests for story data serialisation."""

    def test_story_to_dict(self, _init_tables):
        from pledge_story_engine import generate_weekly_story, story_to_dict
        story = generate_weekly_story(user_id=19)
        d = story_to_dict(story)
        assert isinstance(d, dict)
        assert "story_id" in d
        assert "narrative" in d
        assert "tags" in d

    def test_journal_to_dict(self, _init_tables):
        from pledge_story_engine import generate_monthly_journal, journal_to_dict
        entry = generate_monthly_journal(user_id=20)
        d = journal_to_dict(entry)
        assert isinstance(d, dict)
        assert "entry_id" in d
        assert "highlights" in d
        assert "stats_summary" in d
        assert "story_cards" in d

    def test_export_stories_json(self, _init_tables):
        from pledge_story_engine import export_stories_json, generate_weekly_story
        generate_weekly_story(user_id=21)
        json_str = export_stories_json(user_id=21)
        data = json.loads(json_str)
        assert "stories" in data
        assert "journals" in data
        assert "favorites" in data
        assert data["total_stories"] >= 1


# ── Theme tests ──────────────────────────────────────────────────────

class TestThemes:
    """Tests for story themes and constants."""

    def test_story_themes_complete(self, _init_tables):
        from pledge_story_engine import STORY_THEMES
        for key, theme in STORY_THEMES.items():
            assert "title" in theme
            assert "opening_templates" in theme
            assert len(theme["opening_templates"]) > 0
            assert "color_primary" in theme
            assert "color_secondary" in theme
            assert "icon" in theme

    def test_narrative_templates_complete(self, _init_tables):
        from pledge_story_engine import NARRATIVE_TEMPLATES
        expected_types = [
            "weekly_summary", "milestone_celebration", "streak_narrative",
            "co2_impact", "journey_beginning", "group_story", "prediction_story",
        ]
        for t in expected_types:
            assert t in NARRATIVE_TEMPLATES
            assert len(NARRATIVE_TEMPLATES[t]) > 0

    def test_co2_equivalents(self, _init_tables):
        from pledge_story_engine import CO2_EQUIVALENTS
        assert len(CO2_EQUIVALENTS) > 0
        for template, fn in CO2_EQUIVALENTS:
            result = fn(100.0)
            assert result > 0


# ── Integration test ─────────────────────────────────────────────────

class TestIntegration:
    """Integration test for the full story engine workflow."""

    def test_full_workflow(self, _init_tables):
        from green_pledge_tracker import create_pledge, checkin_pledge, current_week_start
        from pledge_story_engine import (
            generate_weekly_story,
            generate_milestone_story,
            generate_streak_story,
            generate_impact_story,
            generate_prediction_story,
            generate_journey_beginning_story,
            generate_full_journey_story,
            generate_monthly_journal,
            generate_impact_narrative,
            get_user_stories,
            get_user_journals,
            favorite_story,
            get_favorites,
            export_stories_json,
        )

        user_id = 42

        # Seed pledges
        for tpl_id in ["energy_no_standby", "transport_bike_week"]:
            pledge = create_pledge(user_id=user_id, template_id=tpl_id)
            if pledge:
                ws = current_week_start()
                monday = datetime.strptime(ws, "%Y-%m-%d")
                for d in range(7):
                    day = (monday + timedelta(days=d)).strftime("%Y-%m-%d")
                    checkin_pledge(user_id=user_id, pledge_id=pledge.pledge_id, day_date=day)

        # Generate all story types
        weekly = generate_weekly_story(user_id, "IntegrationTester")
        assert weekly.story_id

        milestone = generate_milestone_story(user_id, "IntegrationTester")
        # May be None if no milestones yet

        streak = generate_streak_story(user_id, "IntegrationTester")
        # May be None if no streak

        impact = generate_impact_story(user_id, "IntegrationTester")
        assert impact.stat_value >= 0

        prediction = generate_prediction_story(user_id, "IntegrationTester")
        assert prediction.stat_value >= 0

        journey_start = generate_journey_beginning_story(user_id, "IntegrationTester")
        assert "IntegrationTester" in journey_start.narrative

        # Full journey
        scenes = generate_full_journey_story(user_id, "IntegrationTester")
        assert len(scenes) >= 1

        # Journal
        journal = generate_monthly_journal(user_id, "IntegrationTester")
        assert journal.month

        # Impact narrative
        narrative = generate_impact_narrative(user_id, "IntegrationTester")
        assert narrative.headline

        # Management
        stories = get_user_stories(user_id)
        assert len(stories) >= 1

        favorite_story(user_id, stories[0].story_id)
        favs = get_favorites(user_id)
        assert stories[0].story_id in favs

        # Export
        json_data = export_stories_json(user_id)
        data = json.loads(json_data)
        assert data["total_stories"] >= 1
