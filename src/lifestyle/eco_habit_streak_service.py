"""
Eco-Habit Streak Tracker Core Service Layer
Encapsulates business operations, streak freeze mechanics, daily habit completion, and analytics.
"""

from typing import List, Dict, Any, Optional
import logging

from src.lifestyle.eco_habit_streak_types import EcoHabit, HabitCategory, HabitFrequency
from src.lifestyle.eco_habit_streak_db import (
    init_habit_streak_db,
    create_user_habit,
    get_user_habits_with_streaks,
    log_habit_completion,
    get_habit_analytics_summary,
)

logger = logging.getLogger(__name__)


class EcoHabitStreakService:
    def __init__(self, db_name: str = "eco_buddy.db"):
        self.db_name = db_name
        init_habit_streak_db(self.db_name)

    def add_custom_habit(
        self,
        user_id: int,
        title: str,
        description: str,
        category: HabitCategory,
        frequency: HabitFrequency,
        target_value: float,
        unit: str,
        co2_saved_per_unit: float,
        xp_per_completion: int,
    ) -> Optional[EcoHabit]:
        """Creates a new eco-habit for the user."""
        habit = EcoHabit(
            id=None,
            user_id=user_id,
            title=title,
            description=description,
            category=category,
            frequency=frequency,
            target_value=target_value,
            unit=unit,
            co2_saved_per_unit=co2_saved_per_unit,
            xp_per_completion=xp_per_completion,
        )
        return create_user_habit(habit, self.db_name)

    def get_habits_for_user(self, user_id: int, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves user habits with current streak info and optional category filtering."""
        habits = get_user_habits_with_streaks(user_id, self.db_name)
        if category_filter and category_filter != "All":
            habits = [h for h in habits if h["category"] == category_filter]
        return habits

    def complete_habit(self, user_id: int, habit_id: int, value_logged: float, notes: str = "") -> Dict[str, Any]:
        """Logs daily completion for a habit."""
        if value_logged <= 0:
            return {"success": False, "message": "Value logged must be greater than zero."}
        return log_habit_completion(user_id, habit_id, value_logged, notes, self.db_name)

    def get_user_summary(self, user_id: int) -> Dict[str, Any]:
        """Calculates total lifetime habit streak metrics and impact."""
        return get_habit_analytics_summary(user_id, self.db_name)
