"""
Unit and Integration Tests for Smart Pantry & Food Waste Analyzer Engine
"""

import unittest
import os
from datetime import date, timedelta
from eco_food_waste_pantry_types import (
    FoodCategory,
    StorageCondition,
    PantryItem,
)
from eco_food_waste_pantry_db import (
    init_food_waste_pantry_db,
    get_user_pantry_items,
    mark_pantry_item_status,
    get_food_waste_summary_stats,
)
from eco_food_waste_pantry_service import FoodWastePantryService

TEST_DB = "test_eco_food_waste_pantry.db"


class TestFoodWastePantryEngine(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        init_food_waste_pantry_db(TEST_DB)
        self.service = FoodWastePantryService(db_name=TEST_DB)

    def tearDown(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_database_initialization_and_seeding(self):
        items = self.service.get_active_pantry(1)
        self.assertGreaterEqual(len(items), 5)
        self.assertEqual(items[0].item_name, "Fresh Organic Spinach")

    def test_spoilage_risk_calculation(self):
        today_str = date.today().isoformat()
        item = PantryItem(
            id=1,
            user_id=1,
            item_name="Test Milk",
            category=FoodCategory.DAIRY,
            quantity=1.0,
            unit="carton",
            purchase_date=today_str,
            shelf_life_days=2,
            storage_condition=StorageCondition.REFRIGERATED,
            co2_footprint_kg_per_unit=0.7,
            cost_per_unit_usd=3.50,
        )
        self.assertEqual(item.get_spoilage_risk(), "HIGH_RISK")

    def test_mark_consumed_and_wasted(self):
        items = self.service.get_active_pantry(1)
        item_id = items[0].id

        # Mark consumed
        self.assertTrue(self.service.mark_consumed(item_id))
        active_remaining = self.service.get_active_pantry(1)
        self.assertEqual(len(active_remaining), len(items) - 1)

    def test_summary_analytics(self):
        items = self.service.get_active_pantry(1)
        self.service.mark_consumed(items[0].id)
        self.service.mark_wasted(items[1].id)

        summary = self.service.get_user_summary(1)
        self.assertEqual(summary.items_consumed, 1)
        self.assertEqual(summary.items_wasted, 1)
        self.assertGreater(summary.co2_prevented_kg, 0.0)


if __name__ == "__main__":
    unittest.main()
