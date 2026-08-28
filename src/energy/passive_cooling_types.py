"""Data models and constants for Passive Cooling and Thermal Comfort Simulation.

Based on ASHRAE 55 Adaptive Comfort Standard, ISO 7730 PMV/PPD,
and Building Thermal Physics calculations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ClimateZone(str, Enum):
    HOT_ARID = "Hot & Arid (BWh/BWk)"
    HOT_HUMID = "Hot & Humid (Cfa/Af)"
    TEMPERATE = "Temperate (Cfb/Csb)"
    CONTINENTAL = "Continental / Cold (Dfb/Dfa)"
    MEDITERRANEAN = "Mediterranean (Csa/Csb)"


class InsulationLevel(str, Enum):
    UNINSULATED = "Uninsulated / Single Glaze (U > 4.5 W/m²K)"
    STANDARD = "Standard Code Compliant (U ~ 1.8 - 2.5 W/m²K)"
    HIGH_PERFORMANCE = "High-Performance Double Glaze (U ~ 1.1 - 1.4 W/m²K)"
    PASSIVE_HOUSE = "Passivhaus Triple Glaze (U < 0.8 W/m²K)"


class ShadingStrategy(str, Enum):
    NONE = "None / Direct Insolation"
    OVERHANG = "Exterior Fixed Overhangs (40% solar cut)"
    LOUVERS = "Automated Dynamic Louvers (75% solar cut)"
    EXTERIOR_VEGETATION = "Bioshading & Trellis Vines (60% solar cut)"
    LOW_E_SOLAR_FILM = "Reflective Low-E Film (50% solar cut)"


class VentilationMode(str, Enum):
    SEALED_AC = "Sealed Envelope with Conventional HVAC"
    NIGHT_PURGE = "Night Purge Flush Ventilation"
    CROSS_VENTILATION = "Wind-Driven Cross Ventilation (Diurnal)"
    THERMAL_CHIMNEY = "Solar Thermal Chimney / Stack Effect"


@dataclass
class BuildingParameters:
    building_name: str
    floor_area_m2: float
    ceiling_height_m: float
    window_to_wall_ratio: float
    climate_zone: ClimateZone
    insulation_level: InsulationLevel
    shading_strategy: ShadingStrategy
    ventilation_mode: VentilationMode
    occupant_count: int
    internal_heat_gain_w_per_m2: float = 12.0
    thermal_mass_capacity_kj_m2_k: float = 180.0  # concrete/masonry thermal inertia
    air_changes_per_hour: float = 1.5
    electricity_cost_kwh: float = 0.18
    grid_emission_factor_kg_kwh: float = 0.42


@dataclass
class HourlyComfortPoint:
    hour: int
    outdoor_temp_c: float
    outdoor_humidity_pct: float
    solar_radiation_w_m2: float
    indoor_temp_unconditioned_c: float
    indoor_temp_passive_c: float
    predicted_mean_vote_pmv: float
    predicted_percentage_dissatisfied_ppd: float
    cooling_load_saved_kwh: float


@dataclass
class PassiveCoolingSimulationResult:
    building_name: str
    annual_cooling_energy_baseline_kwh: float
    annual_cooling_energy_passive_kwh: float
    annual_energy_saved_kwh: float
    energy_savings_percentage: float
    annual_cost_savings_usd: float
    annual_co2_abatement_kg: float
    peak_indoor_temp_reduction_c: float
    hours_in_comfort_zone_unconditioned: int
    hours_in_comfort_zone_passive: int
    thermal_resilience_hours_during_heatwave: int
    estimated_retrofit_capex_usd: float
    simple_payback_years: float
    hourly_profiles: List[HourlyComfortPoint] = field(default_factory=list)
    strategy_breakdown_pct: Dict[str, float] = field(default_factory=dict)
