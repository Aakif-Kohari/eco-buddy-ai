import time
import sqlite3
import os
from typing import Tuple, Dict, Any
from src.core.database_connection import database_connection

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

class CompositeRateLimiter:
    """
    Composite Rate Limiter using a Token Bucket for bursts and Sliding Window logging
    for sustained limits. Backed by SQLite for persistence.
    """

    @staticmethod
    def check_limit(key_id: int, rate_limit: int, endpoint: str) -> Tuple[bool, int, Dict[str, str]]:
        """
        Check if the request is allowed based on the rate limit.
        Uses Token Bucket: capacity = rate_limit, refill rate = rate_limit per hour.
        Returns: (is_allowed, status_code, headers)
        """
        if rate_limit <= 0:
            return False, 429, {"Retry-After": "3600"}

        capacity = rate_limit
        refill_rate_per_second = rate_limit / 3600.0  # Limit is typically per hour

        now = time.time()
        is_allowed = False
        retry_after = 0

        with database_connection(DB_NAME) as conn:
            # Need exclusive lock to update tokens reliably
            conn.execute("BEGIN EXCLUSIVE TRANSACTION")
            cursor = conn.cursor()

            cursor.execute("SELECT tokens, last_refill FROM rate_limit_buckets WHERE key_id = ?", (key_id,))
            row = cursor.fetchone()

            if not row:
                # Initialize bucket
                tokens = capacity - 1
                cursor.execute(
                    "INSERT INTO rate_limit_buckets (key_id, tokens, last_refill) VALUES (?, ?, ?)",
                    (key_id, tokens, now)
                )
                is_allowed = True
            else:
                tokens, last_refill = row
                
                # Calculate refill
                time_passed = now - last_refill
                new_tokens = time_passed * refill_rate_per_second
                
                tokens = min(capacity, tokens + new_tokens)

                if tokens >= 1:
                    tokens -= 1
                    cursor.execute(
                        "UPDATE rate_limit_buckets SET tokens = ?, last_refill = ? WHERE key_id = ?",
                        (tokens, now, key_id)
                    )
                    is_allowed = True
                else:
                    # Calculate time until 1 token is available
                    time_needed = (1 - tokens) / refill_rate_per_second
                    retry_after = max(1, int(time_needed))
                    is_allowed = False
                    
            # Always log the request
            status_code = 200 if is_allowed else 429
            cursor.execute(
                "INSERT INTO rate_limit_log (key_id, endpoint, timestamp, status_code) VALUES (?, ?, ?, ?)",
                (key_id, endpoint, now, status_code)
            )
            
            conn.commit()

        if is_allowed:
            return True, 200, {}
        else:
            return False, 429, {"Retry-After": str(retry_after)}

    @staticmethod
    def get_usage_stats(key_id: int = None, limit: int = 100) -> list:
        """Fetch rate limit logs, optionally filtered by key_id."""
        with database_connection(DB_NAME) as conn:
            cursor = conn.cursor()
            if key_id:
                cursor.execute(
                    "SELECT timestamp, endpoint, status_code FROM rate_limit_log WHERE key_id = ? ORDER BY timestamp DESC LIMIT ?", 
                    (key_id, limit)
                )
            else:
                cursor.execute(
                    "SELECT key_id, timestamp, endpoint, status_code FROM rate_limit_log ORDER BY timestamp DESC LIMIT ?", 
                    (limit,)
                )
            
            rows = cursor.fetchall()
            
            if key_id:
                return [{"timestamp": r[0], "endpoint": r[1], "status_code": r[2]} for r in rows]
            else:
                return [{"key_id": r[0], "timestamp": r[1], "endpoint": r[2], "status_code": r[3]} for r in rows]
