"""
Unit and Integration Tests for Eco-Footprint Scenario Simulator
"""

import unittest
import os
from src.utils.eco_scenario_simulator_types import (
    FootprintScenario,
    ScenarioLever,
    ScenarioLeverCategory,
)
from src.utils.eco_scenario_simulator_db import (
    init_scenario_simulator_db,
    save_footprint_scenario,
    get_user_scenarios,
)
from src.utils.eco_scenario_simulator_service import FootprintScenarioSimulatorService

TEST_DB = "test_eco_scenario_simulator.db"


class TestScenarioSimulatorEngine(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        init_scenario_simulator_db(TEST_DB)
        self.service = FootprintScenarioSimulatorService(db_name=TEST_DB)

    def tearDown(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_lever_calculations(self):
        lever = ScenarioLever(
            name="EV Switch",
            category=ScenarioLeverCategory.TRANSPORT,
            baseline_value=10000.0,
            simulated_value=5000.0,
            unit="km",
            emission_factor_kg=0.19,
            description="Reduce gas car driving",
        )
        # Delta = (5000 - 10000) * 0.19 = -950.0 kg CO2
        self.assertEqual(lever.calculate_co2_delta_kg(), -950.0)

    def test_scenario_totals(self):
        levers = self.service.get_default_levers()
        scenario = FootprintScenario(
            id=None,
            user_id=1,
            scenario_name="Test Net Zero",
            description="Testing calculation totals",
            target_year=2030,
            levers=levers,
        )
        base = scenario.calculate_total_baseline_co2_kg()
        sim = scenario.calculate_total_simulated_co2_kg()
        self.assertGreater(base, sim)
        self.assertGreater(scenario.calculate_annual_reduction_pct(), 0.0)

    def test_projection_timeline(self):
        levers = self.service.get_default_levers()
        scenario = FootprintScenario(
            id=None,
            user_id=1,
            scenario_name="Timeline Test",
            description="Testing projections",
            target_year=2030,
            levers=levers,
        )
        projections = self.service.build_projection_timeline(scenario, start_year=2026)
        self.assertEqual(len(projections), 5)  # 2026, 2027, 2028, 2029, 2030
        self.assertEqual(projections[0].year, 2026)
        self.assertEqual(projections[-1].year, 2030)
        self.assertGreater(projections[-1].cumulative_savings_kg, 0)

    def test_db_persistence(self):
        levers = self.service.get_default_levers()
        scenario = FootprintScenario(
            id=None,
            user_id=1,
            scenario_name="Saved DB Test",
            description="Persistence verification",
            target_year=2035,
            levers=levers,
        )
        saved = self.service.save_scenario(scenario)
        self.assertIsNotNone(saved)
        self.assertIsNotNone(saved.id)

        user_scenarios = self.service.get_scenarios(user_id=1)
        self.assertEqual(len(user_scenarios), 1)
        self.assertEqual(user_scenarios[0].scenario_name, "Saved DB Test")


if __name__ == "__main__":
    unittest.main()
