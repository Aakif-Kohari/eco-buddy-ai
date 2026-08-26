"""Data models and constants for Soil Organic Carbon (SOC) and Agroecology Simulation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class SoilTextureType(str, Enum):
    CLAY_LOAM = "Clay Loam (High Retention, 28% Clay)"
    SILT_LOAM = "Silt Loam (Moderate Retention, 18% Clay)"
    SANDY_LOAM = "Sandy Loam (Fast Mineralization, 8% Clay)"
    PEAT_ORGANIC = "Peat Organic Muck (> 40% Organic Matter)"


class TillagePractice(str, Enum):
    CONVENTIONAL_INTENSIVE = "Conventional Deep Inversion Tillage (High Soil Carbon Oxidation)"
    REDUCED_MINIMUM_TILL = "Reduced / Minimum Conservation Tillage (Moderate Disturbance)"
    NO_TILL = "Continuous Zero Tillage (Direct Drill Seeding)"


class CoverCropStrategy(str, Enum):
    NONE_FALLOW = "Winter Bare Fallow"
    LEGUME_CRIMSON_CLOVER = "Legume Cover (Crimson Clover / Vetch - Nitrogen Fixing)"
    GRASS_RYE = "Cereal Rye / Sorghum-Sudangrass (High Biomass Carbon)"
    MULTI_SPECIES_POLY = "Multi-Species Diverse Cocktail (7+ Species Poly-culture)"


@dataclass
class FarmFieldParameters:
    field_name: str
    area_hectares: float
    baseline_soc_pct: float  # Topsoil SOC (e.g. 1.8%)
    bulk_density_g_cm3: float  # e.g. 1.35 g/cm3
    sampling_depth_cm: float  # e.g. 30 cm
    soil_texture: SoilTextureType
    tillage_practice: TillagePractice
    cover_crop_strategy: CoverCropStrategy
    compost_addition_dry_tons_per_ha_yr: float
    synthetic_nitrogen_kg_per_ha_yr: float
    carbon_credit_price_usd_ton: float = 30.0


@dataclass
class AnnualSoilCarbonPoint:
    year: int
    soc_stock_tons_c_ha: float
    net_annual_sequestration_tons_co2e_ha: float
    n2o_fertilizer_emissions_tons_co2e_ha: float
    net_ghg_balance_tons_co2e_ha: float
    cumulative_carbon_credits_usd: float


@dataclass
class AgroecologySimulationResult:
    field_name: str
    area_hectares: float
    initial_soc_stock_tons_c_ha: float
    final_soc_stock_tons_c_ha_yr10: float
    net_10yr_carbon_sequestered_tons_co2e: float
    annual_sequestration_rate_tons_co2e_per_ha: float
    synthetic_n_fertilizer_offset_kg_yr: float
    total_carbon_credit_revenue_10yr_usd: float
    soil_water_holding_capacity_uplift_pct: float
    trajectory: List[AnnualSoilCarbonPoint] = field(default_factory=list)
