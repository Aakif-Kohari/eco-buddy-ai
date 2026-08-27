import unittest
from smart_grid_ev_v2g import SmartEVV2GEngine

class TestSmartEVV2G(unittest.TestCase):
    def setUp(self):
        self.engine = SmartEVV2GEngine()

    def test_initial_chargers_count(self):
        chargers = self.engine.get_chargers()
        self.assertEqual(len(chargers), 3)

    def test_charger_type_filtering(self):
        v2g_chargers = self.engine.get_chargers("V2G Bi-Directional Hub 50kW")
        self.assertEqual(len(v2g_chargers), 2)

    def test_fleet_metrics_calculation(self):
        metrics = self.engine.calculate_fleet_metrics()
        self.assertIn("total_charging_power_kw", metrics)
        self.assertEqual(metrics["total_charging_power_kw"], 120.0)
        self.assertEqual(metrics["total_v2g_discharge_power_kw"], 95.0)

    def test_register_charger(self):
        new_ch = self.engine.register_charger(
            station_name="Airport Express EV Fleet Hub",
            charger_type="V2G Bi-Directional Hub 50kW",
            connected_vehicle_model="Hyundai Ioniq 6",
            battery_capacity_kwh=77.4,
            current_soc_pct=85.0,
            v2g_enabled=True
        )
        self.assertEqual(new_ch.station_name, "Airport Express EV Fleet Hub")
        self.assertEqual(len(self.engine.chargers), 4)

    def test_v2g_dispatch(self):
        record = self.engine.trigger_v2g_peak_shaving("ch-101", 50.0)
        self.assertEqual(record.discharged_energy_kwh, 50.0)
        self.assertEqual(record.grid_tariff_earned_usd, 16.0)

if __name__ == "__main__":
    unittest.main()
