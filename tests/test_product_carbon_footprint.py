"""Tests for product_carbon_footprint module."""

from __future__ import annotations

import json
import math
import pytest

from src.carbon.product_carbon_footprint import (
    LIFECYCLE_STAGES,
    PRODUCT_CATALOGUE,
    PACKAGING_FACTORS,
    CartItem,
    CartItemResult,
    ShoppingCartResult,
    calculate_product_footprint,
    calculate_shopping_cart,
    list_products,
    list_categories,
)


# ── Product Catalogue ────────────────────────────────────────────────────────


class TestProductCatalogue:
    def test_all_products_have_required_keys(self):
        for key, info in PRODUCT_CATALOGUE.items():
            assert "name" in info, f"{key} missing 'name'"
            assert "icon" in info, f"{key} missing 'icon'"
            assert "category" in info, f"{key} missing 'category'"
            assert "unit_weight_kg" in info, f"{key} missing 'unit_weight_kg'"
            assert "conventional" in info, f"{key} missing 'conventional'"

    def test_conventional_has_all_stages(self):
        for key, info in PRODUCT_CATALOGUE.items():
            for stage in LIFECYCLE_STAGES:
                assert stage in info["conventional"], (
                    f"{key} conventional missing stage '{stage}'"
                )

    def test_eco_alternative_has_all_stages(self):
        for key, info in PRODUCT_CATALOGUE.items():
            eco = info.get("eco_alternative")
            if eco is not None:
                for stage in LIFECYCLE_STAGES:
                    assert stage in eco, f"{key} eco_alternative missing stage '{stage}'"

    def test_eco_alternative_has_name(self):
        for key, info in PRODUCT_CATALOGUE.items():
            eco = info.get("eco_alternative")
            if eco is not None:
                assert "name" in eco, f"{key} eco_alternative missing 'name'"

    def test_categories_are_strings(self):
        for key, info in PRODUCT_CATALOGUE.items():
            assert isinstance(info["category"], str)
            assert len(info["category"]) > 0

    def test_unit_weight_positive(self):
        for key, info in PRODUCT_CATALOGUE.items():
            assert info["unit_weight_kg"] > 0, f"{key} has non-positive weight"

    def test_conventional_totals_positive(self):
        for key, info in PRODUCT_CATALOGUE.items():
            total = sum(info["conventional"].values())
            assert total > 0, f"{key} conventional total is zero"


# ── Packaging Factors ───────────────────────────────────────────────────────


class TestPackagingFactors:
    def test_all_packaging_types(self):
        expected = {"none", "minimal", "standard", "excessive"}
        assert set(PACKAGING_FACTORS.keys()) == expected

    def test_multipliers_monotonic(self):
        prev = 0
        for pf in PACKAGING_FACTORS.values():
            assert pf["multiplier"] >= prev
            prev = pf["multiplier"]

    def test_disposal_increases_with_excess(self):
        none_d = PACKAGING_FACTORS["none"]["disposal_kg"]
        exc_d = PACKAGING_FACTORS["excessive"]["disposal_kg"]
        assert exc_d > none_d


# ── Single Product Calculation ───────────────────────────────────────────────


