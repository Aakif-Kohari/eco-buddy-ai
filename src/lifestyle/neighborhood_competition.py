"""
Neighborhood Competition Engine.
Manages anonymous aggregation of user eco-scores by geographic boundaries and calculates neighborhood-wide metrics.
"""

from typing import Dict, List, Any
import hashlib
from datetime import datetime, timedelta


class NeighborhoodCompetition:
    """Aggregates and anonymizes user data for community-level sustainability challenges."""

    def __init__(self):
        # Simulated database of neighborhood metrics
        self.neighborhood_data: Dict[str, Dict[str, Any]] = {}

    def _anonymize_user_id(self, user_id: str, zip_code: str) -> str:
        """Creates a deterministic but anonymous identifier for a user within a specific zip code."""
        # Salt with zip code to ensure anonymity is scoped to the neighborhood
        salted_id = f"{user_id}_{zip_code}_anonymous_salt"
        return hashlib.sha256(salted_id.encode()).hexdigest()[:12]

    def submit_anonymous_score(
        self, user_id: str, zip_code: str, eco_score: float, carbon_saved_kg: float
    ) -> None:
        """Submits a user's score to the neighborhood aggregate, ensuring privacy."""
        anon_id = self._anonymize_user_id(user_id, zip_code)

        if zip_code not in self.neighborhood_data:
            self.neighborhood_data[zip_code] = {
                "total_participants": 0,
                "anonymous_users": set(),
                "total_eco_score_sum": 0.0,
                "total_carbon_saved_kg": 0.0,
                "last_updated": datetime.now().isoformat(),
            }

        data = self.neighborhood_data[zip_code]

        # Only count unique anonymous users to prevent spam
        if anon_id not in data["anonymous_users"]:
            data["anonymous_users"].add(anon_id)
            data["total_participants"] += 1

        data["total_eco_score_sum"] += eco_score
        data["total_carbon_saved_kg"] += carbon_saved_kg
        data["last_updated"] = datetime.now().isoformat()

    def get_neighborhood_metrics(self, zip_code: str) -> Dict[str, Any]:
        """Retrieves aggregated metrics for a specific neighborhood."""
        if zip_code not in self.neighborhood_data:
            return {
                "zip_code": zip_code,
                "total_participants": 0,
                "average_eco_score": 0.0,
                "total_carbon_saved_kg": 0.0,
                "status": "No data available",
            }

        data = self.neighborhood_data[zip_code]
        participants = max(1, data["total_participants"])  # Avoid division by zero

        return {
            "zip_code": zip_code,
            "total_participants": data["total_participants"],
            "average_eco_score": round(data["total_eco_score_sum"] / participants, 1),
            "total_carbon_saved_kg": round(data["total_carbon_saved_kg"], 2),
            "last_updated": data["last_updated"],
            "status": "Active",
        }

    def get_all_neighborhoods_summary(self) -> List[Dict[str, Any]]:
        """Returns a summary of all tracked neighborhoods for leaderboard generation."""
        summaries = []
        for zip_code in self.neighborhood_data.keys():
            summaries.append(self.get_neighborhood_metrics(zip_code))
        return summaries
