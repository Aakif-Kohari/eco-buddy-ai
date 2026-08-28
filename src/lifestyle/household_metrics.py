"""Household sustainability metrics and analytics.

This module provides analytical functions to evaluate household
performance across carbon, energy, water, waste, and more.
It integrates data from household_activities and base household properties.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.lifestyle.household_activities import get_category_breakdown, get_member_contribution_breakdown
from src.lifestyle.household_goals import get_goals

logger = logging.getLogger(__name__)

# Base benchmarks per category (kg CO2e / month / person) - purely illustrative
BENCHMARKS = {
    "Energy": 150.0,
    "Transport": 200.0,
    "Food": 180.0,
    "Waste": 50.0,
    "Water": 30.0,
    "Shopping": 100.0,
    "Other": 40.0
}

def calculate_sustainability_score(household_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """Calculate the household's overall sustainability score.
    
    The score (0-100) is derived from their carbon footprint compared to 
    standard benchmarks, adjusted for the number of household members.
    
    Returns:
        Dict containing the score, total_footprint, and feedback message.
    """
    from household import get_members, get_household
    
    hh = get_household(household_id)
    if not hh:
        return {"score": 0, "total_footprint": 0.0, "feedback": "Household not found."}
        
    members = get_members(household_id)
    member_count = len(members) if members else 1
    
    breakdown = get_category_breakdown(household_id, start_date, end_date)
    total_footprint = sum(breakdown.values())
    
    if total_footprint == 0.0:
        return {
            "score": 100, 
            "total_footprint": 0.0, 
            "feedback": "No activities logged yet. Perfect baseline!",
            "category_breakdown": breakdown
        }
    
    # Calculate a simple benchmark footprint for the period
    # Assuming the breakdown covers roughly 1 month if no dates given.
    # For a real implementation, we would scale benchmarks by the actual date delta.
    expected_footprint = sum(BENCHMARKS.values()) * member_count
    
    # Score logic: 100 if footprint is 0, 50 if footprint matches expected, 0 if 2x expected.
    ratio = total_footprint / expected_footprint
    raw_score = 100 - (ratio * 50)
    score = max(0, min(100, int(raw_score)))
    
    if score >= 80:
        feedback = "Excellent! Your household is operating highly sustainably."
    elif score >= 50:
        feedback = "Good job. Your household is around average, but there's room to improve."
    else:
        feedback = "Your household impact is higher than average. Consider checking your highest impact categories."
        
    return {
        "score": score,
        "total_footprint": total_footprint,
        "feedback": feedback,
        "category_breakdown": breakdown,
        "expected_monthly_footprint": expected_footprint
    }


def get_household_analytics_summary(household_id: int) -> Dict[str, Any]:
    """Compile a comprehensive analytics summary for the dashboard."""
    from household import get_members
    
    score_data = calculate_sustainability_score(household_id)
    member_breakdown = get_member_contribution_breakdown(household_id)
    
    # Goal progress
    goals = get_goals(household_id)
    active_goals = [g for g in goals if g["status"] == "active"]
    completed_goals = [g for g in goals if g["status"] == "completed"]
    
    goal_completion_rate = 0.0
    if len(goals) > 0:
        goal_completion_rate = (len(completed_goals) / len(goals)) * 100
        
    members = get_members(household_id)
    
    return {
        "score_data": score_data,
        "member_breakdown": member_breakdown,
        "metrics": {
            "total_members": len(members),
            "active_goals_count": len(active_goals),
            "completed_goals_count": len(completed_goals),
            "goal_completion_rate": goal_completion_rate,
            "total_footprint_kg": score_data["total_footprint"]
        },
        "top_improvement_area": _identify_top_improvement_area(score_data["category_breakdown"], len(members) or 1)
    }

def _identify_top_improvement_area(breakdown: Dict[str, float], member_count: int) -> str:
    """Identify the category most exceeding its benchmark."""
    worst_cat = None
    max_exceed_ratio = 0.0
    
    for cat, impact in breakdown.items():
        if cat in BENCHMARKS:
            benchmark = BENCHMARKS[cat] * member_count
            if benchmark > 0:
                ratio = impact / benchmark
                if ratio > max_exceed_ratio and ratio > 1.0:
                    max_exceed_ratio = ratio
                    worst_cat = cat
                    
    if worst_cat:
        return f"{worst_cat} (exceeds benchmark by {int((max_exceed_ratio - 1) * 100)}%)"
    return "None right now! You are within benchmarks across the board."
