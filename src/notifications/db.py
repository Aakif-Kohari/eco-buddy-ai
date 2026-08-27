"""
Notification Database Engine.

Provides an isolated, robust interface for managing notifications, templates,
and preferences within the SQLite database.
"""

import sqlite3
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from database import DB_NAME
import sqlite3
def get_connection():
    return sqlite3.connect(DB_NAME)
from src.notifications.models import NotificationPreference, NotificationPayload

logger = logging.getLogger(__name__)

class NotificationDB:
    """Encapsulates all database operations for the notification engine."""
    
    def __init__(self, db_path: str = DB_NAME):
        self.db_path = db_path
        self._init_tables()
        
    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
        
    def _init_tables(self):
        """Creates required tables if they don't exist."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Preferences
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    user_id INTEGER PRIMARY KEY,
                    email_enabled BOOLEAN DEFAULT 1,
                    in_app_enabled BOOLEAN DEFAULT 1,
                    push_enabled BOOLEAN DEFAULT 0,
                    quiet_hours_start TEXT,
                    quiet_hours_end TEXT,
                    timezone TEXT DEFAULT 'UTC',
                    opted_out_categories TEXT DEFAULT '[]',
                    daily_digest_enabled BOOLEAN DEFAULT 0,
                    weekly_digest_enabled BOOLEAN DEFAULT 1
                )
            ''')
            
            # Notifications
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    priority TEXT DEFAULT 'normal',
                    status TEXT DEFAULT 'pending',
                    action_url TEXT,
                    icon TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    scheduled_for TEXT,
                    sent_at TEXT,
                    read_at TEXT,
                    expires_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    error_log TEXT,
                    dedupe_key TEXT
                )
            ''')
            
            # Indexes for quick polling and history lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_dedupe ON notifications(dedupe_key)')
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error initializing notification tables: {e}")
        finally:
            if conn:
                conn.close()

    def get_preferences(self, user_id: int) -> NotificationPreference:
        """Retrieves or creates default preferences for a user."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                cols = [col[0] for col in cursor.description]
                data = dict(zip(cols, row))
                data["opted_out_categories"] = json.loads(data.get("opted_out_categories", "[]"))
                return NotificationPreference.from_dict(data)
            
            # Create default
            pref = NotificationPreference(user_id=user_id)
            self.save_preferences(pref)
            return pref
            
        except sqlite3.Error as e:
            logger.error(f"Error getting preferences for {user_id}: {e}")
            return NotificationPreference(user_id=user_id)
        finally:
            if conn:
                conn.close()

    def save_preferences(self, pref: NotificationPreference) -> bool:
        """Saves a user's notification preferences."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            data = pref.to_dict()
            cursor.execute('''
                INSERT OR REPLACE INTO notification_preferences 
                (user_id, email_enabled, in_app_enabled, push_enabled, 
                 quiet_hours_start, quiet_hours_end, timezone, 
                 opted_out_categories, daily_digest_enabled, weekly_digest_enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['user_id'], data['email_enabled'], data['in_app_enabled'], data['push_enabled'],
                data['quiet_hours_start'], data['quiet_hours_end'], data['timezone'],
                json.dumps(data['opted_out_categories']), data['daily_digest_enabled'], data['weekly_digest_enabled']
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error saving preferences for {pref.user_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def insert_notification(self, payload: NotificationPayload) -> bool:
        """Inserts a new notification into the database."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications 
                (id, user_id, category, title, message, priority, status, action_url, icon, 
                 metadata, created_at, scheduled_for, sent_at, read_at, expires_at, 
                 retry_count, error_log, dedupe_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', payload.to_db_tuple())
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error inserting notification {payload.id}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_pending_notifications(self, limit: int = 100) -> List[NotificationPayload]:
        """Retrieves pending notifications ready for delivery."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            now_iso = datetime.utcnow().isoformat()
            
            cursor.execute('''
                SELECT * FROM notifications 
                WHERE status = 'pending' 
                  AND (scheduled_for IS NULL OR scheduled_for <= ?)
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
            ''', (now_iso, limit))
            
            rows = cursor.fetchall()
            return [NotificationPayload.from_db_row(r) for r in rows]
        except sqlite3.Error as e:
            logger.error(f"Error fetching pending notifications: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def update_notification_status(self, notif_id: str, status: str, 
                                   error_log: Optional[str] = None, 
                                   retry_count: Optional[int] = None) -> bool:
        """Updates the status and metadata of a notification."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            now_iso = datetime.utcnow().isoformat()
            
            updates = ["status = ?"]
            params = [status]
            
            if status == "sent":
                updates.append("sent_at = ?")
                params.append(now_iso)
            elif status == "read":
                updates.append("read_at = ?")
                params.append(now_iso)
                
            if error_log is not None:
                updates.append("error_log = ?")
                params.append(error_log)
                
            if retry_count is not None:
                updates.append("retry_count = ?")
                params.append(retry_count)
                
            params.append(notif_id)
            query = f"UPDATE notifications SET {', '.join(updates)} WHERE id = ?"
            
            cursor.execute(query, tuple(params))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating notification {notif_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_user_history(self, user_id: int, limit: int = 50, offset: int = 0, unread_only: bool = False) -> List[NotificationPayload]:
        """Gets a user's notification history for in-app display."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            query = "SELECT * FROM notifications WHERE user_id = ? AND status IN ('sent', 'read', 'pending')"
            params = [user_id]
            
            if unread_only:
                query += " AND status = 'sent' AND read_at IS NULL"
                
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, tuple(params))
            return [NotificationPayload.from_db_row(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching history for user {user_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def check_dedupe_exists(self, user_id: int, dedupe_key: str, window_hours: int = 24) -> bool:
        """Checks if a similar notification was already sent within the window to prevent spam."""
        if not dedupe_key:
            return False
            
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Since sqlite doesn't easily do datetime math on ISO strings without date(), 
            # we do a simple string comparison on a calculated threshold in Python.
            from datetime import timedelta
            threshold = (datetime.utcnow() - timedelta(hours=window_hours)).isoformat()
            
            cursor.execute('''
                SELECT 1 FROM notifications 
                WHERE user_id = ? AND dedupe_key = ? AND created_at >= ?
                LIMIT 1
            ''', (user_id, dedupe_key, threshold))
            
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Error checking dedupe key {dedupe_key}: {e}")
            return False
        finally:
            if conn:
                conn.close()
                
    def mark_all_read(self, user_id: int) -> bool:
        """Marks all unread notifications for a user as read."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            now_iso = datetime.utcnow().isoformat()
            
            cursor.execute('''
                UPDATE notifications 
                SET status = 'read', read_at = ? 
                WHERE user_id = ? AND status = 'sent' AND read_at IS NULL
            ''', (now_iso, user_id))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error marking all as read for user {user_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()
