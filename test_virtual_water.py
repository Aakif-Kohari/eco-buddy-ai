"""
Unit tests for Virtual Water Tracker and Consumer Goods Water DB.
"""

import pytest
from virtual_water_tracker import VirtualWaterTracker
from consumer_goods_water_db import ConsumerGoodsWaterDB


def test_db_retrieval():
    db = ConsumerGoodsWaterDB()
    factors = db.get_product_factors("beef")

    assert factors is not None
    assert factors["blue"] == 15000
    assert factors["unit"] == "kg"

    assert db.get_regional_stress("middle_east_north_africa") == 0.85
    assert db.get_stress_category(0.85) == "Extreme Stress"


def test_tracker_log_purchase():
    tracker = VirtualWaterTracker()
    record = tracker.log_purchase("beef", 2.0, "south_america")

    assert record["product"] == "beef"
    assert record["quantity"] == 2.0
    assert record["blue_water_l"] == 30000.0  # 15000 * 2
    assert record["water_stress_index"] == 0.25
    # Scarcity weighted blue = 30000 * (1 + 0.25) = 37500
    # Green = 500 * 2 = 1000
    # Grey = 2000 * 2 = 4000 -> weighted = 4000 * 1.25 = 5000
    # Total scarcity weighted = 37500 + 1000 + 5000 = 43500
    assert record["scarcity_weighted_total_l"] == 43500.0


def test_tracker_aggregation():
    tracker = VirtualWaterTracker()
    tracker.log_purchase("beef", 1.0, "south_america")
    tracker.log_purchase("cotton_clothing", 3.0, "south_asia")

    agg = tracker.get_aggregated_footprint()

    assert agg["total_purchases"] == 2
    assert agg["total_blue_water_l"] == 15000.0 + (4000.0 * 3)  # 27000.0
    assert "south_america" in agg["regional_impact"]
    assert "south_asia" in agg["regional_impact"]


def test_tracker_empty_aggregation():
    tracker = VirtualWaterTracker()
    agg = tracker.get_aggregated_footprint()

    assert agg["total_purchases"] == 0
    assert agg["total_raw_water_l"] == 0.0


def test_tracker_high_impact_items():
    tracker = VirtualWaterTracker()
    tracker.log_purchase("wheat", 10.0, "north_america")  # Low impact
    tracker.log_purchase("beef", 5.0, "middle_east_north_africa")  # High impact

    high_impact = tracker.get_high_impact_items()
    assert len(high_impact) <= 5
    assert high_impact[0]["product"] == "beef"


def test_tracker_suggestions():
    tracker = VirtualWaterTracker()
    suggestions = tracker.suggest_alternatives("beef")

    assert len(suggestions) > 0
    assert any(
        "plant-based" in s.lower() or "chicken" in s.lower() for s in suggestions
    )

    unknown_suggestions = tracker.suggest_alternatives("unknown_item")
    assert len(unknown_suggestions) == 1
    assert "locally sourced" in unknown_suggestions[0].lower()
