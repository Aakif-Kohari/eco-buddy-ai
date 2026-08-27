"""
Carbon Risk Analyzer.
Evaluates permanence risk, market volatility, and co-benefit distribution across holdings.
"""

from typing import Dict, List, Any
import math


class CarbonRiskAnalyzer:
    """Analyzes the risk profile of a carbon offset portfolio."""

    # Risk scores (0-100, lower is better) for different project types
    PERMANENCE_RISK = {
        "reforestation": 35,  # Risk of wildfire/reversal
        "renewable_energy": 10,  # Highly permanent
        "methane_capture": 15,  # Highly permanent
        "direct_air_capture": 5,  # Most permanent
    }

    # Co-benefit scores (0-100, higher is better)
    CO_BENEFIT_SCORES = {
        "reforestation": 90,  # Biodiversity, community
        "renewable_energy": 60,  # Local jobs, air quality
        "methane_capture": 70,  # Air quality, waste reduction
        "direct_air_capture": 40,  # Primarily carbon only
    }

    def __init__(self, portfolio_summary: Dict[str, Any]):
        self.summary = portfolio_summary

    def calculate_herfindahl_hirschman_index(self) -> float:
        """Calculates the HHI to measure portfolio concentration risk."""
        total_tonnes = self.summary["total_tonnes"]
        if total_tonnes == 0:
            return 0.0

        hhi = 0.0
        for tonnes in self.summary["type_breakdown"].values():
            market_share = tonnes / total_tonnes
            hhi += market_share**2

        # Normalize to 0-100 scale (10000 is max monopoly)
        return round(hhi * 10000, 1)

    def evaluate_portfolio_risk(self) -> Dict[str, Any]:
        """Evaluates the overall risk and co-benefit profile of the portfolio."""
        total_tonnes = self.summary["total_tonnes"]
        if total_tonnes == 0:
            return {"error": "Portfolio is empty"}

        weighted_permanence_risk = 0.0
        weighted_co_benefit = 0.0

        for p_type, tonnes in self.summary["type_breakdown"].items():
            weight = tonnes / total_tonnes
            permanence = self.PERMANENCE_RISK.get(p_type, 50)
            co_benefit = self.CO_BENEFIT_SCORES.get(p_type, 50)

            weighted_permanence_risk += permanence * weight
            weighted_co_benefit += co_benefit * weight

        hhi = self.calculate_herfindahl_hirschman_index()

        # Diversification score (inverse of HHI, scaled to 0-100)
        diversification_score = max(0, 100 - (hhi / 100))

        return {
            "hhi_score": hhi,
            "diversification_score": round(diversification_score, 1),
            "weighted_permanence_risk": round(weighted_permanence_risk, 1),
            "weighted_co_benefit_score": round(weighted_co_benefit, 1),
            "overall_risk_rating": self._get_risk_rating(
                weighted_permanence_risk, diversification_score
            ),
        }

    def _get_risk_rating(self, permanence_risk: float, diversification: float) -> str:
        """Determines the overall risk rating."""
        if permanence_risk < 20 and diversification > 70:
            return "Low Risk"
        elif permanence_risk < 35 and diversification > 50:
            return "Moderate Risk"
        else:
            return "High Risk"

    def generate_risk_recommendations(self) -> List[str]:
        """Generates actionable recommendations based on risk analysis."""
        recs = []
        risk_profile = self.evaluate_portfolio_risk()

        if risk_profile["hhi_score"] > 5000:
            recs.append(
                "⚠️ **High Concentration:** Your portfolio is heavily reliant on a single project type. Consider diversifying to reduce risk."
            )

        if risk_profile["weighted_permanence_risk"] > 30:
            recs.append(
                "🌲 **Permanence Risk:** A significant portion of your portfolio is in nature-based solutions. Consider adding technological removals (e.g., Direct Air Capture) for permanence."
            )

        if risk_profile["weighted_co_benefit_score"] < 60:
            recs.append(
                "🤝 **Co-benefits:** Your portfolio could be improved by adding projects with strong community or biodiversity co-benefits, such as reforestation or clean cookstoves."
            )

        if not recs:
            recs.append(
                "✅ **Excellent Portfolio:** Your offset portfolio is well-diversified, permanent, and delivers strong co-benefits!"
            )

        return recs
