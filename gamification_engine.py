import datetime
from typing import Dict, Any

class GamificationEngine:
    """
    Manages user progression, levels, and badges based on their eco-actions 
    and footprint mitigations.
    """

    LEVEL_THRESHOLDS = [
        (0, "Seedling"),
        (100, "Sprout"),
        (500, "Sapling"),
        (1000, "Tree"),
        (2500, "Grove"),
        (5000, "Forest Guardian"),
        (10000, "Earth Champion")
    ]

    BADGES = [
        {"id": "B01", "name": "First Step", "description": "Logged your first footprint.", "xp_reward": 50},
        {"id": "B02", "name": "Carbon Neutralizer", "description": "Offset at least 1 ton of CO2.", "xp_reward": 200},
        {"id": "B03", "name": "Zero Waste Week", "description": "Logged 0 waste for 7 days.", "xp_reward": 500},
        {"id": "B04", "name": "Transit Hero", "description": "Used public transit 20 times.", "xp_reward": 300},
    ]

    def __init__(self, db_connector=None):
        self.db = db_connector
        # Mock in-memory state for fast prototyping
        self.user_state = {}

    def init_user(self, user_id: str):
        if user_id not in self.user_state:
            self.user_state[user_id] = {
                "xp": 0,
                "level": "Seedling",
                "badges_earned": [],
                "streak_days": 0,
                "last_active": None
            }

    def award_xp(self, user_id: str, amount: int, reason: str) -> Dict[str, Any]:
        """Awards XP and checks for level-ups."""
        self.init_user(user_id)
        state = self.user_state[user_id]
        
        old_level = state["level"]
        state["xp"] += amount
        
        # Calculate new level
        new_level = old_level
        for threshold, name in self.LEVEL_THRESHOLDS:
            if state["xp"] >= threshold:
                new_level = name
                
        leveled_up = new_level != old_level
        state["level"] = new_level
        
        return {
            "xp_awarded": amount,
            "new_total_xp": state["xp"],
            "leveled_up": leveled_up,
            "current_level": new_level,
            "reason": reason
        }

    def award_badge(self, user_id: str, badge_id: str) -> bool:
        """Awards a specific badge if not already earned."""
        self.init_user(user_id)
        state = self.user_state[user_id]
        
        if badge_id in state["badges_earned"]:
            return False
            
        badge = next((b for b in self.BADGES if b["id"] == badge_id), None)
        if badge:
            state["badges_earned"].append(badge_id)
            self.award_xp(user_id, badge["xp_reward"], f"Earned badge: {badge['name']}")
            return True
            
        return False

    def update_streak(self, user_id: str) -> int:
        """Updates daily login streak."""
        self.init_user(user_id)
        state = self.user_state[user_id]
        
        now = datetime.datetime.now().date()
        
        if state["last_active"] == now:
            return state["streak_days"]
            
        if state["last_active"] == now - datetime.timedelta(days=1):
            state["streak_days"] += 1
            self.award_xp(user_id, 10, "Daily streak bonus!")
        else:
            state["streak_days"] = 1 # Reset
            
        state["last_active"] = now
        return state["streak_days"]

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        self.init_user(user_id)
        return self.user_state[user_id]
