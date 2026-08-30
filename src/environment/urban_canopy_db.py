"""Database persistence module for Urban Canopy & Microclimate Planner.
"""

import os
import sqlite3
import json
from typing import List, Dict, Any, Optional

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


def init_urban_canopy_db(db_path: str = DB_NAME) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS urban_canopy_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            zone_name TEXT NOT NULL,
            baseline_temp_c REAL,
            target_canopy_pct REAL,
            species TEXT,
            soil_type TEXT,
            trees_recommended INTEGER,
            air_temp_drop_c REAL,
            annual_carbon_kg REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_canopy_plan(
    user_id: int,
    zone_name: str,
    baseline_temp: float,
    target_canopy: float,
    species: str,
    soil_type: str,
    trees: int,
    temp_drop: float,
    carbon_kg: float,
    db_path: str = DB_NAME,
) -> int:
    init_urban_canopy_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO urban_canopy_plans (
            user_id, zone_name, baseline_temp_c, target_canopy_pct,
            species, soil_type, trees_recommended, air_temp_drop_c, annual_carbon_kg
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, zone_name, baseline_temp, target_canopy, species, soil_type, trees, temp_drop, carbon_kg),
    )
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return plan_id


def get_user_canopy_plans(user_id: int, db_path: str = DB_NAME) -> List[Dict[str, Any]]:
    init_urban_canopy_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM urban_canopy_plans WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    plans = [dict(row) for row in rows]
    conn.close()
    return plans
