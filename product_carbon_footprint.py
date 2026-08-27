"""Product Carbon Footprint (PCF) Calculator & Green Shopping Advisor for EcoBuddy AI.

Estimates the CO₂ footprint of everyday consumer products across their full
lifecycle — raw materials, manufacturing, transport, use, and disposal.
Compares conventional items against eco-friendly alternatives, calculates
shopping cart totals, and provides personalised green shopping recommendations.

Emissions modelled as::

    kg CO₂ = unit_weight_kg × carbon_intensity_per_kg × quantity

Carbon intensities are derived from published lifecycle assessment (LCA)
databases (European Environment Agency, DEFRA, IPCC) and deliberately
conservative so they can be tuned per-user without touching calculation logic.
"""

from __future__ import annotations

import os
import json
import sqlite3
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

# ── Lifecycle Stages ─────────────────────────────────────────────────────────

LIFECYCLE_STAGES = ("materials", "manufacturing", "transport", "use_phase", "disposal")

# ── Product Catalogue ────────────────────────────────────────────────────────

# Each product has:
#   - name / icon / category
#   - conventional: carbon intensity per kg at each lifecycle stage
#   - eco_alternative (optional): same structure for the green alternative
#   - unit_weight_kg: typical weight of one unit
#   - typical_lifetime_uses: how many times the product is used before replacement

