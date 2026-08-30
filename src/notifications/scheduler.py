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

    def check_collaborative_goal_reminders(self):
        """
        Scans collaborative household goals and dispatches alerts for 'At Risk' status 
        or if specific members drag the group off-track.
        """
        try:
            # Import inline to avoid circular imports if any
            from src.utils.collaborative_goals import (
                get_goals_for_household,
                get_allocations_for_goal,
                evaluate_household_progress
            )
            from src.lifestyle.household import get_households_for_user, get_members
            from src.database import get_user_assessments
            from src.utils.goals import GOAL_ACTIVE, STATUS_AT_RISK, STATUS_OFF_TRACK
            
            conn = get_connection()
            cursor = conn.cursor()
            
            # Fetch all active collaborative goals
            cursor.execute("SELECT id, household_id FROM collaborative_goals WHERE status = ?", (GOAL_ACTIVE,))
            active_goals = cursor.fetchall()
            
            for goal_id, household_id in active_goals:
                # We need the full goal dict, so we can fetch it via get_goal
                from src.utils.collaborative_goals import get_goal
                goal = get_goal(goal_id)
                if not goal:
                    continue
                    
                members = get_members(household_id)
                if not members:
                    continue
                    
                # Evaluate household overall progress
                household_assessments = []
                for m in members:
                    if m["user_id"] is not None:
                        member_assessments = get_user_assessments(m["user_id"])
                        for a in member_assessments:
                            household_assessments.append({
                                "date": a.created_at.date() if isinstance(a.created_at, datetime) else a.created_at,
                                "footprint": a.score,
                                "user_id": a.user_id
                            })
                            
                aggregated = []
                if household_assessments:
                    import pandas as pd
                    df = pd.DataFrame(household_assessments)
                    df['date'] = pd.to_datetime(df['date']).dt.date
                    grouped = df.groupby('date')['footprint'].sum().reset_index()
                    aggregated = grouped.to_dict('records')
                    
                progress = evaluate_household_progress(goal, aggregated)
                
                # Check overall household status
                if progress["status"] in [STATUS_AT_RISK, STATUS_OFF_TRACK]:
                    for m in members:
                        if m["user_id"] is not None:
                            self.dispatcher.dispatch(
                                user_id=m["user_id"],
                                category="goals",
                                title="Household Goal At Risk",
                                message=f"Your household is currently {progress['status_label'].lower()} for its collaborative goal. Team up to get back on track!",
                                priority="high",
                                icon="⚠️",
                                dedupe_key=f"collab_goal_risk_{goal_id}_{progress['status']}"
                            )
                
                # Check individual allocations
                allocations = get_allocations_for_goal(goal_id)
                if allocations:
                    for m in members:
                        if m["user_id"] is not None:
                            allocated_target = allocations.get(m["id"], 0.0)
                            latest_actual = 0.0
                            ma = get_user_assessments(m["user_id"])
                            if ma:
                                latest_actual = sorted(ma, key=lambda x: x.created_at)[-1].score
                            
                            variance = latest_actual - allocated_target
                            # Arbitrary threshold: if variance is > 20% of their allocation or > 100kg
                            if allocated_target > 0 and (variance / allocated_target > 0.20 or variance > 100):
                                self.dispatcher.dispatch(
                                    user_id=m["user_id"],
                                    category="goals",
                                    title="You're Dragging the Household Behind!",
                                    message=f"You are exceeding your allocated target of {allocated_target:.0f} kg CO2 by {variance:.0f} kg. Try to reduce your personal footprint to help the household succeed.",
                                    priority="medium",
                                    icon="📉",
                                    dedupe_key=f"collab_goal_drag_{goal_id}_{m['id']}"
                                )
                                
        except sqlite3.OperationalError:
            logger.info("Collaborative goals tables not found, skipping.")
        except Exception as e:
            logger.error(f"Error checking collaborative goal reminders: {e}")
            
    def run_all_jobs(self):
        """Runs all scheduled jobs. Designed to be called by a cron trigger."""
        self.generate_weekly_digests()
        self.check_goal_reminders()
        self.check_collaborative_goal_reminders()
        
        # Finally process the queue to actually send things
        self.dispatcher.process_queue()
