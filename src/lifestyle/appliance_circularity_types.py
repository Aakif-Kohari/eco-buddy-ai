"""Domain models and dataclasses for Appliance Circularity & Repairability Lifecycle Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class ApplianceCategory(str, Enum):
    WASHING_MACHINE = "Washing Machine (Front/Top Load, Motor & Bearing Wear)"
    REFRIGERATOR = "Refrigerator / Freezer (Compressor & Refrigerant Circuit)"
    DISHWASHER = "Dishwasher (Circulation Pump & Electronic PCB)"
    HEAT_PUMP_AC = "Heat Pump / Air Conditioner (Inverter & Heat Exchanger)"
    LAPTOP_ELECTRONICS = "Laptop / Personal Computer (Battery, Display & Motherboard)"


class FailureSeverity(str, Enum):
    MINOR_WEAR = "Minor Cosmetic / Gasket / Filter Wear (Inexpensive DIY Fix)"
    MODERATE_MECHANICAL = "Motor / Pump / Mechanical Drive Issue (Standard Service)"
    CRITICAL_CORE = "Compressor / Motherboard / Structural Failure (Major Overhaul)"


@dataclass
class ApplianceAssessmentInputs:
    appliance_name: str
    category: ApplianceCategory
    age_years: float
    original_purchase_cost_usd: float
    estimated_repair_cost_usd: float
    new_replacement_cost_usd: float
    failure_severity: FailureSeverity
    manufacturer_spare_parts_years: float = 7.0
    repairability_index_score: float = 7.5  # 1.0 to 10.0 scale


@dataclass
class CircularityEvaluationResult:
    appliance_name: str
    recommended_decision: str  # "Repair & Extend Life" vs "Eco-Recycle & Replace"
    failure_probability_next_2yrs_pct: float
    residual_economic_value_usd: float
    embodied_carbon_saved_by_repair_kg: float
    repair_economic_payback_years: float
    lifecycle_circularity_score: float  # 0 to 100
    actionable_advice: str
