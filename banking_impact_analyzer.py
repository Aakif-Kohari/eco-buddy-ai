"""
Banking Impact Analyzer.
Calculates the implied carbon footprint of standard bank accounts and compares them to green alternatives.
"""

from typing import Dict, Any, List


class BankingImpactAnalyzer:
    """Analyzes the hidden carbon footprint of retail banking relationships."""

    # Estimated financed emissions per $10,000 in deposits (tonnes CO2e/year)
    # Traditional banks lend to fossil fuels; green banks lend to renewables.
    DEPOSIT_EMISSION_FACTORS = {
        "traditional_large_bank": 0.85,
        "traditional_regional_bank": 0.60,
        "credit_union": 0.40,
        "certified_green_bank": 0.10,
        "online_neobank": 0.50,
    }

    def __init__(self, deposit_amount_usd: float):
        self.deposit_amount = deposit_amount_usd

    def calculate_deposit_footprint(self, bank_type: str) -> Dict[str, Any]:
        """Calculates the annual carbon footprint of deposits at a specific bank type."""
        if bank_type not in self.DEPOSIT_EMISSION_FACTORS:
            raise ValueError(f"Unknown bank type: {bank_type}")

        factor = self.DEPOSIT_EMISSION_FACTORS[bank_type]
        # Factor is per $10k, so multiply by (amount / 10000)
        annual_emissions_tonnes = (self.deposit_amount / 10_000.0) * factor

        return {
            "bank_type": bank_type,
            "deposit_amount_usd": self.deposit_amount,
            "annual_emissions_tonnes": round(annual_emissions_tonnes, 3),
            "equivalent_tree_seedlings": round(
                annual_emissions_tonnes * 1000 / 20
            ),  # ~20kg CO2 absorbed per tree/year
        }

    def compare_banking_options(self, current_bank_type: str) -> List[Dict[str, Any]]:
        """Compares the current bank's footprint against greener alternatives."""
        current_footprint = self.calculate_deposit_footprint(current_bank_type)
        alternatives = []

        for bank_type, factor in self.DEPOSIT_EMISSION_FACTORS.items():
            if bank_type == current_bank_type:
                continue

            alt_footprint = self.calculate_deposit_footprint(bank_type)
            savings_tonnes = (
                current_footprint["annual_emissions_tonnes"]
                - alt_footprint["annual_emissions_tonnes"]
            )

            if savings_tonnes > 0:
                alternatives.append(
                    {
                        "alternative_bank_type": bank_type.replace("_", " ").title(),
                        "annual_emissions_tonnes": alt_footprint[
                            "annual_emissions_tonnes"
                        ],
                        "potential_annual_savings_tonnes": round(savings_tonnes, 3),
                        "savings_percentage": round(
                            (
                                savings_tonnes
                                / current_footprint["annual_emissions_tonnes"]
                            )
                            * 100,
                            1,
                        )
                        if current_footprint["annual_emissions_tonnes"] > 0
                        else 0,
                    }
                )

        # Sort by highest savings
        alternatives.sort(
            key=lambda x: x["potential_annual_savings_tonnes"], reverse=True
        )
        return alternatives
