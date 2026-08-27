"""
Comprehensive Unit Tests for Smart Grid EV V2G Engine
"""

import pytest
from smart_grid_ev_v2g_engine import SmartGridEvV2gEngine, EvChargerAsset

def test_v2g_capacity_calculation():
    engine = SmartGridEvV2gEngine()
    chargers = [
        EvChargerAsset(
            charger_id="TEST-CHG-1",
            station_name="Test Station",
            charger_type="DC_FAST_V2G",
            connector_standard="CCS2_ISO15118",
            power_rating_kw=100.0,
            current_power_kw=80.0,
            connected_ev_vin="VIN123",
            ev_battery_capacity_kwh=100.0,
            ev_state_of_charge_pct=90.0,
            target_soc_pct=80.0,
            v2g_mode_active=True,
            grid_feedin_rate_kw=50.0,
            revenue_earned_usd=25.0
        )
    ]
    cap = engine.calculate_v2g_capacity(chargers)
    assert cap == 50.0

def test_register_depot_hub():
    engine = SmartGridEvV2gEngine()
    chargers = [
        EvChargerAsset(
            charger_id="TEST-CHG-2",
            station_name="Test Station 2",
            charger_type="LEVEL_2_BIDIRECTIONAL",
            connector_standard="NACS_BIDIRECTIONAL",
            power_rating_kw=19.2,
            current_power_kw=15.0,
            connected_ev_vin="VIN456",
            ev_battery_capacity_kwh=80.0,
            ev_state_of_charge_pct=85.0,
            target_soc_pct=80.0,
            v2g_mode_active=True,
            grid_feedin_rate_kw=10.0,
            revenue_earned_usd=12.0
        )
    ]
    hub = engine.register_depot_hub("HUB-99", "Hub Test", "Boston, MA", "Eversource", 2000.0, chargers)
    assert hub.hub_id == "HUB-99"
    assert hub.current_demand_kw == 10.0
