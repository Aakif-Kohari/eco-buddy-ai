import os
import sqlite3
import logging
import datetime
from typing import Any, Dict, List, Optional, Union

from src.utils.goals import (
    create_goal,
    evaluate_progress,
    _coerce_date,
    GOAL_ACTIVE,
    GOAL_COMPLETED,
    GOAL_ARCHIVED
)
from src.lifestyle.household import get_household, get_members

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

GOAL_PENDING = "pending"

def _get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_NAME)

def init_collaborative_db() -> bool:
    """Create the collaborative goals tables if they do not exist yet."""
    conn = None
    try:
        conn = _get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS collaborative_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER NOT NULL,
                proposer_user_id INTEGER NOT NULL,
                baseline_kg REAL NOT NULL,
                target_kg REAL NOT NULL,
                start_date DATE NOT NULL,
                target_date DATE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                allocation_strategy TEXT NOT NULL DEFAULT 'proportional',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS goal_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                vote TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(goal_id, user_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS goal_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                allocated_target_kg REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(goal_id, member_id)
            )
            """
        )
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Collaborative Goal init error: %s", exc)
        return False
    finally:
        if conn:
            conn.close()

def propose_goal(
    household_id: int, 
    proposer_user_id: int, 
    baseline_kg: float, 
    target_kg: float, 
    start_date: Union[str, datetime.date], 
    target_date: Union[str, datetime.date],
    allocation_strategy: str = "proportional"
) -> Optional[int]:
    """Propose a new collaborative goal for a household."""
    init_collaborative_db()
    
    start_date_str = _coerce_date(start_date, "start_date").isoformat()
    target_date_str = _coerce_date(target_date, "target_date").isoformat()
    
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.execute(
            """
            INSERT INTO collaborative_goals 
            (household_id, proposer_user_id, baseline_kg, target_kg, start_date, target_date, status, allocation_strategy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (household_id, proposer_user_id, baseline_kg, target_kg, start_date_str, target_date_str, GOAL_PENDING, allocation_strategy)
        )
        goal_id = cursor.lastrowid
        conn.commit()
        
        # Auto-approve for the proposer
        vote_on_proposal(goal_id, proposer_user_id, "approve")
        
        return goal_id
    except sqlite3.Error as exc:
        logger.error("Error proposing goal: %s", exc)
        return None
    finally:
        if conn:
            conn.close()

def vote_on_proposal(goal_id: int, user_id: int, vote: str) -> bool:
    """Record a user's vote on a proposal (approve/reject)."""
    init_collaborative_db()
    if vote not in ("approve", "reject"):
        return False
        
    conn = None
    try:
        conn = _get_conn()
        conn.execute(
            """
            INSERT INTO goal_votes (goal_id, user_id, vote)
            VALUES (?, ?, ?)
            ON CONFLICT(goal_id, user_id) DO UPDATE SET vote = excluded.vote
            """,
            (goal_id, user_id, vote)
        )
        conn.commit()
        
        # Check if we should activate the goal
        tally_votes(goal_id)
        
        return True
    except sqlite3.Error as exc:
        logger.error("Error voting on proposal: %s", exc)
        return False
    finally:
        if conn:
            conn.close()

def tally_votes(goal_id: int) -> bool:
    """Check if the goal has a majority of approvals, and activate if so."""
    goal = get_goal(goal_id)
    if not goal or goal["status"] != GOAL_PENDING:
        return False
        
    household_id = goal["household_id"]
    members = get_members(household_id)
    if not members:
        return False
        
    # How many active users are in this household?
    voters = [m for m in members if m["user_id"] is not None]
    total_eligible = len(voters) if voters else len(members)
    
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.execute(
            "SELECT count(*) FROM goal_votes WHERE goal_id = ? AND vote = 'approve'",
            (goal_id,)
        )
        approvals = cursor.fetchone()[0]
        
        if approvals > total_eligible / 2:
            conn.execute(
                "UPDATE collaborative_goals SET status = ? WHERE id = ?",
                (GOAL_ACTIVE, goal_id)
            )
            conn.commit()
            _allocate_reductions(goal_id)
            return True
            
        return False
    except sqlite3.Error as exc:
        logger.error("Error tallying votes: %s", exc)
        return False
    finally:
        if conn:
            conn.close()

