"""
Unit tests for PCF Label Generator and Supply Chain Transparency.
"""

import pytest
from src.utils.pcf_label_generator import PCFLabelGenerator
from src.business.supply_chain_transparency import SupplyChainTransparency


def test_calculate_material_impact():
    gen = PCFLabelGenerator()
    materials = [
        {"name": "wood", "weight_kg": 2.0},
        {"name": "metal", "weight_kg": 1.0},
    ]
    impact = gen.calculate_material_impact(materials)
    # wood: 2.0 * 0.5 = 1.0, metal: 1.0 * 4.0 = 4.0. Total = 5.0
    assert impact == 5.0


def test_calculate_transport_impact():
    gen = PCFLabelGenerator()
    # 1000 kg (1 tonne) * 100 km * 0.1 (truck) = 10.0
    impact = gen.calculate_transport_impact(
        weight_kg=1000.0, distance_km=100.0, mode="truck"
    )
    assert impact == 10.0


def test_generate_label_grading():
    gen = PCFLabelGenerator()
    label = gen.generate_label(
        product_name="Test",
        materials=[{"name": "wood", "weight_kg": 1.0}],
        manufacturing_energy_kwh=1.0,
        transport_distance_km=10.0,
        transport_mode="ship",
    )
    assert label["grade"] == "A"  # Very low impact
    assert label["total_pcf_kg_co2e"] > 0


def test_supply_chain_transparency_scoring():
    scorer = SupplyChainTransparency()

    stage_eval = scorer.evaluate_stage(
        "raw_materials", data_provided=True, certification="FSC"
    )
    assert stage_eval["score"] == 90  # 50 (data) + 40 (cert)
    assert len(stage_eval["risks"]) == 0

    stage_eval_bad = scorer.evaluate_stage(
        "manufacturing", data_provided=False, certification="none"
    )
    assert stage_eval_bad["score"] == 0
    assert "No data disclosed" in stage_eval_bad["risks"]


def test_overall_transparency_score():
    scorer = SupplyChainTransparency()
    evaluations = [
        {"stage": "raw_materials", "score": 90, "certification": "FSC", "risks": []},
        {
            "stage": "manufacturing",
            "score": 50,
            "certification": "none",
            "risks": ["Lacks third-party certification"],
        },
        {
            "stage": "distribution",
            "score": 50,
            "certification": "none",
            "risks": ["Lacks third-party certification"],
        },
        {
            "stage": "end_of_life",
            "score": 0,
            "certification": "none",
            "risks": ["No data disclosed", "No end-of-life plan"],
        },
    ]

    result = scorer.calculate_overall_score(evaluations)
    assert result["overall_score_pct"] == 47.5  # (90+50+50+0) / 400 * 100
    assert result["grade"] == "Low"
    assert len(result["identified_risks"]) == 4
