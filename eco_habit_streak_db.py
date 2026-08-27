"""
Eco-Habit Streak Tracker Database Layer
Handles SQLite table initialization, habit creation, logging, streak calculation, freeze tokens, and analytics queries.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta, datetime

from database_connection import database_connection, execute_with_retry
from eco_habit_streak_types import (
    EcoHabit,
    HabitCategory,
    HabitFrequency,
    HabitStreakRecord,
    HabitLogEntry,
)

logger = logging.getLogger(__name__)
DB_NAME = "eco_buddy.db"


def init_habit_streak_db(db_name: str = DB_NAME) -> bool:
    """Initializes SQLite tables for eco habit tracking and streak mechanics."""
    def _create():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()

            # Eco Habits Master Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eco_habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    target_value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    co2_saved_per_unit REAL NOT NULL,
                    xp_per_completion INTEGER NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Habit Streak Tracking Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habit_streak_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    current_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    total_completions INTEGER DEFAULT 0,
                    last_completed_date TEXT,
                    freeze_tokens_remaining INTEGER DEFAULT 2,
                    FOREIGN KEY(habit_id) REFERENCES eco_habits(id),
                    UNIQUE(habit_id, user_id)
                )
            """)

            # Daily Habit Completion Logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habit_completion_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habit_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    logged_date TEXT NOT NULL,
                    value_logged REAL NOT NULL,
                    co2_avoided_kg REAL NOT NULL,
                    xp_earned INTEGER NOT NULL,
                    notes TEXT,
                    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(habit_id) REFERENCES eco_habits(id)
                )
            """)

            conn.commit()

    try:
        execute_with_retry(_create)
        _seed_default_habits(db_name)
        return True
    except sqlite3.Error as e:
        logger.error("Failed to initialize habit streak DB: %s", e)
        return False


def _seed_default_habits(db_name: str = DB_NAME) -> None:
    """Seeds starter eco-habits if none exist for default user."""
    def _seed():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM eco_habits WHERE user_id = 1")
            count = cursor.fetchone()[0]

            if count == 0:
                defaults = [
                    (1, "Reusable Water Bottle", "Use a refillable water bottle instead of purchasing single-use plastic.", HabitCategory.WASTE.value, HabitFrequency.DAILY.value, 1.0, "bottle", 0.15, 20),
                    (1, "Meatless Monday / Lunch", "Choose a 100% plant-based meal for lunch or dinner.", HabitCategory.FOOD.value, HabitFrequency.DAILY.value, 1.0, "meal", 1.80, 50),
                    (1, "Public Transit / Cycle Commute", "Use bike or public bus/train for daily commute.", HabitCategory.TRANSPORT.value, HabitFrequency.WEEKDAYS.value, 10.0, "km", 0.19, 45),
                    (1, "Cold Water Wash", "Do laundry loads with cold water to save electricity.", HabitCategory.ENERGY.value, HabitFrequency.WEEKLY.value, 1.0, "load", 0.65, 30),
                    (1, "5-Minute Shower", "Limit shower duration to 5 minutes to save water and heating energy.", HabitCategory.WATER.value, HabitFrequency.DAILY.value, 1.0, "shower", 0.40, 25),
                ]

                for d in defaults:
                    cursor.execute("""
                        INSERT INTO eco_habits (user_id, title, description, category, frequency, target_value, unit, co2_saved_per_unit, xp_per_completion)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, d)
                    habit_id = cursor.lastrowid
                    cursor.execute("""
                        INSERT INTO habit_streak_records (habit_id, user_id, current_streak, longest_streak, total_completions)
                        VALUES (?, ?, 0, 0, 0)
                    """, (habit_id, d[0]))

                conn.commit()

    try:
        execute_with_retry(_seed)
    except Exception as e:
        logger.error("Error seeding default habits: %s", e)


def create_user_habit(habit: EcoHabit, db_name: str = DB_NAME) -> Optional[EcoHabit]:
    """Creates a new custom eco habit for a user."""
    def _insert():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO eco_habits (user_id, title, description, category, frequency, target_value, unit, co2_saved_per_unit, xp_per_completion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                habit.user_id, habit.title, habit.description, habit.category.value,
                habit.frequency.value, habit.target_value, habit.unit, habit.co2_saved_per_unit, habit.xp_per_completion
            ))
            habit_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO habit_streak_records (habit_id, user_id, current_streak, longest_streak, total_completions)
                VALUES (?, ?, 0, 0, 0)
            """, (habit_id, habit.user_id))

            conn.commit()

            habit.id = habit_id
            return habit

    try:
        return execute_with_retry(_insert)
    except Exception as e:
        logger.error("Error creating custom habit: %s", e)
        return None


def get_user_habits_with_streaks(user_id: int, db_name: str = DB_NAME) -> List[Dict[str, Any]]:
    """Fetches all active habits for a user along with current streak statistics."""
    def _fetch():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    h.id, h.title, h.description, h.category, h.frequency, h.target_value, h.unit,
                    h.co2_saved_per_unit, h.xp_per_completion,
                    s.current_streak, s.longest_streak, s.total_completions, s.last_completed_date, s.freeze_tokens_remaining
                FROM eco_habits h
                LEFT JOIN habit_streak_records s ON h.id = s.habit_id AND s.user_id = h.user_id
                WHERE h.user_id = ? AND h.is_active = 1
                ORDER BY h.id ASC
            """, (user_id,))
            rows = cursor.fetchall()
            results = []
            today_str = date.today().isoformat()

            for r in rows:
                last_date_str = r[12]
                completed_today = (last_date_str == today_str)

                results.append({
                    "habit_id": r[0],
                    "title": r[1],
                    "description": r[2],
                    "category": r[3],
                    "frequency": r[4],
                    "target_value": r[5],
                    "unit": r[6],
                    "co2_saved_per_unit": r[7],
                    "xp_per_completion": r[8],
                    "current_streak": r[9] or 0,
                    "longest_streak": r[10] or 0,
                    "total_completions": r[11] or 0,
                    "last_completed_date": last_date_str,
                    "freeze_tokens": r[13] or 0,
                    "completed_today": completed_today,
                })
            return results

    try:
        return execute_with_retry(_fetch)
    except Exception as e:
        logger.error("Error fetching user habits with streaks: %s", e)
        return []


