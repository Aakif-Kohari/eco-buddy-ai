"""
Goal Tracker for EcoBuddy AI
Manages user sustainability goals, progress tracking, and achievements.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
import json

logger = logging.getLogger(__name__)


class GoalType(Enum):
    """Types of goals."""
    FOOTPRINT = "footprint"
    ECO_SCORE = "eco_score"
    STREAK = "streak"
    ASSESSMENTS = "assessments"
    ENERGY = "energy"
    TRANSPORT = "transport"
    DIET = "diet"
    WASTE = "waste"
    CUSTOM = "custom"


class GoalStatus(Enum):
    """Goal status states."""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class Goal:
    """Data class for a goal."""
    id: str
    user_id: int
    title: str
    description: str
    type: GoalType
    target_value: float
    current_value: float = 0.0
    unit: str = "kg CO₂"
    start_date: datetime = field(default_factory=datetime.now)
    target_date: Optional[datetime] = None
    status: GoalStatus = GoalStatus.ACTIVE
    progress: float = 0.0
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    rewards: Dict[str, Any] = field(default_factory=dict)
    is_recurring: bool = False
    recurrence_interval_days: int = 30
    parent_goal_id: Optional[str] = None
    sub_goals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'type': self.type.value,
            'target_value': self.target_value,
            'current_value': self.current_value,
            'unit': self.unit,
            'start_date': self.start_date.isoformat(),
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'status': self.status.value,
            'progress': self.progress,
            'milestones': self.milestones,
            'rewards': self.rewards,
            'is_recurring': self.is_recurring,
            'recurrence_interval_days': self.recurrence_interval_days,
            'parent_goal_id': self.parent_goal_id,
            'sub_goals': self.sub_goals,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Goal':
        """Create goal from dictionary."""
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            title=data['title'],
            description=data['description'],
            type=GoalType(data['type']),
            target_value=data['target_value'],
            current_value=data.get('current_value', 0.0),
            unit=data.get('unit', 'kg CO₂'),
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else datetime.now(),
            target_date=datetime.fromisoformat(data['target_date']) if data.get('target_date') else None,
            status=GoalStatus(data.get('status', 'active')),
            progress=data.get('progress', 0.0),
            milestones=data.get('milestones', []),
            rewards=data.get('rewards', {}),
            is_recurring=data.get('is_recurring', False),
            recurrence_interval_days=data.get('recurrence_interval_days', 30),
            parent_goal_id=data.get('parent_goal_id'),
            sub_goals=data.get('sub_goals', []),
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None
        )


@dataclass
class GoalProgress:
    """Data class for goal progress update."""
    goal_id: str
    user_id: int
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    note: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GoalTracker:
    """
    Manages user goals, progress tracking, and milestone achievements.
    """
    
    def __init__(self):
        self._goals: Dict[str, Goal] = {}
        self._user_goals: Dict[int, List[str]] = {}  # user_id -> goal_ids
        self._goal_progress: Dict[str, List[GoalProgress]] = {}  # goal_id -> progress history
        self._lock = threading.Lock()
        self._goal_counter = 0
        
        # Load default goals
        self._load_default_goals()
        
        # Start monitoring thread
        self._stop_monitor = False
        self._monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self._monitor_thread.start()
        
        logger.info("GoalTracker initialized")
    
    def _generate_id(self) -> str:
        """Generate unique goal ID."""
        self._goal_counter += 1
        timestamp = int(time.time() * 1000)
        return f"goal_{timestamp}_{self._goal_counter}"
    
    def _load_default_goals(self) -> None:
        """Load default goal templates."""
        # Default goals are created when user first uses the system
        pass
    
    def create_goal(
        self,
        user_id: int,
        title: str,
        description: str,
        type: GoalType,
        target_value: float,
        target_date: Optional[datetime] = None,
        **kwargs
    ) -> Goal:
        """
        Create a new goal.
        
        Args:
            user_id: User ID
            title: Goal title
            description: Goal description
            type: Goal type
            target_value: Target value
            target_date: Target date (default: 30 days from now)
            **kwargs: Additional fields
        
        Returns:
            Goal object
        """
        if target_date is None:
            target_date = datetime.now() + timedelta(days=30)
        
        goal = Goal(
            id=self._generate_id(),
            user_id=user_id,
            title=title,
            description=description,
            type=type,
            target_value=target_value,
            unit=kwargs.get('unit', 'kg CO₂'),
            start_date=kwargs.get('start_date', datetime.now()),
            target_date=target_date,
            milestones=kwargs.get('milestones', []),
            rewards=kwargs.get('rewards', {}),
            is_recurring=kwargs.get('is_recurring', False),
            recurrence_interval_days=kwargs.get('recurrence_interval_days', 30),
            parent_goal_id=kwargs.get('parent_goal_id'),
            metadata=kwargs.get('metadata', {})
        )
        
        with self._lock:
            self._goals[goal.id] = goal
            if user_id not in self._user_goals:
                self._user_goals[user_id] = []
            self._user_goals[user_id].append(goal.id)
            self._goal_progress[goal.id] = []
        
        logger.info(f"Created goal {goal.id} for user {user_id}: {title}")
        return goal
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return self._goals.get(goal_id)
    
    def get_user_goals(
        self,
        user_id: int,
        status: Optional[GoalStatus] = None,
        goal_type: Optional[GoalType] = None,
        active_only: bool = True
    ) -> List[Goal]:
        """Get goals for a user."""
        goal_ids = self._user_goals.get(user_id, [])
        goals = [self._goals[g_id] for g_id in goal_ids if g_id in self._goals]
        
        if status:
            goals = [g for g in goals if g.status == status]
        if goal_type:
            goals = [g for g in goals if g.type == goal_type]
        if active_only:
            goals = [g for g in goals if g.status == GoalStatus.ACTIVE]
        
        return goals
    
    def get_active_goals(self, user_id: int) -> List[Goal]:
        """Get active goals for a user."""
        return self.get_user_goals(user_id, status=GoalStatus.ACTIVE)
    
    def update_goal_progress(
        self,
        goal_id: str,
        value: float,
        note: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Update goal progress.
        
        Args:
            goal_id: Goal ID
            value: Current value
            note: Optional note
            **kwargs: Additional metadata
        
        Returns:
            True if successful
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            
            if goal.status != GoalStatus.ACTIVE:
                return False
            
            goal.current_value = value
            goal.progress = min((value / goal.target_value) * 100, 100.0)
            goal.updated_at = datetime.now()
            
            # Add progress record
            progress = GoalProgress(
                goal_id=goal_id,
                user_id=goal.user_id,
                value=value,
                note=note,
                metadata=kwargs
            )
            self._goal_progress[goal_id].append(progress)
            
            # Check for completion
            if goal.progress >= 100.0:
                self._complete_goal(goal_id)
            else:
                # Check for milestones
                self._check_milestones(goal)
            
            logger.info(f"Updated goal {goal_id}: {goal.progress:.1f}%")
            return True
    
    def _complete_goal(self, goal_id: str) -> None:
        """Complete a goal and award rewards."""
        goal = self._goals.get(goal_id)
        if not goal:
            return
        
        goal.status = GoalStatus.COMPLETED
        goal.completed_at = datetime.now()
        goal.updated_at = datetime.now()
        
        # Award rewards
        if goal.rewards:
            from .gamification_v2 import add_xp, add_coins
            if 'xp' in goal.rewards:
                add_xp(goal.user_id, goal.rewards['xp'])
            if 'coins' in goal.rewards:
                add_coins(goal.user_id, goal.rewards['coins'])
        
        # Create notification
        from .notification_manager import create_notification, NotificationType
        create_notification(
            user_id=goal.user_id,
            type=NotificationType.ACHIEVEMENT,
            template_key='milestone_reached',
            count=goal.title,
            total_goal=goal.target_value
        )
        
        # Check for recurring goal
        if goal.is_recurring:
            self._create_recurring_goal(goal)
        
        logger.info(f"Goal {goal_id} completed by user {goal.user_id}")
    
    def _create_recurring_goal(self, goal: Goal) -> None:
        """Create a recurring goal instance."""
        new_target_date = datetime.now() + timedelta(days=goal.recurrence_interval_days)
        
        self.create_goal(
            user_id=goal.user_id,
            title=f"{goal.title} (Recurring)",
            description=goal.description,
            type=goal.type,
            target_value=goal.target_value,
            target_date=new_target_date,
            unit=goal.unit,
            is_recurring=True,
            recurrence_interval_days=goal.recurrence_interval_days,
            parent_goal_id=goal.id,
            rewards=goal.rewards,
            metadata=goal.metadata
        )
    
    def _check_milestones(self, goal: Goal) -> None:
        """Check and trigger milestone achievements."""
        if not goal.milestones:
            return
        
        for milestone in goal.milestones:
            if milestone.get('achieved', False):
                continue
            
            threshold = milestone.get('threshold', 0)
            if goal.progress >= threshold:
                milestone['achieved'] = True
                milestone['achieved_at'] = datetime.now().isoformat()
                
                # Create notification for milestone
                from .notification_manager import create_notification, NotificationType
                create_notification(
                    user_id=goal.user_id,
                    type=NotificationType.ACHIEVEMENT,
                    template_key='milestone_reached',
                    count=f"{threshold}%",
                    total_goal=goal.title
                )
                
                logger.info(f"Milestone {threshold}% reached for goal {goal.id}")
    
    def get_goal_progress_history(
        self,
        goal_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[GoalProgress]:
        """Get progress history for a goal."""
        history = self._goal_progress.get(goal_id, [])
        history.sort(key=lambda p: p.timestamp, reverse=True)
        return history[offset:offset + limit]
    
    def get_goal_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get goal statistics for a user."""
        goals = self.get_user_goals(user_id, active_only=False)
        
        stats = {
            'total_goals': len(goals),
            'active': 0,
            'completed': 0,
            'failed': 0,
            'archived': 0,
            'by_type': {},
            'average_progress': 0,
            'completion_rate': 0
        }
        
        total_progress = 0
        for goal in goals:
            stats['by_type'][goal.type.value] = stats['by_type'].get(goal.type.value, 0) + 1
            
            if goal.status == GoalStatus.ACTIVE:
                stats['active'] += 1
            elif goal.status == GoalStatus.COMPLETED:
                stats['completed'] += 1
            elif goal.status == GoalStatus.FAILED:
                stats['failed'] += 1
            elif goal.status == GoalStatus.ARCHIVED:
                stats['archived'] += 1
            
            total_progress += goal.progress
        
        if goals:
            stats['average_progress'] = total_progress / len(goals)
            stats['completion_rate'] = (stats['completed'] / len(goals)) * 100
        
        return stats
    
    def get_goal_recommendations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get goal recommendations based on user data."""
        recommendations = []
        
        try:
            from database import get_assessments
            
            assessments = get_assessments(user_id)
            if assessments:
                latest = assessments[0]
                footprint = latest.get('footprint', 0)
                eco_score = latest.get('eco_score', 0)
                
                # Recommend footprint reduction goal
                if footprint > 500:
                    target = footprint * 0.8  # 20% reduction
                    recommendations.append({
                        'title': 'Reduce Carbon Footprint',
                        'description': f'Reduce your carbon footprint from {footprint:.0f} to {target:.0f} kg CO₂',
                        'type': GoalType.FOOTPRINT,
                        'target_value': target,
                        'unit': 'kg CO₂',
                        'rewards': {'xp': 200, 'coins': 50}
                    })
                
                # Recommend eco score improvement
                if eco_score < 80:
                    target = min(eco_score + 10, 100)
                    recommendations.append({
                        'title': 'Improve Eco Score',
                        'description': f'Improve your Eco Score from {eco_score:.0f} to {target:.0f}',
                        'type': GoalType.ECO_SCORE,
                        'target_value': target,
                        'unit': 'points',
                        'rewards': {'xp': 150, 'coins': 30}
                    })
            
            # Recommend streak goal
            from .gamification import get_user_streak
            streak = get_user_streak(user_id)
            if streak < 30:
                target = min(streak + 7, 30)
                recommendations.append({
                    'title': 'Build Your Streak',
                    'description': f'Extend your streak from {streak} to {target} days',
                    'type': GoalType.STREAK,
                    'target_value': target,
                    'unit': 'days',
                    'rewards': {'xp': 100, 'coins': 20}
                })
            
        except Exception as e:
            logger.error(f"Failed to get goal recommendations: {e}")
        
        return recommendations
    
    def _monitor_worker(self) -> None:
        """Background worker for goal monitoring."""
        while not self._stop_monitor:
            try:
                time.sleep(3600)  # Check every hour
                self._check_expiring_goals()
            except Exception as e:
                logger.error(f"Monitor worker error: {e}")
    
    def _check_expiring_goals(self) -> None:
        """Check for expiring goals and create reminders."""
        now = datetime.now()
        
        with self._lock:
            for goal in self._goals.values():
                if goal.status != GoalStatus.ACTIVE:
                    continue
                
                if goal.target_date:
                    days_until_expiry = (goal.target_date - now).days
                    
                    if days_until_expiry <= 3 and days_until_expiry > 0:
                        # Goal expiring soon
                        from .notification_manager import create_notification, NotificationType
                        create_notification(
                            user_id=goal.user_id,
                            type=NotificationType.REMINDER,
                            template_key='goal_reminder',
                            progress=goal.progress,
                            goal=goal.target_value,
                            current=goal.current_value
                        )
                    elif days_until_expiry < 0:
                        # Goal expired
                        goal.status = GoalStatus.FAILED
                        goal.updated_at = now
                        logger.info(f"Goal {goal.id} failed - target date passed")


# Global goal tracker instance
_goal_tracker: Optional[GoalTracker] = None
_goal_tracker_lock = threading.Lock()


def get_goal_tracker() -> GoalTracker:
    """Get or create global goal tracker instance."""
    global _goal_tracker
    with _goal_tracker_lock:
        if _goal_tracker is None:
            _goal_tracker = GoalTracker()
        return _goal_tracker


def create_goal(
    user_id: int,
    title: str,
    description: str,
    type: GoalType,
    target_value: float,
    **kwargs
) -> Goal:
    """Convenience function to create a goal."""
    tracker = get_goal_tracker()
    return tracker.create_goal(user_id, title, description, type, target_value, **kwargs)


def get_user_goals(user_id: int, active_only: bool = True) -> List[Goal]:
    """Convenience function to get user goals."""
    tracker = get_goal_tracker()
    return tracker.get_user_goals(user_id, active_only=active_only)


def update_goal_progress(goal_id: str, value: float, note: Optional[str] = None) -> bool:
    """Convenience function to update goal progress."""
    tracker = get_goal_tracker()
    return tracker.update_goal_progress(goal_id, value, note)


def get_goal_recommendations(user_id: int) -> List[Dict[str, Any]]:
    """Convenience function to get goal recommendations."""
    tracker = get_goal_tracker()
    return tracker.get_goal_recommendations(user_id)