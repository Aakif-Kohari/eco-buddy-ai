import pytest

from src.business.business_footprint import (
    calculate_business_footprint,
    generate_b2b_recommendations,
)
from src.carbon.scope3_screener import categorize_business_expense


def test_categorize_business_expense_software():
    result = categorize_business_expense("software_cloud", 100.0, "usd")
    assert result["category_name"] == "Purchased Goods and Services"
    assert result["emissions_kg_co2e"] == 35.0  # 100 * 0.35


def test_categorize_business_expense_travel():
    result = categorize_business_expense("business_travel_air", 1000.0, "km")
    assert result["category_name"] == "Business Travel"
    assert result["emissions_kg_co2e"] == 255.0  # 1000 * 0.255


def test_categorize_invalid_expense():
    with pytest.raises(ValueError, match="Unknown expense type"):
        categorize_business_expense("invalid_type", 100.0)


def test_calculate_business_footprint_aggregation():
    expenses = [
        {"type": "software_cloud", "amount": 100.0, "unit": "usd"},
        {"type": "business_travel_air", "amount": 1000.0, "unit": "km"},
    ]
    footprint = calculate_business_footprint(expenses)
    assert footprint["total_emissions_kg"] == 290.0
    assert "Purchased Goods and Services" in footprint["category_breakdown"]
    assert "Business Travel" in footprint["category_breakdown"]
    assert footprint["business_eco_score"] > 0


def test_generate_b2b_recommendations():
    footprint = {
        "total_emissions_kg": 500.0,
        "category_breakdown": {
            "Purchased Goods and Services": 150.0,
            "Business Travel": 350.0,
        },
        "business_eco_score": 75.0,
    }
    recs = generate_b2b_recommendations(footprint)
    assert any("IT & Procurement" in r for r in recs)
    assert any("Travel Policy" in r for r in recs)
