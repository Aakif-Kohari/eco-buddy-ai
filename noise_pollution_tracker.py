"""
Noise Pollution Tracker.
Estimates ambient noise exposure based on location type and daily time spent.
"""

from typing import Dict, Any, List

# Average decibel (dB) levels for different environments
ENVIRONMENT_NOISE_LEVELS = {
    "dense_urban": 75,  # Busy city streets
    "suburban": 55,  # Residential areas
    "near_highway": 85,  # Major road proximity
    "park_green": 45,  # Quiet parks
    "indoor_home": 40,  # Typical indoor environment
    "office": 60,  # Typical office environment
}

# Health impact multipliers per hour of exposure (arbitrary units for relative comparison)
HEALTH_IMPACT_MULTIPLIERS = {
    "stress": 1.5,
    "sleep_disruption": 2.0,
    "cardiovascular": 1.2,
}


class NoisePollutionTracker:
    """Calculates daily noise exposure and associated health impact metrics."""

    def __init__(self):
        self.environments = ENVIRONMENT_NOISE_LEVELS
        self.multipliers = HEALTH_IMPACT_MULTIPLIERS

    def calculate_daily_exposure(
        self, time_allocation: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculates weighted average noise exposure and health impact.
        time_allocation: dict mapping environment name to hours spent per day.
        """
        total_hours = sum(time_allocation.values())
        if total_hours == 0:
            total_hours = 24.0  # Default to 24h if empty

        weighted_db_sum = 0.0
        for env, hours in time_allocation.items():
            db_level = self.environments.get(env, 50)  # Default to 50dB if unknown
            weighted_db_sum += db_level * hours

        average_db = round(weighted_db_sum / total_hours, 1)

        # Calculate health impact score (0-100, higher is worse)
        # Baseline: 50dB is 0 impact, 85dB is 100 impact
        raw_impact = max(0, average_db - 50)
        impact_score = min(100, round((raw_impact / 35.0) * 100, 1))

        return {
            "total_hours_logged": round(total_hours, 1),
            "average_daily_db": average_db,
            "health_impact_score": impact_score,
            "risk_level": self._get_risk_level(average_db),
            "breakdown": {
                env: self.environments.get(env, 50) for env in time_allocation.keys()
            },
        }

    def _get_risk_level(self, average_db: float) -> str:
        """Categorizes noise exposure risk."""
        if average_db < 50:
            return "Low"
        elif average_db < 65:
            return "Moderate"
        elif average_db < 80:
            return "High"
        else:
            return "Severe"
