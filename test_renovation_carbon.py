"""
Unit tests for Renovation Carbon Estimator and Sustainable Material DB.
"""

import pytest
from renovation_carbon_estimator import RenovationCarbonEstimator
from sustainable_material_db import SustainableMaterialDB


def test_material_db_retrieval():
    db = SustainableMaterialDB()
    specs = db.get_material_specs("hempcrete")

    assert specs is not None
    assert specs["name"] == "Hempcrete"
    assert specs["embodied_carbon_per_kg"] == -0.10  # Carbon negative
    assert db.get_material_display_name("steel_virgin") == "Virgin Steel"


def test_renovation_estimator_base_calculation():
    # 1 m3 of standard concrete, 50 km transport
    # Weight: 1 * 2400 = 2400 kg
    # Material carbon: 2400 * 0.15 = 360 kg
    # Transport carbon: (2400/1000) * 50 * 0.1 = 12 kg
    # Total: 372 kg
    estimator = RenovationCarbonEstimator(
        "concrete_standard", volume_m3=1.0, transport_distance_km=50.0
    )
    result = estimator.calculate_embodied_carbon()

    assert result["weight_kg"] == 2400.0
    assert result["material_carbon_kg"] == 360.0
    assert result["transport_carbon_kg"] == 12.0
    assert result["total_embodied_carbon_kg"] == 372.0


def test_renovation_estimator_carbon_negative():
    estimator = RenovationCarbonEstimator(
        "hempcrete", volume_m3=1.0, transport_distance_km=10.0
    )
    result = estimator.calculate_embodied_carbon()

    # Weight: 400 kg
    # Material carbon: 400 * -0.10 = -40 kg
    # Transport carbon: 0.4 * 10 * 0.1 = 0.4 kg
    # Total: -39.6 kg
    assert result["total_embodied_carbon_kg"] == -39.6


def test_low_carbon_score_calculation():
    estimator = RenovationCarbonEstimator(
        "wood_reclaimed", volume_m3=1.0, transport_distance_km=10.0
    )
    result = estimator.calculate_embodied_carbon()
    score = estimator.calculate_low_carbon_score(result["total_embodied_carbon_kg"])

    # Reclaimed wood has very low carbon and high recyclability, score should be high
    assert score > 80.0


def test_green_swap_recommendations():
    estimator = RenovationCarbonEstimator(
        "concrete_standard", volume_m3=1.0, transport_distance_km=10.0
    )
    recs = estimator.get_green_swap_recommendations()

    assert any("Low-Carbon Concrete" in r for r in recs)
    assert any("Hempcrete" in r for r in recs)

    # Hempcrete should not recommend itself as a swap
    estimator_hemp = RenovationCarbonEstimator(
        "hempcrete", volume_m3=1.0, transport_distance_km=10.0
    )
    recs_hemp = estimator_hemp.get_green_swap_recommendations()
    assert not any("Hempcrete" in r for r in recs_hemp)


def test_renovation_estimator_unknown_material():
    with pytest.raises(ValueError, match="Unknown material"):
        RenovationCarbonEstimator(
            "magic_unobtanium", volume_m3=1.0, transport_distance_km=10.0
        )
