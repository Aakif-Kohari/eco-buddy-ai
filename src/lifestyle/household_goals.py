"""Household sustainability goals tracking.

This module provides the database and logic for household-level
sustainability goals (e.g., "Reduce electricity by 20% by Dec").
"""

import sqlite3
import logging
from typing import Any, List, Dict, Optional
from datetime import datetime

from src.lifestyle.household import _get_conn

logger = logging.getLogger(__name__)

VALID_METRICS = ["carbon", "energy", "water", "waste", "food", "transport", "other"]
VALID_STATUSES = ["active", "completed", "failed", "abandoned"]

def init_goals_db() -> bool:
    """Initialize the household goals tables."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS household_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                metric TEXT NOT NULL,
                target_value REAL NOT NULL,
                current_value REAL NOT NULL DEFAULT 0.0,
                unit TEXT NOT NULL,
                deadline DATE,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error initializing household_goals DB: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def create_goal(
    household_id: int,
    title: str,
    metric: str,
    target_value: float,
    unit: str,
    current_value: float = 0.0,
    deadline: Optional[str] = None
) -> Optional[int]:
    """Create a new sustainability goal for a src.lifestyle.household."""
    if not title.strip():
        logger.error("Goal title cannot be empty.")
        return None
        
    if metric not in VALID_METRICS:
        logger.error(f"Invalid metric: {metric}")
        return None
        
    if deadline:
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            logger.error("Invalid deadline format. Use YYYY-MM-DD.")
            return None

    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM households WHERE id = ?", (household_id,))
        if not cursor.fetchone():
            logger.error(f"Household {household_id} does not exist.")
            return None
            
        cursor.execute('''
            INSERT INTO household_goals 
            (household_id, title, metric, target_value, current_value, unit, deadline, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        ''', (household_id, title, metric, target_value, current_value, unit, deadline))
        
        goal_id = cursor.lastrowid
        conn.commit()
        return goal_id
    except sqlite3.Error as e:
        logger.error(f"Database error creating goal: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_goals(
    household_id: int,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieve goals for a src.lifestyle.household."""
    query = '''
        SELECT id, household_id, title, metric, target_value, current_value, 
               unit, deadline, status, created_at, updated_at
        FROM household_goals
        WHERE household_id = ?
    '''
    params: List[Any] = [household_id]
    
    if status:
        query += " AND status = ?"
        params.append(status)
        
    query += " ORDER BY deadline ASC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error fetching goals: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_goal(goal_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single goal by ID."""
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM household_goals WHERE id = ?", (goal_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching goal {goal_id}: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def update_goal_progress(goal_id: int, new_current_value: float) -> bool:
    """Update the current value of a goal."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        # Check if the goal should automatically be marked completed
        cursor.execute("SELECT target_value FROM household_goals WHERE id = ?", (goal_id,))
        row = cursor.fetchone()
        if not row:
            return False
            
        target = row[0]
        status = 'completed' if new_current_value >= target else 'active'
        
        cursor.execute('''
            UPDATE household_goals 
            SET current_value = ?, status = CASE WHEN status = 'active' THEN ? ELSE status END, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_current_value, status, goal_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error updating goal progress for {goal_id}: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def update_goal_status(goal_id: int, status: str) -> bool:
    """Explicitly change the status of a goal (e.g., mark abandoned)."""
    if status not in VALID_STATUSES:
        logger.error(f"Invalid status: {status}")
        return False
        
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE household_goals 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, goal_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error updating goal status for {goal_id}: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def delete_goal(goal_id: int) -> bool:
    """Delete a goal."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM household_goals WHERE id = ?", (goal_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error deleting goal {goal_id}: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def check_overdue_goals(household_id: int) -> int:
    """Scan and mark active goals as failed if they are past their deadline.
    
    Returns:
        Number of goals marked as failed.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE household_goals
            SET status = 'failed', updated_at = CURRENT_TIMESTAMP
            WHERE household_id = ? AND status = 'active' AND deadline IS NOT NULL AND deadline < ?
        ''', (household_id, today))
        
        count = cursor.rowcount
        conn.commit()
        return count
    except sqlite3.Error as e:
        logger.error(f"Error checking overdue goals for household {household_id}: {e}")
        return 0
    finally:
        if 'conn' in locals() and conn:
            conn.close()
