"""
Tests for green_pledge_tracker module.
Run with: pytest test_green_pledge_tracker.py -v
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from green_pledge_tracker import (
    get_all_templates,
    get_templates_by_category,
    get_template_by_id,
    get_categories,
    current_week_start,
    current_week_end,
    weeks_between,
    estimate_co2_equivalents,
    score_pledge_fit,
    _compute_level,
    _compute_badges,
    pledge_to_dict,
    PledgeDifficulty,
    DIFFICULTY_MULTIPLIER,
    PLEDGE_CATEGORIES,
    PledgeTemplate,
    UserPledgeStats,
)


# ── Template catalogue tests ─────────────────────────────────────────

class TestTemplateCatalogue:
    def test_get_all_templates_returns_list(self):
        templates = get_all_templates()
        assert isinstance(templates, list)
        assert len(templates) > 0

    def test_all_templates_are_pledge_template(self):
        for t in get_all_templates():
            assert isinstance(t, PledgeTemplate)

    def test_templates_have_required_fields(self):
        for t in get_all_templates():
            assert t.id, "Template must have an id"
            assert t.category in PLEDGE_CATEGORIES, f"Unknown category: {t.category}"
            assert t.title
            assert t.description
            assert t.difficulty in ("easy", "medium", "hard")
            assert t.weekly_co2_saved_kg >= 0
            assert t.xp_reward > 0
            assert t.eco_points > 0

    def test_get_templates_by_category_energy(self):
        energy = get_templates_by_category("energy")
        assert len(energy) >= 1
        for t in energy:
            assert t.category == "energy"

    def test_get_templates_by_category_transport(self):
        transport = get_templates_by_category("transport")
        assert len(transport) >= 1
        for t in transport:
            assert t.category == "transport"

    def test_get_templates_by_category_diet(self):
        diet = get_templates_by_category("diet")
        assert len(diet) >= 1

    def test_get_templates_by_category_waste(self):
        waste = get_templates_by_category("waste")
        assert len(waste) >= 1

    def test_get_templates_by_category_water(self):
        water = get_templates_by_category("water")
        assert len(water) >= 1

    def test_get_templates_by_category_lifestyle(self):
        lifestyle = get_templates_by_category("lifestyle")
        assert len(lifestyle) >= 1

    def test_get_templates_by_unknown_category(self):
        result = get_templates_by_category("nonexistent")
        assert result == []

    def test_get_template_by_id_valid(self):
        first = get_all_templates()[0]
        found = get_template_by_id(first.id)
        assert found is not None
        assert found.id == first.id

    def test_get_template_by_id_invalid(self):
        assert get_template_by_id("nonexistent_id_123") is None

    def test_get_categories(self):
        cats = get_categories()
        assert isinstance(cats, dict)
        assert "energy" in cats
        assert "transport" in cats
        assert "diet" in cats
        assert all("label" in v for v in cats.values())
        assert all("color" in v for v in cats.values())


# ── Week helper tests ────────────────────────────────────────────────

class TestWeekHelpers:
    def test_current_week_start_format(self):
        ws = current_week_start()
        # Should be YYYY-MM-DD
        datetime.strptime(ws, "%Y-%m-%d")  # Raises on bad format

    def test_current_week_start_is_monday(self):
        ws = current_week_start()
        dt = datetime.strptime(ws, "%Y-%m-%d")
        assert dt.weekday() == 0  # Monday

    def test_current_week_end_format(self):
        we = current_week_end()
        datetime.strptime(we, "%Y-%m-%d")

    def test_current_week_end_is_sunday(self):
        we = current_week_end()
        dt = datetime.strptime(we, "%Y-%m-%d")
        assert dt.weekday() == 6  # Sunday

    def test_current_week_start_to_end_span(self):
        ws = current_week_start()
        we = current_week_end()
        assert ws <= we

    def test_weeks_between_same_week(self):
        assert weeks_between("2026-08-24", "2026-08-28") == 0

    def test_weeks_between_two_weeks(self):
        assert weeks_between("2026-08-17", "2026-08-31") == 2

    def test_weeks_between_zero(self):
        assert weeks_between("2026-08-24", "2026-08-24") == 0


# ── CO₂ equivalents tests ────────────────────────────────────────────

class TestCO2Equivalents:
    def test_zero_co2(self):
        eq = estimate_co2_equivalents(0)
        assert eq["co2_kg"] == 0.0
        assert eq["car_km"] == 0.0

    def test_positive_co2(self):
        eq = estimate_co2_equivalents(50)
        assert eq["co2_kg"] == 50.0
        assert eq["car_km"] > 0
        assert eq["trees_needed"] > 0
        assert eq["smartphone_charges"] > 0
        assert eq["beef_burgers"] > 0

    def test_negative_co2(self):
        eq = estimate_co2_equivalents(-10)
        assert eq["co2_kg"] == -10.0

    def test_all_keys_present(self):
        eq = estimate_co2_equivalents(100)
        expected_keys = {
            "co2_kg", "car_km", "trees_needed", "smartphone_charges",
            "beef_burgers", "flight_minutes", "shower_minutes",
        }
        assert set(eq.keys()) == expected_keys

    def test_equivalence_rates(self):
        eq = estimate_co2_equivalents(19)
        assert eq["car_km"] == pytest.approx(100.0, abs=1.0)


# ── Pledge fit scoring tests ─────────────────────────────────────────

class TestPledgeFit:
    def test_fit_score_has_all_keys(self):
        tpl = get_all_templates()[0]
        fit = score_pledge_fit(5000, tpl)
        assert "template_id" in fit
        assert "fit_score" in fit
        assert "impact_ratio_pct" in fit

    def test_higher_footprint_lower_impact_ratio(self):
        tpl = get_all_templates()[0]
        low = score_pledge_fit(1000, tpl)
        high = score_pledge_fit(10000, tpl)
        assert low["impact_ratio_pct"] > high["impact_ratio_pct"]

    def test_zero_footprint(self):
        tpl = get_all_templates()[0]
        fit = score_pledge_fit(0, tpl)
        assert fit["impact_ratio_pct"] == 0.0

    def test_hard_pledge_higher_difficulty_score(self):
        easy = [t for t in get_all_templates() if t.difficulty == "easy"][0]
        hard = [t for t in get_all_templates() if t.difficulty == "hard"][0]
        f_easy = score_pledge_fit(5000, easy)
        f_hard = score_pledge_fit(5000, hard)
        assert f_hard["difficulty_score"] > f_easy["difficulty_score"]


# ── Level computation tests ──────────────────────────────────────────

class TestLevelComputation:
    def test_level_seedling(self):
        stats = UserPledgeStats(user_id=1, total_xp_earned=0)
        assert _compute_level(stats) == "Seedling"

    def test_level_sapling(self):
        stats = UserPledgeStats(user_id=1, total_xp_earned=60)
        assert _compute_level(stats) == "Sapling"

    def test_level_champion(self):
        stats = UserPledgeStats(user_id=1, total_xp_earned=900)
        assert _compute_level(stats) == "Champion"

    def test_level_eco_legend(self):
        stats = UserPledgeStats(user_id=1, total_xp_earned=2000)
        assert _compute_level(stats) == "Eco Legend"

    def test_level_between_thresholds(self):
        stats = UserPledgeStats(user_id=1, total_xp_earned=300)
        assert _compute_level(stats) == "Sapling"


# ── Badge computation tests ──────────────────────────────────────────

class TestBadgeComputation:
    def test_no_badges_for_new_user(self):
        stats = UserPledgeStats(user_id=1)
        badges = _compute_badges(stats)
        assert badges == []

    def test_first_pledge_badge(self):
        stats = UserPledgeStats(user_id=1, total_pledges_completed=1)
        badges = _compute_badges(stats)
        assert "🌱 First Pledge" in badges

    def test_pledge_warrior_badge(self):
        stats = UserPledgeStats(user_id=1, total_pledges_completed=10)
        badges = _compute_badges(stats)
        assert "💪 Pledge Warrior" in badges

    def test_streak_badge(self):
        stats = UserPledgeStats(user_id=1, current_streak=3)
        badges = _compute_badges(stats)
        assert "⚡ 3-Week Streak" in badges

    def test_co2_badges(self):
        stats = UserPledgeStats(user_id=1, total_co2_saved_kg=55.0)
        badges = _compute_badges(stats)
        assert "🌎 50 kg CO₂ Saved" in badges
        # But not 100
        assert "🌐 100 kg CO₂ Saved" not in badges

    def test_eco_points_badge(self):
        stats = UserPledgeStats(user_id=1, total_eco_points=150)
        badges = _compute_badges(stats)
        assert "💎 100 Eco Points" in badges

    def test_completion_rate_badge(self):
        stats = UserPledgeStats(
            user_id=1,
            total_pledges_completed=10,
            completion_rate_pct=95.0,
        )
        badges = _compute_badges(stats)
        assert "🎯 90% Completion" in badges


# ── Pledge template dataclass tests ──────────────────────────────────

class TestPledgeTemplate:
    def test_from_dict(self):
        d = {
            "id": "test_pledge",
            "category": "energy",
            "title": "Test",
            "description": "A test pledge",
            "difficulty": "easy",
            "weekly_co2_saved_kg": 1.0,
            "xp_reward": 10,
            "eco_points": 2,
        }
        t = PledgeTemplate.from_dict(d)
        assert t.id == "test_pledge"
        assert t.weekly_co2_saved_kg == 1.0

    def test_from_dict_extra_keys(self):
        d = {
            "id": "test",
            "category": "energy",
            "title": "T",
            "description": "D",
            "difficulty": "easy",
            "weekly_co2_saved_kg": 0.5,
            "xp_reward": 5,
            "eco_points": 1,
            "extra_key": "ignored",
        }
        t = PledgeTemplate.from_dict(d)
        assert t.id == "test"


# ── Pledge-to-dict serialization ─────────────────────────────────────

class TestPledgeToDict:
    def test_pledge_to_dict(self):
        from green_pledge_tracker import ActivePledge
        p = ActivePledge(
            pledge_id="abc123",
            template_id="energy_no_standby",
            user_id=1,
            week_start="2026-08-24",
            status="active",
        )
        d = pledge_to_dict(p)
        assert d["pledge_id"] == "abc123"
        assert d["title"] == "Power Down Standby"
        assert d["category"] == "energy"
        assert "category_info" in d

    def test_pledge_to_dict_unknown_template(self):
        from green_pledge_tracker import ActivePledge
        p = ActivePledge(
            pledge_id="xyz",
            template_id="nonexistent_template",
            user_id=1,
            week_start="2026-08-24",
        )
        d = pledge_to_dict(p)
        assert "title" not in d or d.get("title") is None


# ── Difficulty multiplier tests ──────────────────────────────────────

class TestDifficultyMultiplier:
    def test_easy_multiplier(self):
        assert DIFFICULTY_MULTIPLIER[PledgeDifficulty.EASY] == 1.0

    def test_medium_multiplier(self):
        assert DIFFICULTY_MULTIPLIER[PledgeDifficulty.MEDIUM] == 1.5

    def test_hard_multiplier(self):
        assert DIFFICULTY_MULTIPLIER[PledgeDifficulty.HARD] == 2.0

    def test_all_difficulties_covered(self):
        for diff in PledgeDifficulty:
            assert diff in DIFFICULTY_MULTIPLIER


# ── Categories data integrity ────────────────────────────────────────

class TestCategoryData:
    def test_pledge_categories_have_required_fields(self):
        for key, val in PLEDGE_CATEGORIES.items():
            assert "label" in val
            assert "color" in val
            assert val["label"]
            assert val["color"].startswith("#")

    def test_all_template_categories_exist_in_pledge_categories(self):
        for t in get_all_templates():
            assert t.category in PLEDGE_CATEGORIES, (
                f"Template {t.id} has unknown category '{t.category}'"
            )

    def test_no_duplicate_template_ids(self):
        ids = [t.id for t in get_all_templates()]
        assert len(ids) == len(set(ids)), "Duplicate template IDs found"
