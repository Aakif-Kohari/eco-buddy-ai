"""Household Data Export and Import System.

Provides utilities for households to backup their complete dataset
(activities, goals, budgets) into JSON format, and parse it back if needed
for data portability and transparency.
"""

import json
import logging
from typing import Dict, Any, Optional

from household import get_household, get_members
from household_activities import get_activities
from household_goals import get_goals
from household_budgeting import get_budgets
from household_gamification import get_badges, get_challenges, _get_household_xp

logger = logging.getLogger(__name__)


def export_household_data_json(household_id: int) -> Optional[str]:
    """Export the entire household dataset as a JSON string."""
    try:
        # 1. Base Household Info
        hh = get_household(household_id)
        if not hh:
            logger.error(f"Cannot export. Household {household_id} not found.")
            return None
            
        # 2. Members
        members = get_members(household_id)
        
        # 3. Activities
        activities = get_activities(household_id, limit=50000)
        
        # 4. Goals
        goals = get_goals(household_id)
        
        # 5. Budgets
        budgets = get_budgets(household_id, active_only=False)
        
        # 6. Gamification
        xp_data = _get_household_xp(household_id)
        badges = get_badges(household_id)
        challenges = get_challenges(household_id)
        
        export_payload = {
            "version": "1.0",
            "exported_at": hh.get("created_at"), # Approximation of time if we don't use datetime.now
            "household": {
                "id": hh["id"],
                "name": hh["name"],
                "allocation_method": hh.get("allocation_method", "equal"),
                "region": hh.get("region", "Global")
            },
            "members": [
                {
                    "id": m["id"],
                    "name": m["name"],
                    "role": m["role"],
                    "weight": m["weight"]
                } for m in members
            ],
            "activities": [
                {
                    "id": act["id"],
                    "category": act["category"],
                    "value": act["value"],
                    "unit": act["unit"],
                    "impact_kg_co2": act["impact_kg_co2"],
                    "date": act["activity_date"],
                    "description": act["description"],
                    "member_id": act["member_id"]
                } for act in activities
            ],
            "goals": [
                {
                    "title": g["title"],
                    "metric": g["metric"],
                    "target_value": g["target_value"],
                    "current_value": g["current_value"],
                    "unit": g["unit"],
                    "status": g["status"],
                    "deadline": g["deadline"]
                } for g in goals
            ],
            "budgets": [
                {
                    "category": b["category"],
                    "limit_value": b["limit_value"],
                    "unit": b["unit"],
                    "period": b["period"],
                    "active": b["active"]
                } for b in budgets
            ],
            "gamification": {
                "xp": xp_data["total_xp"],
                "level": xp_data["level"],
                "badges": [
                    {
                        "name": b["badge_name"],
                        "earned_date": b["earned_date"]
                    } for b in badges
                ],
                "challenges": [
                    {
                        "title": c["title"],
                        "status": c["status"]
                    } for c in challenges
                ]
            }
        }
        
        return json.dumps(export_payload, indent=2)
    except Exception as e:
        logger.error(f"Error exporting household data: {e}")
        return None


def calculate_data_completeness(household_id: int) -> float:
    """Analyze how much of the system's features a household is actively using."""
    score = 0.0
    total_checks = 5.0
    
    hh = get_household(household_id)
    if not hh:
        return 0.0
        
    members = get_members(household_id)
    if members:
        score += 1.0
        
    activities = get_activities(household_id, limit=1)
    if activities:
        score += 1.0
        
    goals = get_goals(household_id)
    if goals:
        score += 1.0
        
    budgets = get_budgets(household_id)
    if budgets:
        score += 1.0
        
    badges = get_badges(household_id)
    if badges:
        score += 1.0
        
    return (score / total_checks) * 100.0
