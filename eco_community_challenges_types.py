"""
Community Challenges Engine Types & Models
Defines data structures, Enums, dataclasses, and verification logic for Eco-Community Challenges.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, date


class ChallengeCategory(str, Enum):
    ZERO_WASTE = "Zero Waste"
    ENERGY_SAVER = "Energy Saver"
    SUSTAINABLE_MOBILITY = "Sustainable Mobility"
    PLANT_BASED_DIET = "Plant-Based Diet"
    WATER_CONSERVATION = "Water Conservation"
    CIRCULAR_COMMERCE = "Circular Commerce"


class ChallengeDifficulty(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    EPIC = "Epic"


class VerificationType(str, Enum):
    SELF_REPORT = "Self Report"
    METER_READING = "Meter Reading"
    RECEIPT_VERIFICATION = "Receipt Verification"
    COMMUNITY_VOUCH = "Community Vouch"


@dataclass
class ChallengeCriteria:
    target_metric: str
    target_value: float
    unit: str
    verification_type: VerificationType = VerificationType.SELF_REPORT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_metric": self.target_metric,
            "target_value": self.target_value,
            "unit": self.unit,
            "verification_type": self.verification_type.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChallengeCriteria":
        return cls(
            target_metric=data.get("target_metric", "co2_reduction_kg"),
            target_value=float(data.get("target_value", 10.0)),
            unit=data.get("unit", "kg"),
            verification_type=VerificationType(data.get("verification_type", "Self Report")),
        )


@dataclass
class CommunityChallenge:
    id: Optional[int]
    title: str
    description: str
    category: ChallengeCategory
    difficulty: ChallengeDifficulty
    duration_days: int
    co2_impact_kg: float
    xp_reward: int
    criteria: ChallengeCriteria
    created_at: Optional[str] = None
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "duration_days": self.duration_days,
            "co2_impact_kg": self.co2_impact_kg,
            "xp_reward": self.xp_reward,
            "criteria": self.criteria.to_dict(),
            "created_at": self.created_at,
            "is_active": self.is_active,
        }


@dataclass
class UserChallengeEnrollment:
    id: Optional[int]
    user_id: int
    challenge_id: int
    joined_date: str
    target_completion_date: str
    current_progress: float
    target_goal: float
    status: str  # "ACTIVE", "COMPLETED", "FAILED"
    proof_submitted: Optional[str] = None
    completed_at: Optional[str] = None

    def calculate_percentage(self) -> float:
        if self.target_goal <= 0:
            return 100.0
        return min(100.0, round((self.current_progress / self.target_goal) * 100.0, 1))

    def is_expired(self) -> bool:
        if self.status != "ACTIVE":
            return False
        today_str = date.today().isoformat()
        return today_str > self.target_completion_date


@dataclass
class ChallengeAnalyticsSummary:
    total_challenges: int
    active_participants: int
    total_co2_avoided_kg: float
    total_xp_awarded: int
    completion_rate_pct: float
