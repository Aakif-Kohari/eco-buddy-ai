import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock

from plugins.smart_grid.devices import SolarPanel, BatterySystem, EVCharger, SmartHVAC, SmartAppliance
from plugins.smart_grid.telemetry import MessageBroker, TelemetryEngine
from plugins.smart_grid.forecaster import SmartGridForecaster
from plugins.smart_grid.optimizer import GridOptimizer
from plugins.smart_grid.engine import SmartGridSimulation

# --- 1. Device Tests ---

def test_solar_panel():
    solar = SolarPanel("Test Solar", max_power_kw=5.0)
    
    # Tick with 0 irradiance (night)
    state = solar.tick(3600.0, {"solar_irradiance_w_m2": 0.0})
    assert state.power_kw == 0.0
    assert state.status == "IDLE"
    
    # Tick with high irradiance (noon)
    state2 = solar.tick(3600.0, {"solar_irradiance_w_m2": 1000.0})
    assert state2.power_kw < 0.0 # Generation is negative
    assert state2.status == "GENERATING"
    
def test_battery_system():
    batt = BatterySystem("Test Battery", capacity_kwh=10.0, max_charge_kw=5.0, max_discharge_kw=5.0)
    assert batt.current_charge_kwh == 5.0 # Starts at 50%
    
    # Charge it
    batt.set_mode("CHARGE")
    state = batt.tick(3600.0, {}) # 1 hour at 5kW
    assert state.power_kw == 5.0
    assert batt.current_charge_kwh == 10.0 # Full
    
    # Discharge it
    batt.set_mode("DISCHARGE")
    state2 = batt.tick(1800.0, {}) # 30 mins at 5kW = 2.5kWh
    assert state2.power_kw == -5.0
    assert batt.current_charge_kwh == 7.5

def test_ev_charger():
    ev = EVCharger("Test EV", max_power_kw=7.0)
    
    # Unplugged tick
    assert ev.tick(3600.0, {}).power_kw == 0.0
    
    ev.plug_in_car(14.0)
    ev.start_charging()
    
    # 1 hour tick
    state = ev.tick(3600.0, {})
    assert state.power_kw == 7.0
    assert ev.session_delivered_kwh == 7.0
    assert state.status == "CHARGING"
    
    # 2nd hour tick (finishes charging)
    state2 = ev.tick(3600.0, {})
    assert state2.power_kw == 7.0
    assert ev.session_delivered_kwh == 14.0
    assert state2.status == "CHARGING"
    
    # 3rd hour tick (registers complete)
    state3 = ev.tick(3600.0, {})
    assert state3.status == "COMPLETE"
    
def test_smart_hvac():
    hvac = SmartHVAC("Test HVAC", max_power_kw=3.0, target_temp_c=22.0)
    
    # Very hot outside, indoor should heat up, HVAC should turn on cooling
    hvac.current_indoor_temp_c = 25.0
    state = hvac.tick(3600.0, {"outdoor_temperature_c": 35.0})
    assert state.status == "COOLING"
    assert state.power_kw > 0.0
    assert hvac.current_indoor_temp_c < 25.0 # Should have cooled down

def test_smart_appliance():
    app = SmartAppliance("Washer", max_power_kw=2.0)
    app.start_cycle()
    
    # Phase 1 is 900 seconds
    state = app.tick(900.0, {})
    assert state.status == "PHASE_1"
    
    # Phase 2 
    state2 = app.tick(1.0, {})
    assert state2.status == "PHASE_2"

# --- 2. Telemetry and Broker Tests ---

@pytest.mark.asyncio
async def test_message_broker():
    broker = MessageBroker()
    received = []
    
    async def callback(topic, payload):
        received.append((topic, payload))
        
    await broker.subscribe("home/devices/#", callback)
    
    await broker.publish("home/devices/solar/123/state", {"power": 5.0})
    await asyncio.sleep(0.1) # Yield to event loop
    
    assert len(received) == 1
    assert received[0][1]["power"] == 5.0
    
    # Test unsubscribe
    await broker.unsubscribe("home/devices/#", callback)
    await broker.publish("home/devices/solar/123/state", {"power": 2.0})
    await asyncio.sleep(0.1)
    
    assert len(received) == 1 # Shouldn't increase

@pytest.mark.asyncio
async def test_telemetry_engine():
    broker = MessageBroker()
    engine = TelemetryEngine(broker)
    engine.poll_interval_seconds = 0.05
    
    ev = EVCharger("Mock EV")
    engine.register_device(ev)
    
    await engine.start()
    await asyncio.sleep(0.15)
    await engine.stop()
    
    assert len(broker.message_history) >= 2 # Should have polled at least twice

# --- 3. Forecaster Tests ---

def test_forecaster():
    forecaster = SmartGridForecaster(region="US-CA")
    start_ts = time.time()
    
    # Carbon forecast
    carbon = forecaster.predict_carbon_intensity(start_ts, horizon_hours=24)
    assert len(carbon) == 96 # 24 hours * 4 (15 min intervals)
    assert carbon[0]["predicted_g_co2_per_kwh"] > 0
    
    # Solar forecast
    solar = forecaster.predict_solar_irradiance(start_ts, horizon_hours=24)
    assert len(solar) == 96
    
    # Check night time is 0
    night_samples = [s for s in solar if s["hour_of_day"] < 5.0 or s["hour_of_day"] > 20.0]
    for s in night_samples:
        assert s["predicted_irradiance_w_m2"] == 0.0

# --- 4. Optimizer Tests ---

def test_grid_optimizer():
    forecaster = SmartGridForecaster()
    opt = GridOptimizer(forecaster)
    
    ev = EVCharger("Test EV", max_power_kw=7.0)
    ev.plug_in_car(20.0)
    opt.register_device(ev)
    
    batt = BatterySystem("Test Batt", capacity_kwh=10.0, max_charge_kw=5.0, max_discharge_kw=5.0)
    opt.register_device(batt)
    
    report = opt.run_optimization(time.time())
    
    assert "ev_commands" in report
    assert "battery_commands" in report
    assert report["forecast_horizon_hours"] == 12

# --- 5. Full Simulation Engine Test ---

@pytest.mark.asyncio
async def test_smart_grid_simulation():
    # Run the massive simulation for 2 "real" seconds at 3600x speed
    # Which equals 2 hours of simulated time
    sim = SmartGridSimulation(speed_multiplier=3600.0)
    
    await sim.run_simulation(duration_real_seconds=2.0)
    
    assert sim.is_running is False
    assert len(sim.devices) == 5
    
    # Ensure telemetry loop populated the broker
    assert len(sim.broker.message_history) > 0
