"""Database persistence layer for Bioclimatic Passive Cooling Audits.
"""

import os
import sqlite3
from typing import List, Dict, Any

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


def init_passive_comfort_db(db_path: str = DB_NAME) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS passive_cooling_audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            building_name TEXT NOT NULL,
            indoor_temp_c REAL,
            temp_drop_c REAL,
            pmv_index REAL,
            ppd_pct REAL,
            avoided_kwh REAL,
            savings_usd REAL,
            comfort_rating TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_comfort_audit(
    user_id: int,
    building_name: str,
    indoor_temp: float,
    temp_drop: float,
    pmv: float,
    ppd: float,
    avoided_kwh: float,
    savings_usd: float,
    comfort_rating: str,
    db_path: str = DB_NAME,
) -> int:
    init_passive_comfort_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO passive_cooling_audits (
            user_id, building_name, indoor_temp_c, temp_drop_c,
            pmv_index, ppd_pct, avoided_kwh, savings_usd, comfort_rating
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, building_name, indoor_temp, temp_drop, pmv, ppd, avoided_kwh, savings_usd, comfort_rating),
    )
    audit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return audit_id


def get_user_comfort_audits(user_id: int, db_path: str = DB_NAME) -> List[Dict[str, Any]]:
    init_passive_comfort_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM passive_cooling_audits WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    audits = [dict(row) for row in rows]
    conn.close()
    return audits
