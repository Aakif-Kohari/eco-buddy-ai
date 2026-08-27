"""
Unit tests for FoodFootprintPlugin.
"""

import pytest
from plugins import get_plugin, discover_plugins
from plugins.food_footprint import FoodFootprintPlugin


def test_food_footprint_plugin_discovery():
    discover_plugins()
    plugin = get_plugin("food_footprint")
    assert plugin is not None
    assert isinstance(plugin, FoodFootprintPlugin)
    assert plugin.category == "Food & Agriculture"


def test_food_footprint_calculation_vegan():
    plugin = FoodFootprintPlugin()
    inputs = {
        "diet_pattern": "Vegan",
        "red_meat_meals_per_week": 0,
        "dairy_servings_per_day": 0,
        "food_waste_pct": 5,
        "organic_local_pct": 50
    }
    result = plugin.calculate(inputs)
    assert result.unit == "kg CO2e/year"
    assert result.total < 500  # Highly efficient
    assert "Red Meat" in result.contributors
    assert result.contributors["Red Meat"] == 0.0
    assert result.metadata["annual_water_liters"] > 0
    assert result.metadata["trees_to_offset"] > 0


def test_food_footprint_calculation_heavy_meat():
    plugin = FoodFootprintPlugin()
    inputs = {
        "diet_pattern": "Heavy Meat",
        "red_meat_meals_per_week": 7,
        "dairy_servings_per_day": 3,
        "food_waste_pct": 25,
        "organic_local_pct": 10
    }
    result = plugin.calculate(inputs)
    assert result.total > 2000
    assert result.contributors["Red Meat"] > 1000
    
    recs = plugin.get_recommendations(result)
    assert len(recs) >= 2
    assert any("red meat" in r.lower() for r in recs)
