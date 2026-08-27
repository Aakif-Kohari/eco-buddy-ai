"""
Avoided Emissions Tracker.
Calculates baseline emissions of conventional activities and subtracts actual emissions of sustainable alternatives.
"""

from typing import Dict, Any, List


class AvoidedEmissionsTracker:
    """Tracks and calculates Scope 4 (Avoided) src.carbon.emissions."""

    def __init__(self):
        self.avoided_activities: List[Dict[str, Any]] = []
        self.total_avoided_kg = 0.0

    def log_avoided_activity(
        self,
        activity_type: str,
        quantity: float,
        baseline_factor: float,
        alternative_factor: float,
    ) -> Dict[str, Any]:
        """
        Logs an activity and calculates the avoided src.carbon.emissions.

        Args:
            activity_type: e.g., "remote_work_day", "virtual_meeting", "digital_document"
            quantity: Number of units (e.g., days, meetings)
            baseline_factor: kg CO2e per unit for the conventional method
            alternative_factor: kg CO2e per unit for the sustainable method
        """
        baseline_total = quantity * baseline_factor
        alternative_total = quantity * alternative_factor
        avoided = max(0.0, baseline_total - alternative_total)

        record = {
            "activity_type": activity_type,
            "quantity": quantity,
            "baseline_kg": round(baseline_total, 2),
            "alternative_kg": round(alternative_total, 2),
            "avoided_kg": round(avoided, 2),
        }

        self.avoided_activities.append(record)
        self.total_avoided_kg += avoided

        return record

    def get_summary(self) -> Dict[str, Any]:
        """Returns a summary of all logged avoided src.carbon.emissions."""
        # Group by activity type
        by_type = {}
        for activity in self.avoided_activities:
            a_type = activity["activity_type"]
            if a_type not in by_type:
                by_type[a_type] = 0.0
            by_type[a_type] += activity["avoided_kg"]

        return {
            "total_avoided_kg": round(self.total_avoided_kg, 2),
            "breakdown_by_type": {k: round(v, 2) for k, v in by_type.items()},
            "activity_count": len(self.avoided_activities),
        }

    def reset_tracker(self) -> None:
        """Clears all logged activities."""
        self.avoided_activities = []
        self.total_avoided_kg = 0.0
