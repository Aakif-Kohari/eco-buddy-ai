"""
Eco-Food Waste & Smart Pantry Analyzer Core Service Layer
Encapsulates business operations, spoilage risk calculation, recipe suggestion triggers, and analytics.
"""

from typing import List, Dict, Any, Optional
import logging

from eco_food_waste_pantry_types import (
    PantryItem,
    FoodCategory,
    StorageCondition,
    FoodWasteSummary,
)
from eco_food_waste_pantry_db import (
    init_food_waste_pantry_db,
    add_pantry_item,
    get_user_pantry_items,
    mark_pantry_item_status,
    get_food_waste_summary_stats,
)

logger = logging.getLogger(__name__)


class FoodWastePantryService:
    def __init__(self, db_name: str = "eco_buddy.db"):
        self.db_name = db_name
        init_food_waste_pantry_db(self.db_name)

    def add_item_to_pantry(
        self,
        user_id: int,
        item_name: str,
        category: FoodCategory,
        quantity: float,
        unit: str,
        purchase_date: str,
        shelf_life_days: int,
        storage_condition: StorageCondition,
        co2_footprint_kg_per_unit: float,
        cost_per_unit_usd: float,
    ) -> Optional[PantryItem]:
        """Adds a food item to user's smart pantry."""
        item = PantryItem(
            id=None,
            user_id=user_id,
            item_name=item_name,
            category=category,
            quantity=quantity,
            unit=unit,
            purchase_date=purchase_date,
            shelf_life_days=shelf_life_days,
            storage_condition=storage_condition,
            co2_footprint_kg_per_unit=co2_footprint_kg_per_unit,
            cost_per_unit_usd=cost_per_unit_usd,
        )
        return add_pantry_item(item, self.db_name)

    def get_active_pantry(self, user_id: int, category_filter: Optional[str] = None) -> List[PantryItem]:
        """Retrieves active pantry items with optional category filtering."""
        items = get_user_pantry_items(user_id, self.db_name)
        if category_filter and category_filter != "All":
            items = [i for i in items if i.category.value == category_filter]
        return items

    def get_at_risk_items(self, user_id: int) -> List[PantryItem]:
        """Returns pantry items expiring within 3 days or already expired."""
        items = get_user_pantry_items(user_id, self.db_name)
        return [i for i in items if i.get_spoilage_risk() in ["EXPIRED", "HIGH_RISK", "MODERATE_RISK"]]

    def mark_consumed(self, item_id: int) -> bool:
        """Marks item as consumed successfully."""
        return mark_pantry_item_status(item_id, is_consumed=True, is_wasted=False, db_name=self.db_name)

    def mark_wasted(self, item_id: int) -> bool:
        """Marks item as wasted/discarded."""
        return mark_pantry_item_status(item_id, is_consumed=False, is_wasted=True, db_name=self.db_name)

    def get_user_summary(self, user_id: int) -> FoodWasteSummary:
        """Calculates total food waste metrics and environmental impact."""
        return get_food_waste_summary_stats(user_id, self.db_name)
