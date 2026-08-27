"""
Smart Shopping List Builder.
Generates an optimized shopping list that minimizes carbon per dollar spent while meeting dietary needs.
"""

from typing import Dict, Any, List
from src.carbon.price_carbon_analyzer import PriceCarbonAnalyzer


class SmartShoppingList:
    """Builds budget-constrained, eco-optimized shopping lists."""

    def __init__(self):
        self.analyzer = PriceCarbonAnalyzer()

    def generate_optimized_list(
        self, budget_usd: float, required_categories: List[str]
    ) -> Dict[str, Any]:
        """
        Generates a shopping list that maximizes nutritional value and minimizes carbon within a budget.
        Uses a greedy algorithm based on efficiency scores.
        """
        all_items = self.analyzer.get_all_items_with_efficiency()

        # Filter to only include required categories
        filtered_items = [
            item for item in all_items if item["category"] in required_categories
        ]

        remaining_budget = budget_usd
        shopping_list = []
        total_carbon = 0.0
        total_nutrition = 0.0

        # Greedily add the most efficient items until budget is exhausted
        for item in filtered_items:
            if remaining_budget <= 0:
                break

            # Determine how much of this item we can buy
            # We'll buy in 1kg increments for simplicity, or whatever the remaining budget allows
            kg_to_buy = min(1.0, remaining_budget / item["price_per_kg"])

            if kg_to_buy > 0.1:  # Minimum viable purchase of 0.1 kg
                cost = kg_to_buy * item["price_per_kg"]
                carbon = kg_to_buy * item["carbon_per_kg"]
                nutrition = kg_to_buy * item["nutrition_score"]

                shopping_list.append(
                    {
                        "item": item["name"],
                        "category": item["category"],
                        "quantity_kg": round(kg_to_buy, 2),
                        "cost_usd": round(cost, 2),
                        "carbon_kg": round(carbon, 2),
                        "nutrition_points": round(nutrition, 1),
                    }
                )

                remaining_budget -= cost
                total_carbon += carbon
                total_nutrition += nutrition

        return {
            "budget_usd": budget_usd,
            "remaining_budget_usd": round(remaining_budget, 2),
            "total_carbon_kg": round(total_carbon, 2),
            "total_nutrition_points": round(total_nutrition, 1),
            "average_carbon_per_dollar": round(
                total_carbon / (budget_usd - remaining_budget), 2
            )
            if (budget_usd - remaining_budget) > 0
            else 0.0,
            "items": shopping_list,
        }

    def compare_lists(
        self,
        standard_items: List[str],
        optimized_categories: List[str],
        budget_usd: float,
    ) -> Dict[str, Any]:
        """Compares a user's standard list against the optimized generator."""
        # Calculate standard list metrics
        std_cost = 0.0
        std_carbon = 0.0
        for item_name in standard_items:
            data = self.analyzer.get_item_data(item_name)
            if data:
                std_cost += data["price_per_kg"]  # Assuming 1kg each for comparison
                std_carbon += data["carbon_per_kg"]

        optimized = self.generate_optimized_list(budget_usd, optimized_categories)

        return {
            "standard": {
                "estimated_cost_usd": round(std_cost, 2),
                "estimated_carbon_kg": round(std_carbon, 2),
            },
            "optimized": {
                "budget_usd": optimized["budget_usd"],
                "total_carbon_kg": optimized["total_carbon_kg"],
                "total_nutrition_points": optimized["total_nutrition_points"],
            },
            "carbon_savings_kg": round(std_carbon - optimized["total_carbon_kg"], 2),
            "carbon_savings_pct": round(
                ((std_carbon - optimized["total_carbon_kg"]) / std_carbon) * 100, 1
            )
            if std_carbon > 0
            else 0.0,
        }
