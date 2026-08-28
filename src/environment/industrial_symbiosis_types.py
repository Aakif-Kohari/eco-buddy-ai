"""Domain models and dataclasses for Industrial Symbiosis and Waste Heat Recovery Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class HeatSourceStreamType(str, Enum):
    FLUE_GAS_HIGH_TEMP = "High-Temperature Furnace Flue Gas (350°C - 650°C)"
    BOILER_BLOWDOWN = "Boiler Blowdown & Condensate Liquid (100°C - 180°C)"
    COMPRESSOR_COOLING_AIR = "Air Compressor & Chiller Reject Air (50°C - 90°C)"
    INDUSTRIAL_EFFLUENT = "Thermal Wastewater Effluent (40°C - 75°C)"
    DATA_CENTER_EXHAUST = "Data Center Hot Aisle Liquid/Air (35°C - 55°C)"


class HeatRecoveryTechnology(str, Enum):
    ORGANIC_RANKINE_CYCLE = "Organic Rankine Cycle (ORC Power Generation)"
    PLATE_HEAT_EXCHANGER = "Plate & Frame Heat Exchanger (District Heating)"
    ABSORPTION_CHILLER = "Absorption Chiller (Thermal Waste-to-Cooling)"
    HEAT_PIPE_ECONOMIZER = "Heat Pipe Waste Heat Economizer (Pre-heating)"


@dataclass
class IndustrialStreamParameters:
    facility_name: str
    stream_type: HeatSourceStreamType
    mass_flow_rate_kg_s: float
    inlet_temperature_c: float
    target_outlet_temperature_c: float
    recovery_tech: HeatRecoveryTechnology
    annual_operating_hours: float = 7500.0
    avoided_fuel_carbon_intensity_kg_co2_kwh: float = 0.202  # Natural Gas baseline


@dataclass
class HeatRecoveryResult:
    facility_name: str
    thermal_power_available_kw: float
    thermal_power_recovered_kw: float
    annual_energy_recovered_mwh: float
    annual_avoided_emissions_metric_tons: float
    annual_cost_savings_usd: float
    estimated_payback_years: float
    system_thermal_efficiency_pct: float
