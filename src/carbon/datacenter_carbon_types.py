"""Domain models and specifications for Data Center & AI Workload Carbon Profiler.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class GPUModel(str, Enum):
    NVIDIA_B200 = "NVIDIA Blackwell B200 (1000W TDP, 4.5 kg CO₂e embodied/hr)"
    NVIDIA_H100 = "NVIDIA H100 SXM (700W TDP, 3.2 kg CO₂e embodied/hr)"
    NVIDIA_A100 = "NVIDIA A100 SXM (400W TDP, 2.1 kg CO₂e embodied/hr)"
    NVIDIA_L40S = "NVIDIA L40S (350W TDP, 1.8 kg CO₂e embodied/hr)"
    GOOGLE_TPU_V5P = "Google TPU v5p (300W TDP, 1.5 kg CO₂e embodied/hr)"
    GOOGLE_TPU_V5E = "Google TPU v5e (250W TDP, 1.2 kg CO₂e embodied/hr)"
    AMD_MI300X = "AMD Instinct MI300X (750W TDP, 3.4 kg CO₂e embodied/hr)"
    AWS_TRAINIUM2 = "AWS Trainium2 (450W TDP, 2.0 kg CO₂e embodied/hr)"


class CloudRegion(str, Enum):
    US_EAST_VIRGINIA = "us-east-1 (N. Virginia, 370 g CO₂e/kWh, PUE 1.20)"
    US_WEST_OREGON = "us-west-2 (Oregon Hydro, 95 g CO₂e/kWh, PUE 1.12)"
    US_CENTRAL_IOWA = "us-central-1 (Iowa Wind/Solar, 180 g CO₂e/kWh, PUE 1.14)"
    EU_WEST_IRELAND = "eu-west-1 (Ireland Wind, 280 g CO₂e/kWh, PUE 1.18)"
    EU_NORTH_SWEDEN = "eu-north-1 (Stockholm Hydro/Nuclear, 25 g CO₂e/kWh, PUE 1.08)"
    EU_CENTRAL_FRANKFURT = "eu-central-1 (Frankfurt Grid Mix, 310 g CO₂e/kWh, PUE 1.19)"
    AP_SOUTH_MUMBAI = "ap-south-1 (Mumbai Coal/Solar, 680 g CO₂e/kWh, PUE 1.30)"
    AP_NORTHEAST_TOKYO = "ap-northeast-1 (Tokyo Grid Mix, 450 g CO₂e/kWh, PUE 1.22)"


class CoolingTechnology(str, Enum):
    DIRECT_TO_CHIP_LIQUID = "Direct-to-Chip Liquid Cooling (PUE 1.08, WUE 0.15 L/kWh)"
    REAR_DOOR_HEAT_EXCHANGER = "Rear-Door Heat Exchangers (PUE 1.15, WUE 0.35 L/kWh)"
    TRADITIONAL_CRAC_AIR = "Conventional CRAC Air Cooling (PUE 1.35, WUE 1.20 L/kWh)"
    TWO_PHASE_IMMERSION = "Two-Phase Immersion Cooling (PUE 1.03, WUE 0.02 L/kWh)"


@dataclass
class AIWorkloadParameters:
    job_name: str
    gpu_model: GPUModel
    gpu_count: int
    training_duration_hours: float
    average_gpu_utilization_pct: float
    cloud_region: CloudRegion
    cooling_tech: CoolingTechnology
    model_parameter_count_billions: float
    dataset_tokens_billions: float
    embodied_hardware_lifespan_years: float = 4.0
    carbon_offset_price_per_ton: float = 35.0


@dataclass
class OptimizationOpportunity:
    target_region: CloudRegion
    carbon_reduction_pct: float
    avoided_emissions_kg: float
    water_saved_liters: float
    net_cost_differential_usd: float


@dataclass
class AIWorkloadCarbonResult:
    job_name: str
    total_compute_energy_kwh: float
    total_facility_energy_kwh: float  # With PUE overhead
    effective_pue: float
    operational_emissions_kg_co2: float
    embodied_hardware_emissions_kg_co2: float
    total_footprint_kg_co2: float
    water_consumption_liters: float
    emissions_per_million_tokens_g: float
    carbon_offset_cost_usd: float
    green_region_alternatives: List[OptimizationOpportunity] = field(default_factory=list)
    hourly_profile: List[Dict[str, float]] = field(default_factory=list)
