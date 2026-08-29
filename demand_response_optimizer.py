"""
Demand Response Optimizer.
Evaluates a household's daily energy load and identifies flexible appliances that can be shifted without impacting user comfort.
"""

from typing import Dict, Any, List
from load_shifting_engine import LoadShiftingEngine


class DemandResponseOptimizer:
    """Identifies and optimizes flexible household energy loads."""

    # Common flexible appliances and their typical usage patterns
    FLEXIBLE_APPLIANCES = {
        "ev_charging": {
            "name": "EV Charging",
            "avg_kwh": 30.0,
            "duration_hours": 6,
            "typical_start_hour": 18,
        },
        "dishwasher": {
            "name": "Dishwasher",
            "avg_kwh": 1.5,
            "duration_hours": 2,
            "typical_start_hour": 20,
        },
        "washing_machine": {
            "name": "Washing Machine",
            "avg_kwh": 1.0,
            "duration_hours": 1,
            "typical_start_hour": 19,
        },
        "pool_pump": {
            "name": "Pool Pump",
            "avg_kwh": 3.0,
            "duration_hours": 4,
            "typical_start_hour": 12,
        },
        "water_heater_boost": {
            "name": "Water Heater Boost",
            "avg_kwh": 4.0,
            "duration_hours": 2,
            "typical_start_hour": 17,
        },
    }

    def __init__(self):
        self.engine = LoadShiftingEngine()
        self.selected_appliances: List[str] = []

    def select_appliances(self, appliance_keys: List[str]):
        """Selects which appliances to optimize."""
        self.selected_appliances = [
            key for key in appliance_keys if key in self.FLEXIBLE_APPLIANCES
        ]

    def optimize_all_selected(self, preference: str = "carbon") -> Dict[str, Any]:
        """
        Optimizes all selected appliances and aggregates the total savings.
        """
        total_money_saved = 0.0
        total_carbon_saved = 0.0
        appliance_results = []

        for app_key in self.selected_appliances:
            app = self.FLEXIBLE_APPLIANCES[app_key]

            # Baseline hours
            baseline_hours = [
                (app["typical_start_hour"] + i) % 24
                for i in range(app["duration_hours"])
            ]

            # Optimal hours
            optimal_hours = self.engine.find_optimal_hours(
                app["duration_hours"], preference=preference
            )

            # Calculate savings
            savings = self.engine.calculate_shift_savings(
                appliance_kwh=app["avg_kwh"],
                baseline_hours=baseline_hours,
                optimal_hours=optimal_hours,
            )

            total_money_saved += savings["money_saved_usd"]
            total_carbon_saved += savings["carbon_saved_kg"]

            appliance_results.append(
                {
                    "appliance": app["name"],
                    "kwh": app["avg_kwh"],
                    "baseline_hours": baseline_hours,
                    "optimal_hours": optimal_hours,
                    "savings": savings,
                }
            )

        return {
            "preference": preference,
            "total_money_saved_usd": round(total_money_saved, 2),
            "total_carbon_saved_kg": round(total_carbon_saved, 2),
            "appliance_breakdown": appliance_results,
        }

    def generate_load_curve_data(
        self, optimized: bool = False, preference: str = "carbon"
    ) -> List[Dict[str, float]]:
        """
        Generates a 24-hour load curve (kW) for visualization.
        """
        hourly_load = {h: 0.0 for h in range(24)}

        for app_key in self.selected_appliances:
            app = self.FLEXIBLE_APPLIANCES[app_key]
            power_kw = app["avg_kwh"] / app["duration_hours"]

            if optimized:
                hours_to_use = self.engine.find_optimal_hours(
                    app["duration_hours"], preference=preference
                )
            else:
                hours_to_use = [
                    (app["typical_start_hour"] + i) % 24
                    for i in range(app["duration_hours"])
                ]

            for h in hours_to_use:
                hourly_load[h] += power_kw

        return [
            {"hour": h, "load_kw": round(load, 2)} for h, load in hourly_load.items()
        ]
