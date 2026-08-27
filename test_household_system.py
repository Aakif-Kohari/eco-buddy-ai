"""Tests for the Household Sustainability Management System."""

import pytest
import sqlite3
from datetime import datetime, timedelta, date

from household import init_household_db, create_household, add_member, get_members, update_member, remove_member, delete_household
from household_activities import (
    init_activities_db, log_activity, get_activities, get_activity_by_id,
    update_activity, delete_activity, get_category_breakdown,
    get_member_contribution_breakdown
)
from household_goals import (
    init_goals_db, create_goal, get_goals, get_goal,
    update_goal_progress, update_goal_status, delete_goal, check_overdue_goals
)
from household_metrics import calculate_sustainability_score, get_household_analytics_summary
from household_budgeting import (
    init_budgeting_db, set_budget, get_budgets, deactivate_budget, evaluate_budgets,
    check_and_generate_alerts, get_unread_alerts, mark_alerts_read
)
from household_gamification import (
    init_household_gamification_db, award_household_xp, _get_household_xp,
    award_badge, get_badges, create_challenge, complete_challenge, get_challenges
)
from household_recommendations import generate_household_recommendations


@pytest.fixture
def setup_db():
    """Setup and teardown in-memory databases or fresh test DB state."""
    init_household_db()
    init_activities_db()
    init_goals_db()
    init_budgeting_db()
    init_household_gamification_db()
    
    hh_id = create_household("Test House", 9999, method="equal", region="US")
    m1 = add_member(hh_id, "Alice", weight=1.0, role="Adult", user_id=9999)
    m2 = add_member(hh_id, "Bob", weight=1.0, role="Adult", user_id=None)
    m3 = add_member(hh_id, "Charlie", weight=0.5, role="Child", user_id=None)
    
    yield {"hh_id": hh_id, "members": [m1, m2, m3]}
    
    delete_household(hh_id)


class TestHouseholdManagement:
    def test_household_creation_and_deletion(self):
        init_household_db()
        hh_id = create_household("Temp House", 1111)
        assert hh_id is not None
        assert delete_household(hh_id)

    def test_member_updates(self, setup_db):
        m1 = setup_db["members"][0]
        assert update_member(m1, weight=2.0, role="Guest")
        # Assuming there is a get_member or similar, but we can verify via breakdown logic indirectly
        # or we just rely on the true return value for now.


class TestHouseholdActivities:
    def test_log_shared_activity(self, setup_db):
        hh_id = setup_db["hh_id"]
        act_id = log_activity(hh_id, "Energy", 100.0, "kWh", 50.0, "2026-08-01", "Shared power bill")
        assert act_id is not None
        
        act = get_activity_by_id(act_id)
        assert act["household_id"] == hh_id
        assert act["member_id"] is None
        assert act["category"] == "Energy"
        assert act["value"] == 100.0
        
    def test_log_individual_activity(self, setup_db):
        hh_id = setup_db["hh_id"]
        m1 = setup_db["members"][0]
        
        act_id = log_activity(hh_id, "Transport", 50.0, "mi", 20.0, "2026-08-02", member_id=m1)
        assert act_id is not None
        act = get_activity_by_id(act_id)
        assert act["member_id"] == m1
        assert act["member_name"] == "Alice"
        
    def test_invalid_category(self, setup_db):
        hh_id = setup_db["hh_id"]
        act_id = log_activity(hh_id, "SpaceTravel", 100, "km", 1000, "2026-08-01")
        assert act_id is None
        
    def test_negative_value(self, setup_db):
        hh_id = setup_db["hh_id"]
        act_id = log_activity(hh_id, "Energy", -50.0, "kWh", 10, "2026-08-01")
        assert act_id is None
        
    def test_update_activity(self, setup_db):
        hh_id = setup_db["hh_id"]
        act_id = log_activity(hh_id, "Food", 10, "meals", 25.0, "2026-08-01")
        
        success = update_activity(act_id, value=20, impact_kg_co2=50.0, is_shared=True)
        assert success
        
        act = get_activity_by_id(act_id)
        assert act["value"] == 20.0
        assert act["impact_kg_co2"] == 50.0
        assert act["member_id"] is None
        
    def test_delete_activity(self, setup_db):
        hh_id = setup_db["hh_id"]
        act_id = log_activity(hh_id, "Waste", 5, "bags", 10.0, "2026-08-01")
        assert delete_activity(act_id)
        assert get_activity_by_id(act_id) is None

    def test_get_activities_filtering(self, setup_db):
        hh_id = setup_db["hh_id"]
        m1 = setup_db["members"][0]
        log_activity(hh_id, "Energy", 10, "unit", 5, "2026-08-01")
        log_activity(hh_id, "Energy", 10, "unit", 5, "2026-08-02")
        log_activity(hh_id, "Transport", 10, "unit", 5, "2026-08-03", member_id=m1)
        
        # Test category filter
        assert len(get_activities(hh_id, category="Energy")) == 2
        # Test date filter
        assert len(get_activities(hh_id, start_date="2026-08-02", end_date="2026-08-03")) == 2
        # Test shared filter
        assert len(get_activities(hh_id, member_id=-1)) == 2
        # Test individual filter
        assert len(get_activities(hh_id, member_id=m1)) == 1

    def test_get_category_breakdown(self, setup_db):
        hh_id = setup_db["hh_id"]
        log_activity(hh_id, "Energy", 100, "kWh", 50.0, "2026-08-01")
        log_activity(hh_id, "Energy", 50, "kWh", 25.0, "2026-08-02")
        log_activity(hh_id, "Food", 10, "meals", 15.0, "2026-08-03")
        
        breakdown = get_category_breakdown(hh_id)
        assert breakdown["Energy"] == 75.0
        assert breakdown["Food"] == 15.0
        assert breakdown["Transport"] == 0.0

    def test_member_contribution_breakdown(self, setup_db):
        hh_id = setup_db["hh_id"]
        m1, m2, m3 = setup_db["members"]
        
        log_activity(hh_id, "Energy", 200, "kWh", 100.0, "2026-08-01")
        log_activity(hh_id, "Transport", 50, "mi", 20.0, "2026-08-02", member_id=m1)
        log_activity(hh_id, "Transport", 80, "mi", 30.0, "2026-08-03", member_id=m2)
        
        res = get_member_contribution_breakdown(hh_id)
        assert res["shared_total"] == 100.0
        assert res["members"][m1]["individual"] == 20.0
        assert res["members"][m1]["allocated"] == 40.0
        assert res["members"][m1]["total"] == 60.0
        assert res["members"][m2]["individual"] == 30.0
        assert res["members"][m2]["allocated"] == 40.0
        assert res["members"][m2]["total"] == 70.0
        assert res["members"][m3]["individual"] == 0.0
        assert res["members"][m3]["allocated"] == 20.0
        assert res["members"][m3]["total"] == 20.0
        assert res["household_total"] == 150.0


