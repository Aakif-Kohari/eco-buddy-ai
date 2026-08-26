"""
Unit tests for Travel Itinerary Optimizer and Multi-Modal Router.
"""

import pytest
from travel_itinerary_optimizer import TravelItineraryOptimizer
from multimodal_router import MultimodalRouter


def test_calculate_leg_metrics():
    optimizer = TravelItineraryOptimizer()
    metrics = optimizer.calculate_leg_metrics(distance_km=500, mode="train")

    assert metrics["distance_km"] == 500
    assert metrics["carbon_kg"] == 500 * 0.035  # 17.5
    assert metrics["time_hours"] == 500 / 120  # ~4.17
    assert metrics["cost_usd"] == 500 * 0.12  # 60.0


def test_calculate_leg_metrics_flight_overhead():
    optimizer = TravelItineraryOptimizer()
    metrics = optimizer.calculate_leg_metrics(distance_km=500, mode="flight_short")

    # Should include 2.5 hours overhead and $50 base fee
    assert metrics["time_hours"] == (500 / 600) + 2.5
    assert metrics["cost_usd"] == (500 * 0.15) + 50.0


def test_optimize_itinerary_aggregation():
    optimizer = TravelItineraryOptimizer()
    legs = [
        {"distance_km": 300, "mode": "flight_short"},
        {"distance_km": 800, "mode": "ice_car"},
    ]

    result = optimizer.optimize_itinerary(legs)
    assert "original" in result
    assert "greenest" in result
    assert (
        result["greenest"]["total_carbon_kg"] <= result["original"]["total_carbon_kg"]
    )


def test_add_ev_charging_stops():
    router = MultimodalRouter()
    assert router.add_ev_charging_stops(300, 400) == 0
    assert router.add_ev_charging_stops(500, 400) == 1
    assert router.add_ev_charging_stops(900, 400) == 2


def test_evaluate_modal_shift():
    router = MultimodalRouter()
    # Shifting from short flight to train for 400km
    shift = router.evaluate_modal_shift(original_mode="flight_short", distance_km=400)

    assert shift["recommended_mode"] == "train"
    assert shift["carbon_saved_kg"] > 0
    assert shift["is_viable_shift"] is True


def test_generate_comprehensive_report():
    router = MultimodalRouter()
    legs = [
        {"distance_km": 400, "mode": "flight_short"},
        {"distance_km": 1200, "mode": "ice_car"},
    ]

    report = router.generate_comprehensive_report(legs)
    assert "optimization_summary" in report
    assert "modal_shift_opportunities" in report
    assert report["total_potential_carbon_savings_kg"] >= 0
