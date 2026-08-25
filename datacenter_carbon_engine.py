"""Carbon and Water accounting engine for AI Workloads and Green Data Centers.

Calculates:
- Operational Scope 2 emissions based on regional marginal grid carbon intensity
- Scope 3 hardware manufacturing LCA embodied footprint
- PUE and WUE thermodynamic overhead multipliers
- Optimal low-carbon spatial & temporal compute rescheduling opportunities
"""

import math
from typing import Dict, List
from datacenter_carbon_types import (
    AIWorkloadParameters,
    AIWorkloadCarbonResult,
    GPUModel,
    CloudRegion,
    CoolingTechnology,
    OptimizationOpportunity,
)


class DataCenterCarbonEngine:
    GPU_SPECS = {
        GPUModel.NVIDIA_H100: {"tdp_w": 700.0, "embodied_kg": 150.0, "flops_fp16_tflops": 1979.0},
        GPUModel.NVIDIA_A100: {"tdp_w": 400.0, "embodied_kg": 110.0, "flops_fp16_tflops": 312.0},
        GPUModel.NVIDIA_L40S: {"tdp_w": 350.0, "embodied_kg": 95.0, "flops_fp16_tflops": 366.0},
        GPUModel.GOOGLE_TPU_V5E: {"tdp_w": 250.0, "embodied_kg": 75.0, "flops_fp16_tflops": 197.0},
        GPUModel.AMD_MI300X: {"tdp_w": 750.0, "embodied_kg": 160.0, "flops_fp16_tflops": 2614.0},
    }

    REGION_GRID_DATA = {
        CloudRegion.US_EAST_VIRGINIA: {"intensity_g_kwh": 370.0, "base_pue": 1.20, "cost_kwh": 0.11},
        CloudRegion.US_WEST_OREGON: {"intensity_g_kwh": 95.0, "base_pue": 1.12, "cost_kwh": 0.09},
        CloudRegion.EU_WEST_IRELAND: {"intensity_g_kwh": 280.0, "base_pue": 1.18, "cost_kwh": 0.16},
        CloudRegion.EU_NORTH_SWEDEN: {"intensity_g_kwh": 25.0, "base_pue": 1.08, "cost_kwh": 0.08},
        CloudRegion.AP_SOUTH_MUMBAI: {"intensity_g_kwh": 680.0, "base_pue": 1.30, "cost_kwh": 0.12},
    }

    COOLING_FACTORS = {
        CoolingTechnology.DIRECT_TO_CHIP_LIQUID: {"pue_delta": -0.05, "wue_l_kwh": 0.15},
        CoolingTechnology.REAR_DOOR_HEAT_EXCHANGER: {"pue_delta": 0.0, "wue_l_kwh": 0.35},
        CoolingTechnology.TRADITIONAL_CRAC_AIR: {"pue_delta": 0.15, "wue_l_kwh": 1.20},
        CoolingTechnology.TWO_PHASE_IMMERSION: {"pue_delta": -0.09, "wue_l_kwh": 0.02},
    }

    @classmethod
    def calculate_workload_emissions(cls, params: AIWorkloadParameters) -> AIWorkloadCarbonResult:
        gpu = cls.GPU_SPECS.get(params.gpu_model, cls.GPU_SPECS[GPUModel.NVIDIA_A100])
        region = cls.REGION_GRID_DATA.get(params.cloud_region, cls.REGION_GRID_DATA[CloudRegion.US_EAST_VIRGINIA])
        cooling = cls.COOLING_FACTORS.get(params.cooling_tech, cls.COOLING_FACTORS[CoolingTechnology.REAR_DOOR_HEAT_EXCHANGER])

        # Server chassis + CPU/RAM power overhead (estimated 25% over GPU TDP)
        active_gpu_w = gpu["tdp_w"] * (params.average_gpu_utilization_pct / 100.0)
        total_rack_power_w = params.gpu_count * (active_gpu_w * 1.25)
        compute_energy_kwh = (total_rack_power_w * params.training_duration_hours) / 1000.0

        # PUE adjusted for cooling technology
        effective_pue = max(1.02, region["base_pue"] + cooling["pue_delta"])
        total_facility_energy_kwh = compute_energy_kwh * effective_pue

        # Scope 2 Operational emissions (kg CO2e)
        operational_co2_kg = (total_facility_energy_kwh * region["intensity_g_kwh"]) / 1000.0

        # Scope 3 Embodied hardware emissions amortized over hours
        lifespan_hours = params.embodied_hardware_lifespan_years * 365.25 * 24.0
        embodied_co2_kg = (params.gpu_count * gpu["embodied_kg"] * (params.training_duration_hours / lifespan_hours))

        total_co2_kg = operational_co2_kg + embodied_co2_kg

        # Water consumption (WUE L/kWh * total facility energy)
        water_liters = total_facility_energy_kwh * cooling["wue_l_kwh"]

        # Token metrics
        total_tokens_millions = params.dataset_tokens_billions * 1000.0
        emissions_per_million_tokens = (total_co2_kg * 1000.0) / max(1.0, total_tokens_millions)

        offset_cost = (total_co2_kg / 1000.0) * params.carbon_offset_price_per_ton

        # Alternative region evaluations
        alternatives: List[OptimizationOpportunity] = []
        for r_name, r_data in cls.REGION_GRID_DATA.items():
            if r_name == params.cloud_region:
                continue
            alt_pue = max(1.02, r_data["base_pue"] + cooling["pue_delta"])
            alt_facility_kwh = compute_energy_kwh * alt_pue
            alt_op_co2 = (alt_facility_kwh * r_data["intensity_g_kwh"]) / 1000.0
            alt_tot_co2 = alt_op_co2 + embodied_co2_kg

            co2_saved_kg = max(0.0, total_co2_kg - alt_tot_co2)
            pct_reduction = (co2_saved_kg / max(1.0, total_co2_kg)) * 100.0
            alt_water = alt_facility_kwh * cooling["wue_l_kwh"]
            water_saved = max(0.0, water_liters - alt_water)

            cost_diff = (alt_facility_kwh * r_data["cost_kwh"]) - (total_facility_energy_kwh * region["cost_kwh"])

            if pct_reduction > 0:
                alternatives.append(
                    OptimizationOpportunity(
                        target_region=r_name,
                        carbon_reduction_pct=round(pct_reduction, 1),
                        avoided_emissions_kg=round(co2_saved_kg, 1),
                        water_saved_liters=round(water_saved, 1),
                        net_cost_differential_usd=round(cost_diff, 2),
                    )
                )

        # Sort alternatives by emission reduction
        alternatives.sort(key=lambda x: x.carbon_reduction_pct, reverse=True)

        # Synthetic hourly breakdown
        hourly_profile = []
        for h in range(min(24, int(params.training_duration_hours))):
            diurnal_var = 1.0 + 0.12 * math.sin((h - 8) * math.pi / 12.0)
            h_co2 = (operational_co2_kg / max(1, params.training_duration_hours)) * diurnal_var
            hourly_profile.append({"hour": h, "co2_kg": round(h_co2, 2)})

        return AIWorkloadCarbonResult(
            job_name=params.job_name,
            total_compute_energy_kwh=round(compute_energy_kwh, 1),
            total_facility_energy_kwh=round(total_facility_energy_kwh, 1),
            effective_pue=round(effective_pue, 3),
            operational_emissions_kg_co2=round(operational_co2_kg, 1),
            embodied_hardware_emissions_kg_co2=round(embodied_co2_kg, 1),
            total_footprint_kg_co2=round(total_co2_kg, 1),
            water_consumption_liters=round(water_liters, 1),
            emissions_per_million_tokens_g=round(emissions_per_million_tokens, 2),
            carbon_offset_cost_usd=round(offset_cost, 2),
            green_region_alternatives=alternatives,
            hourly_profile=hourly_profile,
        )
