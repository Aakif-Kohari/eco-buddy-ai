"""
Unit tests for the Microgrid & Battery Energy Storage (BESS) Simulator
"""

import unittest
from src.lib.microgrid_simulator import MicrogridStorageSimulator, BATTERY_CHEMISTRIES

class TestMicrogridStorageSimulator(unittest.TestCase):

    def setUp(self):
        self.simulator = MicrogridStorageSimulator()

    def test_simulate_daily_dispatch_with_battery(self):
        res = self.simulator.simulate_daily_dispatch(
            solar_capacity_kw=5.0,
            battery_capacity_kwh=10.0,
            daily_consumption_kwh=20.0,
            battery_chemistry="lfp"
        )
        self.assertIn("self_sufficiency_pct", res)
        self.assertGreater(res["self_sufficiency_pct"], 0.0)
        self.assertGreater(res["annual_financial_savings_usd"], 0.0)
        self.assertGreater(res["annual_carbon_abatement_kg"], 0.0)
        self.assertGreater(res["battery_discharged_kwh"], 0.0)

    def test_simulate_daily_dispatch_zero_battery(self):
        res = self.simulator.simulate_daily_dispatch(
            solar_capacity_kw=5.0,
            battery_capacity_kwh=0.0,
            daily_consumption_kwh=20.0
        )
        self.assertEqual(res["battery_discharged_kwh"], 0.0)
        self.assertGreater(res["direct_solar_consumed_kwh"], 0.0)

    def test_battery_chemistry_lifespan(self):
        res_lfp = self.simulator.simulate_daily_dispatch(5.0, 10.0, 20.0, "lfp")
        res_nmc = self.simulator.simulate_daily_dispatch(5.0, 10.0, 20.0, "nmc")
        self.assertGreater(res_lfp["expected_battery_lifespan_years"], res_nmc["expected_battery_lifespan_years"])

if __name__ == "__main__":
    unittest.main()