class TestCalculateProductFootprint:
    def test_returns_dict_with_required_keys(self):
        result = calculate_product_footprint("cotton_tshirt", 2, "standard")
        assert "product_key" in result
        assert "product_name" in result
        assert "conventional" in result
        assert "eco_alternative" in result
        assert "savings" in result
        assert "packaging" in result

    def test_conventional_total_positive(self):
        result = calculate_product_footprint("beef_kg", 1, "none")
        assert result["conventional"]["total_kg"] > 0

    def test_conventional_quantity_scaling(self):
        r1 = calculate_product_footprint("cotton_tshirt", 1, "none")
        r3 = calculate_product_footprint("cotton_tshirt", 3, "none")
        assert abs(r3["conventional"]["total_kg"] - r1["conventional"]["total_kg"] * 3) < 0.1

    def test_eco_alternative_has_lower_footprint(self):
        result = calculate_product_footprint("beef_kg", 1, "standard")
        assert result["eco_alternative"]["total_kg"] < result["conventional"]["total_kg"]

    def test_savings_kg_positive(self):
        result = calculate_product_footprint("smartphone", 1, "standard")
        assert result["savings"]["kg_total"] > 0

    def test_savings_pct_range(self):
        result = calculate_product_footprint("laptop", 1, "standard")
        pct = result["savings"]["pct"]
        assert 0 < pct < 100

    def test_packaging_disposal_none(self):
        result = calculate_product_footprint("cotton_tshirt", 5, "none")
        assert result["packaging"]["disposal_kg"] == 0.0

    def test_packaging_disposal_excessive(self):
        result = calculate_product_footprint("cotton_tshirt", 1, "excessive")
        assert result["packaging"]["disposal_kg"] > 0

    def test_packaging_multiplies_conventional(self):
        r_none = calculate_product_footprint("cotton_tshirt", 1, "none")
        r_excess = calculate_product_footprint("cotton_tshirt", 1, "excessive")
        assert r_excess["conventional"]["total_kg"] > r_none["conventional"]["total_kg"]

    def test_lifecycle_stages_populated(self):
        result = calculate_product_footprint("running_shoes", 1, "standard")
        for stage in LIFECYCLE_STAGES:
            assert stage in result["conventional"]["lifecycle"]

    def test_unknown_product_raises(self):
        with pytest.raises(ValueError, match="Unknown product"):
            calculate_product_footprint("unicorn_dust", 1)

    def test_zero_quantity_handled(self):
        result = calculate_product_footprint("cotton_tshirt", 0, "standard")
        # Should still work with 0 quantity
        assert result["quantity"] == 0
        assert result["conventional"]["total_kg"] == 0.0

    def test_eco_total_matches_lifecycle_sum(self):
        result = calculate_product_footprint("beef_kg", 1, "none")
        eco_lifecycle_sum = sum(
            v for k, v in result["eco_alternative"]["lifecycle"].items()
        )
        assert abs(eco_lifecycle_sum - result["eco_alternative"]["total_kg"]) < 0.1

    def test_category_populated(self):
        result = calculate_product_footprint("denim_jeans", 1, "standard")
        assert result["category"] == "Clothing"

    def test_products_without_eco_alternative(self):
        """Some products might not have eco alternatives — should still work."""
        for key, info in PRODUCT_CATALOGUE.items():
            result = calculate_product_footprint(key, 1, "standard")
            if info.get("eco_alternative") is None:
                assert result["eco_alternative"]["total_kg"] is None
                assert result["savings"]["kg_total"] is None


# ── Shopping Cart Calculation ───────────────────────────────────────────────


class TestCalculateShoppingCart:
    def test_empty_cart(self):
        result = calculate_shopping_cart([])
        assert isinstance(result, ShoppingCartResult)
        assert result.total_conventional_kg == 0
        assert len(result.items) == 0

    def test_single_item(self):
        items = [{"product_key": "cotton_tshirt", "quantity": 2}]
        result = calculate_shopping_cart(items)
        assert len(result.items) == 1
        assert result.items[0].quantity == 2
        assert result.total_conventional_kg > 0

    def test_multiple_items(self):
        items = [
            {"product_key": "cotton_tshirt", "quantity": 2},
            {"product_key": "beef_kg", "quantity": 1},
            {"product_key": "smartphone", "quantity": 1},
        ]
        result = calculate_shopping_cart(items)
        assert len(result.items) == 3
        assert result.total_conventional_kg > 0

    def test_total_is_sum_of_items(self):
        items = [
            {"product_key": "cotton_tshirt", "quantity": 1},
            {"product_key": "chicken_kg", "quantity": 3},
        ]
        result = calculate_shopping_cart(items)
        item_sum = sum(i.total_conventional_kg for i in result.items)
        assert abs(result.total_conventional_kg - item_sum) < 0.1

    def test_category_breakdown_populated(self):
        items = [
            {"product_key": "cotton_tshirt", "quantity": 1},
            {"product_key": "beef_kg", "quantity": 1},
        ]
        result = calculate_shopping_cart(items)
        assert "Clothing" in result.category_breakdown
        assert "Food" in result.category_breakdown

    def test_lifecycle_totals_populated(self):
        items = [{"product_key": "running_shoes", "quantity": 1}]
        result = calculate_shopping_cart(items)
        for stage in LIFECYCLE_STAGES:
            assert stage in result.lifecycle_totals
            assert result.lifecycle_totals[stage] >= 0

    def test_total_eco_kg(self):
        items = [
            {"product_key": "beef_kg", "quantity": 2},
            {"product_key": "cotton_tshirt", "quantity": 3},
        ]
        result = calculate_shopping_cart(items)
        assert result.total_eco_kg is not None
        assert result.total_eco_kg < result.total_conventional_kg

    def test_total_potential_savings(self):
        items = [{"product_key": "laptop", "quantity": 1}]
        result = calculate_shopping_cart(items)
        assert result.total_potential_savings_kg is not None
        assert result.total_potential_savings_kg > 0

    def test_equivalents(self):
        items = [{"product_key": "smartphone", "quantity": 1}]
        result = calculate_shopping_cart(items)
        assert result.equivalent_km_driven > 0
        assert result.equivalent_trees > 0

    def test_packaging_totals(self):
        items = [
            {"product_key": "plastic_bottle_pack", "quantity": 1, "packaging": "excessive"},
        ]
        result = calculate_shopping_cart(items)
        assert result.total_packaging_kg > 0

    def test_recommendations_generated(self):
        items = [
            {"product_key": "beef_kg", "quantity": 3},
            {"product_key": "cotton_tshirt", "quantity": 5},
            {"product_key": "smartphone", "quantity": 1},
        ]
        result = calculate_shopping_cart(items)
        assert len(result.recommendations) > 0

    def test_recommendations_have_required_keys(self):
        items = [{"product_key": "beef_kg", "quantity": 2}]
        result = calculate_shopping_cart(items)
        for rec in result.recommendations:
            assert "product" in rec
            assert "action" in rec
            assert "savings_kg" in rec
            assert "impact" in rec

    def test_recommendations_sorted_by_savings(self):
        items = [
            {"product_key": "laptop", "quantity": 1},
            {"product_key": "cotton_tshirt", "quantity": 1},
            {"product_key": "beef_kg", "quantity": 5},
        ]
        result = calculate_shopping_cart(items)
        savings = [r["savings_kg"] for r in result.recommendations]
        assert savings == sorted(savings, reverse=True)

    def test_default_packaging_is_standard(self):
        items = [{"product_key": "cotton_tshirt", "quantity": 1}]
        result = calculate_shopping_cart(items)
        # Packaging should be applied (standard)
        assert result.total_packaging_kg == 0.4  # 1 * 0.4

    def test_packaging_key_in_item(self):
        items = [{"product_key": "cotton_tshirt", "quantity": 1, "packaging": "minimal"}]
        result = calculate_shopping_cart(items)
        assert result.total_packaging_kg == 0.1


