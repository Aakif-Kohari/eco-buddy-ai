"""Data models and constants for the Eco Impact Comparison Dashboard."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime


class ImpactCategory(Enum):
    """Categories of environmental impact."""
    CARBON = "carbon"
    WATER = "water"
    ENERGY = "energy"
    WASTE = "waste"
    TRANSPORT = "transport"
    FOOD = "food"
    LIFESTYLE = "lifestyle"


class ComparisonPeriod(Enum):
    """Time periods for comparison."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class TrendDirection(Enum):
    """Direction of environmental impact trend."""
    IMPROVING = "improving"
    STABLE = "stable"
    WORSENING = "worsening"


class BadgeLevel(Enum):
    """Achievement badge levels."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


@dataclass
class ImpactRecord:
    """Single impact measurement record."""
    record_id: str
    user_id: str
    timestamp: str
    category: ImpactCategory
    value: float
    unit: str
    baseline: float
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class UserProfile:
    """User profile for comparison."""
    user_id: str
    username: str
    display_name: str
    avatar_url: Optional[str]
    joined_date: str
    total_assessments: int
    eco_score: float
    carbon_saved_kg: float
    water_saved_liters: float
    trees_equivalent: float
    badges: List[str] = field(default_factory=list)
    region: str = "Global"
    diet_type: str = "Vegetarian"
    primary_transport: str = "Car"


@dataclass
class CommunityStats:
    """Aggregate community statistics."""
    total_users: int
    active_users_30d: int
    avg_eco_score: float
    total_carbon_saved_tons: float
    total_water_saved_megaliters: float
    total_trees_equivalent: int
    top_performers: List[UserProfile] = field(default_factory=list)
    regional_averages: Dict[str, float] = field(default_factory=dict)


@dataclass
class ImpactTrend:
    """Trend data for a specific metric over time."""
    category: ImpactCategory
    period: ComparisonPeriod
    data_points: List[Dict[str, float]] = field(default_factory=list)
    direction: TrendDirection = TrendDirection.STABLE
    change_percent: float = 0.0
    best_period: Optional[str] = None
    worst_period: Optional[str] = None


@dataclass
class ComparisonResult:
    """Result of comparing user against community."""
    user_id: str
    category: ImpactCategory
    user_value: float
    community_avg: float
    community_median: float
    percentile: float
    rank: int
    total_participants: int
    is_above_average: bool
    improvement_potential_kg: float


@dataclass
class EcoChallenge:
    """Environmental challenge."""
    challenge_id: str
    title: str
    description: str
    category: ImpactCategory
    duration_days: int
    target_reduction_percent: float
    participants: int
    max_participants: int
    start_date: str
    end_date: str
    is_active: bool
    reward_badge: str


@dataclass
class GoalProgress:
    """Progress toward an environmental goal."""
    goal_id: str
    user_id: str
    title: str
    category: ImpactCategory
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

    @property
    def days_remaining(self) -> int:
        try:
            deadline = datetime.strptime(self.deadline, "%Y-%m-%d")
            now = datetime.now()
            delta = deadline - now
            return max(delta.days, 0)
        except (ValueError, TypeError):
            return 0


# ─── Constants ────────────────────────────────────────────────────────────

EMISSION_FACTORS = {
    "transport": {
        "Car": 0.19,
        "Bus": 0.089,
        "Train": 0.041,
        "Bike": 0.0,
        "Walking": 0.0,
        "Electric Car": 0.053,
        "Motorcycle": 0.103,
    },
    "diet": {
        "Vegan": 1.5,
        "Vegetarian": 2.0,
        "Pescatarian": 2.5,
        "Omnivore": 3.3,
        "Heavy Meat": 4.5,
    },
    "energy": {
        "Global": 0.475,
        "US": 0.386,
        "UK": 0.233,
        "EU": 0.296,
        "India": 0.708,
        "China": 0.555,
    },
}

WATER_FACTORS = {
    "shower_minutes_daily": 8.0,
    "laundry_loads_weekly": 3.0,
    "dishwasher_runs_weekly": 4.0,
    "garden_minutes_daily": 15.0,
    "virtual_water_diet_kg": {
        "Vegan": 1250,
        "Vegetarian": 1750,
        "Omnivore": 3500,
        "Heavy Meat": 5000,
    },
}

WASTE_FACTORS = {
    "recycling_rate_global": 0.174,
    "composting_rate_global": 0.058,
    "food_waste_kg_per_capita_year": 74.0,
    "packaging_kg_per_capita_year": 45.0,
}

ECO_SCORE_WEIGHTS = {
    ImpactCategory.CARBON: 0.30,
    ImpactCategory.WATER: 0.20,
    ImpactCategory.ENERGY: 0.20,
    ImpactCategory.WASTE: 0.15,
    ImpactCategory.TRANSPORT: 0.10,
    ImpactCategory.FOOD: 0.05,
}

BADGE_THRESHOLDS = {
    BadgeLevel.BRONZE: {"eco_score": 40, "carbon_saved": 10},
    BadgeLevel.SILVER: {"eco_score": 55, "carbon_saved": 50},
    BadgeLevel.GOLD: {"eco_score": 70, "carbon_saved": 100},
    BadgeLevel.PLATINUM: {"eco_score": 85, "carbon_saved": 250},
    BadgeLevel.DIAMOND: {"eco_score": 95, "carbon_saved": 500},
}

REGIONAL_BENCHMARKS = {
    "Global": {"avg_carbon_kg_year": 4500, "avg_water_l_day": 3800, "avg_energy_kwh_month": 250},
    "US": {"avg_carbon_kg_year": 5200, "avg_water_l_day": 4000, "avg_energy_kwh_month": 350},
    "UK": {"avg_carbon_kg_year": 3800, "avg_water_l_day": 3500, "avg_energy_kwh_month": 280},
    "EU": {"avg_carbon_kg_year": 4200, "avg_water_l_day": 3600, "avg_energy_kwh_month": 270},
    "India": {"avg_carbon_kg_year": 1900, "avg_water_l_day": 3200, "avg_energy_kwh_month": 120},
}
