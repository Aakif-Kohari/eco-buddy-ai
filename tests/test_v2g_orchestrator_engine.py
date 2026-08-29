"""Unit tests for V2G Energy Orchestration Engine.
"""

import pytest
from src.utils.v2g_orchestrator_types import (
    FleetVehicleConfig,
    BatteryChemistry,
    ChargingTariffScheme,
    GridServiceMode,
)
from src.utils.v2g_orchestrator_engine import V2GOrchestratorEngine


@pytest.fixture
def default_fleet_config():
    return FleetVehicleConfig(
        vehicle_id="ev_test",
        battery_capacity_kwh=80.0,
        chemistry=BatteryChemistry.LFP,
        max_charge_power_kw=11.0,
        max_discharge_power_kw=11.0,
        round_trip_efficiency_pct=92.0,
    )


def test_v2g_simulation_arbitrage(default_fleet_config):
    result = V2GOrchestratorEngine.simulate_fleet(
        fleet_size=10,
        vehicle_cfg=default_fleet_config,
        tariff_scheme=ChargingTariffScheme.TIME_OF_USE_AGGRESSIVE,
        service_mode=GridServiceMode.ARBITRAGE_ONLY,
        rooftop_solar_peak_kw=50.0,
    )

    assert result.fleet_size == 10
    assert result.total_fleet_capacity_kwh == 800.0
    assert result.annual_grid_revenue_usd > 0.0
    assert result.annual_co2_avoided_tons > 0.0
    assert result.estimated_battery_cycle_life_years > 5.0
    assert len(result.hourly_schedule) == 24


def test_lfp_vs_nmc_lifespan(default_fleet_config):
    cfg_nmc = FleetVehicleConfig(
        vehicle_id="ev_nmc",
        battery_capacity_kwh=80.0,
        chemistry=BatteryChemistry.NMC_811,
        max_charge_power_kw=11.0,
        max_discharge_power_kw=11.0,
        round_trip_efficiency_pct=92.0,
    )

    res_lfp = V2GOrchestratorEngine.simulate_fleet(
        fleet_size=5,
        vehicle_cfg=default_fleet_config,
        tariff_scheme=ChargingTariffScheme.TIME_OF_USE_MODERATE,
        service_mode=GridServiceMode.ARBITRAGE_ONLY,
        rooftop_solar_peak_kw=0.0,
    )
    res_nmc = V2GOrchestratorEngine.simulate_fleet(
        fleet_size=5,
        vehicle_cfg=cfg_nmc,
        tariff_scheme=ChargingTariffScheme.TIME_OF_USE_MODERATE,
        service_mode=GridServiceMode.ARBITRAGE_ONLY,
        rooftop_solar_peak_kw=0.0,
    )

    assert res_lfp.estimated_battery_cycle_life_years > res_nmc.estimated_battery_cycle_life_years
    assert res_lfp.annual_battery_degradation_pct < res_nmc.annual_battery_degradation_pct
