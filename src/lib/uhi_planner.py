"""
Urban Heat Island (UHI) & Biospheric Tree Canopy Microclimate Planner for EcoBuddy AI
Models impervious surface surface temperatures, microclimate cooling from green infrastructure,
and calculates building HVAC cooling load reductions.
"""

from typing import Dict, List, Any, Optional

SURFACE_ALBEDO_PROPERTIES = {
    "asphalt": {"albedo": 0.08, "thermal_emissivity": 0.90, "surface_temp_delta_c": 14.5},
    "concrete": {"albedo": 0.25, "thermal_emissivity": 0.88, "surface_temp_delta_c": 8.0},
    "dark_roof": {"albedo": 0.12, "thermal_emissivity": 0.90, "surface_temp_delta_c": 16.0},
    "cool_white_roof": {"albedo": 0.70, "thermal_emissivity": 0.92, "surface_temp_delta_c": 2.5},
    "dense_grass": {"albedo": 0.25, "thermal_emissivity": 0.95, "surface_temp_delta_c": -1.5},
    "tree_canopy": {"albedo": 0.18, "thermal_emissivity": 0.98, "surface_temp_delta_c": -4.2}
}


class UrbanHeatIslandPlanner:
    """Calculates urban heat index severity and tree canopy cooling/carbon benefits."""

    def __init__(self, surface_props: Optional[Dict[str, Dict[str, float]]] = None):
        self.surfaces = surface_props or SURFACE_ALBEDO_PROPERTIES

    def calculate_microclimate_cooling(
        self,
        district_area_sqm: float,
        impervious_pct: float,
        current_canopy_pct: float,
        proposed_canopy_addition_pct: float,
        baseline_ambient_temp_c: float = 34.0
    ) -> Dict[str, Any]:
        """
        Calculates localized ambient temperature reduction, evapotranspiration cooling, and energy savings.
        """
        target_canopy = min(current_canopy_pct + proposed_canopy_addition_pct, 80.0)
        impervious_ratio = min(max(impervious_pct / 100.0, 0.0), 1.0)

        # Baseline UHI elevation over rural background (°C)
        baseline_uhi_elevation = round(3.5 * impervious_ratio * (1.0 - (current_canopy_pct / 100.0)), 2)
        current_district_temp = round(baseline_ambient_temp_c + baseline_uhi_elevation, 2)

        # Temperature reduction per 10% canopy increase (~0.45°C - 0.7°C depending on imperviousness)
        delta_temp_reduction = round((proposed_canopy_addition_pct / 10.0) * (0.55 + 0.25 * impervious_ratio), 2)
        projected_district_temp = round(max(current_district_temp - delta_temp_reduction, baseline_ambient_temp_c), 2)

        # HVAC cooling energy reduction (~2.5% reduction in electricity per 1°C ambient cooling)
        hvac_cooling_energy_savings_pct = round(min(delta_temp_reduction * 2.8, 25.0), 1)

        # Carbon sequestration from newly planted urban canopy trees
        # Average mature urban tree covers ~30 sqm canopy and sequesters ~22 kg CO2/year
        additional_canopy_sqm = district_area_sqm * (proposed_canopy_addition_pct / 100.0)
        estimated_trees_planted = int(additional_canopy_sqm / 30.0)
        annual_co2_sequestered_kg = round(estimated_trees_planted * 22.0, 2)

        return {
            "district_area_sqm": district_area_sqm,
            "current_district_temp_c": current_district_temp,
            "projected_district_temp_c": projected_district_temp,
            "ambient_cooling_delta_c": delta_temp_reduction,
            "hvac_energy_savings_pct": hvac_cooling_energy_savings_pct,
            "estimated_trees_planted": estimated_trees_planted,
            "annual_co2_sequestered_kg": annual_co2_sequestered_kg,
            "stormwater_interception_m3_yr": round(additional_canopy_sqm * 0.45, 1)
        }
