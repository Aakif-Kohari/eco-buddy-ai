"""
Carbon Equivalence Engine
Translates abstract kg CO₂ values into relatable real-world metrics.
"""

from typing import List, Dict, Any

EQUIVALENCE_FACTORS = {
    "trees_planted": {"name": "Trees planted (grown for 10 years)", "kg_per_unit": 6.0, "icon": "🌳"},
    "miles_driven": {"name": "Miles driven by average car", "kg_per_unit": 0.39, "icon": "🚗"},
    "smartphones_charged": {"name": "Smartphones charged", "kg_per_unit": 0.008, "icon": "📱"},
    "flights_ny_london": {"name": "Flights from NY to London", "kg_per_unit": 900.0, "icon": "✈️"},
    "gallons_gas": {"name": "Gallons of gasoline consumed", "kg_per_unit": 8.887, "icon": "⛽"},
    "pounds_coal": {"name": "Pounds of coal burned", "kg_per_unit": 0.893, "icon": "🪨"},
    "beef_burgers": {"name": "Number of beef burgers", "kg_per_unit": 2.5, "icon": "🍔"},
    "netflix_hours": {"name": "Hours of watching Netflix", "kg_per_unit": 0.056, "icon": "📺"},
    "showers_taken": {"name": "Average warm showers taken", "kg_per_unit": 1.2, "icon": "🚿"},
    "laundry_loads": {"name": "Loads of laundry (washed & dried)", "kg_per_unit": 2.4, "icon": "🧺"},
    "cups_coffee": {"name": "Cups of coffee", "kg_per_unit": 0.28, "icon": "☕"},
    "plastic_bags": {"name": "Plastic bags produced", "kg_per_unit": 0.033, "icon": "🛍️"},
    "home_electricity_days": {"name": "Days of electricity for an average home", "kg_per_unit": 15.0, "icon": "🏠"},
    "tshirts_produced": {"name": "Fast fashion t-shirts produced", "kg_per_unit": 2.1, "icon": "👕"},
    "bottled_water_liters": {"name": "Liters of bottled water", "kg_per_unit": 0.33, "icon": "💧"}
}

def translate_footprint(kg_co2: float, region: str = "Global", top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Translate kg CO2 into equivalence metrics.
    Currently uses global factors. Future enhancement can override based on region.
    """
    if kg_co2 < 0:
        return []
        
    results = []
    for key, data in EQUIVALENCE_FACTORS.items():
        if data["kg_per_unit"] <= 0:
            continue
            
        units = kg_co2 / data["kg_per_unit"]
        
        # Round intelligently
        if units > 100:
            units = round(units)
        elif units > 10:
            units = round(units, 1)
        else:
            units = round(units, 2)
            
        results.append({
            "key": key,
            "name": data["name"],
            "units": units,
            "icon": data["icon"]
        })
        
    # Sort by how "relatable" the number is. 
    # Numbers closer to 50 tend to be more relatable than millions or fractions.
    results_sorted = sorted(results, key=lambda x: abs(x["units"] - 50))
    
    return results_sorted[:top_n]


def get_category_equivalences(category: str, kg_co2: float) -> List[Dict[str, Any]]:
    """
    Get specifically related metrics based on the category.
    """
    if kg_co2 < 0:
        return []

    # Map categories to relevant metric keys
    category_map = {
        "transport": ["miles_driven", "gallons_gas", "flights_ny_london"],
        "diet": ["beef_burgers", "cups_coffee", "bottled_water_liters"],
        "energy": ["home_electricity_days", "showers_taken", "laundry_loads", "pounds_coal", "smartphones_charged"],
        "shopping": ["tshirts_produced", "plastic_bags", "netflix_hours"]
    }
    
    related_keys = category_map.get(category.lower(), list(EQUIVALENCE_FACTORS.keys())[:3])
    
    results = []
    for key in related_keys:
        data = EQUIVALENCE_FACTORS.get(key)
        if data and data["kg_per_unit"] > 0:
            units = kg_co2 / data["kg_per_unit"]
            if units > 100:
                units = round(units)
            elif units > 10:
                units = round(units, 1)
            else:
                units = round(units, 2)
            results.append({
                "key": key,
                "name": data["name"],
                "units": units,
                "icon": data["icon"]
            })
            
    return results
