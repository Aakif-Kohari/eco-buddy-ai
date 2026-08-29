"""
Comprehensive Unit Test Suite for Enterprise Circular Economy Lifecycle Studio
"""

import pytest
from src.utils.circular_economy_engine import CircularEconomyEngine, CircularMaterialComponent

def test_material_circularity_index_calculation():
    engine = CircularEconomyEngine()
    components = [
        CircularMaterialComponent(
            material_name="Recycled Steel",
            weight_kg=10.0,
            virgin_content_pct=10.0,
            recycled_content_pct=90.0,
            recyclability_rate_pct=95.0,
            toxicity_index=0.01,
            embodied_carbon_kg_co2e=5.0
        )
    ]
    mci = engine.calculate_material_circularity_index(components)
    assert mci > 0.8
    assert mci <= 1.0

def test_register_product_profile():
    engine = CircularEconomyEngine()
    components = [
        CircularMaterialComponent(
            material_name="Bio Polyethylene",
            weight_kg=5.0,
            virgin_content_pct=20.0,
            recycled_content_pct=80.0,
            recyclability_rate_pct=90.0,
            toxicity_index=0.02,
            embodied_carbon_kg_co2e=4.0
        )
    ]
    profile = engine.register_product_profile(
        product_id="TEST-999",
        product_name="Test Eco Product",
        category="Packaging Solutions",
        components=components,
        eol_pathway="Composting"
    )
    assert profile.product_id == "TEST-999"
    assert profile.total_weight_kg == 5.0
    assert profile.material_circularity_index > 0.0

def test_filter_profiles():
    engine = CircularEconomyEngine()
    results = engine.filter_profiles(category_filter="Industrial Hardware", min_mci=0.5)
    assert len(results) >= 1
    assert results[0].category == "Industrial Hardware"
