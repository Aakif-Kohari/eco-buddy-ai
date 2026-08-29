"""
Textile Lifecycle Assessment (LCA) Engine.
Manages dataset of fabric types with cradle-to-gate emission factors, water usage, and microplastic shedding rates.
"""

from typing import Dict, Any

# Base impacts per kg of material
# Carbon: kg CO2e/kg, Water: liters/kg, Microplastics: mg/kg per wash
FABRIC_DATABASE = {
    "conventional cotton": {
        "carbon_factor": 8.0,
        "water_factor": 10000.0,
        "microplastic_factor": 0.0,
        "description": "High water and pesticide usage, but biodegradable.",
    },
    "organic cotton": {
        "carbon_factor": 6.0,
        "water_factor": 9000.0,
        "microplastic_factor": 0.0,
        "description": "Lower chemical impact, slightly better water efficiency.",
    },
    "polyester": {
        "carbon_factor": 9.0,
        "water_factor": 50.0,
        "microplastic_factor": 150.0,
        "description": "Fossil-fuel derived, high carbon, sheds microplastics.",
    },
    "recycled polyester": {
        "carbon_factor": 5.0,
        "water_factor": 40.0,
        "microplastic_factor": 150.0,
        "description": "Lower carbon than virgin polyester, but still sheds microplastics.",
    },
    "wool": {
        "carbon_factor": 15.0,
        "water_factor": 500.0,
        "microplastic_factor": 0.0,
        "description": "High methane emissions from sheep, but durable and biodegradable.",
    },
    "linen": {
        "carbon_factor": 2.0,
        "water_factor": 2000.0,
        "microplastic_factor": 0.0,
        "description": "Very low impact, requires minimal water and pesticides.",
    },
}


class TextileLCAEngine:
    """Calculates lifecycle environmental impacts of textiles."""

    def __init__(self):
        self.database = FABRIC_DATABASE

    def get_material_data(self, material: str) -> Dict[str, Any]:
        """Retrieves base impact data for a material."""
        material_lower = material.lower()
        for key in self.database:
            if key in material_lower:
                return {"material": key, **self.database[key]}

        # Default to conventional cotton if unknown
        return {
            "material": "unknown (defaulted to conventional cotton)",
            **self.database["conventional cotton"],
        }

    def calculate_washing_impact(
        self, material: str, weight_kg: float, num_washes: int
    ) -> Dict[str, float]:
        """Calculates the use-phase impact (washing) over the garment's life."""
        data = self.get_material_data(material)

        # Microplastics are the primary washing impact for synthetics
        microplastics_mg = data["microplastic_factor"] * weight_kg * num_washes

        # Water and energy for washing (approx 0.5 kWh and 50L per wash per kg)
        wash_carbon_kg = (
            num_washes * weight_kg * 0.5 * 0.4
        )  # 0.4 kg CO2e per kWh grid average
        wash_water_l = num_washes * weight_kg * 50.0

        return {
            "washing_carbon_kg": round(wash_carbon_kg, 2),
            "washing_water_l": round(wash_water_l, 2),
            "microplastics_mg": round(microplastics_mg, 2),
        }
