"""
Unit Tests for Industrial CCUS Engine
"""

import pytest
from industrial_ccus_engine import IndustrialCcusEngine, CcusCaptureUnit

def test_ccus_total_capture():
    engine = IndustrialCcusEngine()
    units = [
        CcusCaptureUnit(
            unit_id="U1",
            unit_name="Unit 1",
            technology_type="AMINE",
            flue_gas_flow_rate_m3_hr=100.0,
            co2_concentration_pct=10.0,
            capture_efficiency_pct=90.0,
            daily_co2_captured_metric_tons=100.0,
            parasitic_energy_penalty_mwh_per_ton=2.0,
            solvent_degradation_rate_ppm=0.5,
            operating_status="ACTIVE"
        )
    ]
    tot = engine.calculate_total_capture(units)
    assert tot == 100.0

def test_register_facility():
    engine = IndustrialCcusEngine()
    units = [
        CcusCaptureUnit(
            unit_id="U2",
            unit_name="Unit 2",
            technology_type="DAC",
            flue_gas_flow_rate_m3_hr=200.0,
            co2_concentration_pct=0.04,
            capture_efficiency_pct=85.0,
            daily_co2_captured_metric_tons=50.0,
            parasitic_energy_penalty_mwh_per_ton=1.5,
            solvent_degradation_rate_ppm=0.1,
            operating_status="ACTIVE"
        )
    ]
    fac = engine.register_facility_profile("F-10", "Steel Plant X", "STEEL_PRODUCTION", "Gary, IN", 200000.0, units)
    assert fac.facility_id == "F-10"
    assert fac.annual_net_captured_tons == 18250.0
