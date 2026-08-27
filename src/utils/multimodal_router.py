"""
Multi-Modal Router.
Generates and ranks alternative routing options, factoring in layovers, EV charging, and modal shifts.
"""

from typing import Dict, List, Any
from src.lifestyle.travel_itinerary_optimizer import TravelItineraryOptimizer


class MultimodalRouter:
    """Enhances itinerary optimization with realistic multi-modal constraints."""

    def __init__(self):
        self.optimizer = TravelItineraryOptimizer()

    def add_ev_charging_stops(
        self, distance_km: float, ev_range_km: float = 400.0
    ) -> int:
        """Calculates the number of required charging stops for an EV journey."""
        if distance_km <= ev_range_km:
            return 0
        # Each stop adds ~0.5 hours
        return math.ceil(distance_km / ev_range_km) - 1

    def evaluate_modal_shift(
        self, original_mode: str, distance_km: float
    ) -> Dict[str, Any]:
        """Evaluates the impact of shifting from a high-carbon mode to a lower-carbon one."""
        original_metrics = self.optimizer.calculate_leg_metrics(
            distance_km, original_mode
        )

        # Determine best alternative
        if distance_km < 600 and original_mode in ["flight_short", "ice_car"]:
            best_alt_mode = "train"
        elif distance_km >= 600 and original_mode == "flight_long":
            best_alt_mode = "train"  # High-speed rail alternative
        else:
            best_alt_mode = original_mode

        alt_metrics = self.optimizer.calculate_leg_metrics(distance_km, best_alt_mode)

        # Adjust for EV charging if applicable
        if best_alt_mode == "ev_car":
            stops = self.add_ev_charging_stops(distance_km)
            alt_metrics["time_hours"] += stops * 0.5
            alt_metrics["charging_stops"] = stops
        else:
            alt_metrics["charging_stops"] = 0

        carbon_saved = original_metrics["carbon_kg"] - alt_metrics["carbon_kg"]
        cost_diff = alt_metrics["cost_usd"] - original_metrics["cost_usd"]
        time_diff = alt_metrics["time_hours"] - original_metrics["time_hours"]

        return {
            "original_mode": original_mode,
            "recommended_mode": best_alt_mode,
            "distance_km": distance_km,
            "carbon_saved_kg": round(carbon_saved, 2),
            "cost_difference_usd": round(cost_diff, 2),
            "time_difference_hours": round(time_diff, 2),
            "charging_stops": alt_metrics.get("charging_stops", 0),
            "is_viable_shift": carbon_saved
            > 10.0,  # Only recommend if saving > 10kg CO2e
        }

    def generate_comprehensive_report(
        self, legs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generates a full report including modal shift recommendations for each leg."""
        optimization = self.optimizer.optimize_itinerary(legs)

        shift_recommendations = []
        for leg in legs:
            shift = self.evaluate_modal_shift(leg["mode"], leg["distance_km"])
            if shift["is_viable_shift"]:
                shift_recommendations.append(shift)

        return {
            "optimization_summary": optimization,
            "modal_shift_opportunities": shift_recommendations,
            "total_potential_carbon_savings_kg": round(
                sum(s["carbon_saved_kg"] for s in shift_recommendations), 2
            ),
        }
