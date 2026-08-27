import unittest
from src.carbon.industrial_carbon_capture_ccus import CCUSEngine

class TestIndustrialCarbonCaptureCCUS(unittest.TestCase):
    def setUp(self):
        self.engine = CCUSEngine()

    def test_initial_facilities_count(self):
        facs = self.engine.get_facilities()
        self.assertEqual(len(facs), 3)

    def test_sector_filtering(self):
        steel_facs = self.engine.get_facilities("Steel Mill")
        self.assertEqual(len(steel_facs), 1)
        self.assertEqual(steel_facs[0].industry_sector, "Steel Mill")

    def test_telemetry_calculations(self):
        telemetry = self.engine.calculate_total_telemetry()
        self.assertIn("total_daily_co2_captured_tons", telemetry)
        self.assertEqual(telemetry["total_daily_co2_captured_tons"], 2620.0)

    def test_facility_registration(self):
        new_fac = self.engine.register_facility(
            facility_name="Bavarian Glass Factory Capture Node",
            industry_sector="Chemical Refinery",
            capture_technology="Amine Absorption",
            flue_gas_flow_m3h=50000.0,
            co2_concentration_pct=15.0,
            sequestration_destination="Basalt Mineralization"
        )
        self.assertEqual(new_fac.facility_name, "Bavarian Glass Factory Capture Node")
        self.assertEqual(len(self.engine.facilities), 4)

    def test_credit_issuance(self):
        credit = self.engine.issue_carbon_offset_credit("ccus-101", 500.0)
        self.assertEqual(credit.verified_co2_tons, 500.0)
        self.assertEqual(credit.monetary_value_usd, 42500.0)

if __name__ == "__main__":
    unittest.main()
