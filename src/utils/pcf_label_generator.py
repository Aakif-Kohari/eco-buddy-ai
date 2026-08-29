"""
Product Carbon Footprint (PCF) Label Generator.
Aggregates material inputs, manufacturing energy, and transportation into a standardized PCF value.
"""

from typing import Dict, Any, List


class PCFLabelGenerator:
    """Generates standardized Product Carbon Footprint labels."""

    # Emission factors for common inputs
    MATERIAL_FACTORS = {
        "plastic": 2.5,  # kg CO2e / kg
        "metal": 4.0,  # kg CO2e / kg
        "wood": 0.5,  # kg CO2e / kg
        "glass": 1.2,  # kg CO2e / kg
        "paper": 1.0,  # kg CO2e / kg
    }

    TRANSPORT_FACTORS = {
        "truck": 0.1,  # kg CO2e / tonne-km
        "ship": 0.01,  # kg CO2e / tonne-km
        "air": 1.0,  # kg CO2e / tonne-km
    }

    def __init__(self):
        pass

    def calculate_material_impact(self, materials: List[Dict[str, float]]) -> float:
        """Calculates total carbon impact from raw materials."""
        total = 0.0
        for mat in materials:
            name = mat["name"].lower()
            weight_kg = mat["weight_kg"]
            factor = self.MATERIAL_FACTORS.get(name, 2.0)  # Default to 2.0 if unknown
            total += weight_kg * factor
        return round(total, 2)

    def calculate_manufacturing_impact(
        self, energy_kwh: float, grid_factor: float = 0.4
    ) -> float:
        """Calculates carbon impact from manufacturing energy use."""
        return round(energy_kwh * grid_factor, 2)

    def calculate_transport_impact(
        self, weight_kg: float, distance_km: float, mode: str
    ) -> float:
        """Calculates carbon impact from transportation."""
        mode_lower = mode.lower()
        factor = self.TRANSPORT_FACTORS.get(mode_lower, 0.1)
        weight_tonnes = weight_kg / 1000.0
        return round(weight_tonnes * distance_km * factor, 2)

    def generate_label(
        self,
        product_name: str,
        materials: List[Dict[str, float]],
        manufacturing_energy_kwh: float,
        transport_distance_km: float,
        transport_mode: str,
    ) -> Dict[str, Any]:
        """Generates a complete PCF label dictionary."""
        mat_impact = self.calculate_material_impact(materials)
        mfg_impact = self.calculate_manufacturing_impact(manufacturing_energy_kwh)
        trans_impact = self.calculate_transport_impact(
            sum(m["weight_kg"] for m in materials),
            transport_distance_km,
            transport_mode,
        )

        total_pcf = round(mat_impact + mfg_impact + trans_impact, 2)

        return {
            "product_name": product_name,
            "total_pcf_kg_co2e": total_pcf,
            "breakdown": {
                "materials_kg_co2e": mat_impact,
                "manufacturing_kg_co2e": mfg_impact,
                "transport_kg_co2e": trans_impact,
            },
            "grade": self._assign_grade(total_pcf),
            "methodology": "ISO 14067 compliant simplified assessment",
        }

    def _assign_grade(self, total_pcf: float) -> str:
        """Assigns a simple A-E grade based on total footprint (context-dependent)."""
        if total_pcf < 1.0:
            return "A"
        elif total_pcf < 5.0:
            return "B"
        elif total_pcf < 10.0:
            return "C"
        elif total_pcf < 20.0:
            return "D"
        else:
            return "E"
