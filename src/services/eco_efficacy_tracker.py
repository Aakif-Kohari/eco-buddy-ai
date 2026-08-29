"""
Eco-Efficacy Tracker.
Administers brief self-assessments measuring climate anxiety and perceived personal agency, calculating a dynamic score.
"""

from typing import Dict, Any, List


class EcoEfficacyTracker:
    """Tracks and calculates a user's sense of agency and climate-related well-being."""

    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def administer_check_in(
        self, anxiety_level: int, agency_level: int, action_taken_today: bool
    ) -> Dict[str, Any]:
        """
        Processes a daily check-in to calculate the Eco-Efficacy score.

        Args:
            anxiety_level: 1-10 (10 = highly anxious)
            agency_level: 1-10 (10 = high sense of personal agency)
            action_taken_today: Boolean indicating if a micro-action was completed.
        """
        # Validate inputs
        anxiety_level = max(1, min(10, anxiety_level))
        agency_level = max(1, min(10, agency_level))

        # Calculate base efficacy score
        # High agency and low anxiety = high efficacy
        # We invert anxiety so that lower anxiety contributes positively
        inverted_anxiety = 11 - anxiety_level

        # Weight agency slightly higher as it's the primary driver of efficacy
        base_score = (agency_level * 6.0) + (inverted_anxiety * 4.0)

        # Bonus for taking action today (positive reinforcement loop)
        action_bonus = 10.0 if action_taken_today else 0.0

        # Normalize to 0-100 scale
        # Max base score = (10 * 6) + (10 * 4) = 100. Plus 10 bonus = 110.
        raw_score = base_score + action_bonus
        final_score = min(100.0, max(0.0, raw_score))

        entry = {
            "anxiety_level": anxiety_level,
            "agency_level": agency_level,
            "action_taken": action_taken_today,
            "efficacy_score": round(final_score, 1),
            "interpretation": self._interpret_score(final_score),
        }

        self.history.append(entry)
        return entry

    def _interpret_score(self, score: float) -> str:
        """Provides a qualitative interpretation of the efficacy score."""
        if score >= 80:
            return (
                "🌟 High Efficacy: You feel empowered and are taking meaningful action."
            )
        elif score >= 60:
            return "🌱 Moderate Efficacy: You have a good foundation. Small, consistent steps will build momentum."
        elif score >= 40:
            return "🌥️ Building Efficacy: It's normal to feel overwhelmed. Focus on one tiny, manageable action today."
        else:
            return "🤝 Support Needed: Climate anxiety is valid. Consider connecting with local community groups for shared action."

    def get_trend_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Returns the most recent check-in data for trend visualization."""
        return self.history[-days:]
