"""
Unit tests for Price-to-Carbon Analyzer and Smart Shopping List.
"""

import pytest
from src.carbon.price_carbon_analyzer import PriceCarbonAnalyzer
from src.lifestyle.smart_shopping_list import SmartShoppingList


def test_efficiency_calculation():
    analyzer = PriceCarbonAnalyzer()

    # Beef: high price, high carbon -> low efficiency
    beef_score = analyzer.calculate_efficiency_score("beef")
    # Lentils: low price, low carbon, high nutrition -> high efficiency
    lentil_score = analyzer.calculate_efficiency_score("lentils")

    assert lentil_score > beef_score
    assert beef_score > 0.0


def test_find_substitutions():
    analyzer = PriceCarbonAnalyzer()

    # Beef should have chicken or plant proteins as alternatives
    subs = analyzer.find_substitutions("beef")
    assert len(subs) > 0

    # Check that the first suggestion is actually more efficient
    assert subs[0]["efficiency_score"] > analyzer.calculate_efficiency_score("beef")
    assert subs[0]["carbon_savings_pct"] > 0


def test_smart_list_generation():
    builder = SmartShoppingList()

    result = builder.generate_optimized_list(
        budget_usd=20.0, required_categories=["grain", "plant_protein"]
    )

    assert result["budget_usd"] == 20.0
    assert result["remaining_budget_usd"] >= 0.0
    assert len(result["items"]) > 0

    # Verify the items belong to the requested categories
    for item in result["items"]:
        assert item["category"] in ["grain", "plant_protein"]


def test_list_comparison():
    builder = SmartShoppingList()

    comparison = builder.compare_lists(
        standard_items=["beef", "tomatoes_imported"],
        optimized_categories=["plant_protein", "vegetable"],
        budget_usd=20.0,
    )

    assert comparison["standard"]["estimated_carbon_kg"] > 0
    assert comparison["optimized"]["total_carbon_kg"] >= 0
    # The optimized list should generally have lower carbon than the high-carbon standard list
    assert comparison["carbon_savings_kg"] > 0
