"""
Unit tests for Aviation Carbon Optimizer and SAF Impact Calculator.
"""

import pytest
from aviation_carbon_optimizer import AviationCarbonOptimizer
from saf_impact_calculator import SAFImpactCalculator


def test_aviation_optimizer_base():
    opt = AviationCarbonOptimizer(
        distance_km=1000, cabin_class="economy", has_layover=False
    )
    result = opt.calculate_emissions()

    # Base: 1000 * 0.15 = 150
    assert result["base_emissions_kg"] == 150.0
    assert result["total_emissions_kg"] == 150.0
    assert result["routing_type"] == "Direct"


def test_aviation_optimizer_layover_and_class():
    opt = AviationCarbonOptimizer(
        distance_km=1000, cabin_class="business", has_layover=True
    )
    result = opt.calculate_emissions()

    # Base: 150. Class mult: 3.0 -> 450. Layover mult: 1.25 -> 562.5
    assert result["total_emissions_kg"] == 562.5
    assert result["routing_type"] == "With Layover"


def test_aviation_optimizer_rail_comparison_viable():
    opt = AviationCarbonOptimizer(
        distance_km=500, cabin_class="economy", has_layover=False
    )
    comp = opt.compare_with_rail()

    assert comp["viable"] is True
    assert comp["flight_emissions_kg"] == 75.0
    assert comp["rail_emissions_kg"] == 20.0  # 500 * 0.04
    assert comp["savings_kg"] == 55.0


def test_aviation_optimizer_rail_comparison_not_viable():
    opt = AviationCarbonOptimizer(
        distance_km=1500, cabin_class="economy", has_layover=False
    )
    comp = opt.compare_with_rail()

    assert comp["viable"] is False


def test_saf_calculator_scenarios():
    calc = SAFImpactCalculator(
        base_flight_emissions_kg=1000.0, base_ticket_price_usd=500.0
    )
    scenarios = calc.calculate_saf_scenarios()

    assert len(scenarios) == 3
    assert scenarios[0]["blend_pct"] == 10
    assert scenarios[2]["blend_pct"] == 100

    # For 100% blend: 1000 * 1.0 * 0.80 = 800 kg saved
    assert scenarios[2]["carbon_saved_kg"] == 800.0
    # Cost premium: 800 * 0.50 = 400
    assert scenarios[2]["cost_premium_usd"] == 400.0
    assert scenarios[2]["total_price_usd"] == 900.0
