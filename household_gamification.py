"""Household Gamification and Collective Challenges.

This module provides systems for households to earn collective XP,
unlock team badges, and participate in sustainability challenges.
"""

import sqlite3
import logging
from typing import Any, List, Dict, Optional
from datetime import datetime

from household import _get_conn

logger = logging.getLogger(__name__)

def init_household_gamification_db() -> bool:
    """Initialize the household gamification tables."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS household_xp (
                household_id INTEGER PRIMARY KEY,
                total_xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS household_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER NOT NULL,
                badge_name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                earned_date DATE NOT NULL,
                FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS household_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                xp_reward INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active', -- 'active', 'completed', 'failed'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error initializing household_gamification DB: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def award_household_xp(household_id: int, xp_amount: int) -> Dict[str, Any]:
    """Award XP to a household and handle potential level ups."""
    if xp_amount <= 0:
        return _get_household_xp(household_id)
        
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        # Ensure row exists
        cursor.execute("INSERT OR IGNORE INTO household_xp (household_id, total_xp, level) VALUES (?, 0, 1)", (household_id,))
        
        cursor.execute("SELECT total_xp, level FROM household_xp WHERE household_id = ?", (household_id,))
        row = cursor.fetchone()
        
        current_xp = row[0] + xp_amount
        current_level = row[1]
        
        # Simple leveling formula: Level = sqrt(XP / 100) + 1
        import math
        new_level = max(1, int(math.sqrt(current_xp / 100)) + 1)
        
        cursor.execute('''
            UPDATE household_xp 
            SET total_xp = ?, level = ? 
            WHERE household_id = ?
        ''', (current_xp, new_level, household_id))
        
        conn.commit()
        return {
            "total_xp": current_xp,
            "level": new_level,
            "leveled_up": new_level > current_level
        }
    except sqlite3.Error as e:
        logger.error(f"Error awarding household XP: {e}")
        return {"total_xp": 0, "level": 1, "leveled_up": False}
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def _get_household_xp(household_id: int) -> Dict[str, Any]:
    """Get current XP and Level for a household."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT total_xp, level FROM household_xp WHERE household_id = ?", (household_id,))
        row = cursor.fetchone()
        if row:
            return {"total_xp": row[0], "level": row[1], "leveled_up": False}
        return {"total_xp": 0, "level": 1, "leveled_up": False}
    except sqlite3.Error as e:
        logger.error(f"Error getting household XP: {e}")
        return {"total_xp": 0, "level": 1, "leveled_up": False}
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def award_badge(household_id: int, badge_name: str, description: str, icon: str = "🏆") -> bool:
    """Award a collective badge to the household."""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        # Check if they already have it
        cursor.execute("SELECT id FROM household_badges WHERE household_id = ? AND badge_name = ?", (household_id, badge_name))
        if cursor.fetchone():
            return False
            
        cursor.execute('''
            INSERT INTO household_badges (household_id, badge_name, description, icon, earned_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (household_id, badge_name, description, icon, today))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error awarding household badge: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_badges(household_id: int) -> List[Dict[str, Any]]:
    """Retrieve all badges earned by a household."""
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM household_badges WHERE household_id = ? ORDER BY earned_date DESC", (household_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error fetching household badges: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def create_challenge(household_id: int, title: str, description: str, xp_reward: int) -> Optional[int]:
    """Create a new household collective challenge."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO household_challenges (household_id, title, description, xp_reward)
            VALUES (?, ?, ?, ?)
        ''', (household_id, title, description, xp_reward))
        challenge_id = cursor.lastrowid
        conn.commit()
        return challenge_id
    except sqlite3.Error as e:
        logger.error(f"Error creating household challenge: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def complete_challenge(challenge_id: int) -> bool:
    """Mark a challenge as completed and award the XP to the household."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        # Get challenge info
        cursor.execute("SELECT household_id, xp_reward, status FROM household_challenges WHERE id = ?", (challenge_id,))
        row = cursor.fetchone()
        if not row or row[2] != 'active':
            return False
            
        hh_id, xp, _ = row
        
        # Mark complete
        cursor.execute('''
            UPDATE household_challenges 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (challenge_id,))
        
        conn.commit()
        
        # Award XP
        award_household_xp(hh_id, xp)
        return True
    except sqlite3.Error as e:
        logger.error(f"Error completing household challenge: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_challenges(household_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get challenges for a household."""
    query = "SELECT * FROM household_challenges WHERE household_id = ?"
    params: List[Any] = [household_id]
    
    if status:
        query += " AND status = ?"
        params.append(status)
        
    query += " ORDER BY created_at DESC"
    
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error fetching household challenges: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()
