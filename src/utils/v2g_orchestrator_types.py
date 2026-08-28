"""Data models and type definitions for Vehicle-to-Grid (V2G) Bi-directional Orchestrator.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class BatteryChemistry(str, Enum):
    LFP = "Lithium Iron Phosphate (LFP) - 4,000+ Cycles, Low Degradation"
    NMC_811 = "Nickel Manganese Cobalt (NMC 811) - High Density, Moderate Fade"
    NCA = "Nickel Cobalt Aluminum (NCA) - High Energy, Standard Degradation"
    SOLID_STATE = "Solid State Electrolyte - Next-Gen 6,000+ Cycles"


class ChargingTariffScheme(str, Enum):
    TIME_OF_USE_AGGRESSIVE = "Aggressive Dynamic TOU ($0.08 off-peak / $0.45 peak)"
    TIME_OF_USE_MODERATE = "Standard 2-Tier TOU ($0.12 off-peak / $0.32 peak)"
    FIXED_FLAT = "Flat Commercial Tariff ($0.18 / kWh flat)"


class GridServiceMode(str, Enum):
    ARBITRAGE_ONLY = "Price Arbitrage Only (Charge low, discharge peak)"
    SOLAR_SELF_CONSUMPTION = "Solar Co-location & Maximum Self-Consumption"
    PEAK_DEMAND_SHAVING = "Facility Peak Shaving & Capacity Defense"
    FREQUENCY_REGULATION = "Fast Frequency Response (FFR) & Grid Support"


@dataclass
class FleetVehicleConfig:
    vehicle_id: str
    battery_capacity_kwh: float
    chemistry: BatteryChemistry
    max_charge_power_kw: float
    max_discharge_power_kw: float
    round_trip_efficiency_pct: float
    min_allowable_soc_pct: float = 20.0
    target_departure_soc_pct: float = 80.0
    arrival_hour: int = 18
    departure_hour: int = 7
    daily_commute_kwh: float = 14.0


@dataclass
class V2GHourlyDispatch:
    hour: int
    tariff_price_usd_kwh: float
    grid_carbon_intensity_g_kwh: float
    solar_generation_kw: float
    fleet_charging_kw: float
    fleet_discharging_kw: float
    net_grid_exchange_kw: float
    average_fleet_soc_pct: float
    cumulative_cashflow_usd: float


@dataclass
class V2GOrchestrationResult:
    fleet_size: int
    total_fleet_capacity_kwh: float
    annual_grid_revenue_usd: float
    annual_charging_cost_usd: float
    net_annual_arbitrage_profit_usd: float
    annual_co2_avoided_tons: float
    annual_battery_degradation_pct: float
    estimated_battery_cycle_life_years: float
    solar_self_consumption_pct: float
    hourly_schedule: List[V2GHourlyDispatch] = field(default_factory=list)
