"""Data models and constants for the Eco Wellness Tracker."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime, timedelta


class HabitCategory(Enum):
    """Categories of eco-friendly habits."""
    ENERGY = "energy"
    WATER = "water"
    TRANSPORT = "transport"
    FOOD = "food"
    WASTE = "waste"
    NATURE = "nature"
    MINDFULNESS = "mindfulness"
    SHOPPING = "shopping"


class HabitFrequency(Enum):
    """How often a habit should be performed."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class StreakTier(Enum):
    """Streak achievement tiers."""
    STARTER = "starter"
    CONSISTENT = "consistent"
    DEDICATED = "dedicated"
    CHAMPION = "champion"
    LEGEND = "legend"


class WellnessScore(Enum):
    """Overall wellness score categories."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    NEEDS_WORK = "needs_work"


@dataclass
class EcoHabit:
    """An eco-friendly habit to track."""
    habit_id: str
    name: str
    description: str
    category: HabitCategory
    frequency: HabitFrequency
    eco_points: int
    carbon_save_kg: float
    water_save_liters: float
    icon: str
    color: str
    is_active: bool = True
    created_at: str = ""


@dataclass
class HabitLog:
    """A single log entry for a habit completion."""
    log_id: str
    habit_id: str
    user_id: str
    completed_at: str
    notes: str = ""
    eco_points_earned: int = 0


@dataclass
class HabitStreak:
    """Streak information for a habit."""
    habit_id: str
    user_id: str
    current_streak: int
    longest_streak: int
    total_completions: int
    last_completed_at: Optional[str]
    tier: StreakTier
    streak_started_at: str

    @property
    def is_active_today(self) -> bool:
        if not self.last_completed_at:
            return False
        try:
            last = datetime.strptime(self.last_completed_at, "%Y-%m-%d %H:%M:%S")
            return last.date() == datetime.now().date()
        except (ValueError, TypeError):
            return False


@dataclass
class DailyWellnessScore:
    """Daily wellness score record."""
    date: str
    eco_score: float
    habits_completed: int
    habits_total: int
    eco_points: int
    carbon_saved_kg: float
    water_saved_liters: float
    mood: int  # 1-5
    energy_level: int  # 1-5
    nature_time_minutes: int
    mindfulness_minutes: int


@dataclass
class WellnessGoal:
    """A wellness goal to achieve."""
    goal_id: str
    user_id: str
    title: str
    category: HabitCategory
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
            return max((deadline - datetime.now()).days, 0)
        except (ValueError, TypeError):
            return 0


@dataclass
class WellnessWeeklyReport:
    """Weekly wellness summary src.reporting.report."""
    week_start: str
    week_end: str
    total_habits_completed: int
    total_eco_points: int
    total_carbon_saved_kg: float
    total_water_saved_liters: float
    avg_mood: float
    avg_energy: float
    total_nature_minutes: int
    total_mindfulness_minutes: int
    completion_rate: float
    top_habit: str
    streak_highlights: List[Dict[str, str]]


@dataclass
class WellnessFilterOptions:
    """Filter options for the dashboard."""
    category: HabitCategory | None
    frequency: HabitFrequency | None
    date_from: str
    date_to: str
    min_streak: int
    show_completed_only: bool


@dataclass
class WellnessStats:
    """Aggregate wellness statistics."""
    total_habits: int
    active_habits: int
    total_completions: int
    total_eco_points: int
    total_carbon_saved_kg: float
    total_water_saved_liters: float
    avg_daily_score: float
    current_best_streak: int
    total_days_tracked: int
    completion_rate: float
    top_category: str
    weekly_trend: str  # "improving", "stable", "declining"


STREAK_THRESHOLDS = {
    StreakTier.STARTER: 1,
    StreakTier.CONSISTENT: 7,
    StreakTier.DEDICATED: 21,
    StreakTier.CHAMPION: 60,
    StreakTier.LEGEND: 100,
}

STREAK_COLORS = {
    StreakTier.STARTER: "#94a3b8",
    StreakTier.CONSISTENT: "#22c55e",
    StreakTier.DEDICATED: "#0ea5e9",
    StreakTier.CHAMPION: "#f59e0b",
    StreakTier.LEGEND: "#8b5cf6",
}

CATEGORY_ICONS = {
    HabitCategory.ENERGY: "⚡",
    HabitCategory.WATER: "💧",
    HabitCategory.TRANSPORT: "🚲",
    HabitCategory.FOOD: "🥗",
    HabitCategory.WASTE: "♻️",
    HabitCategory.NATURE: "🌿",
    HabitCategory.MINDFULNESS: "🧘",
    HabitCategory.SHOPPING: "🛍️",
}

CATEGORY_COLORS = {
    HabitCategory.ENERGY: "#f59e0b",
    HabitCategory.WATER: "#0ea5e9",
    HabitCategory.TRANSPORT: "#22c55e",
    HabitCategory.FOOD: "#14b8a6",
    HabitCategory.WASTE: "#8b5cf6",
    HabitCategory.NATURE: "#16a34a",
    HabitCategory.MINDFULNESS: "#ec4899",
    HabitCategory.SHOPPING: "#f97316",
}

MOOD_LABELS = {1: "😢 Awful", 2: "😐 Low", 3: "🙂 Okay", 4: "😊 Good", 5: "😄 Great"}
ENERGY_LABELS = {1: "🪫 Exhausted", 2: "😴 Tired", 3: "🙂 Normal", 4: "⚡ Energized", 5: "🔥 Peak"}
