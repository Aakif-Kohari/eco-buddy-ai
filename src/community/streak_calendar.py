from datetime import date, timedelta
from typing import Dict, Any, Tuple
import sqlite3
import os

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_activity_intensity(count: int) -> int:
    """Map daily activity counts to a 0-4 intensity scale."""
    if count <= 0:
        return 0
    elif count == 1:
        return 1
    elif count == 2:
        return 2
    elif count <= 4:
        return 3
    else:
        return 4

def get_daily_activity_counts(user_id: int, year: int) -> Dict[date, Dict[str, Any]]:
    """
    Fetch daily activity from the database for a specific year.
    Returns a dictionary mapping date objects to their summary stats.
    """
    start_date = date(year, 1, 1).isoformat()
    end_date = date(year, 12, 31).isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT activity_date, assessment_count, challenge_count, xp_earned, habit_count
        FROM daily_activity_summary
        WHERE user_id = ? AND activity_date BETWEEN ? AND ?
    """
    cursor.execute(query, (user_id, start_date, end_date))
    rows = cursor.fetchall()
    conn.close()

    activity_data = {}
    for row in rows:
        activity_date = date.fromisoformat(row["activity_date"])
        total_actions = (
            row["assessment_count"] + 
            row["challenge_count"] + 
            row["habit_count"] + 
            (1 if row["xp_earned"] > 0 else 0)
        )
        intensity = get_activity_intensity(total_actions)
        
        activity_data[activity_date] = {
            "assessment_count": row["assessment_count"],
            "challenge_count": row["challenge_count"],
            "xp_earned": row["xp_earned"],
            "habit_count": row["habit_count"],
            "total_actions": total_actions,
            "intensity_level": intensity
        }
        
    return activity_data

def compute_streak_stats(activity_data: Dict[date, Dict[str, Any]], current_date: date = None) -> Tuple[int, int, int]:
    """
    Calculate current streak, longest streak, and total active days.
    
    Args:
        activity_data: Dictionary mapping date objects to activity data
        current_date: The date to calculate current streak from. Defaults to today.
        
    Returns:
        Tuple of (current_streak, longest_streak, total_active_days)
    """
    if not activity_data:
        return 0, 0, 0

    if current_date is None:
        current_date = date.today()

    active_dates = sorted([d for d, data in activity_data.items() if data["total_actions"] > 0], reverse=True)
    total_active_days = len(active_dates)
    
    if not active_dates:
        return 0, 0, 0

    current_streak = 0
    longest_streak = 0
    current_temp_streak = 0
    
    # Calculate current streak
    check_date = current_date
    if check_date in active_dates:
        current_streak += 1
        check_date -= timedelta(days=1)
        while check_date in active_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
    else:
        # If today is not active, check if yesterday was (streak is still alive if yesterday was active)
        check_date -= timedelta(days=1)
        if check_date in active_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
            while check_date in active_dates:
                current_streak += 1
                check_date -= timedelta(days=1)

    # Calculate longest streak
    sorted_active_dates_fwd = sorted(active_dates)
    if sorted_active_dates_fwd:
        current_temp_streak = 1
        longest_streak = 1
        for i in range(1, len(sorted_active_dates_fwd)):
            if (sorted_active_dates_fwd[i] - sorted_active_dates_fwd[i-1]).days == 1:
                current_temp_streak += 1
                longest_streak = max(longest_streak, current_temp_streak)
            else:
                current_temp_streak = 1

    return current_streak, longest_streak, total_active_days
