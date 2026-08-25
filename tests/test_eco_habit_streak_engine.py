"""
Unit and Integration Tests for Eco-Habit Streak Tracker Engine
"""

import unittest
import os
from eco_habit_streak_types import HabitCategory, HabitFrequency, EcoHabit
from eco_habit_streak_db import (
    init_habit_streak_db,
    get_user_habits_with_streaks,
    log_habit_completion,
    get_habit_analytics_summary,
)
from eco_habit_streak_service import EcoHabitStreakService

TEST_DB = "test_eco_habit_streaks.db"


class TestEcoHabitStreakEngine(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        init_habit_streak_db(TEST_DB)
        self.service = EcoHabitStreakService(db_name=TEST_DB)

    def tearDown(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_database_initialization_and_default_seeding(self):
        habits = self.service.get_habits_for_user(1)
        self.assertGreaterEqual(len(habits), 5)
        self.assertEqual(habits[0]["title"], "Reusable Water Bottle")

    def test_custom_habit_creation(self):
        new_habit = self.service.add_custom_habit(
            user_id=1,
            title="Solar Power Appliance Use",
            description="Run dishwasher during peak solar generation hours.",
            category=HabitCategory.ENERGY,
            frequency=HabitFrequency.DAILY,
            target_value=1.0,
            unit="run",
            co2_saved_per_unit=0.8,
            xp_per_completion=30,
        )
        self.assertIsNotNone(new_habit)
        self.assertIsNotNone(new_habit.id)

    def test_habit_completion_and_streak_increment(self):
        habits = self.service.get_habits_for_user(1)
        habit_id = habits[0]["habit_id"]

        # Log completion today
        res1 = self.service.complete_habit(user_id=1, habit_id=habit_id, value_logged=1.0)
        self.assertTrue(res1["success"])
        self.assertEqual(res1["current_streak"], 1)

        # Duplicate log today should fail
        res2 = self.service.complete_habit(user_id=1, habit_id=habit_id, value_logged=1.0)
        self.assertFalse(res2["success"])

    def test_habit_summary_analytics(self):
        habits = self.service.get_habits_for_user(1)
        self.service.complete_habit(user_id=1, habit_id=habits[0]["habit_id"], value_logged=1.0)

        summary = self.service.get_user_summary(1)
        self.assertGreater(summary["total_co2_avoided_kg"], 0)
        self.assertGreater(summary["total_xp_earned"], 0)
        self.assertEqual(summary["total_completions"], 1)


if __name__ == "__main__":
    unittest.main()
