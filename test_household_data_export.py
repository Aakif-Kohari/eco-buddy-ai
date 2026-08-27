"""Tests for Household Data Export and Import System."""

import pytest
import json

from household import init_household_db, create_household, delete_household, add_member
from household_activities import init_activities_db, log_activity
from household_goals import init_goals_db, create_goal
from household_budgeting import init_budgeting_db, set_budget
from household_gamification import init_household_gamification_db, award_badge
from household_data_export import export_household_data_json, calculate_data_completeness

@pytest.fixture
def setup_db():
    init_household_db()
    init_activities_db()
    init_goals_db()
    init_budgeting_db()
    init_household_gamification_db()
    
    hh_id = create_household("Export House", 111)
    yield hh_id
    delete_household(hh_id)


class TestDataExport:
    def test_export_json_empty(self, setup_db):
        hh_id = setup_db
        json_str = export_household_data_json(hh_id)
        assert json_str is not None
        
        data = json.loads(json_str)
        assert data["household"]["name"] == "Export House"
        assert len(data["members"]) == 0
        assert len(data["activities"]) == 0
        assert len(data["goals"]) == 0

    def test_export_json_populated(self, setup_db):
        hh_id = setup_db
        m1 = add_member(hh_id, "Alice")
        log_activity(hh_id, "Energy", 100, "kWh", 50.0, "2026-08-01")
        create_goal(hh_id, "Goal 1", "energy", 100, "kWh")
        set_budget(hh_id, "Energy", 200, "kWh")
        award_badge(hh_id, "First Badge", "Desc")
        
        json_str = export_household_data_json(hh_id)
        assert json_str is not None
        
        data = json.loads(json_str)
        assert len(data["members"]) == 1
        assert len(data["activities"]) == 1
        assert len(data["goals"]) == 1
        assert len(data["budgets"]) == 1
        assert len(data["gamification"]["badges"]) == 1
        
        assert data["activities"][0]["category"] == "Energy"
        assert data["goals"][0]["title"] == "Goal 1"

    def test_calculate_completeness(self, setup_db):
        hh_id = setup_db
        assert calculate_data_completeness(hh_id) == 0.0
        
        add_member(hh_id, "Alice")
        assert calculate_data_completeness(hh_id) == 20.0
        
        log_activity(hh_id, "Energy", 100, "kWh", 50.0, "2026-08-01")
        assert calculate_data_completeness(hh_id) == 40.0
        
        create_goal(hh_id, "Goal 1", "energy", 100, "kWh")
        assert calculate_data_completeness(hh_id) == 60.0
        
        set_budget(hh_id, "Energy", 200, "kWh")
        assert calculate_data_completeness(hh_id) == 80.0
        
        award_badge(hh_id, "First Badge", "Desc")
        assert calculate_data_completeness(hh_id) == 100.0
