import math
from typing import Any

from config import HOURS_PER_DAY


def optimize_charging_schedule(
    battery_capacity_kwh: float,
    current_soc_pct: float,
    target_soc_pct: float,
    charging_rate_kw: float,
    grid_profile: list[float],
    pricing_profile: list[float],
) -> dict[str, Any]:
    """
    Calculates the optimal charging schedule to minimize carbon footprint and cost.

    Args:
        battery_capacity_kwh: Total battery capacity in kWh.
        current_soc_pct: Current state of charge (0-100).
        target_soc_pct: Desired state of charge (0-100).
        charging_rate_kw: Charging power in kW.
        grid_profile: 24-hour list of carbon intensity (kg CO2e/kWh).
        pricing_profile: 24-hour list of electricity price ($/kWh).

    Returns:
        Dictionary containing optimal schedule, carbon savings, and cost savings.
    """
    if target_soc_pct <= current_soc_pct:
        raise ValueError("Target SOC must be greater than current SOC.")

    energy_needed = battery_capacity_kwh * ((target_soc_pct - current_soc_pct) / 100.0)
    hours_needed = math.ceil(energy_needed / charging_rate_kw)

    if hours_needed > HOURS_PER_DAY:
        raise ValueError(
            "Charging requirement exceeds 24 hours at the given charging rate."
        )

    # Find the hours with the lowest carbon intensity
    indexed_profile = [(intensity, hour) for hour, intensity in enumerate(grid_profile)]
    indexed_profile.sort(key=lambda x: x[0])

    optimal_hours = sorted([item[1] for item in indexed_profile[:hours_needed]])

    # Calculate metrics for optimal schedule
    optimal_carbon = sum(grid_profile[h] * charging_rate_kw for h in optimal_hours)
    optimal_cost = sum(pricing_profile[h] * charging_rate_kw for h in optimal_hours)

    # Calculate metrics for uncontrolled schedule (assumes starting at hour 0)
    uncontrolled_hours = list(range(hours_needed))
    uncontrolled_carbon = sum(
        grid_profile[h] * charging_rate_kw for h in uncontrolled_hours
    )
    uncontrolled_cost = sum(
        pricing_profile[h] * charging_rate_kw for h in uncontrolled_hours
    )

    # Build 24-hour schedule array
    schedule = [0.0] * HOURS_PER_DAY
    for h in optimal_hours:
        schedule[h] = charging_rate_kw

    return {
        "energy_needed_kwh": round(energy_needed, 2),
        "hours_needed": hours_needed,
        "optimal_hours": optimal_hours,
        "schedule": schedule,
        "optimal_carbon_kg": round(optimal_carbon, 2),
        "uncontrolled_carbon_kg": round(uncontrolled_carbon, 2),
        "carbon_savings_kg": round(max(0.0, uncontrolled_carbon - optimal_carbon), 2),
        "optimal_cost_usd": round(optimal_cost, 2),
        "uncontrolled_cost_usd": round(uncontrolled_cost, 2),
        "cost_savings_usd": round(max(0.0, uncontrolled_cost - optimal_cost), 2),
    }


def generate_charging_recommendations(result: dict[str, Any]) -> list[str]:
    """Generates human-readable recommendations based on optimization results."""
    recommendations = []
    if result["carbon_savings_kg"] > 0:
        recommendations.append(
            f"🌱 Smart charging saves {result['carbon_savings_kg']} kg of CO2e compared to immediate charging."
        )
    if result["cost_savings_usd"] > 0:
        recommendations.append(
            f"💰 Shifting to off-peak hours saves ${result['cost_savings_usd']} per charging session."
        )
    if not result["optimal_hours"]:
        recommendations.append(
            "✅ Your battery is already at or above the target charge level."
        )
    else:
        start_hour = result["optimal_hours"][0]
        end_hour = result["optimal_hours"][-1] + 1
        recommendations.append(
            f"⏰ Schedule your charger to run between {start_hour}:00 and {end_hour}:00 for maximum efficiency."
        )
    return recommendations
