"""
Dividend Rebate Calculator.
Models universal basic dividend returns or household-specific rebates based on income brackets and household size.
"""

from typing import Dict, Any


class DividendRebateCalculator:
    """Calculates the potential carbon dividend rebate for a household."""

    # Mock policy parameters for a "Fee and Dividend" model
    BASE_DIVIDEND_PER_ADULT = 600.0  # USD per year
    BASE_DIVIDEND_PER_CHILD = 300.0  # USD per year

    # Income phase-out multiplier (simplified mock)
    # Households above $150k see a gradual reduction in the dividend
    INCOME_PHASE_OUT_THRESHOLD = 150000.0
    PHASE_OUT_RATE = 0.002  # 0.2% reduction per dollar over threshold

    def __init__(
        self, num_adults: int, num_children: int, annual_household_income_usd: float
    ):
        self.num_adults = max(1, num_adults)
        self.num_children = max(0, num_children)
        self.income = max(0.0, annual_household_income_usd)

    def calculate_rebate(self) -> Dict[str, Any]:
        """Calculates the total annual dividend rebate for the household."""
        # 1. Calculate base dividend
        base_rebate = (self.num_adults * self.BASE_DIVIDEND_PER_ADULT) + (
            self.num_children * self.BASE_DIVIDEND_PER_CHILD
        )

        # 2. Apply income phase-out if applicable
        reduction = 0.0
        if self.income > self.INCOME_PHASE_OUT_THRESHOLD:
            excess_income = self.income - self.INCOME_PHASE_OUT_THRESHOLD
            reduction = excess_income * self.PHASE_OUT_RATE

        # Ensure reduction doesn't exceed the base rebate
        reduction = min(reduction, base_rebate)
        final_rebate = base_rebate - reduction

        return {
            "num_adults": self.num_adults,
            "num_children": self.num_children,
            "annual_income_usd": self.income,
            "base_rebate_usd": round(base_rebate, 2),
            "income_reduction_usd": round(reduction, 2),
            "final_annual_rebate_usd": round(final_rebate, 2),
            "monthly_rebate_usd": round(final_rebate / 12.0, 2),
        }

    def calculate_net_financial_impact(
        self, tax_liability_usd: float
    ) -> Dict[str, Any]:
        """
        Calculates the net financial impact (Rebate minus Tax Liability).
        A positive number means the household profits from the policy.
        """
        rebate_data = self.calculate_rebate()
        final_rebate = rebate_data["final_annual_rebate_usd"]

        net_impact = final_rebate - tax_liability_usd

        return {
            "tax_liability_usd": round(tax_liability_usd, 2),
            "final_rebate_usd": round(final_rebate, 2),
            "net_annual_impact_usd": round(net_impact, 2),
            "is_net_positive": net_impact >= 0,
            "interpretation": self._interpret_net_impact(net_impact),
        }

    def _interpret_net_impact(self, net_impact: float) -> str:
        """Provides a qualitative interpretation of the net financial impact."""
        if net_impact > 500:
            return "📈 **Net Gainer:** Your household would receive significantly more in dividends than you would pay in carbon costs."
        elif net_impact >= 0:
            return "⚖️ **Revenue Neutral:** The dividend rebate effectively offsets your increased carbon costs."
        else:
            return "📉 **Net Payer:** Your household would pay more in carbon costs than you receive in dividends. Reducing your footprint would improve this outcome."
