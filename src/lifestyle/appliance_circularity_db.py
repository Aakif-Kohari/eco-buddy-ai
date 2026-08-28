"""Database persistence for Appliance Circularity Assessments.
"""

import os
import sqlite3
from typing import List, Dict, Any

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


def init_appliance_circularity_db(db_path: str = DB_NAME) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS appliance_circularity_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            appliance_name TEXT NOT NULL,
            category TEXT,
            recommended_decision TEXT,
            failure_prob_pct REAL,
            residual_value_usd REAL,
            embodied_carbon_saved_kg REAL,
            circularity_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_circularity_assessment(
    user_id: int,
    appliance_name: str,
    category: str,
    decision: str,
    failure_prob: float,
    residual_val: float,
    carbon_saved: float,
    score: float,
    db_path: str = DB_NAME,
) -> int:
    init_appliance_circularity_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO appliance_circularity_assessments (
            user_id, appliance_name, category, recommended_decision,
            failure_prob_pct, residual_value_usd, embodied_carbon_saved_kg, circularity_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, appliance_name, category, decision, failure_prob, residual_val, carbon_saved, score),
    )
    audit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return audit_id


def get_user_circularity_assessments(user_id: int, db_path: str = DB_NAME) -> List[Dict[str, Any]]:
    init_appliance_circularity_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM appliance_circularity_assessments WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    items = [dict(row) for row in rows]
    conn.close()
    return items
