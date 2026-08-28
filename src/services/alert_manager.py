"""
Alert Manager.
Categorizes alerts by severity, generates simulated root-cause hypotheses, and suggests corrective actions.
"""

from typing import List, Dict, Any


class AlertManager:
    """Manages the generation and categorization of carbon footprint anomaly alerts."""

    SEVERITY_LEVELS = {
        "low": {"color": "#ffc107", "icon": "⚠️", "multiplier": 1.5},
        "medium": {"color": "#fd7e14", "icon": "🚨", "multiplier": 2.5},
        "high": {"color": "#dc3545", "icon": "🔥", "multiplier": 4.0},
    }

    def __init__(self):
        self.root_cause_hypotheses = {
            "transport": "Sudden increase in flights, long-distance driving, or change in daily commute.",
            "energy": "Extreme weather leading to increased HVAC usage, or addition of high-draw appliances.",
            "diet": "Shift towards high-impact foods (e.g., red meat, dairy) or increased food waste.",
            "shopping": "Purchase of high-embodied-carbon goods (e.g., new electronics, fast fashion).",
        }

    def determine_severity(self, z_score: float) -> str:
        """Determines the severity level based on the absolute Z-score."""
        abs_z = abs(z_score)
        if abs_z >= 3.0:
            return "high"
        elif abs_z >= 2.0:
            return "medium"
        else:
            return "low"

    def generate_alert(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a structured alert for a specific anomalous data point.

        Args:
            anomaly_data: Dictionary containing anomaly metrics (z_score, carbon_kg, etc.).

        Returns:
            Structured alert dictionary with severity, hypothesis, and recommendations.
        """
        z_score = anomaly_data.get("z_score", 0.0)
        carbon_kg = anomaly_data.get("carbon_kg", 0.0)
        mean = anomaly_data.get("mean_baseline", 0.0)

        severity = self.determine_severity(z_score)
        severity_info = self.SEVERITY_LEVELS[severity]

        # Simulate root cause based on magnitude of deviation
        deviation_pct = ((carbon_kg - mean) / mean) * 100 if mean > 0 else 0

        if deviation_pct > 100:
            category = "transport"
        elif deviation_pct > 50:
            category = "energy"
        elif deviation_pct > 25:
            category = "diet"
        else:
            category = "shopping"

        hypothesis = self.root_cause_hypotheses.get(
            category, "Unidentified spike in activity."
        )

        recommendations = self._get_recommendations(category, severity)

        return {
            "date": anomaly_data.get("date", "Unknown Date"),
            "carbon_kg": carbon_kg,
            "z_score": z_score,
            "severity": severity,
            "severity_icon": severity_info["icon"],
            "severity_color": severity_info["color"],
            "deviation_pct": round(deviation_pct, 1),
            "hypothesis": hypothesis,
            "recommendations": recommendations,
            "resolved": False,
        }

    def _get_recommendations(self, category: str, severity: str) -> List[str]:
        """Returns context-aware recommendations based on category and severity."""
        recs = {
            "transport": [
                "Consider consolidating trips or exploring public transit alternatives.",
                "If flying is unavoidable, look into verified carbon offset programs for this specific route.",
            ],
            "energy": [
                "Check for phantom power draw from electronics and use smart power strips.",
                "Review your thermostat settings; a 1-2 degree adjustment can yield significant savings.",
            ],
            "diet": [
                "Try incorporating one or two plant-based meals per week to offset high-impact days.",
                "Plan meals ahead to reduce food waste, which contributes significantly to methane emissions.",
            ],
            "shopping": [
                "Evaluate if the purchase was a necessity or if a second-hand alternative was available.",
                "Extend the lifespan of current goods through proper maintenance and repair.",
            ],
        }

        base_recs = recs.get(category, recs["shopping"])
        if severity == "high":
            base_recs.insert(
                0,
                "🚨 Immediate Action: Review this period's activities in detail to identify the primary driver.",
            )

        return base_recs