class TestHouseholdGoals:
    def test_create_and_get_goal(self, setup_db):
        hh_id = setup_db["hh_id"]
        g_id = create_goal(hh_id, "Reduce Energy", "energy", 100.0, "%")
        assert g_id is not None
        
        goal = get_goal(g_id)
        assert goal["title"] == "Reduce Energy"
        assert goal["status"] == "active"
        
    def test_create_invalid_goal(self, setup_db):
        hh_id = setup_db["hh_id"]
        assert create_goal(hh_id, "", "energy", 100.0, "%") is None
        assert create_goal(hh_id, "G", "invalid_metric", 100.0, "%") is None
        assert create_goal(hh_id, "G", "energy", 100.0, "%", deadline="2026/08/01") is None

    def test_update_goal_progress(self, setup_db):
        hh_id = setup_db["hh_id"]
        g_id = create_goal(hh_id, "Plant 10 Trees", "other", 10.0, "trees")
        
        update_goal_progress(g_id, 5.0)
        assert get_goal(g_id)["status"] == "active"
        
        update_goal_progress(g_id, 10.0)
        assert get_goal(g_id)["status"] == "completed"
        
    def test_update_goal_status(self, setup_db):
        hh_id = setup_db["hh_id"]
        g_id = create_goal(hh_id, "Test", "other", 10.0, "unit")
        assert update_goal_status(g_id, "abandoned")
        assert get_goal(g_id)["status"] == "abandoned"

    def test_delete_goal(self, setup_db):
        hh_id = setup_db["hh_id"]
        g_id = create_goal(hh_id, "Test", "other", 10.0, "unit")
        assert delete_goal(g_id)
        assert get_goal(g_id) is None
        
    def test_overdue_goals(self, setup_db):
        hh_id = setup_db["hh_id"]
        past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        g1 = create_goal(hh_id, "Past", "energy", 100, "kWh", deadline=past_date)
        
        future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        g2 = create_goal(hh_id, "Future", "energy", 100, "kWh", deadline=future_date)
        
        assert check_overdue_goals(hh_id) == 1
        assert get_goal(g1)["status"] == "failed"
        assert get_goal(g2)["status"] == "active"