def log_habit_completion(user_id: int, habit_id: int, value_logged: float, notes: str = "", db_name: str = DB_NAME) -> Dict[str, Any]:
    """Logs a habit completion, updates daily streak mechanics, awards XP and CO2 savings."""
    def _log():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()

            # Get habit details
            cursor.execute("SELECT target_value, co2_saved_per_unit, xp_per_completion FROM eco_habits WHERE id = ? AND user_id = ?", (habit_id, user_id))
            habit_row = cursor.fetchone()
            if not habit_row:
                return {"success": False, "message": "Habit not found."}

            target_val, co2_per_unit, xp_per_comp = habit_row[0], habit_row[1], habit_row[2]

            today = date.today()
            today_str = today.isoformat()

            # Check existing streak record
            cursor.execute("SELECT current_streak, longest_streak, total_completions, last_completed_date, freeze_tokens_remaining FROM habit_streak_records WHERE habit_id = ? AND user_id = ?", (habit_id, user_id))
            streak_row = cursor.fetchone()

            if not streak_row:
                curr_streak, long_streak, total_comp, last_date_str, freeze_tokens = 0, 0, 0, None, 2
            else:
                curr_streak, long_streak, total_comp, last_date_str, freeze_tokens = streak_row[0], streak_row[1], streak_row[2], streak_row[3], streak_row[4]

            if last_date_str == today_str:
                return {"success": False, "message": "Habit already logged for today!"}

            # Streak logic
            if last_date_str:
                last_date = date.fromisoformat(last_date_str)
                days_diff = (today - last_date).days
                if days_diff == 1:
                    curr_streak += 1
                elif days_diff == 2 and freeze_tokens > 0:
                    # Use streak freeze token
                    freeze_tokens -= 1
                    curr_streak += 1
                else:
                    curr_streak = 1
            else:
                curr_streak = 1

            if curr_streak > long_streak:
                long_streak = curr_streak

            total_comp += 1
            co2_avoided = round(value_logged * co2_per_unit, 2)
            xp_earned = int(xp_per_comp * (value_logged / target_val)) if target_val > 0 else xp_per_comp

            # Update streak table
            cursor.execute("""
                INSERT INTO habit_streak_records (habit_id, user_id, current_streak, longest_streak, total_completions, last_completed_date, freeze_tokens_remaining)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(habit_id, user_id) DO UPDATE SET
                    current_streak = excluded.current_streak,
                    longest_streak = excluded.longest_streak,
                    total_completions = excluded.total_completions,
                    last_completed_date = excluded.last_completed_date,
                    freeze_tokens_remaining = excluded.freeze_tokens_remaining
            """, (habit_id, user_id, curr_streak, long_streak, total_comp, today_str, freeze_tokens))

            # Insert log entry
            cursor.execute("""
                INSERT INTO habit_completion_logs (habit_id, user_id, logged_date, value_logged, co2_avoided_kg, xp_earned, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (habit_id, user_id, today_str, value_logged, co2_avoided, xp_earned, notes))

            conn.commit()

            return {
                "success": True,
                "current_streak": curr_streak,
                "longest_streak": long_streak,
                "co2_avoided_kg": co2_avoided,
                "xp_earned": xp_earned,
                "freeze_tokens_remaining": freeze_tokens,
            }

    try:
        return execute_with_retry(_log)
    except Exception as e:
        logger.error("Error logging habit completion: %s", e)
        return {"success": False, "message": str(e)}


def get_habit_analytics_summary(user_id: int, db_name: str = DB_NAME) -> Dict[str, Any]:
    """Calculates overall user habit stats (total XP, total CO2 saved, max streak)."""
    def _stats():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    SUM(co2_avoided_kg),
                    SUM(xp_earned),
                    COUNT(*)
                FROM habit_completion_logs
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            total_co2 = round(row[0] or 0.0, 2)
            total_xp = int(row[1] or 0)
            total_logs = row[2] or 0

            cursor.execute("SELECT MAX(current_streak), MAX(longest_streak) FROM habit_streak_records WHERE user_id = ?", (user_id,))
            s_row = cursor.fetchone()
            active_max_streak = s_row[0] or 0
            all_time_max_streak = s_row[1] or 0

            return {
                "total_co2_avoided_kg": total_co2,
                "total_xp_earned": total_xp,
                "total_completions": total_logs,
                "active_max_streak": active_max_streak,
                "all_time_max_streak": all_time_max_streak,
            }

    try:
        return execute_with_retry(_stats)
    except Exception as e:
        logger.error("Error calculating habit analytics: %s", e)
        return {
            "total_co2_avoided_kg": 0.0,
            "total_xp_earned": 0,
            "total_completions": 0,
            "active_max_streak": 0,
            "all_time_max_streak": 0,
        }
