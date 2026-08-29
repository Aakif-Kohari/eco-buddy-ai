"""
Unit tests for Biodiversity Net Gain Calculator and Habitat Restoration DB.
"""

import pytest
from biodiversity_net_gain import BiodiversityNetGainCalculator
from habitat_restoration_db import HabitatRestorationDB


def test_db_retrieval():
    db = HabitatRestorationDB()
    action = db.get_action_details("native_tree_planting")

    assert action is not None
    assert action["bu_per_sqm"] == 0.5
    assert "birds" in action["wildlife_support"]

    assert db.get_baseline_score("standard_suburban_lawn") == 0.3


def test_bng_calculator_add_action():
    calc = BiodiversityNetGainCalculator(
        baseline_condition="standard_suburban_lawn", total_area_sqm=100.0
    )
    success = calc.add_restoration_action(
        "native_tree_planting", area_sqm=20.0, management_years=5
    )

    assert success is True
    assert len(calc.actions_logged) == 1
    # BU gained = 0.5 * 20 * (1 + (5 * 0.1)) = 10 * 1.5 = 15.0
    assert calc.actions_logged[0]["bu_gained"] == 15.0


def test_bng_calculator_net_gain_positive():
    calc = BiodiversityNetGainCalculator(
        baseline_condition="degraded_urban_lot", total_area_sqm=50.0
    )
    calc.add_restoration_action("wetland_creation", area_sqm=10.0, management_years=10)

    result = calc.calculate_net_gain()

    assert result["is_positive_gain"] is True
    assert result["bng_percentage"] > 0.0
    assert "amphibians" in result["wildlife_supported"]


def test_bng_calculator_empty():
    calc = BiodiversityNetGainCalculator(
        baseline_condition="managed_parkland", total_area_sqm=0.0
    )
    result = calc.calculate_net_gain()

    assert result["total_bu_gained"] == 0.0
    assert result["bng_percentage"] == 0.0


def test_bng_recommendations():
    calc = BiodiversityNetGainCalculator(
        baseline_condition="standard_suburban_lawn", total_area_sqm=100.0
    )

    # Empty recommendations
    recs_empty = calc.get_recommendations()
    assert any("Start Small" in r for r in recs_empty)

    # Low diversity recommendations
    calc.add_restoration_action("lawn_conversion", area_sqm=20.0, management_years=1)
    recs_low_div = calc.get_recommendations()
    assert any("Increase Diversity" in r for r in recs_low_div)
    assert any("Long-term Commitment" in r for r in recs_low_div)


def test_bng_management_multiplier():
    calc = BiodiversityNetGainCalculator(
        baseline_condition="abandoned_agricultural", total_area_sqm=200.0
    )
    calc.add_restoration_action("hedge_planting", area_sqm=10.0, management_years=10)

    # Base BU = 0.25 * 10 = 2.5
    # Multiplier = 1 + (10 * 0.1) = 2.0
    # Total BU = 5.0
    assert calc.actions_logged[0]["bu_gained"] == 5.0
