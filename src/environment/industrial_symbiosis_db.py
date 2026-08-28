"""Database persistence for Industrial Symbiosis networks.
"""

import os
import sqlite3
from typing import List, Dict, Any

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


def init_industrial_symbiosis_db(db_path: str = DB_NAME) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS industrial_heat_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            facility_name TEXT NOT NULL,
            stream_type TEXT,
            recovered_kw REAL,
            annual_mwh REAL,
            avoided_co2_tons REAL,
            annual_savings_usd REAL,
            payback_years REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_industrial_plan(
    user_id: int,
    facility_name: str,
    stream_type: str,
    recovered_kw: float,
    annual_mwh: float,
    avoided_co2_tons: float,
    annual_savings_usd: float,
    payback_years: float,
    db_path: str = DB_NAME,
) -> int:
    init_industrial_symbiosis_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO industrial_heat_plans (
            user_id, facility_name, stream_type, recovered_kw,
            annual_mwh, avoided_co2_tons, annual_savings_usd, payback_years
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, facility_name, stream_type, recovered_kw, annual_mwh, avoided_co2_tons, annual_savings_usd, payback_years),
    )
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return plan_id


def get_user_industrial_plans(user_id: int, db_path: str = DB_NAME) -> List[Dict[str, Any]]:
    init_industrial_symbiosis_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM industrial_heat_plans WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    plans = [dict(row) for row in rows]
    conn.close()
    return plans
