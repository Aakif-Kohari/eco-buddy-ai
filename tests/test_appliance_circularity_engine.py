"""Unit tests for Appliance Circularity & Lifecycle Engine.
"""

import pytest
from src.lifestyle.appliance_circularity_types import (
    ApplianceAssessmentInputs,
    ApplianceCategory,
    FailureSeverity,
)
from src.lifestyle.appliance_circularity_engine import ApplianceCircularityEngine
from src.lifestyle.appliance_circularity_db import (
    init_appliance_circularity_db,
    save_circularity_assessment,
    get_user_circularity_assessments,
)


@pytest.fixture
def young_repairable_washer():
    return ApplianceAssessmentInputs(
        appliance_name="Bosch Serie 6 Washer",
        category=ApplianceCategory.WASHING_MACHINE,
        age_years=3.5,
        original_purchase_cost_usd=850.0,
        estimated_repair_cost_usd=160.0,
        new_replacement_cost_usd=900.0,
        failure_severity=FailureSeverity.MINOR_WEAR,
        repairability_index_score=8.2,
    )


def test_repair_recommendation_for_young_appliance(young_repairable_washer):
    result = ApplianceCircularityEngine.evaluate_appliance_decision(young_repairable_washer)

    assert result.recommended_decision == "Repair & Extend Life"
    assert result.embodied_carbon_saved_by_repair_kg > 0.0
    assert result.residual_economic_value_usd > 0.0
    assert result.lifecycle_circularity_score > 60.0
    assert result.failure_probability_next_2yrs_pct < 50.0


def test_replace_recommendation_for_aged_appliance():
    aged_refrigerator = ApplianceAssessmentInputs(
        appliance_name="Old Frost Refrigerator",
        category=ApplianceCategory.REFRIGERATOR,
        age_years=16.0,  # Exceeded 14.0 characteristic life
        original_purchase_cost_usd=1200.0,
        estimated_repair_cost_usd=700.0,
        new_replacement_cost_usd=1100.0,
        failure_severity=FailureSeverity.CRITICAL_CORE,
        repairability_index_score=4.0,
    )

    result = ApplianceCircularityEngine.evaluate_appliance_decision(aged_refrigerator)
    assert result.recommended_decision == "Eco-Recycle & Replace"
    assert result.failure_probability_next_2yrs_pct > 30.0


def test_appliance_circularity_db_persistence(tmp_path):
    db_file = str(tmp_path / "test_appliance.db")
    init_appliance_circularity_db(db_file)

    audit_id = save_circularity_assessment(
        user_id=88,
        appliance_name="Miele Dishwasher",
        category="Dishwasher",
        decision="Repair & Extend Life",
        failure_prob=14.2,
        residual_val=450.0,
        carbon_saved=184.8,
        score=78.5,
        db_path=db_file,
    )

    assert audit_id > 0
    items = get_user_circularity_assessments(88, db_path=db_file)
    assert len(items) == 1
    assert items[0]["appliance_name"] == "Miele Dishwasher"
    assert items[0]["recommended_decision"] == "Repair & Extend Life"
