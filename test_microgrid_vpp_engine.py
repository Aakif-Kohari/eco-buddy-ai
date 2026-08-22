"""
Unit Test Suite for Microgrid & Virtual Power Plant Engine
"""

import pytest
from microgrid_vpp_engine import MicrogridVppEngine, DistributedEnergyResource

def test_vpp_efficiency_calculation():
    engine = MicrogridVppEngine()
    assets = [
        DistributedEnergyResource(
            asset_id="DER-1",
            asset_name="Solar PV",
            asset_type="SOLAR_PV",
            capacity_kw=1000.0,
            current_output_kw=800.0,
            state_of_charge_pct=100.0,
            operating_status="ACTIVE",
            carbon_offset_kg_per_hr=300.0
        )
    ]
    eff = engine.calculate_vpp_efficiency(assets)
    assert eff == 80.0

def test_register_facility_profile():
    engine = MicrogridVppEngine()
    assets = [
        DistributedEnergyResource(
            asset_id="DER-2",
            asset_name="BESS Unit",
            asset_type="BESS",
            capacity_kw=500.0,
            current_output_kw=400.0,
            state_of_charge_pct=95.0,
            operating_status="ACTIVE",
            carbon_offset_kg_per_hr=150.0
        )
    ]
    profile = engine.register_facility_profile("GRID-100", "Facility X", "Denver, CO", 1000.0, assets)
    assert profile.microgrid_id == "GRID-100"
    assert profile.total_capacity_kw == 500.0
