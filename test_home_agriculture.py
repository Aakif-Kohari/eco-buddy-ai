"""
Unit tests for Home Agriculture Tracker and Sequestration Calculator.
"""

import pytest
from home_agriculture_tracker import HomeAgricultureTracker
from sequestration_calculator import SequestrationCalculator


def test_agriculture_tracker_avoided_emissions():
    tracker = HomeAgricultureTracker(
        garden_area_sqm=10.0, crops_grown=["tomatoes", "carrots"], composting=True
    )
    result = tracker.calculate_avoided_emissions()

    # Area per crop = 5.0 sqm
    # Tomatoes: 5.0 * 5.0 kg/sqm * 1.5 kg CO2e/kg = 37.5
    # Carrots: 5.0 * 4.0 kg/sqm * 0.4 kg CO2e/kg = 8.0
    # Total = 45.5
    assert result["total_avoided_emissions_kg"] == 45.5
    assert result["crop_breakdown_kg"]["tomatoes"] == 37.5
    assert result["crop_breakdown_kg"]["carrots"] == 8.0


def test_agriculture_tracker_empty_garden():
    tracker = HomeAgricultureTracker(
        garden_area_sqm=0.0, crops_grown=[], composting=False
    )
    result = tracker.calculate_avoided_emissions()

    assert result["total_avoided_emissions_kg"] == 0.0
    assert result["crop_breakdown_kg"] == {}


def test_sequestration_calculator_base():
    calc = SequestrationCalculator(
        composting=True, lawn_converted_sqm=10.0, has_perennials=True
    )
    result = calc.calculate_sequestration()

    # Compost: 25.0
    # Lawn: 10.0 * 0.5 = 5.0
    # Perennials: 10.0
    # Total: 40.0
    assert result["total_sequestered_kg"] == 40.0
    assert result["composting_kg"] == 25.0
    assert result["lawn_conversion_kg"] == 5.0
    assert result["perennials_kg"] == 10.0


def test_sequestration_calculator_none():
    calc = SequestrationCalculator(
        composting=False, lawn_converted_sqm=0.0, has_perennials=False
    )
    result = calc.calculate_sequestration()

    assert result["total_sequestered_kg"] == 0.0


def test_regeneration_score_calculation():
    tracker = HomeAgricultureTracker(
        garden_area_sqm=10.0, crops_grown=["tomatoes"], composting=True
    )
    ag_result = tracker.calculate_avoided_emissions()  # 10 * 5 * 1.5 = 75.0

    calc = SequestrationCalculator(
        composting=True, lawn_converted_sqm=0.0, has_perennials=False
    )
    seq_result = calc.calculate_sequestration()  # 25.0

    # Total impact = 75.0 + 25.0 = 100.0
    # Benchmark = 50.0. Score = (100 / 50) * 100 = 200 -> capped at 100.0
    score = tracker.get_regeneration_score(
        ag_result["total_avoided_emissions_kg"], seq_result["total_sequestered_kg"]
    )
    assert score == 100.0


def test_sequestration_recommendations():
    calc = SequestrationCalculator(
        composting=False, lawn_converted_sqm=2.0, has_perennials=False
    )
    recs = calc.get_practice_recommendations()

    assert len(recs) == 3
    assert any("Composting" in r for r in recs)
    assert any("Convert Lawn" in r for r in recs)
    assert any("Plant Perennials" in r for r in recs)
