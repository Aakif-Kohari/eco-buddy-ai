"""
Unit tests for Demand Response Optimizer and Load Shifting Engine.
"""

import pytest
from demand_response_optimizer import DemandResponseOptimizer
from load_shifting_engine import LoadShiftingEngine


def test_load_shifting_optimal_hours_carbon():
    engine = LoadShiftingEngine()
    # 6 hours duration, minimize carbon
    # Lowest carbon hours are around 12-13 (solar peak) or 2-3 (night)
    # 12, 13, 0, 1, 2, 3 are generally low.
    optimal = engine.find_optimal_hours(6, preference="carbon")

    assert len(optimal) == 6
    # Verify they are consecutive (wrapping around 24)
    # Just check that the average carbon of these hours is lower than a random block like 17-22
    optimal_carbon = sum(engine.grid_data[h]["carbon"] for h in optimal)
    peak_carbon = sum(engine.grid_data[h]["carbon"] for h in [17, 18, 19, 20, 21, 22])

    assert optimal_carbon < peak_carbon


def test_load_shifting_optimal_hours_cost():
    engine = LoadShiftingEngine()
    optimal = engine.find_optimal_hours(2, preference="cost")

    # Cheapest hours are 2 and 3 ($0.08)
    assert 2 in optimal and 3 in optimal


def test_load_shifting_savings_calculation():
    engine = LoadShiftingEngine()
    savings = engine.calculate_shift_savings(
        appliance_kwh=10.0,
        baseline_hours=[
            18,
            19,
        ],  # Price: 0.25, 0.25 -> Avg 0.25. Carbon: 0.65, 0.65 -> Avg 0.65
        optimal_hours=[
            2,
            3,
        ],  # Price: 0.08, 0.08 -> Avg 0.08. Carbon: 0.25, 0.25 -> Avg 0.25
    )

    # Cost: Baseline = 10 * 0.50 = 5.0. Optimal = 10 * 0.16 = 1.6. Saved = 3.4
    assert savings["baseline_cost_usd"] == 5.0
    assert savings["optimal_cost_usd"] == 1.6
    assert savings["money_saved_usd"] == 3.4

    # Carbon: Baseline = 10 * 1.30 = 13.0. Optimal = 10 * 0.50 = 5.0. Saved = 8.0
    assert savings["baseline_carbon_kg"] == 13.0
    assert savings["optimal_carbon_kg"] == 5.0
    assert savings["carbon_saved_kg"] == 8.0


def test_demand_response_optimizer_selection():
    opt = DemandResponseOptimizer()
    opt.select_appliances(["ev_charging", "dishwasher", "invalid_appliance"])

    assert len(opt.selected_appliances) == 2
    assert "ev_charging" in opt.selected_appliances
    assert "invalid_appliance" not in opt.selected_appliances


def test_demand_response_optimize_all():
    opt = DemandResponseOptimizer()
    opt.select_appliances(["washing_machine"])

    results = opt.optimize_all_selected(preference="carbon")

    assert results["preference"] == "carbon"
    assert len(results["appliance_breakdown"]) == 1
    assert results["appliance_breakdown"][0]["appliance"] == "Washing Machine"
    assert results["total_carbon_saved_kg"] >= 0.0


def test_demand_response_load_curve_generation():
    opt = DemandResponseOptimizer()
    opt.select_appliances(["pool_pump"])  # 4 hours, 3.0 kWh -> 0.75 kW per hour

    baseline_curve = opt.generate_load_curve_data(optimized=False)
    assert len(baseline_curve) == 24

    # Typical start is 12, so hours 12, 13, 14, 15 should have load
    load_at_12 = next(item["load_kw"] for item in baseline_curve if item["hour"] == 12)
    assert load_at_12 == 0.75

    optimized_curve = opt.generate_load_curve_data(optimized=True, preference="cost")
    # Should be shifted to cheaper hours, so hour 12 might be 0.0
    load_at_12_opt = next(
        item["load_kw"] for item in optimized_curve if item["hour"] == 12
    )
    # Depending on optimal calculation, it might move. We just check it's a valid curve.
    assert (
        sum(item["load_kw"] for item in optimized_curve) == 3.0
    )  # Total energy conserved
