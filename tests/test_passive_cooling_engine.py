"""Unit tests for Passive Cooling and Thermal Comfort Simulation Engine.
"""

import pytest
from passive_cooling_types import (
    BuildingParameters,
    ClimateZone,
    InsulationLevel,
    ShadingStrategy,
    VentilationMode,
)
from passive_cooling_engine import PassiveCoolingEngine


@pytest.fixture
def standard_building():
    return BuildingParameters(
        building_name="Test Residence",
        floor_area_m2=200.0,
        ceiling_height_m=3.0,
        window_to_wall_ratio=0.30,
        climate_zone=ClimateZone.HOT_ARID,
        insulation_level=InsulationLevel.HIGH_PERFORMANCE,
        shading_strategy=ShadingStrategy.LOUVERS,
        ventilation_mode=VentilationMode.NIGHT_PURGE,
        occupant_count=4,
        electricity_cost_kwh=0.20,
    )


def test_weather_generation_diurnal_bounds():
    profile = PassiveCoolingEngine.generate_diurnal_weather_profile(ClimateZone.HOT_ARID)
    assert len(profile) == 24
    for temp, hum, sol in profile:
        assert 10.0 <= temp <= 50.0
        assert 5.0 <= hum <= 100.0
        assert 0.0 <= sol <= 1200.0


def test_pmv_ppd_calculation():
    pmv, ppd = PassiveCoolingEngine.calculate_pmv_ppd(24.5, 50.0, air_vel=0.2)
    assert -0.5 <= pmv <= 0.5
    assert ppd <= 15.0


def test_simulation_energy_savings(standard_building):
    result = PassiveCoolingEngine.simulate(standard_building)
    assert result.annual_cooling_energy_baseline_kwh > result.annual_cooling_energy_passive_kwh
    assert result.annual_energy_saved_kwh > 0.0
    assert result.energy_savings_percentage > 10.0
    assert result.annual_cost_savings_usd > 0.0
    assert result.annual_co2_abatement_kg > 0.0
    assert result.peak_indoor_temp_reduction_c > 0.0
    assert len(result.hourly_profiles) == 24
    assert result.simple_payback_years > 0.0


def test_uninsulated_vs_passive_house():
    p_uninsulated = BuildingParameters(
        building_name="Base",
        floor_area_m2=150.0,
        ceiling_height_m=2.8,
        window_to_wall_ratio=0.4,
        climate_zone=ClimateZone.HOT_HUMID,
        insulation_level=InsulationLevel.UNINSULATED,
        shading_strategy=ShadingStrategy.NONE,
        ventilation_mode=VentilationMode.SEALED_AC,
        occupant_count=3,
    )
    p_passive = BuildingParameters(
        building_name="Eco",
        floor_area_m2=150.0,
        ceiling_height_m=2.8,
        window_to_wall_ratio=0.4,
        climate_zone=ClimateZone.HOT_HUMID,
        insulation_level=InsulationLevel.PASSIVE_HOUSE,
        shading_strategy=ShadingStrategy.LOUVERS,
        ventilation_mode=VentilationMode.NIGHT_PURGE,
        occupant_count=3,
    )
    res_base = PassiveCoolingEngine.simulate(p_uninsulated)
    res_pass = PassiveCoolingEngine.simulate(p_passive)

    assert res_pass.annual_cooling_energy_passive_kwh < res_base.annual_cooling_energy_baseline_kwh
    assert res_pass.peak_indoor_temp_reduction_c > res_base.peak_indoor_temp_reduction_c
