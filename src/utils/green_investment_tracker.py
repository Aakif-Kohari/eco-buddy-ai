"""
Green Investment Tracker.
Estimates the financed emissions of user investment portfolios based on asset class allocations (PCAF methodology).
"""

from typing import Dict, List, Any


class GreenInvestmentTracker:
    """Calculates the implied carbon footprint of financial portfolios."""

    # Simplified PCAF-style financed emission factors (tonnes CO2e per $1M invested)
    # Source: Approximate global averages for illustrative purposes
    EMISSION_INTENSITIES = {
        "equities_developed": 150.0,
        "equities_emerging": 250.0,
        "corporate_bonds": 120.0,
        "government_bonds": 50.0,
        "real_estate": 200.0,
        "esg_funds": 80.0,
        "cash": 0.0,
    }

    def __init__(self, total_portfolio_value_usd: float):
        self.total_value = total_portfolio_value_usd
        self.allocations: Dict[str, float] = {}  # Percentage (0-100)

    def set_allocation(self, asset_class: str, percentage: float) -> None:
        """Sets the percentage allocation for a specific asset class."""
        if asset_class not in self.EMISSION_INTENSITIES:
            raise ValueError(f"Unknown asset class: {asset_class}")
        if percentage < 0 or percentage > 100:
            raise ValueError("Percentage must be between 0 and 100.")

        self.allocations[asset_class] = percentage

    def validate_allocations(self) -> bool:
        """Checks if allocations sum to 100%."""
        total = sum(self.allocations.values())
        return abs(total - 100.0) < 0.1  # Allow small floating point errors

    def calculate_financed_emissions(self) -> Dict[str, Any]:
        """Calculates the total financed emissions of the portfolio."""
        if not self.validate_allocations():
            raise ValueError("Asset allocations must sum to 100%")

        total_emissions_tonnes = 0.0
        breakdown = {}

        for asset_class, pct in self.allocations.items():
            value_millions = (self.total_value * (pct / 100.0)) / 1_000_000
            intensity = self.EMISSION_INTENSITIES[asset_class]

            emissions = value_millions * intensity
            total_emissions_tonnes += emissions

            breakdown[asset_class] = {
                "allocation_pct": pct,
                "value_usd": round(value_millions * 1_000_000, 2),
                "emissions_tonnes": round(emissions, 2),
            }

        return {
            "total_portfolio_value_usd": self.total_value,
            "total_financed_emissions_tonnes": round(total_emissions_tonnes, 2),
            "emissions_per_dollar_invested": round(
                (total_emissions_tonnes * 1000) / self.total_value, 4
            )
            if self.total_value > 0
            else 0.0,
            "breakdown": breakdown,
        }

    def suggest_greener_alternatives(self) -> List[Dict[str, Any]]:
        """Suggests shifts from high-emission to low-emission asset classes."""
        suggestions = []
        high_emission_classes = [
            k
            for k, v in self.allocations.items()
            if self.EMISSION_INTENSITIES[k] > 150.0 and v > 0
        ]

        for asset in high_emission_classes:
            current_pct = self.allocations[asset]
            suggestions.append(
                {
                    "current_asset": asset.replace("_", " ").title(),
                    "current_emission_intensity": self.EMISSION_INTENSITIES[asset],
                    "recommended_action": f"Consider reallocating {current_pct / 2:.0f}% of this holding into 'esg_funds' or 'government_bonds' to significantly reduce your financed footprint.",
                    "potential_savings_tonnes": round(
                        (current_pct / 200.0)
                        * (self.total_value / 1_000_000)
                        * (self.EMISSION_INTENSITIES[asset] - 80.0),
                        2,
                    ),
                }
            )

        return suggestions
