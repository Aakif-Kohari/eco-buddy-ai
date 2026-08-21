import unittest
from circular_economy_marketplace import CircularEconomyEngine

class TestCircularEconomyMarketplace(unittest.TestCase):
    def setUp(self):
        self.engine = CircularEconomyEngine()

    def test_initial_listings_count(self):
        listings = self.engine.get_listings()
        self.assertEqual(len(listings), 3)

    def test_category_filtering(self):
        polymers = self.engine.get_listings("Recycled Polymer Plastic")
        self.assertEqual(len(polymers), 1)
        self.assertEqual(polymers[0].category, "Recycled Polymer Plastic")

    def test_marketplace_impact_calculation(self):
        impact = self.engine.calculate_marketplace_impact()
        self.assertIn("available_secondary_materials_tons", impact)
        self.assertEqual(impact["available_secondary_materials_tons"], 605.0)

    def test_register_listing(self):
        new_mat = self.engine.register_listing(
            material_name="Recycled Bio-Polymer Granules",
            category="Recycled Polymer Plastic",
            purity_grade_pct=98.0,
            quantity_metric_tons=200.0,
            unit_price_usd_ton=1100.0,
            seller_facility_name="EcoPlast Refining Corp"
        )
        self.assertEqual(new_mat.material_name, "Recycled Bio-Polymer Granules")
        self.assertEqual(len(self.engine.listings), 4)

    def test_execute_purchase(self):
        tx = self.engine.execute_circular_purchase("mat-101", "Global Packaging Solutions Ltd", 50.0)
        self.assertEqual(tx.purchased_quantity_tons, 50.0)
        self.assertEqual(tx.total_cost_usd, 62500.0)

if __name__ == "__main__":
    unittest.main()
