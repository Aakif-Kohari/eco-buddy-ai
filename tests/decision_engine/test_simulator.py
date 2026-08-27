"""Tests for simulator orchestration."""
from src.decision_engine.simulator import DecisionSimulator, TimeHorizonEngine, TradeOffDetector
from src.decision_engine.models import ScenarioInputs, TransportMode

def test_tradeoff_detection():
    base = ScenarioInputs()
    alt = ScenarioInputs()
    alt.transport.primary_mode = TransportMode.EV_CAR
    
    result = DecisionSimulator.simulate(base, {"ev": alt})
    
    assert len(result.alternatives) == 1
    assert "ev" in result.trade_offs
    
    # We expect a Finance vs Carbon tradeoff (Cost up, CO2 down)
    tradeoffs = result.trade_offs["ev"]
    assert any(t.metric_improved == "Carbon Emissions" and t.metric_worsened == "Upfront Cost" for t in tradeoffs)

def test_rankings():
    base = ScenarioInputs()
    alt_cheap = ScenarioInputs()
    alt_cheap.transport.telecommute_days_per_week = 5
    alt_cheap.transport.primary_mode = TransportMode.WALKING
    alt_cheap.transport.weekend_travel_km = 0
    alt_cheap.transport.weekly_commute_km = 0
    
    alt_expensive = ScenarioInputs()
    alt_expensive.transport.primary_mode = TransportMode.EV_CAR
    
    result = DecisionSimulator.simulate(base, {"cheap": alt_cheap, "expensive": alt_expensive})
    
    # cheap should have lowest cost
    assert result.rankings["lowest_cost"][0] == "cheap"
