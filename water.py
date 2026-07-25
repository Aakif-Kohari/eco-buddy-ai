# water.py
import streamlit as st
from config import normalize_diet

GLOBAL_WATER_AVERAGE_LITERS = 3800.0

WATER_FACTORS = {
    "shower_liter_per_min": 10.0,
    "laundry_liter_per_load": 50.0,
    "dishwasher_liter_per_run": 15.0,
    "garden_liter_per_min": 20.0,
}

DIET_VIRTUAL_WATER = {
    "Vegan": 2000.0,
    "Vegetarian": 2500.0,
    "Omnivore": 4000.0,
    "Heavy Meat": 5000.0
}

@st.cache_data
def calculate_water_footprint(shower_mins_per_day, laundry_loads_per_week, dishwasher_runs_per_week, garden_mins_per_week, diet):
    """
    Calculates the estimated daily water footprint in liters.
    """
    daily_shower = shower_mins_per_day * WATER_FACTORS["shower_liter_per_min"]
    daily_laundry = (laundry_loads_per_week * WATER_FACTORS["laundry_liter_per_load"]) / 7.0
    daily_dishwasher = (dishwasher_runs_per_week * WATER_FACTORS["dishwasher_liter_per_run"]) / 7.0
    daily_garden = (garden_mins_per_week * WATER_FACTORS["garden_liter_per_min"]) / 7.0
    
    diet = normalize_diet(diet)
    daily_diet = DIET_VIRTUAL_WATER.get(diet, DIET_VIRTUAL_WATER["Omnivore"])
    
    total_daily = daily_shower + daily_laundry + daily_dishwasher + daily_garden + daily_diet
    
    contributors = {
        "Shower": daily_shower,
        "Laundry": daily_laundry,
        "Dishwasher": daily_dishwasher,
        "Garden": daily_garden,
        "Diet": daily_diet
    }
    
    return total_daily, contributors
