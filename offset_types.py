"""Data models and constants for the Carbon Offset Marketplace."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime


class OffsetCategory(Enum):
    """Categories of carbon offset projects."""
    FORESTRY = "forestry"
    RENEWABLE_ENERGY = "renewable_energy"
    COOKSTOVE = "cookstove"
    METHANE_CAPTURE = "methane_capture"
    WATER过滤 = "water_filtration"
    OCEAN = "ocean"
    AGRICULTURE = "agriculture"
    DIRECT_AIR_CAPTURE = "direct_air_capture"


class ProjectStatus(Enum):
    """Status of an offset project."""
    ACTIVE = "active"
    FUNDED = "funded"
    COMPLETED = "completed"
    UPCOMING = "upcoming"
    PAUSED = "paused"


class VerificationStandard(Enum):
    """Carbon offset verification standards."""
    GOLD_STANDARD = "Gold Standard"
    VCS = "Verified Carbon Standard"
    CARBON_TRUST = "Carbon Trust"
    ACR = "American Carbon Registry"
    Climate_ACTION = "Climate Action Reserve"
    Plan_VIVO = "Plan Vivo"


class TransactionStatus(Enum):
    """Status of a purchase transaction."""
    PENDING = "pending"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    FAILED = "failed"


@dataclass
class OffsetProject:
    """A carbon offset project."""
    project_id: str
    name: str
    description: str
    long_description: str
    category: OffsetCategory
    status: ProjectStatus
    location: str
    country: str
    continent: str
    verification: VerificationStandard
    price_per_ton: float
    total_tons_available: float
    tons_sold: float
    total_funding_usd: float
    funding_goal_usd: float
    annual_reduction_tons: float
    start_date: str
    end_date: str
    partner_organization: str
    images: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    sdg_goals: List[int] = field(default_factory=list)
    rating: float = 0.0
    review_count: int = 0

    @property
    def tons_remaining(self) -> float:
        return max(self.total_tons_available - self.tons_sold, 0)

    @property
    def funding_percent(self) -> float:
        if self.funding_goal_usd == 0:
            return 0.0
        return min((self.total_funding_usd / self.funding_goal_usd) * 100, 100.0)

    @property
    def is_sold_out(self) -> bool:
        return self.tons_remaining <= 0


@dataclass
class OffsetPurchase:
    """A carbon offset purchase record."""
    purchase_id: str
    user_id: str
    project_id: str
    project_name: str
    tons_purchased: float
    price_per_ton: float
    total_cost: float
    transaction_status: TransactionStatus
    purchase_date: str
    certificate_id: str
    notes: str = ""

    @property
    def carbon_offset_kg(self) -> float:
        return self.tons_purchased * 1000


@dataclass
class UserOffsetPortfolio:
    """User's carbon offset portfolio."""
    user_id: str
    total_tons_offset: float
    total_spent_usd: float
    projects_supported: int
    purchases: List[OffsetPurchase] = field(default_factory=list)
    certificates: List[str] = field(default_factory=list)

    @property
    def avg_price_per_ton(self) -> float:
        if self.total_tons_offset == 0:
            return 0.0
        return self.total_spent_usd / self.total_tons_offset


@dataclass
class OffsetImpact:
    """Impact metrics from offset purchases."""
    trees_planted: int
    homes_powered: int
    cars_removed: int
    flights_offset: int
    swimming_pools_saved: int
    co2_saved_tons: float
    equivalent_years_driving: float


@dataclass
class OffsetFilterOptions:
    """Filter options for the marketplace."""
    search: str
    category: OffsetCategory | None
    continent: str
    min_price: float
    max_price: float
    verification: VerificationStandard | None
    status: ProjectStatus | None
    sort_by: str
    sort_order: str
    min_rating: float
    show_sold_out: bool


@dataclass
class MarketplaceStats:
    """Aggregate marketplace statistics."""
    total_projects: int
    active_projects: int
    total_tons_sold: float
    total_funding_usd: float
    total_users: int
    avg_price_per_ton: float
    top_categories: Dict[str, int]
    top_continents: Dict[str, int]
    monthly_sales: List[Dict[str, float]]


SDG_GOAL_LABELS = {
    1: "No Poverty",
    2: "Zero Hunger",
    3: "Good Health",
    4: "Quality Education",
    5: "Gender Equality",
    6: "Clean Water",
    7: "Affordable Energy",
    8: "Decent Work",
    9: "Industry Innovation",
    10: "Reduced Inequalities",
    11: "Sustainable Cities",
    12: "Responsible Consumption",
    13: "Climate Action",
    14: "Life Below Water",
    15: "Life on Land",
    16: "Peace Justice",
    17: "Partnerships",
}

CATEGORY_ICONS = {
    OffsetCategory.FORESTRY: "🌲",
    OffsetCategory.RENEWABLE_ENERGY: "⚡",
    OffsetCategory.COOKSTOVE: "🍳",
    OffsetCategory.METHANE_CAPTURE: "🏭",
    OffsetCategory.WATER过滤: "💧",
    OffsetCategory.OCEAN: "🌊",
    OffsetCategory.AGRICULTURE: "🌾",
    OffsetCategory.DIRECT_AIR_CAPTURE: "🌬️",
}

CATEGORY_COLORS = {
    OffsetCategory.FORESTRY: "#22c55e",
    OffsetCategory.RENEWABLE_ENERGY: "#f59e0b",
    OffsetCategory.COOKSTOVE: "#ef4444",
    OffsetCategory.METHANE_CAPTURE: "#8b5cf6",
    OffsetCategory.WATER过滤: "#0ea5e9",
    OffsetCategory.OCEAN: "#06b6d4",
    OffsetCategory.AGRICULTURE: "#84cc16",
    OffsetCategory.DIRECT_AIR_CAPTURE: "#6366f1",
}

CONTINENT_OPTIONS = ["All", "Africa", "Asia", "Europe", "North America", "South America", "Oceania"]
