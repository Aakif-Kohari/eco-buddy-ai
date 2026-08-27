"""
Waste Prevention Engine.
Analyzes pantry inventory and generates timely alerts or recipe suggestions.
"""

from typing import Dict, Any, List
from src.utils.spoilage_predictor import SpoilagePredictor
from datetime import datetime


class WastePreventionEngine:
    """Generates actionable insights to prevent food waste."""

    def __init__(self):
        self.predictor = SpoilagePredictor()
        self.recipe_suggestions = {
            "spinach": [
                "Spinach and Feta Omelette",
                "Green Smoothie",
                "Sautéed Garlic Spinach",
            ],
            "milk": ["Pancakes", "Creamy Soup", "Smoothies"],
            "chicken breast": [
                "Chicken Stir-fry",
                "Grilled Chicken Salad",
                "Chicken Curry",
            ],
            "bread": ["French Toast", "Bread Pudding", "Croutons"],
            "tomatoes": ["Fresh Salsa", "Tomato Soup", "Caprese Salad"],
            "default": ["Soup", "Stir-fry", "Smoothie"],
        }

    def analyze_pantry(self, inventory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyzes the entire pantry and returns a health summary and alerts."""
        alerts = []
        health_score = 100.0
        total_items = len(inventory)
        expiring_items = 0

        for item in inventory:
            name = item["name"]
            purchase_date = item["purchase_date"]
            storage = item.get("storage", "refrigerated")

            exp_date = self.predictor.calculate_expiration_date(
                name, purchase_date, storage
            )
            days_left = self.predictor.get_days_until_expiration(exp_date)
            urgency = self.predictor.get_urgency_level(days_left)

            item["expiration_date"] = exp_date.strftime("%Y-%m-%d")
            item["days_remaining"] = days_left
            item["urgency"] = urgency

            if urgency in ["expired", "critical", "warning"]:
                expiring_items += 1
                health_score -= 20 if urgency == "critical" else 10

                # Generate specific recommendation
                recipes = self.recipe_suggestions.get(
                    name, self.recipe_suggestions["default"]
                )
                alerts.append(
                    {
                        "item": name,
                        "days_remaining": days_left,
                        "urgency": urgency,
                        "recommendation": f"Use soon! Try making: {recipes[0]} or {recipes[1]}",
                    }
                )

        if total_items > 0:
            health_score = max(0.0, min(100.0, health_score))
        else:
            health_score = 100.0

        return {
            "health_score": round(health_score, 1),
            "total_items": total_items,
            "expiring_items": expiring_items,
            "inventory": inventory,
            "alerts": alerts,
        }
