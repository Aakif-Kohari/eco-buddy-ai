"""
Challenge Manager for EcoBuddy AI
Manages community challenges, progress tracking, and completion rewards.
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
import uuid

logger = logging.getLogger(__name__)


class ChallengeStatus(Enum):
    """Challenge status states."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ChallengeType(Enum):
    """Types of challenges."""
    INDIVIDUAL = "individual"
    TEAM = "team"
    COMMUNITY = "community"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SPECIAL = "special"


class ChallengeCategory(Enum):
    """Challenge categories."""
    FOOTPRINT = "footprint"
    ENERGY = "energy"
    TRANSPORT = "transport"
    DIET = "diet"
    WASTE = "waste"
    WATER = "water"
    COMMUNITY = "community"
    EDUCATION = "education"


@dataclass
class Challenge:
    """Data class for a challenge."""
    id: str
    title: str
    description: str
    type: ChallengeType
    category: ChallengeCategory
    status: ChallengeStatus
    created_by: int
    created_at: datetime
    start_date: datetime
    end_date: datetime
    target_metric: str
    target_value: float
    current_value: float = 0.0
    progress: float = 0.0
    rewards: Dict[str, Any] = field(default_factory=dict)
    participants: List[int] = field(default_factory=list)
    completed_by: List[int] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    image_url: Optional[str] = None
    is_featured: bool = False
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert challenge to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type.value,
            'category': self.category.value,
            'status': self.status.value,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'target_metric': self.target_metric,
            'target_value': self.target_value,
            'current_value': self.current_value,
            'progress': self.progress,
            'rewards': self.rewards,
            'participants': self.participants,
            'completed_by': self.completed_by,
            'rules': self.rules,
            'tags': self.tags,
            'image_url': self.image_url,
            'is_featured': self.is_featured,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Challenge':
        """Create challenge from dictionary."""
        return cls(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            type=ChallengeType(data['type']),
            category=ChallengeCategory(data['category']),
            status=ChallengeStatus(data['status']),
            created_by=data['created_by'],
            created_at=datetime.fromisoformat(data['created_at']),
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            target_metric=data['target_metric'],
            target_value=data['target_value'],
            current_value=data.get('current_value', 0.0),
            progress=data.get('progress', 0.0),
            rewards=data.get('rewards', {}),
            participants=data.get('participants', []),
            completed_by=data.get('completed_by', []),
            rules=data.get('rules', []),
            tags=data.get('tags', []),
            image_url=data.get('image_url'),
            is_featured=data.get('is_featured', False),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )


