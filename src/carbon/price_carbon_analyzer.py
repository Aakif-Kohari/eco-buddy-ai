"""
Price-to-Carbon Analyzer.
Manages a dataset of grocery items with mock retail prices, carbon footprints, and calculated eco-efficiency scores.
"""

from typing import Dict, Any, List

# Mock dataset: price per kg, carbon footprint per kg (kg CO2e), and category
GROCERY_DATABASE = {
    "beef": {
        "price_per_kg": 15.0,
        "carbon_per_kg": 27.0,
        "category": "meat",
        "nutrition_score": 70,
    },
    "chicken": {
        "price_per_kg": 8.0,
        "carbon_per_kg": 6.0,
        "category": "meat",
        "nutrition_score": 75,
    },
    "lentils": {
        "price_per_kg": 3.0,
        "carbon_per_kg": 0.9,
        "category": "plant_protein",
        "nutrition_score": 85,
    },
    "tofu": {
        "price_per_kg": 4.5,
        "carbon_per_kg": 2.0,
        "category": "plant_protein",
        "nutrition_score": 80,
    },
    "rice": {
        "price_per_kg": 2.0,
        "carbon_per_kg": 4.0,
        "category": "grain",
        "nutrition_score": 60,
    },
    "oats": {
        "price_per_kg": 2.5,
        "carbon_per_kg": 0.5,
        "category": "grain",
        "nutrition_score": 80,
    },
    "almonds": {
        "price_per_kg": 20.0,
        "carbon_per_kg": 4.5,
        "category": "nuts",
        "nutrition_score": 75,
    },
    "peanuts": {
        "price_per_kg": 5.0,
        "carbon_per_kg": 0.4,
        "category": "nuts",
        "nutrition_score": 70,
    },
    "tomatoes_local": {
        "price_per_kg": 3.5,
        "carbon_per_kg": 1.4,
        "category": "vegetable",
        "nutrition_score": 85,
    },
    "tomatoes_imported": {
        "price_per_kg": 4.0,
        "carbon_per_kg": 5.0,
        "category": "vegetable",
        "nutrition_score": 80,
    },
}


class PriceCarbonAnalyzer:
    """Analyzes the price-to-carbon efficiency of grocery items."""

    def __init__(self):
        self.database = GROCERY_DATABASE

    def get_item_data(self, item_name: str) -> Dict[str, Any]:
        """Retrieves data for a specific grocery item."""
        return self.database.get(item_name.lower())

    def calculate_efficiency_score(self, item_name: str) -> float:
        """
        Calculates an eco-efficiency score.
        Higher score = better value (more nutrition, lower carbon, lower price).
        Formula: (Nutrition Score * 10) / (Price * Carbon)
        """
        data = self.get_item_data(item_name)
        if not data:
            return 0.0

        # Avoid division by zero
        price = max(0.1, data["price_per_kg"])
        carbon = max(0.1, data["carbon_per_kg"])

        score = (data["nutrition_score"] * 10) / (price * carbon)
        return round(score, 2)

    def get_all_items_with_efficiency(self) -> List[Dict[str, Any]]:
        """Returns all items augmented with their calculated efficiency scores."""
        items = []
        for name, data in self.database.items():
            items.append(
                {
                    "name": name,
                    **data,
                    "efficiency_score": self.calculate_efficiency_score(name),
                }
            )
        # Sort by efficiency score descending
        return sorted(items, key=lambda x: x["efficiency_score"], reverse=True)

    def find_substitutions(self, target_item: str) -> List[Dict[str, Any]]:
        """Finds cheaper, lower-carbon alternatives within the same category."""
        target_data = self.get_item_data(target_item)
        if not target_data:
            return []

        alternatives = []
        target_efficiency = self.calculate_efficiency_score(target_item)

        for name, data in self.database.items():
            if name == target_item:
                continue
            if data["category"] == target_data["category"]:
                alt_efficiency = self.calculate_efficiency_score(name)
                if alt_efficiency > target_efficiency:
                    alternatives.append(
                        {
                            "name": name,
                            "price_per_kg": data["price_per_kg"],
                            "carbon_per_kg": data["carbon_per_kg"],
                            "efficiency_score": alt_efficiency,
                            "carbon_savings_pct": round(
                                (
                                    (
                                        target_data["carbon_per_kg"]
                                        - data["carbon_per_kg"]
                                    )
                                    / target_data["carbon_per_kg"]
                                )
                                * 100,
                                1,
                            ),
                            "price_savings_pct": round(
                                (
                                    (target_data["price_per_kg"] - data["price_per_kg"])
                                    / target_data["price_per_kg"]
                                )
                                * 100,
                                1,
                            ),
                        }
                    )

        return sorted(alternatives, key=lambda x: x["efficiency_score"], reverse=True)
