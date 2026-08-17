"""
Unit tests for the Green Cloud & AI Workload Carbon Optimizer
"""

import unittest
from src.lib.green_cloud import GreenCloudOptimizer, CLOUD_REGION_CARBON_INTENSITY

class TestGreenCloudOptimizer(unittest.TestCase):

    def setUp(self):
        self.optimizer = GreenCloudOptimizer()

    def test_estimate_workload_emissions_cpu(self):
        res = self.optimizer.estimate_workload_emissions(
            region="us-east-1",
            runtime_hours=10.0,
            cpu_cores=8,
            avg_utilization_pct=80.0,
            memory_gb=32.0,
            storage_tb=1.0
        )
        self.assertIn("energy_consumed_kwh", res)
        self.assertGreater(res["energy_consumed_kwh"], 0.0)
        self.assertGreater(res["emissions_kg_co2e"], 0.0)
        self.assertIn("cleanest_alternative_region", res)
        self.assertGreaterEqual(res["potential_savings_kg_co2e"], 0.0)

    def test_estimate_workload_emissions_gpu(self):
        res = self.optimizer.estimate_workload_emissions(
            region="ap-south-1",
            runtime_hours=5.0,
            cpu_cores=16,
            gpu_type="gpu_nvidia_a100",
            gpu_count=4,
            avg_utilization_pct=90.0
        )
        self.assertGreater(res["total_power_watts"], 500.0)
        self.assertGreater(res["savings_percentage"], 50.0)

    def test_batch_schedule_recommendation(self):
        res = self.optimizer.batch_schedule_recommendation("ai_model_training", flexible_window_hours=24)
        self.assertIn("recommended_dispatch_window", res)
        self.assertGreater(res["projected_carbon_reduction_pct"], 0.0)

if __name__ == "__main__":
    unittest.main()