class TestHouseholdBudgeting:
    def test_set_and_get_budget(self, setup_db):
        hh_id = setup_db["hh_id"]
        b_id = set_budget(hh_id, "Overall", 1000.0, "kg")
        assert b_id is not None
        
        budgets = get_budgets(hh_id)
        assert len(budgets) == 1
        assert budgets[0]["category"] == "Overall"
        assert budgets[0]["limit_value"] == 1000.0
        
    def test_set_invalid_budget(self, setup_db):
        hh_id = setup_db["hh_id"]
        assert set_budget(hh_id, "InvalidCat", 100, "kg") is None
        assert set_budget(hh_id, "Overall", 100, "kg", period="yearly") is None # invalid period string
        assert set_budget(hh_id, "Overall", -10, "kg") is None

    def test_deactivate_budget(self, setup_db):
        hh_id = setup_db["hh_id"]
        b_id = set_budget(hh_id, "Overall", 1000.0, "kg")
        assert deactivate_budget(b_id)
        assert len(get_budgets(hh_id, active_only=True)) == 0
        assert len(get_budgets(hh_id, active_only=False)) == 1

    def test_evaluate_budgets_and_alerts(self, setup_db):
        hh_id = setup_db["hh_id"]
        today = date.today().strftime("%Y-%m-%d")
        
        set_budget(hh_id, "Transport", 100.0, "kg")
        log_activity(hh_id, "Transport", 100, "mi", 85.0, today) # 85% - Warning
        
        evals = evaluate_budgets(hh_id)
        assert len(evals) == 1
        eval_data = list(evals.values())[0]
        assert eval_data["status"] == "warning"
        
        # Test alert generation
        alerts = check_and_generate_alerts(hh_id)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "warning"
        
        # Ensure we don't duplicate alerts in the same month
        alerts_dup = check_and_generate_alerts(hh_id)
        assert len(alerts_dup) == 0
        
        # Mark read
        unread = get_unread_alerts(hh_id)
        assert len(unread) == 1
        assert mark_alerts_read([unread[0]["id"]])
        assert len(get_unread_alerts(hh_id)) == 0


class TestHouseholdGamification:
    def test_award_xp_and_level_up(self, setup_db):
        hh_id = setup_db["hh_id"]
        res = award_household_xp(hh_id, 50)
        assert res["total_xp"] == 50
        assert res["level"] == 1
        assert not res["leveled_up"]
        
        res2 = award_household_xp(hh_id, 300)
        assert res2["total_xp"] == 350
        assert res2["level"] > 1
        assert res2["leveled_up"]

    def test_award_badge(self, setup_db):
        hh_id = setup_db["hh_id"]
        assert award_badge(hh_id, "First Step", "Logged an activity.")
        assert not award_badge(hh_id, "First Step", "Already have it.") # Should fail due to dup
        
        badges = get_badges(hh_id)
        assert len(badges) == 1
        assert badges[0]["badge_name"] == "First Step"

    def test_challenges(self, setup_db):
        hh_id = setup_db["hh_id"]
        c_id = create_challenge(hh_id, "Zero Waste Week", "No waste", 500)
        assert c_id is not None
        
        assert complete_challenge(c_id)
        
        chals = get_challenges(hh_id)
        assert len(chals) == 1
        assert chals[0]["status"] == "completed"
        
        # Verify XP was awarded
        xp_data = _get_household_xp(hh_id)
        assert xp_data["total_xp"] == 500


class TestHouseholdRecommendations:
    def test_recommendations(self, setup_db):
        hh_id = setup_db["hh_id"]
        # Trigger Transport recommendation
        log_activity(hh_id, "Transport", 1000, "mi", 1000.0, "2026-08-01")
        # Ensure no goals (triggers goal rec)
        
        recs = generate_household_recommendations(hh_id)
        assert len(recs) > 0
        assert any("Transport" in r for r in recs)
        assert any("Goal Setting" in r for r in recs)


class TestHouseholdMetrics:
    def test_sustainability_score_perfect(self, setup_db):
        hh_id = setup_db["hh_id"]
        res = calculate_sustainability_score(hh_id)
        assert res["score"] == 100
        assert res["total_footprint"] == 0.0
        
    def test_sustainability_score_high_impact(self, setup_db):
        hh_id = setup_db["hh_id"]
        log_activity(hh_id, "Transport", 5000, "mi", 5000.0, "2026-08-01")
        res = calculate_sustainability_score(hh_id)
        assert res["score"] == 0
        assert res["total_footprint"] == 5000.0

    def test_analytics_summary(self, setup_db):
        hh_id = setup_db["hh_id"]
        log_activity(hh_id, "Energy", 200, "kWh", 100.0, "2026-08-01")
        create_goal(hh_id, "Goal 1", "energy", 100, "kWh")
        
        summary = get_household_analytics_summary(hh_id)
        assert summary["metrics"]["total_members"] == 3
        assert summary["metrics"]["active_goals_count"] == 1
        assert summary["metrics"]["total_footprint_kg"] == 100.0
