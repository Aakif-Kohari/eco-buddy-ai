"""Tests for Household Competitions."""

import pytest
from datetime import datetime, timedelta

from household import init_household_db, create_household, delete_household
from household_activities import init_activities_db, log_activity
from household_competitions import (
    init_competitions_db, create_competition, join_competition,
    get_active_competitions, get_competition_leaderboard
)

@pytest.fixture
def setup_db():
    init_household_db()
    init_activities_db()
    init_competitions_db()
    
    hh_id_1 = create_household("Team Alpha", 111)
    hh_id_2 = create_household("Team Beta", 222)
    
    yield {"h1": hh_id_1, "h2": hh_id_2}
    
    delete_household(hh_id_1)
    delete_household(hh_id_2)


class TestHouseholdCompetitions:
    def test_create_and_get_competitions(self, setup_db):
        comp_id = create_competition(
            "Energy Savers Month", 
            "Use less energy!", 
            "Energy", 
            "2026-08-01", 
            "2026-08-31"
        )
        assert comp_id is not None
        
        comps = get_active_competitions()
        assert len(comps) > 0
        assert comps[-1]["title"] == "Energy Savers Month"

    def test_join_competition(self, setup_db):
        h1 = setup_db["h1"]
        comp_id = create_competition("Comp", "Desc", "Overall", "2026-08-01", "2026-08-31")
        
        assert join_competition(comp_id, h1)
        # Re-joining should ignore and return false or true depending on ignore logic, but our code returns False on duplicate due to rowcount=0
        assert not join_competition(comp_id, h1)

    def test_leaderboard(self, setup_db):
        h1 = setup_db["h1"]
        h2 = setup_db["h2"]
        
        comp_id = create_competition("Energy Duel", "Desc", "Energy", "2026-08-01", "2026-08-31")
        join_competition(comp_id, h1)
        join_competition(comp_id, h2)
        
        # Log activities within date range
        log_activity(h1, "Energy", 100, "kWh", 50.0, "2026-08-15")
        log_activity(h2, "Energy", 200, "kWh", 100.0, "2026-08-15")
        
        # Log activity outside date range (should be ignored)
        log_activity(h1, "Energy", 1000, "kWh", 500.0, "2026-09-05")
        
        # Leaderboard (lowest wins)
        lb = get_competition_leaderboard(comp_id)
        assert len(lb) == 2
        
        assert lb[0]["household_name"] == "Team Alpha"
        assert lb[0]["score"] == 50.0
        assert lb[0]["rank"] == 1
        
        assert lb[1]["household_name"] == "Team Beta"
        assert lb[1]["score"] == 100.0
        assert lb[1]["rank"] == 2
