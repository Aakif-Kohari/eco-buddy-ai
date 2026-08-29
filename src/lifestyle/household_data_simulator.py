"""Household Data Simulator.

Populates newly created households with realistic, randomized historical
data to immediately provide users with meaningful charts and insights.
Simulates a baseline footprint across energy, transport, waste, and food.
"""

import logging
import random
from typing import Optional
from datetime import datetime, timedelta

from src.lifestyle.household import add_member
from src.lifestyle.household_activities import log_activity, VALID_CATEGORIES
from src.lifestyle.household_goals import create_goal

logger = logging.getLogger(__name__)

# Typical monthly footprint averages for simulation (kg CO2e)
SIMULATION_BASELINES = {
    "Energy": {"mean": 200.0, "std": 30.0},
    "Transport": {"mean": 250.0, "std": 50.0},
    "Food": {"mean": 180.0, "std": 20.0},
    "Waste": {"mean": 50.0, "std": 10.0},
    "Water": {"mean": 30.0, "std": 5.0},
    "Shopping": {"mean": 120.0, "std": 40.0}
}

def _random_normal(mean: float, std: float) -> float:
    """Simple Box-Muller transform for normal distribution simulation."""
    import math
    u1 = max(0.0001, random.random())
    u2 = random.random()
    z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return max(0.0, mean + z0 * std)

def simulate_historical_data(household_id: int, months_back: int = 6, num_members: int = 2) -> bool:
    """Generate realistic historical footprint data for a src.lifestyle.household.
    
    Args:
        household_id: The household to populate.
        months_back: Number of months to simulate into the past.
        num_members: How many members to ensure exist in the src.lifestyle.household.
        
    Returns:
        True if simulation was successful.
    """
    try:
        from household import get_members
        current_members = get_members(household_id)
        
        # 1. Ensure members exist
        member_ids = [m['id'] for m in current_members]
        while len(member_ids) < num_members:
            new_m_id = add_member(
                household_id, 
                name=f"Member {len(member_ids)+1}", 
                weight=1.0, 
                role="Adult"
            )
            if new_m_id:
                member_ids.append(new_m_id)
            else:
                break
                
        if not member_ids:
            logger.error("No members available for simulation.")
            return False
            
        today = datetime.now()
        
        # 2. Generate Activities
        # For each month going back, we generate some shared bills and individual activities
        for m_offset in range(months_back, -1, -1):
            base_date = today - timedelta(days=30 * m_offset)
            
            # Randomize date slightly within the month
            # Energy (Shared)
            energy_date = base_date - timedelta(days=random.randint(0, 5))
            energy_val = _random_normal(SIMULATION_BASELINES["Energy"]["mean"], SIMULATION_BASELINES["Energy"]["std"])
            log_activity(
                household_id, "Energy", energy_val, "kWh", energy_val, 
                energy_date.strftime("%Y-%m-%d"), "Monthly Power Bill"
            )
            
            # Water & Waste (Shared)
            water_val = _random_normal(SIMULATION_BASELINES["Water"]["mean"], SIMULATION_BASELINES["Water"]["std"])
            log_activity(
                household_id, "Water", water_val, "L", water_val, 
                base_date.strftime("%Y-%m-%d"), "Shared Water Usage"
            )
            
            waste_val = _random_normal(SIMULATION_BASELINES["Waste"]["mean"], SIMULATION_BASELINES["Waste"]["std"])
            log_activity(
                household_id, "Waste", waste_val, "kg", waste_val, 
                base_date.strftime("%Y-%m-%d"), "Household Trash"
            )
            
            # Individual Activities
            for m_id in member_ids:
                # Transport
                trans_date = base_date - timedelta(days=random.randint(1, 28))
                trans_val = _random_normal(SIMULATION_BASELINES["Transport"]["mean"], SIMULATION_BASELINES["Transport"]["std"])
                log_activity(
                    household_id, "Transport", trans_val, "mi", trans_val, 
                    trans_date.strftime("%Y-%m-%d"), "Monthly Commute", member_id=m_id
                )
                
                # Food
                food_date = base_date - timedelta(days=random.randint(1, 28))
                food_val = _random_normal(SIMULATION_BASELINES["Food"]["mean"], SIMULATION_BASELINES["Food"]["std"])
                log_activity(
                    household_id, "Food", food_val, "meals", food_val, 
                    food_date.strftime("%Y-%m-%d"), "Groceries & Dining", member_id=m_id
                )
                
                # Shopping (only occasional)
                if random.random() > 0.5:
                    shop_date = base_date - timedelta(days=random.randint(1, 28))
                    shop_val = _random_normal(SIMULATION_BASELINES["Shopping"]["mean"], SIMULATION_BASELINES["Shopping"]["std"])
                    log_activity(
                        household_id, "Shopping", shop_val, "items", shop_val, 
                        shop_date.strftime("%Y-%m-%d"), "Retail Purchases", member_id=m_id
                    )
                    
        # 3. Generate a sample goal
        future_date = today + timedelta(days=60)
        create_goal(
            household_id, 
            "Reduce Energy by 10%", 
            "energy", 
            150.0, 
            "kWh", 
            current_value=180.0, 
            deadline=future_date.strftime("%Y-%m-%d")
        )
        
        return True
    except Exception as e:
        logger.error(f"Failed to simulate data: {e}")
        return False
