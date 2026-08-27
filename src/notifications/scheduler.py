"""
Notification Scheduler.

Handles recurring background tasks such as generating weekly digests and 
evaluating goal/milestone reminders.
"""

import logging
from datetime import datetime, timedelta
import sqlite3
from typing import Optional

from src.core.database import DB_NAME
import sqlite3
def get_connection():
    return sqlite3.connect(DB_NAME)
from src.notifications.dispatcher import NotificationDispatcher

logger = logging.getLogger(__name__)

class NotificationScheduler:
    """Evaluates the state of the app to trigger reminders and digests."""
    
    def __init__(self, dispatcher: Optional[NotificationDispatcher] = None):
        self.dispatcher = dispatcher or NotificationDispatcher()
        
    def generate_weekly_digests(self):
        """
        Scans for users who have weekly digests enabled and haven't received 
        one in the past 7 days.
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            # Find users with weekly digest enabled
            cursor.execute("SELECT user_id FROM notification_preferences WHERE weekly_digest_enabled = 1")
            users = cursor.fetchall()
            
            for (user_id,) in users:
                # Check if we already sent a digest recently
                dedupe_key = f"weekly_digest_{datetime.utcnow().isocalendar()[1]}_{datetime.utcnow().year}"
                
                # We use the dispatcher which handles dedupe, but we can also pre-check to save DB hits
                # In this mock, we just generate the digest payload.
                
                # Fetch some stats for the digest (mock logic interacting with core DB)
                cursor.execute("SELECT COUNT(*) FROM user_activities WHERE user_id = ? AND date >= date('now', '-7 days')", (user_id,))
                activities_count = cursor.fetchone()[0]
                
                if activities_count == 0:
                    continue  # Skip empty weeks
                    
                body = f"You logged {activities_count} sustainable activities this week! Keep up the great work."
                
                self.dispatcher.dispatch(
                    user_id=user_id,
                    category="digest",
                    title="Your Weekly Sustainability Digest 🌱",
                    message=body,
                    priority="low",
                    icon="📊",
                    dedupe_key=dedupe_key
                )
                
        except sqlite3.Error as e:
            logger.error(f"Error generating digests: {e}")
        finally:
            conn.close()

    def check_goal_reminders(self):
        """
        Scans for goals that are due soon and triggers reminders.
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            # Note: Assuming 'goals' table exists based on core app logic.
            # Using safe defensive queries just in case schema differs slightly.
            cursor.execute('''
                SELECT id, user_id, title, target_date 
                FROM goals 
                WHERE status != 'completed' 
                  AND target_date IS NOT NULL
            ''')
            goals = cursor.fetchall()
            
            now = datetime.utcnow()
            for goal_id, user_id, title, target_date_str in goals:
                try:
                    # Some dates might be ISO, some might be YYYY-MM-DD
                    if len(target_date_str) == 10:
                        target = datetime.strptime(target_date_str, "%Y-%m-%d")
                    else:
                        target = datetime.fromisoformat(target_date_str)
                        
                    days_left = (target.date() - now.date()).days
                    
                    if days_left == 3:
                        self.dispatcher.dispatch(
                            user_id=user_id,
                            category="goals",
                            title="Goal Deadline Approaching!",
                            message=f"Your goal '{title}' is due in 3 days. Can you make it?",
                            priority="high",
                            icon="🎯",
                            dedupe_key=f"goal_{goal_id}_3days"
                        )
                    elif days_left == 0:
                        self.dispatcher.dispatch(
                            user_id=user_id,
                            category="goals",
                            title="Goal Due Today!",
                            message=f"Today is the deadline for '{title}'. Update your progress now!",
                            priority="high",
                            icon="🚨",
                            dedupe_key=f"goal_{goal_id}_0days"
                        )
                except Exception as e:
                    logger.warning(f"Error parsing date for goal {goal_id}: {e}")
                    
        except sqlite3.OperationalError:
            # Table might not exist in some mocked environments
            logger.info("Goals table not found, skipping goal reminders.")
        except Exception as e:
            logger.error(f"Error checking goal reminders: {e}")
        finally:
            conn.close()
            
    def run_all_jobs(self):
        """Runs all scheduled jobs. Designed to be called by a cron trigger."""
        self.generate_weekly_digests()
        self.check_goal_reminders()
        
        # Finally process the queue to actually send things
        self.dispatcher.process_queue()
