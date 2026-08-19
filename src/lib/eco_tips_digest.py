"""
Eco-Tips Digest Generator
Generates personalized weekly eco-tips digest for users.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """User preferences for eco-tips digest."""
    frequency: str = "weekly"  # weekly, biweekly, monthly
    categories: List[str] = field(default_factory=list)
    tips_per_week: int = 5
    include_stats: bool = True
    include_achievements: bool = True
    include_challenges: bool = True


@dataclass
class WeeklyDigestData:
    """Data for weekly eco-tips digest email."""
    user_email: str
    user_name: str
    week_start: str
    week_end: str
    eco_score: float
    total_footprint: float
    tips: List[Dict[str, Any]]
    achievements: List[Dict[str, Any]]
    challenges: List[Dict[str, Any]]
    streak_days: int
    tree_equivalent: int
    improvement_percentage: float
    tip_of_week: Dict[str, str]
    quote_of_week: str


# Eco-tips database
ECO_TIPS = [
    {
        "id": "tip_001",
        "title": "Switch to LED Lighting",
        "description": "Replace all incandescent bulbs with LED bulbs. They use 75% less energy and last 25 times longer.",
        "category": "energy",
        "difficulty": "easy",
        "co2_savings": 200,
        "cost_savings": 150,
        "icon": "💡"
    },
    {
        "id": "tip_002",
        "title": "Take Shorter Showers",
        "description": "Reduce shower time by 2 minutes. This saves up to 30 liters of water per shower.",
        "category": "water",
        "difficulty": "easy",
        "co2_savings": 50,
        "cost_savings": 30,
        "icon": "🚿"
    },
    {
        "id": "tip_003",
        "title": "Start Composting",
        "description": "Start composting kitchen scraps. Reduces methane emissions from landfills and creates nutrient-rich soil.",
        "category": "waste",
        "difficulty": "medium",
        "co2_savings": 100,
        "cost_savings": 20,
        "icon": "♻️"
    },
    {
        "id": "tip_004",
        "title": "Use Public Transport",
        "description": "Switch to public transport for your daily commute. Saves 0.5-1 kg CO2 per 10 km compared to driving.",
        "category": "transport",
        "difficulty": "medium",
        "co2_savings": 400,
        "cost_savings": 300,
        "icon": "🚌"
    },
    {
        "id": "tip_005",
        "title": "Plant-Based Meals",
        "description": "Have at least 2 plant-based meals per week. Reduces your carbon footprint from food significantly.",
        "category": "food",
        "difficulty": "easy",
        "co2_savings": 150,
        "cost_savings": 50,
        "icon": "🥗"
    },
    {
        "id": "tip_006",
        "title": "Unplug Idle Devices",
        "description": "Unplug chargers and devices when not in use. Standby power can account for 5-10% of your electricity bill.",
        "category": "energy",
        "difficulty": "easy",
        "co2_savings": 80,
        "cost_savings": 60,
        "icon": "🔌"
    },
    {
        "id": "tip_007",
        "title": "Use Reusable Bags",
        "description": "Always carry reusable bags for shopping. Eliminates single-use plastic and reduces waste.",
        "category": "waste",
        "difficulty": "easy",
        "co2_savings": 30,
        "cost_savings": 10,
        "icon": "🛍️"
    },
    {
        "id": "tip_008",
        "title": "Install Solar Panels",
        "description": "If possible, install solar panels for renewable energy. Cuts electricity bills and carbon emissions.",
        "category": "energy",
        "difficulty": "hard",
        "co2_savings": 800,
        "cost_savings": 400,
        "icon": "☀️"
    },
    {
        "id": "tip_009",
        "title": "Cycle to Work",
        "description": "Cycle to work once a week. Reduces emissions, improves health, and saves money.",
        "category": "transport",
        "difficulty": "medium",
        "co2_savings": 200,
        "cost_savings": 100,
        "icon": "🚲"
    },
    {
        "id": "tip_010",
        "title": "Reduce Food Waste",
        "description": "Plan meals and shop with a list to reduce food waste. Saves money and reduces methane emissions.",
        "category": "food",
        "difficulty": "easy",
        "co2_savings": 120,
        "cost_savings": 80,
        "icon": "🍽️"
    },
    {
        "id": "tip_011",
        "title": "Carpool to Work",
        "description": "Share rides with colleagues. Reduces emissions and saves on fuel costs.",
        "category": "transport",
        "difficulty": "medium",
        "co2_savings": 300,
        "cost_savings": 200,
        "icon": "🚗"
    },
    {
        "id": "tip_012",
        "title": "Install Smart Thermostat",
        "description": "Use a smart thermostat to optimize heating and cooling. Saves energy and money.",
        "category": "energy",
        "difficulty": "medium",
        "co2_savings": 350,
        "cost_savings": 250,
        "icon": "🌡️"
    },
    {
        "id": "tip_013",
        "title": "Recycle Effectively",
        "description": "Learn your local recycling rules and recycle properly. Reduces landfill waste.",
        "category": "waste",
        "difficulty": "easy",
        "co2_savings": 80,
        "cost_savings": 0,
        "icon": "♻️"
    },
    {
        "id": "tip_014",
        "title": "Buy Local Food",
        "description": "Buy locally produced food. Reduces transportation emissions and supports local farmers.",
        "category": "food",
        "difficulty": "medium",
        "co2_savings": 100,
        "cost_savings": 0,
        "icon": "🌽"
    },
    {
        "id": "tip_015",
        "title": "Use Energy-Efficient Appliances",
        "description": "When replacing appliances, choose Energy Star rated models. Saves energy and money long-term.",
        "category": "energy",
        "difficulty": "hard",
        "co2_savings": 300,
        "cost_savings": 150,
        "icon": "🔋"
    },
    {
        "id": "tip_016",
        "title": "Reduce Meat Consumption",
        "description": "Reduce meat consumption by 50%. Lowers your food carbon footprint significantly.",
        "category": "food",
        "difficulty": "medium",
        "co2_savings": 250,
        "cost_savings": 100,
        "icon": "🥩"
    },
    {
        "id": "tip_017",
        "title": "Collect Rainwater",
        "description": "Install a rain barrel to collect rainwater for gardening. Saves water and reduces runoff.",
        "category": "water",
        "difficulty": "medium",
        "co2_savings": 40,
        "cost_savings": 50,
        "icon": "🌧️"
    },
    {
        "id": "tip_018",
        "title": "Air Dry Clothes",
        "description": "Air dry your clothes instead of using a dryer. Saves energy and extends clothing life.",
        "category": "energy",
        "difficulty": "easy",
        "co2_savings": 60,
        "cost_savings": 40,
        "icon": "👕"
    },
    {
        "id": "tip_019",
        "title": "Plant Trees",
        "description": "Plant a tree or support reforestation. Trees absorb CO2 and improve air quality.",
        "category": "offset",
        "difficulty": "easy",
        "co2_savings": 100,
        "cost_savings": 0,
        "icon": "🌳"
    },
    {
        "id": "tip_020",
        "title": "Use Public Transport for Leisure",
        "description": "Use public transport for weekend activities. Reduces emissions and saves parking hassle.",
        "category": "transport",
        "difficulty": "easy",
        "co2_savings": 150,
        "cost_savings": 80,
        "icon": "🚆"
    },
]


class EcoTipsDigestGenerator:
    """Generates personalized weekly eco-tips digests."""
    
    def __init__(self):
        self.tips = ECO_TIPS
        self.quotes = [
            "The greatest threat to our planet is the belief that someone else will save it.",
            "We do not inherit the earth from our ancestors; we borrow it from our children.",
            "Small acts, when multiplied by millions of people, can transform the world.",
            "The environment is where we all meet; where we all have a mutual interest.",
            "Sustainability is not a trend; it's a necessity.",
            "Every day is Earth Day. Let's protect our planet together.",
            "Be the change you wish to see in the world.",
            "Think globally, act locally.",
            "The earth is what we all have in common.",
            "There is no planet B.",
        ]
    
    def generate_digest(
        self,
        user_data: Dict[str, Any],
        preferences: Optional[UserPreferences] = None
    ) -> WeeklyDigestData:
        """Generate a personalized weekly digest for a user."""
        preferences = preferences or UserPreferences()
        
        user_email = user_data.get("email", "")
        user_name = user_data.get("name", "Eco Warrior")
        eco_score = user_data.get("eco_score", 0)
        total_footprint = user_data.get("total_footprint", 0)
        streak_days = user_data.get("streak_days", 0)
        previous_footprint = user_data.get("previous_footprint", total_footprint)
        
        # Calculate improvement
        if previous_footprint > 0:
            improvement = ((previous_footprint - total_footprint) / previous_footprint) * 100
        else:
            improvement = 0
        
        selected_tips = self._select_tips(preferences, user_data)
        achievements = self._get_achievements(user_data)
        challenges = self._get_challenges(user_data)
        tree_equivalent = max(1, round(total_footprint / 22)) if total_footprint > 0 else 1
        
        # Tip of the week
        tip_of_week = selected_tips[0] if selected_tips else {"text": "Start small, think big!", "icon": "🌱"}
        
        # Quote of the week
        quote_of_week = random.choice(self.quotes)
        
        # Date range
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%d %b %Y")
        week_end = (today + timedelta(days=6 - today.weekday())).strftime("%d %b %Y")
        
        return WeeklyDigestData(
            user_email=user_email,
            user_name=user_name,
            week_start=week_start,
            week_end=week_end,
            eco_score=eco_score,
            total_footprint=total_footprint,
            tips=selected_tips,
            achievements=achievements,
            challenges=challenges,
            streak_days=streak_days,
            tree_equivalent=tree_equivalent,
            improvement_percentage=improvement,
            tip_of_week=tip_of_week,
            quote_of_week=quote_of_week
        )
    
    def _select_tips(
        self,
        preferences: UserPreferences,
        user_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Select personalized tips for the user."""
        if preferences.categories:
            filtered_tips = [t for t in self.tips if t["category"] in preferences.categories]
        else:
            filtered_tips = self.tips.copy()
        
        # Prioritize tips based on user's carbon footprint
        user_categories = user_data.get("contributors", {})
        if user_categories:
            sorted_categories = sorted(
                user_categories.items(),
                key=lambda x: x[1],
                reverse=True
            )
            high_impact_categories = [cat for cat, val in sorted_categories if val > 0]
            
            if high_impact_categories:
                high_impact_tips = [t for t in filtered_tips if t["category"] in high_impact_categories]
                other_tips = [t for t in filtered_tips if t["category"] not in high_impact_categories]
                filtered_tips = high_impact_tips + other_tips
        
        # Select tips
        count = min(preferences.tips_per_week, len(filtered_tips))
        return filtered_tips[:count]
    
    def _get_achievements(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get user's achievements."""
        achievements = []
        
        eco_score = user_data.get("eco_score", 0)
        streak_days = user_data.get("streak_days", 0)
        total_assessments = user_data.get("total_assessments", 0)
        
        # Eco score achievements
        if eco_score >= 90:
            achievements.append({
                "name": "🏆 Eco Champion",
                "description": "Achieved 90+ Eco Score"
            })
        elif eco_score >= 80:
            achievements.append({
                "name": "🌟 Green Guardian",
                "description": "Achieved 80+ Eco Score"
            })
        elif eco_score >= 70:
            achievements.append({
                "name": "🌿 Eco Warrior",
                "description": "Achieved 70+ Eco Score"
            })
        elif eco_score >= 60:
            achievements.append({
                "name": "🌱 Eco Learner",
                "description": "Achieved 60+ Eco Score"
            })
        
        # Streak achievements
        if streak_days >= 30:
            achievements.append({
                "name": "🔥 30-Day Streak",
                "description": "Maintained 30-day sustainability streak"
            })
        elif streak_days >= 14:
            achievements.append({
                "name": "🔥 14-Day Streak",
                "description": "Maintained 14-day sustainability streak"
            })
        elif streak_days >= 7:
            achievements.append({
                "name": "🔥 7-Day Streak",
                "description": "Maintained 7-day sustainability streak"
            })
        elif streak_days >= 3:
            achievements.append({
                "name": "🔥 3-Day Streak",
                "description": "Maintained 3-day sustainability streak"
            })
        
        # Assessment achievements
        if total_assessments >= 50:
            achievements.append({
                "name": "📊 Assessment Master",
                "description": "Completed 50+ assessments"
            })
        elif total_assessments >= 25:
            achievements.append({
                "name": "📊 Assessment Pro",
                "description": "Completed 25+ assessments"
            })
        elif total_assessments >= 10:
            achievements.append({
                "name": "📊 Assessment Explorer",
                "description": "Completed 10+ assessments"
            })
        elif total_assessments >= 5:
            achievements.append({
                "name": "📊 Assessment Beginner",
                "description": "Completed 5+ assessments"
            })
        
        return achievements
    
    def _get_challenges(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get user's active challenges."""
        challenges = user_data.get("challenges", [])
        
        # If no challenges, create sample ones
        if not challenges:
            challenges = [
                {
                    "title": "Reduce Energy Usage",
                    "progress": 60,
                    "target": 100,
                    "icon": "⚡"
                },
                {
                    "title": "Plant-Based Week",
                    "progress": 40,
                    "target": 100,
                    "icon": "🥗"
                }
            ]
        
        return challenges