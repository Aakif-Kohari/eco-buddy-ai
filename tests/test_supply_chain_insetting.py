"""
Unit tests for the Scope 3 Supply Chain Insetting & Decarbonization Planner
"""

import unittest
from src.lib.supply_chain_insetting import SupplyChainInsettingPlanner, SCOPE3_CATEGORIES, INSETTING_INTERVENTIONS

class TestSupplyChainInsettingPlanner(unittest.TestCase):

    def setUp(self):
        self.planner = SupplyChainInsettingPlanner()

    def test_calculate_category_emissions(self):
        res = self.planner.calculate_category_emissions(
            category_key="cat1_purchased_goods",
            activity_amount=10000.0,
            supplier_primary_data_discount_pct=20.0
        )
        self.assertIn("adjusted_emissions_tco2e", res)
        self.assertLess(res["adjusted_emissions_tco2e"], res["raw_emissions_tco2e"])
        self.assertEqual(res["primary_data_confidence"], "High (Direct Supplier Audited)")

    def test_evaluate_insetting_intervention_funded(self):
        res = self.planner.evaluate_insetting_intervention(
            intervention_type="regenerative_agriculture",
            target_abatement_tonnes=100.0,
            co_investment_budget=3000.0
        )
        self.assertTrue(res["is_fully_funded"])
        self.assertEqual(res["funding_gap_usd"], 0.0)
        self.assertEqual(res["total_estimated_project_cost_usd"], 2500.0)
        self.assertGreater(len(res["co_benefits"]), 0)

    def test_evaluate_insetting_intervention_gap(self):
        res = self.planner.evaluate_insetting_intervention(
            intervention_type="bio_based_packaging_feedstock",
            target_abatement_tonnes=50.0,
            co_investment_budget=1000.0
        )
        self.assertFalse(res["is_fully_funded"])
        self.assertGreater(res["funding_gap_usd"], 0.0)

if __name__ == "__main__":
    unittest.main()
