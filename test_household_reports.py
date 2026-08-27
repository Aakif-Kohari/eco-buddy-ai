"""Tests for Household Reports and Simulator."""

import pytest
from datetime import datetime

from household import init_household_db, create_household, add_member, delete_household
from household_activities import init_activities_db
from household_goals import init_goals_db
from household_budgeting import init_budgeting_db
from household_gamification import init_household_gamification_db
from household_data_simulator import simulate_historical_data, SIMULATION_BASELINES
from household_reports_generator import generate_markdown_report, generate_csv_export

@pytest.fixture
def setup_db():
    init_household_db()
    init_activities_db()
    init_goals_db()
    init_budgeting_db()
    init_household_gamification_db()
    
    hh_id = create_household("Sim House", 111)
    yield hh_id
    delete_household(hh_id)


class TestHouseholdSimulator:
    def test_simulation_generates_data(self, setup_db):
        hh_id = setup_db
        assert simulate_historical_data(hh_id, months_back=2, num_members=3)
        
        # Verify members created
        from household import get_members
        members = get_members(hh_id)
        assert len(members) == 3
        
        # Verify activities created
        from household_activities import get_activities
        acts = get_activities(hh_id)
        assert len(acts) > 10 # 3 months * (3 shared + 3 individual * 3 members) = ~30 activities
        
        # Verify goal created
        from household_goals import get_goals
        goals = get_goals(hh_id)
        assert len(goals) == 1

    def test_simulation_empty_household(self, setup_db):
        # Even with no prior members, simulation should inject the requested number of members
        hh_id = setup_db
        assert simulate_historical_data(hh_id, num_members=5)
        from household import get_members
        assert len(get_members(hh_id)) == 5


class TestHouseholdReports:
    def test_markdown_report_generation(self, setup_db):
        hh_id = setup_db
        # Generate some data
        simulate_historical_data(hh_id, months_back=1, num_members=2)
        
        md = generate_markdown_report(hh_id)
        
        assert "# Sustainability Report: Sim House" in md
        assert "## 1. Executive Summary" in md
        assert "## 2. Category Breakdown" in md
        assert "## 3. Member Contributions" in md
        assert "## 4. Goals Status" in md
        assert "## 5. Recent Activities" in md
        assert "Energy" in md
        assert "Transport" in md

    def test_csv_report_generation(self, setup_db):
        hh_id = setup_db
        simulate_historical_data(hh_id, months_back=1, num_members=2)
        
        csv_data = generate_csv_export(hh_id)
        
        # Check header
        assert "ID,Date,Category,Member,Value,Unit,Impact_kg_CO2,Description,Logged_At" in csv_data
        
        # Check some lines exist
        lines = csv_data.strip().split('\n')
        assert len(lines) > 5
        assert "Energy" in csv_data or "Transport" in csv_data

    def test_empty_household_report(self, setup_db):
        hh_id = setup_db
        # No simulation, completely empty
        
        md = generate_markdown_report(hh_id)
        assert "No activity data available" in md
        
        csv_data = generate_csv_export(hh_id)
        lines = csv_data.strip().split('\n')
        assert len(lines) == 1 # Only header
