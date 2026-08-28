"""
Sustainable Material Database.
Manages a comprehensive dataset of common building materials with cradle-to-gate emission factors and recyclability scores.
"""

from typing import Dict, Any, Optional


class SustainableMaterialDB:
    """Provides data on the embodied carbon and end-of-life value of construction materials."""

    # Mock dataset: density (kg/m3), embodied carbon (kg CO2e per kg), recyclability score (0-100)
    MATERIAL_DATABASE = {
        "concrete_standard": {
            "name": "Standard Concrete",
            "density_kg_m3": 2400.0,
            "embodied_carbon_per_kg": 0.15,
            "recyclability_score": 40,
            "lifespan_years": 50,
        },
        "concrete_low_carbon": {
            "name": "Low-Carbon Concrete (Fly Ash Blend)",
            "density_kg_m3": 2400.0,
            "embodied_carbon_per_kg": 0.09,
            "recyclability_score": 40,
            "lifespan_years": 50,
        },
        "steel_virgin": {
            "name": "Virgin Steel",
            "density_kg_m3": 7850.0,
            "embodied_carbon_per_kg": 1.85,
            "recyclability_score": 90,
            "lifespan_years": 100,
        },
        "steel_recycled": {
            "name": "Recycled Steel",
            "density_kg_m3": 7850.0,
            "embodied_carbon_per_kg": 0.60,
            "recyclability_score": 95,
            "lifespan_years": 100,
        },
        "wood_virgin": {
            "name": "Virgin Hardwood",
            "density_kg_m3": 700.0,
            "embodied_carbon_per_kg": 0.50,  # Net positive due to processing/transport
            "recyclability_score": 60,
            "lifespan_years": 30,
        },
        "wood_reclaimed": {
            "name": "Reclaimed Wood",
            "density_kg_m3": 700.0,
            "embodied_carbon_per_kg": 0.05,  # Very low, mostly transport
            "recyclability_score": 80,
            "lifespan_years": 30,
        },
        "hempcrete": {
            "name": "Hempcrete",
            "density_kg_m3": 400.0,
            "embodied_carbon_per_kg": -0.10,  # Carbon negative (sequesters more than it emits)
            "recyclability_score": 70,
            "lifespan_years": 40,
        },
    }

    def __init__(self):
        self.database = self.MATERIAL_DATABASE

    def get_material_specs(self, material_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves specifications for a given material key."""
        return self.database.get(material_key.lower())

    def get_all_materials(self) -> list:
        """Returns a list of all available material keys."""
        return list(self.database.keys())

    def get_material_display_name(self, material_key: str) -> str:
        """Returns the human-readable name of the material."""
        specs = self.get_material_specs(material_key)
        return specs["name"] if specs else material_key.replace("_", " ").title()

    def get_materials_by_category(self, category: str) -> list:
        """Filters materials by a broad category (mock implementation)."""
        # Simple keyword matching for demonstration
        return [key for key in self.database.keys() if category.lower() in key.lower()]
