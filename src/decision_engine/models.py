"""
Decision Simulator Data Models.

Contains the comprehensive definitions of all data structures used by the
Personal Sustainability Decision Simulator & Trade-off Analysis Engine.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import json

class TransportMode(str, Enum):
    WALKING = "walking"
    CYCLING = "cycling"
    PUBLIC_TRANSIT = "public_transit"
    ICE_CAR = "ice_car"
    EV_CAR = "ev_car"
    HYBRID_CAR = "hybrid_car"
    CARPOOL = "carpool"
    MOTORCYCLE = "motorcycle"
    E_BIKE = "e_bike"

class EnergySource(str, Enum):
    GRID_DEFAULT = "grid_default"
    GRID_RENEWABLE = "grid_renewable"
    SOLAR_ROOF = "solar_roof"
    WIND_LOCAL = "wind_local"
    GEOTHERMAL = "geothermal"

class DietType(str, Enum):
    MEAT_HEAVY = "meat_heavy"
    OMNIVORE = "omnivore"
    PESCATARIAN = "pescatarian"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    FLEXITARIAN = "flexitarian"
    LOCAL_SOURCED = "local_sourced"

@dataclass
class TransportInputs:
    primary_mode: TransportMode = TransportMode.ICE_CAR
    weekly_commute_km: float = 100.0
    weekend_travel_km: float = 50.0
    flights_per_year: int = 1
    car_efficiency_mpg: float = 25.0
    ev_efficiency_kwh_per_100km: float = 15.0
    carpool_passengers: int = 1
    public_transit_type: str = "bus"
    telecommute_days_per_week: int = 0
    vehicle_age_years: int = 5
    annual_maintenance_cost: float = 500.0

@dataclass
class EnergyInputs:
    primary_source: EnergySource = EnergySource.GRID_DEFAULT
    monthly_electricity_kwh: float = 300.0
    monthly_gas_therms: float = 20.0
    thermostat_winter_c: float = 21.0
    thermostat_summer_c: float = 22.0
    has_smart_thermostat: bool = False
    led_lighting_percentage: float = 50.0
    appliance_efficiency_rating: str = "average"
    hvac_age_years: int = 10
    insulation_quality: str = "average"
    solar_capacity_kw: float = 0.0

@dataclass
class FoodInputs:
    diet_type: DietType = DietType.OMNIVORE
    food_waste_percentage: float = 20.0
    composting_enabled: bool = False
    local_food_percentage: float = 10.0
    organic_food_percentage: float = 10.0
    dining_out_frequency_per_week: int = 3
    grocery_budget_monthly: float = 400.0

@dataclass
class WasteInputs:
    weekly_trash_bags: float = 3.0
    recycling_rate_percentage: float = 30.0
    single_use_plastics_per_week: int = 15
    repairs_vs_replace_ratio: float = 0.2
    second_hand_purchases_percentage: float = 10.0

@dataclass
class WaterInputs:
    shower_duration_minutes: float = 10.0
    low_flow_fixtures_installed: bool = False
    weekly_laundry_loads: int = 4
    dishwasher_usage_per_week: int = 4
    lawn_watering_hours_per_week: float = 2.0
    rainwater_harvesting_liters: float = 0.0

@dataclass
class ScenarioInputs:
    transport: TransportInputs = field(default_factory=TransportInputs)
    energy: EnergyInputs = field(default_factory=EnergyInputs)
    food: FoodInputs = field(default_factory=FoodInputs)
    waste: WasteInputs = field(default_factory=WasteInputs)
    water: WaterInputs = field(default_factory=WaterInputs)

@dataclass
class EnvironmentalImpact:
    carbon_emissions_kg_co2e_per_year: float = 0.0
    energy_consumption_kwh_per_year: float = 0.0
    water_footprint_liters_per_year: float = 0.0
    waste_generation_kg_per_year: float = 0.0
    sustainability_score: float = 0.0
    
    transport_co2e: float = 0.0
    energy_co2e: float = 0.0
    food_co2e: float = 0.0
    waste_co2e: float = 0.0
    
    def __sub__(self, other: 'EnvironmentalImpact') -> 'EnvironmentalImpact':
        return EnvironmentalImpact(
            carbon_emissions_kg_co2e_per_year=self.carbon_emissions_kg_co2e_per_year - other.carbon_emissions_kg_co2e_per_year,
            energy_consumption_kwh_per_year=self.energy_consumption_kwh_per_year - other.energy_consumption_kwh_per_year,
            water_footprint_liters_per_year=self.water_footprint_liters_per_year - other.water_footprint_liters_per_year,
            waste_generation_kg_per_year=self.waste_generation_kg_per_year - other.waste_generation_kg_per_year,
            sustainability_score=self.sustainability_score - other.sustainability_score,
            transport_co2e=self.transport_co2e - other.transport_co2e,
            energy_co2e=self.energy_co2e - other.energy_co2e,
            food_co2e=self.food_co2e - other.food_co2e,
            waste_co2e=self.waste_co2e - other.waste_co2e,
        )

@dataclass
class FinancialImpact:
    implementation_cost_upfront: float = 0.0
    monthly_recurring_cost: float = 0.0
    yearly_recurring_cost: float = 0.0
    estimated_lifespan_years: int = 10
    
    def calculate_total_cost_over_years(self, years: float, inflation_rate: float = 0.03) -> float:
        total = self.implementation_cost_upfront
        current_yearly = self.yearly_recurring_cost
        for _ in range(int(years)):
            total += current_yearly
            current_yearly *= (1 + inflation_rate)
        
        fraction = years - int(years)
        if fraction > 0:
            total += current_yearly * fraction
            
        return total

@dataclass
class TimeHorizonProjection:
    horizon_months: int
    cumulative_carbon_kg: float
    cumulative_cost: float
    cumulative_water_liters: float
    cumulative_waste_kg: float
    net_savings_vs_baseline: float = 0.0
    roi_percentage: float = 0.0

@dataclass
class Scenario:
    id: str
    name: str
    description: str
    is_baseline: bool
    inputs: ScenarioInputs
    environmental_impact: EnvironmentalImpact = field(default_factory=EnvironmentalImpact)
    financial_impact: FinancialImpact = field(default_factory=FinancialImpact)
    projections: Dict[int, TimeHorizonProjection] = field(default_factory=dict)
    
@dataclass
class TradeOff:
    category: str
    description: str
    severity: str # "low", "medium", "high"
    metric_improved: str
    metric_worsened: str
    magnitude_improved: float
    magnitude_worsened: float

@dataclass
class SimulationResult:
    baseline: Scenario
    alternatives: List[Scenario]
    trade_offs: Dict[str, List[TradeOff]]
    rankings: Dict[str, List[str]]
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)
