"""
Tests for green_pledge_tracker and pledge_leaderboard modules
==============================================================
Covers pledge templates, CRUD operations, streaks, community impact,
accountability groups, challenges, announcements, and leaderboard scoring.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

# ── Test database setup ──────────────────────────────────────────────

TEST_DB = "test_leaderboard.db"


@pytest.fixture(autouse=True)
def _setup_test_db(tmp_path, monkeypatch):
    """Use an in-memory SQLite DB for every test."""
    db_path = str(tmp_path / TEST_DB)
    monkeypatch.setattr("green_pledge_tracker.DB_NAME", db_path)
    monkeypatch.setattr("pledge_leaderboard.DB_NAME", db_path)
    monkeypatch.setattr("database_connection.database_connection", lambda name: _ctx(name))
    yield db_path


class _ctx:
    """Minimal context manager that returns a sqlite3 connection."""
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
    init_pledge_tables()
    init_leaderboard_tables()


# ── green_pledge_tracker tests ───────────────────────────────────────

class TestPledgeTemplates:
    """Tests for pledge template catalogue."""

    def test_get_all_templates_returns_list(self, _init_tables):
        from green_pledge_tracker import get_all_templates
        templates = get_all_templates()
        assert isinstance(templates, list)
        assert len(templates) > 0

    def test_templates_have_required_fields(self, _init_tables):
        from green_pledge_tracker import get_all_templates
        for tpl in get_all_templates():
            assert tpl.id
            assert tpl.title
            assert tpl.description
            assert tpl.category in ("energy", "transport", "diet", "waste", "water", "lifestyle")
            assert tpl.difficulty in ("easy", "medium", "hard")
            assert tpl.weekly_co2_saved_kg > 0
            assert tpl.xp_reward > 0
            assert tpl.eco_points > 0

    def test_get_templates_by_category(self, _init_tables):
        from green_pledge_tracker import get_templates_by_category
        energy = get_templates_by_category("energy")
        assert len(energy) > 0
        for tpl in energy:
            assert tpl.category == "energy"

    def test_get_template_by_id_found(self, _init_tables):
        from green_pledge_tracker import get_template_by_id, get_all_templates
        first = get_all_templates()[0]
        result = get_template_by_id(first.id)
        assert result is not None
        assert result.id == first.id

    def test_get_template_by_id_not_found(self, _init_tables):
        from green_pledge_tracker import get_template_by_id
        result = get_template_by_id("nonexistent_id")
        assert result is None

    def test_get_categories(self, _init_tables):
        from green_pledge_tracker import get_categories
        cats = get_categories()
        assert isinstance(cats, dict)
        assert "energy" in cats
        assert "label" in cats["energy"]
        assert "color" in cats["energy"]


class TestPledgeCRUD:
    """Tests for pledge creation, check-in, completion, and abandonment."""

    def test_create_pledge(self, _init_tables):
        from green_pledge_tracker import create_pledge
        pledge = create_pledge(user_id=1, template_id="energy_no_standby")
        assert pledge is not None
        assert pledge.user_id == 1
        assert pledge.template_id == "energy_no_standby"
        assert pledge.status == "active"
        assert pledge.day_checkins == 0

    def test_create_pledge_duplicate_returns_none(self, _init_tables):
        from green_pledge_tracker import create_pledge
        p1 = create_pledge(user_id=1, template_id="energy_no_standby")
        assert p1 is not None
        p2 = create_pledge(user_id=1, template_id="energy_no_standby")
        assert p2 is None

    def test_create_pledge_invalid_template(self, _init_tables):
        from green_pledge_tracker import create_pledge
        result = create_pledge(user_id=1, template_id="invalid")
        assert result is None

    def test_checkin_pledge(self, _init_tables):
        from green_pledge_tracker import create_pledge, checkin_pledge
        pledge = create_pledge(user_id=1, template_id="energy_no_standby")
        result = checkin_pledge(user_id=1, pledge_id=pledge.pledge_id)
        assert result is not None
        assert result.day_checkins == 1
        assert result.completion_pct > 0

    def test_checkin_pledge_wrong_user(self, _init_tables):
        from green_pledge_tracker import create_pledge, checkin_pledge
        pledge = create_pledge(user_id=1, template_id="energy_no_standby")
        result = checkin_pledge(user_id=2, pledge_id=pledge.pledge_id)
        assert result is None

    def test_checkin_pledge_duplicate_day(self, _init_tables):
        from green_pledge_tracker import create_pledge, checkin_pledge
        pledge = create_pledge(user_id=1, template_id="energy_no_standby")
        r1 = checkin_pledge(user_id=1, pledge_id=pledge.pledge_id)
        assert r1 is not None
        r2 = checkin_pledge(user_id=1, pledge_id=pledge.pledge_id)
        assert r2 is None  # duplicate day

    def test_checkin_pledge_completes_after_7(self, _init_tables):
        from green_pledge_tracker import create_pledge, checkin_pledge, current_week_start
        week = current_week_start()
        pledge = create_pledge(user_id=1, template_id="energy_no_standby", week=week)
        for day_offset in range(7):
            day = (datetime.strptime(week, "%Y-%m-%d") + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            result = checkin_pledge(user_id=1, pledge_id=pledge.pledge_id, day_date=day)
        assert result.status == "completed"
        assert result.earned_xp > 0

    def test_abandon_pledge(self, _init_tables):
        from green_pledge_tracker import create_pledge, abandon_pledge
        pledge = create_pledge(user_id=1, template_id="energy_no_standby")
        assert abandon_pledge(user_id=1, pledge_id=pledge.pledge_id) is True

    def test_abandon_pledge_wrong_user(self, _init_tables):
        from green_pledge_tracker import create_pledge, abandon_pledge
        pledge = create_pledge(user_id=1, template_id="energy_no_standby")
        assert abandon_pledge(user_id=2, pledge_id=pledge.pledge_id) is False


class TestUserPledges:
    """Tests for retrieving user pledge data."""

    def test_get_user_weekly_pledges(self, _init_tables):
        from green_pledge_tracker import create_pledge, get_user_weekly_pledges
        create_pledge(user_id=1, template_id="energy_no_standby")
        create_pledge(user_id=1, template_id="energy_cold_wash")
        pledges = get_user_weekly_pledges(user_id=1)
        assert len(pledges) == 2

    def test_get_user_all_pledges(self, _init_tables):
        from green_pledge_tracker import create_pledge, get_user_all_pledges
        create_pledge(user_id=1, template_id="energy_no_standby")
        create_pledge(user_id=1, template_id="transport_bike_week")
        all_pledges = get_user_all_pledges(user_id=1)
        assert len(all_pledges) >= 2

    def test_get_pledge_checkin_dates(self, _init_tables):
        from green_pledge_tracker import create_pledge, checkin_pledge, get_pledge_checkin_dates
        pledge = create_pledge(user_id=1, template_id="energy_no_standby")
        checkin_pledge(user_id=1, pledge_id=pledge.pledge_id, day_date="2026-08-20")
        checkin_pledge(user_id=1, pledge_id=pledge.pledge_id, day_date="2026-08-21")
        dates = get_pledge_checkin_dates(pledge.pledge_id)
        assert len(dates) == 2
        assert "2026-08-20" in dates
        assert "2026-08-21" in dates


class TestUserStats:
    """Tests for user pledge statistics and levels."""

    def test_get_user_pledge_stats_new_user(self, _init_tables):
        from green_pledge_tracker import get_user_pledge_stats
        stats = get_user_pledge_stats(user_id=999)
        assert stats.total_pledges_made == 0
        assert stats.level == "Seedling"
        assert stats.completion_rate_pct == 0.0

    def test_stats_after_completion(self, _init_tables):
        from green_pledge_tracker import create_pledge, checkin_pledge, get_user_pledge_stats, current_week_start
        week = current_week_start()
        pledge = create_pledge(user_id=10, template_id="energy_no_standby", week=week)
        for day_offset in range(7):
            day = (datetime.strptime(week, "%Y-%m-%d") + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            checkin_pledge(user_id=10, pledge_id=pledge.pledge_id, day_date=day)

        stats = get_user_pledge_stats(user_id=10)
        assert stats.total_pledges_completed >= 1
        assert stats.total_xp_earned > 0
        assert stats.total_co2_saved_kg > 0
        assert stats.completion_rate_pct > 0

    def test_compute_level(self, _init_tables):
        from green_pledge_tracker import _compute_level, UserPledgeStats
        stats = UserPledgeStats(user_id=1, total_xp_earned=0)
        assert _compute_level(stats) == "Seedling"
        stats.total_xp_earned = 50
        assert _compute_level(stats) == "Sapling"
        stats.total_xp_earned = 150
        assert _compute_level(stats) == "Sprout"
        stats.total_xp_earned = 400
        assert _compute_level(stats) == "Guardian"
        stats.total_xp_earned = 800
        assert _compute_level(stats) == "Champion"
        stats.total_xp_earned = 1500
        assert _compute_level(stats) == "Eco Legend"


class TestStreaks:
    """Tests for streak calculation."""

    def test_streak_zero(self, _init_tables):
        from green_pledge_tracker import calculate_streak
        current, best = calculate_streak(user_id=999)
        assert current == 0
        assert best == 0

    def test_streak_one_week(self, _init_tables):
        from green_pledge_tracker import create_pledge, checkin_pledge, calculate_streak, current_week_start
        week = current_week_start()
        pledge = create_pledge(user_id=20, template_id="energy_no_standby", week=week)
        for day_offset in range(7):
            day = (datetime.strptime(week, "%Y-%m-%d") + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            checkin_pledge(user_id=20, pledge_id=pledge.pledge_id, day_date=day)
        current, best = calculate_streak(user_id=20)
        assert current >= 1
        assert best >= 1


class TestCommunityImpact:
    """Tests for community impact aggregation."""

    def test_empty_community_impact(self, _init_tables):
        from green_pledge_tracker import get_community_impact
        impact = get_community_impact()
        assert impact.total_participants == 0
        assert impact.total_pledges == 0
        assert impact.total_completed == 0
        assert impact.community_co2_saved_kg == 0.0


class TestPledgeSuggestions:
    """Tests for pledge suggestion engine."""

    def test_suggest_pledges(self, _init_tables):
        from green_pledge_tracker import suggest_pledges_for_user
        suggestions = suggest_pledges_for_user(user_footprint=5000.0, user_pledges=[], n=4)
        assert len(suggestions) <= 4
        assert len(suggestions) > 0
        for s in suggestions:
            assert "template_id" in s
            assert "fit_score" in s
            assert "impact_ratio_pct" in s

    def test_suggest_excludes_enrolled(self, _init_tables):
        from green_pledge_tracker import create_pledge, suggest_pledges_for_user
        pledge = create_pledge(user_id=1, template_id="energy_no_standby")
        my_pledges = [pledge]
        suggestions = suggest_pledges_for_user(5000.0, my_pledges, n=20)
        enrolled_ids = {p.template_id for p in my_pledges}
        for s in suggestions:
            assert s["template_id"] not in enrolled_ids


class TestProjections:
    """Tests for annual CO₂ projection."""

    def test_estimate_co2_equivalents(self, _init_tables):
        from green_pledge_tracker import estimate_co2_equivalents
        eq = estimate_co2_equivalents(100.0)
        assert eq["co2_kg"] == 100.0
        assert eq["car_km"] > 0
        assert eq["trees_needed"] > 0
        assert eq["smartphone_charges"] > 0
        assert eq["beef_burgers"] > 0


# ── pledge_leaderboard tests ─────────────────────────────────────────

class TestGroupCRUD:
    """Tests for accountability group creation and management."""

    def test_create_group(self, _init_tables):
        from pledge_leaderboard import create_group
        group = create_group(name="Test Group", owner_id=1, description="A test group")
        assert group is not None
        assert group.name == "Test Group"
        assert group.owner_id == 1
        assert group.member_count == 1  # owner auto-joined
        assert group.invite_code

    def test_create_group_duplicate_name(self, _init_tables):
        from pledge_leaderboard import create_group
        g1 = create_group(name="Unique", owner_id=1)
        g2 = create_group(name="Unique", owner_id=2)
        assert g2 is None

    def test_join_group(self, _init_tables):
        from pledge_leaderboard import create_group, join_group
        g = create_group(name="Joinable", owner_id=1)
        result = join_group(user_id=2, invite_code=g.invite_code)
        assert result is not None
        assert result.member_count == 2

    def test_join_group_wrong_code(self, _init_tables):
        from pledge_leaderboard import create_group, join_group
        g = create_group(name="Wrong Code", owner_id=1)
        result = join_group(user_id=2, invite_code="WRONGCODE")
        assert result is None

    def test_join_group_already_member(self, _init_tables):
        from pledge_leaderboard import create_group, join_group
        g = create_group(name="Already In", owner_id=1)
        result = join_group(user_id=1, invite_code=g.invite_code)
        assert result is None  # owner already member

    def test_leave_group(self, _init_tables):
        from pledge_leaderboard import create_group, join_group, leave_group
        g = create_group(name="Leaveable", owner_id=1)
        join_group(user_id=2, invite_code=g.invite_code)
        assert leave_group(user_id=2, group_id=g.group_id) is True

    def test_leave_group_owner_cannot_leave(self, _init_tables):
        from pledge_leaderboard import create_group, leave_group
        g = create_group(name="OwnerStay", owner_id=1)
        assert leave_group(user_id=1, group_id=g.group_id) is False

    def test_delete_group(self, _init_tables):
        from pledge_leaderboard import create_group, delete_group
        g = create_group(name="Deletable", owner_id=1)
        assert delete_group(user_id=1, group_id=g.group_id) is True
        from pledge_leaderboard import _fetch_group
        assert _fetch_group(g.group_id) is None

    def test_delete_group_wrong_owner(self, _init_tables):
        from pledge_leaderboard import create_group, delete_group
        g = create_group(name="Not Yours", owner_id=1)
        assert delete_group(user_id=2, group_id=g.group_id) is False

    def test_transfer_ownership(self, _init_tables):
        from pledge_leaderboard import create_group, join_group, transfer_ownership, _fetch_group
        g = create_group(name="Transfer", owner_id=1)
        join_group(user_id=2, invite_code=g.invite_code)
        assert transfer_ownership(owner_id=1, group_id=g.group_id, new_owner_id=2) is True
        updated = _fetch_group(g.group_id)
        assert updated.owner_id == 2

    def test_get_user_groups(self, _init_tables):
        from pledge_leaderboard import create_group, get_user_groups
        create_group(name="G1", owner_id=1)
        create_group(name="G2", owner_id=1)
        groups = get_user_groups(user_id=1)
        assert len(groups) == 2

    def test_get_public_groups(self, _init_tables):
        from pledge_leaderboard import create_group, get_public_groups
        create_group(name="Pub1", owner_id=1)
        create_group(name="Pub2", owner_id=2)
        groups = get_public_groups()
        assert len(groups) >= 2

    def test_get_group_members(self, _init_tables):
        from pledge_leaderboard import create_group, join_group, get_group_members
        g = create_group(name="Members", owner_id=1)
        join_group(user_id=2, invite_code=g.invite_code)
        members = get_group_members(g.group_id)
        assert len(members) == 2


class TestGroupChallenges:
    """Tests for group challenge creation and progress tracking."""

    def test_create_challenge(self, _init_tables):
        from pledge_leaderboard import create_group, create_group_challenge
        g = create_group(name="ChalGroup", owner_id=1)
        ch = create_group_challenge(
            creator_id=1,
            group_id=g.group_id,
            title="Test Challenge",
            description="Complete 5 pledges",
            target_type="pledges_completed",
            target_value=5.0,
        )
        assert ch is not None
        assert ch.title == "Test Challenge"
        assert ch.status == "active"

    def test_create_challenge_non_admin_fails(self, _init_tables):
        from pledge_leaderboard import create_group, join_group, create_group_challenge
        g = create_group(name="NoChal", owner_id=1)
        join_group(user_id=2, invite_code=g.invite_code)
        ch = create_group_challenge(
            creator_id=2,
            group_id=g.group_id,
            title="Should Fail",
            target_type="pledges_completed",
            target_value=5.0,
        )
        assert ch is None

    def test_challenge_progress(self, _init_tables):
        from pledge_leaderboard import create_group, create_group_challenge, update_challenge_progress
        g = create_group(name="Progress", owner_id=1)
        ch = create_group_challenge(
            creator_id=1, group_id=g.group_id,
            title="Prog Test", target_type="pledges_completed", target_value=5.0,
        )
        updated = update_challenge_progress(ch.challenge_id, 3.0)
        assert updated.current_value == 3.0
        assert updated.status == "active"

    def test_challenge_completion(self, _init_tables):
        from pledge_leaderboard import create_group, create_group_challenge, update_challenge_progress
        g = create_group(name="Complete", owner_id=1)
        ch = create_group_challenge(
            creator_id=1, group_id=g.group_id,
            title="Complete Test", target_type="pledges_completed", target_value=5.0, xp_reward=200,
        )
        updated = update_challenge_progress(ch.challenge_id, 5.0)
        assert updated.status == "completed"
        assert updated.completed_at != ""


class TestAnnouncements:
    """Tests for group announcements."""

    def test_post_announcement(self, _init_tables):
        from pledge_leaderboard import create_group, post_announcement
        g = create_group(name="AnnGroup", owner_id=1)
        ann = post_announcement(
            author_id=1,
            group_id=g.group_id,
            title="Hello World",
            body="Welcome to the group!",
            priority="normal",
        )
        assert ann is not None
        assert ann.title == "Hello World"

    def test_post_announcement_non_admin_fails(self, _init_tables):
        from pledge_leaderboard import create_group, join_group, post_announcement
        g = create_group(name="NoAnn", owner_id=1)
        join_group(user_id=2, invite_code=g.invite_code)
        ann = post_announcement(author_id=2, group_id=g.group_id, title="Fail", body="test")
        assert ann is None

    def test_get_announcements(self, _init_tables):
        from pledge_leaderboard import create_group, post_announcement, get_group_announcements
        g = create_group(name="GetAnn", owner_id=1)
        post_announcement(author_id=1, group_id=g.group_id, title="A1", body="body1")
        post_announcement(author_id=1, group_id=g.group_id, title="A2", body="body2")
        anns = get_group_announcements(g.group_id)
        assert len(anns) == 2


class TestLeaderboard:
    """Tests for leaderboard scoring and ranking."""

    def test_empty_leaderboard(self, _init_tables):
        from pledge_leaderboard import get_leaderboard
        lb = get_leaderboard()
        assert isinstance(lb, list)
        assert len(lb) == 0

    def test_leaderboard_ranking(self, _init_tables):
        from pledge_leaderboard import create_group, get_leaderboard
        g1 = create_group(name="Alpha", owner_id=1)
        g2 = create_group(name="Beta", owner_id=2)
        lb = get_leaderboard()
        assert len(lb) >= 2
        # Both start at 0 XP so both should appear
        names = {e.group_name for e in lb}
        assert "Alpha" in names
        assert "Beta" in names

    def test_group_score_computation(self, _init_tables):
        from pledge_leaderboard import create_group, _compute_group_score
        g = create_group(name="Scored", owner_id=1)
        score = _compute_group_score(g)
        assert score > 0  # at least some score from being a member


class TestShareCards:
    """Tests for social share card generation."""

    def test_group_share_card(self, _init_tables):
        from pledge_leaderboard import create_group, generate_group_share_card
        g = create_group(name="ShareTest", owner_id=1)
        card = generate_group_share_card(g)
        assert "title" in card
        assert "stats" in card
        assert "tagline" in card
        assert card["title"] == "ShareTest"
        assert card["stats"]["members"] == 1

    def test_tagline_varies_by_co2(self, _init_tables):
        from pledge_leaderboard import AccountabilityGroup, _generate_tagline
        g = AccountabilityGroup(
            group_id="x", name="Test", description="", owner_id=1,
            privacy="public", invite_code="ABC", max_members=10,
            member_count=5, total_co2_saved_kg=600.0,
        )
        tagline = _generate_tagline(g)
        assert "600" in tagline

    def test_export_group_json(self, _init_tables):
        from pledge_leaderboard import create_group, export_group_json
        g = create_group(name="ExportTest", owner_id=1)
        json_str = export_group_json(g.group_id)
        data = json.loads(json_str)
        assert "group" in data
        assert "members" in data
        assert data["group"]["name"] == "ExportTest"


class TestWeeklySnapshots:
    """Tests for weekly snapshot tracking."""

    def test_take_snapshot(self, _init_tables):
        from pledge_leaderboard import create_group, take_weekly_snapshot
        g = create_group(name="Snapshot", owner_id=1)
        snap = take_weekly_snapshot(g.group_id)
        assert snap is not None
        assert snap.group_id == g.group_id

    def test_weekly_trend(self, _init_tables):
        from pledge_leaderboard import create_group, take_weekly_snapshot, get_group_weekly_trend
        g = create_group(name="Trend", owner_id=1)
        take_weekly_snapshot(g.group_id)
        trend = get_group_weekly_trend(g.group_id)
        assert len(trend) >= 1


class TestGroupLevels:
    """Tests for group level computation."""

    def test_group_level_at_creation(self, _init_tables):
        from pledge_leaderboard import create_group
        g = create_group(name="LevelTest", owner_id=1)
        assert g.level == "Seedling"

    def test_group_badges_at_creation(self, _init_tables):
        from pledge_leaderboard import create_group
        g = create_group(name="BadgeTest", owner_id=1)
        # Owner auto-joined, so member_count=1 — no badge yet
        assert isinstance(g.badges, list)


class TestGroupMaxMembers:
    """Tests for member limit enforcement."""

    def test_cannot_join_full_group(self, _init_tables):
        from pledge_leaderboard import create_group, join_group
        g = create_group(name="Full", owner_id=1, max_members=2)
        join_group(user_id=2, invite_code=g.invite_code)
        result = join_group(user_id=3, invite_code=g.invite_code)
        assert result is None
