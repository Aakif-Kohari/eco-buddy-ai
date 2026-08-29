import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock

from plugins.smart_grid.devices_advanced import SmartWaterHeater, WindTurbine, SmartPoolPump
from plugins.smart_grid.api import app
from plugins.smart_grid.ml_pipeline import GridMLPipeline

# --- Advanced Devices Tests ---

def test_smart_water_heater():
    heater = SmartWaterHeater("Test Heater", max_power_kw=4.5)
    
    # Tick with low temp to trigger heating
    heater.current_temp_c = 40.0
    state = heater.tick(3600.0, {}) # 1 hour
    assert state.status == "HEATING"
    assert state.power_kw == 4.5
    assert heater.current_temp_c > 40.0 # Should have heated up
    
    # Tick with high temp
    heater.current_temp_c = 65.0
    state2 = heater.tick(3600.0, {})
    assert state2.status == "IDLE"
    assert state2.power_kw == 0.0

def test_wind_turbine():
    turbine = WindTurbine("Test Turbine", max_power_kw=10.0)
    
    # Low wind
    state = turbine.tick(3600.0, {"wind_speed_m_s": 2.0})
    assert state.power_kw == 0.0
    assert state.status == "IDLE"
    
    # High wind (above rated)
    state2 = turbine.tick(3600.0, {"wind_speed_m_s": 15.0})
    assert state2.power_kw < 0.0 # Generation
    assert state2.status == "GENERATING"
    
    # Storm (cut out)
    state3 = turbine.tick(3600.0, {"wind_speed_m_s": 40.0})
    assert state3.power_kw == 0.0
    assert state3.status == "BRAKED_HIGH_WIND"

def test_smart_pool_pump():
    pump = SmartPoolPump("Test Pump", required_hours_per_day=4.0)
    
    # Mock localtime to prevent day rollover during the test
    with patch('time.localtime') as mock_localtime:
        mock_struct = time.struct_time((2023, 1, 1, 12, 0, 0, 0, 1, -1))
        mock_localtime.return_value = mock_struct
        
        # Force run
        pump.is_running = True
        state = pump.tick(7200.0, {}) # 2 hours
        assert state.status == "PUMPING"
        assert pump.hours_run_today == 2.0
        
        # Run past quota
        state2 = pump.tick(10800.0, {}) # 3 more hours
        assert pump.is_running is False
        assert state2.status == "QUOTA_MET"

# --- ML Pipeline Tests ---

def test_ml_pipeline_generation():
    pipeline = GridMLPipeline()
    X, y_solar, y_carbon = pipeline.generate_synthetic_training_data(samples=100)
    
    assert len(X) == 100
    assert len(y_solar) == 100
    assert len(y_carbon) == 100
    assert len(X[0]) == 4 # 4 features
    
def test_ml_pipeline_train_predict():
    pipeline = GridMLPipeline()
    
    # Only run if sklearn is available, otherwise mock it
    import plugins.smart_grid.ml_pipeline as ml_mod
    if ml_mod.SKLEARN_AVAILABLE:
        success = pipeline.train_models()
        assert success is True
        assert pipeline.is_trained is True
        
        solar, carbon = pipeline.predict_future(time.time(), horizon_hours=5)
        assert len(solar) == 5
        assert len(carbon) == 5
        assert "pred_solar" in solar[0]
        assert "pred_carbon" in carbon[0]
    else:
        pytest.skip("scikit-learn not installed")
