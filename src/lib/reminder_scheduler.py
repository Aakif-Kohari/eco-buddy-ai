"""
Reminder Scheduler for EcoBuddy AI
Schedules and manages reminders for users.
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import queue
import json

logger = logging.getLogger(__name__)


class ReminderType(Enum):
    """Types of reminders."""
    ASSESSMENT = "assessment"
    BUDGET = "budget"
    STREAK = "streak"
    GOAL = "goal"
    CHALLENGE = "challenge"
    CUSTOM = "custom"


class ReminderFrequency(Enum):
    """Reminder frequency options."""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


@dataclass
class Reminder:
    """Data class for a reminder."""
    id: str
    user_id: int
    type: ReminderType
    frequency: ReminderFrequency
    title: str
    message: str
    schedule_time: datetime
    last_triggered: Optional[datetime] = None
    next_trigger: Optional[datetime] = None
    enabled: bool = True
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert reminder to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type.value,
            'frequency': self.frequency.value,
            'title': self.title,
            'message': self.message,
            'schedule_time': self.schedule_time.isoformat(),
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None,
            'next_trigger': self.next_trigger.isoformat() if self.next_trigger else None,
            'enabled': self.enabled,
            'action_url': self.action_url,
            'action_label': self.action_label,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Reminder':
        """Create reminder from dictionary."""
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            type=ReminderType(data['type']),
            frequency=ReminderFrequency(data['frequency']),
            title=data['title'],
            message=data['message'],
            schedule_time=datetime.fromisoformat(data['schedule_time']),
            last_triggered=datetime.fromisoformat(data['last_triggered']) if data.get('last_triggered') else None,
            next_trigger=datetime.fromisoformat(data['next_trigger']) if data.get('next_trigger') else None,
            enabled=data.get('enabled', True),
            action_url=data.get('action_url'),
            action_label=data.get('action_label'),
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now()
        )


class ReminderScheduler:
    """
    Schedules and manages reminders for users.
    Handles recurring and one-time reminders.
    """
    
    def __init__(self):
        self._reminders: Dict[str, Reminder] = {}
        self._user_reminders: Dict[int, List[str]] = {}
        self._scheduler_queue = queue.Queue()
        self._stop_scheduler = False
        self._lock = threading.Lock()
        self._reminder_counter = 0
        
        # Default reminder templates
        self._templates = self._load_templates()
        
        # Start scheduler thread
        self._scheduler_thread = threading.Thread(target=self._scheduler_worker, daemon=True)
        self._scheduler_thread.start()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        
        logger.info("ReminderScheduler initialized")
    
    def _load_templates(self) -> Dict[str, Any]:
        """Load reminder templates."""
        return {
            'assessment': {
                'title': '🌱 Assessment Reminder',
                'message': "It's time to log your sustainability assessment! Your last assessment was {days} days ago.",
                'action_label': 'Start Assessment'
            },
            'budget': {
                'title': '💰 Budget Check-in',
                'message': 'You\'ve used {percentage}% of your monthly carbon budget. Current usage: {usage:.1f} kg CO₂.',
                'action_label': 'View Budget'
            },
            'streak': {
                'title': '🔥 Streak Alert',
                'message': "Don't break your streak! You've been consistent for {streak} days. Log today's assessment!",
                'action_label': 'Log Assessment'
            },
            'goal': {
                'title': '🎯 Goal Progress Update',
                'message': "You're {progress}% towards your goal of {goal} kg CO₂. Keep going!",
                'action_label': 'View Goals'
            },
            'challenge': {
                'title': '🏁 Challenge Update',
                'message': "The '{challenge}' challenge has {days_left} days left. You've completed {progress}%!",
                'action_label': 'View Challenge'
            }
        }
    
    def create_reminder(
        self,
        user_id: int,
        type: ReminderType,
        frequency: ReminderFrequency,
        schedule_time: datetime,
        **kwargs
    ) -> Reminder:
        """
        Create a new reminder.
        
        Args:
            user_id: User ID
            type: Reminder type
            frequency: Reminder frequency
            schedule_time: When to trigger the reminder
            **kwargs: Template variables
        
        Returns:
            Reminder object
        """
        template = self._templates.get(type.value, {})
        title = template.get('title', f'{type.value.title()} Reminder')
        message = template.get('message', 'Reminder').format(**kwargs) if kwargs else template.get('message', 'Reminder')
        action_label = template.get('action_label')
        
        reminder = Reminder(
            id=self._generate_id(user_id),
            user_id=user_id,
            type=type,
            frequency=frequency,
            title=title,
            message=message,
            schedule_time=schedule_time,
            action_label=action_label,
            metadata=kwargs,
            next_trigger=schedule_time
        )
        
        with self._lock:
            self._reminders[reminder.id] = reminder
            if user_id not in self._user_reminders:
                self._user_reminders[user_id] = []
            self._user_reminders[user_id].append(reminder.id)
        
        # Schedule for next trigger
        self._scheduler_queue.put(reminder)
        
        logger.info(f"Created reminder {reminder.id} for user {user_id}")
        return reminder
    
    def _generate_id(self, user_id: int) -> str:
        """Generate unique reminder ID."""
        self._reminder_counter += 1
        timestamp = int(time.time() * 1000)
        return f"reminder_{user_id}_{timestamp}_{self._reminder_counter}"
    
    def _scheduler_worker(self) -> None:
        """Background worker for processing reminders."""
        while not self._stop_scheduler:
            try:
                reminder = self._scheduler_queue.get(timeout=1)
                if reminder:
                    self._process_reminder(reminder)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Scheduler worker error: {e}")
    
    def _process_reminder(self, reminder: Reminder) -> None:
        """Process a reminder and trigger notification."""
        try:
            now = datetime.now()
            
            # Check if reminder should trigger now
            if reminder.next_trigger and reminder.next_trigger <= now:
                # Trigger the reminder
                self._trigger_reminder(reminder)
                
                # Update for next trigger
                if reminder.enabled:
                    self._schedule_next_trigger(reminder)
                else:
                    reminder.next_trigger = None
            else:
                # Reschedule
                if reminder.enabled:
                    self._schedule_next_trigger(reminder)
                    
        except Exception as e:
            logger.error(f"Failed to process reminder {reminder.id}: {e}")
    
    def _trigger_reminder(self, reminder: Reminder) -> None:
        """Trigger a reminder notification."""
        from .notification_manager import create_notification, NotificationType
        
        try:
            # Create notification
            create_notification(
                user_id=reminder.user_id,
                type=NotificationType.REMINDER,
                template_key='assessment_reminder' if reminder.type == ReminderType.ASSESSMENT else 'budget_checkin',
                **reminder.metadata
            )
            
            reminder.last_triggered = datetime.now()
            logger.info(f"Triggered reminder {reminder.id}")
            
        except Exception as e:
            logger.error(f"Failed to trigger reminder {reminder.id}: {e}")
    
    def _schedule_next_trigger(self, reminder: Reminder) -> None:
        """Schedule the next trigger for a recurring reminder."""
        if reminder.frequency == ReminderFrequency.ONCE:
            reminder.next_trigger = None
            return
        
        now = datetime.now()
        
        if reminder.frequency == ReminderFrequency.DAILY:
            next_time = reminder.schedule_time.replace(
                hour=reminder.schedule_time.hour,
                minute=reminder.schedule_time.minute,
                second=reminder.schedule_time.second
            )
            while next_time <= now:
                next_time = next_time + timedelta(days=1)
            reminder.next_trigger = next_time
            
        elif reminder.frequency == ReminderFrequency.WEEKLY:
            next_time = reminder.schedule_time
            while next_time <= now:
                next_time = next_time + timedelta(weeks=1)
            reminder.next_trigger = next_time
            
        elif reminder.frequency == ReminderFrequency.MONTHLY:
            next_time = reminder.schedule_time
            while next_time <= now:
                next_time = next_time + timedelta(days=30)
            reminder.next_trigger = next_time
        
        elif reminder.frequency == ReminderFrequency.CUSTOM:
            # Custom interval from metadata
            interval_hours = reminder.metadata.get('interval_hours', 24)
            reminder.next_trigger = now + timedelta(hours=interval_hours)
        
        # Reschedule in queue
        if reminder.next_trigger:
            self._scheduler_queue.put(reminder)
    
    def _cleanup_worker(self) -> None:
        """Background worker for cleaning up old reminders."""
        while not self._stop_scheduler:
            try:
                time.sleep(3600)  # Run every hour
                self._cleanup_old_reminders()
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
    
    def _cleanup_old_reminders(self, days: int = 90) -> None:
        """Remove reminders older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        to_remove = []
        
        with self._lock:
            for reminder_id, reminder in self._reminders.items():
                if reminder.created_at < cutoff and reminder.frequency == ReminderFrequency.ONCE:
                    to_remove.append(reminder_id)
            
            for reminder_id in to_remove:
                reminder = self._reminders[reminder_id]
                del self._reminders[reminder_id]
                if reminder.user_id in self._user_reminders:
                    self._user_reminders[reminder.user_id] = [
                        r_id for r_id in self._user_reminders[reminder.user_id]
                        if r_id != reminder_id
                    ]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old reminders")
    
    def get_user_reminders(self, user_id: int) -> List[Reminder]:
        """Get all reminders for a user."""
        with self._lock:
            reminder_ids = self._user_reminders.get(user_id, [])
            return [self._reminders[r_id] for r_id in reminder_ids if r_id in self._reminders]
    
    def get_active_reminders(self, user_id: int) -> List[Reminder]:
        """Get active (enabled and not expired) reminders for a user."""
        reminders = self.get_user_reminders(user_id)
        now = datetime.now()
        return [
            r for r in reminders
            if r.enabled and (r.next_trigger is None or r.next_trigger > now)
        ]
    
    def update_reminder(self, reminder_id: str, **kwargs) -> Optional[Reminder]:
        """Update a reminder."""
        with self._lock:
            reminder = self._reminders.get(reminder_id)
            if not reminder:
                return None
            
            for key, value in kwargs.items():
                if hasattr(reminder, key):
                    setattr(reminder, key, value)
            
            reminder.updated_at = datetime.now()
            
            # Reschedule if needed
            if kwargs.get('schedule_time') or kwargs.get('frequency'):
                self._schedule_next_trigger(reminder)
                self._scheduler_queue.put(reminder)
            
            return reminder
    
    def delete_reminder(self, reminder_id: str) -> bool:
        """Delete a reminder."""
        with self._lock:
            reminder = self._reminders.get(reminder_id)
            if not reminder:
                return False
            
            del self._reminders[reminder_id]
            if reminder.user_id in self._user_reminders:
                self._user_reminders[reminder.user_id] = [
                    r_id for r_id in self._user_reminders[reminder.user_id]
                    if r_id != reminder_id
                ]
            
            logger.info(f"Deleted reminder {reminder_id}")
            return True
    
    def delete_user_reminders(self, user_id: int) -> int:
        """Delete all reminders for a user."""
        count = 0
        with self._lock:
            reminder_ids = self._user_reminders.get(user_id, [])
            for reminder_id in reminder_ids:
                if reminder_id in self._reminders:
                    del self._reminders[reminder_id]
                    count += 1
            self._user_reminders[user_id] = []
        
        logger.info(f"Deleted {count} reminders for user {user_id}")
        return count
    
    def enable_reminder(self, reminder_id: str, enabled: bool) -> Optional[Reminder]:
        """Enable or disable a reminder."""
        with self._lock:
            reminder = self._reminders.get(reminder_id)
            if reminder:
                reminder.enabled = enabled
                if enabled:
                    self._schedule_next_trigger(reminder)
                    self._scheduler_queue.put(reminder)
                return reminder
            return None
    
    def get_reminder_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get reminder statistics."""
        stats = {
            'total_reminders': len(self._reminders),
            'by_type': {},
            'by_frequency': {},
            'enabled': 0,
            'disabled': 0
        }
        
        with self._lock:
            reminders = list(self._reminders.values())
            if user_id:
                reminder_ids = self._user_reminders.get(user_id, [])
                reminders = [r for r in reminders if r.id in reminder_ids]
            
            for r in reminders:
                stats['by_type'][r.type.value] = stats['by_type'].get(r.type.value, 0) + 1
                stats['by_frequency'][r.frequency.value] = stats['by_frequency'].get(r.frequency.value, 0) + 1
                if r.enabled:
                    stats['enabled'] += 1
                else:
                    stats['disabled'] += 1
        
        return stats
    
    def create_default_reminders(self, user_id: int) -> List[Reminder]:
        """Create default reminders for a new user."""
        reminders = []
        now = datetime.now()
        
        # Assessment reminder (weekly)
        assessment_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if assessment_time <= now:
            assessment_time += timedelta(days=1)
        
        reminders.append(
            self.create_reminder(
                user_id=user_id,
                type=ReminderType.ASSESSMENT,
                frequency=ReminderFrequency.WEEKLY,
                schedule_time=assessment_time,
                days=0
            )
        )
        
        # Budget reminder (monthly)
        budget_time = now.replace(day=1, hour=10, minute=0, second=0, microsecond=0)
        if budget_time <= now:
            budget_time += timedelta(days=30)
        
        reminders.append(
            self.create_reminder(
                user_id=user_id,
                type=ReminderType.BUDGET,
                frequency=ReminderFrequency.MONTHLY,
                schedule_time=budget_time,
                percentage=0
            )
        )
        
        logger.info(f"Created default reminders for user {user_id}")
        return reminders
    
    def stop(self) -> None:
        """Stop the reminder scheduler."""
        self._stop_scheduler = True
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)


# Global reminder scheduler instance
_reminder_scheduler: Optional[ReminderScheduler] = None
_reminder_scheduler_lock = threading.Lock()


def get_reminder_scheduler() -> ReminderScheduler:
    """Get or create global reminder scheduler instance."""
    global _reminder_scheduler
    with _reminder_scheduler_lock:
        if _reminder_scheduler is None:
            _reminder_scheduler = ReminderScheduler()
        return _reminder_scheduler


def create_reminder(
    user_id: int,
    type: ReminderType,
    frequency: ReminderFrequency,
    schedule_time: datetime,
    **kwargs
) -> Reminder:
    """
    Convenience function to create a reminder.
    
    Args:
        user_id: User ID
        type: Reminder type
        frequency: Reminder frequency
        schedule_time: When to trigger the reminder
        **kwargs: Template variables
    
    Returns:
        Reminder object
    """
    scheduler = get_reminder_scheduler()
    return scheduler.create_reminder(user_id, type, frequency, schedule_time, **kwargs)


def get_user_reminders(user_id: int) -> List[Reminder]:
    """Convenience function to get user reminders."""
    scheduler = get_reminder_scheduler()
    return scheduler.get_user_reminders(user_id)