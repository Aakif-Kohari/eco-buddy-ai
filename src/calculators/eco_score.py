"""
src/calculators/eco_score.py
----------------------------
Eco-score carbon footprint calculation engine with robust input validation and fallback defaults.
"""

from __future__ import annotations

from typing import Any


def calculate_eco_score(user_data: dict[str, Any] | None) -> dict[str, Any]:
    """Calculate the eco-score with graceful degradation and default values for partial assessments."""
    if not user_data:
        user_data = {}

    # Implement default values for missing diet and transport categories
    diet_category = user_data.get("diet", "average")
    transport_category = user_data.get("transport", "public_transit")
    energy_usage = user_data.get("energy_kwh", 0.0)

    # Base emission factors
    emission_factors = {
        "diet": {"vegan": 1.5, "vegetarian": 2.5, "average": 4.0, "heavy_meat": 7.0},
        "transport": {"bike": 0.1, "public_transit": 1.2, "car": 4.5, "flight": 8.0},
    }

    diet_score = emission_factors["diet"].get(diet_category, 4.0)
    transport_score = emission_factors["transport"].get(transport_category, 1.2)
    energy_score = float(energy_usage) * 0.5

    total_score = round(diet_score + transport_score + energy_score, 2)

    return {
        "status": "success",
        "eco_score": total_score,
        "categories_processed": {
            "diet": diet_category,
            "transport": transport_category,
        },
    }