@dataclass
class ChallengeProgress:
    """Data class for user challenge progress."""
    challenge_id: str
    user_id: int
    progress_value: float = 0.0
    completed: bool = False
    completed_at: Optional[datetime] = None
    joined_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChallengeManager:
    """
    Manages community challenges, progress tracking, and rewards.
    """
    
    def __init__(self):
        self._challenges: Dict[str, Challenge] = {}
        self._user_progress: Dict[str, Dict[int, ChallengeProgress]] = {}  # challenge_id -> user_id -> progress
        self._user_challenges: Dict[int, List[str]] = {}  # user_id -> challenge_ids
        self._lock = threading.Lock()
        self._challenge_counter = 0
        
        # Load default challenges
        self._load_default_challenges()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        
        logger.info("ChallengeManager initialized")
    
    def _load_default_challenges(self) -> None:
        """Load default challenges."""
        now = datetime.now()
        
        default_challenges = [
            Challenge(
                id=self._generate_id(),
                title="7-Day Green Commute",
                description="Use sustainable transportation for 7 consecutive days",
                type=ChallengeType.INDIVIDUAL,
                category=ChallengeCategory.TRANSPORT,
                status=ChallengeStatus.ACTIVE,
                created_by=1,
                created_at=now,
                start_date=now,
                end_date=now + timedelta(days=7),
                target_metric="sustainable_trips",
                target_value=7,
                rewards={'xp': 100, 'badge': 'green_commuter'},
                rules=["Use public transport, bike, or walk", "Log your commute daily"],
                tags=["transport", "sustainable", "weekly"]
            ),
            Challenge(
                id=self._generate_id(),
                title="30-Day Plant-Based Challenge",
                description="Adopt a plant-based diet for 30 days",
                type=ChallengeType.INDIVIDUAL,
                category=ChallengeCategory.DIET,
                status=ChallengeStatus.ACTIVE,
                created_by=1,
                created_at=now,
                start_date=now,
                end_date=now + timedelta(days=30),
                target_metric="plant_meals",
                target_value=90,
                rewards={'xp': 200, 'badge': 'plant_champion'},
                rules=["Eat only plant-based meals", "Share your recipes"],
                tags=["diet", "sustainable", "monthly"]
            ),
            Challenge(
                id=self._generate_id(),
                title="Carbon Reduction Challenge",
                description="Reduce your carbon footprint by 20%",
                type=ChallengeType.INDIVIDUAL,
                category=ChallengeCategory.FOOTPRINT,
                status=ChallengeStatus.ACTIVE,
                created_by=1,
                created_at=now,
                start_date=now,
                end_date=now + timedelta(days=30),
                target_metric="footprint_reduction",
                target_value=20,
                rewards={'xp': 300, 'badge': 'carbon_reducer'},
                rules=["Log your activities daily", "Track your progress"],
                tags=["footprint", "reduction", "monthly"]
            ),
            Challenge(
                id=self._generate_id(),
                title="Team Eco Challenge",
                description="Team with the lowest average footprint wins",
                type=ChallengeType.TEAM,
                category=ChallengeCategory.COMMUNITY,
                status=ChallengeStatus.ACTIVE,
                created_by=1,
                created_at=now,
                start_date=now,
                end_date=now + timedelta(days=14),
                target_metric="team_avg_footprint",
                target_value=0,
                rewards={'xp': 150, 'badge': 'eco_team'},
                rules=["Form teams of 3-5 members", "Log your impact daily"],
                tags=["team", "community", "competition"]
            ),
            Challenge(
                id=self._generate_id(),
                title="Waste Reduction Week",
                description="Reduce household waste by 50%",
                type=ChallengeType.INDIVIDUAL,
                category=ChallengeCategory.WASTE,
                status=ChallengeStatus.ACTIVE,
                created_by=1,
                created_at=now,
                start_date=now,
                end_date=now + timedelta(days=7),
                target_metric="waste_reduction",
                target_value=50,
                rewards={'xp': 150, 'badge': 'waste_warrior'},
                rules=["Recycle more", "Compost organic waste", "Avoid single-use plastics"],
                tags=["waste", "recycling", "weekly"]
            )
        ]
        
        for challenge in default_challenges:
            self._challenges[challenge.id] = challenge
            logger.info(f"Loaded default challenge: {challenge.title}")
    
    def _generate_id(self) -> str:
        """Generate unique challenge ID."""
        self._challenge_counter += 1
        timestamp = int(time.time() * 1000)
        return f"challenge_{timestamp}_{self._challenge_counter}"
    
    def create_challenge(
        self,
        title: str,
        description: str,
        type: ChallengeType,
        category: ChallengeCategory,
        created_by: int,
        start_date: datetime,
        end_date: datetime,
        target_metric: str,
        target_value: float,
        **kwargs
    ) -> Challenge:
        """
        Create a new challenge.
        
        Args:
            title: Challenge title
            description: Challenge description
            type: Challenge type
            category: Challenge category
            created_by: User ID of creator
            start_date: Challenge start date
            end_date: Challenge end date
            target_metric: Target metric name
            target_value: Target value
            **kwargs: Additional fields
        
        Returns:
            Challenge object
        """
        challenge = Challenge(
            id=self._generate_id(),
            title=title,
            description=description,
            type=type,
            category=category,
            status=ChallengeStatus.DRAFT,
            created_by=created_by,
            created_at=datetime.now(),
            start_date=start_date,
            end_date=end_date,
            target_metric=target_metric,
            target_value=target_value,
            rules=kwargs.get('rules', []),
            tags=kwargs.get('tags', []),
            rewards=kwargs.get('rewards', {}),
            image_url=kwargs.get('image_url'),
            is_featured=kwargs.get('is_featured', False)
        )
        
        with self._lock:
            self._challenges[challenge.id] = challenge
        
        logger.info(f"Created challenge: {challenge.title}")
        return challenge
    
    def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Get a challenge by ID."""
        return self._challenges.get(challenge_id)
    
    def get_all_challenges(
        self,
        status: Optional[ChallengeStatus] = None,
        type: Optional[ChallengeType] = None,
        category: Optional[ChallengeCategory] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Challenge]:
        """Get challenges with filters."""
        challenges = list(self._challenges.values())
        
        if status:
            challenges = [c for c in challenges if c.status == status]
        if type:
            challenges = [c for c in challenges if c.type == type]
        if category:
            challenges = [c for c in challenges if c.category == category]
        
        # Sort by start date (newest first)
        challenges.sort(key=lambda c: c.start_date, reverse=True)
        
        return challenges[offset:offset + limit]
    
    def get_active_challenges(self) -> List[Challenge]:
        """Get all active challenges."""
        now = datetime.now()
        return [
            c for c in self._challenges.values()
            if c.status == ChallengeStatus.ACTIVE
            and c.start_date <= now
            and c.end_date >= now
        ]
    
    def get_featured_challenges(self) -> List[Challenge]:
        """Get featured challenges."""
        return [c for c in self._challenges.values() if c.is_featured and c.status == ChallengeStatus.ACTIVE]
    
    def join_challenge(self, challenge_id: str, user_id: int) -> bool:
        """Join a challenge."""
        with self._lock:
            challenge = self._challenges.get(challenge_id)
            if not challenge:
                return False
            
            if challenge.status != ChallengeStatus.ACTIVE:
                return False
            
            if user_id in challenge.participants:
                return False
            
            challenge.participants.append(user_id)
            
            if user_id not in self._user_challenges:
                self._user_challenges[user_id] = []
            self._user_challenges[user_id].append(challenge_id)
            
            # Initialize progress
            self._user_progress.setdefault(challenge_id, {})[user_id] = ChallengeProgress(
                challenge_id=challenge_id,
                user_id=user_id
            )
            
            logger.info(f"User {user_id} joined challenge {challenge_id}")
            return True
    
    def leave_challenge(self, challenge_id: str, user_id: int) -> bool:
        """Leave a challenge."""
        with self._lock:
            challenge = self._challenges.get(challenge_id)
            if not challenge:
                return False
            
            if user_id not in challenge.participants:
                return False
            
            challenge.participants.remove(user_id)
            
            if user_id in self._user_challenges:
                self._user_challenges[user_id] = [c for c in self._user_challenges[user_id] if c != challenge_id]
            
            if challenge_id in self._user_progress:
                self._user_progress[challenge_id].pop(user_id, None)
            
            logger.info(f"User {user_id} left challenge {challenge_id}")
            return True
    
    def update_progress(self, challenge_id: str, user_id: int, value: float) -> bool:
        """Update user progress for a challenge."""
        with self._lock:
            challenge = self._challenges.get(challenge_id)
            if not challenge:
                return False
            
            if user_id not in challenge.participants:
                return False
            
            if challenge_id not in self._user_progress:
                self._user_progress[challenge_id] = {}
            
            if user_id not in self._user_progress[challenge_id]:
                self._user_progress[challenge_id][user_id] = ChallengeProgress(
                    challenge_id=challenge_id,
                    user_id=user_id
                )
            
            progress = self._user_progress[challenge_id][user_id]
            progress.progress_value = min(value, challenge.target_value)
            progress.last_updated = datetime.now()
            
            # Check if completed
            if progress.progress_value >= challenge.target_value and not progress.completed:
                progress.completed = True
                progress.completed_at = datetime.now()
                challenge.completed_by.append(user_id)
                
                # Award rewards
                self._award_rewards(challenge_id, user_id)
                
                logger.info(f"User {user_id} completed challenge {challenge_id}")
            
            # Update challenge progress
            challenge.current_value = sum(
                p.progress_value for p in self._user_progress[challenge_id].values()
            ) / len(challenge.participants) if challenge.participants else 0
            
            challenge.progress = (challenge.current_value / challenge.target_value) * 100 if challenge.target_value > 0 else 0
            
            return True
    
    def _award_rewards(self, challenge_id: str, user_id: int) -> None:
        """Award rewards to a user for completing a challenge."""
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            return
        
        rewards = challenge.rewards
        
        try:
            # Award XP
            if 'xp' in rewards:
                from .gamification import award_xp
                award_xp(user_id, rewards['xp'])
                logger.info(f"Awarded {rewards['xp']} XP to user {user_id}")
            
            # Award badge
            if 'badge' in rewards:
                from .gamification import award_badge
                award_badge(user_id, rewards['badge'])
                logger.info(f"Awarded badge {rewards['badge']} to user {user_id}")
            
            # Create notification
            from .notification_manager import create_notification, NotificationType
            create_notification(
                user_id=user_id,
                type=NotificationType.ACHIEVEMENT,
                template_key='challenge_completed',
                challenge_name=challenge.title,
                xp=rewards.get('xp', 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to award rewards for challenge {challenge_id}: {e}")
    
    def get_user_challenges(self, user_id: int) -> List[Challenge]:
        """Get all challenges a user has joined."""
        challenge_ids = self._user_challenges.get(user_id, [])
        return [self._challenges[cid] for cid in challenge_ids if cid in self._challenges]
    
    def get_user_progress(self, user_id: int, challenge_id: str) -> Optional[ChallengeProgress]:
        """Get user progress for a specific challenge."""
        return self._user_progress.get(challenge_id, {}).get(user_id)
    
    def get_challenge_leaderboard(self, challenge_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard for a challenge."""
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            return []
        
        progress_list = []
        for user_id, progress in self._user_progress.get(challenge_id, {}).items():
            # Get username
            username = self._get_username(user_id)
            progress_list.append({
                'user_id': user_id,
                'username': username,
                'progress': progress.progress_value,
                'percentage': (progress.progress_value / challenge.target_value) * 100 if challenge.target_value > 0 else 0,
                'completed': progress.completed
            })
        
        # Sort by progress (descending)
        progress_list.sort(key=lambda x: x['progress'], reverse=True)
        
        return progress_list[:limit]
    
    def _get_username(self, user_id: int) -> str:
        """Get username from database."""
        try:
            from database import get_user_by_id
            user = get_user_by_id(user_id)
            return user.get('username', f'User_{user_id}') if user else f'User_{user_id}'
        except:
            return f'User_{user_id}'
    
    def get_challenge_statistics(self, challenge_id: str) -> Dict[str, Any]:
        """Get statistics for a challenge."""
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            return {}
        
        participants = challenge.participants
        completed = challenge.completed_by
        
        return {
            'total_participants': len(participants),
            'completed': len(completed),
            'completion_rate': (len(completed) / len(participants)) * 100 if participants else 0,
            'average_progress': challenge.progress,
            'current_value': challenge.current_value,
            'target_value': challenge.target_value,
            'time_remaining': (challenge.end_date - datetime.now()).days if challenge.end_date > datetime.now() else 0
        }
    
    def update_challenge_status(self, challenge_id: str, status: ChallengeStatus) -> bool:
        """Update challenge status."""
        with self._lock:
            challenge = self._challenges.get(challenge_id)
            if not challenge:
                return False
            
            challenge.status = status
            challenge.updated_at = datetime.now()
            return True
    
    def delete_challenge(self, challenge_id: str) -> bool:
        """Delete a challenge."""
        with self._lock:
            if challenge_id in self._challenges:
                del self._challenges[challenge_id]
                self._user_progress.pop(challenge_id, None)
                # Remove from user challenges
                for user_id in self._user_challenges:
                    self._user_challenges[user_id] = [
                        cid for cid in self._user_challenges[user_id] if cid != challenge_id
                    ]
                logger.info(f"Deleted challenge {challenge_id}")
                return True
            return False
    
    def _cleanup_worker(self) -> None:
        """Background worker for cleaning up expired challenges."""
        while True:
            try:
                time.sleep(3600)  # Run every hour
                self._cleanup_expired_challenges()
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
    
    def _cleanup_expired_challenges(self) -> None:
        """Mark expired challenges as expired."""
        now = datetime.now()
        with self._lock:
            for challenge in self._challenges.values():
                if challenge.status == ChallengeStatus.ACTIVE and challenge.end_date < now:
                    challenge.status = ChallengeStatus.EXPIRED
                    challenge.updated_at = now
                    logger.info(f"Challenge {challenge.id} expired")
    
    def get_challenge_stats(self) -> Dict[str, Any]:
        """Get challenge manager statistics."""
        stats = {
            'total_challenges': len(self._challenges),
            'by_status': {},
            'by_type': {},
            'by_category': {},
            'active_challenges': 0,
            'total_participants': 0
        }
        
        for challenge in self._challenges.values():
            stats['by_status'][challenge.status.value] = stats['by_status'].get(challenge.status.value, 0) + 1
            stats['by_type'][challenge.type.value] = stats['by_type'].get(challenge.type.value, 0) + 1
            stats['by_category'][challenge.category.value] = stats['by_category'].get(challenge.category.value, 0) + 1
            
            if challenge.status == ChallengeStatus.ACTIVE:
                stats['active_challenges'] += 1
                stats['total_participants'] += len(challenge.participants)
        
        return stats


