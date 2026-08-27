"""
Eco-Footprint Scenario Simulator Data Types
Dataclasses, Enums, and structures for scenario parameters, lever adjustments, and projection outputs.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class ScenarioLeverCategory(str, Enum):
    TRANSPORT = "Transport"
    ENERGY = "Energy"
    DIET = "Diet"
    CONSUMPTION = "Consumption"


@dataclass
class ScenarioLever:
    name: str
    category: ScenarioLeverCategory
    baseline_value: float
    simulated_value: float
    unit: str
    emission_factor_kg: float
    description: str

    def calculate_co2_delta_kg(self) -> float:
        """Returns annual CO2 difference in kg (negative means reduction)."""
        return round((self.simulated_value - self.baseline_value) * self.emission_factor_kg, 2)


@dataclass
class FootprintScenario:
    id: Optional[int]
    user_id: int
    scenario_name: str
    description: str
    target_year: int
    levers: List[ScenarioLever]
    created_at: Optional[str] = None

    def calculate_total_baseline_co2_kg(self) -> float:
        return round(sum(l.baseline_value * l.emission_factor_kg for l in self.levers), 2)

    def calculate_total_simulated_co2_kg(self) -> float:
        return round(sum(l.simulated_value * l.emission_factor_kg for l in self.levers), 2)

    def calculate_annual_reduction_pct(self) -> float:
        base = self.calculate_total_baseline_co2_kg()
        if base <= 0:
            return 0.0
        sim = self.calculate_total_simulated_co2_kg()
        return round(((base - sim) / base) * 100.0, 1)


@dataclass
class ScenarioProjectionPoint:
    year: int
    baseline_co2_kg: float
    simulated_co2_kg: float
    cumulative_savings_kg: float
