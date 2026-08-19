"""
Unit tests for the Circular Economy & Upcycling Module
"""

import unittest
from src.lib.circular_economy import CircularEconomyEngine, MATERIAL_CIRCULARITY_FACTORS, UPCYCLING_IDEAS

class TestCircularEconomyEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CircularEconomyEngine()

    def test_calculate_circularity_score_valid(self):
        res = self.engine.calculate_circularity_score(
            category="electronics",
            current_age_years=2.0,
            expected_lifespan_years=4.0,
            condition_rating=4,
            repair_attempts=1
        )
        self.assertIn("circularity_index", res)
        self.assertGreaterEqual(res["circularity_index"], 0.0)
        self.assertLessEqual(res["circularity_index"], 100.0)
        self.assertGreater(res["retained_embodied_co2_kg"], 0.0)
        self.assertIn("recommended_pathway", res)
        self.assertTrue(len(res["upcycling_recommendations"]) > 0)

    def test_condition_pathways(self):
        res_high = self.engine.calculate_circularity_score(
            category="furniture_wood",
            current_age_years=1.0,
            expected_lifespan_years=10.0,
            condition_rating=5
        )
        self.assertEqual(res_high["recommended_pathway"], "Direct Reuse / Resell / Community Exchange")

        res_low = self.engine.calculate_circularity_score(
            category="plastics",
            current_age_years=5.0,
            expected_lifespan_years=2.0,
            condition_rating=1
        )
        self.assertEqual(res_low["recommended_pathway"], "Material Harvesting & High-Grade Recycling")

    def test_batch_exchange_impact(self):
        items = [
            {"category": "textiles", "age_years": 1.0, "expected_lifespan_years": 2.0, "condition": 4, "repairs": 0},
            {"category": "metals", "age_years": 3.0, "expected_lifespan_years": 5.0, "condition": 3, "repairs": 1}
        ]
        batch = self.engine.assess_item_exchange_impact(items)
        self.assertEqual(batch["total_items"], 2)
        self.assertGreater(batch["total_co2_saved_kg"], 0.0)
        self.assertGreater(batch["total_embodied_retained_kg"], 0.0)
        self.assertIn("textiles", batch["category_breakdown"])

    def test_empty_batch(self):
        batch = self.engine.assess_item_exchange_impact([])
        self.assertEqual(batch["total_items"], 0)
        self.assertEqual(batch["total_co2_saved_kg"], 0.0)

if __name__ == "__main__":
    unittest.main()