# ── CartItemResult ───────────────────────────────────────────────────────────


class TestCartItemResult:
    def test_lifecycle_breakdown_stages(self):
        items = [{"product_key": "beef_kg", "quantity": 1}]
        result = calculate_shopping_cart(items)
        for stage in LIFECYCLE_STAGES:
            assert stage in result.items[0].lifecycle_breakdown

    def test_eco_savings_matches(self):
        items = [{"product_key": "smartphone", "quantity": 1}]
        result = calculate_shopping_cart(items)
        item = result.items[0]
        if item.eco_savings_kg is not None:
            assert item.eco_savings_kg == item.total_conventional_kg - item.total_eco_kg


# ── List Helpers ─────────────────────────────────────────────────────────────


class TestListHelpers:
    def test_list_products_all(self):
        products = list_products()
        assert len(products) == len(PRODUCT_CATALOGUE)

    def test_list_products_by_category(self):
        clothing = list_products(category="Clothing")
        for p in clothing:
            assert p["category"] == "Clothing"
        assert len(clothing) > 0

    def test_list_products_empty_category(self):
        products = list_products(category="NonExistent")
        assert len(products) == 0

    def test_product_dict_has_required_keys(self):
        products = list_products()
        for p in products:
            assert "key" in p
            assert "name" in p
            assert "icon" in p
            assert "category" in p
            assert "conventional_kg" in p

    def test_list_categories(self):
        categories = list_categories()
        assert len(categories) > 0
        assert "Clothing" in categories
        assert "Food" in categories
        assert "Electronics" in categories
        assert "Household" in categories

    def test_categories_sorted(self):
        categories = list_categories()
        assert categories == sorted(categories)


# ── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_large_quantity(self):
        result = calculate_product_footprint("cotton_tshirt", 1000, "none")
        assert result["conventional"]["total_kg"] > 100

    def test_all_products_calculable(self):
        """Every product in the catalogue should produce a valid result."""
        for key in PRODUCT_CATALOGUE:
            result = calculate_product_footprint(key, 1, "standard")
            assert result["conventional"]["total_kg"] > 0

    def test_cart_with_mixed_packaging(self):
        items = [
            {"product_key": "cotton_tshirt", "quantity": 2, "packaging": "none"},
            {"product_key": "beef_kg", "quantity": 1, "packaging": "excessive"},
        ]
        result = calculate_shopping_cart(items)
        assert result.total_packaging_kg > 0

    def test_eco_alternative_per_unit_matches_total(self):
        items = [{"product_key": "denim_jeans", "quantity": 3}]
        result = calculate_shopping_cart(items)
        item = result.items[0]
        if item.unit_eco_kg is not None:
            expected = round(item.unit_eco_kg * item.quantity, 2)
            assert abs(item.total_eco_kg - expected) < 0.2

    def test_category_breakdown_sums_to_total(self):
        items = [
            {"product_key": "cotton_tshirt", "quantity": 1},
            {"product_key": "beef_kg", "quantity": 1},
            {"product_key": "smartphone", "quantity": 1},
            {"product_key": "plastic_bottle_pack", "quantity": 1},
        ]
        result = calculate_shopping_cart(items)
        cat_sum = sum(result.category_breakdown.values())
        assert abs(cat_sum - result.total_conventional_kg) < 1.0