PRODUCT_CATALOGUE: dict[str, dict[str, Any]] = {
    # ── Clothing ────────────────────────────────────────────────────────
    "cotton_tshirt": {
        "name": "Cotton T-Shirt",
        "icon": "👕",
        "category": "Clothing",
        "unit_weight_kg": 0.25,
        "typical_lifetime_uses": 50,
        "conventional": {
            "materials": 2.1,
            "manufacturing": 1.8,
            "transport": 0.6,
            "use_phase": 1.2,
            "disposal": 0.5,
        },
        "eco_alternative": {
            "name": "Organic Cotton T-Shirt",
            "materials": 1.4,
            "manufacturing": 1.2,
            "transport": 0.5,
            "use_phase": 0.8,
            "disposal": 0.3,
        },
    },
    "denim_jeans": {
        "name": "Denim Jeans",
        "icon": "👖",
        "category": "Clothing",
        "unit_weight_kg": 0.8,
        "typical_lifetime_uses": 100,
        "conventional": {
            "materials": 5.0,
            "manufacturing": 3.5,
            "transport": 1.2,
            "use_phase": 4.0,
            "disposal": 1.5,
        },
        "eco_alternative": {
            "name": "Recycled Denim Jeans",
            "materials": 2.8,
            "manufacturing": 2.0,
            "transport": 1.0,
            "use_phase": 3.0,
            "disposal": 0.8,
        },
    },
    "running_shoes": {
        "name": "Running Shoes",
        "icon": "👟",
        "category": "Clothing",
        "unit_weight_kg": 0.6,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 6.0,
            "manufacturing": 4.5,
            "transport": 1.5,
            "use_phase": 0.5,
            "disposal": 2.0,
        },
        "eco_alternative": {
            "name": "Recycled-Material Shoes",
            "materials": 3.0,
            "manufacturing": 3.0,
            "transport": 1.2,
            "use_phase": 0.4,
            "disposal": 1.0,
        },
    },
    "winter_jacket": {
        "name": "Winter Jacket",
        "icon": "🧥",
        "category": "Clothing",
        "unit_weight_kg": 1.2,
        "typical_lifetime_uses": 150,
        "conventional": {
            "materials": 8.0,
            "manufacturing": 5.0,
            "transport": 2.0,
            "use_phase": 6.0,
            "disposal": 2.5,
        },
        "eco_alternative": {
            "name": "Recycled-Content Jacket",
            "materials": 4.5,
            "manufacturing": 3.5,
            "transport": 1.8,
            "use_phase": 5.0,
            "disposal": 1.5,
        },
    },
    # ── Food ────────────────────────────────────────────────────────────
    "beef_kg": {
        "name": "Beef (1 kg)",
        "icon": "🥩",
        "category": "Food",
        "unit_weight_kg": 1.0,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 20.0,
            "manufacturing": 5.0,
            "transport": 2.5,
            "use_phase": 1.0,
            "disposal": 1.5,
        },
        "eco_alternative": {
            "name": "Plant-Based Burger Patties (1 kg)",
            "materials": 3.0,
            "manufacturing": 1.5,
            "transport": 1.0,
            "use_phase": 0.5,
            "disposal": 0.5,
        },
    },
    "chicken_kg": {
        "name": "Chicken (1 kg)",
        "icon": "🍗",
        "category": "Food",
        "unit_weight_kg": 1.0,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 6.0,
            "manufacturing": 2.0,
            "transport": 1.5,
            "use_phase": 0.5,
            "disposal": 1.0,
        },
        "eco_alternative": {
            "name": "Lentils (1 kg)",
            "materials": 0.9,
            "manufacturing": 0.3,
            "transport": 0.5,
            "use_phase": 0.3,
            "disposal": 0.2,
        },
    },
    "rice_kg": {
        "name": "Rice (1 kg)",
        "icon": "🍚",
        "category": "Food",
        "unit_weight_kg": 1.0,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 2.5,
            "manufacturing": 1.5,
            "transport": 1.0,
            "use_phase": 1.5,
            "disposal": 0.5,
        },
        "eco_alternative": {
            "name": "Quinoa (1 kg)",
            "materials": 1.5,
            "manufacturing": 1.0,
            "transport": 0.8,
            "use_phase": 1.0,
            "disposal": 0.3,
        },
    },
    "coffee_kg": {
        "name": "Coffee Beans (1 kg)",
        "icon": "☕",
        "category": "Food",
        "unit_weight_kg": 1.0,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 5.0,
            "manufacturing": 3.0,
            "transport": 3.5,
            "use_phase": 2.0,
            "disposal": 0.8,
        },
        "eco_alternative": {
            "name": "Fair-Trade Organic Coffee (1 kg)",
            "materials": 3.5,
            "manufacturing": 2.0,
            "transport": 3.0,
            "use_phase": 1.5,
            "disposal": 0.5,
        },
    },
    # ── Electronics ─────────────────────────────────────────────────────
    "smartphone": {
        "name": "Smartphone",
        "icon": "📱",
        "category": "Electronics",
        "unit_weight_kg": 0.2,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 35.0,
            "manufacturing": 25.0,
            "transport": 5.0,
            "use_phase": 12.0,
            "disposal": 8.0,
        },
        "eco_alternative": {
            "name": "Refurbished Smartphone",
            "materials": 8.0,
            "manufacturing": 5.0,
            "transport": 3.0,
            "use_phase": 10.0,
            "disposal": 4.0,
        },
    },
    "laptop": {
        "name": "Laptop",
        "icon": "💻",
        "category": "Electronics",
        "unit_weight_kg": 2.0,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 120.0,
            "manufacturing": 80.0,
            "transport": 15.0,
            "use_phase": 60.0,
            "disposal": 30.0,
        },
        "eco_alternative": {
            "name": "Refurbished Laptop",
            "materials": 30.0,
            "manufacturing": 20.0,
            "transport": 10.0,
            "use_phase": 50.0,
            "disposal": 15.0,
        },
    },
    "led_bulb": {
        "name": "LED Light Bulb",
        "icon": "💡",
        "category": "Electronics",
        "unit_weight_kg": 0.05,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 0.3,
            "manufacturing": 0.2,
            "transport": 0.1,
            "use_phase": 0.8,
            "disposal": 0.1,
        },
        "eco_alternative": {
            "name": "Solar-Powered LED Lantern",
            "materials": 0.5,
            "manufacturing": 0.3,
            "transport": 0.15,
            "use_phase": 0.2,
            "disposal": 0.1,
        },
    },
    # ── Household ───────────────────────────────────────────────────────
    "plastic_bottle_pack": {
        "name": "Pack of 24 Plastic Water Bottles",
        "icon": "🧴",
        "category": "Household",
        "unit_weight_kg": 1.2,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 3.5,
            "manufacturing": 2.0,
            "transport": 1.5,
            "use_phase": 0.0,
            "disposal": 4.0,
        },
        "eco_alternative": {
            "name": "Reusable Stainless Steel Bottle",
            "materials": 2.0,
            "manufacturing": 1.0,
            "transport": 0.5,
            "use_phase": 0.0,
            "disposal": 0.3,
        },
    },
    "cleaning_spray": {
        "name": "Cleaning Spray (750 ml)",
        "icon": "🧹",
        "category": "Household",
        "unit_weight_kg": 0.8,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 0.8,
            "manufacturing": 0.5,
            "transport": 0.3,
            "use_phase": 0.2,
            "disposal": 0.6,
        },
        "eco_alternative": {
            "name": "Concentrate Refill Pods",
            "materials": 0.3,
            "manufacturing": 0.2,
            "transport": 0.15,
            "use_phase": 0.1,
            "disposal": 0.15,
        },
    },
    "paper_towels": {
        "name": "Paper Towels (6 rolls)",
        "icon": "🧻",
        "category": "Household",
        "unit_weight_kg": 1.0,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 1.5,
            "manufacturing": 1.0,
            "transport": 0.5,
            "use_phase": 0.0,
            "disposal": 1.2,
        },
        "eco_alternative": {
            "name": "Reusable Cloth Towels (set of 12)",
            "materials": 1.0,
            "manufacturing": 0.5,
            "transport": 0.3,
            "use_phase": 0.2,
            "disposal": 0.1,
        },
    },
    # ── Transport ───────────────────────────────────────────────────────
    "petrol_litres": {
        "name": "Petrol (1 Litre)",
        "icon": "⛽",
        "category": "Transport",
        "unit_weight_kg": 0.75,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 1.2,
            "manufacturing": 0.8,
            "transport": 0.3,
            "use_phase": 2.31,
            "disposal": 0.1,
        },
        "eco_alternative": {
            "name": "Electric Vehicle Charge (1 kWh equiv.)",
            "materials": 0.2,
            "manufacturing": 0.1,
            "transport": 0.05,
            "use_phase": 0.4,
            "disposal": 0.05,
        },
    },
    "fast_food_meal": {
        "name": "Fast Food Meal (burger, fries, drink)",
        "icon": "🍔",
        "category": "Food",
        "unit_weight_kg": 0.6,
        "typical_lifetime_uses": 1,
        "conventional": {
            "materials": 4.0,
            "manufacturing": 2.5,
            "transport": 1.5,
            "use_phase": 0.5,
            "disposal": 2.0,
        },
        "eco_alternative": {
            "name": "Homemade Plant-Based Meal",
            "materials": 1.5,
            "manufacturing": 0.5,
            "transport": 0.5,
            "use_phase": 0.3,
            "disposal": 0.4,
        },
    },
}

