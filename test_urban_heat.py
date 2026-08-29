"""
Unit tests for Urban Heat Mitigation Calculator and Green Infrastructure DB.
"""

import pytest
from urban_heat_mitigation import UrbanHeatMitigationCalculator
from green_infrastructure_db import GreenInfrastructureDB


def test_db_retrieval():
    db = GreenInfrastructureDB()
    details = db.get_option_details("mature_tree_canopy")

    assert details is not None
    assert details["name"] == "Mature Tree Planting"
    assert details["cooling_effect_c"] == 1.5
    assert db.get_option_display_name("green_roof_extensive") == "Extensive Green Roof"


def test_mitigation_calculator_add_measure():
    calc = UrbanHeatMitigationCalculator(
        baseline_temp_c=35.0, annual_hvac_cost_usd=1000.0, property_area_sqm=100.0
    )
    success = calc.add_measure("mature_tree_canopy", quantity=2.0)

    assert success is True
    assert len(calc.installed_measures) == 1
    assert calc.installed_measures[0]["cooling_effect_c"] == 3.0  # 1.5 * 2
    assert calc.installed_measures[0]["installation_cost_usd"] == 1000.0  # 500 * 2


def test_mitigation_calculator_roi_positive():
    calc = UrbanHeatMitigationCalculator(
        baseline_temp_c=35.0, annual_hvac_cost_usd=2000.0, property_area_sqm=200.0
    )
    # Add a measure with high cooling and reasonable cost
    calc.add_measure("green_roof_extensive", quantity=50.0)  # 50 sqm

    result = calc.calculate_roi()

    assert result["total_cooling_effect_c"] == 2.5  # 0.05 * 50
    assert result["projected_temp_c"] == 32.5
    assert result["annual_hvac_savings_usd"] > 0.0
    assert result["total_installation_cost_usd"] == 7500.0  # 150 * 50


def test_mitigation_calculator_empty():
    calc = UrbanHeatMitigationCalculator(
        baseline_temp_c=30.0, annual_hvac_cost_usd=500.0, property_area_sqm=50.0
    )
    result = calc.calculate_roi()

    assert result["total_cooling_effect_c"] == 0.0
    assert result["projected_temp_c"] == 30.0
    assert result["twenty_year_net_savings_usd"] == 0.0


def test_mitigation_payback_calculation():
    calc = UrbanHeatMitigationCalculator(
        baseline_temp_c=40.0, annual_hvac_cost_usd=3000.0, property_area_sqm=300.0
    )
    calc.add_measure("rain_garden", quantity=20.0)  # Low cost, decent cooling

    result = calc.calculate_roi()

    # Installation: 80 * 20 = 1600
    # Cooling: 0.04 * 20 = 0.8 C
    # HVAC savings: (3000 * 0.7) * (0.8 * 0.08) = 2100 * 0.064 = 134.4
    # Maintenance: 1600 * 0.03 = 48
    # Net annual: 134.4 - 48 = 86.4
    # Payback: 1600 / 86.4 = ~18.5 years

    assert result["total_installation_cost_usd"] == 1600.0
    assert abs(result["net_annual_savings_usd"] - 86.4) < 1.0
    assert isinstance(result["payback_years"], float)
    assert result["payback_years"] > 0.0


def test_mitigation_multiple_measures():
    calc = UrbanHeatMitigationCalculator(
        baseline_temp_c=35.0, annual_hvac_cost_usd=1500.0, property_area_sqm=150.0
    )
    calc.add_measure("mature_tree_canopy", 1.0)
    calc.add_measure("permeable_pavement", 10.0)

    result = calc.calculate_roi()

    assert len(result["measure_breakdown"]) == 2
    assert result["total_cooling_effect_c"] == 1.5 + 0.2  # 1.5 + (0.02 * 10)
    assert result["total_installation_cost_usd"] == 500.0 + 1200.0
