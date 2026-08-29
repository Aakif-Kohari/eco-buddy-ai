"""
Renovation Carbon Estimator.
Calculates the total embodied carbon of a project based on material volumes, weights, and transportation distances.
"""

from typing import Dict, Any
from sustainable_material_db import SustainableMaterialDB


class RenovationCarbonEstimator:
    """Estimates the upfront embodied carbon of home renovation projects."""

    # Transportation emission factor: kg CO2e per tonne-km
    TRANSPORT_FACTOR = 0.1

    def __init__(
        self, material_key: str, volume_m3: float, transport_distance_km: float
    ):
        self.db = SustainableMaterialDB()
        self.material_key = material_key.lower()
        self.volume_m3 = max(0.0, volume_m3)
        self.transport_distance_km = max(0.0, transport_distance_km)

        self.specs = self.db.get_material_specs(self.material_key)
        if not self.specs:
            raise ValueError(f"Unknown material: {material_key}")

    def calculate_embodied_carbon(self) -> Dict[str, Any]:
        """Calculates the total embodied carbon including transportation."""
        # 1. Calculate weight
        weight_kg = self.volume_m3 * self.specs["density_kg_m3"]
        weight_tonnes = weight_kg / 1000.0

        # 2. Calculate material embodied carbon
        material_carbon_kg = weight_kg * self.specs["embodied_carbon_per_kg"]

        # 3. Calculate transportation carbon
        transport_carbon_kg = (
            weight_tonnes * self.transport_distance_km * self.TRANSPORT_FACTOR
        )

        # 4. Total upfront carbon
        total_carbon_kg = material_carbon_kg + transport_carbon_kg

        return {
            "material_name": self.specs["name"],
            "volume_m3": self.volume_m3,
            "weight_kg": round(weight_kg, 2),
            "material_carbon_kg": round(material_carbon_kg, 2),
            "transport_carbon_kg": round(transport_carbon_kg, 2),
            "total_embodied_carbon_kg": round(total_carbon_kg, 2),
            "recyclability_score": self.specs["recyclability_score"],
            "lifespan_years": self.specs["lifespan_years"],
        }

    def calculate_low_carbon_score(self, total_carbon_kg: float) -> float:
        """
        Calculates a 'Low-Carbon Renovation Score' (0-100).
        Lower carbon and higher recyclability yield a higher score.
        Mock benchmark: 1000 kg CO2e is considered "high" for a small project.
        """
        # Invert carbon impact (lower is better)
        carbon_score = max(0.0, 100.0 - (total_carbon_kg / 10.0))

        # Weight carbon score (70%) and recyclability (30%)
        final_score = (carbon_score * 0.7) + (self.specs["recyclability_score"] * 0.3)

        return min(100.0, max(0.0, round(final_score, 1)))

    def get_green_swap_recommendations(self) -> list:
        """Suggests lower-carbon alternatives within the same material family."""
        recs = []
        if (
            "concrete" in self.material_key
            and self.material_key != "concrete_low_carbon"
        ):
            recs.append(
                "🧱 **Swap:** Use Low-Carbon Concrete (fly ash or slag blend) to reduce embodied carbon by up to 40%."
            )
        if "steel" in self.material_key and self.material_key != "steel_recycled":
            recs.append(
                "🏗️ **Swap:** Specify Recycled Steel, which has roughly 1/3 the embodied carbon of virgin steel."
            )
        if "wood" in self.material_key and self.material_key != "wood_reclaimed":
            recs.append(
                "🪵 **Swap:** Choose Reclaimed Wood to avoid the processing emissions of virgin lumber."
            )
        if "hempcrete" not in self.material_key:
            recs.append(
                "🌿 **Alternative:** For non-structural insulation or infill, consider Hempcrete, which is carbon negative."
            )

        return recs