# ── Packaging Multipliers ────────────────────────────────────────────────────

PACKAGING_FACTORS: dict[str, dict[str, Any]] = {
    "none": {"name": "No Packaging", "multiplier": 1.0, "disposal_kg": 0.0},
    "minimal": {"name": "Minimal (Paper/Card)", "multiplier": 1.02, "disposal_kg": 0.1},
    "standard": {"name": "Standard (Plastic + Card)", "multiplier": 1.08, "disposal_kg": 0.4},
    "excessive": {"name": "Excessive (Multi-layer Plastic)", "multiplier": 1.18, "disposal_kg": 1.2},
}

# ── Shopping Cart Entry ──────────────────────────────────────────────────────


@dataclass
class CartItem:
    """A single product in the shopping cart."""
    product_key: str
    quantity: int
    packaging: str = "standard"

    @property
    def product_info(self) -> dict[str, Any]:
        return PRODUCT_CATALOGUE[self.product_key]


@dataclass
class CartItemResult:
    """Carbon result for one cart item."""
    product_key: str
    product_name: str
    icon: str
    category: str
    quantity: int
    unit_conventional_kg: float
    unit_eco_kg: float | None
    total_conventional_kg: float
    total_eco_kg: float | None
    lifecycle_breakdown: dict[str, float]
    eco_savings_kg: float | None
    eco_savings_pct: float | None
    packaging_disposal_kg: float


