"""
Food Spoilage Predictor.
Contains a database of common grocery items with shelf-life curves and storage condition modifiers.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta

# Base shelf life in days for common items under ideal conditions
BASE_SHELF_LIFE = {
    "spinach": 5,
    "milk": 7,
    "chicken breast": 2,
    "apples": 21,
    "bread": 5,
    "eggs": 21,
    "tomatoes": 7,
    "cheese": 14,
    "ground beef": 2,
    "carrots": 14,
}

# Storage condition multipliers (1.0 = ideal, <1.0 = worse, >1.0 = better)
STORAGE_MODIFIERS = {
    "refrigerated": 1.0,
    "pantry": 0.8,  # Generally shorter than refrigerated for perishables
    "freezer": 5.0,  # Extends life significantly
    "counter": 0.6,  # Worst for most perishables
}


class SpoilagePredictor:
    """Predicts food spoilage based on item type, purchase date, and storage."""

    def __init__(self):
        self.item_database = BASE_SHELF_LIFE

    def get_base_shelf_life(self, item_name: str) -> int:
        """Returns base shelf life in days, defaulting to 3 days if unknown."""
        item_lower = item_name.lower()
        for key in self.item_database:
            if key in item_lower:
                return self.item_database[key]
        return 3  # Default conservative estimate

    def calculate_expiration_date(
        self, item_name: str, purchase_date: str, storage_condition: str
    ) -> datetime:
        """Calculates the predicted expiration date."""
        base_days = self.get_base_shelf_life(item_name)
        modifier = STORAGE_MODIFIERS.get(storage_condition.lower(), 1.0)

        effective_days = int(base_days * modifier)
        purchase_dt = datetime.strptime(purchase_date, "%Y-%m-%d")
        return purchase_dt + timedelta(days=effective_days)

    def get_days_until_expiration(self, expiration_date: datetime) -> int:
        """Calculates days remaining until expiration."""
        today = datetime.now()
        delta = expiration_date - today
        return delta.days

    def get_urgency_level(self, days_remaining: int) -> str:
        """Categorizes urgency based on days remaining."""
        if days_remaining < 0:
            return "expired"
        elif days_remaining <= 2:
            return "critical"
        elif days_remaining <= 5:
            return "warning"
        else:
            return "safe"
