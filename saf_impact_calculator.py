"""
SAF Impact Calculator.
Models the carbon reduction potential and cost premium of various Sustainable Aviation Fuel blending percentages.
"""

from typing import Dict, Any


class SAFImpactCalculator:
    """Calculates the environmental and financial impact of using Sustainable Aviation Fuel."""

    # SAF reduces lifecycle emissions by approximately 80% compared to conventional jet fuel
    SAF_CARBON_REDUCTION_PCT = 0.80

    # Mock cost premium per kg of CO2e saved (highly variable in reality)
    COST_PREMIUM_PER_KG_CO2E_SAVED = 0.50  # USD

    def __init__(self, base_flight_emissions_kg: float, base_ticket_price_usd: float):
        self.base_emissions_kg = base_flight_emissions_kg
        self.base_price_usd = base_ticket_price_usd

    def calculate_saf_scenarios(self) -> list:
        """Calculates impact for 10%, 50%, and 100% SAF blending scenarios."""
        scenarios = []
        blend_percentages = [10, 50, 100]

        for blend_pct in blend_percentages:
            blend_decimal = blend_pct / 100.0

            # Carbon saved is proportional to the blend percentage and the 80% lifecycle reduction
            carbon_saved_kg = (
                self.base_emissions_kg * blend_decimal * self.SAF_CARBON_REDUCTION_PCT
            )
            remaining_emissions_kg = self.base_emissions_kg - carbon_saved_kg

            # Cost premium calculation
            cost_premium_usd = carbon_saved_kg * self.COST_PREMIUM_PER_KG_CO2E_SAVED
            total_ticket_price_usd = self.base_price_usd + cost_premium_usd

            scenarios.append(
                {
                    "blend_pct": blend_pct,
                    "carbon_saved_kg": round(carbon_saved_kg, 2),
                    "remaining_emissions_kg": round(remaining_emissions_kg, 2),
                    "cost_premium_usd": round(cost_premium_usd, 2),
                    "total_price_usd": round(total_ticket_price_usd, 2),
                }
            )

        return scenarios

    def get_saf_education_snippet(self) -> str:
        """Returns a brief educational explanation of SAF."""
        return (
            "**What is SAF?** Sustainable Aviation Fuel is made from renewable resources like waste oils, "
            "agricultural residues, or even captured CO2. While it emits CO2 when burned, its *lifecycle* "
            "emissions are up to 80% lower than conventional jet fuel because the feedstock absorbed CO2 "
            "while growing, or it prevents waste from decomposing in landfills."
        )
