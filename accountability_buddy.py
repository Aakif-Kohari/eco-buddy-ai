import sqlite3
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from database_connection import database_connection

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

class BuddySystem:
    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with database_connection(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, username FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def send_buddy_request(self, sender_id: int, receiver_id: int) -> Tuple[bool, str]:
        if sender_id == receiver_id:
            return False, "You cannot send a buddy request to yourself."

        with database_connection(self.db_name) as conn:
            cursor = conn.cursor()
            # Check if they are already buddies
            cursor.execute("""
                SELECT id FROM buddy_pairs 
                WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
            """, (sender_id, receiver_id, receiver_id, sender_id))
            if cursor.fetchone():
                return False, "You are already buddies with this user."

            # Check if a pending request already exists
            cursor.execute("""
                SELECT id, status FROM buddy_requests 
                WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
                AND status = 'pending'
            """, (sender_id, receiver_id, receiver_id, sender_id))
            if cursor.fetchone():
                return False, "A pending request already exists between you and this user."

            # Create request
            cursor.execute("""
                INSERT INTO buddy_requests (sender_id, receiver_id, status) 
                VALUES (?, ?, 'pending')
            """, (sender_id, receiver_id))
            conn.commit()
            return True, "Buddy request sent."

    def accept_buddy_request(self, request_id: int) -> Tuple[bool, str]:
        with database_connection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sender_id, receiver_id, status FROM buddy_requests WHERE id = ?", (request_id,))
            req = cursor.fetchone()
            if not req or req[2] != 'pending':
                return False, "Request not found or not pending."
            
            sender_id, receiver_id = req[0], req[1]

            cursor.execute("UPDATE buddy_requests SET status = 'accepted' WHERE id = ?", (request_id,))
            cursor.execute("INSERT INTO buddy_pairs (user1_id, user2_id) VALUES (?, ?)", (sender_id, receiver_id))
            conn.commit()
            return True, "Buddy request accepted."

    def reject_buddy_request(self, request_id: int) -> Tuple[bool, str]:
        with database_connection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE buddy_requests SET status = 'rejected' WHERE id = ?", (request_id,))
            conn.commit()
            return True, "Buddy request rejected."

    def remove_buddy(self, user_id: int, buddy_id: int) -> Tuple[bool, str]:
        with database_connection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM buddy_pairs 
                WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
            """, (user_id, buddy_id, buddy_id, user_id))
            if cursor.rowcount > 0:
                conn.commit()
                return True, "Buddy removed."
            return False, "Buddy not found."

    def get_pending_requests(self, user_id: int) -> List[Dict[str, Any]]:
        with database_connection(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT br.id, br.sender_id, u.username as sender_name, br.created_at 
                FROM buddy_requests br
                JOIN users u ON br.sender_id = u.id
                WHERE br.receiver_id = ? AND br.status = 'pending'
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_buddies(self, user_id: int) -> List[Dict[str, Any]]:
        with database_connection(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT bp.id as pair_id, bp.synergy_score, u.id as buddy_id, u.username as buddy_name 
                FROM buddy_pairs bp
                JOIN users u ON (bp.user1_id = u.id OR bp.user2_id = u.id)
                WHERE (bp.user1_id = ? OR bp.user2_id = ?) AND u.id != ?
            """, (user_id, user_id, user_id))
            return [dict(row) for row in cursor.fetchall()]

    def send_nudge(self, sender_id: int, receiver_id: int, message: str) -> bool:
        with database_connection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO buddy_nudges (sender_id, receiver_id, message) 
                VALUES (?, ?, ?)
            """, (sender_id, receiver_id, message))
            conn.commit()
            return True

    def get_nudge_history(self, user1_id: int, user2_id: int) -> List[Dict[str, Any]]:
        with database_connection(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT n.id, n.sender_id, n.receiver_id, n.message, n.created_at, u.username as sender_name
                FROM buddy_nudges n
                JOIN users u ON n.sender_id = u.id
                WHERE (n.sender_id = ? AND n.receiver_id = ?) OR (n.sender_id = ? AND n.receiver_id = ?)
                ORDER BY n.created_at DESC
                LIMIT 50
            """, (user1_id, user2_id, user2_id, user1_id))
            return [dict(row) for row in cursor.fetchall()]

    def calculate_synergy_score(self, user1_id: int, user2_id: int) -> float:
        """
        Calculates a synergy score (0-100) based on shared activity or similar footprints.
        For simplicity, we'll assign a base score and add points based on nudges.
        """
        with database_connection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM buddy_nudges 
                WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            """, (user1_id, user2_id, user2_id, user1_id))
            nudge_count = cursor.fetchone()[0]

            score = min(100.0, 50.0 + (nudge_count * 5.0))
            
            cursor.execute("""
                UPDATE buddy_pairs SET synergy_score = ?
                WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
            """, (score, user1_id, user2_id, user2_id, user1_id))
            conn.commit()
            return score

    def get_buddy_comparison(self, user1_id: int, user2_id: int) -> Dict[str, Any]:
        """
        Aggregates stats for comparison. We will attempt to get their total footprints.
        """
        user1_fp = self._get_user_footprint_total(user1_id)
        user2_fp = self._get_user_footprint_total(user2_id)
        synergy = self.calculate_synergy_score(user1_id, user2_id)
        
        return {
            "user1": {"id": user1_id, "total_footprint": user1_fp},
            "user2": {"id": user2_id, "total_footprint": user2_fp},
            "synergy_score": synergy
        }

    def _get_user_footprint_total(self, user_id: int) -> float:
        try:
            with database_connection(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(total_kg) FROM assessments WHERE user_id = ?", (user_id,))
                res = cursor.fetchone()
                return float(res[0]) if res and res[0] is not None else 0.0
        except Exception as e:
            logger.error(f"Error fetching footprint for user {user_id}: {e}")
            return 0.0