@dataclass
class ShoppingCartResult:
    """Complete shopping cart carbon analysis."""
    items: list[CartItemResult]
    total_conventional_kg: float
    total_eco_kg: float | None
    total_potential_savings_kg: float | None
    total_packaging_kg: float
    category_breakdown: dict[str, float]
    lifecycle_totals: dict[str, float]
    recommendations: list[dict[str, Any]]
    equivalent_trees: float
    equivalent_km_driven: float


# ── Single Product Calculation ───────────────────────────────────────────────


def calculate_product_footprint(
    product_key: str,
    quantity: int = 1,
    packaging: str = "standard",
) -> dict[str, Any]:
    """Calculate the carbon footprint for a single product type.

    Parameters
    ----------
    product_key : str
        Key from PRODUCT_CATALOGUE (e.g. ``"cotton_tshirt"``).
    quantity : int
        Number of units purchased.
    packaging : str
        One of ``"none"``, ``"minimal"``, ``"standard"``, ``"excessive"``.

    Returns
    -------
    dict with conventional & eco footprint, lifecycle breakdown, and savings.
    """
    if product_key not in PRODUCT_CATALOGUE:
        raise ValueError(
            f"Unknown product '{product_key}'. "
            f"Available: {sorted(PRODUCT_CATALOGUE)}"
        )

    product = PRODUCT_CATALOGUE[product_key]
    pkg = PACKAGING_FACTORS.get(packaging, PACKAGING_FACTORS["standard"])

    # Conventional lifecycle
    conv_stages = product["conventional"]
    conv_total_per_unit = sum(conv_stages.values())
    # Apply packaging multiplier (only to manufacturing + materials)
    pkg_factor = (pkg["multiplier"] - 1.0) / 2  # split between materials & manufacturing
    conv_total_adjusted = (
        conv_stages["materials"] * (1 + pkg_factor)
        + conv_stages["manufacturing"] * (1 + pkg_factor)
        + conv_stages["transport"]
        + conv_stages["use_phase"]
        + conv_stages["disposal"]
        + pkg["disposal_kg"]
    )

    # Eco alternative (if available)
    eco_total_per_unit = None
    eco_stages = product.get("eco_alternative")
    if eco_stages:
        eco_total_per_unit = sum(
            v for k, v in eco_stages.items() if k != "name"
        )

    savings_kg = None
    savings_pct = None
    if eco_total_per_unit is not None:
        savings_kg = conv_total_adjusted - eco_total_per_unit
        savings_pct = (
            round((savings_kg / conv_total_adjusted) * 100, 1)
            if conv_total_adjusted > 0
            else 0.0
        )

    return {
        "product_key": product_key,
        "product_name": product["name"],
        "icon": product["icon"],
        "category": product["category"],
        "quantity": quantity,
        "unit_weight_kg": product["unit_weight_kg"],
        "typical_lifetime_uses": product["typical_lifetime_uses"],
        "conventional": {
            "per_unit_kg": round(conv_total_adjusted, 3),
            "total_kg": round(conv_total_adjusted * quantity, 3),
            "lifecycle": {
                k: round(v * (1 + pkg_factor) if k in ("materials", "manufacturing") else v, 3)
                for k, v in conv_stages.items()
            },
        },
        "eco_alternative": {
            "name": eco_stages["name"] if eco_stages else None,
            "per_unit_kg": round(eco_total_per_unit, 3) if eco_total_per_unit else None,
            "total_kg": round(eco_total_per_unit * quantity, 3) if eco_total_per_unit else None,
            "lifecycle": {
                k: round(v, 3) for k, v in (eco_stages or {}).items() if k != "name"
            } if eco_stages else None,
        },
        "packaging": {
            "type": packaging,
            "factor": pkg["multiplier"],
            "disposal_kg": pkg["disposal_kg"] * quantity,
        },
        "savings": {
            "kg_per_unit": round(savings_kg, 3) if savings_kg is not None else None,
            "kg_total": round(savings_kg * quantity, 3) if savings_kg is not None else None,
            "pct": savings_pct,
        },
    }


