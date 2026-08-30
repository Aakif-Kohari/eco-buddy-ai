"""Simulation engine for Urban Heat Island (UHI) mitigation, evapotranspiration cooling, and agroforestry planning.
"""

import math
from typing import Dict, Any
from src.environment.urban_canopy_types import (
    UrbanZoneParameters,
    CanopyCoolingResult,
    TreeSpeciesType,
    SoilPermeabilityType,
)


class UrbanCanopyPlannerEngine:
    """Calculates thermodynamic temperature moderation, stormwater capture, and carbon storage."""

    SPECIES_PROPERTIES = {
        TreeSpeciesType.OAK: {"canopy_diameter_m": 8.0, "sequestration_kg_yr": 22.0, "transpiration_liters_day": 150.0, "lai": 5.2},
        TreeSpeciesType.MAPLE: {"canopy_diameter_m": 6.5, "sequestration_kg_yr": 16.0, "transpiration_liters_day": 110.0, "lai": 4.1},
        TreeSpeciesType.PINE: {"canopy_diameter_m": 5.0, "sequestration_kg_yr": 12.0, "transpiration_liters_day": 75.0, "lai": 3.8},
        TreeSpeciesType.BIRCH: {"canopy_diameter_m": 4.5, "sequestration_kg_yr": 10.0, "transpiration_liters_day": 85.0, "lai": 3.4},
        TreeSpeciesType.FRUIT_AGROFORESTRY: {"canopy_diameter_m": 5.5, "sequestration_kg_yr": 14.0, "transpiration_liters_day": 95.0, "lai": 4.0},
    }

    SOIL_FACTORS = {
        SoilPermeabilityType.CLAY_COMPACTED: {"runoff_coefficient": 0.70, "retention_multiplier": 0.5},
        SoilPermeabilityType.LOAMY_HEALTHY: {"runoff_coefficient": 0.35, "retention_multiplier": 1.0},
        SoilPermeabilityType.SANDY_POROUS: {"runoff_coefficient": 0.20, "retention_multiplier": 0.7},
        SoilPermeabilityType.BIOSWALE_ENGINEERED: {"runoff_coefficient": 0.05, "retention_multiplier": 1.4},
    }

    @classmethod
    def calculate_canopy_impact(cls, params: UrbanZoneParameters) -> CanopyCoolingResult:
        species = cls.SPECIES_PROPERTIES.get(params.selected_species, cls.SPECIES_PROPERTIES[TreeSpeciesType.OAK])
        soil = cls.SOIL_FACTORS.get(params.soil_type, cls.SOIL_FACTORS[SoilPermeabilityType.LOAMY_HEALTHY])

        # Tree crown area (m²)
        crown_radius = species["canopy_diameter_m"] / 2.0
        single_tree_area = math.pi * (crown_radius ** 2)

        # Additional canopy area needed
        delta_canopy_pct = max(0.0, params.target_canopy_cover_pct - params.current_canopy_cover_pct)
        delta_canopy_area_sq_m = params.district_area_sq_meters * (delta_canopy_pct / 100.0)

        recommended_tree_count = int(math.ceil(delta_canopy_area_sq_m / max(1.0, single_tree_area)))

        # Evapotranspiration and surface cooling calculation
        # Latent heat of vaporization of water ≈ 2.26 MJ/kg ≈ 0.627 kWh/kg (or per liter)
        daily_transpiration_total_liters = recommended_tree_count * species["transpiration_liters_day"]
        active_growing_days = 200.0
        annual_transpiration_liters = daily_transpiration_total_liters * active_growing_days
        latent_cooling_kwh = annual_transpiration_liters * 0.627

        # Empirical surface and ambient temperature drop model (Oke / Akbari microclimate model)
        # Every 10% canopy increase on impervious ground yields ~1.2°C surface reduction and ~0.45°C ambient air drop
        surface_temp_drop = (delta_canopy_pct / 10.0) * (1.20 * (1.0 + params.impervious_surface_fraction * 0.5))
        air_temp_drop = (delta_canopy_pct / 10.0) * (0.45 * (species["lai"] / 4.0))

        # Carbon sequestration
        annual_carbon_kg = recommended_tree_count * species["sequestration_kg_yr"]

        # Stormwater absorption
        # Volume = Area * Rainfall (m) * (1 - runoff_coeff)
        rainfall_meters = params.annual_rainfall_mm / 1000.0
        stormwater_absorbed_m3 = (delta_canopy_area_sq_m * rainfall_meters) * (1.0 - soil["runoff_coefficient"]) * soil["retention_multiplier"]

        # Building cooling energy savings ($0.14/kWh avoided air conditioning load)
        cooling_energy_savings_usd = (latent_cooling_kwh * 0.08) * 0.14

        # Thermal comfort classification
        if air_temp_drop >= 2.0:
            comfort_index = "Excellent: Substantial Urban Heat Island Mitigation (-2°C+)"
        elif air_temp_drop >= 1.0:
            comfort_index = "Moderate: Noticeable Neighborhood Cooling Benefit (-1°C to -2°C)"
        else:
            comfort_index = "Mild: Localized Canopy Shade Benefit (< 1°C)"

        return CanopyCoolingResult(
            zone_name=params.zone_name,
            surface_temperature_reduction_c=round(surface_temp_drop, 2),
            ambient_air_temperature_reduction_c=round(air_temp_drop, 2),
            evapotranspiration_cooling_kwh_per_year=round(latent_cooling_kwh, 1),
            annual_carbon_sequestration_kg_co2=round(annual_carbon_kg, 1),
            stormwater_runoff_absorbed_cubic_meters=round(stormwater_absorbed_m3, 1),
            cooling_energy_savings_usd=round(cooling_energy_savings_usd, 2),
            species_tree_count_recommended=recommended_tree_count,
            thermal_comfort_improvement_index=comfort_index,
        )
