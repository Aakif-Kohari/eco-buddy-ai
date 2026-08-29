"""Household Scenario Modeling and What-If Simulations.

This module provides an engine to project the impact of hypothetical
lifestyle changes (e.g., buying an EV, going vegan, installing solar)
on a household's footprint, budget, and goals over time.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.lifestyle.household_metrics import calculate_sustainability_score
from src.lifestyle.household_activities import get_category_breakdown, VALID_CATEGORIES

logger = logging.getLogger(__name__)

SCENARIO_PRESETS = {
    "buy_ev": {
        "title": "Switch Shared Car to EV",
        "description": "Replaces household gasoline vehicle trips with Electric Vehicle trips.",
        "category_impacts": {
            "Transport": -0.65, # Reduces transport emissions by ~65%
            "Energy": +0.15     # Increases home energy by ~15% for charging
        },
        "cost_estimate": "$35,000"
    },
    "solar_panels": {
        "title": "Install Rooftop Solar",
        "description": "Generates 80% of household electricity via solar panels.",
        "category_impacts": {
            "Energy": -0.80
        },
        "cost_estimate": "$12,000"
    },
    "vegan_household": {
        "title": "Go 100% Plant-Based",
        "description": "All household members adopt a strict vegan diet.",
        "category_impacts": {
            "Food": -0.50
        },
        "cost_estimate": "$0"
    },
    "composting": {
        "title": "Start Household Composting",
        "description": "Diverts organic waste from landfills.",
        "category_impacts": {
            "Waste": -0.40
        },
        "cost_estimate": "$50"
    },
    "public_transit": {
        "title": "Commute via Public Transit",
        "description": "Replace daily driving commutes with bus/train.",
        "category_impacts": {
            "Transport": -0.45
        },
        "cost_estimate": "-$2,000 (Savings)"
    },
    "smart_thermostat": {
        "title": "Install Smart Thermostat",
        "description": "Optimizes heating and cooling based on occupancy.",
        "category_impacts": {
            "Energy": -0.15
        },
        "cost_estimate": "$250"
    }
}

def simulate_scenarios(household_id: int) -> List[Dict[str, Any]]:
    """Run all scenario presets against the household's current footprint.
    
    Returns:
        A list of scenario dictionaries with projected outcomes.
    """
    baseline_breakdown = get_category_breakdown(household_id)
    baseline_total = sum(baseline_breakdown.values())
    
    if baseline_total == 0.0:
        return []
        
    results = []
    
    for key, preset in SCENARIO_PRESETS.items():
        projected_breakdown = baseline_breakdown.copy()
        
        for cat, impact_ratio in preset["category_impacts"].items():
            if cat in projected_breakdown:
                current_val = projected_breakdown[cat]
                projected_val = current_val * (1.0 + impact_ratio)
                projected_breakdown[cat] = max(0.0, projected_val)
                
        projected_total = sum(projected_breakdown.values())
        reduction_kg = baseline_total - projected_total
        reduction_pct = (reduction_kg / baseline_total * 100) if baseline_total > 0 else 0.0
        
        results.append({
            "id": key,
            "title": preset["title"],
            "description": preset["description"],
            "cost_estimate": preset["cost_estimate"],
            "projected_total_kg": projected_total,
            "reduction_kg": reduction_kg,
            "reduction_pct": reduction_pct,
            "projected_breakdown": projected_breakdown
        })
        
    # Sort by highest reduction
    results.sort(key=lambda x: x["reduction_kg"], reverse=True)
    return results


def calculate_payback_period(scenario_key: str, household_id: int, carbon_price_per_ton: float = 50.0) -> Optional[float]:
    """Calculate the estimated financial/carbon payback period in years.
    
    Assumes a fixed social cost of carbon or an actual carbon tax scenario.
    """
    if scenario_key not in SCENARIO_PRESETS:
        return None
        
    preset = SCENARIO_PRESETS[scenario_key]
    cost_str = preset["cost_estimate"].replace("$", "").replace(",", "")
    
    try:
        cost = float(cost_str)
    except ValueError:
        return None # e.g. for "$0" or "Savings" if not cleanly parsable
        
    if cost <= 0:
        return 0.0
        
    baseline_breakdown = get_category_breakdown(household_id)
    baseline_total = sum(baseline_breakdown.values())
    
    projected_breakdown = baseline_breakdown.copy()
    for cat, impact_ratio in preset["category_impacts"].items():
        if cat in projected_breakdown:
            projected_breakdown[cat] = max(0.0, projected_breakdown[cat] * (1.0 + impact_ratio))
            
    reduction_kg = baseline_total - sum(projected_breakdown.values())
    
    # Convert reduction (assuming monthly baseline) to annual tons
    annual_reduction_tons = (reduction_kg * 12) / 1000.0
    
    if annual_reduction_tons <= 0:
        return float('inf')
        
    annual_savings = annual_reduction_tons * carbon_price_per_ton
    
    if annual_savings <= 0:
        return float('inf')
        
    return cost / annual_savings


def recommend_top_scenario(household_id: int) -> Optional[Dict[str, Any]]:
    """Determine the single most impactful scenario for a src.lifestyle.household."""
    scenarios = simulate_scenarios(household_id)
    if not scenarios:
        return None
        
    # Pick the one with highest absolute reduction
    return scenarios[0]


def project_goal_achievement(household_id: int, goal_id: int, scenario_key: str) -> Dict[str, Any]:
    """Determine if a scenario would help achieve a specific goal."""
    from household_goals import get_goal
    goal = get_goal(goal_id)
    if not goal:
        return {"helps": False, "reason": "Goal not found."}
        
    if scenario_key not in SCENARIO_PRESETS:
        return {"helps": False, "reason": "Scenario not found."}
        
    metric = goal["metric"].title()
    preset = SCENARIO_PRESETS[scenario_key]
    
    if metric == "Overall":
        impact = sum(preset["category_impacts"].values())
    else:
        impact = preset["category_impacts"].get(metric, 0.0)
        
    if impact < 0:
        return {
            "helps": True, 
            "projected_reduction_pct": abs(impact) * 100,
            "reason": f"This scenario reduces {metric} footprint by ~{abs(impact)*100:.0f}%."
        }
    else:
        return {
            "helps": False,
            "projected_reduction_pct": 0,
            "reason": f"This scenario does not reduce {metric} src.carbon.emissions."
        }
