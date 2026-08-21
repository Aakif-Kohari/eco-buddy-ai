"""
Green Space Health Impact Analyzer.
Calculates mitigating health benefits provided by proximity to parks or tree canopy.
"""

from typing import Dict, Any


class GreenSpaceHealthImpact:
    """Analyzes how green space mitigates urban stress and noise impacts."""

    def __init__(self):
        pass

    def calculate_mitigation(
        self,
        noise_impact_score: float,
        weekly_park_visits: int,
        home_tree_canopy_pct: float,
    ) -> Dict[str, Any]:
        """
        Calculates the health benefits of green space exposure.

        Args:
            noise_impact_score: The baseline noise impact score (0-100).
            weekly_park_visits: Number of times visiting a park/green space per week.
            home_tree_canopy_pct: Percentage of tree canopy coverage near home (0-100).
        """
        # Mitigation factors
        park_mitigation = weekly_park_visits * 3.0  # Up to ~30 points reduction
        canopy_mitigation = (
            home_tree_canopy_pct / 100.0
        ) * 15.0  # Up to 15 points reduction

        total_mitigation = min(noise_impact_score, park_mitigation + canopy_mitigation)
        adjusted_impact_score = max(0, noise_impact_score - total_mitigation)

        # Calculate specific health benefits
        stress_reduction_pct = min(
            40, round((park_mitigation + canopy_mitigation) * 0.8, 1)
        )
        sleep_quality_improvement = (
            "Significant"
            if adjusted_impact_score < 30
            else "Moderate"
            if adjusted_impact_score < 60
            else "Minimal"
        )

        return {
            "baseline_noise_impact": noise_impact_score,
            "park_mitigation_points": round(park_mitigation, 1),
            "canopy_mitigation_points": round(canopy_mitigation, 1),
            "total_mitigation_points": round(total_mitigation, 1),
            "adjusted_health_impact_score": round(adjusted_impact_score, 1),
            "estimated_stress_reduction_pct": stress_reduction_pct,
            "sleep_quality_improvement": sleep_quality_improvement,
            "recommendations": self._generate_recommendations(
                weekly_park_visits, home_tree_canopy_pct, adjusted_impact_score
            ),
        }

    def _generate_recommendations(
        self, visits: int, canopy_pct: float, adjusted_score: float
    ) -> list:
        """Generates actionable insights based on the analysis."""
        recs = []
        if visits < 2:
            recs.append(
                "🌳 Aim for at least 2 park visits per week to significantly lower stress hormones."
            )
        if canopy_pct < 20:
            recs.append(
                "🪴 Consider adding indoor plants or supporting local tree-planting initiatives to improve your micro-environment."
            )
        if adjusted_score > 50:
            recs.append(
                "🎧 Your adjusted impact score remains high. Consider using noise-canceling headphones or white noise machines for sleep."
            )
        if not recs:
            recs.append(
                "✅ Your green space habits are excellent and effectively mitigating urban environmental stressors!"
            )

        return recs
