import pytest
from src.services.satellite_iot_agriculture import (
    HexCell,
    FluidDynamics,
    DroneAgent,
    AnalyticsEngine,
    PredictiveProgress,
    DashboardVisualizer
)

def test_evapotranspiration_equations():
    """Test Penman-Monteith approximation in HexCell."""
    cell = HexCell(0, 0, 0, 10.0, soil_moisture=0.8)
    # High temp, high wind, low humidity should cause high loss
    loss = cell.evapotranspiration(35.0, 20.0, 0.2)
    assert loss > 0
    assert cell.soil_moisture < 0.8
    assert cell.soil_moisture >= 0.0

def test_runoff_fluid_dynamics():
    """Test fertilizer runoff due to heavy rainfall."""
    cells = [
        HexCell(0, 0, 0, 10.0, nitrogen_level=100.0, soil_moisture=0.9),
        HexCell(1, 0, -1, 10.0, nitrogen_level=50.0, soil_moisture=0.9)
    ]
    
    # Heavy rainfall > 20.0 triggers runoff
    total_runoff = FluidDynamics.calculate_runoff(cells, 30.0)
    assert total_runoff > 0
    assert cells[0].nitrogen_level < 100.0
    assert cells[1].nitrogen_level < 50.0

    # Low rainfall does not trigger runoff
    total_runoff_low = FluidDynamics.calculate_runoff(cells, 10.0)
    assert total_runoff_low == 0.0

def test_drone_q_learning_reinforcement():
    """Test drone Q-Learning logic and spot spraying."""
    drone = DroneAgent("TEST-DRONE")
    cell = HexCell(0, 0, 0, 10.0, nitrogen_level=20.0) # Critical state
    
    # Force exploration off to rely on Q-table (which starts at 0, so max might be first action, we'll run it a few times)
    drone.exploration_rate = 0.0
    
    initial_n = cell.nitrogen_level
    initial_payload = drone.payload
    
    # Force the action to SPRAY to test logic
    state = drone._get_state_key(cell.nitrogen_level)
    drone.update_q_value(state, "SPRAY", 10.0, "LOW")
    
    action = drone.choose_action(state)
    assert action == "SPRAY"
    
    reward = drone.act_on_cell(cell)
    assert reward == 10.0  # Reward for spraying CRITICAL
    assert cell.nitrogen_level == initial_n + 10.0
    assert drone.payload == initial_payload - 1.0
    
def test_predictive_progress_and_analytics():
    """Test trend detection and yield estimation."""
    cells = [HexCell(0, 0, 0, 10.0, topsoil_depth=30.0, nitrogen_level=100.0, soil_moisture=0.5)]
    engine = AnalyticsEngine(cells)
    engine.snapshot()
    
    cells[0].topsoil_depth = 25.0
    engine.snapshot()
    
    recs = engine.get_recommendations()
    # It takes > 5 history points to recommend crop rotation for topsoil
    assert len(recs) == 0
    
    for _ in range(6):
        cells[0].topsoil_depth -= 1.0
        engine.snapshot()
        
    recs = engine.get_recommendations()
    assert any("crop rotation schedule" in r for r in recs)
    
    pred = PredictiveProgress(engine)
    yield_est = pred.estimate_harvest_yield()
    assert yield_est > 0
    
    depletion_year = pred.predict_topsoil_depletion_year(2026)
    assert depletion_year >= 2026
