"""
Green Cloud & AI Workload Carbon Optimizer for EcoBuddy AI
Calculates cloud compute emissions, regional grid carbon intensity matching,
and delivers serverless/batch scheduling optimization.
"""

from typing import Dict, List, Any, Optional

CLOUD_REGION_CARBON_INTENSITY = {
    "us-east-1": {"name": "US East (N. Virginia)", "gco2_per_kwh": 379.0, "pue": 1.15},
    "us-west-2": {"name": "US West (Oregon)", "gco2_per_kwh": 120.0, "pue": 1.12},
    "eu-west-1": {"name": "Europe (Ireland)", "gco2_per_kwh": 286.0, "pue": 1.14},
    "eu-north-1": {"name": "Europe (Stockholm)", "gco2_per_kwh": 18.0, "pue": 1.09},
    "eu-central-1": {"name": "Europe (Frankfurt)", "gco2_per_kwh": 310.0, "pue": 1.16},
    "ap-southeast-1": {"name": "Asia Pacific (Singapore)", "gco2_per_kwh": 395.0, "pue": 1.20},
    "ap-south-1": {"name": "Asia Pacific (Mumbai)", "gco2_per_kwh": 708.0, "pue": 1.22},
    "ca-central-1": {"name": "Canada (Central - Hydro)", "gco2_per_kwh": 30.0, "pue": 1.10}
}

HARDWARE_POWER_SPECS = {
    "cpu_generic_core": {"watts_idle": 2.5, "watts_max": 10.0},
    "gpu_nvidia_t4": {"watts_idle": 15.0, "watts_max": 70.0},
    "gpu_nvidia_a100": {"watts_idle": 50.0, "watts_max": 400.0},
    "gpu_nvidia_h100": {"watts_idle": 70.0, "watts_max": 700.0},
    "memory_gb": {"watts": 0.38},
    "storage_ssd_tb": {"watts": 1.2}
}


class GreenCloudOptimizer:
    """Calculates IT compute workload carbon footprint and provides clean region migration recommendations."""

    def __init__(self, region_factors: Optional[Dict[str, Dict[str, Any]]] = None):
        self.regions = region_factors or CLOUD_REGION_CARBON_INTENSITY

    def estimate_workload_emissions(
        self,
        region: str,
        runtime_hours: float,
        cpu_cores: int = 4,
        gpu_type: Optional[str] = None,
        gpu_count: int = 0,
        avg_utilization_pct: float = 75.0,
        memory_gb: float = 16.0,
        storage_tb: float = 0.5
    ) -> Dict[str, Any]:
        """
        Estimates total kWh energy and kg CO2e for a given compute workload.
        """
        region_key = region.lower().strip()
        reg_info = self.regions.get(region_key, {"name": region, "gco2_per_kwh": 400.0, "pue": 1.2})

        util = min(max(avg_utilization_pct / 100.0, 0.05), 1.0)

        # CPU power consumption
        cpu_idle = HARDWARE_POWER_SPECS["cpu_generic_core"]["watts_idle"] * cpu_cores
        cpu_max = HARDWARE_POWER_SPECS["cpu_generic_core"]["watts_max"] * cpu_cores
        cpu_power_watts = cpu_idle + (cpu_max - cpu_idle) * util

        # GPU power consumption
        gpu_power_watts = 0.0
        if gpu_type and gpu_count > 0:
            gpu_spec = HARDWARE_POWER_SPECS.get(gpu_type.lower(), {"watts_idle": 20.0, "watts_max": 200.0})
            gpu_power_watts = (gpu_spec["watts_idle"] + (gpu_spec["watts_max"] - gpu_spec["watts_idle"]) * util) * gpu_count

        # Memory and Storage power
        mem_power_watts = memory_gb * HARDWARE_POWER_SPECS["memory_gb"]["watts"]
        storage_power_watts = storage_tb * HARDWARE_POWER_SPECS["storage_ssd_tb"]["watts"]

        total_server_watts = cpu_power_watts + gpu_power_watts + mem_power_watts + storage_power_watts
        total_facility_watts = total_server_watts * reg_info["pue"]

        total_kwh = round((total_facility_watts * runtime_hours) / 1000.0, 4)
        total_kg_co2 = round((total_kwh * reg_info["gco2_per_kwh"]) / 1000.0, 4)

        # Find best green region alternative
        cleanest_region_key = min(self.regions.keys(), key=lambda k: self.regions[k]["gco2_per_kwh"])
        cleanest_info = self.regions[cleanest_region_key]
        cleanest_kwh = round(((total_server_watts * cleanest_info["pue"]) * runtime_hours) / 1000.0, 4)
        cleanest_co2 = round((cleanest_kwh * cleanest_info["gco2_per_kwh"]) / 1000.0, 4)
        avoided_co2 = max(round(total_kg_co2 - cleanest_co2, 4), 0.0)

        return {
            "current_region": reg_info["name"],
            "runtime_hours": runtime_hours,
            "total_power_watts": round(total_facility_watts, 2),
            "energy_consumed_kwh": total_kwh,
            "emissions_kg_co2e": total_kg_co2,
            "cleanest_alternative_region": cleanest_info["name"],
            "cleanest_region_emissions_kg": cleanest_co2,
            "potential_savings_kg_co2e": avoided_co2,
            "savings_percentage": round((avoided_co2 / total_kg_co2 * 100) if total_kg_co2 > 0 else 0, 1)
        }

    def batch_schedule_recommendation(self, workload_type: str, flexible_window_hours: int = 12) -> Dict[str, Any]:
        """
        Provides intelligent scheduling recommendations to match low-carbon renewable generation windows.
        """
        recommendations = {
            "batch_analytics": {"best_window": "01:00 - 05:00 UTC (Off-peak wind surplus)", "curtailment_discount_pct": 35.0},
            "ai_model_training": {"best_window": "11:00 - 15:00 UTC (Solar peak / hydro dispatch)", "curtailment_discount_pct": 45.0},
            "ci_cd_pipelines": {"best_window": "Immediate with green-region dispatch", "curtailment_discount_pct": 20.0},
            "database_backups": {"best_window": "02:30 - 04:30 UTC", "curtailment_discount_pct": 30.0}
        }
        fallback = {"best_window": "Late night green grid hours (00:00 - 06:00 UTC)", "curtailment_discount_pct": 25.0}
        plan = recommendations.get(workload_type.lower().strip(), fallback)

        return {
            "workload_type": workload_type,
            "flexible_window_hours": flexible_window_hours,
            "recommended_dispatch_window": plan["best_window"],
            "projected_carbon_reduction_pct": plan["curtailment_discount_pct"]
        }
