"""Data models and constants for Industrial Waste Heat Recovery (WHR) and Organic Rankine Cycle (ORC).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class HeatSourceIndustry(str, Enum):
    CEMENT_KILN = "Cement Kiln Exhaust (320°C, High Particulate)"
    STEEL_REHEATING = "Steel Reheating Furnace Flue Gas (480°C)"
    GLASS_MELTING = "Glass Furnace Exhaust (420°C)"
    CHEMICAL_REACTION = "Exothermic Chemical Refining (180°C)"
    DIESEL_GENSET = "Heavy Diesel/Gas Engine Exhaust (360°C)"


class WorkingFluid(str, Enum):
    R245FA = "R245fa (Hydrofluorocarbon - Standard Low Temp ORC)"
    CYCLOPENTANE = "Cyclopentane (Hydrocarbon - High Efficiency Medium Temp)"
    SOLKATHERM_SES36 = "Solkatherm SES36 (Fluorinated Ether - Stable to 250°C)"
    WATER_STEAM = "Direct Steam (Supercritical / Subcritical Rankine)"


class RecoveryApplication(str, Enum):
    ORC_ELECTRICITY = "Organic Rankine Cycle (ORC) Power Generation"
    DISTRICT_HEATING = "Direct Heat Exchanger for District Heating / Hot Water"
    ABSORPTION_CHILLING = "Thermal Absorption Chiller (Cooling Co-generation)"
    STEAM_INJECTION = "Heat Recovery Steam Generator (HRSG)"


@dataclass
class IndustrialPlantParameters:
    plant_name: str
    industry_type: HeatSourceIndustry
    exhaust_gas_temp_c: float
    exhaust_mass_flow_kg_s: float
    working_fluid: WorkingFluid
    application: RecoveryApplication
    annual_operating_hours: float = 7500.0
    ambient_sink_temp_c: float = 25.0
    pinch_point_delta_t_c: float = 12.0
    electricity_export_tariff_usd_kwh: float = 0.12
    grid_emission_intensity_kg_co2_kwh: float = 0.48


@dataclass
class HeatPinchPoint:
    stream_name: str
    inlet_temp_c: float
    outlet_temp_c: float
    heat_transferred_kw: float


@dataclass
class WasteHeatRecoveryResult:
    plant_name: str
    recoverable_thermal_heat_kw: float
    gross_electrical_power_kw: float
    net_thermal_efficiency_pct: float
    annual_electricity_generated_mwh: float
    annual_cost_savings_usd: float
    annual_co2_avoided_tons: float
    exergy_efficiency_pct: float
    estimated_turnkey_capex_usd: float
    simple_payback_years: float
    pinch_points: List[HeatPinchPoint] = field(default_factory=list)
    cashflow_10yr: List[Dict[str, float]] = field(default_factory=list)
