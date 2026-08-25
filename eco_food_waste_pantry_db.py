"""
Eco-Food Waste & Smart Pantry Analyzer Database Layer
Handles SQLite table initialization, pantry item tracking, consumption/spoilage updates, and summary statistics.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta, datetime

from database_connection import database_connection, execute_with_retry
from eco_food_waste_pantry_types import (
    PantryItem,
    FoodCategory,
    StorageCondition,
    FoodWasteSummary,
)

logger = logging.getLogger(__name__)
DB_NAME = "eco_buddy.db"


def init_food_waste_pantry_db(db_name: str = DB_NAME) -> bool:
    """Initializes SQLite tables for smart pantry and food waste tracking."""
    def _create():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()

            # Smart Pantry Items Master Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS smart_pantry_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    item_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    unit TEXT NOT NULL,
                    purchase_date TEXT NOT NULL,
                    shelf_life_days INTEGER NOT NULL,
                    storage_condition TEXT NOT NULL,
                    co2_footprint_kg_per_unit REAL NOT NULL,
                    cost_per_unit_usd REAL NOT NULL,
                    is_consumed INTEGER DEFAULT 0,
                    is_wasted INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    try:
        execute_with_retry(_create)
        _seed_default_pantry_items(db_name)
        return True
    except sqlite3.Error as e:
        logger.error("Failed to initialize food waste pantry DB: %s", e)
        return False


def _seed_default_pantry_items(db_name: str = DB_NAME) -> None:
    """Seeds sample pantry inventory for default user if empty."""
    def _seed():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM smart_pantry_inventory WHERE user_id = 1")
            count = cursor.fetchone()[0]

            if count == 0:
                today_str = date.today().isoformat()
                three_days_ago = (date.today() - timedelta(days=3)).isoformat()

                defaults = [
                    (1, "Fresh Organic Spinach", FoodCategory.PRODUCE.value, 1.0, "bag", three_days_ago, 5, StorageCondition.REFRIGERATED.value, 0.45, 3.49, 0, 0),
                    (1, "Almond Milk (Unsweetened)", FoodCategory.DAIRY.value, 1.0, "carton", three_days_ago, 10, StorageCondition.REFRIGERATED.value, 0.70, 3.99, 0, 0),
                    (1, "Whole Wheat Bread", FoodCategory.BAKERY.value, 1.0, "loaf", today_str, 7, StorageCondition.PANTRY_ROOM_TEMP.value, 0.85, 2.99, 0, 0),
                    (1, "Avocados", FoodCategory.PRODUCE.value, 3.0, "items", three_days_ago, 4, StorageCondition.PANTRY_ROOM_TEMP.value, 0.60, 4.50, 0, 0),
                    (1, "Greek Yogurt", FoodCategory.DAIRY.value, 2.0, "tubs", today_str, 14, StorageCondition.REFRIGERATED.value, 1.20, 5.20, 0, 0),
                ]

                cursor.executemany("""
                    INSERT INTO smart_pantry_inventory
                    (user_id, item_name, category, quantity, unit, purchase_date, shelf_life_days, storage_condition, co2_footprint_kg_per_unit, cost_per_unit_usd, is_consumed, is_wasted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, defaults)

                conn.commit()

    try:
        execute_with_retry(_seed)
    except Exception as e:
        logger.error("Error seeding pantry items: %s", e)


def add_pantry_item(item: PantryItem, db_name: str = DB_NAME) -> Optional[PantryItem]:
    """Adds a new food item to pantry inventory."""
    def _insert():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO smart_pantry_inventory
                (user_id, item_name, category, quantity, unit, purchase_date, shelf_life_days, storage_condition, co2_footprint_kg_per_unit, cost_per_unit_usd, is_consumed, is_wasted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (
                item.user_id, item.item_name, item.category.value, item.quantity, item.unit,
                item.purchase_date, item.shelf_life_days, item.storage_condition.value,
                item.co2_footprint_kg_per_unit, item.cost_per_unit_usd
            ))

            item.id = cursor.lastrowid
            conn.commit()
            return item

    try:
        return execute_with_retry(_insert)
    except Exception as e:
        logger.error("Error adding pantry item: %s", e)
        return None


