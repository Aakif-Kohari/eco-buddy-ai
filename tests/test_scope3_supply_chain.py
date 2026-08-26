import unittest
from scope3_supply_chain import Scope3SupplyChainEngine

class TestScope3SupplyChain(unittest.TestCase):
    def setUp(self):
        self.engine = Scope3SupplyChainEngine()

    def test_initial_suppliers_count(self):
        suppliers = self.engine.get_suppliers()
        self.assertEqual(len(suppliers), 3)

    def test_tier_filtering(self):
        tier1 = self.engine.get_suppliers("Tier-1 Direct Supplier")
        self.assertEqual(len(tier1), 2)

    def test_summary_calculation(self):
        summary = self.engine.calculate_scope3_summary()
        self.assertIn("total_procurement_spend_usd", summary)
        self.assertEqual(summary["total_allocated_scope3_emissions_tons"], 13160.0)

    def test_register_supplier(self):
        new_sup = self.engine.register_supplier(
            vendor_name="Kyoto Resin Chemical Works",
            tier_level="Tier-1 Direct Supplier",
            procurement_category="Chemical Synthesis",
            annual_spend_usd=5000000.0,
            carbon_intensity_kg_co2_per_usd=0.50,
            sbti_netzero_committed=True
        )
        self.assertEqual(new_sup.vendor_name, "Kyoto Resin Chemical Works")
        self.assertEqual(len(self.engine.suppliers), 4)

    def test_initiate_engagement(self):
        eng = self.engine.initiate_decarbonization_engagement("sup-101", 25.0, 200000.0)
        self.assertEqual(eng.target_reduction_pct, 25.0)
        self.assertEqual(eng.allocated_grant_usd, 200000.0)

if __name__ == "__main__":
    unittest.main()
