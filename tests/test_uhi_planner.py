"""
Unit tests for the Urban Heat Island & Tree Canopy Microclimate Planner
"""

import unittest
from src.lib.uhi_planner import UrbanHeatIslandPlanner

class TestUrbanHeatIslandPlanner(unittest.TestCase):

    def setUp(self):
        self.planner = UrbanHeatIslandPlanner()

    def test_calculate_microclimate_cooling(self):
        res = self.planner.calculate_microclimate_cooling(
            district_area_sqm=100000.0,
            impervious_pct=60.0,
            current_canopy_pct=15.0,
            proposed_canopy_addition_pct=10.0,
            baseline_ambient_temp_c=32.0
        )
        self.assertIn("ambient_cooling_delta_c", res)
        self.assertGreater(res["ambient_cooling_delta_c"], 0.0)
        self.assertLess(res["projected_district_temp_c"], res["current_district_temp_c"])
        self.assertGreater(res["hvac_energy_savings_pct"], 0.0)
        self.assertGreater(res["estimated_trees_planted"], 0)
        self.assertGreater(res["annual_co2_sequestered_kg"], 0.0)

    def test_extreme_impervious_cooling(self):
        res_high_paved = self.planner.calculate_microclimate_cooling(10000.0, 90.0, 5.0, 20.0)
        res_low_paved = self.planner.calculate_microclimate_cooling(10000.0, 20.0, 5.0, 20.0)
        self.assertGreater(res_high_paved["ambient_cooling_delta_c"], res_low_paved["ambient_cooling_delta_c"])

if __name__ == "__main__":
    unittest.main()
