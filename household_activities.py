"""Household activities tracking module.

This module provides the database and logic for tracking sustainability
activities at a household level. Activities can be shared (e.g., a shared electricity bill)
or individual (e.g., a specific member's flight or daily commute).
"""

import sqlite3
import logging
from typing import Any, List, Dict, Optional
from datetime import datetime, date

from household import _get_conn, get_members

logger = logging.getLogger(__name__)

VALID_CATEGORIES = ["Energy", "Water", "Waste", "Food", "Transport", "Shopping", "Other"]

def init_activities_db() -> bool:
    """Initialize the household activities tables."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS household_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER NOT NULL,
                member_id INTEGER, -- NULL means shared activity
                category TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                impact_kg_co2 REAL NOT NULL DEFAULT 0.0,
                activity_date DATE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES household_members(id) ON DELETE SET NULL
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_hh_activities_household 
            ON household_activities(household_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_hh_activities_date
            ON household_activities(activity_date)
        ''')
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error initializing household_activities DB: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def log_activity(
    household_id: int,
    category: str,
    value: float,
    unit: str,
    impact_kg_co2: float,
    activity_date: str,
    description: str = "",
    member_id: Optional[int] = None
) -> Optional[int]:
    """Log a new activity for a household or a specific member.
    
    Args:
        household_id: ID of the household.
        category: Sustainability category (e.g. Energy, Transport).
        value: The raw value (e.g. 500 for 500 kWh).
        unit: Unit of measurement.
        impact_kg_co2: The calculated carbon footprint of the activity.
        activity_date: Date string in YYYY-MM-DD format.
        description: Optional description.
        member_id: Optional member ID if this is an individual activity.
    
    Returns:
        The ID of the newly created activity, or None on failure.
    """
    if category not in VALID_CATEGORIES:
        logger.error(f"Invalid category: {category}")
        return None
        
    if value < 0:
        logger.error("Activity value cannot be negative.")
        return None
        
    try:
        # Validate date format
        datetime.strptime(activity_date, "%Y-%m-%d")
    except ValueError:
        logger.error("Invalid activity_date format. Use YYYY-MM-DD.")
        return None

    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        # Verify household exists
        cursor.execute("SELECT id FROM households WHERE id = ?", (household_id,))
        if not cursor.fetchone():
            logger.error(f"Household {household_id} does not exist.")
            return None
            
        # Verify member belongs to household if provided
        if member_id is not None:
            cursor.execute("SELECT id FROM household_members WHERE id = ? AND household_id = ?", 
                           (member_id, household_id))
            if not cursor.fetchone():
                logger.error(f"Member {member_id} does not belong to household {household_id}.")
                return None
        
        cursor.execute('''
            INSERT INTO household_activities 
            (household_id, member_id, category, value, unit, impact_kg_co2, activity_date, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (household_id, member_id, category, value, unit, impact_kg_co2, activity_date, description))
        
        activity_id = cursor.lastrowid
        conn.commit()
        return activity_id
    except sqlite3.Error as e:
        logger.error(f"Database error logging activity: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_activities(
    household_id: int, 
    member_id: Optional[int] = None, 
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieve activities based on filters.
    
    Args:
        household_id: Required household ID.
        member_id: Optional member ID (filter by member, or use -1 to force shared only).
        category: Optional category filter.
        start_date: Optional start date (inclusive).
        end_date: Optional end date (inclusive).
        limit: Max results.
        offset: Pagination offset.
        
    Returns:
        List of activity dictionaries.
    """
    query = '''
        SELECT a.id, a.household_id, a.member_id, a.category, a.value, a.unit, 
               a.impact_kg_co2, a.activity_date, a.description, a.created_at, m.name as member_name
        FROM household_activities a
        LEFT JOIN household_members m ON a.member_id = m.id
        WHERE a.household_id = ?
    '''
    params: List[Any] = [household_id]
    
    if member_id == -1:
        query += " AND a.member_id IS NULL"
    elif member_id is not None:
        query += " AND a.member_id = ?"
        params.append(member_id)
        
    if category:
        query += " AND a.category = ?"
        params.append(category)
        
    if start_date:
        query += " AND a.activity_date >= ?"
        params.append(start_date)
        
    if end_date:
        query += " AND a.activity_date <= ?"
        params.append(end_date)
        
    query += " ORDER BY a.activity_date DESC, a.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Database error getting activities: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_activity_by_id(activity_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single activity by ID."""
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, a.household_id, a.member_id, a.category, a.value, a.unit, 
                   a.impact_kg_co2, a.activity_date, a.description, a.created_at, m.name as member_name
            FROM household_activities a
            LEFT JOIN household_members m ON a.member_id = m.id
            WHERE a.id = ?
        ''', (activity_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching activity {activity_id}: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def update_activity(
    activity_id: int,
    category: Optional[str] = None,
    value: Optional[float] = None,
    unit: Optional[str] = None,
    impact_kg_co2: Optional[float] = None,
    activity_date: Optional[str] = None,
    description: Optional[str] = None,
    member_id: Optional[int] = None,
    is_shared: bool = False
) -> bool:
    """Update an existing activity.
    
    Args:
        activity_id: ID of activity to update.
        category: New category.
        value: New value.
        unit: New unit.
        impact_kg_co2: New impact.
        activity_date: New date.
        description: New description.
        member_id: New member ID.
        is_shared: If true, sets member_id to NULL.
    """
    updates = []
    params: List[Any] = []
    
    if category is not None:
        if category not in VALID_CATEGORIES:
            logger.error(f"Invalid category: {category}")
            return False
        updates.append("category = ?")
        params.append(category)
        
    if value is not None:
        if value < 0:
            logger.error("Value cannot be negative.")
            return False
        updates.append("value = ?")
        params.append(value)
        
    if unit is not None:
        updates.append("unit = ?")
        params.append(unit)
        
    if impact_kg_co2 is not None:
        updates.append("impact_kg_co2 = ?")
        params.append(impact_kg_co2)
        
    if activity_date is not None:
        try:
            datetime.strptime(activity_date, "%Y-%m-%d")
            updates.append("activity_date = ?")
            params.append(activity_date)
        except ValueError:
            logger.error("Invalid activity_date format.")
            return False
            
    if description is not None:
        updates.append("description = ?")
        params.append(description)
        
    if is_shared:
        updates.append("member_id = NULL")
    elif member_id is not None:
        updates.append("member_id = ?")
        params.append(member_id)
        
    if not updates:
        return True
        
    updates.append("updated_at = CURRENT_TIMESTAMP")
    query = f"UPDATE household_activities SET {', '.join(updates)} WHERE id = ?"
    params.append(activity_id)
    
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        if member_id is not None and not is_shared:
            # Verify member exists and belongs to same household
            cursor.execute('''
                SELECT h.id FROM household_activities a
                JOIN household_members m ON m.household_id = a.household_id
                WHERE a.id = ? AND m.id = ?
            ''', (activity_id, member_id))
            if not cursor.fetchone():
                logger.error("Member does not belong to the activity's household.")
                return False
                
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error updating activity {activity_id}: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def delete_activity(activity_id: int) -> bool:
    """Delete an activity."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM household_activities WHERE id = ?", (activity_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error deleting activity {activity_id}: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_category_breakdown(household_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, float]:
    """Get total footprint aggregated by category."""
    query = '''
        SELECT category, SUM(impact_kg_co2) as total_impact
        FROM household_activities
        WHERE household_id = ?
    '''
    params: List[Any] = [household_id]
    
    if start_date:
        query += " AND activity_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND activity_date <= ?"
        params.append(end_date)
        
    query += " GROUP BY category"
    
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        breakdown = {cat: 0.0 for cat in VALID_CATEGORIES}
        for row in rows:
            breakdown[row[0]] = float(row[1] or 0.0)
        return breakdown
    except sqlite3.Error as e:
        logger.error(f"Error getting category breakdown: {e}")
        return {cat: 0.0 for cat in VALID_CATEGORIES}
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_member_contribution_breakdown(household_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """Calculate the contribution breakdown mapping shared and individual footprints."""
    # Base structure
    result = {
        "shared_total": 0.0,
        "members": {},       # member_id -> {"name": str, "individual": float, "allocated": float, "total": float}
        "household_total": 0.0
    }
    
    members = get_members(household_id)
    
    if members:
        for m in members:
            result["members"][m["id"]] = {
                "name": m["name"],
                "individual": 0.0,
                "allocated": 0.0,
                "total": 0.0,
                "weight": m.get("weight", 1.0)
            }
        
    query = '''
        SELECT member_id, SUM(impact_kg_co2) as total_impact
        FROM household_activities
        WHERE household_id = ?
    '''
    params: List[Any] = [household_id]
    
    if start_date:
        query += " AND activity_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND activity_date <= ?"
        params.append(end_date)
        
    query += " GROUP BY member_id"
    
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        shared_impact = 0.0
        for row in rows:
            m_id = row[0]
            impact = float(row[1] or 0.0)
            
            if m_id is None or m_id not in result["members"]:
                shared_impact += impact
            else:
                result["members"][m_id]["individual"] += impact
                
        result["shared_total"] = shared_impact
        
        # Calculate allocation (simplified equal weight logic as fallback, but use weights if available)
        total_weight = sum(m["weight"] for m in result["members"].values())
        if total_weight > 0:
            for m_id, m_data in result["members"].items():
                alloc_share = (m_data["weight"] / total_weight) * shared_impact
                m_data["allocated"] = alloc_share
                m_data["total"] = m_data["individual"] + alloc_share
        
        result["household_total"] = sum(m["total"] for m in result["members"].values())
        return result
        
    except sqlite3.Error as e:
        logger.error(f"Error computing member breakdown: {e}")
        return result
    finally:
        if 'conn' in locals() and conn:
            conn.close()
