"""Unit tests for Industrial Waste Heat Recovery and ORC Engine.
"""

import pytest
from src.environment.waste_heat_recovery_types import (
    IndustrialPlantParameters,
    HeatSourceIndustry,
    WorkingFluid,
    RecoveryApplication,
)
from src.environment.waste_heat_recovery_engine import WasteHeatRecoveryEngine


@pytest.fixture
def steel_mill_plant():
    return IndustrialPlantParameters(
        plant_name="Steelworks Unit 1",
        industry_type=HeatSourceIndustry.STEEL_REHEATING,
        exhaust_gas_temp_c=480.0,
        exhaust_mass_flow_kg_s=20.0,
        working_fluid=WorkingFluid.CYCLOPENTANE,
        application=RecoveryApplication.ORC_ELECTRICITY,
        annual_operating_hours=8000.0,
        electricity_export_tariff_usd_kwh=0.12,
    )


def test_whr_calculation_orc(steel_mill_plant):
    result = WasteHeatRecoveryEngine.calculate_recovery(steel_mill_plant)

    assert result.recoverable_thermal_heat_kw > 0.0
    assert result.gross_electrical_power_kw > 0.0
    assert result.net_thermal_efficiency_pct > 10.0
    assert result.annual_electricity_generated_mwh > 0.0
    assert result.annual_cost_savings_usd > 0.0
    assert result.annual_co2_avoided_tons > 0.0
    assert result.simple_payback_years > 0.0
    assert len(result.pinch_points) == 2
    assert len(result.cashflow_10yr) == 10


def test_district_heating_mode(steel_mill_plant):
    plant_heat = IndustrialPlantParameters(
        plant_name="Heat Net",
        industry_type=HeatSourceIndustry.STEEL_REHEATING,
        exhaust_gas_temp_c=300.0,
        exhaust_mass_flow_kg_s=15.0,
        working_fluid=WorkingFluid.WATER_STEAM,
        application=RecoveryApplication.DISTRICT_HEATING,
        annual_operating_hours=6000.0,
    )
    result = WasteHeatRecoveryEngine.calculate_recovery(plant_heat)

    assert result.gross_electrical_power_kw == 0.0
    assert result.recoverable_thermal_heat_kw > 0.0
    assert result.annual_cost_savings_usd > 0.0
    assert result.annual_co2_avoided_tons > 0.0
