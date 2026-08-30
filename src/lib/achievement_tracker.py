"""
Achievement Tracker for EcoBuddy AI
Tracks user achievements, milestones, and progress towards goals.
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


class AchievementCategory(Enum):
    """Achievement categories."""
    ASSESSMENT = "assessment"
    FOOTPRINT = "footprint"
    STREAK = "streak"
    QUESTS = "quests"
    COMMUNITY = "community"
    CHALLENGES = "challenges"
    BADGES = "badges"
    LEVEL = "level"
    SPECIAL = "special"


class AchievementTier(Enum):
    """Achievement tiers."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


@dataclass
class Achievement:
    """Data class for an achievement."""
    id: str
    name: str
    description: str
    category: AchievementCategory
    tier: AchievementTier
    icon: str
    points: int
    requirements: Dict[str, Any]
    is_hidden: bool = False
    parent_achievement: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserAchievement:
    """Data class for user achievement progress."""
    achievement_id: str
    user_id: int
    unlocked: bool = False
    progress: float = 0.0
    unlocked_at: Optional[datetime] = None
    current_streak: int = 0
    best_streak: int = 0


class AchievementTracker:
    """
    Tracks user achievements, milestones, and progress.
    """
    
    def __init__(self):
        self._achievements: Dict[str, Achievement] = {}
        self._user_achievements: Dict[int, Dict[str, UserAchievement]] = {}
        self._lock = threading.Lock()
        
        # Load default achievements
        self._load_default_achievements()
        
        logger.info("AchievementTracker initialized")
    
    def _load_default_achievements(self) -> None:
        """Load default achievements."""
        defaults = [
            # Assessment achievements
            Achievement(
                id="first_assessment",
                name="First Step",
                description="Complete your first sustainability assessment",
                category=AchievementCategory.ASSESSMENT,
                tier=AchievementTier.BRONZE,
                icon="📝",
                points=10,
                requirements={'assessments': 1}
            ),
            Achievement(
                id="assessment_10",
                name="Eco Learner",
                description="Complete 10 assessments",
                category=AchievementCategory.ASSESSMENT,
                tier=AchievementTier.SILVER,
                icon="📚",
                points=50,
                requirements={'assessments': 10}
            ),
            Achievement(
                id="assessment_50",
                name="Eco Scholar",
                description="Complete 50 assessments",
                category=AchievementCategory.ASSESSMENT,
                tier=AchievementTier.GOLD,
                icon="🎓",
                points=150,
                requirements={'assessments': 50}
            ),
            Achievement(
                id="assessment_100",
                name="Eco Master",
                description="Complete 100 assessments",
                category=AchievementCategory.ASSESSMENT,
                tier=AchievementTier.PLATINUM,
                icon="👑",
                points=300,
                requirements={'assessments': 100}
            ),
            
            # Streak achievements
            Achievement(
                id="streak_7",
                name="Week Warrior",
                description="Maintain a 7-day streak",
                category=AchievementCategory.STREAK,
                tier=AchievementTier.BRONZE,
                icon="🔥",
                points=20,
                requirements={'streak': 7}
            ),
            Achievement(
                id="streak_30",
                name="Month Master",
                description="Maintain a 30-day streak",
                category=AchievementCategory.STREAK,
                tier=AchievementTier.SILVER,
                icon="🌙",
                points=75,
                requirements={'streak': 30}
            ),
            Achievement(
                id="streak_100",
                name="Century Club",
                description="Maintain a 100-day streak",
                category=AchievementCategory.STREAK,
                tier=AchievementTier.GOLD,
                icon="💯",
                points=200,
                requirements={'streak': 100}
            ),
            Achievement(
                id="streak_365",
                name="Year of Green",
                description="Maintain a 365-day streak",
                category=AchievementCategory.STREAK,
                tier=AchievementTier.DIAMOND,
                icon="🌟",
                points=500,
                requirements={'streak': 365}
            ),
            
            # Footprint achievements
            Achievement(
                id="footprint_1000",
                name="Carbon Reducer",
                description="Reduce footprint below 1000 kg CO₂",
                category=AchievementCategory.FOOTPRINT,
                tier=AchievementTier.SILVER,
                icon="🌿",
                points=50,
                requirements={'footprint': 1000}
            ),
            Achievement(
                id="footprint_500",
                name="Eco Champion",
                description="Reduce footprint below 500 kg CO₂",
                category=AchievementCategory.FOOTPRINT,
                tier=AchievementTier.GOLD,
                icon="🏆",
                points=150,
                requirements={'footprint': 500}
            ),
            Achievement(
                id="footprint_100",
                name="Carbon Zero Hero",
                description="Reduce footprint below 100 kg CO₂",
                category=AchievementCategory.FOOTPRINT,
                tier=AchievementTier.PLATINUM,
                icon="⭐",
                points=300,
                requirements={'footprint': 100}
            ),
            
            # Quest achievements
            Achievement(
                id="quest_5",
                name="Quest Novice",
                description="Complete 5 quests",
                category=AchievementCategory.QUESTS,
                tier=AchievementTier.BRONZE,
                icon="🎯",
                points=25,
                requirements={'quests': 5}
            ),
            Achievement(
                id="quest_25",
                name="Quest Master",
                description="Complete 25 quests",
                category=AchievementCategory.QUESTS,
                tier=AchievementTier.SILVER,
                icon="🏅",
                points=100,
                requirements={'quests': 25}
            ),
            Achievement(
                id="quest_50",
                name="Quest Legend",
                description="Complete 50 quests",
                category=AchievementCategory.QUESTS,
                tier=AchievementTier.GOLD,
                icon="👑",
                points=250,
                requirements={'quests': 50}
            ),
            
            # Level achievements
            Achievement(
                id="level_5",
                name="Eco Learner",
                description="Reach level 5",
                category=AchievementCategory.LEVEL,
                tier=AchievementTier.BRONZE,
                icon="🌱",
                points=30,
                requirements={'level': 5}
            ),
            Achievement(
                id="level_10",
                name="Eco Warrior",
                description="Reach level 10",
                category=AchievementCategory.LEVEL,
                tier=AchievementTier.SILVER,
                icon="⚔️",
                points=80,
                requirements={'level': 10}
            ),
            Achievement(
                id="level_25",
                name="Eco Guardian",
                description="Reach level 25",
                category=AchievementCategory.LEVEL,
                tier=AchievementTier.GOLD,
                icon="🛡️",
                points=200,
                requirements={'level': 25}
            ),
            Achievement(
                id="level_50",
                name="Eco Champion",
                description="Reach level 50",
                category=AchievementCategory.LEVEL,
                tier=AchievementTier.PLATINUM,
                icon="🌟",
                points=400,
                requirements={'level': 50}
            ),
            Achievement(
                id="level_100",
                name="Eco Legend",
                description="Reach level 100",
                category=AchievementCategory.LEVEL,
                tier=AchievementTier.DIAMOND,
                icon="👑",
                points=1000,
                requirements={'level': 100}
            ),
            
            # Community achievements
            Achievement(
                id="join_team",
                name="Team Player",
                description="Join a team",
                category=AchievementCategory.COMMUNITY,
                tier=AchievementTier.BRONZE,
                icon="🤝",
                points=15,
                requirements={'team_joined': True}
            ),
            Achievement(
                id="challenge_1",
                name="Challenge Accepted",
                description="Complete your first challenge",
                category=AchievementCategory.CHALLENGES,
                tier=AchievementTier.BRONZE,
                icon="🏁",
                points=20,
                requirements={'challenges': 1}
            ),
            Achievement(
                id="challenge_10",
                name="Challenge Master",
                description="Complete 10 challenges",
                category=AchievementCategory.CHALLENGES,
                tier=AchievementTier.SILVER,
                icon="🏆",
                points=100,
                requirements={'challenges': 10}
            ),
            Achievement(
                id="challenge_50",
                name="Challenge Legend",
                description="Complete 50 challenges",
                category=AchievementCategory.CHALLENGES,
                tier=AchievementTier.GOLD,
                icon="👑",
                points=300,
                requirements={'challenges': 50}
            ),
            
            # Badge achievements
            Achievement(
                id="badge_collector_5",
                name="Badge Collector",
                description="Collect 5 badges",
                category=AchievementCategory.BADGES,
                tier=AchievementTier.BRONZE,
                icon="🏅",
                points=25,
                requirements={'badges': 5}
            ),
            Achievement(
                id="badge_collector_15",
                name="Badge Master",
                description="Collect 15 badges",
                category=AchievementCategory.BADGES,
                tier=AchievementTier.SILVER,
                icon="🎖️",
                points=75,
                requirements={'badges': 15}
            ),
            Achievement(
                id="badge_collector_30",
                name="Badge Legend",
                description="Collect 30 badges",
                category=AchievementCategory.BADGES,
                tier=AchievementTier.GOLD,
                icon="🌟",
                points=200,
                requirements={'badges': 30}
            ),
            
            # Special achievements
            Achievement(
                id="all_streak",
                name="Streak Complete",
                description="Unlock all streak achievements",
                category=AchievementCategory.SPECIAL,
                tier=AchievementTier.DIAMOND,
                icon="💎",
                points=500,
                requirements={'streak_achievements': 4},
                is_hidden=True
            ),
            Achievement(
                id="all_assessment",
                name="Assessment Complete",
                description="Unlock all assessment achievements",
                category=AchievementCategory.SPECIAL,
                tier=AchievementTier.DIAMOND,
                icon="💎",
                points=500,
                requirements={'assessment_achievements': 4},
                is_hidden=True
            )
        ]
        
        for achievement in defaults:
            self._achievements[achievement.id] = achievement
        
        logger.info(f"Loaded {len(defaults)} default achievements")
    
    def get_achievement(self, achievement_id: str) -> Optional[Achievement]:
        """Get an achievement by ID."""
        return self._achievements.get(achievement_id)
    
    def get_all_achievements(
        self,
        category: Optional[AchievementCategory] = None,
        tier: Optional[AchievementTier] = None,
        include_hidden: bool = False
    ) -> List[Achievement]:
        """Get all achievements with optional filters."""
        achievements = list(self._achievements.values())
        
        if not include_hidden:
            achievements = [a for a in achievements if not a.is_hidden]
        if category:
            achievements = [a for a in achievements if a.category == category]
        if tier:
            achievements = [a for a in achievements if a.tier == tier]
        
        return achievements
    
    def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        """Get all achievements for a user."""
        return list(self._user_achievements.get(user_id, {}).values())
    
    def get_unlocked_achievements(self, user_id: int) -> List[UserAchievement]:
        """Get unlocked achievements for a user."""
        user_achievements = self._user_achievements.get(user_id, {})
        return [ua for ua in user_achievements.values() if ua.unlocked]
    
    def check_achievements(self, user_id: int, context: Dict[str, Any]) -> List[Achievement]:
        """
        Check and unlock achievements based on context.
        
        Args:
            user_id: User ID
            context: Context data (assessments, streak, etc.)
        
        Returns:
            List of newly unlocked achievements
        """
        unlocked = []
        
        for achievement in self._achievements.values():
            if achievement.id in self._user_achievements.get(user_id, {}):
                user_achievement = self._user_achievements[user_id][achievement.id]
                if user_achievement.unlocked:
                    continue
            else:
                # Initialize user achievement
                if user_id not in self._user_achievements:
                    self._user_achievements[user_id] = {}
                self._user_achievements[user_id][achievement.id] = UserAchievement(
                    achievement_id=achievement.id,
                    user_id=user_id
                )
                user_achievement = self._user_achievements[user_id][achievement.id]
            
            # Check if requirements are met
            if self._check_requirements(achievement.requirements, context):
                user_achievement.unlocked = True
                user_achievement.unlocked_at = datetime.now()
                unlocked.append(achievement)
                
                # Create notification
                from .notification_manager import create_notification, NotificationType
                create_notification(
                    user_id=user_id,
                    type=NotificationType.ACHIEVEMENT,
                    template_key='new_badge',
                    badge_name=achievement.name,
                    reason="achieving a milestone"
                )
                
                logger.info(f"User {user_id} unlocked achievement: {achievement.name}")
        
        return unlocked
    
    def _check_requirements(self, requirements: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if user meets achievement requirements."""
        for key, value in requirements.items():
            if key not in context:
                return False
            
            if isinstance(value, dict):
                if not self._check_complex_requirement(value, context[key]):
                    return False
            else:
                if context[key] < value:
                    return False
        
        return True
    
    def _check_complex_requirement(self, requirement: Dict[str, Any], actual_value: Any) -> bool:
        """Check complex requirements with operators."""
        operator = requirement.get('operator', 'gte')
        value = requirement.get('value')
        
        if operator == 'gte':
            return actual_value >= value
        elif operator == 'lte':
            return actual_value <= value
        elif operator == 'eq':
            return actual_value == value
        elif operator == 'gt':
            return actual_value > value
        elif operator == 'lt':
            return actual_value < value
        elif operator == 'between':
            return value[0] <= actual_value <= value[1]
        
        return False
    
    def update_progress(
        self,
        user_id: int,
        achievement_id: str,
        progress: float
    ) -> bool:
        """Update progress for a specific achievement."""
        with self._lock:
            achievement = self._achievements.get(achievement_id)
            if not achievement:
                return False
            
            if user_id not in self._user_achievements:
                self._user_achievements[user_id] = {}
            
            if achievement_id not in self._user_achievements[user_id]:
                self._user_achievements[user_id][achievement_id] = UserAchievement(
                    achievement_id=achievement_id,
                    user_id=user_id
                )
            
            user_achievement = self._user_achievements[user_id][achievement_id]
            user_achievement.progress = min(progress, 100.0)
            return True
    
    def get_achievement_stats(self, user_id: int) -> Dict[str, Any]:
        """Get achievement statistics for a user."""
        user_achievements = self._user_achievements.get(user_id, {})
        unlocked = [ua for ua in user_achievements.values() if ua.unlocked]
        
        stats = {
            'total': len(self._achievements),
            'unlocked': len(unlocked),
            'completion_rate': (len(unlocked) / len(self._achievements)) * 100 if self._achievements else 0,
            'by_category': {},
            'by_tier': {},
            'recent_unlocks': []
        }
        
        for ua in unlocked:
            achievement = self._achievements.get(ua.achievement_id)
            if achievement:
                stats['by_category'][achievement.category.value] = stats['by_category'].get(achievement.category.value, 0) + 1
                stats['by_tier'][achievement.tier.value] = stats['by_tier'].get(achievement.tier.value, 0) + 1
        
        # Get recent unlocks
        recent = sorted(
            [ua for ua in unlocked if ua.unlocked_at],
            key=lambda x: x.unlocked_at,
            reverse=True
        )[:5]
        stats['recent_unlocks'] = [
            {
                'id': ua.achievement_id,
                'unlocked_at': ua.unlocked_at.isoformat()
            }
            for ua in recent
        ]
        
        return stats
    
    def get_next_achievements(self, user_id: int) -> List[Achievement]:
        """Get achievements the user is close to unlocking."""
        user_achievements = self._user_achievements.get(user_id, {})
        next_achievements = []
        
        for achievement in self._achievements.values():
            if achievement.id in user_achievements and user_achievements[achievement.id].unlocked:
                continue
            
            # Calculate progress based on requirements
            progress = 0
            total_requirements = len(achievement.requirements)
            met = 0
            
            # Use context from user data
            context = self._get_user_context(user_id)
            
            for key, value in achievement.requirements.items():
                if key in context:
                    if isinstance(value, dict):
                        if self._check_complex_requirement(value, context[key]):
                            met += 1
                    else:
                        if context[key] >= value:
                            met += 1
            
            if total_requirements > 0:
                progress = (met / total_requirements) * 100
            
            if progress >= 50:  # 50%+ progress
                next_achievements.append(achievement)
        
        return next_achievements[:5]
    
    def _get_user_context(self, user_id: int) -> Dict[str, Any]:
        """Get user context for achievement checking."""
        context = {}
        
        try:
            from database import get_assessments
            from .gamification_v2 import get_user_level, get_user_coins
            
            # Assessments
            assessments = get_assessments(user_id)
            context['assessments'] = len(assessments)
            
            # Streak
            from .gamification import get_user_streak
            context['streak'] = get_user_streak(user_id)
            
            # Level
            level = get_user_level(user_id)
            context['level'] = level.level if level else 0
            
            # Quests completed
            # This would come from quest system
            context['quests'] = 0
            
            # Challenges completed
            # This would come from challenge system
            context['challenges'] = 0
            
            # Badges
            context['badges'] = 0
            
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
        
        return context


# Global achievement tracker instance
_achievement_tracker: Optional[AchievementTracker] = None
_achievement_tracker_lock = threading.Lock()


def get_achievement_tracker() -> AchievementTracker:
    """Get or create global achievement tracker instance."""
    global _achievement_tracker
    with _achievement_tracker_lock:
        if _achievement_tracker is None:
            _achievement_tracker = AchievementTracker()
        return _achievement_tracker


def check_achievements(user_id: int, context: Dict[str, Any]) -> List[Achievement]:
    """Convenience function to check and unlock achievements."""
    tracker = get_achievement_tracker()
    return tracker.check_achievements(user_id, context)


def get_unlocked_achievements(user_id: int) -> List[UserAchievement]:
    """Convenience function to get unlocked achievements."""
    tracker = get_achievement_tracker()
    return tracker.get_unlocked_achievements(user_id)