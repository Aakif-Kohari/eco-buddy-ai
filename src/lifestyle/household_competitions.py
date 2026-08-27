"""Household Competitions and Leaderboards.

Provides the logic to pit households against each other in friendly
sustainability competitions (e.g., "Lowest Energy Footprint this Month").
"""

import sqlite3
import logging
from typing import Any, List, Dict, Optional
from datetime import datetime

from src.lifestyle.household import _get_conn
from src.lifestyle.household_activities import get_category_breakdown

logger = logging.getLogger(__name__)

def init_competitions_db() -> bool:
    """Initialize the household competitions tables."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS household_competitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                metric_category TEXT NOT NULL, -- e.g., 'Energy', 'Transport', or 'Overall'
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                status TEXT NOT NULL DEFAULT 'active', -- 'upcoming', 'active', 'completed'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competition_participants (
                competition_id INTEGER NOT NULL,
                household_id INTEGER NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (competition_id, household_id),
                FOREIGN KEY (competition_id) REFERENCES household_competitions(id) ON DELETE CASCADE,
                FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error initializing competitions DB: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def create_competition(
    title: str,
    description: str,
    metric_category: str,
    start_date: str,
    end_date: str
) -> Optional[int]:
    """Create a new neighborhood/community competition."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        # Simple status logic based on date
        today = datetime.now().strftime("%Y-%m-%d")
        status = 'active'
        if start_date > today:
            status = 'upcoming'
        elif end_date < today:
            status = 'completed'
            
        cursor.execute('''
            INSERT INTO household_competitions 
            (title, description, metric_category, start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, description, metric_category, start_date, end_date, status))
        
        comp_id = cursor.lastrowid
        conn.commit()
        return comp_id
    except sqlite3.Error as e:
        logger.error(f"Database error creating competition: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def join_competition(competition_id: int, household_id: int) -> bool:
    """Enroll a household into a competition."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM households WHERE id = ?", (household_id,))
        if not cursor.fetchone():
            return False
            
        cursor.execute("SELECT id FROM household_competitions WHERE id = ?", (competition_id,))
        if not cursor.fetchone():
            return False
            
        cursor.execute('''
            INSERT OR IGNORE INTO competition_participants (competition_id, household_id)
            VALUES (?, ?)
        ''', (competition_id, household_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error joining competition: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_active_competitions() -> List[Dict[str, Any]]:
    """Get all active or upcoming competitions."""
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM household_competitions WHERE status != 'completed' ORDER BY start_date ASC")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error getting competitions: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_competition_leaderboard(competition_id: int) -> List[Dict[str, Any]]:
    """Calculate and return the leaderboard for a competition.
    
    Lowest footprint wins.
    """
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM household_competitions WHERE id = ?", (competition_id,))
        comp = cursor.fetchone()
        if not comp:
            return []
            
        cat = comp['metric_category']
        start_d = comp['start_date']
        end_d = comp['end_date']
        
        cursor.execute('''
            SELECT h.id, h.name 
            FROM competition_participants p
            JOIN households h ON p.household_id = h.id
            WHERE p.competition_id = ?
        ''', (competition_id,))
        
        participants = cursor.fetchall()
        
        leaderboard = []
        for p in participants:
            hh_id = p['id']
            # Fetch breakdown for that period
            brk = get_category_breakdown(hh_id, start_date=start_d, end_date=end_d)
            if cat == 'Overall':
                score = sum(brk.values())
            else:
                score = brk.get(cat, 0.0)
                
            leaderboard.append({
                "household_id": hh_id,
                "household_name": p['name'],
                "score": score
            })
            
        # Sort lowest to highest
        leaderboard.sort(key=lambda x: x['score'])
        
        # Add ranks
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1
            
        return leaderboard
    except sqlite3.Error as e:
        logger.error(f"Error generating leaderboard: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()
