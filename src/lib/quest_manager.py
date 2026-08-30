"""
Quest Manager for EcoBuddy AI
Manages daily, weekly, monthly, and special quests.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import threading
import json

logger = logging.getLogger(__name__)


@dataclass
class QuestTemplate:
    """Template for generating quests."""
    id: str
    title: str
    description: str
    type: str  # daily, weekly, monthly, special
    difficulty: str  # easy, medium, hard, epic, legendary
    xp_reward: int
    coin_reward: int
    requirements: Dict[str, Any]
    duration_days: int
    icon: str
    category: str
    prerequisites: List[str] = field(default_factory=list)
    rewards: Dict[str, Any] = field(default_factory=dict)


class QuestManager:
    """
    Manages quest generation, assignment, and tracking.
    Generates daily, weekly, and monthly quests for users.
    """
    
    def __init__(self):
        self._quest_templates: Dict[str, QuestTemplate] = {}
        self._user_quests: Dict[int, Dict[str, Dict[str, Any]]] = {}  # user_id -> quest_id -> quest_data
        self._lock = threading.Lock()
        
        # Load quest templates
        self._load_quest_templates()
        
        # Start daily regeneration thread
        self._stop_worker = False
        self._worker_thread = threading.Thread(target=self._daily_quest_regen, daemon=True)
        self._worker_thread.start()
        
        logger.info("QuestManager initialized")
    
    def _load_quest_templates(self) -> None:
        """Load quest templates."""
        defaults = [
            # Daily quests
            QuestTemplate(
                id="daily_assessment",
                title="Daily Assessment",
                description="Complete your daily sustainability assessment",
                type="daily",
                difficulty="easy",
                xp_reward=50,
                coin_reward=10,
                requirements={'type': 'assessment', 'count': 1},
                duration_days=1,
                icon="📝",
                category="assessment"
            ),
            QuestTemplate(
                id="daily_log",
                title="Daily Log",
                description="Log your activities for today",
                type="daily",
                difficulty="easy",
                xp_reward=30,
                coin_reward=5,
                requirements={'type': 'log', 'count': 1},
                duration_days=1,
                icon="📊",
                category="logging"
            ),
            QuestTemplate(
                id="daily_transport",
                title="Green Commute",
                description="Use sustainable transport today",
                type="daily",
                difficulty="medium",
                xp_reward=40,
                coin_reward=8,
                requirements={'type': 'sustainable_transport', 'count': 1},
                duration_days=1,
                icon="🚲",
                category="transport"
            ),
            QuestTemplate(
                id="daily_plant_meal",
                title="Plant-Based Meal",
                description="Eat at least one plant-based meal today",
                type="daily",
                difficulty="easy",
                xp_reward=25,
                coin_reward=5,
                requirements={'type': 'plant_meal', 'count': 1},
                duration_days=1,
                icon="🥗",
                category="diet"
            ),
            
            # Weekly quests
            QuestTemplate(
                id="weekly_assessments",
                title="Assessment Streak",
                description="Complete assessments for 5 days this week",
                type="weekly",
                difficulty="medium",
                xp_reward=150,
                coin_reward=30,
                requirements={'type': 'assessments', 'count': 5},
                duration_days=7,
                icon="📚",
                category="assessment"
            ),
            QuestTemplate(
                id="weekly_transport",
                title="Green Week",
                description="Use sustainable transport 5 times this week",
                type="weekly",
                difficulty="medium",
                xp_reward=120,
                coin_reward=25,
                requirements={'type': 'sustainable_transport', 'count': 5},
                duration_days=7,
                icon="🚴",
                category="transport"
            ),
            QuestTemplate(
                id="weekly_energy",
                title="Energy Saver",
                description="Reduce energy usage by 15% this week",
                type="weekly",
                difficulty="hard",
                xp_reward=200,
                coin_reward=40,
                requirements={'type': 'energy_reduction', 'percentage': 15},
                duration_days=7,
                icon="💡",
                category="energy"
            ),
            QuestTemplate(
                id="weekly_plant_meals",
                title="Plant-Based Week",
                description="Eat plant-based meals for 5 days this week",
                type="weekly",
                difficulty="medium",
                xp_reward=100,
                coin_reward=20,
                requirements={'type': 'plant_meals', 'count': 5},
                duration_days=7,
                icon="🌿",
                category="diet"
            ),
            
            # Monthly quests
            QuestTemplate(
                id="monthly_footprint",
                title="Carbon Reducer",
                description="Reduce your carbon footprint by 20% this month",
                type="monthly",
                difficulty="hard",
                xp_reward=300,
                coin_reward=50,
                requirements={'type': 'footprint_reduction', 'percentage': 20},
                duration_days=30,
                icon="🌍",
                category="footprint"
            ),
            QuestTemplate(
                id="monthly_quests",
                title="Quest Master",
                description="Complete 15 daily/weekly quests this month",
                type="monthly",
                difficulty="hard",
                xp_reward=250,
                coin_reward=45,
                requirements={'type': 'quests_completed', 'count': 15},
                duration_days=30,
                icon="🎯",
                category="quests"
            ),
            QuestTemplate(
                id="monthly_challenge",
                title="Challenge Champion",
                description="Complete 3 challenges this month",
                type="monthly",
                difficulty="epic",
                xp_reward=400,
                coin_reward=60,
                requirements={'type': 'challenges', 'count': 3},
                duration_days=30,
                icon="🏆",
                category="challenges"
            ),
            
            # Special quests (one-time)
            QuestTemplate(
                id="special_first_assessment",
                title="First Assessment",
                description="Complete your very first assessment",
                type="special",
                difficulty="easy",
                xp_reward=100,
                coin_reward=20,
                requirements={'type': 'assessment', 'count': 1},
                duration_days=365,
                icon="🌟",
                category="special"
            ),
            QuestTemplate(
                id="special_week_streak",
                title="First Week",
                description="Complete assessments for 7 days straight",
                type="special",
                difficulty="medium",
                xp_reward=150,
                coin_reward=30,
                requirements={'type': 'streak', 'count': 7},
                duration_days=365,
                icon="🔥",
                category="special"
            ),
            QuestTemplate(
                id="special_month_streak",
                title="First Month",
                description="Complete assessments for 30 days straight",
                type="special",
                difficulty="hard",
                xp_reward=300,
                coin_reward=50,
                requirements={'type': 'streak', 'count': 30},
                duration_days=365,
                icon="🌙",
                category="special"
            ),
            QuestTemplate(
                id="special_eco_score",
                title="Eco Champion",
                description="Achieve an Eco Score of 90 or higher",
                type="special",
                difficulty="hard",
                xp_reward=200,
                coin_reward=35,
                requirements={'type': 'eco_score', 'score': 90},
                duration_days=365,
                icon="⭐",
                category="special"
            )
        ]
        
        for template in defaults:
            self._quest_templates[template.id] = template
        
        logger.info(f"Loaded {len(defaults)} quest templates")
    
    def _daily_quest_regen(self) -> None:
        """Background worker for daily quest regeneration."""
        while not self._stop_worker:
            try:
                # Check if day has changed
                now = datetime.now()
                if now.hour == 0 and now.minute == 0:
                    self._regenerate_daily_quests()
                    self._regenerate_weekly_quests()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Quest regeneration error: {e}")
    
    def _regenerate_daily_quests(self) -> None:
        """Regenerate daily quests for all users."""
        with self._lock:
            for user_id in self._user_quests.keys():
                # Remove old daily quests
                to_remove = []
                for quest_id, quest_data in self._user_quests[user_id].items():
                    template = self._quest_templates.get(quest_id)
                    if template and template.type == 'daily':
                        to_remove.append(quest_id)
                
                for quest_id in to_remove:
                    del self._user_quests[user_id][quest_id]
                
                # Generate new daily quests
                self._assign_quests_for_user(user_id, 'daily', count=3)
            
            logger.info(f"Regenerated daily quests for {len(self._user_quests)} users")
    
    def _regenerate_weekly_quests(self) -> None:
        """Regenerate weekly quests for all users."""
        now = datetime.now()
        if now.weekday() == 0:  # Monday
            with self._lock:
                for user_id in self._user_quests.keys():
                    # Remove old weekly quests
                    to_remove = []
                    for quest_id, quest_data in self._user_quests[user_id].items():
                        template = self._quest_templates.get(quest_id)
                        if template and template.type == 'weekly':
                            to_remove.append(quest_id)
                    
                    for quest_id in to_remove:
                        del self._user_quests[user_id][quest_id]
                    
                    # Generate new weekly quests
                    self._assign_quests_for_user(user_id, 'weekly', count=2)
                
                logger.info(f"Regenerated weekly quests for {len(self._user_quests)} users")
    
    def _assign_quests_for_user(
        self,
        user_id: int,
        quest_type: str,
        count: int = 3
    ) -> None:
        """Assign quests of a specific type to a user."""
        if user_id not in self._user_quests:
            self._user_quests[user_id] = {}
        
        # Get available quests
        available = [
            q for q in self._quest_templates.values()
            if q.type == quest_type
            and q.id not in self._user_quests[user_id]
        ]
        
        # Check prerequisites and user level
        user_level = self._get_user_level(user_id)
        available = [
            q for q in available
            if self._check_prerequisites(q, user_id)
            and self._check_difficulty_access(q, user_level)
        ]
        
        # Select random quests
        import random
        selected = random.sample(
            available,
            min(count, len(available))
        )
        
        for template in selected:
            self._user_quests[user_id][template.id] = {
                'id': template.id,
                'accepted': False,
                'progress': 0.0,
                'completed': False,
                'expires_at': (datetime.now() + timedelta(days=template.duration_days)).isoformat()
            }
    
    def _check_prerequisites(self, quest: QuestTemplate, user_id: int) -> bool:
        """Check if user meets quest prerequisites."""
        if not quest.prerequisites:
            return True
        
        user_quests = self._user_quests.get(user_id, {})
        return all(p in user_quests for p in quest.prerequisites)
    
    def _check_difficulty_access(self, quest: QuestTemplate, user_level: int) -> bool:
        """Check if user can access quest based on difficulty."""
        difficulty_levels = {
            'easy': 0,
            'medium': 3,
            'hard': 7,
            'epic': 15,
            'legendary': 25
        }
        required_level = difficulty_levels.get(quest.difficulty, 0)
        return user_level >= required_level
    
    def _get_user_level(self, user_id: int) -> int:
        """Get user level."""
        try:
            from .gamification_v2 import get_user_level
            level = get_user_level(user_id)
            return level.level if level else 1
        except:
            return 1
    
    def get_user_quests(
        self,
        user_id: int,
        include_completed: bool = False
    ) -> List[Dict[str, Any]]:
        """Get quests for a user."""
        user_quests = self._user_quests.get(user_id, {})
        quests = []
        
        for quest_id, quest_data in user_quests.items():
            template = self._quest_templates.get(quest_id)
            if not template:
                continue
            
            if not include_completed and quest_data['completed']:
                continue
            
            quests.append({
                'template': template,
                'data': quest_data
            })
        
        return quests
    
    def accept_quest(self, user_id: int, quest_id: str) -> bool:
        """Accept a quest."""
        with self._lock:
            if user_id not in self._user_quests:
                return False
            
            if quest_id not in self._user_quests[user_id]:
                return False
            
            if self._user_quests[user_id][quest_id]['accepted']:
                return False
            
            self._user_quests[user_id][quest_id]['accepted'] = True
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
            
            quest_data = self._user_quests[user_id][quest_id]
            if not quest_data['accepted'] or quest_data['completed']:
                return False
            
            quest_data['progress'] = min(progress, 100.0)
            
            if quest_data['progress'] >= 100.0:
                quest_data['completed'] = True
                self._on_quest_complete(user_id, quest_id)
            
            return True
    
    def _on_quest_complete(self, user_id: int, quest_id: str) -> None:
        """Handle quest completion."""
        template = self._quest_templates.get(quest_id)
        if not template:
            return
        
        # Award XP and coins
        from .gamification_v2 import add_xp, add_coins
        add_xp(user_id, template.xp_reward)
        add_coins(user_id, template.coin_reward)
        
        # Create notification
        from .notification_manager import create_notification, NotificationType
        create_notification(
            user_id=user_id,
            type=NotificationType.ACHIEVEMENT,
            template_key='challenge_completed',
            challenge_name=template.title,
            xp=template.xp_reward
        )
        
        logger.info(f"User {user_id} completed quest: {template.title}")
    
    def get_quest_stats(self, user_id: int) -> Dict[str, Any]:
        """Get quest statistics for a user."""
        user_quests = self._user_quests.get(user_id, {})
        
        stats = {
            'total': len(user_quests),
            'accepted': 0,
            'completed': 0,
            'in_progress': 0,
            'expired': 0,
            'by_type': {}
        }
        
        for quest_id, quest_data in user_quests.items():
            template = self._quest_templates.get(quest_id)
            if not template:
                continue
            
            if quest_data['accepted']:
                if quest_data['completed']:
                    stats['completed'] += 1
                else:
                    stats['in_progress'] += 1
            stats['accepted'] += 1
            
            stats['by_type'][template.type] = stats['by_type'].get(template.type, 0) + 1
        
        return stats


# Global quest manager instance
_quest_manager: Optional[QuestManager] = None
_quest_manager_lock = threading.Lock()


def get_quest_manager() -> QuestManager:
    """Get or create global quest manager instance."""
    global _quest_manager
    with _quest_manager_lock:
        if _quest_manager is None:
            _quest_manager = QuestManager()
        return _quest_manager


def get_user_quests(user_id: int, include_completed: bool = False) -> List[Dict[str, Any]]:
    """Convenience function to get user quests."""
    manager = get_quest_manager()
    return manager.get_user_quests(user_id, include_completed)


def accept_quest(user_id: int, quest_id: str) -> bool:
    """Convenience function to accept a quest."""
    manager = get_quest_manager()
    return manager.accept_quest(user_id, quest_id)


def update_quest_progress(user_id: int, quest_id: str, progress: float) -> bool:
    """Convenience function to update quest progress."""
    manager = get_quest_manager()
    return manager.update_quest_progress(user_id, quest_id, progress)