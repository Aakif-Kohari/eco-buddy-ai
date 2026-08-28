"""
Eco-Footprint Scenario Simulator Core Service Layer
Encapsulates scenario calculations, multi-year linear/exponential forecasting models, and lever impact ranking.
"""

from typing import List, Dict, Any, Optional
import logging

from src.utils.eco_scenario_simulator_types import (
    FootprintScenario,
    ScenarioLever,
    ScenarioLeverCategory,
    ScenarioProjectionPoint,
)
from src.utils.eco_scenario_simulator_db import (
    init_scenario_simulator_db,
    save_footprint_scenario,
    get_user_scenarios,
)

logger = logging.getLogger(__name__)


class FootprintScenarioSimulatorService:
    def __init__(self, db_name: str = "eco_buddy.db"):
        self.db_name = db_name
        init_scenario_simulator_db(self.db_name)

    def get_default_levers(self) -> List[ScenarioLever]:
        """Provides default lifestyle levers for scenario creation."""
        return [
            ScenarioLever("Car Commute Distance", ScenarioLeverCategory.TRANSPORT, 12000.0, 6000.0, "km/yr", 0.19, "Switch half of driving to remote work / transit"),
            ScenarioLever("Gasoline Vehicle Share", ScenarioLeverCategory.TRANSPORT, 1.0, 0.0, "ratio", 1200.0, "Transition from gas vehicle to EV"),
            ScenarioLever("Home Electricity Use", ScenarioLeverCategory.ENERGY, 4500.0, 3000.0, "kWh/yr", 0.45, "Efficiency upgrades & LED lighting"),
            ScenarioLever("Grid Electricity Share", ScenarioLeverCategory.ENERGY, 1.0, 0.2, "share", 1800.0, "Install residential solar power to reduce grid reliance"),
            ScenarioLever("Animal-Based Meal Ratio", ScenarioLeverCategory.DIET, 0.8, 0.3, "share", 950.0, "Shift diet away from high-impact animal products"),
            ScenarioLever("Fast Fashion Purchase Count", ScenarioLeverCategory.CONSUMPTION, 20.0, 5.0, "items/yr", 14.5, "Buy sustainable / second-hand apparel"),
        ]

    def build_projection_timeline(self, scenario: FootprintScenario, start_year: int = 2026) -> List[ScenarioProjectionPoint]:
        """Generates year-by-year carbon trajectory from start_year to target_year."""
        target_year = max(start_year + 1, scenario.target_year)
        total_years = target_year - start_year

        base_annual = scenario.calculate_total_baseline_co2_kg()
        sim_annual = scenario.calculate_total_simulated_co2_kg()
        annual_diff = base_annual - sim_annual

        projections = []
        cumulative_saved = 0.0

        for idx in range(total_years + 1):
            yr = start_year + idx
            progress_ratio = idx / total_years
            # Linear transition model
            current_sim_annual = base_annual - (annual_diff * progress_ratio)
            saved_this_year = base_annual - current_sim_annual
            cumulative_saved += saved_this_year

            projections.append(ScenarioProjectionPoint(
                year=yr,
                baseline_co2_kg=round(base_annual, 2),
                simulated_co2_kg=round(current_sim_annual, 2),
                cumulative_savings_kg=round(cumulative_saved, 2),
            ))

        return projections

    def save_scenario(self, scenario: FootprintScenario) -> Optional[FootprintScenario]:
        return save_footprint_scenario(scenario, self.db_name)

    def get_scenarios(self, user_id: int) -> List[FootprintScenario]:
        return get_user_scenarios(user_id, self.db_name)
