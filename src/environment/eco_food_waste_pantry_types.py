"""
Eco-Food Waste & Smart Pantry Analyzer Data Types
Dataclasses, Enums, and structures for pantry item tracking, spoilage risk prediction, and emissions footprint.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class FoodCategory(str, Enum):
    PRODUCE = "Produce (Fruits & Veggies)"
    DAIRY = "Dairy & Eggs"
    MEAT_SEAFOOD = "Meat & Seafood"
    BAKERY = "Bakery & Grains"
    PANTRY_DRY = "Pantry & Dry Goods"
    BEVERAGES = "Beverages"


class StorageCondition(str, Enum):
    REFRIGERATED = "Refrigerated"
    FROZEN = "Frozen"
    PANTRY_ROOM_TEMP = "Pantry (Room Temp)"


@dataclass
class PantryItem:
    id: Optional[int]
    user_id: int
    item_name: str
    category: FoodCategory
    quantity: float
    unit: str
    purchase_date: str
    shelf_life_days: int
    storage_condition: StorageCondition
    co2_footprint_kg_per_unit: float
    cost_per_unit_usd: float
    is_consumed: bool = False
    is_wasted: bool = False

    def calculate_expiration_date(self) -> date:
        p_date = date.fromisoformat(self.purchase_date)
        return p_date + datetime.timedelta(days=self.shelf_life_days)

    def days_until_expiration(self) -> int:
        p_date = date.fromisoformat(self.purchase_date)
        exp_date = p_date + datetime.timedelta(days=self.shelf_life_days)
        return (exp_date - date.today()).days

    def get_spoilage_risk(self) -> str:
        days_left = self.days_until_expiration()
        if days_left < 0:
            return "EXPIRED"
        elif days_left <= 2:
            return "HIGH_RISK"
        elif days_left <= 5:
            return "MODERATE_RISK"
        return "LOW_RISK"


@dataclass
class FoodWasteSummary:
    total_items_tracked: int
    items_consumed: int
    items_wasted: int
    co2_prevented_kg: float
    co2_lost_to_waste_kg: float
    money_saved_usd: float
    money_lost_usd: float
    waste_reduction_rate_pct: float
