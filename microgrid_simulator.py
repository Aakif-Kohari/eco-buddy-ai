"""
Microgrid Simulator.
Models hourly solar generation profiles, household demand curves, and grid independence metrics for a mock neighborhood.
"""

import math
from typing import Dict, Any, List


class MicrogridSimulator:
    """Simulates the energy dynamics of a local neighborhood microgrid."""

    def __init__(self, num_households: int = 5):
        self.num_households = num_households
        # Mock household profiles: {id: {"solar_kw": float, "avg_demand_kw": float}}
        self.households = {}
        for i in range(num_households):
            self.households[f"house_{i + 1}"] = {
                "solar_kw": 5.0 if i % 2 == 0 else 0.0,  # Every other house has solar
                "avg_demand_kw": 1.5 + (i * 0.2),  # Varying demand
            }

    def generate_hourly_profile(self, hour: int) -> Dict[str, Any]:
        """
        Generates energy generation and demand for a specific hour of the day (0-23).

        Args:
            hour: The hour of the day (0-23).

        Returns:
            Dictionary containing total generation, total demand, and net grid interaction.
        """
        total_generation_kw = 0.0
        total_demand_kw = 0.0
        household_details = {}

        for h_id, specs in self.households.items():
            # Solar generation follows a bell curve peaking at noon (hour 12)
            if specs["solar_kw"] > 0:
                # Simple solar model: 0 at night, peaks at 12
                sun_factor = (
                    max(0.0, math.sin((hour - 6) * math.pi / 12))
                    if 6 <= hour <= 18
                    else 0.0
                )
                # Add some random weather variation (mocked as a fixed 0.8-1.0 multiplier)
                weather_factor = 0.9
                generation = specs["solar_kw"] * sun_factor * weather_factor
            else:
                generation = 0.0

            # Demand varies: higher in morning (7-9) and evening (18-21)
            demand_multiplier = 1.0
            if 7 <= hour <= 9 or 18 <= hour <= 21:
                demand_multiplier = 1.5
            elif 0 <= hour <= 5:
                demand_multiplier = 0.5

            demand = specs["avg_demand_kw"] * demand_multiplier

            total_generation_kw += generation
            total_demand_kw += demand

            household_details[h_id] = {
                "generation_kw": round(generation, 2),
                "demand_kw": round(demand, 2),
                "net_kw": round(
                    generation - demand, 2
                ),  # Positive = excess, Negative = deficit
            }

        net_grid_interaction = total_demand_kw - total_generation_kw

        return {
            "hour": hour,
            "total_generation_kw": round(total_generation_kw, 2),
            "total_demand_kw": round(total_demand_kw, 2),
            "net_grid_import_kw": round(max(0.0, net_grid_interaction), 2),
            "net_grid_export_kw": round(max(0.0, -net_grid_interaction), 2),
            "household_details": household_details,
        }

    def simulate_full_day(self) -> List[Dict[str, Any]]:
        """Simulates a full 24-hour period for the microgrid."""
        daily_profile = []
        for hour in range(24):
            daily_profile.append(self.generate_hourly_profile(hour))
        return daily_profile

    def calculate_grid_independence(self, daily_profile: List[Dict[str, Any]]) -> float:
        """Calculates the percentage of total demand met by local generation."""
        total_demand = sum(h["total_demand_kw"] for h in daily_profile)
        total_local_used = sum(
            h["total_generation_kw"] for h in daily_profile
        )  # Simplified: assumes all local gen is used locally or exported

        if total_demand == 0:
            return 100.0

        # More accurate: local used = total gen - total exported
        total_exported = sum(h["net_grid_export_kw"] for h in daily_profile)
        actual_local_used = (
            sum(h["total_generation_kw"] for h in daily_profile) - total_exported
        )

        independence_pct = (actual_local_used / total_demand) * 100
        return round(min(100.0, max(0.0, independence_pct)), 1)
