"""
Block Leaderboard Engine.
Ranks neighborhoods, tracks weekly community challenges, and distributes collective rewards.
"""

from typing import Dict, List, Any
from src.lifestyle.neighborhood_competition import NeighborhoodCompetition


class BlockLeaderboard:
    """Manages neighborhood rankings and community challenge progression."""

    def __init__(self):
        self.competition = NeighborhoodCompetition()
        self.weekly_challenges = {
            "challenge_1": {
                "name": "Zero-Waste Week",
                "goal_carbon_saved_kg": 5000.0,
                "description": "Collectively save 5,000 kg of CO2e through waste reduction.",
            },
            "challenge_2": {
                "name": "Green Commute Month",
                "goal_carbon_saved_kg": 15000.0,
                "description": "Save 15,000 kg of CO2e by using public transit, biking, or walking.",
            },
        }

    def generate_leaderboard(
        self, metric: str = "average_eco_score"
    ) -> List[Dict[str, Any]]:
        """Generates a ranked leaderboard of neighborhoods based on the specified metric."""
        summaries = self.competition.get_all_neighborhoods_summary()

        # Filter out neighborhoods with no participants
        active_summaries = [s for s in summaries if s["total_participants"] > 0]

        # Sort descending by the chosen metric
        sorted_leaderboard = sorted(
            active_summaries, key=lambda x: x.get(metric, 0.0), reverse=True
        )

        # Add rank
        for rank, neighborhood in enumerate(sorted_leaderboard, start=1):
            neighborhood["rank"] = rank

        return sorted_leaderboard

    def evaluate_community_challenge_progress(
        self, zip_code: str, challenge_id: str
    ) -> Dict[str, Any]:
        """Evaluates a specific neighborhood's progress toward a weekly challenge."""
        if challenge_id not in self.weekly_challenges:
            raise ValueError("Invalid challenge ID")

        metrics = self.competition.get_neighborhood_metrics(zip_code)
        challenge = self.weekly_challenges[challenge_id]

        total_saved = metrics["total_carbon_saved_kg"]
        goal = challenge["goal_carbon_saved_kg"]
        progress_pct = min(100.0, round((total_saved / goal) * 100, 1))

        return {
            "challenge_name": challenge["name"],
            "goal_kg": goal,
            "current_saved_kg": total_saved,
            "progress_pct": progress_pct,
            "is_completed": progress_pct >= 100.0,
            "participants": metrics["total_participants"],
        }

    def get_localized_sustainability_tips(self, zip_code: str) -> List[str]:
        """Generates tips based on the neighborhood's current performance."""
        metrics = self.competition.get_neighborhood_metrics(zip_code)
        tips = []

        if metrics["average_eco_score"] < 60:
            tips.append(
                "🏘️ **Community Tip:** Host a neighborhood swap meet to reduce consumption and boost your average eco-score!"
            )
        if metrics["total_carbon_saved_kg"] < 1000:
            tips.append(
                "🚲 **Transport Tip:** Organize a 'Car-Free Friday' in your zip code to rapidly increase your collective carbon savings."
            )
        if not tips:
            tips.append(
                "🌟 **Excellent Work!** Your neighborhood is leading the way. Consider mentoring a neighboring zip code to help them improve."
            )

        return tips