def _allocate_reductions(goal_id: int):
    """Dynamically allocate the target across members."""
    goal = get_goal(goal_id)
    if not goal:
        return
        
    members = get_members(goal["household_id"])
    if not members:
        return
        
    total_reduction = goal["baseline_kg"] - goal["target_kg"]
    
    # Distribute reductions
    conn = None
    try:
        conn = _get_conn()
        
        if goal["allocation_strategy"] == "proportional":
            total_weight = sum(m["weight"] for m in members)
            for member in members:
                share = (member["weight"] / total_weight) if total_weight > 0 else (1.0 / len(members))
                member_reduction = total_reduction * share
                member_target = max(0.0, (goal["baseline_kg"] * share) - member_reduction)
                
                conn.execute(
                    """
                    INSERT INTO goal_allocations (goal_id, member_id, allocated_target_kg)
                    VALUES (?, ?, ?)
                    ON CONFLICT(goal_id, member_id) DO UPDATE SET allocated_target_kg = excluded.allocated_target_kg
                    """,
                    (goal_id, member["id"], member_target)
                )
        else:
            split_reduction = total_reduction / len(members)
            for member in members:
                member_target = max(0.0, (goal["baseline_kg"] / len(members)) - split_reduction)
                conn.execute(
                    """
                    INSERT INTO goal_allocations (goal_id, member_id, allocated_target_kg)
                    VALUES (?, ?, ?)
                    ON CONFLICT(goal_id, member_id) DO UPDATE SET allocated_target_kg = excluded.allocated_target_kg
                    """,
                    (goal_id, member["id"], member_target)
                )
        conn.commit()
    except sqlite3.Error as exc:
        logger.error("Error allocating reductions: %s", exc)
    finally:
        if conn:
            conn.close()


def get_goal(goal_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a collaborative goal."""
    init_collaborative_db()
    conn = None
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM collaborative_goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            return None
        return dict(row)
    except sqlite3.Error as exc:
        logger.error("Error fetching goal: %s", exc)
        return None
    finally:
        if conn:
            conn.close()

def get_goals_for_household(household_id: int) -> List[Dict[str, Any]]:
    """Get all collaborative goals for a household."""
    init_collaborative_db()
    conn = None
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM collaborative_goals WHERE household_id = ? ORDER BY created_at DESC", 
            (household_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        logger.error("Error fetching household goals: %s", exc)
        return []
    finally:
        if conn:
            conn.close()

def get_votes_for_goal(goal_id: int) -> List[Dict[str, Any]]:
    init_collaborative_db()
    conn = None
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM goal_votes WHERE goal_id = ?", (goal_id,)).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        logger.error("Error fetching goal votes: %s", exc)
        return []
    finally:
        if conn:
            conn.close()

def get_allocations_for_goal(goal_id: int) -> Dict[int, float]:
    """Returns mapping of member_id to allocated_target_kg"""
    init_collaborative_db()
    conn = None
    try:
        conn = _get_conn()
        rows = conn.execute("SELECT member_id, allocated_target_kg FROM goal_allocations WHERE goal_id = ?", (goal_id,)).fetchall()
        return {row[0]: row[1] for row in rows}
    except sqlite3.Error as exc:
        logger.error("Error fetching goal allocations: %s", exc)
        return {}
    finally:
        if conn:
            conn.close()

def evaluate_household_progress(goal: Dict[str, Any], aggregated_assessments: List[Dict[str, Any]], as_of: Optional[Union[str, datetime.date]] = None) -> Dict[str, Any]:
    """
    Evaluates household progress by adapting the individual evaluate_progress function.
    The aggregated_assessments should represent the household's total footprint over time.
    """
    goal_dict = {
        "id": goal["id"],
        "user_id": None, # it's a household goal
        "baseline_kg": goal["baseline_kg"],
        "target_kg": goal["target_kg"],
        "start_date": goal["start_date"],
        "target_date": goal["target_date"],
        "status": goal["status"]
    }
    
    return evaluate_progress(goal_dict, aggregated_assessments, as_of)
