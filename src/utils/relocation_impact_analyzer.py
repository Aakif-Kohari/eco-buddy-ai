"""
Relocation Impact Analyzer.
Calculates the differential carbon footprint between a user's current location and a potential destination.
"""

from typing import Dict, Any, Optional
from src.utils.city_environmental_db import CityEnvironmentalDB


class RelocationImpactAnalyzer:
    """Analyzes the environmental impact of relocating between cities."""

    def __init__(self):
        self.db = CityEnvironmentalDB()
        # Baseline annual emissions for an average person (kg CO2e)
        self.baseline_transport = 2000.0
        self.baseline_housing_energy = 3000.0

    def calculate_differential_footprint(
        self, current_city: str, target_city: str
    ) -> Optional[Dict[str, Any]]:
        """Calculates the change in carbon footprint when moving from current to target city."""
        current_profile = self.db.get_city_profile(current_city)
        target_profile = self.db.get_city_profile(target_city)

        if not current_profile or not target_profile:
            return None

        # 1. Transport Impact (based on transit score)
        # Higher transit score = lower personal transport emissions
        current_transport_factor = 1.0 - (current_profile["transit_score"] / 200.0)
        target_transport_factor = 1.0 - (target_profile["transit_score"] / 200.0)

        current_transport_emissions = self.baseline_transport * current_transport_factor
        target_transport_emissions = self.baseline_transport * target_transport_factor
        transport_delta = target_transport_emissions - current_transport_emissions

        # 2. Housing Energy Impact (based on climate and efficiency)
        # Total degree days drive heating/cooling needs
        current_degree_days = (
            current_profile["heating_degree_days"]
            + current_profile["cooling_degree_days"]
        )
        target_degree_days = (
            target_profile["heating_degree_days"]
            + target_profile["cooling_degree_days"]
        )

        current_housing_emissions = (
            self.baseline_housing_energy
            * (current_degree_days / 5000.0)
            * current_profile["housing_efficiency_factor"]
        )
        target_housing_emissions = (
            self.baseline_housing_energy
            * (target_degree_days / 5000.0)
            * target_profile["housing_efficiency_factor"]
        )
        housing_delta = target_housing_emissions - current_housing_emissions

        # 3. Grid Intensity Impact (applied to housing energy)
        # We approximate that housing energy is 70% electricity for this model
        current_grid_impact = (current_housing_emissions * 0.7) * (
            current_profile["grid_intensity"] / 0.4
        )  # 0.4 is global avg
        target_grid_impact = (target_housing_emissions * 0.7) * (
            target_profile["grid_intensity"] / 0.4
        )
        grid_delta = target_grid_impact - current_grid_impact

        total_delta = transport_delta + housing_delta + grid_delta

        return {
            "current_city": current_profile["name"],
            "target_city": target_profile["name"],
            "current_total_estimated": round(
                current_transport_emissions + current_housing_emissions, 1
            ),
            "target_total_estimated": round(
                target_transport_emissions + target_housing_emissions + grid_delta, 1
            ),
            "annual_delta_kg_co2e": round(total_delta, 1),
            "breakdown": {
                "transport_delta_kg": round(transport_delta, 1),
                "housing_climate_delta_kg": round(housing_delta, 1),
                "grid_intensity_delta_kg": round(grid_delta, 1),
            },
            "recommendations": self._generate_recommendations(
                current_profile, target_profile, total_delta
            ),
        }

    def _generate_recommendations(
        self, current: dict, target: dict, total_delta: float
    ) -> list:
        """Generates personalized climate adaptation tips based on the move."""
        recs = []
        if total_delta > 500:
            recs.append(
                "⚠️ **High Impact Move:** Your target city has a significantly higher baseline carbon footprint. Consider offsetting this increase."
            )
        elif total_delta < -500:
            recs.append(
                "🌟 **Eco-Friendly Move:** Your target city offers a much lower carbon lifestyle. Great choice!"
            )

        if target["transit_score"] < current["transit_score"]:
            recs.append(
                f"🚗 **Transit Warning:** Public transit is less developed in {target['name']}. Consider an EV or e-bike to compensate."
            )
        elif target["transit_score"] > current["transit_score"]:
            recs.append(
                f"🚆 **Transit Opportunity:** Take advantage of {target['name']}'s excellent public transit to reduce car dependency."
            )

        if target["housing_efficiency_factor"] > 1.0:
            recs.append(
                "🏠 **Housing Tip:** Look for apartments with high energy efficiency ratings (e.g., LEED, Passive House) to offset the local climate demands."
            )

        return recs
