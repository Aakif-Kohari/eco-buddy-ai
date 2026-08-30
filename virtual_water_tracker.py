"""
Virtual Water Tracker.
Calculates the embedded virtual water (blue, green, and grey water) of user-purchased goods based on weight, type, and country of origin.
"""

from typing import Dict, Any, List
from consumer_goods_water_db import ConsumerGoodsWaterDB


class VirtualWaterTracker:
    """Calculates and analyzes the virtual water footprint of consumer purchases."""

    def __init__(self):
        self.db = ConsumerGoodsWaterDB()
        self.logged_purchases: List[Dict[str, Any]] = []

    def log_purchase(
        self, product_name: str, quantity: float, region: str
    ) -> Dict[str, Any]:
        """
        Logs a purchase and calculates its virtual water footprint.

        Args:
            product_name: The name of the product (e.g., 'beef', 'cotton_clothing').
            quantity: The amount purchased (in kg or units, matching the product definition).
            region: The region of origin (e.g., 'south_asia', 'north_america').

        Returns:
            A dictionary containing the calculated water footprint details.
        """
        factors = self.db.get_product_factors(product_name)
        if not factors:
            raise ValueError(f"Unknown product: {product_name}")

        stress_index = self.db.get_regional_stress(region)

        # Calculate base water footprint
        blue_water = factors["blue"] * quantity
        green_water = factors["green"] * quantity
        grey_water = factors["grey"] * quantity
        total_water = blue_water + green_water + grey_water

        # Apply water stress weighting to blue and grey water (green water is rain, less stressful)
        # This creates a "Water Scarcity Footprint" metric
        scarcity_weighted_blue = blue_water * (1 + stress_index)
        scarcity_weighted_grey = grey_water * (1 + stress_index)
        scarcity_weighted_total = (
            scarcity_weighted_blue + green_water + scarcity_weighted_grey
        )

        purchase_record = {
            "product": product_name,
            "quantity": quantity,
            "unit": factors["unit"],
            "region": region,
            "water_stress_index": stress_index,
            "blue_water_l": round(blue_water, 2),
            "green_water_l": round(green_water, 2),
            "grey_water_l": round(grey_water, 2),
            "total_water_l": round(total_water, 2),
            "scarcity_weighted_total_l": round(scarcity_weighted_total, 2),
        }

        self.logged_purchases.append(purchase_record)
        return purchase_record

    def get_aggregated_footprint(self) -> Dict[str, Any]:
        """Aggregates the total virtual water footprint of all logged purchases."""
        if not self.logged_purchases:
            return self._empty_aggregation()

        total_blue = sum(p["blue_water_l"] for p in self.logged_purchases)
        total_green = sum(p["green_water_l"] for p in self.logged_purchases)
        total_grey = sum(p["grey_water_l"] for p in self.logged_purchases)
        total_scarcity = sum(
            p["scarcity_weighted_total_l"] for p in self.logged_purchases
        )

        # Group by region to show global trade impact
        regional_impact = {}
        for p in self.logged_purchases:
            reg = p["region"]
            if reg not in regional_impact:
                regional_impact[reg] = {"scarcity_weighted_l": 0.0, "items": 0}
            regional_impact[reg]["scarcity_weighted_l"] += p[
                "scarcity_weighted_total_l"
            ]
            regional_impact[reg]["items"] += 1

        for reg in regional_impact:
            regional_impact[reg]["scarcity_weighted_l"] = round(
                regional_impact[reg]["scarcity_weighted_l"], 2
            )

        return {
            "total_purchases": len(self.logged_purchases),
            "total_blue_water_l": round(total_blue, 2),
            "total_green_water_l": round(total_green, 2),
            "total_grey_water_l": round(total_grey, 2),
            "total_raw_water_l": round(total_blue + total_green + total_grey, 2),
            "total_scarcity_weighted_l": round(total_scarcity, 2),
            "regional_impact": regional_impact,
        }

    def _empty_aggregation(self) -> Dict[str, Any]:
        """Returns an empty aggregation structure."""
        return {
            "total_purchases": 0,
            "total_blue_water_l": 0.0,
            "total_green_water_l": 0.0,
            "total_grey_water_l": 0.0,
            "total_raw_water_l": 0.0,
            "total_scarcity_weighted_l": 0.0,
            "regional_impact": {},
        }

    def get_high_impact_items(self) -> List[Dict[str, Any]]:
        """Identifies purchases with the highest scarcity-weighted water footprint."""
        if not self.logged_purchases:
            return []

        # Sort by scarcity weighted total descending
        sorted_purchases = sorted(
            self.logged_purchases,
            key=lambda x: x["scarcity_weighted_total_l"],
            reverse=True,
        )
        return sorted_purchases[:5]  # Return top 5

    def suggest_alternatives(self, product_name: str) -> List[str]:
        """Suggests lower-water-footprint alternatives for a given product."""
        suggestions = {
            "beef": [
                "Consider replacing one beef meal per week with chicken or plant-based proteins (e.g., lentils, tofu), which use up to 90% less blue water.",
                "Look for locally sourced meat to reduce the grey water footprint associated with long-distance transport.",
            ],
            "cotton_clothing": [
                "Opt for clothing made from organic cotton, hemp, or recycled materials, which significantly reduce blue water usage.",
                "Buy second-hand clothing to avoid the initial manufacturing water footprint entirely.",
            ],
            "almonds": [
                "Consider substituting almonds with oats or soy for milk alternatives, as they generally require less blue water in non-drought regions.",
                "If buying almonds, look for those sourced from regions with lower water stress indices.",
            ],
            "coffee": [
                "Try reducing daily coffee consumption or switching to tea, which typically has a lower blue water footprint.",
                "Look for shade-grown or rainwater-fed coffee certifications.",
            ],
            "rice": [
                "Consider alternating rice with wheat, barley, or quinoa, which often have lower blue water requirements depending on the region.",
                "Look for sustainably irrigated rice certifications.",
            ],
        }
        return suggestions.get(
            product_name.lower(),
            [
                "Look for locally sourced, seasonal, or certified sustainable versions of this product to minimize blue and grey water footprints."
            ],
        )
