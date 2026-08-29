"""
Unit Tests for Landfill Methane Engine
"""

import pytest
from src.environment.landfill_methane_engine import LandfillMethaneEngine, GasWellheadSensor

def test_calculate_ch4_flow():
    engine = LandfillMethaneEngine()
    wells = [
        GasWellheadSensor(
            well_id="W1",
            well_name="Well 1",
            methane_concentration_pct=50.0,
            carbon_dioxide_pct=40.0,
            oxygen_pct=0.5,
            flow_rate_cfm=100.0,
            vacuum_pressure_inches_wcat=-10.0,
            temperature_celsius=35.0,
            well_status="OPTIMAL_EXTRACTION"
        )
    ]
    flow = engine.calculate_total_ch4_flow_cfm(wells)
    assert flow == 50.0

def test_register_landfill():
    engine = LandfillMethaneEngine()
    wells = [
        GasWellheadSensor(
            well_id="W2",
            well_name="Well 2",
            methane_concentration_pct=60.0,
            carbon_dioxide_pct=35.0,
            oxygen_pct=0.2,
            flow_rate_cfm=200.0,
            vacuum_pressure_inches_wcat=-15.0,
            temperature_celsius=36.0,
            well_status="OPTIMAL_EXTRACTION"
        )
    ]
    fac = engine.register_landfill_facility("LF-99", "Landfill X", "Miami, FL", 200.0, 5000000.0, wells)
    assert fac.facility_id == "LF-99"
    assert fac.rng_production_mcf_day > 0.0
