"""Household Carbon and Sustainability Budgeting.

This module provides tools for setting, tracking, and evaluating
sustainability budgets for households. Budgets can be defined by category
(e.g., "Transport", "Energy") or overall, over specific time periods
(e.g., monthly, weekly, annually).
"""

import sqlite3
import logging
from typing import Any, List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from calendar import monthrange

from household import _get_conn
from household_activities import VALID_CATEGORIES, get_category_breakdown

logger = logging.getLogger(__name__)

VALID_BUDGET_PERIODS = ["weekly", "monthly", "quarterly", "annually"]

def init_budgeting_db() -> bool:
    """Initialize the household budgets tables."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS household_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER NOT NULL,
                category TEXT NOT NULL, -- 'Overall' or specific category
                limit_value REAL NOT NULL,
                unit TEXT NOT NULL,
                period TEXT NOT NULL DEFAULT 'monthly',
                active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
                UNIQUE(household_id, category, period)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS household_budget_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                budget_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL, -- 'warning' (e.g., 80%), 'exceeded'
                message TEXT NOT NULL,
                triggered_date DATE NOT NULL,
                is_read BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY (budget_id) REFERENCES household_budgets(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error initializing household_budgets DB: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def set_budget(
    household_id: int,
    category: str,
    limit_value: float,
    unit: str,
    period: str = "monthly"
) -> Optional[int]:
    """Create or update a sustainability budget.
    
    Args:
        household_id: ID of the household.
        category: 'Overall' or a valid category from VALID_CATEGORIES.
        limit_value: The numerical limit (e.g., 500 kg CO2e).
        unit: Unit of measurement (usually kg CO2e).
        period: One of VALID_BUDGET_PERIODS.
        
    Returns:
        The budget ID, or None on error.
    """
    if category != "Overall" and category not in VALID_CATEGORIES:
        logger.error(f"Invalid category for budget: {category}")
        return None
        
    if period not in VALID_BUDGET_PERIODS:
        logger.error(f"Invalid budget period: {period}")
        return None
        
    if limit_value <= 0:
        logger.error("Budget limit must be positive.")
        return None

    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        # Upsert logic (since household_id, category, period must be unique)
        cursor.execute('''
            INSERT INTO household_budgets (household_id, category, limit_value, unit, period, active)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(household_id, category, period) DO UPDATE SET
                limit_value=excluded.limit_value,
                unit=excluded.unit,
                active=1,
                updated_at=CURRENT_TIMESTAMP
        ''', (household_id, category, limit_value, unit, period))
        
        # To get the ID, we query it back
        cursor.execute('''
            SELECT id FROM household_budgets 
            WHERE household_id = ? AND category = ? AND period = ?
        ''', (household_id, category, period))
        
        row = cursor.fetchone()
        conn.commit()
        return row[0] if row else None
    except sqlite3.Error as e:
        logger.error(f"Database error setting budget: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_budgets(household_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
    """Retrieve all budgets for a household."""
    query = "SELECT * FROM household_budgets WHERE household_id = ?"
    if active_only:
        query += " AND active = 1"
        
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (household_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error fetching budgets: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def deactivate_budget(budget_id: int) -> bool:
    """Mark a budget as inactive."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE household_budgets SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (budget_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error deactivating budget: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def _get_date_range_for_period(period: str, reference_date: Optional[date] = None) -> Tuple[str, str]:
    """Calculate the start and end string dates for a given period."""
    if not reference_date:
        reference_date = date.today()
        
    if period == "weekly":
        # Monday to Sunday
        start = reference_date - timedelta(days=reference_date.weekday())
        end = start + timedelta(days=6)
    elif period == "monthly":
        start = reference_date.replace(day=1)
        _, last_day = monthrange(reference_date.year, reference_date.month)
        end = reference_date.replace(day=last_day)
    elif period == "quarterly":
        quarter = (reference_date.month - 1) // 3 + 1
        start_month = 3 * quarter - 2
        start = reference_date.replace(month=start_month, day=1)
        end_month = start_month + 2
        _, last_day = monthrange(reference_date.year, end_month)
        end = reference_date.replace(month=end_month, day=last_day)
    elif period == "annually":
        start = reference_date.replace(month=1, day=1)
        end = reference_date.replace(month=12, day=31)
    else:
        # Default to monthly if invalid
        start = reference_date.replace(day=1)
        _, last_day = monthrange(reference_date.year, reference_date.month)
        end = reference_date.replace(day=last_day)
        
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def evaluate_budgets(household_id: int, reference_date: Optional[date] = None) -> Dict[int, Dict[str, Any]]:
    """Evaluate current consumption against active budgets.
    
    Returns:
        Dict mapping budget_id to evaluation data (spent, remaining, percentage, status).
    """
    budgets = get_budgets(household_id, active_only=True)
    if not budgets:
        return {}
        
    # We need to fetch breakdowns for different periods.
    # To optimize, we group budgets by period, fetch the breakdown for that period,
    # and then apply the category limits.
    
    period_breakdowns: Dict[str, Dict[str, float]] = {}
    evaluations: Dict[int, Dict[str, Any]] = {}
    
    for b in budgets:
        period = b["period"]
        if period not in period_breakdowns:
            start_d, end_d = _get_date_range_for_period(period, reference_date)
            breakdown = get_category_breakdown(household_id, start_date=start_d, end_date=end_d)
            # Add an 'Overall' key
            breakdown["Overall"] = sum(breakdown.values())
            period_breakdowns[period] = breakdown
            
        category = b["category"]
        limit = b["limit_value"]
        
        # For our simple model, we assume budgets track CO2e.
        spent = period_breakdowns[period].get(category, 0.0)
        percentage = (spent / limit) * 100 if limit > 0 else 0.0
        
        if percentage >= 100:
            status = "exceeded"
        elif percentage >= 80:
            status = "warning"
        else:
            status = "on_track"
            
        evaluations[b["id"]] = {
            "budget": b,
            "spent": spent,
            "remaining": max(0.0, limit - spent),
            "percentage": percentage,
            "status": status,
            "start_date": start_d,
            "end_date": end_d
        }
        
    return evaluations


