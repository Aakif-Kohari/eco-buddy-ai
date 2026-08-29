"""
Notification Dispatcher.

Handles the logic of determining IF a notification should be sent based on 
user preferences, quiet hours, and deduplication rules, and then routes it.
"""

import logging
from datetime import datetime, time
from datetime import timezone, timedelta
from typing import Optional, Dict, Any, Tuple

from src.notifications.models import NotificationPayload, NotificationPreference
from src.notifications.db import NotificationDB

logger = logging.getLogger(__name__)

class NotificationDispatcher:
    """Core logic engine for validating and routing notifications."""
    
    def __init__(self, db: Optional[NotificationDB] = None):
        self.db = db or NotificationDB()
        
    def _is_quiet_hours(self, pref: NotificationPreference) -> Tuple[bool, Optional[datetime]]:
        """
        Determines if the current time is within the user's configured quiet hours.
        Returns a tuple: (is_quiet, next_available_time_utc).
        """
        if not pref.quiet_hours_start or not pref.quiet_hours_end:
            return False, None
            
        # Fallback to simple UTC for standard python without pytz
        now_utc = datetime.utcnow()
        now_local = now_utc
        current_time = now_local.time()
        
        start = pref.quiet_hours_start
        end = pref.quiet_hours_end
        
        is_quiet = False
        if start <= end:
            is_quiet = start <= current_time <= end
        else:
            # Spans midnight
            is_quiet = current_time >= start or current_time <= end
            
        if not is_quiet:
            return False, None
            
        # Calculate when quiet hours end to schedule the notification
        # This requires some date math in the local timezone
        target_local = now_local.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
        if current_time > end:
            # The end time is on the next day
            from datetime import timedelta
            target_local += timedelta(days=1)
            
        # Convert back to UTC for database storage
        target_utc = target_local
        return True, target_utc

    def dispatch(self, user_id: int, category: str, title: str, message: str, 
                 priority: str = "normal", action_url: Optional[str] = None, 
                 icon: str = "🔔", metadata: Optional[Dict[str, Any]] = None,
                 dedupe_key: Optional[str] = None) -> Optional[str]:
        """
        Validates preferences and queues a notification for delivery.
        Returns the notification ID if queued, or None if suppressed.
        """
        pref = self.db.get_preferences(user_id)
        
        # 1. Opt-out check
        if category in pref.opted_out_categories:
            logger.info(f"User {user_id} opted out of {category}. Suppressing.")
            return None
            
        if not pref.in_app_enabled and not pref.email_enabled:
            logger.info(f"User {user_id} has disabled all notifications. Suppressing.")
            return None
            
        # 2. Deduplication check
        if dedupe_key:
            if self.db.check_dedupe_exists(user_id, dedupe_key, window_hours=24):
                logger.info(f"Duplicate notification {dedupe_key} for user {user_id}. Suppressing.")
                return None
                
        # 3. Quiet Hours Check
        scheduled_for = None
        # Urgent priority bypasses quiet hours
        if priority != "urgent":
            is_quiet, next_time = self._is_quiet_hours(pref)
            if is_quiet:
                logger.info(f"User {user_id} is in quiet hours. Deferring to {next_time}.")
                scheduled_for = next_time
                
        # 4. Build payload and insert
        payload = NotificationPayload(
            user_id=user_id,
            category=category,
            title=title,
            message=message,
            priority=priority,
            action_url=action_url,
            icon=icon,
            metadata=metadata or {},
            scheduled_for=scheduled_for,
            dedupe_key=dedupe_key
        )
        
        if self.db.insert_notification(payload):
            return payload.id
        return None

    def process_queue(self):
        """
        Processes pending notifications. In a real environment, this runs in a worker.
        For Streamlit, we might call this opportunistically or via a background thread.
        """
        pending = self.db.get_pending_notifications(limit=50)
        
        for notif in pending:
            try:
                # Simulate Delivery (Email / Push / WebSocket)
                # In this system, 'sent' implies it's available in the in-app inbox
                # and any external deliveries (like email) have been fired.
                
                # ... (Mock email delivery logic here) ...
                
                self.db.update_notification_status(notif.id, "sent")
                logger.info(f"Successfully delivered notification {notif.id}")
            except Exception as e:
                logger.error(f"Failed to deliver notification {notif.id}: {e}")
                
                # Retry logic
                new_retry = notif.retry_count + 1
                if new_retry >= 3:
                    self.db.update_notification_status(notif.id, "failed", error_log=str(e), retry_count=new_retry)
                else:
                    # Exponential backoff (simulated by updating retry count and leaving as pending)
                    # For simplicity, we just increment retry count. A real system would adjust scheduled_for
                    from datetime import timedelta
                    backoff = datetime.utcnow() + timedelta(minutes=5 ** new_retry)
                    # We need to manually run an update query to change scheduled_for here
                    # To keep it simple, we use the db method and a custom query inside it
                    # (Skipped complex backoff scheduling for brevity, handled by retry_handler)
                    self.db.update_notification_status(notif.id, "pending", error_log=str(e), retry_count=new_retry)
                    
                    conn = self.db._get_conn()
                    conn.execute("UPDATE notifications SET scheduled_for = ? WHERE id = ?", (backoff.isoformat(), notif.id))
                    conn.commit()
                    conn.close()
