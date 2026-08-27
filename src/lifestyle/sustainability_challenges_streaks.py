"""
Sustainability Achievements & Gamification System
A comprehensive system to track, reward, and gamify sustainable actions
"""

import json
import datetime
import random
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict


class ActionCategory(Enum):
    """Categories of sustainable actions"""
    ENERGY = "energy"
    WATER = "water"
    WASTE = "waste"
    TRANSPORT = "transport"
    FOOD = "food"
    SHOPPING = "shopping"
    COMMUNITY = "community"


class AchievementTier(Enum):
    """Tier levels for achievements"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


@dataclass
class SustainableAction:
    """Represents a single sustainable action"""
    action_id: str
    name: str
    description: str
    category: ActionCategory
    points: int
    co2_saved: float  # in kg
    water_saved: float  # in liters
    waste_reduced: float  # in kg
    frequency_limit: Optional[int] = None  # Max times per day
    requires_verification: bool = False
    
    def __post_init__(self):
        if self.frequency_limit is None:
            self.frequency_limit = 999


@dataclass
class Achievement:
    """Represents an achievement that can be earned"""
    achievement_id: str
    name: str
    description: str
    tier: AchievementTier
    category: ActionCategory
    points_required: int
    actions_required: int
    icon: str = "🏆"
    unlocked: bool = False
    unlocked_date: Optional[datetime.datetime] = None
    
    def unlock(self):
        """Mark achievement as unlocked"""
        self.unlocked = True
        self.unlocked_date = datetime.datetime.now()


@dataclass
class UserProfile:
    """User profile with gamification stats"""
    user_id: str
    username: str
    total_points: int = 0
    level: int = 1
    xp: int = 0
    xp_to_next_level: int = 100
    actions_completed: List[Dict] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    streaks: Dict[str, int] = field(default_factory=dict)
    daily_points: List[int] = field(default_factory=list)
    badges: List[str] = field(default_factory=list)
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    last_action_date: Optional[datetime.date] = None
    
    def add_xp(self, amount: int) -> bool:
        """Add XP and handle level ups"""
        self.xp += amount
        leveled_up = False
        
        while self.xp >= self.xp_to_next_level:
            self.xp -= self.xp_to_next_level
            self.level += 1
            self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
            leveled_up = True
            
        return leveled_up
    
    def update_streak(self, category: str):
        """Update daily streak for a category"""
        today = datetime.date.today()
        
        if category not in self.streaks:
            self.streaks[category] = 1
        else:
            last_action = self.last_action_date
            if last_action:
                days_diff = (today - last_action).days
                if days_diff == 1:
                    self.streaks[category] += 1
                elif days_diff > 1:
                    self.streaks[category] = 1
        
        self.last_action_date = today


class SustainabilityGamification:
    """Main system for sustainability gamification"""
    
    def __init__(self):
        self.users: Dict[str, UserProfile] = {}
        self.actions: Dict[str, SustainableAction] = {}
        self.achievements: Dict[str, Achievement] = {}
        self.leaderboard: List[Tuple[str, int]] = []
        self.daily_challenges: List[Dict] = []
        self.seasonal_events: List[Dict] = []
        
        # Initialize with default actions and achievements
        self._initialize_actions()
        self._initialize_achievements()
        self._generate_daily_challenges()
    
    def _initialize_actions(self):
        """Initialize default sustainable actions"""
        default_actions = [
            SustainableAction(
                action_id="walk_bike",
                name="Walk or Bike",
                description="Travel by walking or biking instead of driving",
                category=ActionCategory.TRANSPORT,
                points=15,
                co2_saved=2.5,
                water_saved=0,
                waste_reduced=0,
                frequency_limit=3
            ),
            SustainableAction(
                action_id="public_transit",
                name="Public Transit",
                description="Use public transportation",
                category=ActionCategory.TRANSPORT,
                points=12,
                co2_saved=2.0,
                water_saved=0,
                waste_reduced=0,
                frequency_limit=2
            ),
            SustainableAction(
                action_id="reduce_energy",
                name="Reduce Energy Usage",
                description="Turn off unused lights and electronics",
                category=ActionCategory.ENERGY,
                points=10,
                co2_saved=1.5,
                water_saved=0,
                waste_reduced=0,
                frequency_limit=5
            ),
            SustainableAction(
                action_id="recycle",
                name="Recycle Waste",
                description="Sort and recycle your waste",
                category=ActionCategory.WASTE,
                points=8,
                co2_saved=0.5,
                water_saved=0,
                waste_reduced=1.0,
                frequency_limit=3
            ),
            SustainableAction(
                action_id="compost",
                name="Compost Food Waste",
                description="Compost organic waste",
                category=ActionCategory.WASTE,
                points=12,
                co2_saved=1.0,
                water_saved=0,
                waste_reduced=2.0,
                frequency_limit=2
            ),
            SustainableAction(
                action_id="short_shower",
                name="Short Shower",
                description="Take a 5-minute shower",
                category=ActionCategory.WATER,
                points=10,
                co2_saved=0.3,
                water_saved=50,
                waste_reduced=0,
                frequency_limit=1
            ),
            SustainableAction(
                action_id="plant_tree",
                name="Plant a Tree",
                description="Plant a tree in your community",
                category=ActionCategory.COMMUNITY,
                points=50,
                co2_saved=25.0,
                water_saved=0,
                waste_reduced=0,
                frequency_limit=1
            ),
            SustainableAction(
                action_id="meatless_meal",
                name="Meatless Meal",
                description="Eat a meal without meat",
                category=ActionCategory.FOOD,
                points=15,
                co2_saved=3.0,
                water_saved=1000,
                waste_reduced=0,
                frequency_limit=3
            ),
            SustainableAction(
                action_id="reusable_bag",
                name="Use Reusable Bag",
                description="Use a reusable shopping bag",
                category=ActionCategory.SHOPPING,
                points=8,
                co2_saved=0.2,
                water_saved=0,
                waste_reduced=0.5,
                frequency_limit=2
            ),
            SustainableAction(
                action_id="solar_install",
                name="Solar Panel Installation",
                description="Install solar panels at home",
                category=ActionCategory.ENERGY,
                points=100,
                co2_saved=50.0,
                water_saved=0,
                waste_reduced=0,
                frequency_limit=1
            ),
        ]
        
        for action in default_actions:
            self.actions[action.action_id] = action
    
    def _initialize_achievements(self):
        """Initialize achievement system"""
        achievement_configs = [
            # Energy achievements
            ("energy_saver", "Energy Saver", "Save 50 kWh of energy", 
             AchievementTier.BRONZE, ActionCategory.ENERGY, 50, 5, "💡"),
            ("energy_hero", "Energy Hero", "Save 200 kWh of energy", 
             AchievementTier.SILVER, ActionCategory.ENERGY, 200, 20, "⚡"),
            ("energy_master", "Energy Master", "Save 500 kWh of energy", 
             AchievementTier.GOLD, ActionCategory.ENERGY, 500, 50, "🔋"),
            
            # Water achievements
            ("water_saver", "Water Saver", "Save 1000 liters of water", 
             AchievementTier.BRONZE, ActionCategory.WATER, 30, 5, "💧"),
            ("water_hero", "Water Hero", "Save 5000 liters of water", 
             AchievementTier.SILVER, ActionCategory.WATER, 100, 20, "🌊"),
            
            # Waste achievements
            ("recycler", "Recycler Extraordinaire", "Recycle 10 kg of waste", 
             AchievementTier.BRONZE, ActionCategory.WASTE, 40, 10, "♻️"),
            ("waste_warrior", "Waste Warrior", "Recycle 50 kg of waste", 
             AchievementTier.SILVER, ActionCategory.WASTE, 150, 50, "🗑️"),
            
            # Transport achievements
            ("walker", "Eco-Commuter", "Walk or bike 50 times", 
             AchievementTier.SILVER, ActionCategory.TRANSPORT, 75, 50, "🚶"),
            ("transit_master", "Public Transit Master", "Use public transit 100 times", 
             AchievementTier.GOLD, ActionCategory.TRANSPORT, 150, 100, "🚌"),
            
            # General achievements
            ("eco_beginner", "Eco Beginner", "Complete 10 sustainable actions", 
             AchievementTier.BRONZE, ActionCategory.COMMUNITY, 20, 10, "🌱"),
            ("sustainability_star", "Sustainability Star", "Complete 100 sustainable actions", 
             AchievementTier.GOLD, ActionCategory.COMMUNITY, 200, 100, "⭐"),
            ("planet_hero", "Planet Hero", "Complete 500 sustainable actions", 
             AchievementTier.PLATINUM, ActionCategory.COMMUNITY, 1000, 500, "🌍"),
            ("sustainability_legend", "Sustainability Legend", "Complete 1000 sustainable actions", 
             AchievementTier.DIAMOND, ActionCategory.COMMUNITY, 2000, 1000, "👑"),
            
            # Streak achievements
            ("streak_7", "7-Day Streak", "Complete sustainable actions for 7 days straight", 
             AchievementTier.BRONZE, ActionCategory.COMMUNITY, 0, 0, "🔥"),
            ("streak_30", "30-Day Streak", "Complete sustainable actions for 30 days straight", 
             AchievementTier.SILVER, ActionCategory.COMMUNITY, 0, 0, "💪"),
            ("streak_100", "100-Day Streak", "Complete sustainable actions for 100 days straight", 
             AchievementTier.GOLD, ActionCategory.COMMUNITY, 0, 0, "🏅"),
        ]
        
        for config in achievement_configs:
            achievement = Achievement(
                achievement_id=config[0],
                name=config[1],
                description=config[2],
                tier=config[3],
                category=config[4],
                points_required=config[5],
                actions_required=config[6],
                icon=config[7]
            )
            self.achievements[achievement.achievement_id] = achievement
    
    def _generate_daily_challenges(self):
        """Generate daily sustainability challenges"""
        challenges = [
            {
                "id": "challenge_1",
                "name": "Green Commute Day",
                "description": "Use only eco-friendly transportation today",
                "bonus_points": 25,
                "actions": ["walk_bike", "public_transit"],
                "date": datetime.date.today().isoformat()
            },
            {
                "id": "challenge_2",
                "name": "Zero Waste Challenge",
                "description": "Minimize waste production today",
                "bonus_points": 30,
                "actions": ["recycle", "compost", "reusable_bag"],
                "date": datetime.date.today().isoformat()
            },
            {
                "id": "challenge_3",
                "name": "Energy Conservation Day",
                "description": "Conserve as much energy as possible",
                "bonus_points": 20,
                "actions": ["reduce_energy"],
                "date": datetime.date.today().isoformat()
            }
        ]
        self.daily_challenges = challenges
    
    def register_user(self, user_id: str, username: str) -> UserProfile:
        """Register a new user"""
        if user_id in self.users:
            raise ValueError(f"User {user_id} already exists")
        
        user = UserProfile(user_id=user_id, username=username)
        self.users[user_id] = user
        return user
    
    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def complete_action(self, user_id: str, action_id: str, quantity: int = 1) -> Dict:
        """
        Complete a sustainable action and award points
        
        Returns:
            Dict with action results including points earned, achievements unlocked, etc.
        """
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        
        if action_id not in self.actions:
            raise ValueError(f"Action {action_id} not found")
        
        user = self.users[user_id]
        action = self.actions[action_id]
        
        # Check frequency limit
        daily_count = sum(1 for a in user.actions_completed 
                         if a['action_id'] == action_id and 
                         datetime.datetime.fromisoformat(a['timestamp']).date() == datetime.date.today())
        
        if daily_count >= action.frequency_limit:
            return {
                "success": False,
                "message": f"Daily limit of {action.frequency_limit} reached for this action",
                "points_earned": 0
            }
        
        # Calculate points (with bonus for quantity)
        total_points = action.points * quantity
        
        # Apply bonus for streaks
        bonus_multiplier = 1.0
        if action.category.value in user.streaks:
            streak_days = user.streaks[action.category.value]
            if streak_days >= 7:
                bonus_multiplier = 1.5
            elif streak_days >= 30:
                bonus_multiplier = 2.0
            elif streak_days >= 100:
                bonus_multiplier = 3.0
        
        total_points = int(total_points * bonus_multiplier)
        
        # Record the action
        action_record = {
            "action_id": action_id,
            "name": action.name,
            "category": action.category.value,
            "points": total_points,
            "co2_saved": action.co2_saved * quantity,
            "water_saved": action.water_saved * quantity,
            "waste_reduced": action.waste_reduced * quantity,
            "timestamp": datetime.datetime.now().isoformat(),
            "quantity": quantity
        }
        
        user.actions_completed.append(action_record)
        user.total_points += total_points
        
        # Add XP
        xp_earned = total_points // 2
        leveled_up = user.add_xp(xp_earned)
        
        # Update streak
        user.update_streak(action.category.value)
        
        # Check for achievements
        unlocked_achievements = self._check_achievements(user)
        
        # Update leaderboard
        self._update_leaderboard()
        
        return {
            "success": True,
            "action": action.name,
            "points_earned": total_points,
            "xp_earned": xp_earned,
            "leveled_up": leveled_up,
            "new_level": user.level if leveled_up else None,
            "achievements_unlocked": unlocked_achievements,
            "total_points": user.total_points,
            "co2_saved": action.co2_saved * quantity,
            "water_saved": action.water_saved * quantity,
            "waste_reduced": action.waste_reduced * quantity
        }
    
    def _check_achievements(self, user: UserProfile) -> List[str]:
        """Check and unlock achievements for a user"""
        unlocked = []
        
        # Calculate stats
        total_actions = len(user.actions_completed)
        category_counts = defaultdict(int)
        total_co2 = 0
        total_water = 0
        total_waste = 0
        
        for action in user.actions_completed:
            category_counts[action['category']] += 1
            total_co2 += action.get('co2_saved', 0)
            total_water += action.get('water_saved', 0)
            total_waste += action.get('waste_reduced', 0)
        
        # Check each achievement
        for ach_id, achievement in self.achievements.items():
            if achievement.unlocked or ach_id in user.achievements:
                continue
            
            # Check category-specific achievements
            if achievement.category != ActionCategory.COMMUNITY:
                category_count = category_counts.get(achievement.category.value, 0)
                if category_count >= achievement.actions_required:
                    achievement.unlock()
                    user.achievements.append(ach_id)
                    unlocked.append(achievement.name)
                    continue
            
            # Check general achievements
            if achievement.category == ActionCategory.COMMUNITY:
                if ach_id.startswith("streak"):
                    # Streak achievements
                    max_streak = max(user.streaks.values()) if user.streaks else 0
                    if ach_id == "streak_7" and max_streak >= 7:
                        achievement.unlock()
                        user.achievements.append(ach_id)
                        unlocked.append(achievement.name)
                    elif ach_id == "streak_30" and max_streak >= 30:
                        achievement.unlock()
                        user.achievements.append(ach_id)
                        unlocked.append(achievement.name)
                    elif ach_id == "streak_100" and max_streak >= 100:
                        achievement.unlock()
                        user.achievements.append(ach_id)
                        unlocked.append(achievement.name)
                else:
                    # General action count achievements
                    if total_actions >= achievement.actions_required and achievement.points_required == 0:
                        achievement.unlock()
                        user.achievements.append(ach_id)
                        unlocked.append(achievement.name)
                    elif user.total_points >= achievement.points_required:
                        achievement.unlock()
                        user.achievements.append(ach_id)
                        unlocked.append(achievement.name)
        
        return unlocked
    
    def _update_leaderboard(self):
        """Update the leaderboard"""
        self.leaderboard = sorted(
            [(user_id, user.total_points) for user_id, user in self.users.items()],
            key=lambda x: x[1],
            reverse=True
        )
    
    def get_leaderboard(self, limit: int = 10) -> List[Tuple[str, int, str]]:
        """Get top users from leaderboard"""
        result = []
        for i, (user_id, points) in enumerate(self.leaderboard[:limit], 1):
            user = self.users[user_id]
            result.append((user.username, points, user.level))
        return result
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get comprehensive stats for a user"""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        
        user = self.users[user_id]
        
        # Calculate category stats
        category_stats = defaultdict(lambda: {"count": 0, "points": 0})
        total_co2 = 0
        total_water = 0
        total_waste = 0
        
        for action in user.actions_completed:
            category = action['category']
            category_stats[category]["count"] += 1
            category_stats[category]["points"] += action['points']
            total_co2 += action.get('co2_saved', 0)
            total_water += action.get('water_saved', 0)
            total_waste += action.get('waste_reduced', 0)
        
        # Get unlocked achievements
        unlocked_achievements = [
            self.achievements[ach_id] for ach_id in user.achievements 
            if ach_id in self.achievements
        ]
        
        # Group achievements by tier
        achievements_by_tier = defaultdict(list)
        for ach in unlocked_achievements:
            achievements_by_tier[ach.tier.value].append(ach.name)
        
        return {
            "user_id": user.user_id,
            "username": user.username,
            "level": user.level,
            "xp": user.xp,
            "xp_to_next_level": user.xp_to_next_level,
            "total_points": user.total_points,
            "total_actions": len(user.actions_completed),
            "category_stats": dict(category_stats),
            "achievements": {
                "total": len(unlocked_achievements),
                "by_tier": dict(achievements_by_tier),
                "list": [{"name": a.name, "tier": a.tier.value, "icon": a.icon} 
                        for a in unlocked_achievements]
            },
            "streaks": user.streaks,
            "impact": {
                "co2_saved_kg": total_co2,
                "water_saved_liters": total_water,
                "waste_reduced_kg": total_waste
            },
            "daily_challenges_completed": len([c for c in self.daily_challenges 
                                              if any(a['action_id'] in c['actions'] 
                                                    for a in user.actions_completed[-10:])])
        }
    
    def get_daily_challenges(self, user_id: str) -> List[Dict]:
        """Get daily challenges for a user with progress"""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        
        user = self.users[user_id]
        today = datetime.date.today().isoformat()
        
        challenges_with_progress = []
        for challenge in self.daily_challenges:
            if challenge['date'] != today:
                continue
            
            # Check progress
            completed_actions = []
            for action_id in challenge['actions']:
                completed = any(
                    a['action_id'] == action_id and 
                    datetime.datetime.fromisoformat(a['timestamp']).date() == datetime.date.today()
                    for a in user.actions_completed
                )
                completed_actions.append({
                    "action_id": action_id,
                    "completed": completed
                })
            
            all_completed = all(ca['completed'] for ca in completed_actions)
            
            challenges_with_progress.append({
                **challenge,
                "progress": {
                    "completed": sum(1 for ca in completed_actions if ca['completed']),
                    "total": len(completed_actions),
                    "all_completed": all_completed,
                    "actions": completed_actions
                }
            })
        
        return challenges_with_progress
    
    def complete_daily_challenge(self, user_id: str, challenge_id: str) -> Dict:
        """Complete a daily challenge and earn bonus points"""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        
        user = self.users[user_id]
        
        # Find challenge
        challenge = next((c for c in self.daily_challenges if c['id'] == challenge_id), None)
        if not challenge:
            return {"success": False, "message": "Challenge not found"}
        
        # Check if all actions are completed
        today = datetime.date.today().isoformat()
        if challenge['date'] != today:
            return {"success": False, "message": "Challenge not available today"}
        
        all_completed = all(
            any(
                a['action_id'] == action_id and 
                datetime.datetime.fromisoformat(a['timestamp']).date() == datetime.date.today()
                for a in user.actions_completed
            )
            for action_id in challenge['actions']
        )
        
        if not all_completed:
            return {"success": False, "message": "Not all challenge actions completed"}
        
        # Award bonus points
        bonus_points = challenge.get('bonus_points', 20)
        user.total_points += bonus_points
        user.add_xp(bonus_points // 2)
        
        return {
            "success": True,
            "challenge": challenge['name'],
            "bonus_points": bonus_points,
            "message": f"Daily challenge completed! Earned {bonus_points} bonus points!"
        }
    
    def get_seasonal_event(self) -> Dict:
        """Get current seasonal event if active"""
        # Simple seasonal events based on month
        month = datetime.datetime.now().month
        
        events = {
            3: {"name": "Spring Clean", "icon": "🌸", "description": "Spring cleaning and recycling drive"},
            6: {"name": "Summer Solar", "icon": "☀️", "description": "Maximize solar energy usage"},
            9: {"name": "Fall Harvest", "icon": "🍂", "description": "Local and seasonal eating challenge"},
            12: {"name": "Winter Conservation", "icon": "❄️", "description": "Energy conservation challenge"}
        }
        
        return events.get(month, {"name": "No Active Event", "icon": "🌍", "description": "Check back soon!"})
    
    def save_data(self, filename: str = "sustainability_data.json"):
        """Save all data to JSON file"""
        data = {
            "users": {},
            "actions": {},
            "achievements": {},
            "daily_challenges": self.daily_challenges,
            "leaderboard": self.leaderboard,
            "saved_at": datetime.datetime.now().isoformat()
        }
        
        # Serialize users
        for user_id, user in self.users.items():
            data["users"][user_id] = {
                "user_id": user.user_id,
                "username": user.username,
                "total_points": user.total_points,
                "level": user.level,
                "xp": user.xp,
                "xp_to_next_level": user.xp_to_next_level,
                "actions_completed": user.actions_completed,
                "achievements": user.achievements,
                "streaks": user.streaks,
                "daily_points": user.daily_points,
                "badges": user.badges,
                "created_at": user.created_at.isoformat(),
                "last_action_date": user.last_action_date.isoformat() if user.last_action_date else None
            }
        
        # Serialize achievements
        for ach_id, achievement in self.achievements.items():
            data["achievements"][ach_id] = {
                "achievement_id": achievement.achievement_id,
                "name": achievement.name,
                "description": achievement.description,
                "tier": achievement.tier.value,
                "category": achievement.category.value,
                "points_required": achievement.points_required,
                "actions_required": achievement.actions_required,
                "icon": achievement.icon,
                "unlocked": achievement.unlocked,
                "unlocked_date": achievement.unlocked_date.isoformat() if achievement.unlocked_date else None
            }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Data saved to {filename}")
    
    def load_data(self, filename: str = "sustainability_data.json"):
        """Load data from JSON file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Load users
            for user_id, user_data in data["users"].items():
                user = UserProfile(
                    user_id=user_data["user_id"],
                    username=user_data["username"],
                    total_points=user_data["total_points"],
                    level=user_data["level"],
                    xp=user_data["xp"],
                    xp_to_next_level=user_data["xp_to_next_level"],
                    actions_completed=user_data["actions_completed"],
                    achievements=user_data["achievements"],
                    streaks=user_data["streaks"],
                    daily_points=user_data.get("daily_points", []),
                    badges=user_data.get("badges", []),
                    created_at=datetime.datetime.fromisoformat(user_data["created_at"]),
                    last_action_date=datetime.datetime.fromisoformat(user_data["last_action_date"]).date() 
                                    if user_data.get("last_action_date") else None
                )
                self.users[user_id] = user
            
            # Load achievements
            for ach_id, ach_data in data["achievements"].items():
                achievement = Achievement(
                    achievement_id=ach_data["achievement_id"],
                    name=ach_data["name"],
                    description=ach_data["description"],
                    tier=AchievementTier(ach_data["tier"]),
                    category=ActionCategory(ach_data["category"]),
                    points_required=ach_data["points_required"],
                    actions_required=ach_data["actions_required"],
                    icon=ach_data["icon"],
                    unlocked=ach_data["unlocked"],
                    unlocked_date=datetime.datetime.fromisoformat(ach_data["unlocked_date"]) 
                                 if ach_data.get("unlocked_date") else None
                )
                self.achievements[ach_id] = achievement
            
            # Load other data
            self.daily_challenges = data.get("daily_challenges", [])
            self.leaderboard = data.get("leaderboard", [])
            
            print(f"✅ Data loaded from {filename}")
            return True
            
        except FileNotFoundError:
            print(f"ℹ️ No saved data found at {filename}")
            return False
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False


# Example usage and demonstration
def demo_system():
    """Demonstrate the sustainability gamification system"""
    print("🌍 SUSTAINABILITY ACHIEVEMENTS & GAMIFICATION SYSTEM 🌍")
    print("=" * 60)
    
    # Initialize system
    system = SustainabilityGamification()
    
    # Try to load existing data
    system.load_data()
    
    # Register users
    print("\n📝 Registering users...")
    alice = system.register_user("user_001", "EcoAlice")
    bob = system.register_user("user_002", "GreenBob")
    charlie = system.register_user("user_003", "SustainableCharlie")
    
    print(f"✅ Registered: {alice.username}, {bob.username}, {charlie.username}")
    
    # Complete some actions
    print("\n🎯 Completing sustainable actions...")
    
    # Alice's actions
    actions_alice = [
        ("walk_bike", 2),
        ("recycle", 1),
        ("reduce_energy", 3),
        ("meatless_meal", 1),
        ("short_shower", 1),
        ("walk_bike", 1),
        ("reusable_bag", 2),
        ("compost", 1),
        ("public_transit", 1),
    ]
    
    for action_id, quantity in actions_alice:
        result = system.complete_action("user_001", action_id, quantity)
        if result["success"]:
            print(f"  ✅ {alice.username}: {result['action']} → {result['points_earned']} points")
            if result.get("achievements_unlocked"):
                for ach in result["achievements_unlocked"]:
                    print(f"    🏅 NEW ACHIEVEMENT: {ach}!")
    
    # Bob's actions
    actions_bob = [
        ("plant_tree", 1),
        ("solar_install", 1),
        ("recycle", 3),
        ("reduce_energy", 5),
        ("walk_bike", 3),
        ("meatless_meal", 2),
        ("compost", 2),
    ]
    
    for action_id, quantity in actions_bob:
        result = system.complete_action("user_002", action_id, quantity)
        if result["success"]:
            print(f"  ✅ {bob.username}: {result['action']} → {result['points_earned']} points")
            if result.get("achievements_unlocked"):
                for ach in result["achievements_unlocked"]:
                    print(f"    🏅 NEW ACHIEVEMENT: {ach}!")
    
    # Charlie's actions
    actions_charlie = [
        ("public_transit", 3),
        ("recycle", 2),
        ("reusable_bag", 3),
        ("reduce_energy", 2),
        ("walk_bike", 2),
    ]
    
    for action_id, quantity in actions_charlie:
        result = system.complete_action("user_003", action_id, quantity)
        if result["success"]:
            print(f"  ✅ {charlie.username}: {result['action']} → {result['points_earned']} points")
            if result.get("achievements_unlocked"):
                for ach in result["achievements_unlocked"]:
                    print(f"    🏅 NEW ACHIEVEMENT: {ach}!")
    
    # Complete daily challenge
    print("\n🎯 Completing daily challenges...")
    challenge_result = system.complete_daily_challenge("user_001", "challenge_1")
    if challenge_result["success"]:
        print(f"  ✅ {alice.username}: {challenge_result['message']}")
    
    # Display stats
    print("\n📊 USER STATS")
    print("-" * 60)
    
    for user_id in ["user_001", "user_002", "user_003"]:
        stats = system.get_user_stats(user_id)
        print(f"\n👤 {stats['username']}")
        print(f"  Level: {stats['level']} (XP: {stats['xp']}/{stats['xp_to_next_level']})")
        print(f"  Points: {stats['total_points']}")
        print(f"  Actions: {stats['total_actions']}")
        print(f"  Achievements: {stats['achievements']['total']}")
        print(f"  Impact: {stats['impact']['co2_saved_kg']:.1f} kg CO2 saved, "
              f"{stats['impact']['water_saved_liters']:.0f} L water saved, "
              f"{stats['impact']['waste_reduced_kg']:.1f} kg waste reduced")
        if stats['streaks']:
            print(f"  Streaks: {', '.join([f'{k}: {v} days' for k, v in stats['streaks'].items()])}")
    
    # Leaderboard
    print("\n🏆 LEADERBOARD")
    print("-" * 60)
    leaderboard = system.get_leaderboard(5)
    for rank, (username, points, level) in enumerate(leaderboard, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
        print(f"  {medal} {username}: {points} points (Level {level})")
    
    # Seasonal event
    print("\n🌱 SEASONAL EVENT")
    print("-" * 60)
    event = system.get_seasonal_event()
    print(f"  {event['icon']} {event['name']}: {event['description']}")
    
    # Save data
    print("\n💾 Saving data...")
    system.save_data()
    
    print("\n✨ Demonstration complete! ✨")


if __name__ == "__main__":
    demo_system()
