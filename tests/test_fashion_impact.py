import pytest
from plugins.fashion_impact import FashionImpactCalculator

def test_fashion_calculator_initialization():
    calc = FashionImpactCalculator()
    assert calc.df is not None
    assert not calc.df.empty
    
    materials = calc.get_available_materials()
    assert "Cotton (Conventional)" in materials
    assert "Polyester (Virgin)" in materials

def test_get_material_metrics():
    calc = FashionImpactCalculator()
    metrics = calc.get_material_metrics("Cotton (Organic)")
    assert metrics['carbon_factor'] == 15.0
    assert metrics['water_factor'] == 5000.0
    
    with pytest.raises(ValueError):
        calc.get_material_metrics("Vibranium")

def test_calculate_garment_impact():
    calc = FashionImpactCalculator()
    
    # 100% Cotton T-Shirt (0.2 kg)
    blend = {"Cotton (Conventional)": 1.0}
    impact = calc.calculate_garment_impact(
        garment_weight_kg=0.2,
        material_blend=blend,
        is_second_hand=False,
        lifespan_years=2.0
    )
    
    # Carbon = 0.2 * 20.0 = 4.0 kg CO2
    assert impact["total_carbon_kg"] == 4.0
    # Water = 0.2 * 10000 = 2000 Liters
    assert impact["total_water_liters"] == 2000.0
    assert impact["carbon_per_year_kg"] == 2.0
    assert impact["contains_microplastics"] is False
    assert impact["is_second_hand"] is False

def test_mixed_blend_impact():
    calc = FashionImpactCalculator()
    
    # 60% Cotton, 40% Polyester sweater (0.5 kg)
    blend = {
        "Cotton (Conventional)": 0.6,
        "Polyester (Virgin)": 0.4
    }
    
    impact = calc.calculate_garment_impact(
        garment_weight_kg=0.5,
        material_blend=blend
    )
    
    # Cotton carbon = 0.5 * 0.6 * 20 = 6.0
    # Poly carbon = 0.5 * 0.4 * 22 = 4.4
    # Total = 10.4
    assert impact["total_carbon_kg"] == 10.4
    assert impact["contains_microplastics"] is True # Due to poly

def test_second_hand_impact():
    calc = FashionImpactCalculator()
    
    blend = {"Wool": 1.0}
    impact_new = calc.calculate_garment_impact(1.0, blend, is_second_hand=False)
    impact_used = calc.calculate_garment_impact(1.0, blend, is_second_hand=True)
    
    assert impact_used["total_carbon_kg"] == round(impact_new["total_carbon_kg"] * 0.10, 2)
    assert impact_used["total_water_liters"] == round(impact_new["total_water_liters"] * 0.05, 2)

def test_invalid_blend():
    calc = FashionImpactCalculator()
    blend = {"Silk": 0.5} # Doesn't equal 1.0
    
    with pytest.raises(ValueError):
        calc.calculate_garment_impact(0.5, blend)

def test_recommendations():
    calc = FashionImpactCalculator()
    
    # Bad garment: Synthetic, water intensive, brand new
    impact = {
        "total_water_liters": 3000,
        "contains_microplastics": True,
        "is_second_hand": False
    }
    
    recs = calc.generate_recommendations(impact)
    assert len(recs) == 3
    assert any("microplastic" in r.lower() for r in recs)
    assert any("second-hand" in r.lower() for r in recs)