# Global challenge manager instance
_challenge_manager: Optional[ChallengeManager] = None
_challenge_manager_lock = threading.Lock()


def get_challenge_manager() -> ChallengeManager:
    """Get or create global challenge manager instance."""
    global _challenge_manager
    with _challenge_manager_lock:
        if _challenge_manager is None:
            _challenge_manager = ChallengeManager()
        return _challenge_manager


def create_challenge(
    title: str,
    description: str,
    type: ChallengeType,
    category: ChallengeCategory,
    created_by: int,
    start_date: datetime,
    end_date: datetime,
    target_metric: str,
    target_value: float,
    **kwargs
) -> Challenge:
    """Convenience function to create a challenge."""
    manager = get_challenge_manager()
    return manager.create_challenge(
        title, description, type, category, created_by,
        start_date, end_date, target_metric, target_value, **kwargs
    )


def get_challenge(challenge_id: str) -> Optional[Challenge]:
    """Convenience function to get a challenge."""
    manager = get_challenge_manager()
    return manager.get_challenge(challenge_id)


def get_active_challenges() -> List[Challenge]:
    """Convenience function to get active challenges."""
    manager = get_challenge_manager()
    return manager.get_active_challenges()


def join_challenge(challenge_id: str, user_id: int) -> bool:
    """Convenience function to join a challenge."""
    manager = get_challenge_manager()
    return manager.join_challenge(challenge_id, user_id)


def update_challenge_progress(challenge_id: str, user_id: int, value: float) -> bool:
    """Convenience function to update challenge progress."""
    manager = get_challenge_manager()
    return manager.update_progress(challenge_id, user_id, value)