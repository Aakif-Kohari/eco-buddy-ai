"""
Consumer Goods Water Database.
Manages a comprehensive dataset of common products with their specific water footprint factors and regional water stress indices.
"""

from typing import Dict, Any, Optional

# Virtual water footprint factors (liters per kg or per unit)
# Blue: surface/groundwater, Green: rainwater, Grey: water to dilute pollutants
PRODUCT_WATER_FOOTPRINTS = {
    "beef": {"blue": 15000, "green": 500, "grey": 2000, "unit": "kg"},
    "chicken": {"blue": 4300, "green": 200, "grey": 500, "unit": "kg"},
    "rice": {"blue": 2500, "green": 1500, "grey": 300, "unit": "kg"},
    "wheat": {"blue": 500, "green": 1200, "grey": 100, "unit": "kg"},
    "cotton_clothing": {"blue": 4000, "green": 1000, "grey": 500, "unit": "item"},
    "smartphone": {"blue": 12000, "green": 0, "grey": 3000, "unit": "item"},
    "coffee": {"blue": 18000, "green": 2000, "grey": 500, "unit": "kg"},
    "almonds": {"blue": 16000, "green": 500, "grey": 200, "unit": "kg"},
    "tomatoes": {"blue": 200, "green": 50, "grey": 30, "unit": "kg"},
    "paper": {"blue": 1000, "green": 0, "grey": 200, "unit": "kg"},
}

# Regional water stress indices (0.0 = low stress, 1.0 = extreme stress)
REGIONAL_WATER_STRESS = {
    "north_america": 0.35,
    "europe": 0.30,
    "south_america": 0.25,
    "sub_saharan_africa": 0.65,
    "middle_east_north_africa": 0.85,
    "south_asia": 0.75,
    "east_asia": 0.55,
    "oceania": 0.40,
}


class ConsumerGoodsWaterDB:
    """Provides access to virtual water footprint data and regional stress metrics."""

    def __init__(self):
        self.products = PRODUCT_WATER_FOOTPRINTS
        self.regions = REGIONAL_WATER_STRESS

    def get_product_factors(self, product_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves water footprint factors for a specific product."""
        return self.products.get(product_name.lower())

    def get_all_products(self) -> list:
        """Returns a list of all tracked product names."""
        return list(self.products.keys())

    def get_regional_stress(self, region: str) -> float:
        """Retrieves the water stress index for a specific region."""
        return self.regions.get(region.lower(), 0.5)  # Default to 0.5 if unknown

    def get_all_regions(self) -> list:
        """Returns a list of all tracked regions."""
        return list(self.regions.keys())

    def get_stress_category(self, stress_index: float) -> str:
        """Categorizes the water stress level based on the index."""
        if stress_index < 0.3:
            return "Low Stress"
        elif stress_index < 0.6:
            return "Medium Stress"
        elif stress_index < 0.8:
            return "High Stress"
        else:
            return "Extreme Stress"
