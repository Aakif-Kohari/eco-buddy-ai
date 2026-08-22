"""
Unit tests for Textile LCA Engine and Fashion Impact Comparator.
"""
import pytest
from textile_lca_engine import TextileLCAEngine
from fashion_impact_comparator import FashionImpactComparator

def test_get_material_data():
    engine = TextileLCAEngine()
    data = engine.get_material_data("Organic Cotton")
    assert data["material"] == "organic cotton"
    assert data["carbon_factor"] == 6.0
    assert data["microplastic_factor"] == 0.0
    
    # Test unknown fallback
    unknown_data = engine.get_material_data("mystery fabric")
    assert "conventional cotton" in unknown_data["material"]

def test_calculate_washing_impact():
    engine = TextileLCAEngine()
    impact = engine.calculate_washing_impact("polyester", weight_kg=1.0, num_washes10)
    
    assert impact["microplastics_mg"] == 150.0 * 1.0 * 10  # 1500 mg
    assert impact["washing_water_l"] == 10 * 1.0 * 50.0    # 500 L

def test_evaluate_garment():
    comparator = FashionImpactComparator()
    result = comparator.evaluate_garment(
        material="linen",
        weight_kg=0.5,
        estimated_wears=50,
        washes_per_wear_ratio=0.2  # Washed every 5 wears (10 washes total)
    )
    
    assert result["material"] == "linen"
    assert result["num_washes"] == 10
    assert result["total_microplastics_mg"] == 0.0
    assert "production_carbon_kg" in result["breakdown"]

def test_compare_garments_ranking():
    comparator = FashionImpactComparator()
    garments = [
        {"material": "polyester", "weight_kg": 1.0, "estimated_wears": 10, "washes_per_wear_ratio": 1.0},
        {"material": "linen", "weight_kg": 1.0, "estimated_wears": 50, "washes_per_wear_ratio": 0.2}
    ]
    
    results = comparator.compare_garments(garments)
    
    # Linen should be ranked first (lower total carbon)
    assert results[0]["material"] == "linen"
    assert results[1]["material"] == "polyester"
    assert results[0]["total_carbon_kg"] < results[1]["total_carbon_kg"]