# ── Shopping Cart Analysis ──────────────────────────────────────────────────


def calculate_shopping_cart(
    items: list[dict[str, Any]],
) -> ShoppingCartResult:
    """Analyse a full shopping cart of products.

    Parameters
    ----------
    items : list[dict]
        Each dict must have ``"product_key"`` and ``"quantity"``.
        Optional: ``"packaging"`` (defaults to ``"standard"``).

    Returns
    -------
    ShoppingCartResult
    """
    cart_item_results: list[CartItemResult] = []
    total_conv = 0.0
    total_eco = 0.0
    total_packaging = 0.0
    category_breakdown: dict[str, float] = {}
    lifecycle_totals: dict[str, float] = {stage: 0.0 for stage in LIFECYCLE_STAGES}

    for item in items:
        product_key = item["product_key"]
        quantity = max(1, int(item.get("quantity", 1)))
        packaging = item.get("packaging", "standard")

        result = calculate_product_footprint(product_key, quantity, packaging)

        conv_total = result["conventional"]["total_kg"]
        eco_total = result["eco_alternative"]["total_kg"]
        pkg_disposal = result["packaging"]["disposal_kg"]

        lifecycle_breakdown = result["conventional"]["lifecycle"]
        for stage in LIFECYCLE_STAGES:
            lifecycle_totals[stage] += lifecycle_breakdown.get(stage, 0.0)

        cat = result["category"]
        category_breakdown[cat] = category_breakdown.get(cat, 0.0) + conv_total

        total_conv += conv_total
        if eco_total is not None:
            total_eco += eco_total
        total_packaging += pkg_disposal

        eco_savings = result["savings"]["kg_total"]
        eco_savings_pct = result["savings"]["pct"]

        cart_item_results.append(
            CartItemResult(
                product_key=product_key,
                product_name=result["product_name"],
                icon=result["icon"],
                category=cat,
                quantity=quantity,
                unit_conventional_kg=result["conventional"]["per_unit_kg"],
                unit_eco_kg=result["eco_alternative"]["per_unit_kg"],
                total_conventional_kg=conv_total,
                total_eco_kg=eco_total,
                lifecycle_breakdown=lifecycle_breakdown,
                eco_savings_kg=eco_savings,
                eco_savings_pct=eco_savings_pct,
                packaging_disposal_kg=pkg_disposal,
            )
        )

    total_savings = None
    total_eco_val = None
    if total_eco > 0:
        total_eco_val = round(total_eco, 2)
        total_savings = round(total_conv - total_eco, 2)

    # Equivalents
    kg_per_km_driven = 0.21
    kg_per_tree_year = 21.0
    equivalent_km = round(total_conv / kg_per_km_driven, 0) if total_conv > 0 else 0
    equivalent_trees = round(total_conv / kg_per_tree_year, 1) if total_conv > 0 else 0

    recommendations = _generate_cart_recommendations(cart_item_results)

    return ShoppingCartResult(
        items=cart_item_results,
        total_conventional_kg=round(total_conv, 2),
        total_eco_kg=total_eco_val,
        total_potential_savings_kg=total_savings,
        total_packaging_kg=round(total_packaging, 2),
        category_breakdown={k: round(v, 2) for k, v in category_breakdown.items()},
        lifecycle_totals={k: round(v, 2) for k, v in lifecycle_totals.items()},
        recommendations=recommendations,
        equivalent_trees=equivalent_trees,
        equivalent_km_driven=equivalent_km,
    )


