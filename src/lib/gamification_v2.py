"""
Gamification V2 for EcoBuddy AI
Advanced gamification system with quests, levels, XP, and virtual rewards.
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
import math

logger = logging.getLogger(__name__)


class QuestType(Enum):
    """Types of quests."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SPECIAL = "special"
    STORY = "story"
    BOSS = "boss"


class QuestStatus(Enum):
    """Quest status states."""
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class QuestDifficulty(Enum):
    """Quest difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class Quest:
    """Data class for a quest."""
    id: str
    title: str
    description: str
    type: QuestType
    difficulty: QuestDifficulty
    xp_reward: int
    coin_reward: int = 0
    requirements: Dict[str, Any] = field(default_factory=dict)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    duration_days: int = 1
    is_repeatable: bool = False
    prerequisites: List[str] = field(default_factory=list)
    rewards: Dict[str, Any] = field(default_factory=dict)
    icon: str = "🎯"
    category: str = "general"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type.value,
            'difficulty': self.difficulty.value,
            'xp_reward': self.xp_reward,
            'coin_reward': self.coin_reward,
            'requirements': self.requirements,
            'steps': self.steps,
            'duration_days': self.duration_days,
            'is_repeatable': self.is_repeatable,
            'prerequisites': self.prerequisites,
            'rewards': self.rewards,
            'icon': self.icon,
            'category': self.category
        }


@dataclass
class UserQuest:
    """Data class for user quest progress."""
    quest_id: str
    user_id: int
    status: QuestStatus
    progress: float = 0.0
    steps_completed: List[int] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserLevel:
    """Data class for user level."""
    user_id: int
    level: int = 1
    xp: int = 0
    xp_to_next: int = 100
    total_xp: int = 0
    rank: str = "Novice"
    tier: int = 1
    prestige: int = 0


class GamificationV2:
    """
    Advanced gamification system with quests, levels, and virtual rewards.
    """
    
    def __init__(self):
        self._quests: Dict[str, Quest] = {}
        self._user_quests: Dict[int, Dict[str, UserQuest]] = {}  # user_id -> {quest_id: UserQuest}
        self._user_levels: Dict[int, UserLevel] = {}
        self._user_coins: Dict[int, int] = {}
        self._user_inventory: Dict[int, Dict[str, int]] = {}  # user_id -> {item_id: quantity}
        self._lock = threading.Lock()
        self._quest_counter = 0
        
        # Load default quests
        self._load_default_quests()
        
        # Start background threads
        self._stop_worker = False
        self._worker_thread = threading.Thread(target=self._background_worker, daemon=True)
        self._worker_thread.start()
        
        logger.info("GamificationV2 initialized")
    
    def _load_default_quests(self) -> None:
        """Load default quests."""
        now = datetime.now()
        
        default_quests = [
            Quest(
                id=self._generate_quest_id(),
                title="Eco Warrior Daily",
                description="Complete your daily sustainability assessment",
                type=QuestType.DAILY,
                difficulty=QuestDifficulty.EASY,
                xp_reward=50,
                coin_reward=10,
                requirements={'type': 'assessment', 'count': 1},
                icon="📝",
                category="assessment"
            ),
            Quest(
                id=self._generate_quest_id(),
                title="Carbon Slayer",
                description="Reduce your carbon footprint by 10%",
                type=QuestType.WEEKLY,
                difficulty=QuestDifficulty.MEDIUM,
                xp_reward=150,
                coin_reward=30,
                requirements={'type': 'footprint_reduction', 'percentage': 10},
                duration_days=7,
                icon="⚔️",
                category="footprint"
            ),
            Quest(
                id=self._generate_quest_id(),
                title="Green Commuter",
                description="Use sustainable transport for 5 days",
                type=QuestType.WEEKLY,
                difficulty=QuestDifficulty.MEDIUM,
                xp_reward=120,
                coin_reward=25,
                requirements={'type': 'sustainable_trips', 'count': 5},
                duration_days=7,
                icon="🚲",
                category="transport"
            ),
            Quest(
                id=self._generate_quest_id(),
                title="Energy Saver",
                description="Reduce electricity usage by 20%",
                type=QuestType.MONTHLY,
                difficulty=QuestDifficulty.HARD,
                xp_reward=300,
                coin_reward=50,
                requirements={'type': 'energy_reduction', 'percentage': 20},
                duration_days=30,
                icon="💡",
                category="energy"
            ),
            Quest(
                id=self._generate_quest_id(),
                title="Plant-Based Champion",
                description="Eat plant-based meals for 7 days",
                type=QuestType.WEEKLY,
                difficulty=QuestDifficulty.MEDIUM,
                xp_reward=100,
                coin_reward=20,
                requirements={'type': 'plant_meals', 'count': 7},
                duration_days=7,
                icon="🥗",
                category="diet"
            ),
            Quest(
                id=self._generate_quest_id(),
                title="Waste Warrior",
                description="Recycle and compost for 14 days",
                type=QuestType.MONTHLY,
                difficulty=QuestDifficulty.HARD,
                xp_reward=250,
                coin_reward=40,
                requirements={'type': 'waste_reduction', 'count': 14},
                duration_days=14,
                icon="♻️",
                category="waste"
            ),
            Quest(
                id=self._generate_quest_id(),
                title="Boss Challenge: Carbon Zero",
                description="Achieve a carbon footprint below 100kg CO₂",
                type=QuestType.BOSS,
                difficulty=QuestDifficulty.LEGENDARY,
                xp_reward=1000,
                coin_reward=200,
                requirements={'type': 'footprint', 'target': 100},
                duration_days=30,
                icon="👑",
                category="footprint",
                rewards={'badge': 'carbon_zero', 'title': 'Carbon Zero Hero'}
            ),
            Quest(
                id=self._generate_quest_id(),
                title="Eco Story: The Green Journey",
                description="Complete all daily quests for 7 days",
                type=QuestType.STORY,
                difficulty=QuestDifficulty.EPIC,
                xp_reward=500,
                coin_reward=100,
                requirements={'type': 'daily_quests', 'count': 7},
                duration_days=7,
                icon="📖",
                category="story",
                rewards={'badge': 'story_master', 'title': 'Story Weaver'}
            )
        ]
        
        for quest in default_quests:
            self._quests[quest.id] = quest
        
        logger.info(f"Loaded {len(default_quests)} default quests")
    
    def _generate_quest_id(self) -> str:
        """Generate unique quest ID."""
        self._quest_counter += 1
        timestamp = int(time.time() * 1000)
        return f"quest_{timestamp}_{self._quest_counter}"
    
    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Get a quest by ID."""
        return self._quests.get(quest_id)
    
    def get_all_quests(
        self,
        quest_type: Optional[QuestType] = None,
        difficulty: Optional[QuestDifficulty] = None,
        category: Optional[str] = None
    ) -> List[Quest]:
        """Get all quests with optional filters."""
        quests = list(self._quests.values())
        
        if quest_type:
            quests = [q for q in quests if q.type == quest_type]
        if difficulty:
            quests = [q for q in quests if q.difficulty == difficulty]
        if category:
            quests = [q for q in quests if q.category == category]
        
        return quests
    
    def get_available_quests(self, user_id: int) -> List[Quest]:
        """Get quests available for a user."""
        user_quests = self._user_quests.get(user_id, {})
        available = []
        
        for quest in self._quests.values():
            # Check if already active or completed
            if quest.id in user_quests:
                continue
            
            # Check prerequisites
            if quest.prerequisites:
                if not all(p in user_quests for p in quest.prerequisites):
                    continue
            
            available.append(quest)
        
        return available
    
    def get_active_quests(self, user_id: int) -> List[UserQuest]:
        """Get active quests for a user."""
        user_quests = self._user_quests.get(user_id, {})
        return [
            uq for uq in user_quests.values()
            if uq.status == QuestStatus.ACTIVE
        ]
    
    def get_completed_quests(self, user_id: int) -> List[UserQuest]:
        """Get completed quests for a user."""
        user_quests = self._user_quests.get(user_id, {})
        return [
            uq for uq in user_quests.values()
            if uq.status == QuestStatus.COMPLETED
        ]
    
    def accept_quest(self, user_id: int, quest_id: str) -> bool:
        """Accept a quest."""
        with self._lock:
            quest = self._quests.get(quest_id)
            if not quest:
                return False
            
            if user_id not in self._user_quests:
                self._user_quests[user_id] = {}
            
            if quest_id in self._user_quests[user_id]:
                return False
            
            self._user_quests[user_id][quest_id] = UserQuest(
                quest_id=quest_id,
                user_id=user_id,
                status=QuestStatus.ACTIVE,
                expired_at=datetime.now() + timedelta(days=quest.duration_days)
            )
            
            logger.info(f"User {user_id} accepted quest {quest_id}")
            return True
    
    def update_quest_progress(
        self,
        user_id: int,
        quest_id: str,
        progress: float
    ) -> bool:
        """Update quest progress."""
        with self._lock:
            if user_id not in self._user_quests:
                return False
            
            if quest_id not in self._user_quests[user_id]:
                return False
            
            user_quest = self._user_quests[user_id][quest_id]
            
            if user_quest.status != QuestStatus.ACTIVE:
                return False
            
            user_quest.progress = min(progress, 100.0)
            
            # Check if completed
            if user_quest.progress >= 100.0:
                self._complete_quest(user_id, quest_id)
            
            return True
    
    def _complete_quest(self, user_id: int, quest_id: str) -> None:
        """Complete a quest and award rewards."""
        user_quest = self._user_quests[user_id][quest_id]
        user_quest.status = QuestStatus.COMPLETED
        user_quest.completed_at = datetime.now()
        
        quest = self._quests.get(quest_id)
        if not quest:
            return
        
        # Award XP
        self.add_xp(user_id, quest.xp_reward)
        
        # Award coins
        if quest.coin_reward > 0:
            self.add_coins(user_id, quest.coin_reward)
        
        # Award special rewards
        if quest.rewards:
            if 'badge' in quest.rewards:
                self._award_badge(user_id, quest.rewards['badge'])
            if 'title' in quest.rewards:
                self._award_title(user_id, quest.rewards['title'])
        
        # Create notification
        from .notification_manager import create_notification, NotificationType
        create_notification(
            user_id=user_id,
            type=NotificationType.ACHIEVEMENT,
            template_key='challenge_completed',
            challenge_name=quest.title,
            xp=quest.xp_reward
        )
        
        logger.info(f"User {user_id} completed quest {quest_id}")
    
    def add_xp(self, user_id: int, xp: int) -> None:
        """Add XP to a user."""
        with self._lock:
            if user_id not in self._user_levels:
                self._user_levels[user_id] = UserLevel(user_id=user_id)
            
            level = self._user_levels[user_id]
            level.xp += xp
            level.total_xp += xp
            
            # Check for level up
            while level.xp >= level.xp_to_next:
                level.xp -= level.xp_to_next
                level.level += 1
                level.xp_to_next = self._calculate_xp_to_next(level.level)
                
                # Level up rewards
                self._on_level_up(user_id, level.level)
            
            # Update rank
            level.rank = self._calculate_rank(level.level)
    
    def _calculate_xp_to_next(self, level: int) -> int:
        """Calculate XP needed for next level."""
        return int(100 * math.pow(1.2, level - 1))  # Exponential growth
    
    def _calculate_rank(self, level: int) -> str:
        """Calculate rank based on level."""
        if level >= 100:
            return "Eco Legend"
        elif level >= 75:
            return "Green Master"
        elif level >= 50:
            return "Eco Champion"
        elif level >= 30:
            return "Green Guardian"
        elif level >= 15:
            return "Eco Warrior"
        elif level >= 5:
            return "Eco Learner"
        else:
            return "Novice"
    
    def _on_level_up(self, user_id: int, level: int) -> None:
        """Handle level up events."""
        # Create notification
        from .notification_manager import create_notification, NotificationType
        create_notification(
            user_id=user_id,
            type=NotificationType.ACHIEVEMENT,
            template_key='level_up',
            level=level,
            xp=self._user_levels[user_id].total_xp
        )
        
        # Check for level milestones
        if level in [5, 10, 25, 50, 75, 100]:
            self._award_badge(user_id, f'level_{level}')
        
        logger.info(f"User {user_id} reached level {level}")
    
    def _award_badge(self, user_id: int, badge_id: str) -> None:
        """Award a badge to a user."""
        try:
            from .gamification import award_badge
            award_badge(user_id, badge_id)
        except Exception as e:
            logger.error(f"Failed to award badge {badge_id}: {e}")
    
    def _award_title(self, user_id: int, title: str) -> None:
        """Award a title to a user."""
        # Store title in user metadata
        try:
            from database import update_user_metadata
            update_user_metadata(user_id, {'title': title})
        except Exception as e:
            logger.error(f"Failed to award title {title}: {e}")
    
    def add_coins(self, user_id: int, coins: int) -> None:
        """Add coins to a user."""
        with self._lock:
            if user_id not in self._user_coins:
                self._user_coins[user_id] = 0
            self._user_coins[user_id] += coins
    
    def get_user_level(self, user_id: int) -> Optional[UserLevel]:
        """Get user level information."""
        return self._user_levels.get(user_id)
    
    def get_user_coins(self, user_id: int) -> int:
        """Get user coin balance."""
        return self._user_coins.get(user_id, 0)
    
    def get_user_quests(self, user_id: int) -> Dict[str, UserQuest]:
        """Get all user quests."""
        return self._user_quests.get(user_id, {})
    
    def _background_worker(self) -> None:
        """Background worker for quest expiration."""
        while not self._stop_worker:
            try:
                time.sleep(60)  # Check every minute
                self._expire_quests()
            except Exception as e:
                logger.error(f"Background worker error: {e}")
    
    def _expire_quests(self) -> None:
        """Expire quests that have passed their deadline."""
        now = datetime.now()
        
        with self._lock:
            for user_id, quests in self._user_quests.items():
                for quest_id, user_quest in quests.items():
                    if (user_quest.status == QuestStatus.ACTIVE and
                        user_quest.expired_at and
                        user_quest.expired_at < now):
                        user_quest.status = QuestStatus.EXPIRED
                        logger.info(f"Quest {quest_id} expired for user {user_id}")
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get gamification leaderboard."""
        leaderboard = []
        
        for user_id, level in self._user_levels.items():
            leaderboard.append({
                'user_id': user_id,
                'username': self._get_username(user_id),
                'level': level.level,
                'xp': level.total_xp,
                'rank': level.rank
            })
        
        leaderboard.sort(key=lambda x: x['xp'], reverse=True)
        return leaderboard[:limit]
    
    def _get_username(self, user_id: int) -> str:
        """Get username from database."""
        try:
            from database import get_user_by_id
            user = get_user_by_id(user_id)
            return user.get('username', f'User_{user_id}') if user else f'User_{user_id}'
        except:
            return f'User_{user_id}'
    
    def get_gamification_stats(self, user_id: int) -> Dict[str, Any]:
        """Get gamification statistics for a user."""
        stats = {
            'level': 0,
            'xp': 0,
            'xp_to_next': 0,
            'rank': 'Novice',
            'coins': 0,
            'active_quests': 0,
            'completed_quests': 0,
            'total_xp': 0
        }
        
        if user_id in self._user_levels:
            level = self._user_levels[user_id]
            stats['level'] = level.level
            stats['xp'] = level.xp
            stats['xp_to_next'] = level.xp_to_next
            stats['rank'] = level.rank
            stats['total_xp'] = level.total_xp
        
        stats['coins'] = self.get_user_coins(user_id)
        
        if user_id in self._user_quests:
            quests = self._user_quests[user_id].values()
            stats['active_quests'] = sum(1 for q in quests if q.status == QuestStatus.ACTIVE)
            stats['completed_quests'] = sum(1 for q in quests if q.status == QuestStatus.COMPLETED)
        
        return stats
    
    def stop(self) -> None:
        """Stop the gamification system."""
        self._stop_worker = True
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)


# Global gamification V2 instance
_gamification_v2: Optional[GamificationV2] = None
_gamification_v2_lock = threading.Lock()


def get_gamification_v2() -> GamificationV2:
    """Get or create global gamification V2 instance."""
    global _gamification_v2
    with _gamification_v2_lock:
        if _gamification_v2 is None:
            _gamification_v2 = GamificationV2()
        return _gamification_v2


def accept_quest(user_id: int, quest_id: str) -> bool:
    """Convenience function to accept a quest."""
    gamification = get_gamification_v2()
    return gamification.accept_quest(user_id, quest_id)


def update_quest_progress(user_id: int, quest_id: str, progress: float) -> bool:
    """Convenience function to update quest progress."""
    gamification = get_gamification_v2()
    return gamification.update_quest_progress(user_id, quest_id, progress)


def add_xp(user_id: int, xp: int) -> None:
    """Convenience function to add XP."""
    gamification = get_gamification_v2()
    gamification.add_xp(user_id, xp)


def add_coins(user_id: int, coins: int) -> None:
    """Convenience function to add coins."""
    gamification = get_gamification_v2()
    gamification.add_coins(user_id, coins)


def get_user_level(user_id: int) -> Optional[UserLevel]:
    """Convenience function to get user level."""
    gamification = get_gamification_v2()
    return gamification.get_user_level(user_id)


def get_user_coins(user_id: int) -> int:
    """Convenience function to get user coins."""
    gamification = get_gamification_v2()
    return gamification.get_user_coins(user_id)


def get_gamification_stats(user_id: int) -> Dict[str, Any]:
    """Convenience function to get gamification stats."""
    gamification = get_gamification_v2()
    return gamification.get_gamification_stats(user_id)