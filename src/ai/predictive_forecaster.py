"""
Predictive Forecaster.
Applies time-series forecasting logic to predict future footprint based on historical data and user-defined scenarios.
"""

from typing import Dict, Any, List
from src.utils.footprint_digital_twin import FootprintDigitalTwin


class PredictiveForecaster:
    """Manages forecasting logic and scenario definitions."""

    # Pre-defined scenario impacts (kg CO2e per year)
    SCENARIO_LIBRARY = {
        "work_from_home_2_days": {
            "name": "Work from Home (2 days/week)",
            "reduction_kg": 1000.0,
        },
        "switch_to_ev": {"name": "Switch to Electric Vehicle", "reduction_kg": 2500.0},
        "adopt_plant_based_diet": {
            "name": "Adopt Plant-Based Diet",
            "reduction_kg": 1500.0,
        },
        "install_home_solar": {
            "name": "Install Home Solar Panels",
            "reduction_kg": 3000.0,
        },
        "reduce_flights_by_half": {
            "name": "Reduce Air Travel by 50%",
            "reduction_kg": 1200.0,
        },
    }

    def __init__(
        self, current_footprint: float, historical_data: List[Dict[str, Any]] = None
    ):
        self.twin = FootprintDigitalTwin(current_footprint, historical_data)

    def get_available_scenarios(self) -> List[Dict[str, Any]]:
        """Returns the library of pre-defined future scenarios."""
        return list(self.SCENARIO_LIBRARY.values())

    def apply_scenario_by_key(self, scenario_key: str) -> bool:
        """Applies a scenario from the library to the digital twin."""
        if scenario_key in self.SCENARIO_LIBRARY:
            scenario = self.SCENARIO_LIBRARY[scenario_key]
            self.twin.apply_scenario(scenario["name"], scenario["reduction_kg"])
            return True
        return False

    def generate_forecast_report(self, target_goal_kg: float = None) -> Dict[str, Any]:
        """Generates a comprehensive forecast report comparing baseline vs. scenario trajectories."""
        baseline = self.twin.get_baseline_trajectory(years=5)
        scenario = self.twin.get_scenario_trajectory(years=5)

        # Check alignment with goal
        goal_status = "Not Set"
        if target_goal_kg is not None:
            final_scenario_value = scenario[-1]["projected_footprint_kg"]
            if final_scenario_value <= target_goal_kg:
                goal_status = "On Track"
            else:
                goal_status = "Off Track"

        return {
            "current_footprint_kg": self.twin.current_footprint,
            "target_goal_kg": target_goal_kg,
            "goal_status": goal_status,
            "baseline_trajectory": baseline,
            "scenario_trajectory": scenario,
            "scenarios_applied": self.twin.scenarios_applied,
        }
