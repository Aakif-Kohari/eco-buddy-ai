"""
Water-Energy Nexus Analyzer.
Calculates the embedded energy in household water consumption based on temperature, volume, and grid intensity.
"""

from typing import Dict, Any, List


class WaterEnergyNexus:
    """Quantifies the hidden energy and carbon costs of household water usage."""

    # Constants
    SPECIFIC_HEAT_WATER = 4.186  # kJ/kg°C
    WATER_DENSITY = 1.0  # kg/L
    JOULES_TO_KWH = 2.77778e-7  # Conversion factor

    # Energy to treat and pump municipal water (kWh per cubic meter)
    MUNICIPAL_TREATMENT_PUMPING = 0.35  # kWh/m³

    def __init__(self, grid_carbon_intensity: float = 0.4):
        """
        Args:
            grid_carbon_intensity: kg CO2e per kWh (default 0.4 is a global average)
        """
        self.grid_carbon_intensity = grid_carbon_intensity

    def calculate_heating_energy(
        self,
        volume_liters: float,
        temp_celsius: float,
        inlet_temp_celsius: float = 15.0,
    ) -> float:
        """Calculates the energy required to heat a given volume of water."""
        if temp_celsius <= inlet_temp_celsius:
            return 0.0

        mass_kg = volume_liters * self.WATER_DENSITY
        temp_diff = temp_celsius - inlet_temp_celsius

        # Energy in kJ
        energy_kj = mass_kg * self.SPECIFIC_HEAT_WATER * temp_diff
        # Convert to kWh
        energy_kwh = energy_kj * self.JOULES_TO_KWH

        return round(energy_kwh, 4)

    def calculate_total_nexus_impact(
        self, volume_liters: float, temp_celsius: float, is_hot_water: bool = True
    ) -> Dict[str, Any]:
        """Calculates the total energy and carbon footprint of water usage."""
        volume_m3 = volume_liters / 1000.0

        # 1. Municipal treatment and pumping energy
        treatment_energy_kwh = volume_m3 * self.MUNICIPAL_TREATMENT_PUMPING

        # 2. Heating energy (if applicable)
        heating_energy_kwh = 0.0
        if is_hot_water:
            heating_energy_kwh = self.calculate_heating_energy(
                volume_liters, temp_celsius
            )

        total_energy_kwh = treatment_energy_kwh + heating_energy_kwh
        total_carbon_kg = total_energy_kwh * self.grid_carbon_intensity

        return {
            "volume_liters": volume_liters,
            "treatment_energy_kwh": round(treatment_energy_kwh, 4),
            "heating_energy_kwh": round(heating_energy_kwh, 4),
            "total_energy_kwh": round(total_energy_kwh, 4),
            "total_carbon_kg": round(total_carbon_kg, 4),
            "is_hot_water": is_hot_water,
        }

    def compare_nexus_scenarios(
        self,
        baseline_liters: float,
        baseline_temp: float,
        optimized_liters: float,
        optimized_temp: float,
    ) -> Dict[str, Any]:
        """Compares the nexus impact of a baseline scenario vs an optimized scenario."""
        baseline_impact = self.calculate_total_nexus_impact(
            baseline_liters, baseline_temp
        )
        optimized_impact = self.calculate_total_nexus_impact(
            optimized_liters, optimized_temp
        )

        energy_saved = (
            baseline_impact["total_energy_kwh"] - optimized_impact["total_energy_kwh"]
        )
        carbon_saved = (
            baseline_impact["total_carbon_kg"] - optimized_impact["total_carbon_kg"]
        )
        water_saved = baseline_liters - optimized_liters

        return {
            "baseline": baseline_impact,
            "optimized": optimized_impact,
            "water_saved_liters": round(water_saved, 2),
            "energy_saved_kwh": round(energy_saved, 4),
            "carbon_saved_kg": round(carbon_saved, 4),
            "is_positive_impact": energy_saved > 0 and water_saved > 0,
        }