def check_and_generate_alerts(household_id: int) -> List[Dict[str, Any]]:
    """Run budget evaluation and generate alerts for warnings/exceedances."""
    evaluations = evaluate_budgets(household_id)
    new_alerts = []
    
    today_str = date.today().strftime("%Y-%m-%d")
    
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        for b_id, eval_data in evaluations.items():
            status = eval_data["status"]
            if status in ["warning", "exceeded"]:
                # Check if an alert for this budget+type was already triggered recently
                # For simplicity, we check if there's an alert in the same calendar month.
                # In a robust system we'd tie it to the specific budget period instance.
                cursor.execute('''
                    SELECT id FROM household_budget_alerts
                    WHERE budget_id = ? AND alert_type = ? AND strftime('%Y-%m', triggered_date) = strftime('%Y-%m', ?)
                ''', (b_id, status, today_str))
                
                if not cursor.fetchone():
                    # Generate alert
                    b_cat = eval_data["budget"]["category"]
                    b_per = eval_data["budget"]["period"]
                    pct = eval_data["percentage"]
                    
                    if status == "exceeded":
                        msg = f"Alert! You have exceeded your {b_per} {b_cat} budget ({pct:.1f}% consumed)."
                    else:
                        msg = f"Warning! You are nearing your {b_per} {b_cat} budget limit ({pct:.1f}% consumed)."
                        
                    cursor.execute('''
                        INSERT INTO household_budget_alerts (budget_id, alert_type, message, triggered_date)
                        VALUES (?, ?, ?, ?)
                    ''', (b_id, status, msg, today_str))
                    
                    new_alerts.append({
                        "id": cursor.lastrowid,
                        "budget_id": b_id,
                        "alert_type": status,
                        "message": msg,
                        "triggered_date": today_str
                    })
                    
        conn.commit()
        return new_alerts
    except sqlite3.Error as e:
        logger.error(f"Error generating budget alerts: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_unread_alerts(household_id: int) -> List[Dict[str, Any]]:
    """Get unread budget alerts for a household."""
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.*, b.category, b.period 
            FROM household_budget_alerts a
            JOIN household_budgets b ON a.budget_id = b.id
            WHERE b.household_id = ? AND a.is_read = 0
            ORDER BY a.triggered_date DESC
        ''', (household_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error fetching alerts: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def mark_alerts_read(alert_ids: List[int]) -> bool:
    """Mark specific alerts as read."""
    if not alert_ids:
        return True
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(alert_ids))
        cursor.execute(f"UPDATE household_budget_alerts SET is_read = 1 WHERE id IN ({placeholders})", alert_ids)
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error marking alerts read: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()
