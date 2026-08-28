"""Domain models and dataclasses for Bioclimatic Passive Cooling & Thermal Comfort Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class ThermalMassType(str, Enum):
    RAMMED_EARTH_ADOBE = "Rammed Earth / Adobe (High Heat Capacity, 8-10hr Phase Lag)"
    STONE_MASONRY = "Dense Stone / Heavy Concrete Masonry (Moderate Phase Lag)"
    LIGHTWEIGHT_TIMBER = "Lightweight Timber & Drywall (Low Heat Storage Capacity)"
    PHASE_CHANGE_DRYWALL = "Bio-Phase Change Material (PCM Drywall, Latent Heat Buffering)"


class GlazingOrientation(str, Enum):
    NORTH_OPTIMIZED = "North-Facing Daylighting (Low Direct Solar Radiation Gain)"
    SOUTH_SOLAR_CONTROL = "South-Facing Overhangs (Summer Shading, Winter Solar Capture)"
    EAST_WEST_EXPOSED = "East-West Exposed (High Morning/Evening Heat Flux)"


@dataclass
class BuildingBioclimaticInputs:
    building_name: str
    floor_area_sq_meters: float
    ceiling_height_meters: float
    window_to_wall_ratio: float  # e.g., 0.25 (25%)
    thermal_mass: ThermalMassType
    glazing_orientation: GlazingOrientation
    outdoor_day_peak_temp_c: float
    outdoor_night_min_temp_c: float
    relative_humidity_pct: float = 50.0
    air_speed_m_s: float = 0.2


@dataclass
class BioclimaticCoolingResult:
    building_name: str
    indoor_peak_temperature_c: float
    passive_cooling_temperature_drop_c: float
    fanger_pmv_index: float
    predicted_percentage_dissatisfied_ppd: float
    natural_ventilation_airflow_rate_m3_hr: float
    avoided_cooling_energy_kwh_per_season: float
    annual_cost_savings_usd: float
    avoided_co2_kg_per_season: float
    comfort_category_rating: str
