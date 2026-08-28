"""
Unit tests for Spoilage Predictor and Waste Prevention Engine.
"""

import pytest
from datetime import datetime, timedelta
from src.utils.spoilage_predictor import SpoilagePredictor
from src.environment.waste_prevention_engine import WastePreventionEngine


def test_get_base_shelf_life():
    predictor = SpoilagePredictor()
    assert predictor.get_base_shelf_life("spinach") == 5
    assert predictor.get_base_shelf_life("unknown_item") == 3


def test_calculate_expiration_date():
    predictor = SpoilagePredictor()
    purchase_date = "2023-10-01"

    # Refrigerated spinach: 5 days
    exp_date = predictor.calculate_expiration_date(
        "spinach", purchase_date, "refrigerated"
    )
    assert exp_date == datetime(2023, 10, 6)

    # Frozen spinach: 5 * 5.0 = 25 days
    exp_date_frozen = predictor.calculate_expiration_date(
        "spinach", purchase_date, "freezer"
    )
    assert exp_date_frozen == datetime(2023, 10, 26)


def test_get_urgency_level():
    predictor = SpoilagePredictor()
    assert predictor.get_urgency_level(-1) == "expired"
    assert predictor.get_urgency_level(1) == "critical"
    assert predictor.get_urgency_level(4) == "warning"
    assert predictor.get_urgency_level(10) == "safe"


def test_waste_prevention_analysis():
    engine = WastePreventionEngine()
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    inventory = [
        {"name": "spinach", "purchase_date": yesterday, "storage": "refrigerated"},
        {"name": "apples", "purchase_date": today, "storage": "refrigerated"},
    ]

    analysis = engine.analyze_pantry(inventory)

    assert analysis["total_items"] == 2
    assert analysis["expiring_items"] >= 1  # Spinach should be expiring soon
    assert analysis["health_score"] < 100.0
    assert len(analysis["alerts"]) >= 1
    assert (
        "Smoothie" in analysis["alerts"][0]["recommendation"]
        or "Omelette" in analysis["alerts"][0]["recommendation"]
    )
