"""Extensive edge-case tests for the Household System.

These tests parameterize boundaries, zero-states, and invalid inputs
to ensure the Household Sustainability system handles errors gracefully.
"""

import pytest
from datetime import datetime, timedelta

from src.lifestyle.household import (
    init_household_db, create_household, add_member, delete_household,
    update_household, get_household, update_member, remove_member
)
from src.lifestyle.household_activities import (
    init_activities_db, log_activity, get_activities, VALID_CATEGORIES,
    update_activity, delete_activity, get_category_breakdown, get_member_contribution_breakdown
)
from src.lifestyle.household_budgeting import (
    init_budgeting_db, set_budget, get_budgets, evaluate_budgets, deactivate_budget
)
from src.lifestyle.household_gamification import (
    init_household_gamification_db, award_household_xp, _get_household_xp,
    award_badge, get_badges, create_challenge, complete_challenge
)
from src.lifestyle.household_metrics import calculate_sustainability_score


@pytest.fixture
def setup_edge_db():
    init_household_db()
    init_activities_db()
    init_budgeting_db()
    init_household_gamification_db()
    
    hh_id = create_household("Edge Case House", 999)
    m1 = add_member(hh_id, "Member1")
    
    yield hh_id, m1
    delete_household(hh_id)


class TestActivityEdgeCases:
    
    @pytest.mark.parametrize("value, expected", [
        (0.0, True),
        (0.0001, True),
        (-0.0001, False),
        (-100.0, False),
        (999999999.0, True)
    ])
    def test_log_activity_value_bounds(self, setup_edge_db, value, expected):
        hh_id, m1 = setup_edge_db
        act_id = log_activity(hh_id, "Energy", value, "kWh", 10.0, "2026-08-01")
        if expected:
            assert act_id is not None
        else:
            assert act_id is None

    @pytest.mark.parametrize("category, expected", [
        ("Energy", True),
        ("Water", True),
        ("Waste", True),
        ("Food", True),
        ("Transport", True),
        ("Shopping", True),
        ("Other", True),
        ("InvalidCat", False),
        ("", False),
        (" ", False),
        (None, False)
    ])
    def test_log_activity_categories(self, setup_edge_db, category, expected):
        hh_id, m1 = setup_edge_db
        
        # If category is None, Python might raise TypeError in log_activity if not typed properly.
        # Our function expects str, but let's check gracefully.
        try:
            act_id = log_activity(hh_id, category, 10.0, "unit", 10.0, "2026-08-01")
            if expected:
                assert act_id is not None
            else:
                assert act_id is None
        except Exception:
            assert not expected

    def test_log_activity_invalid_date(self, setup_edge_db):
        hh_id, m1 = setup_edge_db
        assert log_activity(hh_id, "Energy", 10.0, "kWh", 10.0, "08/01/2026") is None # wrong format
        assert log_activity(hh_id, "Energy", 10.0, "kWh", 10.0, "2026-13-01") is None # month 13
        assert log_activity(hh_id, "Energy", 10.0, "kWh", 10.0, "2026-02-30") is None # feb 30

    def test_activity_pagination(self, setup_edge_db):
        hh_id, m1 = setup_edge_db
        for i in range(150):
            log_activity(hh_id, "Energy", 1.0, "kWh", 1.0, f"2026-08-01")
            
        acts = get_activities(hh_id, limit=50, offset=0)
        assert len(acts) == 50
        
        acts_p2 = get_activities(hh_id, limit=50, offset=50)
        assert len(acts_p2) == 50
        
        acts_p3 = get_activities(hh_id, limit=100, offset=100)
        assert len(acts_p3) == 50

    def test_update_activity_invalid_data(self, setup_edge_db):
        hh_id, m1 = setup_edge_db
        act_id = log_activity(hh_id, "Energy", 10.0, "kWh", 10.0, "2026-08-01")
        assert act_id is not None
        
        assert not update_activity(act_id, category="Invalid")
        assert not update_activity(act_id, value=-50.0)
        assert not update_activity(act_id, activity_date="not-a-date")


class TestHouseholdEdgeCases:
    
    def test_household_name_update(self, setup_edge_db):
        hh_id, m1 = setup_edge_db
        assert update_household(hh_id, name="New Name", method="weighted", region="EU")
        hh = get_household(hh_id)
        assert hh["name"] == "New Name"
        assert hh["allocation_method"] == "weighted"
        
    def test_update_member_invalid(self, setup_edge_db):
        hh_id, m1 = setup_edge_db
        # Testing what happens if we remove the member
        assert remove_member(m1)
        
        # Now update member should fail or have no effect silently
        assert not update_member(m1, weight=5.0)

    def test_calculate_score_no_members(self, setup_edge_db):
        hh_id, m1 = setup_edge_db
        remove_member(m1)
        
        res = calculate_sustainability_score(hh_id)
        assert res["score"] == 100
        assert res["total_footprint"] == 0.0

    def test_member_breakdown_missing_member(self, setup_edge_db):
        hh_id, m1 = setup_edge_db
        
        # Log activity for m1
        log_activity(hh_id, "Energy", 100, "kWh", 100.0, "2026-08-01", member_id=m1)
        
        # Remove m1
        remove_member(m1)
        
        # Breakdown should handle it gracefully
        brk = get_member_contribution_breakdown(hh_id)
        # Because member is removed, their past activity might be detached (member_id set to NULL due to ON DELETE SET NULL)
        assert brk["shared_total"] == 100.0
        assert len(brk["members"]) == 0


class TestBudgetEdgeCases:
    
    @pytest.mark.parametrize("limit, expected", [
        (100.0, True),
        (0.1, True),
        (0.0, False),
        (-50.0, False)
    ])
    def test_budget_limit_bounds(self, setup_edge_db, limit, expected):
        hh_id, m1 = setup_edge_db
        b_id = set_budget(hh_id, "Overall", limit, "kg")
        if expected:
            assert b_id is not None
        else:
            assert b_id is None
            
    def test_budget_duplicate_upsert(self, setup_edge_db):
        hh_id, m1 = setup_edge_db
        b1 = set_budget(hh_id, "Energy", 100.0, "kg", "monthly")
        b2 = set_budget(hh_id, "Energy", 200.0, "kg", "monthly")
        
        # Should upsert, replacing the first one
        assert b1 == b2
        
        budgets = get_budgets(hh_id)
        assert len(budgets) == 1
        assert budgets[0]["limit_value"] == 200.0


class TestGamificationEdgeCases:
    
    def test_xp_negative(self, setup_edge_db):
        hh_id, m1 = setup_edge_db
        res = award_household_xp(hh_id, -50)
        assert res["total_xp"] == 0
        
    def test_challenge_already_completed(self, setup_edge_db):
        hh_id, m1 = setup_edge_db
        c_id = create_challenge(hh_id, "Test", "Test", 100)
        
        assert complete_challenge(c_id)
        assert not complete_challenge(c_id) # should fail second time

    def test_badge_duplicate(self, setup_edge_db):
        hh_id, m1 = setup_edge_db
        assert award_badge(hh_id, "Badge 1", "Desc")
        assert not award_badge(hh_id, "Badge 1", "Desc") # duplicate badgename
        
        badges = get_badges(hh_id)
        assert len(badges) == 1
