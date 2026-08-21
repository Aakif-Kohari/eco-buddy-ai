import unittest
import pandas as pd
from renewable_microgrid_vpp import MicrogridVPPEngine, MicrogridAsset

class TestRenewableMicrogridVPP(unittest.TestCase):
    def setUp(self):
        self.engine = MicrogridVPPEngine()

    def test_initial_asset_balance(self):
        balance = self.engine.calculate_current_balance()
        self.assertIn("total_generation_kw", balance)
        self.assertIn("total_load_kw", balance)
        self.assertIn("net_power_kw", balance)
        self.assertEqual(balance["total_generation_kw"], 460.0)
        self.assertEqual(balance["total_load_kw"], 410.0)
        self.assertEqual(balance["net_power_kw"], 50.0)

    def test_add_asset(self):
        new_asset = MicrogridAsset("solar-2", "Expansion Solar Field", "Solar PV", 300.0, 200.0)
        self.engine.add_asset(new_asset)
        balance = self.engine.calculate_current_balance()
        self.assertEqual(balance["total_generation_kw"], 660.0)

    def test_24h_vpp_simulation_length(self):
        schedule = self.engine.simulate_24h_vpp_schedule(bess_capacity_kwh=1000.0, initial_soc_pct=50.0)
        self.assertEqual(len(schedule), 24)
        self.assertEqual(schedule[0].hour, 0)
        self.assertEqual(schedule[23].hour, 23)

    def test_carbon_arbitrage_toggle(self):
        schedule_enabled = self.engine.simulate_24h_vpp_schedule(enable_carbon_arbitrage=True)
        schedule_disabled = self.engine.simulate_24h_vpp_schedule(enable_carbon_arbitrage=False)
        self.assertEqual(len(schedule_enabled), 24)
        self.assertEqual(len(schedule_disabled), 24)

if __name__ == "__main__":
    unittest.main()