def _generate_cart_recommendations(
    items: list[CartItemResult],
) -> list[dict[str, Any]]:
    """Generate prioritised shopping recommendations."""
    recs: list[dict[str, Any]] = []

    # Sort by savings potential descending
    savable = [i for i in items if i.eco_savings_kg is not None and i.eco_savings_kg > 0]
    savable.sort(key=lambda x: x.eco_savings_kg or 0, reverse=True)

    for item in savable[:5]:
        if (item.eco_savings_pct or 0) >= 40:
            impact = "high"
        elif (item.eco_savings_pct or 0) >= 20:
            impact = "medium"
        else:
            impact = "low"

        eco_name = calculate_product_footprint(item.product_key)["eco_alternative"]["name"]

        recs.append({
            "product": item.product_name,
            "icon": item.icon,
            "action": f"Switch from {item.product_name} to {eco_name}",
            "savings_kg": item.eco_savings_kg,
            "savings_pct": item.eco_savings_pct,
            "impact": impact,
        })

    # Packaging recommendations
    high_pkg_items = [i for i in items if i.packaging_disposal_kg > 0.5]
    if high_pkg_items:
        recs.append({
            "product": "Packaging",
            "icon": "📦",
            "action": f"Reduce packaging waste for {len(high_pkg_items)} item(s) — choose minimal or no-packaging options",
            "savings_kg": round(sum(i.packaging_disposal_kg for i in high_pkg_items) * 0.3, 2),
            "savings_pct": None,
            "impact": "medium",
        })

    recs.sort(key=lambda r: r["savings_kg"], reverse=True)
    return recs


# ── Product Catalogue Helpers ────────────────────────────────────────────────


def list_products(category: str | None = None) -> list[dict[str, Any]]:
    """List all products, optionally filtered by category."""
    products = []
    for key, info in PRODUCT_CATALOGUE.items():
        if category and info["category"] != category:
            continue
        conv_total = sum(v for k, v in info["conventional"].items())
        eco_total = None
        if info.get("eco_alternative"):
            eco_total = sum(v for k, v in info["eco_alternative"].items() if k != "name")
        products.append({
            "key": key,
            "name": info["name"],
            "icon": info["icon"],
            "category": info["category"],
            "unit_weight_kg": info["unit_weight_kg"],
            "conventional_kg": round(conv_total, 2),
            "eco_kg": round(eco_total, 2) if eco_total else None,
            "savings_pct": (
                round(((conv_total - eco_total) / conv_total) * 100, 1)
                if eco_total and conv_total > 0
                else None
            ),
        })
    return products


def list_categories() -> list[str]:
    """Return all unique product categories."""
    return sorted(set(p["category"] for p in PRODUCT_CATALOGUE.values()))


# ── Database: Shopping History ───────────────────────────────────────────────


def init_shopping_db() -> bool:
    """Create the shopping footprint tracking table if needed."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shopping_cart_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total_conventional_kg REAL NOT NULL,
                total_eco_kg REAL,
                total_savings_kg REAL,
                total_packaging_kg REAL NOT NULL,
                items_json TEXT NOT NULL,
                category_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Shopping DB init error: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def save_shopping_cart(user_id: int, cart_result: ShoppingCartResult) -> int | None:
    """Persist a shopping cart analysis. Returns the new row id."""
    init_shopping_db()
    conn = None
    try:
        items_summary = [
            {
                "product_key": item.product_key,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "conventional_kg": item.total_conventional_kg,
                "eco_kg": item.total_eco_kg,
            }
            for item in cart_result.items
        ]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.execute(
            """
            INSERT INTO shopping_cart_assessments
                (user_id, total_conventional_kg, total_eco_kg, total_savings_kg,
                 total_packaging_kg, items_json, category_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                cart_result.total_conventional_kg,
                cart_result.total_eco_kg,
                cart_result.total_potential_savings_kg,
                cart_result.total_packaging_kg,
                json.dumps(items_summary),
                json.dumps(cart_result.category_breakdown),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as exc:
        logger.error("Unable to save shopping cart: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def get_shopping_history(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """Return a user's saved shopping cart assessments, newest first."""
    init_shopping_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, user_id, total_conventional_kg, total_eco_kg,
                   total_savings_kg, total_packaging_kg, items_json,
                   category_json, created_at
            FROM shopping_cart_assessments
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        results = []
        for row in rows:
            record = dict(row)
            record["items"] = _safe_json(record.pop("items_json"))
            record["categories"] = _safe_json(record.pop("category_json"))
            results.append(record)
        return results
    except sqlite3.Error as exc:
        logger.error("Unable to load shopping history: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def _safe_json(raw: Any) -> Any:
    try:
        return json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}
