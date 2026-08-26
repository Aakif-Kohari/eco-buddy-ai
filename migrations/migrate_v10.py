import sqlite3
from typing import Any

def migrate(conn: sqlite3.Connection) -> None:
    """
    Migration v10: Create daily_activity_summary table.
    """
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_activity_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_date DATE NOT NULL,
            assessment_count INTEGER DEFAULT 0,
            challenge_count INTEGER DEFAULT 0,
            xp_earned INTEGER DEFAULT 0,
            habit_count INTEGER DEFAULT 0,
            intensity_level INTEGER DEFAULT 0,
            UNIQUE(user_id, activity_date)
        )
    """)

    conn.commit()
