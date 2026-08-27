"""
Eco-Habit Streak Tracker & Gamification Types
Dataclasses, Enums, and structures for habit tracking, frequency, streak history, and reward triggers.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class HabitCategory(str, Enum):
    TRANSPORT = "Transport"
    ENERGY = "Energy"
    FOOD = "Food"
    WASTE = "Waste"
    WATER = "Water"
    MINDFULNESS = "Mindfulness"


class HabitFrequency(str, Enum):
    DAILY = "Daily"
    WEEKLY = "Weekly"
    WEEKDAYS = "Weekdays"


@dataclass
class EcoHabit:
    id: Optional[int]
    user_id: int
    title: str
    description: str
    category: HabitCategory
    frequency: HabitFrequency
    target_value: float
    unit: str
    co2_saved_per_unit: float
    xp_per_completion: int
    created_at: Optional[str] = None
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "frequency": self.frequency.value,
            "target_value": self.target_value,
            "unit": self.unit,
            "co2_saved_per_unit": self.co2_saved_per_unit,
            "xp_per_completion": self.xp_per_completion,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }


@dataclass
class HabitStreakRecord:
    id: Optional[int]
    habit_id: int
    user_id: int
    current_streak: int
    longest_streak: int
    total_completions: int
    last_completed_date: Optional[str]
    freeze_tokens_remaining: int = 2

    def is_streak_active(self) -> bool:
        if not self.last_completed_date:
            return False
        last_date = date.fromisoformat(self.last_completed_date)
        days_diff = (date.today() - last_date).days
        return days_diff <= 1


@dataclass
class HabitLogEntry:
    id: Optional[int]
    habit_id: int
    user_id: int
    logged_date: str
    value_logged: float
    co2_avoided_kg: float
    xp_earned: int
    notes: Optional[str] = None
