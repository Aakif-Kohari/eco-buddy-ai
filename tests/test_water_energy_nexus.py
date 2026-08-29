"""
Unit tests for Water-Energy Nexus and Greywater Simulator.
"""

import pytest
from src.energy.water_energy_nexus import WaterEnergyNexus
from src.environment.greywater_simulator import GreywaterSimulator


def test_calculate_heating_energy():
    nexus = WaterEnergyNexus(grid_carbon_intensity=0.4)
    # Heat 100 liters from 15C to 40C
    # Mass = 100 kg. Temp diff = 25C.
    # Energy kJ = 100 * 4.186 * 25 = 10465 kJ
    # Energy kWh = 10465 * 2.77778e-7 = 0.002907 kWh... wait, 1 kWh = 3600 kJ.
    # 10465 / 3600 = 2.907 kWh.
    energy = nexus.calculate_heating_energy(100.0, 40.0, 15.0)
    assert abs(energy - 2.907) < 0.01


def test_calculate_total_nexus_impact_cold_water():
    nexus = WaterEnergyNexus(grid_carbon_intensity=0.4)
    # 1000 liters (1 m3) of cold water
    impact = nexus.calculate_total_nexus_impact(1000.0, 15.0, is_hot_water=False)

    # Treatment energy: 1 m3 * 0.35 kWh/m3 = 0.35 kWh
    assert impact["treatment_energy_kwh"] == 0.35
    assert impact["heating_energy_kwh"] == 0.0
    assert impact["total_energy_kwh"] == 0.35
    assert impact["total_carbon_kg"] == 0.35 * 0.4  # 0.14


def test_compare_nexus_scenarios():
    nexus = WaterEnergyNexus(grid_carbon_intensity=0.4)
    comparison = nexus.compare_nexus_scenarios(
        baseline_liters=200.0,
        baseline_temp=45.0,
        optimized_liters=150.0,
        optimized_temp=40.0,
    )

    assert comparison["water_saved_liters"] == 50.0
    assert comparison["energy_saved_kwh"] > 0
    assert comparison["carbon_saved_kg"] > 0
    assert comparison["is_positive_impact"] is True


def test_greywater_generation():
    simulator = GreywaterSimulator(household_size=4, grid_carbon_intensity=0.4)
    potential = simulator.calculate_daily_greywater_potential()

    # 40 + 10 + 30 = 80 L/person/day
    assert potential["per_person_liters"] == 80.0
    assert potential["household_total_liters"] == 320.0


def test_greywater_recycling_savings():
    simulator = GreywaterSimulator(household_size=2, grid_carbon_intensity=0.4)
    results = simulator.simulate_recycling_savings(reuse_efficiency_pct=100.0)

    # Generation: 80 * 2 = 160 L
    # Demand: (30 + 20) * 2 = 100 L
    # Reused: min(160, 100) = 100 L
    assert results["daily_water_reused_liters"] == 100.0
    assert results["daily_water_saved_liters"] == 100.0
    assert results["daily_energy_saved_kwh"] > 0
    assert results["annual_carbon_saved_kg"] == results["daily_carbon_saved_kg"] * 365
