"""
Daily Commute Optimizer.
Evaluates multiple daily commute modes, calculating time, cost, and carbon footprint based on distance and mock conditions.
"""

from typing import Dict, Any, List


class DailyCommuteOptimizer:
    """Optimizes daily commute choices based on dynamic environmental and logistical factors."""

    # Base metrics per km: [carbon_kg, cost_usd, time_minutes]
    BASE_METRICS = {
        "driving_gas": [0.192, 0.15, 1.2],
        "driving_ev": [0.053, 0.04, 1.2],
        "public_transit": [0.105, 0.05, 1.5],
        "biking": [0.0, 0.0, 3.0],
        "walking": [0.0, 0.0, 12.0],
    }

    # Weather multipliers: [carbon_multiplier, time_multiplier]
    WEATHER_IMPACT = {
        "sunny": {
            "biking": [1.0, 1.0],
            "walking": [1.0, 1.0],
            "driving_gas": [1.0, 1.0],
        },
        "rainy": {
            "biking": [1.2, 1.3],
            "walking": [1.1, 1.4],
            "driving_gas": [1.05, 1.2],
        },
        "snowy": {
            "biking": [1.5, 2.0],
            "walking": [1.2, 1.8],
            "driving_gas": [1.15, 1.5],
        },
        "extreme_heat": {
            "biking": [1.3, 1.2],
            "walking": [1.2, 1.3],
            "driving_gas": [1.1, 1.1],
        },
    }

    # Traffic multipliers: [time_multiplier]
    TRAFFIC_IMPACT = {
        "light": {"driving_gas": 1.0, "driving_ev": 1.0, "public_transit": 1.0},
        "moderate": {"driving_gas": 1.3, "driving_ev": 1.3, "public_transit": 1.1},
        "heavy": {"driving_gas": 1.8, "driving_ev": 1.8, "public_transit": 1.2},
    }

    def __init__(
        self, distance_km: float, weather: str = "sunny", traffic: str = "light"
    ):
        self.distance_km = max(0.1, distance_km)
        self.weather = weather.lower()
        self.traffic = traffic.lower()

    def evaluate_modes(self) -> List[Dict[str, Any]]:
        """Evaluates all commute modes and returns a ranked list based on carbon footprint."""
        results = []

        for mode, base in self.BASE_METRICS.items():
            base_carbon, base_cost, base_time = base

            # Apply weather impact
            weather_mult = self.WEATHER_IMPACT.get(self.weather, {}).get(
                mode, [1.0, 1.0]
            )
            carbon_mult = weather_mult[0]
            time_mult = weather_mult[1]

            # Apply traffic impact
            traffic_mult = self.TRAFFIC_IMPACT.get(self.traffic, {}).get(mode, 1.0)
            time_mult *= traffic_mult

            # Calculate final metrics
            total_carbon = round(self.distance_km * base_carbon * carbon_mult, 3)
            total_cost = round(self.distance_km * base_cost, 2)
            total_time = round(self.distance_km * base_time * time_mult, 1)

            results.append(
                {
                    "mode": mode.replace("_", " ").title(),
                    "mode_key": mode,
                    "carbon_kg": total_carbon,
                    "cost_usd": total_cost,
                    "time_minutes": total_time,
                    "weather_impact": carbon_mult > 1.0 or time_mult > 1.0,
                }
            )

        # Sort by carbon footprint (ascending)
        return sorted(results, key=lambda x: x["carbon_kg"])

    def get_baseline_carbon(self, mode: str = "driving_gas") -> float:
        """Returns the baseline carbon footprint for a specific mode without dynamic modifiers."""
        base_carbon = self.BASE_METRICS.get(mode, self.BASE_METRICS["driving_gas"])[0]
        return round(self.distance_km * base_carbon, 3)
