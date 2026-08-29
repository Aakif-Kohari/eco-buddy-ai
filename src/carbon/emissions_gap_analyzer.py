"""
Emissions Gap Analyzer.
Compares current Scope 1, 2, and 3 emissions against a target net-zero year to calculate required annual reduction rates.
"""

from typing import Dict, Any, List


class EmissionsGapAnalyzer:
    """Analyzes the gap between current emissions and net-zero targets."""

    def __init__(
        self,
        current_scope1: float,
        current_scope2: float,
        current_scope3: float,
        target_year: int,
    ):
        self.current_scope1 = current_scope1
        self.current_scope2 = current_scope2
        self.current_scope3 = current_scope3
        self.target_year = target_year
        self.current_year = 2024  # Fixed for consistent projection

        self.total_current = current_scope1 + current_scope2 + current_scope3

    def calculate_required_reduction_rate(self) -> Dict[str, Any]:
        """
        Calculates the compound annual growth rate (CAGR) of reduction needed
        to reach net-zero by the target year.
        """
        years_remaining = self.target_year - self.current_year

        if years_remaining <= 0:
            return {
                "status": "invalid",
                "message": "Target year must be in the future.",
                "required_annual_reduction_pct": None,
            }

        # Formula: Final = Initial * (1 - r)^n  =>  0 = Total * (1 - r)^n
        # To avoid exactly 0, we target 1% of current emissions as "practical net-zero"
        target_emissions = self.total_current * 0.01

        # r = 1 - (target / initial)^(1/n)
        reduction_factor = (target_emissions / self.total_current) ** (
            1 / years_remaining
        )
        required_rate = (1 - reduction_factor) * 100

        return {
            "status": "valid",
            "years_remaining": years_remaining,
            "total_current_emissions": round(self.total_current, 2),
            "target_emissions": round(target_emissions, 2),
            "required_annual_reduction_pct": round(required_rate, 1),
            "feasibility": self._assess_feasibility(required_rate),
        }

    def _assess_feasibility(self, rate: float) -> str:
        """Assesses the feasibility of the required reduction rate."""
        if rate <= 5.0:
            return "Highly Feasible (Standard efficiency gains)"
        elif rate <= 10.0:
            return "Feasible (Requires dedicated decarbonization strategy)"
        elif rate <= 15.0:
            return "Challenging (Requires major operational changes and CAPEX)"
        else:
            return "Highly Ambitious (May require carbon removal offsets or business model pivot)"

    def get_scope_breakdown(self) -> Dict[str, float]:
        """Returns the percentage breakdown of current emissions by scope."""
        if self.total_current == 0:
            return {"scope1_pct": 0.0, "scope2_pct": 0.0, "scope3_pct": 0.0}

        return {
            "scope1_pct": round((self.current_scope1 / self.total_current) * 100, 1),
            "scope2_pct": round((self.current_scope2 / self.total_current) * 100, 1),
            "scope3_pct": round((self.current_scope3 / self.total_current) * 100, 1),
        }
