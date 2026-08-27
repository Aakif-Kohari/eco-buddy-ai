"""
Greywater Recycling Simulator.
Models the potential water and energy savings from installing a basic greywater recycling system.
"""

from typing import Dict, Any
from src.energy.water_energy_nexus import WaterEnergyNexus


class GreywaterSimulator:
    """Simulates the dual water and energy savings of greywater recycling."""

    # Typical household greywater generation rates (liters per person per day)
    GREYWATER_GENERATION = {"shower": 40.0, "bathroom_sink": 10.0, "laundry": 30.0}

    # Typical household greywater reuse applications
    REUSE_APPLICATIONS = {
        "toilet_flushing": 30.0,  # liters per person per day
        "garden_irrigation": 20.0,  # liters per person per day
    }

    def __init__(self, household_size: int, grid_carbon_intensity: float = 0.4):
        self.household_size = max(1, household_size)
        self.nexus = WaterEnergyNexus(grid_carbon_intensity)

    def calculate_daily_greywater_potential(self) -> Dict[str, float]:
        """Calculates the total volume of greywater generated daily."""
        total_per_person = sum(self.GREYWATER_GENERATION.values())
        return {
            "per_person_liters": total_per_person,
            "household_total_liters": round(total_per_person * self.household_size, 2),
        }

    def simulate_recycling_savings(
        self, reuse_efficiency_pct: float = 80.0
    ) -> Dict[str, Any]:
        """
        Simulates the savings from recycling greywater for toilet flushing and irrigation.

        Args:
            reuse_efficiency_pct: Percentage of generated greywater successfully captured and reused.
        """
        generation = self.calculate_daily_greywater_potential()
        total_generated = generation["household_total_liters"]

        # Calculate how much can be reused
        total_reuse_demand_per_person = sum(self.REUSE_APPLICATIONS.values())
        household_reuse_demand = total_reuse_demand_per_person * self.household_size

        # Actual reuse is limited by either generation (adjusted for efficiency) or demand
        available_for_reuse = total_generated * (reuse_efficiency_pct / 100.0)
        actual_reused_liters = min(available_for_reuse, household_reuse_demand)

        # Calculate savings
        # 1. Water savings: direct volume reduction
        water_saved_daily = actual_reused_liters

        # 2. Energy savings:
        # - Avoided municipal pumping/treatment for the reused volume
        # - Avoided heating energy if replacing hot water uses (simplified: assume 50% of reused water displaces heated water)
        displaced_hot_water_liters = actual_reused_liters * 0.5
        heating_energy_saved = self.nexus.calculate_heating_energy(
            displaced_hot_water_liters, 40.0
        )  # Assume 40C heated water

        treatment_energy_saved = (
            actual_reused_liters / 1000.0
        ) * self.nexus.MUNICIPAL_TREATMENT_PUMPING
        total_energy_saved_daily = heating_energy_saved + treatment_energy_saved

        carbon_saved_daily = total_energy_saved_daily * self.nexus.grid_carbon_intensity

        return {
            "household_size": self.household_size,
            "daily_greywater_generated_liters": generation["household_total_liters"],
            "daily_water_reused_liters": round(actual_reused_liters, 2),
            "daily_water_saved_liters": round(water_saved_daily, 2),
            "daily_energy_saved_kwh": round(total_energy_saved_daily, 4),
            "daily_carbon_saved_kg": round(carbon_saved_daily, 4),
            "annual_water_saved_liters": round(water_saved_daily * 365, 2),
            "annual_carbon_saved_kg": round(carbon_saved_daily * 365, 2),
        }