def get_user_pantry_items(user_id: int, db_name: str = DB_NAME) -> List[PantryItem]:
    """Fetches active (unconsumed & unwasted) pantry items for a user."""
    def _fetch():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, item_name, category, quantity, unit, purchase_date, shelf_life_days, storage_condition, co2_footprint_kg_per_unit, cost_per_unit_usd, is_consumed, is_wasted
                FROM smart_pantry_inventory
                WHERE user_id = ? AND is_consumed = 0 AND is_wasted = 0
                ORDER BY purchase_date ASC
            """, (user_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append(PantryItem(
                    id=r[0],
                    user_id=r[1],
                    item_name=r[2],
                    category=FoodCategory(r[3]),
                    quantity=r[4],
                    unit=r[5],
                    purchase_date=r[6],
                    shelf_life_days=r[7],
                    storage_condition=StorageCondition(r[8]),
                    co2_footprint_kg_per_unit=r[9],
                    cost_per_unit_usd=r[10],
                    is_consumed=bool(r[11]),
                    is_wasted=bool(r[12]),
                ))
            return results

    try:
        return execute_with_retry(_fetch)
    except Exception as e:
        logger.error("Error fetching user pantry items: %s", e)
        return []


def mark_pantry_item_status(item_id: int, is_consumed: bool, is_wasted: bool, db_name: str = DB_NAME) -> bool:
    """Updates item status as consumed or wasted."""
    def _update():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE smart_pantry_inventory
                SET is_consumed = ?, is_wasted = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (int(is_consumed), int(is_wasted), item_id))
            conn.commit()
            return True

    try:
        return execute_with_retry(_update)
    except Exception as e:
        logger.error("Error updating pantry item status: %s", e)
        return False


def get_food_waste_summary_stats(user_id: int, db_name: str = DB_NAME) -> FoodWasteSummary:
    """Calculates overall food waste prevention metrics, financial savings, and CO2 emissions."""
    def _summary():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*),
                    SUM(CASE WHEN is_consumed = 1 THEN 1 ELSE 0 END),
                    SUM(CASE WHEN is_wasted = 1 THEN 1 ELSE 0 END),
                    SUM(CASE WHEN is_consumed = 1 THEN quantity * co2_footprint_kg_per_unit ELSE 0 END),
                    SUM(CASE WHEN is_wasted = 1 THEN quantity * co2_footprint_kg_per_unit ELSE 0 END),
                    SUM(CASE WHEN is_consumed = 1 THEN quantity * cost_per_unit_usd ELSE 0 END),
                    SUM(CASE WHEN is_wasted = 1 THEN quantity * cost_per_unit_usd ELSE 0 END)
                FROM smart_pantry_inventory
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()

            total_items = row[0] or 0
            consumed = row[1] or 0
            wasted = row[2] or 0
            co2_prevented = round(row[3] or 0.0, 2)
            co2_lost = round(row[4] or 0.0, 2)
            money_saved = round(row[5] or 0.0, 2)
            money_lost = round(row[6] or 0.0, 2)

            resolved = consumed + wasted
            reduction_rate = round((consumed / resolved) * 100.0, 1) if resolved > 0 else 100.0

            return FoodWasteSummary(
                total_items_tracked=total_items,
                items_consumed=consumed,
                items_wasted=wasted,
                co2_prevented_kg=co2_prevented,
                co2_lost_to_waste_kg=co2_lost,
                money_saved_usd=money_saved,
                money_lost_usd=money_lost,
                waste_reduction_rate_pct=reduction_rate,
            )

    try:
        return execute_with_retry(_summary)
    except Exception as e:
        logger.error("Error calculating food waste summary stats: %s", e)
        return FoodWasteSummary(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)
