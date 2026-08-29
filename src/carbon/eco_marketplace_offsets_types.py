"""
Eco-Marketplace & Verified Carbon Offsets Data Types
Dataclasses, Enums, and structures for verified carbon offset projects, purchase transactions, and user portfolio accounting.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class OffsetProjectType(str, Enum):
    REFORESTATION = "Reforestation & Afforestation"
    RENEWABLE_ENERGY = "Renewable Energy"
    METHANE_CAPTURE = "Methane Capture"
    OCEAN_BLUE_CARBON = "Ocean & Blue Carbon"
    DIRECT_AIR_CAPTURE = "Direct Air Capture (DAC)"


class OffsetCertificationStandard(str, Enum):
    GOLD_STANDARD = "Gold Standard"
    VERRA_VCS = "Verra VCS"
    CLIMATE_ACTION_RESERVE = "Climate Action Reserve"
    AMERICAN_CARBON_REGISTRY = "American Carbon Registry"


@dataclass
class CarbonOffsetProject:
    id: Optional[int]
    title: str
    description: str
    project_type: OffsetProjectType
    certification_standard: OffsetCertificationStandard
    location: str
    price_per_tonne_usd: float
    total_available_tonnes: float
    permanence_years: int
    sdg_goals_supported: List[int]
    rating_stars: float = 4.8
    is_verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "project_type": self.project_type.value,
            "certification_standard": self.certification_standard.value,
            "location": self.location,
            "price_per_tonne_usd": self.price_per_tonne_usd,
            "total_available_tonnes": self.total_available_tonnes,
            "permanence_years": self.permanence_years,
            "sdg_goals_supported": self.sdg_goals_supported,
            "rating_stars": self.rating_stars,
            "is_verified": self.is_verified,
        }


@dataclass
class OffsetPurchaseTransaction:
    id: Optional[int]
    user_id: int
    project_id: int
    tonnes_purchased: float
    total_cost_usd: float
    certificate_id: str
    purchased_at: Optional[str] = None


@dataclass
class UserOffsetPortfolioSummary:
    total_tonnes_retired: float
    total_spent_usd: float
    total_certificates: int
    diversification_score: float
    top_project_type: str
