"""
Fashion Impact Comparator.
Calculates total lifecycle impact based on material, weight, wears, and washing habits.
"""

from typing import Dict, Any, List
from src.utils.textile_lca_engine import TextileLCAEngine


class FashionImpactComparator:
    """Compares the environmental footprint of different garment choices."""

    def __init__(self):
        self.engine = TextileLCAEngine()

    def evaluate_garment(
        self,
        material: str,
        weight_kg: float,
        estimated_wears: int,
        washes_per_wear_ratio: float,
    ) -> Dict[str, Any]:
        """
        Evaluates a single garment's total lifecycle impact.

        Args:
            material: Type of fabric.
            weight_kg: Weight of the garment.
            estimated_wears: Total number of times the garment will be worn.
            washes_per_wear_ratio: How often it is washed (e.g., 0.5 means washed every 2 wears).
        """
        data = self.engine.get_material_data(material)
        num_washes = int(estimated_wears * washes_per_wear_ratio)

        # Production phase impacts
        production_carbon = data["carbon_factor"] * weight_kg
        production_water = data["water_factor"] * weight_kg

        # Use phase impacts
        use_phase = self.engine.calculate_washing_impact(
            material, weight_kg, num_washes
        )

        # Total impacts
        total_carbon = production_carbon + use_phase["washing_carbon_kg"]
        total_water = production_water + use_phase["washing_water_l"]

        # Impact per wear (crucial metric for sustainability)
        carbon_per_wear = total_carbon / estimated_wears if estimated_wears > 0 else 0
        water_per_wear = total_water / estimated_wears if estimated_wears > 0 else 0

        return {
            "material": data["material"],
            "description": data["description"],
            "weight_kg": weight_kg,
            "estimated_wears": estimated_wears,
            "num_washes": num_washes,
            "total_carbon_kg": round(total_carbon, 2),
            "total_water_l": round(total_water, 2),
            "total_microplastics_mg": use_phase["microplastics_mg"],
            "carbon_per_wear_kg": round(carbon_per_wear, 3),
            "water_per_wear_l": round(water_per_wear, 2),
            "breakdown": {
                "production_carbon_kg": round(production_carbon, 2),
                "production_water_l": round(production_water, 2),
                "washing_carbon_kg": use_phase["washing_carbon_kg"],
                "washing_water_l": use_phase["washing_water_l"],
            },
        }

    def compare_garments(self, garments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluates and ranks a list of garments by total carbon impact."""
        results = []
        for g in garments:
            result = self.evaluate_garment(
                g["material"],
                g["weight_kg"],
                g["estimated_wears"],
                g["washes_per_wear_ratio"],
            )
            results.append(result)

        # Sort by total carbon (lowest first)
        results.sort(key=lambda x: x["total_carbon_kg"])
        return results
