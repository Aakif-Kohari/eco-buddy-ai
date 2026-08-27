"""
Remote Work Calculator.
Models the carbon savings of telecommuting, factoring in home office energy vs. avoided commute and office overhead.
"""

from typing import Dict, Any
from src.carbon.avoided_emissions_tracker import AvoidedEmissionsTracker


class RemoteWorkCalculator:
    """Calculates the specific avoided emissions of remote work."""

    def __init__(self):
        self.tracker = AvoidedEmissionsTracker()
        # Default factors (kg CO2e)
        self.avg_commute_per_day = 10.0  # Round trip
        self.office_overhead_per_day = 15.0  # Shared lighting, HVAC, etc.
        self.home_office_energy_per_day = 4.0  # Extra heating/cooling, electronics

    def calculate_remote_work_savings(
        self,
        days_per_week: float,
        weeks_per_year: float = 48.0,
        commute_distance_km: float = 20.0,
        vehicle_type: str = "ice_car",
    ) -> Dict[str, Any]:
        """
        Calculates annual avoided emissions from working from home.

        Args:
            days_per_week: Number of days worked from home per week.
            weeks_per_year: Number of working weeks per year.
            commute_distance_km: One-way commute distance.
            vehicle_type: "ice_car", "ev", or "public_transit"
        """
        # Adjust commute factor based on vehicle type
        vehicle_factors = {
            "ice_car": 0.192,  # kg per km
            "ev": 0.053,
            "public_transit": 0.105,
        }
        commute_factor_per_km = vehicle_factors.get(vehicle_type, 0.192)

        # Baseline: Commute + Office Overhead
        daily_commute_emissions = (commute_distance_km * 2) * commute_factor_per_km
        baseline_per_day = daily_commute_emissions + self.office_overhead_per_day

        # Alternative: Home Office Energy
        alternative_per_day = self.home_office_energy_per_day

        total_days = days_per_week * weeks_per_year

        # Log to tracker
        record = self.tracker.log_avoided_activity(
            activity_type=f"remote_work_{vehicle_type}",
            quantity=total_days,
            baseline_factor=baseline_per_day,
            alternative_factor=alternative_per_day,
        )

        return {
            "days_per_year": total_days,
            "baseline_per_day_kg": round(baseline_per_day, 2),
            "alternative_per_day_kg": round(alternative_per_day, 2),
            "annual_avoided_kg": record["avoided_kg"],
            "equivalent_trees": round(
                record["avoided_kg"] / 20.0, 1
            ),  # ~20kg per tree per year
        }
