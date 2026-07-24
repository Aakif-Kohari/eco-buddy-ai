import os

# Base line and sensitivity for total footprint (if not using categories)
ECO_SCORE_BASELINE = float(os.environ.get("SCORING_BASELINE", 4000.0))
ECO_SCORE_SENSITIVITY = float(os.environ.get("SCORING_SENSITIVITY", 1000.0))

# Category weights for the eco score calculation
CATEGORY_WEIGHTS = {
    "Transport": float(os.environ.get("WEIGHT_TRANSPORT", 0.3)),
    "Electricity": float(os.environ.get("WEIGHT_ELECTRICITY", 0.3)),
    "Diet": float(os.environ.get("WEIGHT_DIET", 0.25)),
    "Flights": float(os.environ.get("WEIGHT_FLIGHTS", 0.15)),
}

# Canonical diet type constants
DIET_TYPES = ["Vegetarian", "Non-Vegetarian", "Vegan", "Omnivore", "Heavy Meat"]

DIET_NORMALIZE_MAP = {
    "vegetarian": "Vegetarian", "vegan": "Vegan",
    "non-vegetarian": "Non-Vegetarian",
    "omnivore": "Omnivore", "heavy meat": "Heavy Meat",
    "non veg": "Non-Vegetarian", "non-veg": "Non-Vegetarian",
    "plant based": "Vegan", "plant-based": "Vegan",
}


def normalize_diet(diet):
    if not diet:
        return "Vegetarian"
    lower = diet.strip().lower()
    if lower in DIET_NORMALIZE_MAP:
        return DIET_NORMALIZE_MAP[lower]
    if diet in DIET_TYPES:
        return diet
    return "Vegetarian"
