"""Data models and constants for the Green Transportation Planner."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime


class TransportMode(Enum):
    """Transportation modes."""
    WALKING = "walking"
    CYCLING = "cycling"
    BUS = "bus"
    TRAIN = "train"
    METRO = "metro"
    CAR = "car"
    ELECTRIC_CAR = "electric_car"
    CARPOOL = "carpool"
    SCOOTER = "scooter"
    FERRY = "ferry"


class RoutePreference(Enum):
    """Route optimization preferences."""
    FASTEST = "fastest"
    SHORTEST = "shortest"
    GREENEST = "greenest"
    CHEAPEST = "cheapest"
    LEAST_EFFORT = "least_effort"


class TripCategory(Enum):
    """Categories of trips."""
    COMMUTE = "commute"
    ERRANDS = "errands"
    RECREATION = "recreation"
    BUSINESS = "business"
    TRAVEL = "travel"
    SCHOOL = "school"


class VehicleType(Enum):
    """Types of personal vehicles."""
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    PLUG_IN_HYBRID = "plug_in_hybrid"
    ELECTRIC = "electric"
    NONE = "none"


@dataclass
class TransportModeInfo:
    """Information about a transportation mode."""
    mode: TransportMode
    name: str
    icon: str
    color: str
    emission_factor_kg_per_km: float
    avg_speed_kmh: float
    cost_per_km: float
    calories_per_km: float
    comfort_rating: int  # 1-5
    reliability_rating: int  # 1-5
    is_active: bool = True


@dataclass
class Route:
    """A transportation route between two points."""
    route_id: str
    origin: str
    destination: str
    distance_km: float
    duration_minutes: float
    mode: TransportMode
    emission_kg: float
    cost_usd: float
    calories_burned: float
    steps: List[Dict[str, str]]
    preference_score: float
    is_recommended: bool = False


@dataclass
class TripPlan:
    """A planned trip with multiple route options."""
    plan_id: str
    origin: str
    destination: str
    date: str
    time: str
    category: TripCategory
    routes: List[Route]
    selected_route_id: Optional[str]
    notes: str = ""


@dataclass
class TripLog:
    """A logged completed trip."""
    log_id: str
    user_id: str
    origin: str
    destination: str
    distance_km: float
    mode: TransportMode
    duration_minutes: float
    emission_kg: float
    cost_usd: float
    date: str
    category: TripCategory
    notes: str = ""


@dataclass
class Vehicle:
    """A personal vehicle."""
    vehicle_id: str
    name: str
    vehicle_type: VehicleType
    fuel_efficiency_km_per_l: float
    emission_factor_kg_per_km: float
    year: int
    make: str
    model: str
    is_default: bool = False


@dataclass
class CommuteStats:
    """Statistics for commute patterns."""
    avg_daily_distance_km: float
    avg_daily_emission_kg: float
    avg_daily_cost_usd: float
    total_monthly_trips: int
    most_used_mode: TransportMode
    greenest_day: str
    worst_day: str
    monthly_savings_usd: float
    monthly_co2_saved_kg: float


@dataclass
class TransportFilterOptions:
    """Filter options for trip history."""
    category: TripCategory | None
    mode: TransportMode | None
    date_from: str
    date_to: str
    min_distance: float
    max_distance: float
    sort_by: str
    sort_order: str


@dataclass
class TransportStats:
    """Aggregate transport statistics."""
    total_trips: int
    total_distance_km: float
    total_emission_kg: float
    total_cost_usd: float
    total_calories: float
    avg_emission_per_trip: float
    greenest_mode: TransportMode
    most_used_mode: TransportMode
    monthly_trend: List[Dict[str, float]]
    mode_distribution: Dict[str, int]
    co2_avoided_kg: float
    trees_equivalent: int


@dataclass
class EmissionComparison:
    """Comparison of emissions across transport modes."""
    mode: TransportMode
    mode_name: str
    emission_kg: float
    time_minutes: float
    cost_usd: float
    calories: float
    is_greenest: bool
    savings_vs_car_kg: float


EMISSION_FACTORS = {
    TransportMode.WALKING: 0.0,
    TransportMode.CYCLING: 0.0,
    TransportMode.BUS: 0.089,
    TransportMode.TRAIN: 0.041,
    TransportMode.METRO: 0.035,
    TransportMode.CAR: 0.19,
    TransportMode.ELECTRIC_CAR: 0.053,
    TransportMode.CARPOOL: 0.095,
    TransportMode.SCOOTER: 0.065,
    TransportMode.FERRY: 0.12,
}

AVG_SPEEDS = {
    TransportMode.WALKING: 5.0,
    TransportMode.CYCLING: 16.0,
    TransportMode.BUS: 20.0,
    TransportMode.TRAIN: 80.0,
    TransportMode.METRO: 35.0,
    TransportMode.CAR: 30.0,
    TransportMode.ELECTRIC_CAR: 30.0,
    TransportMode.CARPOOL: 30.0,
    TransportMode.SCOOTER: 25.0,
    TransportMode.FERRY: 22.0,
}

COST_PER_KM = {
    TransportMode.WALKING: 0.0,
    TransportMode.CYCLING: 0.01,
    TransportMode.BUS: 0.15,
    TransportMode.TRAIN: 0.12,
    TransportMode.METRO: 0.10,
    TransportMode.CAR: 0.25,
    TransportMode.ELECTRIC_CAR: 0.08,
    TransportMode.CARPOOL: 0.12,
    TransportMode.SCOOTER: 0.18,
    TransportMode.FERRY: 0.20,
}

CALORIES_PER_KM = {
    TransportMode.WALKING: 60.0,
    TransportMode.CYCLING: 35.0,
    TransportMode.BUS: 5.0,
    TransportMode.TRAIN: 5.0,
    TransportMode.METRO: 8.0,
    TransportMode.CAR: 3.0,
    TransportMode.ELECTRIC_CAR: 3.0,
    TransportMode.CARPOOL: 3.0,
    TransportMode.SCOOTER: 15.0,
    TransportMode.FERRY: 5.0,
}

MODE_ICONS = {
    TransportMode.WALKING: "🚶",
    TransportMode.CYCLING: "🚲",
    TransportMode.BUS: "🚌",
    TransportMode.TRAIN: "🚆",
    TransportMode.METRO: "🚇",
    TransportMode.CAR: "🚗",
    TransportMode.ELECTRIC_CAR: "⚡",
    TransportMode.CARPOOL: "👥",
    TransportMode.SCOOTER: "🛴",
    TransportMode.FERRY: "⛴️",
}

MODE_COLORS = {
    TransportMode.WALKING: "#22c55e",
    TransportMode.CYCLING: "#16a34a",
    TransportMode.BUS: "#f59e0b",
    TransportMode.TRAIN: "#0ea5e9",
    TransportMode.METRO: "#8b5cf6",
    TransportMode.CAR: "#ef4444",
    TransportMode.ELECTRIC_CAR: "#06b6d4",
    TransportMode.CARPOOL: "#f97316",
    TransportMode.SCOOTER: "#ec4899",
    TransportMode.FERRY: "#6366f1",
}
