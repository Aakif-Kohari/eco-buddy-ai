"""
Carbon Tax Simulator.
Applies different mock carbon tax rates to a user's logged historical carbon footprint across different scopes.
"""

from typing import Dict, Any


class CarbonTaxSimulator:
    """Simulates the financial impact of various carbon pricing policies on a household."""

    def __init__(
        self, annual_household_footprint_tonnes: float, tax_rate_per_tonne_usd: float
    ):
        """
        Initializes the simulator.

        Args:
            annual_household_footprint_tonnes: Total annual carbon footprint in metric tonnes.
            tax_rate_per_tonne_usd: The proposed carbon tax rate in USD per tonne.
        """
        self.footprint_tonnes = max(0.0, annual_household_footprint_tonnes)
        self.tax_rate = max(0.0, tax_rate_per_tonne_usd)

    def calculate_tax_liability(self) -> Dict[str, Any]:
        """Calculates the total annual tax liability based on the footprint and tax rate."""
        total_liability = self.footprint_tonnes * self.tax_rate

        # Mock breakdown by scope (assuming typical household distribution)
        # Scope 1: Direct (heating, personal vehicles) ~30%
        # Scope 2: Indirect (electricity) ~20%
        # Scope 3: Other (goods, services, food) ~50%
        scope1_liability = total_liability * 0.30
        scope2_liability = total_liability * 0.20
        scope3_liability = total_liability * 0.50

        return {
            "footprint_tonnes": self.footprint_tonnes,
            "tax_rate_per_tonne": self.tax_rate,
            "total_annual_liability_usd": round(total_liability, 2),
            "breakdown": {
                "scope1_direct_usd": round(scope1_liability, 2),
                "scope2_electricity_usd": round(scope2_liability, 2),
                "scope3_consumption_usd": round(scope3_liability, 2),
            },
        }

    def get_policy_education_snippet(self) -> str:
        """Returns a brief, non-partisan explanation of carbon pricing."""
        return (
            "**How Carbon Pricing Works:** A carbon tax puts a direct price on greenhouse gas emissions. "
            "This creates a financial incentive for businesses and individuals to reduce their carbon footprint. "
            "The revenue generated is often returned to households as a 'dividend' or 'rebate' to offset "
            "increased costs, ensuring the policy remains progressive and protects lower-income families."
        )
