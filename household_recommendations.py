"""Household Sustainability Recommendations Engine.

Generates deterministic, tailored sustainability recommendations based on
a household's past activities, current goals, and member composition.
"""

import logging
from typing import List, Dict, Any

from household_activities import get_category_breakdown, VALID_CATEGORIES
from household_goals import get_goals
from household import get_members

logger = logging.getLogger(__name__)

# Basic heuristics for generating recommendations. 
# If a category constitutes more than this percentage of the total footprint, we trigger a specific rec.
CATEGORY_THRESHOLDS_PCT = {
    "Energy": 0.40,
    "Transport": 0.35,
    "Food": 0.30,
    "Waste": 0.15,
    "Water": 0.10,
    "Shopping": 0.20
}

RECOMMENDATION_LIBRARY = {
    "Energy": [
        "Your household's energy footprint is quite high. Consider conducting a phantom load audit (unplugging unused appliances).",
        "Consider pooling resources to invest in a smart thermostat for the house.",
        "Check if your utility provider offers a green energy purchasing program."
    ],
    "Transport": [
        "Transport makes up a massive portion of your shared footprint. Can household members carpool to common destinations?",
        "Consider shifting local errands to walking or biking instead of driving."
    ],
    "Food": [
        "Dietary choices are heavily impacting your score. Trying a 'Meatless Monday' as a household can dramatically reduce this.",
        "Consider bulk-buying household staples to reduce packaging waste and delivery emissions."
    ],
    "Waste": [
        "Waste emissions are higher than expected. Consider starting a shared household compost bin.",
        "Review your local recycling guidelines and place a sorting cheat-sheet near the bin."
    ],
    "Water": [
        "Consider installing low-flow showerheads in shared bathrooms.",
        "Run the dishwasher and washing machine only when you have a full load."
    ],
    "Shopping": [
        "Consider a 'no-spend' week for non-essential items.",
        "Buy second-hand furniture or appliances for shared household needs."
    ]
}

def generate_household_recommendations(household_id: int) -> List[str]:
    """Analyze household data and generate actionable recommendations.
    
    Args:
        household_id: The ID of the household.
        
    Returns:
        List of strings containing recommendations.
    """
    recommendations = []
    
    try:
        # 1. Analyze Footprint Breakdown
        breakdown = get_category_breakdown(household_id)
        total_footprint = sum(breakdown.values())
        
        if total_footprint > 0:
            for cat, impact in breakdown.items():
                if cat in CATEGORY_THRESHOLDS_PCT:
                    ratio = impact / total_footprint
                    if ratio > CATEGORY_THRESHOLDS_PCT[cat]:
                        # Pick the first recommendation for simplicity, in a real system we might randomize or track seen recs.
                        recs = RECOMMENDATION_LIBRARY.get(cat, [])
                        if recs:
                            recommendations.append(f"💡 {cat} Insight: {recs[0]}")
                            
        # 2. Analyze Goals
        goals = get_goals(household_id, status="active")
        if not goals:
            recommendations.append("🎯 Goal Setting: You have no active collective goals. Setting a shared goal (e.g., 'Reduce energy by 10%') increases accountability!")
        else:
            # Check for goals that are severely lagging
            for g in goals:
                if g['target_value'] > 0:
                    progress_pct = g['current_value'] / g['target_value']
                    # Assuming linear time progression isn't tracked here, but if progress is exactly 0 after being active.
                    if progress_pct == 0.0:
                        recommendations.append(f"⚠️ Goal Lag: Your goal '{g['title']}' hasn't seen any progress yet. Discuss an action plan with your housemates!")
                        
        # 3. Analyze Members
        members = get_members(household_id)
        if members and len(members) == 1:
            recommendations.append("👥 Teamwork: You are the only member in this household. Invite your flatmates or family members to track shared bills and activities together.")
            
        # Fallback positive reinforcement
        if not recommendations:
            recommendations.append("🌟 Keep it up! Your household's data looks incredibly balanced right now.")
            
        return recommendations
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return ["Stay mindful of your daily household energy consumption."]
