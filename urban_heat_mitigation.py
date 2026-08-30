"""
Urban Heat Mitigation Calculator.
Calculates the localized temperature reduction and subsequent HVAC load decrease based on green infrastructure installed.
"""

from typing import Dict, Any, List
from green_infrastructure_db import GreenInfrastructureDB


class UrbanHeatMitigationCalculator:
    """Estimates the cooling effect and financial ROI of green infrastructure."""

    def __init__(
        self,
        baseline_temp_c: float,
        annual_hvac_cost_usd: float,
        property_area_sqm: float,
    ):
        self.db = GreenInfrastructureDB()
        self.baseline_temp_c = baseline_temp_c
        self.annual_hvac_cost_usd = annual_hvac_cost_usd
        self.property_area_sqm = property_area_sqm
        self.installed_measures: List[Dict[str, Any]] = []

    def add_measure(self, option_key: str, quantity: float) -> bool:
        """
        Adds a green infrastructure measure to the property.

        Args:
            option_key: The type of measure (e.g., 'mature_tree_canopy').
            quantity: The amount installed (in sqm or number of trees).
        """
        details = self.db.get_option_details(option_key)
        if not details:
            return False

        total_cooling_effect = details["cooling_effect_c"] * quantity
        installation_cost = details["cost_per_unit_usd"] * quantity
        annual_maintenance = installation_cost * details["maintenance_annual_pct"]

        self.installed_measures.append(
            {
                "option_key": option_key,
                "option_name": details["name"],
                "unit": details["unit"],
                "quantity": quantity,
                "cooling_effect_c": round(total_cooling_effect, 2),
                "installation_cost_usd": round(installation_cost, 2),
                "annual_maintenance_usd": round(annual_maintenance, 2),
                "lifespan_years": details["lifespan_years"],
            }
        )

        return True

    def calculate_roi(self) -> Dict[str, Any]:
        """Calculates the long-term financial and environmental ROI of the installed measures."""
        if not self.installed_measures:
            return self._empty_result()

        total_cooling_c = sum(m["cooling_effect_c"] for m in self.installed_measures)
        new_temp_c = self.baseline_temp_c - total_cooling_c

        # Mock HVAC savings model: 1°C reduction = ~8% savings on cooling costs
        # Assuming 70% of HVAC cost is cooling (simplified)
        cooling_cost_portion = self.annual_hvac_cost_usd * 0.70
        hvac_savings_pct = min(0.70, total_cooling_c * 0.08)  # Cap at 70% max savings
        annual_hvac_savings_usd = cooling_cost_portion * hvac_savings_pct

        total_installation_cost = sum(
            m["installation_cost_usd"] for m in self.installed_measures
        )
        total_annual_maintenance = sum(
            m["annual_maintenance_usd"] for m in self.installed_measures
        )

        net_annual_savings = annual_hvac_savings_usd - total_annual_maintenance

        # Simple payback period
        if net_annual_savings > 0:
            payback_years = total_installation_cost / net_annual_savings
        else:
            payback_years = float("inf")

        # 20-year Net Present Value (simplified, no discount rate for brevity)
        lifespan = min(m["lifespan_years"] for m in self.installed_measures)
        analysis_period = min(20, lifespan)
        total_net_savings_20yr = (
            net_annual_savings * analysis_period
        ) - total_installation_cost

        return {
            "baseline_temp_c": self.baseline_temp_c,
            "projected_temp_c": round(new_temp_c, 2),
            "total_cooling_effect_c": round(total_cooling_c, 2),
            "total_installation_cost_usd": round(total_installation_cost, 2),
            "annual_hvac_savings_usd": round(annual_hvac_savings_usd, 2),
            "total_annual_maintenance_usd": round(total_annual_maintenance, 2),
            "net_annual_savings_usd": round(net_annual_savings, 2),
            "payback_years": round(payback_years, 1)
            if payback_years != float("inf")
            else "Never",
            "twenty_year_net_savings_usd": round(total_net_savings_20yr, 2),
            "measure_breakdown": self.installed_measures,
        }

    def _empty_result(self) -> Dict[str, Any]:
        """Returns an empty result structure."""
        return {
            "baseline_temp_c": self.baseline_temp_c,
            "projected_temp_c": self.baseline_temp_c,
            "total_cooling_effect_c": 0.0,
            "total_installation_cost_usd": 0.0,
            "annual_hvac_savings_usd": 0.0,
            "total_annual_maintenance_usd": 0.0,
            "net_annual_savings_usd": 0.0,
            "payback_years": "N/A",
            "twenty_year_net_savings_usd": 0.0,
            "measure_breakdown": [],
        }
