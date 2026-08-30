"""Domain types and data models for Urban Canopy and Agroforestry Microclimate Planner.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class TreeSpeciesType(str, Enum):
    OAK = "Quercus robur (English Oak - High Leaf Area, High Sequestration)"
    MAPLE = "Acer rubrum (Red Maple - Medium Transpiration, Urban Hardy)"
    PINE = "Pinus sylvestris (Scots Pine - Evergreen Albedo Stability)"
    BIRCH = "Betula pendula (Silver Birch - High Reflectance, Fast Growth)"
    FRUIT_AGROFORESTRY = "Malus domestica (Apple/Agroforestry - High Edible Yield & Canopy)"


class SoilPermeabilityType(str, Enum):
    CLAY_COMPACTED = "Compacted Urban Clay (Low Permeability, High Runoff)"
    LOAMY_HEALTHY = "Aerated Loamy Soil (Moderate Retention & Infiltration)"
    SANDY_POROUS = "Porous Sandy Substrate (High Infiltration, Low Water Stored)"
    BIOSWALE_ENGINEERED = "Engineered Bioswale Soil Matrix (Optimized Rain Absorption)"


@dataclass
class UrbanZoneParameters:
    zone_name: str
    baseline_surface_temp_c: float
    impervious_surface_fraction: float  # 0.0 to 1.0 (asphalt, concrete)
    current_canopy_cover_pct: float     # 0.0 to 100.0%
    target_canopy_cover_pct: float      # 0.0 to 100.0%
    selected_species: TreeSpeciesType
    soil_type: SoilPermeabilityType
    district_area_sq_meters: float
    annual_rainfall_mm: float = 750.0


@dataclass
class CanopyCoolingResult:
    zone_name: str
    surface_temperature_reduction_c: float
    ambient_air_temperature_reduction_c: float
    evapotranspiration_cooling_kwh_per_year: float
    annual_carbon_sequestration_kg_co2: float
    stormwater_runoff_absorbed_cubic_meters: float
    cooling_energy_savings_usd: float
    species_tree_count_recommended: int
    thermal_comfort_improvement_index: str
