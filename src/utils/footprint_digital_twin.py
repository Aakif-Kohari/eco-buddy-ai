"""
Footprint Digital Twin.
Constructs a dynamic, state-based model of the user's current carbon profile and baseline trajectory.
"""

from typing import Dict, Any, List
import datetime


class FootprintDigitalTwin:
    """Models the user's current carbon state and projects baseline trajectory."""

    def __init__(
        self,
        current_annual_footprint: float,
        historical_data: List[Dict[str, Any]] = None,
    ):
        self.current_footprint = current_annual_footprint
        self.historical_data = historical_data or []
        self.scenarios_applied = []

    def get_baseline_trajectory(self, years: int = 5) -> List[Dict[str, Any]]:
        """
        Generates a baseline trajectory assuming no behavior changes.
        Applies a slight natural regression to the mean (0.5% annual increase due to inflation/lifestyle creep).
        """
        trajectory = []
        current_year = datetime.datetime.now().year
        projected_value = self.current_footprint

        for i in range(years + 1):
            trajectory.append(
                {
                    "year": current_year + i,
                    "projected_footprint_kg": round(projected_value, 1),
                    "scenario": "Baseline (No Change)",
                }
            )
            # 0.5% annual increase
            projected_value *= 1.005

        return trajectory

    def apply_scenario(self, scenario_name: str, annual_reduction_kg: float) -> None:
        """Applies a future event scenario to the digital twin."""
        self.scenarios_applied.append(
            {"name": scenario_name, "annual_reduction_kg": annual_reduction_kg}
        )

    def get_scenario_trajectory(self, years: int = 5) -> List[Dict[str, Any]]:
        """Generates a trajectory incorporating all applied scenarios."""
        trajectory = []
        current_year = datetime.datetime.now().year
        projected_value = self.current_footprint

        total_annual_reduction = sum(
            s["annual_reduction_kg"] for s in self.scenarios_applied
        )
        scenario_names = (
            ", ".join([s["name"] for s in self.scenarios_applied]) or "Custom Scenarios"
        )

        for i in range(years + 1):
            # Apply reduction, but still account for 0.5% lifestyle creep on the remaining footprint
            projected_value = (projected_value - total_annual_reduction) * 1.005
            projected_value = max(0.0, projected_value)  # Footprint can't be negative

            trajectory.append(
                {
                    "year": current_year + i,
                    "projected_footprint_kg": round(projected_value, 1),
                    "scenario": scenario_names,
                }
            )

        return trajectory
