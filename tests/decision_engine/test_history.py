"""Tests for scenario history manager."""
import pytest
import os
from src.decision_engine.history import ScenarioHistoryManager
from src.decision_engine.models import ScenarioInputs, TransportMode

@pytest.fixture
def history_db(tmp_path):
    db_path = str(tmp_path / "test_history.db")
    mgr = ScenarioHistoryManager(db_path)
    yield mgr
    if os.path.exists(db_path):
        os.remove(db_path)

def test_save_and_load_scenario(history_db):
    inputs = ScenarioInputs()
    inputs.transport.primary_mode = TransportMode.CYCLING
    
    assert history_db.save_scenario(1, "scen1", "My Bike Scenario", inputs, False)
    
    scenarios = history_db.get_user_scenarios(1)
    assert len(scenarios) == 1
    sid, name, is_base, created, loaded_inputs = scenarios[0]
    
    assert sid == "scen1"
    assert name == "My Bike Scenario"
    assert loaded_inputs.transport.primary_mode == TransportMode.CYCLING

def test_delete_scenario(history_db):
    inputs = ScenarioInputs()
    history_db.save_scenario(2, "scen2", "Del Me", inputs)
    assert len(history_db.get_user_scenarios(2)) == 1
    
    history_db.delete_scenario("scen2")
    assert len(history_db.get_user_scenarios(2)) == 0
