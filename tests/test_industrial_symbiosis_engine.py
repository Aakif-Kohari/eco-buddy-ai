"""Unit tests for Industrial Symbiosis and Waste Heat Recovery Engine.
"""

import pytest
from src.environment.industrial_symbiosis_types import (
    IndustrialStreamParameters,
    HeatSourceStreamType,
    HeatRecoveryTechnology,
)
from src.environment.industrial_symbiosis_engine import IndustrialSymbiosisEngine
from src.environment.industrial_symbiosis_db import (
    init_industrial_symbiosis_db,
    save_industrial_plan,
    get_user_industrial_plans,
)


@pytest.fixture
def sample_furnace_stream():
    return IndustrialStreamParameters(
        facility_name="Steel Mill Exhaust",
        stream_type=HeatSourceStreamType.FLUE_GAS_HIGH_TEMP,
        mass_flow_rate_kg_s=12.5,
        inlet_temperature_c=450.0,
        target_outlet_temperature_c=120.0,
        recovery_tech=HeatRecoveryTechnology.PLATE_HEAT_EXCHANGER,
        annual_operating_hours=8000.0,
    )


def test_industrial_heat_recovery_calculation(sample_furnace_stream):
    result = IndustrialSymbiosisEngine.calculate_heat_recovery(sample_furnace_stream)

    assert result.thermal_power_available_kw > 0.0
    assert result.thermal_power_recovered_kw > 0.0
    assert result.annual_energy_recovered_mwh > 0.0
    assert result.annual_avoided_emissions_metric_tons > 0.0
    assert result.annual_cost_savings_usd > 0.0
    assert result.estimated_payback_years > 0.0
    assert result.system_thermal_efficiency_pct == 88.0


def test_orc_power_generation_technology():
    orc_params = IndustrialStreamParameters(
        facility_name="Cement Plant Kiln",
        stream_type=HeatSourceStreamType.FLUE_GAS_HIGH_TEMP,
        mass_flow_rate_kg_s=20.0,
        inlet_temperature_c=380.0,
        target_outlet_temperature_c=150.0,
        recovery_tech=HeatRecoveryTechnology.ORGANIC_RANKINE_CYCLE,
    )

    result = IndustrialSymbiosisEngine.calculate_heat_recovery(orc_params)
    assert result.system_thermal_efficiency_pct == 18.0
    assert result.annual_energy_recovered_mwh > 0.0


def test_industrial_symbiosis_db_persistence(tmp_path):
    db_file = str(tmp_path / "test_industrial.db")
    init_industrial_symbiosis_db(db_file)

    plan_id = save_industrial_plan(
        user_id=101,
        facility_name="Chemical Refinery",
        stream_type="Boiler Blowdown",
        recovered_kw=850.0,
        annual_mwh=6375.0,
        avoided_co2_tons=1287.75,
        annual_savings_usd=414375.0,
        payback_years=0.45,
        db_path=db_file,
    )

    assert plan_id > 0
    plans = get_user_industrial_plans(101, db_path=db_file)
    assert len(plans) == 1
    assert plans[0]["facility_name"] == "Chemical Refinery"
    assert plans[0]["recovered_kw"] == 850.0
