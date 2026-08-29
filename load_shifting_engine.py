"""
Load Shifting Engine.
Calculates the financial savings and carbon reduction of shifting flexible appliance loads to off-peak, high-renewable periods.
"""

from typing import Dict, Any, List


class LoadShiftingEngine:
    """Models the financial and environmental benefits of demand response."""

    # Mock hourly grid data (0-23)
    # Price: $/kWh, Carbon Intensity: kg CO2e/kWh
    HOURLY_GRID_DATA = {
        0: {"price": 0.10, "carbon": 0.30},
        1: {"price": 0.09, "carbon": 0.28},
        2: {"price": 0.08, "carbon": 0.25},
        3: {"price": 0.08, "carbon": 0.25},
        4: {"price": 0.09, "carbon": 0.28},
        5: {"price": 0.12, "carbon": 0.35},
        6: {"price": 0.15, "carbon": 0.45},
        7: {"price": 0.18, "carbon": 0.50},
        8: {"price": 0.20, "carbon": 0.55},
        9: {"price": 0.18, "carbon": 0.50},
        10: {"price": 0.15, "carbon": 0.40},
        11: {"price": 0.12, "carbon": 0.35},
        12: {"price": 0.10, "carbon": 0.25},  # Solar peak
        13: {"price": 0.10, "carbon": 0.25},
        14: {"price": 0.12, "carbon": 0.30},
        15: {"price": 0.15, "carbon": 0.40},
        16: {"price": 0.18, "carbon": 0.50},
        17: {"price": 0.22, "carbon": 0.60},
        18: {"price": 0.25, "carbon": 0.65},  # Evening peak
        19: {"price": 0.25, "carbon": 0.65},
        20: {"price": 0.22, "carbon": 0.60},
        21: {"price": 0.18, "carbon": 0.50},
        22: {"price": 0.15, "carbon": 0.40},
        23: {"price": 0.12, "carbon": 0.35},
    }

    def __init__(self):
        self.grid_data = self.HOURLY_GRID_DATA

    def find_optimal_hours(
        self, duration_hours: int, preference: str = "carbon"
    ) -> List[int]:
        """
        Finds the best consecutive hours to run an appliance.

        Args:
            duration_hours: How many consecutive hours the appliance needs to run.
            preference: 'carbon' to minimize emissions, 'cost' to minimize price.
        """
        best_start_hour = 0
        lowest_metric = float("inf")

        for start_hour in range(24):
            current_metric = 0.0
            for h in range(duration_hours):
                hour = (start_hour + h) % 24
                if preference == "carbon":
                    current_metric += self.grid_data[hour]["carbon"]
                else:
                    current_metric += self.grid_data[hour]["price"]

            if current_metric < lowest_metric:
                lowest_metric = current_metric
                best_start_hour = start_hour

        # Return the list of optimal hours
        return [(best_start_hour + i) % 24 for i in range(duration_hours)]

    def calculate_shift_savings(
        self, appliance_kwh: float, baseline_hours: List[int], optimal_hours: List[int]
    ) -> Dict[str, Any]:
        """
        Calculates the savings achieved by shifting from baseline to optimal hours.
        """
        baseline_cost = (
            sum(self.grid_data[h]["price"] for h in baseline_hours) * appliance_kwh
        )
        optimal_cost = (
            sum(self.grid_data[h]["price"] for h in optimal_hours) * appliance_kwh
        )

        baseline_carbon = (
            sum(self.grid_data[h]["carbon"] for h in baseline_hours) * appliance_kwh
        )
        optimal_carbon = (
            sum(self.grid_data[h]["carbon"] for h in optimal_hours) * appliance_kwh
        )

        return {
            "baseline_cost_usd": round(baseline_cost, 3),
            "optimal_cost_usd": round(optimal_cost, 3),
            "money_saved_usd": round(baseline_cost - optimal_cost, 3),
            "baseline_carbon_kg": round(baseline_carbon, 3),
            "optimal_carbon_kg": round(optimal_carbon, 3),
            "carbon_saved_kg": round(baseline_carbon - optimal_carbon, 3),
        }
