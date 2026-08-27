"""
Unit tests for Habit Tracker persistence, streak calculations, and recommender.
"""

import pytest
import sqlite3
import os
import tempfile
from src.lifestyle.habit_tracker import (
    HabitDatabase,
    HabitTracker,
    HabitRecommender,
    CarbonSavingsCalculator,
    init_habit_db,
    save_user_habits_db,
    load_user_habits_db
)


def test_habit_database_loading():
    habits = HabitDatabase.get_all_habits()
    assert len(habits) >= 20
    transport_habits = HabitDatabase.get_habits_by_category("Transport")
    assert len(transport_habits) == 4
    for h in transport_habits:
        assert h["category"] == "Transport"
        assert h["carbon_saving"] > 0


def test_habit_tracker_persistence_and_streaks():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        init_habit_db(db_path)
        tracker = HabitTracker(user_id=42, db_name=db_path)
        
        # Add habit
        added = tracker.add_habit("💡 Turn off lights")
        assert added is True
        assert "💡 Turn off lights" in tracker.data["active_habits"]
        
        # Complete habit
        completed = tracker.complete_habit("💡 Turn off lights")
        assert completed is True
        assert tracker.data["streaks"]["💡 Turn off lights"] == 1
        
        # Reload tracker from DB
        tracker2 = HabitTracker(user_id=42, db_name=db_path)
        assert "💡 Turn off lights" in tracker2.data["active_habits"]
        assert tracker2.data["streaks"]["💡 Turn off lights"] == 1
        
        stats = tracker2.get_stats()
        assert stats["total_habits"] == 1
        assert stats["completed_today"] == 1
        assert stats["completion_rate"] == 100.0

        # Remove habit
        assert tracker2.remove_habit("💡 Turn off lights") is True
        assert "💡 Turn off lights" not in tracker2.data["active_habits"]
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_carbon_savings_calculator():
    habits = ['💡 Turn off lights', '🥗 Meatless Monday']
    savings = CarbonSavingsCalculator.calculate_savings(habits)
    assert savings["total_carbon"] == pytest.approx(3.5, rel=1e-2)
    assert savings["trees_equivalent"] > 0
    assert savings["cars_equivalent"] > 0
