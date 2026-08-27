"""Data models and constants for the Energy Monitoring Dashboard."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime


class EnergySource(Enum):
    """Sources of energy consumption."""
    SOLAR = "solar"
    WIND = "wind"
    GRID = "grid"
    BATTERY = "battery"
    GAS = "gas"
    OIL = "oil"
    HYDRO = "hydro"


class ApplianceCategory(Enum):
    """Categories of household appliances."""
    HEATING = "heating"
    COOLING = "cooling"
    LIGHTING = "lighting"
    KITCHEN = "kitchen"
    LAUNDRY = "laundry"
    ENTERTAINMENT = "entertainment"
    OFFICE = "office"
    WATER_HEATER = "water_heater"
    OTHER = "other"


class AlertType(Enum):
    """Types of energy alerts."""
    HIGH_CONSUMPTION = "high_consumption"
    PEAK_DEMAND = "peak_demand"
    ANOMALY = "anomaly"
    SAVINGS_OPPORTUNITY = "savings_opportunity"
    DEVICE_OFFLINE = "device_offline"
    BATTERY_LOW = "battery_low"


class ComparisonPeriod(Enum):
    """Time periods for comparison."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class EnergyGoalType(Enum):
    """Types of energy goals."""
    REDUCE_CONSUMPTION = "reduce_consumption"
    INCREASE_SUSTAINABLE = "increase_sustainable"
    REDUCE_COST = "reduce_cost"
    NET_ZERO = "net_zero"


@dataclass
class EnergyReading:
    """A single energy consumption reading."""
    reading_id: str
    timestamp: str
    consumption_kwh: float
    source: EnergySource
    cost_usd: float
    carbon_kg: float
    appliance_category: ApplianceCategory
    device_name: str
    is_peak: bool = False


@dataclass
class Appliance:
    """A monitored household appliance."""
    appliance_id: str
    name: str
    category: ApplianceCategory
    rated_power_watts: float
    avg_daily_kwh: float
    monthly_cost_usd: float
    efficiency_rating: str  # A++ to G
    is_active: bool = True
    last_used: str = ""
    usage_hours_daily: float = 0.0


@dataclass
class EnergyDevice:
    """A smart energy monitoring device."""
    device_id: str
    name: str
    location: str
    is_online: bool
    current_power_watts: float
    today_kwh: float
    firmware_version: str
    last_seen: str


@dataclass
class EnergyAlert:
    """An energy consumption alert."""
    alert_id: str
    alert_type: AlertType
    title: str
    message: str
    severity: str  # low, medium, high, critical
    timestamp: str
    is_read: bool = False
    is_resolved: bool = False
    device_name: str = ""
    recommended_action: str = ""


@dataclass
class EnergyGoal:
    """An energy reduction goal."""
    goal_id: str
    goal_type: EnergyGoalType
    title: str
    target_value: float
    current_value: float
    unit: str
    deadline: str
    created_at: str
    is_completed: bool

    @property
    def progress_percent(self) -> float:
        if self.target_value == 0:
            return 0.0
        return min((self.current_value / self.target_value) * 100, 100.0)


@dataclass
class EnergyBill:
    """A monthly energy bill record."""
    bill_id: str
    month: str
    total_kwh: float
    total_cost_usd: float
    peak_kwh: float
    off_peak_kwh: float
    renewable_kwh: float
    carbon_kg: float
    days: int
    avg_daily_kwh: float

    @property
    def renewable_percent(self) -> float:
        if self.total_kwh == 0:
            return 0.0
        return (self.renewable_kwh / self.total_kwh) * 100


@dataclass
class EnergyInsight:
    """An AI-generated energy insight."""
    insight_id: str
    title: str
    description: str
    category: str
    potential_savings_kwh: float
    potential_savings_usd: float
    potential_carbon_kg: float
    confidence: float
    recommended_actions: List[str]


@dataclass
class EnergyFilterOptions:
    """Filter options for the dashboard."""
    date_from: str
    date_to: str
    category: ApplianceCategory | None
    source: EnergySource | None
    device: str
    sort_by: str
    sort_order: str


@dataclass
class EnergyStats:
    """Aggregate energy statistics."""
    total_kwh_month: float
    total_cost_month: float
    total_carbon_month: float
    avg_daily_kwh: float
    peak_kwh_today: float
    renewable_percent: float
    cost_per_kwh: float
    comparison_last_month_percent: float
    total_devices: int
    active_devices: int
    alerts_count: int
    savings_this_month_usd: float
    monthly_trend: List[Dict[str, float]]
    category_breakdown: Dict[str, float]
    source_breakdown: Dict[str, float]
    hourly_pattern: List[Dict[str, float]]


GRID_EMISSION_FACTOR = 0.475  # kg CO2 per kWh
SOLAR_EMISSION_FACTOR = 0.02
WIND_EMISSION_FACTOR = 0.01
GAS_EMISSION_FACTOR = 0.18
OIL_EMISSION_FACTOR = 0.27

APPLIANCE_ICONS = {
    ApplianceCategory.HEATING: "🔥",
    ApplianceCategory.COOLING: "❄️",
    ApplianceCategory.LIGHTING: "💡",
    ApplianceCategory.KITCHEN: "🍳",
    ApplianceCategory.LAUNDRY: "👕",
    ApplianceCategory.ENTERTAINMENT: "📺",
    ApplianceCategory.OFFICE: "💻",
    ApplianceCategory.WATER_HEATER: "🚿",
    ApplianceCategory.OTHER: "🔌",
}

APPLIANCE_COLORS = {
    ApplianceCategory.HEATING: "#ef4444",
    ApplianceCategory.COOLING: "#0ea5e9",
    ApplianceCategory.LIGHTING: "#f59e0b",
    ApplianceCategory.KITCHEN: "#f97316",
    ApplianceCategory.LAUNDRY: "#8b5cf6",
    ApplianceCategory.ENTERTAINMENT: "#ec4899",
    ApplianceCategory.OFFICE: "#6366f1",
    ApplianceCategory.WATER_HEATER: "#14b8a6",
    ApplianceCategory.OTHER: "#94a3b8",
}

SOURCE_COLORS = {
    EnergySource.SOLAR: "#f59e0b",
    EnergySource.WIND: "#0ea5e9",
    EnergySource.GRID: "#6b7280",
    EnergySource.BATTERY: "#22c55e",
    EnergySource.GAS: "#ef4444",
    EnergySource.OIL: "#92400e",
    EnergySource.HYDRO: "#06b6d4",
}

EFFICIENCY_COLORS = {
    "A++": "#22c55e", "A+": "#22c55e", "A": "#4ade80",
    "B": "#f59e0b", "C": "#f97316", "D": "#ef4444",
    "E": "#dc2626", "F": "#b91c1c", "G": "#7f1d1d",
}
