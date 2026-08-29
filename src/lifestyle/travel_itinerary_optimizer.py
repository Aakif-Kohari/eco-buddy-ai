"""
Travel Itinerary Optimizer.
Processes multi-leg journey inputs and calculates cumulative carbon, cost, and time footprints.
"""

from typing import Dict, List, Any
import math


class TravelItineraryOptimizer:
    """Optimizes multi-day travel plans for lowest combined carbon footprint, cost, and time."""

    # Emission factors (kg CO2e per passenger-km)
    EMISSION_FACTORS = {
        "flight_short": 0.255,
        "flight_long": 0.195,
        "train": 0.035,
        "bus": 0.105,
        "ev_car": 0.053,
        "ice_car": 0.192,
    }

    # Average speeds (km/h) for time estimation
    SPEEDS = {
        "flight_short": 600,
        "flight_long": 800,
        "train": 120,
        "bus": 80,
        "ev_car": 90,
        "ice_car": 90,
    }

    # Base costs per km (USD)
    COSTS = {
        "flight_short": 0.15,
        "flight_long": 0.10,
        "train": 0.12,
        "bus": 0.05,
        "ev_car": 0.04,  # Electricity cost
        "ice_car": 0.12,  # Fuel cost
    }

    def __init__(self):
        pass

    def calculate_leg_metrics(self, distance_km: float, mode: str) -> Dict[str, float]:
        """Calculates carbon, cost, and time for a single journey leg."""
        if mode not in self.EMISSION_FACTORS:
            raise ValueError(f"Unknown transport mode: {mode}")

        carbon = distance_km * self.EMISSION_FACTORS[mode]
        cost = distance_km * self.COSTS[mode]
        time_hours = distance_km / self.SPEEDS[mode]

        # Add fixed overhead for flights (security, boarding)
        if "flight" in mode:
            time_hours += 2.5
            cost += 50.0  # Base airport fees

        return {
            "distance_km": distance_km,
            "mode": mode,
            "carbon_kg": round(carbon, 2),
            "cost_usd": round(cost, 2),
            "time_hours": round(time_hours, 2),
        }

    def optimize_itinerary(self, legs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluates an itinerary and returns optimized alternatives.
        For simplicity, this generates 3 variations: Fastest, Cheapest, Greenest.
        """
        # Base calculation (user's initial input)
        base_metrics = [
            self.calculate_leg_metrics(leg["distance_km"], leg["mode"]) for leg in legs
        ]

        # Generate alternatives by substituting modes where possible
        alternatives = {"greenest": [], "cheapest": [], "fastest": []}

        for leg in legs:
            dist = leg["distance_km"]

            # Greenest: Prefer train or EV
            if dist < 500:
                alternatives["greenest"].append(
                    self.calculate_leg_metrics(dist, "train")
                )
            else:
                alternatives["greenest"].append(
                    self.calculate_leg_metrics(
                        dist, "flight_long" if dist > 1000 else "flight_short"
                    )
                )

            # Cheapest: Prefer bus or train
            alternatives["cheapest"].append(
                self.calculate_leg_metrics(dist, "bus" if dist < 800 else "train")
            )

            # Fastest: Prefer flight or car
            alternatives["fastest"].append(
                self.calculate_leg_metrics(
                    dist, "flight_short" if dist < 1000 else "flight_long"
                )
            )

        # Aggregate totals
        def aggregate(metrics_list):
            return {
                "total_carbon_kg": round(sum(m["carbon_kg"] for m in metrics_list), 2),
                "total_cost_usd": round(sum(m["cost_usd"] for m in metrics_list), 2),
                "total_time_hours": round(
                    sum(m["time_hours"] for m in metrics_list), 2
                ),
                "legs": metrics_list,
            }

        return {
            "original": aggregate(base_metrics),
            "greenest": aggregate(alternatives["greenest"]),
            "cheapest": aggregate(alternatives["cheapest"]),
            "fastest": aggregate(alternatives["fastest"]),
        }
