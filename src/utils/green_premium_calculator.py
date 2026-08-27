"""
Green Premium Calculator.
Computes the initial cost delta between conventional and sustainable product choices.
"""

from typing import Dict, Any, List

# Curated dataset of conventional vs. sustainable product costs and baseline savings
# Costs are in USD. Savings are annual in USD and kg CO2e.
PRODUCT_DATASET = {
    "vehicle_ev": {
        "name": "Electric Vehicle (vs. ICE)",
        "conventional_cost": 35000,
        "sustainable_cost": 42000,
        "annual_cost_savings": 1200,  # Fuel + maintenance
        "annual_carbon_savings_kg": 4000,
        "lifespan_years": 10,
    },
    "home_heat_pump": {
        "name": "Air Source Heat Pump (vs. Gas Boiler)",
        "conventional_cost": 5000,
        "sustainable_cost": 8500,
        "annual_cost_savings": 400,  # Highly dependent on utility rates
        "annual_carbon_savings_kg": 1500,
        "lifespan_years": 15,
    },
    "solar_panels": {
        "name": "Residential Solar Panels (5kW)",
        "conventional_cost": 0,  # Baseline is grid power
        "sustainable_cost": 15000,
        "annual_cost_savings": 1800,
        "annual_carbon_savings_kg": 3500,
        "lifespan_years": 25,
    },
    "led_retrofit": {
        "name": "Whole-Home LED Retrofit",
        "conventional_cost": 100,
        "sustainable_cost": 300,
        "annual_cost_savings": 150,
        "annual_carbon_savings_kg": 200,
        "lifespan_years": 5,
    },
    "energy_star_appliance": {
        "name": "Energy Star Refrigerator (vs. Standard)",
        "conventional_cost": 800,
        "sustainable_cost": 1100,
        "annual_cost_savings": 60,
        "annual_carbon_savings_kg": 150,
        "lifespan_years": 12,
    },
}


class GreenPremiumCalculator:
    """Calculates the upfront 'green premium' for sustainable substitutions."""

    def __init__(self):
        self.dataset = PRODUCT_DATASET

    def get_available_products(self) -> List[str]:
        """Returns a list of available product category keys."""
        return list(self.dataset.keys())

    def get_product_display_name(self, product_key: str) -> str:
        """Returns the human-readable name of the product."""
        return self.dataset.get(product_key, {}).get("name", product_key)

    def calculate_premium(self, product_key: str) -> Dict[str, Any]:
        """Calculates the green premium and baseline metrics for a product."""
        if product_key not in self.dataset:
            raise ValueError(f"Unknown product: {product_key}")

        data = self.dataset[product_key]
        premium = data["sustainable_cost"] - data["conventional_cost"]

        return {
            "product_name": data["name"],
            "conventional_cost_usd": data["conventional_cost"],
            "sustainable_cost_usd": data["sustainable_cost"],
            "green_premium_usd": premium,
            "baseline_annual_cost_savings_usd": data["annual_cost_savings"],
            "baseline_annual_carbon_savings_kg": data["annual_carbon_savings_kg"],
            "lifespan_years": data["lifespan_years"],
        }
