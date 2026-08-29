"""Unit tests for Green Data Center and AI Carbon Profiler.
"""

import pytest
from src.carbon.datacenter_carbon_types import (
    AIWorkloadParameters,
    GPUModel,
    CloudRegion,
    CoolingTechnology,
)
from src.carbon.datacenter_carbon_engine import DataCenterCarbonEngine


@pytest.fixture
def baseline_ai_job():
    return AIWorkloadParameters(
        job_name="Test-LLM-Job",
        gpu_model=GPUModel.NVIDIA_H100,
        gpu_count=16,
        training_duration_hours=48.0,
        average_gpu_utilization_pct=90.0,
        cloud_region=CloudRegion.US_EAST_VIRGINIA,
        cooling_tech=CoolingTechnology.REAR_DOOR_HEAT_EXCHANGER,
        model_parameter_count_billions=70.0,
        dataset_tokens_billions=100.0,
    )


def test_workload_emissions_calculation(baseline_ai_job):
    result = DataCenterCarbonEngine.calculate_workload_emissions(baseline_ai_job)

    assert result.total_compute_energy_kwh > 0.0
    assert result.total_facility_energy_kwh > result.total_compute_energy_kwh
    assert result.operational_emissions_kg_co2 > 0.0
    assert result.embodied_hardware_emissions_kg_co2 > 0.0
    assert result.total_footprint_kg_co2 == pytest.approx(
        result.operational_emissions_kg_co2 + result.embodied_hardware_emissions_kg_co2, rel=1e-2
    )
    assert result.water_consumption_liters > 0.0
    assert result.emissions_per_million_tokens_g > 0.0
    assert len(result.green_region_alternatives) > 0


def test_liquid_vs_air_cooling_pue():
    job_air = AIWorkloadParameters(
        job_name="Air",
        gpu_model=GPUModel.NVIDIA_A100,
        gpu_count=8,
        training_duration_hours=24.0,
        average_gpu_utilization_pct=80.0,
        cloud_region=CloudRegion.US_EAST_VIRGINIA,
        cooling_tech=CoolingTechnology.TRADITIONAL_CRAC_AIR,
        model_parameter_count_billions=7.0,
        dataset_tokens_billions=10.0,
    )
    job_liquid = AIWorkloadParameters(
        job_name="Liquid",
        gpu_model=GPUModel.NVIDIA_A100,
        gpu_count=8,
        training_duration_hours=24.0,
        average_gpu_utilization_pct=80.0,
        cloud_region=CloudRegion.US_EAST_VIRGINIA,
        cooling_tech=CoolingTechnology.DIRECT_TO_CHIP_LIQUID,
        model_parameter_count_billions=7.0,
        dataset_tokens_billions=10.0,
    )

    res_air = DataCenterCarbonEngine.calculate_workload_emissions(job_air)
    res_liquid = DataCenterCarbonEngine.calculate_workload_emissions(job_liquid)

    assert res_liquid.effective_pue < res_air.effective_pue
    assert res_liquid.total_facility_energy_kwh < res_air.total_facility_energy_kwh
    assert res_liquid.water_consumption_liters < res_air.water_consumption_liters


def test_hydro_region_carbon_reduction(baseline_ai_job):
    result = DataCenterCarbonEngine.calculate_workload_emissions(baseline_ai_job)
    sweden_opt = next((opt for opt in result.green_region_alternatives if "sweden" in str(opt.target_region).lower()), None)
    assert sweden_opt is not None
    assert sweden_opt.carbon_reduction_pct > 50.0
