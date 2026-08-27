"""Tests for Household Scenario Modeling."""

import pytest
from datetime import datetime, timedelta

from household import init_household_db, create_household, add_member, delete_household
from household_activities import init_activities_db, log_activity
from household_goals import init_goals_db, create_goal
from household_scenario_modeling import (
    simulate_scenarios, calculate_payback_period, 
    recommend_top_scenario, project_goal_achievement, SCENARIO_PRESETS
)

@pytest.fixture
def setup_db():
    init_household_db()
    init_activities_db()
    init_goals_db()
    
    hh_id = create_household("Sim House", 111)
    m1 = add_member(hh_id, "Alice")
    
    yield hh_id
    
    delete_household(hh_id)


class TestScenarioModeling:
    def test_simulate_scenarios_empty(self, setup_db):
        hh_id = setup_db
        # No activities logged, should return empty list
        results = simulate_scenarios(hh_id)
        assert len(results) == 0

    def test_simulate_scenarios_with_data(self, setup_db):
        hh_id = setup_db
        
        # Log massive transport and energy
        log_activity(hh_id, "Transport", 1000, "mi", 1000.0, "2026-08-01")
        log_activity(hh_id, "Energy", 500, "kWh", 500.0, "2026-08-02")
        
        results = simulate_scenarios(hh_id)
        assert len(results) == len(SCENARIO_PRESETS)
        
        # The top scenario should be buy_ev (reduces 1000 by 65% = 650, increases 500 by 15% = 75, net reduction = 575)
        # Solar reduces 500 by 80% = 400.
        # So EV is top.
        
        top = results[0]
        assert top["id"] == "buy_ev"
        assert top["reduction_kg"] == 575.0
        assert top["projected_total_kg"] == (1500.0 - 575.0)

    def test_calculate_payback_period(self, setup_db):
        hh_id = setup_db
        log_activity(hh_id, "Energy", 1000, "kWh", 1000.0, "2026-08-01")
        
        # Solar panel cost is 12000.
        # Energy footprint 1000 kg / month.
        # Solar reduces by 80% = 800 kg / month = 9.6 tons / year.
        # 9.6 tons * $50/ton = $480 savings / year.
        # Payback = 12000 / 480 = 25 years.
        
        payback = calculate_payback_period("solar_panels", hh_id, carbon_price_per_ton=50.0)
        assert payback is not None
        assert 24.0 < payback < 26.0
        
        # Invalid scenario
        assert calculate_payback_period("invalid_scenario", hh_id) is None

    def test_recommend_top_scenario(self, setup_db):
        hh_id = setup_db
        log_activity(hh_id, "Food", 100, "meals", 2000.0, "2026-08-01")
        
        rec = recommend_top_scenario(hh_id)
        assert rec is not None
        assert rec["id"] == "vegan_household" # 50% of 2000 = 1000 reduction

    def test_project_goal_achievement(self, setup_db):
        hh_id = setup_db
        g_id = create_goal(hh_id, "Reduce Food", "food", 1000.0, "kg")
        
        # Test vegan
        proj = project_goal_achievement(hh_id, g_id, "vegan_household")
        assert proj["helps"] is True
        assert proj["projected_reduction_pct"] == 50.0
        
        # Test EV (doesn't help food)
        proj_ev = project_goal_achievement(hh_id, g_id, "buy_ev")
        assert proj_ev["helps"] is False
        
        # Invalid goal
        assert project_goal_achievement(hh_id, 9999, "vegan_household")["helps"] is False
