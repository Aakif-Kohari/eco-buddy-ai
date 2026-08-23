"""
Substitution ROI Engine.
Calculates the break-even point and long-term financial/environmental return on investment.
"""

from typing import Dict, Any, List
from green_premium_calculator import GreenPremiumCalculator


class SubstitutionROIEngine:
    """Models the financial and environmental ROI of sustainable substitutions."""

    def __init__(self):
        self.calculator = GreenPremiumCalculator()

    def calculate_roi(
        self,
        product_key: str,
        utility_inflation_rate: float = 0.03,
        subsidy_usd: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Calculates the break-even point and cumulative ROI over the product's lifespan.

        Args:
            product_key: The product category identifier.
            utility_inflation_rate: Annual percentage increase in utility costs (e.g., 0.03 for 3%).
            subsidy_usd: Any upfront government or utility rebate.
        """
        baseline = self.calculator.calculate_premium(product_key)

        effective_premium = max(0.0, baseline["green_premium_usd"] - subsidy_usd)
        annual_savings = baseline["baseline_annual_cost_savings_usd"]
        lifespan = baseline["lifespan_years"]

        if effective_premium == 0.0:
            break_even_years = 0.0
        elif annual_savings <= 0:
            break_even_years = float("inf")
        else:
            break_even_years = effective_premium / annual_savings

        # Calculate cumulative financial savings over lifespan with inflation
        total_financial_savings = 0.0
        current_annual_savings = annual_savings

        for year in range(1, lifespan + 1):
            total_financial_savings += current_annual_savings
            current_annual_savings *= 1 + utility_inflation_rate

        net_financial_roi = total_financial_savings - effective_premium
        total_carbon_savings = baseline["baseline_annual_carbon_savings_kg"] * lifespan

        # Generate year-by-year data for charting
        yearly_data = []
        cumulative_savings = -effective_premium
        current_savings = annual_savings

        for year in range(lifespan + 1):
            yearly_data.append(
                {
                    "year": year,
                    "cumulative_net_savings_usd": round(cumulative_savings, 2),
                    "annual_savings_usd": round(current_savings, 2),
                }
            )
            cumulative_savings += current_savings
            current_savings *= 1 + utility_inflation_rate

        return {
            "product_name": baseline["product_name"],
            "effective_premium_usd": round(effective_premium, 2),
            "subsidy_applied_usd": subsidy_usd,
            "break_even_years": round(break_even_years, 1)
            if break_even_years != float("inf")
            else "Never",
            "lifespan_years": lifespan,
            "total_financial_savings_usd": round(total_financial_savings, 2),
            "net_financial_roi_usd": round(net_financial_roi, 2),
            "total_carbon_savings_kg": round(total_carbon_savings, 2),
            "yearly_projection": yearly_data,
            "is_financially_viable": net_financial_roi > 0,
        }
