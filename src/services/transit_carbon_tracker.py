"""
Transit Carbon Tracker.
Maintains a running tally of carbon saved based on logged alternative commute choices.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta


class TransitCarbonTracker:
    """Tracks daily and monthly carbon savings from sustainable commuting."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log_commute(
        self,
        date: str,
        distance_km: float,
        chosen_mode: str,
        baseline_mode: str = "driving_gas",
    ) -> Dict[str, Any]:
        """
        Logs a commute and calculates the carbon saved compared to the baseline.
        """
        from daily_commute_optimizer import DailyCommuteOptimizer

        optimizer = DailyCommuteOptimizer(distance_km)
        baseline_carbon = optimizer.get_baseline_carbon(baseline_mode)

        # Find chosen mode carbon (using base metrics for simplicity in historical tracking)
        base_metrics = DailyCommuteOptimizer.BASE_METRICS.get(
            chosen_mode, DailyCommuteOptimizer.BASE_METRICS["driving_gas"]
        )
        chosen_carbon = distance_km * base_metrics[0]

        carbon_saved = max(0.0, baseline_carbon - chosen_carbon)

        entry = {
            "date": date,
            "distance_km": distance_km,
            "chosen_mode": chosen_mode,
            "baseline_mode": baseline_mode,
            "baseline_carbon_kg": round(baseline_carbon, 3),
            "chosen_carbon_kg": round(chosen_carbon, 3),
            "carbon_saved_kg": round(carbon_saved, 3),
        }

        self.logs.append(entry)
        return entry

    def get_savings_summary(self) -> Dict[str, float]:
        """Aggregates total carbon saved today and this month."""
        today = datetime.now().strftime("%Y-%m-%d")
        current_month = today[:7]

        today_savings = 0.0
        month_savings = 0.0
        total_savings = 0.0

        for log in self.logs:
            total_savings += log["carbon_saved_kg"]
            if log["date"] == today:
                today_savings += log["carbon_saved_kg"]
            if log["date"].startswith(current_month):
                month_savings += log["carbon_saved_kg"]

        return {
            "today_kg": round(today_savings, 3),
            "month_kg": round(month_savings, 3),
            "total_kg": round(total_savings, 3),
        }

    def get_weekly_heatmap_data(self) -> List[Dict[str, Any]]:
        """Prepares data for a weekly commute habit heatmap."""
        # Generate last 7 days
        heatmap_data = []
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            day_logs = [log for log in self.logs if log["date"] == date]

            if day_logs:
                # If multiple trips, sum them
                total_saved = sum(log["carbon_saved_kg"] for log in day_logs)
                modes = list(set(log["chosen_mode"] for log in day_logs))
                heatmap_data.append(
                    {
                        "date": date,
                        "carbon_saved_kg": round(total_saved, 3),
                        "modes_used": ", ".join(modes),
                        "trips_count": len(day_logs),
                    }
                )
            else:
                heatmap_data.append(
                    {
                        "date": date,
                        "carbon_saved_kg": 0.0,
                        "modes_used": "None",
                        "trips_count": 0,
                    }
                )

        return heatmap_data
