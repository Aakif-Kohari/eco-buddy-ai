"""
Multi-Factor Carbon Footprint Engine
====================================
A comprehensive carbon footprint calculator that estimates environmental impact
across multiple lifestyle dimensions.

Author: EcoBuddy Team
Version: 1.0.0
"""

import json
import math
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from pathlib import Path
import hashlib
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class TransportationMode(Enum):
    """Transportation modes with their emission factors."""
    CAR_PETROL = "car_petrol"
    CAR_DIESEL = "car_diesel"
    CAR_ELECTRIC = "car_electric"
    CAR_HYBRID = "car_hybrid"
    MOTORCYCLE = "motorcycle"
    BUS = "bus"
    TRAIN = "train"
    SUBWAY = "subway"
    TRAM = "tram"
    BICYCLE = "bicycle"
    WALKING = "walking"
    DOMESTIC_FLIGHT = "domestic_flight"
    INTERNATIONAL_FLIGHT = "international_flight"
    LONG_HAUL_FLIGHT = "long_haul_flight"


class DietType(Enum):
    """Dietary patterns with their emission factors."""
    OMNIVORE = "omnivore"
    PESCETARIAN = "pescetarian"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    FLEXITARIAN = "flexitarian"
    KETO = "keto"
    PALEO = "paleo"


class EnergySource(Enum):
    """Energy sources for electricity generation."""
    COAL = "coal"
    NATURAL_GAS = "natural_gas"
    NUCLEAR = "nuclear"
    HYDRO = "hydro"
    WIND = "wind"
    SOLAR = "solar"
    GEOTHERMAL = "geothermal"
    BIOMASS = "biomass"
    MIXED = "mixed"


class WasteDisposalMethod(Enum):
    """Waste disposal methods."""
    LANDFILL = "landfill"
    RECYCLING = "recycling"
    COMPOSTING = "composting"
    INCINERATION = "incineration"
    WASTE_TO_ENERGY = "waste_to_energy"


class HouseholdSize(Enum):
    """Household size categories."""
    SINGLE = 1
    COUPLE = 2
    SMALL_FAMILY = 3
    MEDIUM_FAMILY = 4
    LARGE_FAMILY = 5
    EXTRA_LARGE = 6


# ============================================================================
# DATA CLASSES FOR INPUT/OUTPUT
# ============================================================================

@dataclass
class TransportationInput:
    """Input data for transportation src.carbon.emissions."""
    mode: TransportationMode
    distance_km: float
    frequency_per_week: int
    occupancy: int = 1
    vehicle_age_years: Optional[float] = None
    maintenance_level: str = "average"  # poor, average, excellent

    def __post_init__(self):
        if self.distance_km < 0:
            raise ValueError("Distance cannot be negative")
        if self.frequency_per_week < 0:
            raise ValueError("Frequency cannot be negative")
        if self.occupancy <= 0:
            raise ValueError("Occupancy must be at least 1")


@dataclass
class EnergyInput:
    """Input data for energy src.carbon.emissions."""
    electricity_kwh: float
    natural_gas_kwh: float
    heating_oil_liters: float
    energy_source: EnergySource
    renewable_percentage: float = 0.0
    home_area_sqft: Optional[float] = None
    insulation_rating: str = "average"  # poor, average, good, excellent
    smart_thermostat: bool = False

    def __post_init__(self):
        if self.electricity_kwh < 0:
            raise ValueError("Electricity consumption cannot be negative")
        if self.natural_gas_kwh < 0:
            raise ValueError("Natural gas consumption cannot be negative")
        if self.heating_oil_liters < 0:
            raise ValueError("Heating oil consumption cannot be negative")
        if not 0 <= self.renewable_percentage <= 100:
            raise ValueError("Renewable percentage must be between 0 and 100")


@dataclass
class FoodInput:
    """Input data for food src.carbon.emissions."""
    diet_type: DietType
    meat_per_week_kg: float
    dairy_per_week_kg: float
    eggs_per_week: int
    fish_per_week_kg: float
    fruits_vegetables_per_week_kg: float
    grains_per_week_kg: float
    processed_foods_per_week_kg: float
    organic_percentage: float = 0.0
    local_percentage: float = 0.0
    food_waste_percentage: float = 0.0

    def __post_init__(self):
        if self.meat_per_week_kg < 0:
            raise ValueError("Meat consumption cannot be negative")
        if self.dairy_per_week_kg < 0:
            raise ValueError("Dairy consumption cannot be negative")
        if self.eggs_per_week < 0:
            raise ValueError("Eggs per week cannot be negative")
        if self.fish_per_week_kg < 0:
            raise ValueError("Fish consumption cannot be negative")
        if self.fruits_vegetables_per_week_kg < 0:
            raise ValueError("Fruits/vegetables consumption cannot be negative")
        if self.grains_per_week_kg < 0:
            raise ValueError("Grains consumption cannot be negative")
        if self.processed_foods_per_week_kg < 0:
            raise ValueError("Processed foods consumption cannot be negative")
        if not 0 <= self.organic_percentage <= 100:
            raise ValueError("Organic percentage must be between 0 and 100")
        if not 0 <= self.local_percentage <= 100:
            raise ValueError("Local percentage must be between 0 and 100")
        if not 0 <= self.food_waste_percentage <= 100:
            raise ValueError("Food waste percentage must be between 0 and 100")


@dataclass
class HouseholdInput:
    """Input data for household src.carbon.emissions."""
    household_size: HouseholdSize
    number_of_bedrooms: int
    water_usage_liters_per_day: float
    heating_type: str  # gas, electric, oil, wood, geothermal, solar
    cooling_type: str  # central_air, window_unit, evaporative, none
    appliances_efficiency: str = "average"  # poor, average, good, excellent
    light_bulb_type: str = "led"  # led, cfl, incandescent
    energy_star_appliances: bool = False
    water_efficient_fixtures: bool = False

    def __post_init__(self):
        if self.number_of_bedrooms < 0:
            raise ValueError("Number of bedrooms cannot be negative")
        if self.water_usage_liters_per_day < 0:
            raise ValueError("Water usage cannot be negative")


@dataclass
class ConsumptionInput:
    """Input data for consumption src.carbon.emissions."""
    clothing_annual_spend_usd: float
    electronics_annual_spend_usd: float
    furniture_annual_spend_usd: float
    personal_care_annual_spend_usd: float
    entertainment_annual_spend_usd: float
    books_magazines_annual_spend_usd: float
    sustainable_purchases_percentage: float = 0.0
    second_hand_percentage: float = 0.0
    repair_reuse_percentage: float = 0.0

    def __post_init__(self):
        if self.clothing_annual_spend_usd < 0:
            raise ValueError("Clothing spend cannot be negative")
        if self.electronics_annual_spend_usd < 0:
            raise ValueError("Electronics spend cannot be negative")
        if self.furniture_annual_spend_usd < 0:
            raise ValueError("Furniture spend cannot be negative")
        if self.personal_care_annual_spend_usd < 0:
            raise ValueError("Personal care spend cannot be negative")
        if self.entertainment_annual_spend_usd < 0:
            raise ValueError("Entertainment spend cannot be negative")
        if self.books_magazines_annual_spend_usd < 0:
            raise ValueError("Books/magazines spend cannot be negative")
        if not 0 <= self.sustainable_purchases_percentage <= 100:
            raise ValueError("Sustainable purchases percentage must be between 0 and 100")
        if not 0 <= self.second_hand_percentage <= 100:
            raise ValueError("Second-hand percentage must be between 0 and 100")
        if not 0 <= self.repair_reuse_percentage <= 100:
            raise ValueError("Repair/reuse percentage must be between 0 and 100")


@dataclass
class WasteInput:
    """Input data for waste src.carbon.emissions."""
    total_waste_kg_per_week: float
    recycling_kg_per_week: float
    composting_kg_per_week: float
    landfill_kg_per_week: float
    incineration_kg_per_week: float
    waste_reduction_practices: List[str] = field(default_factory=list)
    upcycling_practices: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.total_waste_kg_per_week < 0:
            raise ValueError("Total waste cannot be negative")
        if self.recycling_kg_per_week < 0:
            raise ValueError("Recycling amount cannot be negative")
        if self.composting_kg_per_week < 0:
            raise ValueError("Composting amount cannot be negative")
        if self.landfill_kg_per_week < 0:
            raise ValueError("Landfill amount cannot be negative")
        if self.incineration_kg_per_week < 0:
            raise ValueError("Incineration amount cannot be negative")
        
        total_disposed = (self.recycling_kg_per_week + self.composting_kg_per_week +
                         self.landfill_kg_per_week + self.incineration_kg_per_week)
        if total_disposed > self.total_waste_kg_per_week * 1.01:  # Allow 1% rounding error
            logger.warning(f"Disposed waste ({total_disposed} kg) exceeds total waste ({self.total_waste_kg_per_week} kg)")


@dataclass
class UserProfile:
    """Complete user profile with all input data."""
    user_id: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    transportation: Optional[TransportationInput] = None
    energy: Optional[EnergyInput] = None
    food: Optional[FoodInput] = None
    household: Optional[HouseholdInput] = None
    consumption: Optional[ConsumptionInput] = None
    waste: Optional[WasteInput] = None
    
    def __post_init__(self):
        if self.age is not None and (self.age < 0 or self.age > 150):
            raise ValueError("Age must be between 0 and 150")


@dataclass
class CategoryEmissions:
    """Emissions breakdown by category."""
    transportation: float = 0.0  # kg CO2e per year
    energy: float = 0.0
    food: float = 0.0
    household: float = 0.0
    consumption: float = 0.0
    waste: float = 0.0
    
    def total(self) -> float:
        """Calculate total emissions across all categories."""
        return (self.transportation + self.energy + self.food + 
                self.household + self.consumption + self.waste)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class EmissionResult:
    """Complete emission calculation result."""
    total_emissions_kg_co2e: float
    category_breakdown: CategoryEmissions
    per_capita_emissions: float
    percentile_ranking: Optional[float] = None
    highest_impact_categories: List[Tuple[str, float]] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    comparison_to_average: Optional[Dict[str, float]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    calculation_version: str = "1.0.0"


# ============================================================================
# EMISSION FACTORS DATABASE
# ============================================================================

class EmissionFactorsDatabase:
    """Centralized, configurable emission factor dataset."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_factors()
        return cls._instance
    
    def _initialize_factors(self):
        """Initialize the emission factors src.core.database."""
        # Transportation emission factors (kg CO2e per km)
        self.transportation_factors = {
            TransportationMode.CAR_PETROL: {
                "base": 0.192,
                "city": 0.205,
                "highway": 0.158,
                "congestion": 0.230
            },
            TransportationMode.CAR_DIESEL: {
                "base": 0.171,
                "city": 0.185,
                "highway": 0.143,
                "congestion": 0.210
            },
            TransportationMode.CAR_ELECTRIC: {
                "base": 0.050,
                "city": 0.055,
                "highway": 0.045,
                "congestion": 0.060
            },
            TransportationMode.CAR_HYBRID: {
                "base": 0.110,
                "city": 0.120,
                "highway": 0.095,
                "congestion": 0.135
            },
            TransportationMode.MOTORCYCLE: {
                "base": 0.103,
                "city": 0.110,
                "highway": 0.090
            },
            TransportationMode.BUS: {
                "base": 0.085,
                "city": 0.095,
                "highway": 0.065
            },
            TransportationMode.TRAIN: {
                "base": 0.041,
                "electric": 0.020,
                "diesel": 0.060
            },
            TransportationMode.SUBWAY: {
                "base": 0.033
            },
            TransportationMode.TRAM: {
                "base": 0.028
            },
            TransportationMode.BICYCLE: {
                "base": 0.000
            },
            TransportationMode.WALKING: {
                "base": 0.000
            },
            TransportationMode.DOMESTIC_FLIGHT: {
                "base": 0.255,
                "economy": 0.230,
                "business": 0.380,
                "first_class": 0.510
            },
            TransportationMode.INTERNATIONAL_FLIGHT: {
                "base": 0.185,
                "economy": 0.170,
                "business": 0.280,
                "first_class": 0.375
            },
            TransportationMode.LONG_HAUL_FLIGHT: {
                "base": 0.150,
                "economy": 0.140,
                "business": 0.225,
                "first_class": 0.300
            }
        }
        
        # Energy emission factors (kg CO2e per kWh or per unit)
        self.energy_factors = {
            "electricity": {
                EnergySource.COAL: 0.950,
                EnergySource.NATURAL_GAS: 0.490,
                EnergySource.NUCLEAR: 0.012,
                EnergySource.HYDRO: 0.010,
                EnergySource.WIND: 0.011,
                EnergySource.SOLAR: 0.045,
                EnergySource.GEOTHERMAL: 0.015,
                EnergySource.BIOMASS: 0.230,
                EnergySource.MIXED: 0.450  # Average US grid mix
            },
            "natural_gas": 0.185,  # kg CO2e per kWh
            "heating_oil": 2.680,  # kg CO2e per liter
            "propane": 1.510,  # kg CO2e per liter
            "wood": 0.390  # kg CO2e per kg (dry)
        }
        
        # Food emission factors (kg CO2e per kg of food)
        self.food_factors = {
            "beef": {
                "base": 27.0,
                "grass_fed": 22.0,
                "organic": 25.0,
                "local": 26.0
            },
            "lamb": {
                "base": 24.0,
                "organic": 22.0,
                "local": 23.0
            },
            "pork": {
                "base": 12.0,
                "organic": 11.0,
                "local": 11.5
            },
            "chicken": {
                "base": 6.0,
                "organic": 5.5,
                "free_range": 5.0
            },
            "fish": {
                "base": 5.0,
                "wild_caught": 4.0,
                "farmed": 6.0,
                "sustainable": 3.5
            },
            "dairy": {
                "milk": 1.9,
                "cheese": 8.5,
                "yogurt": 2.2,
                "butter": 12.0,
                "cream": 6.5
            },
            "eggs": {
                "base": 4.8,
                "organic": 4.2,
                "free_range": 4.0
            },
            "vegetables": {
                "base": 0.5,
                "organic": 0.6,
                "local": 0.3,
                "seasonal": 0.4
            },
            "fruits": {
                "base": 0.6,
                "organic": 0.7,
                "local": 0.4,
                "tropical": 1.2
            },
            "grains": {
                "wheat": 0.8,
                "rice": 2.5,
                "corn": 0.6,
                "oats": 0.7,
                "barley": 0.6
            },
            "processed_foods": {
                "base": 2.0,
                "organic": 1.8,
                "local": 1.9
            },
            "plant_proteins": {
                "tofu": 2.0,
                "tempeh": 1.8,
                "seitan": 1.5,
                "legumes": 0.9
            }
        }
        
        # Diet type multipliers (relative to omnivore baseline)
        self.diet_multipliers = {
            DietType.OMNIVORE: 1.0,
            DietType.PESCETARIAN: 0.85,
            DietType.VEGETARIAN: 0.70,
            DietType.VEGAN: 0.55,
            DietType.FLEXITARIAN: 0.90,
            DietType.KETO: 1.10,
            DietType.PALEO: 1.05
        }
        
        # Household emission factors
        self.household_factors = {
            "water": {
                "heating": 0.025,  # kg CO2e per liter (electric heating)
                "gas_heating": 0.012,  # kg CO2e per liter (gas heating)
                "treatment": 0.002  # kg CO2e per liter
            },
            "appliances": {
                "refrigerator": {
                    "poor": 800.0,
                    "average": 500.0,
                    "good": 350.0,
                    "excellent": 200.0
                },
                "washing_machine": {
                    "poor": 300.0,
                    "average": 200.0,
                    "good": 150.0,
                    "excellent": 100.0
                },
                "dishwasher": {
                    "poor": 250.0,
                    "average": 180.0,
                    "good": 130.0,
                    "excellent": 90.0
                },
                "dryer": {
                    "poor": 400.0,
                    "average": 300.0,
                    "good": 200.0,
                    "excellent": 150.0
                },
                "heating_system": {
                    "gas": 2000.0,
                    "electric": 3500.0,
                    "oil": 2800.0,
                    "wood": 1500.0,
                    "geothermal": 800.0,
                    "solar": 400.0
                },
                "cooling_system": {
                    "central_air": 2500.0,
                    "window_unit": 1500.0,
                    "evaporative": 500.0,
                    "none": 0.0
                }
            },
            "lighting": {
                "incandescent": 0.060,  # kg CO2e per hour
                "cfl": 0.015,
                "led": 0.008
            },
            "heating_factors": {
                "gas": 0.185,
                "electric": 0.450,
                "oil": 0.270,
                "wood": 0.039,
                "geothermal": 0.015,
                "solar": 0.010
            }
        }
        
        # Consumption emission factors (kg CO2e per USD)
        self.consumption_factors = {
            "clothing": {
                "base": 0.025,
                "sustainable": 0.018,
                "second_hand": 0.010,
                "fast_fashion": 0.035
            },
            "electronics": {
                "base": 0.050,
                "sustainable": 0.040,
                "refurbished": 0.030,
                "repair": 0.020
            },
            "furniture": {
                "base": 0.030,
                "sustainable": 0.025,
                "second_hand": 0.015,
                "repair": 0.010
            },
            "personal_care": {
                "base": 0.020,
                "sustainable": 0.015,
                "eco_friendly": 0.012
            },
            "entertainment": {
                "base": 0.015,
                "digital": 0.010,
                "streaming": 0.008
            },
            "books_magazines": {
                "base": 0.018,
                "digital": 0.005,
                "used": 0.008
            }
        }
        
        # Waste emission factors (kg CO2e per kg of waste)
        self.waste_factors = {
            WasteDisposalMethod.LANDFILL: {
                "base": 0.800,
                "organic": 0.500,
                "paper": 0.300,
                "plastic": 1.200,
                "metal": 0.050,
                "glass": 0.020
            },
            WasteDisposalMethod.RECYCLING: {
                "base": -0.300,  # Negative emissions due to avoided production
                "paper": -0.500,
                "plastic": -0.200,
                "metal": -1.500,
                "glass": -0.100,
                "organic": -0.100
            },
            WasteDisposalMethod.COMPOSTING: {
                "base": 0.100,
                "organic": 0.050,
                "paper": 0.080
            },
            WasteDisposalMethod.INCINERATION: {
                "base": 0.700,
                "with_energy_recovery": 0.400
            },
            WasteDisposalMethod.WASTE_TO_ENERGY: {
                "base": 0.350
            }
        }
        
        # Regional adjustment factors (relative to global average)
        self.regional_factors = {
            "US": 1.15,
            "Canada": 1.10,
            "UK": 0.95,
            "Germany": 0.90,
            "France": 0.85,
            "China": 1.20,
            "India": 0.70,
            "Brazil": 0.80,
            "Australia": 1.10,
            "Japan": 0.95,
            "default": 1.0
        }
        
        # Average emissions for comparison (kg CO2e per year)
        self.average_emissions = {
            "transportation": 2800.0,
            "energy": 4500.0,
            "food": 2500.0,
            "household": 2000.0,
            "consumption": 1800.0,
            "waste": 500.0,
            "total": 14100.0,
            "per_capita": 5600.0
        }
        
        # Global emission factors for validation
        self.global_averages = {
            "transportation_km_per_day": 20.0,
            "electricity_kwh_per_year": 3000.0,
            "meat_kg_per_year": 43.0,
            "water_liters_per_day": 300.0,
            "waste_kg_per_day": 1.5
        }
        
        # Country-specific emission factors (electricity mix)
        self.country_energy_mix = {
            "US": {
                "renewable_percentage": 20.0,
                "average_intensity": 0.450
            },
            "Canada": {
                "renewable_percentage": 65.0,
                "average_intensity": 0.210
            },
            "UK": {
                "renewable_percentage": 35.0,
                "average_intensity": 0.350
            },
            "Germany": {
                "renewable_percentage": 45.0,
                "average_intensity": 0.320
            },
            "France": {
                "renewable_percentage": 25.0,
                "average_intensity": 0.085  # Mostly nuclear
            },
            "China": {
                "renewable_percentage": 25.0,
                "average_intensity": 0.600
            },
            "India": {
                "renewable_percentage": 22.0,
                "average_intensity": 0.700
            },
            "Brazil": {
                "renewable_percentage": 80.0,
                "average_intensity": 0.120
            },
            "Australia": {
                "renewable_percentage": 25.0,
                "average_intensity": 0.500
            },
            "Japan": {
                "renewable_percentage": 20.0,
                "average_intensity": 0.450
            }
        }
    
    def get_transportation_factor(self, mode: TransportationMode, 
                                 condition: str = "base") -> float:
        """Get emission factor for a transportation mode."""
        factors = self.transportation_factors.get(mode)
        if not factors:
            raise ValueError(f"No factors found for mode: {mode}")
        return factors.get(condition, factors.get("base", 0.0))
    
    def get_energy_factor(self, source: EnergySource) -> float:
        """Get emission factor for electricity generation."""
        return self.energy_factors["electricity"].get(source, 0.450)
    
    def get_food_factor(self, category: str, subcategory: str = "base") -> float:
        """Get emission factor for a food category."""
        factors = self.food_factors.get(category)
        if not factors:
            return 0.0
        if isinstance(factors, dict):
            return factors.get(subcategory, factors.get("base", 0.0))
        return float(factors)
    
    def get_consumption_factor(self, category: str, subcategory: str = "base") -> float:
        """Get emission factor for consumption category."""
        factors = self.consumption_factors.get(category)
        if not factors:
            return 0.0
        if isinstance(factors, dict):
            return factors.get(subcategory, factors.get("base", 0.0))
        return float(factors)
    
    def get_waste_factor(self, method: WasteDisposalMethod, 
                        material: str = "base") -> float:
        """Get emission factor for waste disposal method."""
        factors = self.waste_factors.get(method)
        if not factors:
            return 0.0
        if isinstance(factors, dict):
            return factors.get(material, factors.get("base", 0.0))
        return float(factors)
    
    def get_regional_factor(self, country: Optional[str]) -> float:
        """Get regional adjustment factor."""
        if not country:
            return 1.0
        return self.regional_factors.get(country, self.regional_factors["default"])
    
    def get_average_emissions(self, category: Optional[str] = None) -> Union[float, Dict]:
        """Get average emissions for comparison."""
        if category:
            return self.average_emissions.get(category, 0.0)
        return self.average_emissions


# ============================================================================
# CALCULATION ENGINE
# ============================================================================

class CarbonFootprintEngine:
    """Main calculation engine for carbon footprint estimation."""
    
    def __init__(self):
        """Initialize the engine with emission factors src.core.database."""
        self.factors = EmissionFactorsDatabase()
        self.logger = logging.getLogger(f"{__name__}.CarbonFootprintEngine")
    
    def calculate_transportation(self, inputs: List[TransportationInput]) -> float:
        """
        Calculate transportation emissions for multiple trips/modes.
        
        Args:
            inputs: List of TransportationInput objects
            
        Returns:
            Annual CO2e emissions in kg
        """
        total_emissions = 0.0
        
        for trip in inputs:
            # Get base emission factor for the mode
            base_factor = self.factors.get_transportation_factor(trip.mode)
            
            # Apply vehicle age adjustment
            age_factor = 1.0
            if trip.vehicle_age_years is not None and trip.vehicle_age_years > 5:
                age_factor = 1.0 + (trip.vehicle_age_years - 5) * 0.02
            
            # Apply maintenance adjustment
            maintenance_factors = {
                "poor": 1.15,
                "average": 1.0,
                "excellent": 0.90
            }
            maintenance_factor = maintenance_factors.get(trip.maintenance_level, 1.0)
            
            # Apply occupancy adjustment (carpooling reduces per-person emissions)
            occupancy_factor = 1.0 / max(trip.occupancy, 1)
            
            # Calculate weekly emissions
            weekly_emissions = (trip.distance_km * base_factor * 
                               age_factor * maintenance_factor * 
                               occupancy_factor * trip.frequency_per_week)
            
            # Convert to annual emissions
            annual_emissions = weekly_emissions * 52
            total_emissions += annual_emissions
        
        return total_emissions
    
    def calculate_energy(self, energy_input: EnergyInput, 
                        country: Optional[str] = None) -> float:
        """
        Calculate energy-related src.carbon.emissions.
        
        Args:
            energy_input: EnergyInput object
            country: Optional country for regional adjustment
            
        Returns:
            Annual CO2e emissions in kg
        """
        total_emissions = 0.0
        
        # Electricity emissions
        base_factor = self.factors.get_energy_factor(energy_input.energy_source)
        
        # Apply renewable percentage adjustment
        renewable_factor = 1.0 - (energy_input.renewable_percentage / 100.0)
        electricity_factor = base_factor * renewable_factor
        
        # Apply regional adjustment
        regional_factor = self.factors.get_regional_factor(country)
        electricity_factor *= regional_factor
        
        total_emissions += energy_input.electricity_kwh * electricity_factor
        
        # Natural gas emissions
        gas_factor = self.factors.energy_factors["natural_gas"]
        total_emissions += energy_input.natural_gas_kwh * gas_factor
        
        # Heating oil emissions
        oil_factor = self.factors.energy_factors["heating_oil"]
        total_emissions += energy_input.heating_oil_liters * oil_factor
        
        # Home efficiency adjustments
        if energy_input.home_area_sqft:
            # Adjust based on home size (efficiency per square foot)
            avg_home_size = 1500.0  # Average home size in sqft
            size_ratio = energy_input.home_area_sqft / avg_home_size
            total_emissions *= (0.7 + 0.3 * size_ratio)
        
        # Insulation adjustments
        insulation_factors = {
            "poor": 1.20,
            "average": 1.0,
            "good": 0.85,
            "excellent": 0.70
        }
        insulation_factor = insulation_factors.get(energy_input.insulation_rating, 1.0)
        total_emissions *= insulation_factor
        
        # Smart thermostat savings
        if energy_input.smart_thermostat:
            total_emissions *= 0.92  # 8% savings
        
        return total_emissions
    
    def calculate_food(self, food_input: FoodInput) -> float:
        """
        Calculate food-related src.carbon.emissions.
        
        Args:
            food_input: FoodInput object
            
        Returns:
            Annual CO2e emissions in kg
        """
        # Convert weekly consumption to annual
        annual_meat = food_input.meat_per_week_kg * 52
        annual_dairy = food_input.dairy_per_week_kg * 52
        annual_eggs = food_input.eggs_per_week * 52
        annual_fish = food_input.fish_per_week_kg * 52
        annual_fruits_veg = food_input.fruits_vegetables_per_week_kg * 52
        annual_grains = food_input.grains_per_week_kg * 52
        annual_processed = food_input.processed_foods_per_week_kg * 52
        
        # Calculate emissions for each category
        meat_emissions = self._calculate_meat_emissions(annual_meat)
        dairy_emissions = self._calculate_dairy_emissions(annual_dairy)
        egg_emissions = self._calculate_egg_emissions(annual_eggs)
        fish_emissions = self._calculate_fish_emissions(annual_fish)
        fruits_veg_emissions = self._calculate_fruits_vegetables_emissions(annual_fruits_veg)
        grains_emissions = self._calculate_grains_emissions(annual_grains)
        processed_emissions = self._calculate_processed_emissions(annual_processed)
        
        total_emissions = (meat_emissions + dairy_emissions + egg_emissions + 
                          fish_emissions + fruits_veg_emissions + grains_emissions +
                          processed_emissions)
        
        # Apply diet type multiplier
        diet_multiplier = self.factors.diet_multipliers.get(food_input.diet_type, 1.0)
        total_emissions *= diet_multiplier
        
        # Apply organic and local adjustments
        if food_input.organic_percentage > 0:
            total_emissions *= (1.0 - food_input.organic_percentage / 100.0 * 0.1)
        if food_input.local_percentage > 0:
            total_emissions *= (1.0 - food_input.local_percentage / 100.0 * 0.15)
        
        # Apply food waste adjustment
        if food_input.food_waste_percentage > 0:
            total_emissions *= (1.0 + food_input.food_waste_percentage / 100.0 * 0.3)
        
        return total_emissions
    
    def _calculate_meat_emissions(self, annual_kg: float) -> float:
        """Calculate meat emissions with detailed breakdown."""
        if annual_kg <= 0:
            return 0.0
        
        # Assume a mix of beef, pork, and chicken
        beef_ratio = 0.4
        pork_ratio = 0.3
        chicken_ratio = 0.3
        
        beef_factor = self.factors.get_food_factor("beef")
        pork_factor = self.factors.get_food_factor("pork")
        chicken_factor = self.factors.get_food_factor("chicken")
        
        emissions = (annual_kg * beef_ratio * beef_factor +
                    annual_kg * pork_ratio * pork_factor +
                    annual_kg * chicken_ratio * chicken_factor)
        
        return emissions
    
    def _calculate_dairy_emissions(self, annual_kg: float) -> float:
        """Calculate dairy src.carbon.emissions."""
        if annual_kg <= 0:
            return 0.0
        
        # Assume milk and cheese mix
        milk_ratio = 0.7
        cheese_ratio = 0.3
        
        milk_factor = self.factors.get_food_factor("dairy", "milk")
        cheese_factor = self.factors.get_food_factor("dairy", "cheese")
        
        emissions = (annual_kg * milk_ratio * milk_factor +
                    annual_kg * cheese_ratio * cheese_factor)
        
        return emissions
    
    def _calculate_egg_emissions(self, annual_eggs: int) -> float:
        """Calculate egg src.carbon.emissions."""
        if annual_eggs <= 0:
            return 0.0
        
        # Convert eggs to kg (approximately 50g per egg)
        annual_kg = annual_eggs * 0.05
        factor = self.factors.get_food_factor("eggs")
        
        return annual_kg * factor
    
    def _calculate_fish_emissions(self, annual_kg: float) -> float:
        """Calculate fish src.carbon.emissions."""
        if annual_kg <= 0:
            return 0.0
        
        factor = self.factors.get_food_factor("fish")
        return annual_kg * factor
    
    def _calculate_fruits_vegetables_emissions(self, annual_kg: float) -> float:
        """Calculate fruits and vegetables src.carbon.emissions."""
        if annual_kg <= 0:
            return 0.0
        
        # Split between fruits and vegetables (assuming half and half)
        fruits_ratio = 0.5
        vegetables_ratio = 0.5
        
        fruits_factor = self.factors.get_food_factor("fruits")
        vegetables_factor = self.factors.get_food_factor("vegetables")
        
        emissions = (annual_kg * fruits_ratio * fruits_factor +
                    annual_kg * vegetables_ratio * vegetables_factor)
        
        return emissions
    
    def _calculate_grains_emissions(self, annual_kg: float) -> float:
        """Calculate grains src.carbon.emissions."""
        if annual_kg <= 0:
            return 0.0
        
        # Assume mixed grains (wheat, rice, etc.)
        wheat_ratio = 0.5
        rice_ratio = 0.3
        corn_ratio = 0.2
        
        wheat_factor = self.factors.get_food_factor("grains", "wheat")
        rice_factor = self.factors.get_food_factor("grains", "rice")
        corn_factor = self.factors.get_food_factor("grains", "corn")
        
        emissions = (annual_kg * wheat_ratio * wheat_factor +
                    annual_kg * rice_ratio * rice_factor +
                    annual_kg * corn_ratio * corn_factor)
        
        return emissions
    
    def _calculate_processed_emissions(self, annual_kg: float) -> float:
        """Calculate processed food src.carbon.emissions."""
        if annual_kg <= 0:
            return 0.0
        
        factor = self.factors.get_food_factor("processed_foods")
        return annual_kg * factor
    
    def calculate_household(self, household_input: HouseholdInput) -> float:
        """
        Calculate household-related src.carbon.emissions.
        
        Args:
            household_input: HouseholdInput object
            
        Returns:
            Annual CO2e emissions in kg
        """
        total_emissions = 0.0
        
        # Water heating emissions
        water_heating_factor = self.factors.household_factors["water"]["heating"]
        water_emissions = (household_input.water_usage_liters_per_day * 365 *
                          water_heating_factor)
        total_emissions += water_emissions
        
        # Heating system emissions
        heating_factor = self.factors.household_factors["appliances"]["heating_system"]
        heating_emissions = heating_factor.get(household_input.heating_type, 0.0)
        total_emissions += heating_emissions
        
        # Cooling system emissions
        cooling_factor = self.factors.household_factors["appliances"]["cooling_system"]
        cooling_emissions = cooling_factor.get(household_input.cooling_type, 0.0)
        total_emissions += cooling_emissions
        
        # Lighting emissions
        lighting_hours_per_day = 5.0  # Average lighting usage
        lighting_factors = self.factors.household_factors["lighting"]
        light_factor = lighting_factors.get(household_input.light_bulb_type, 0.015)
        lighting_emissions = (lighting_hours_per_day * 365 * light_factor *
                            household_input.number_of_bedrooms * 10)  # 10 bulbs per bedroom
        total_emissions += lighting_emissions
        
        # Energy Star appliances savings
        if household_input.energy_star_appliances:
            total_emissions *= 0.85  # 15% savings
        
        # Water efficient fixtures savings
        if household_input.water_efficient_fixtures:
            total_emissions *= 0.90  # 10% savings
        
        # Household size adjustment (economies of scale)
        size_factors = {
            1: 1.0,
            2: 1.6,
            3: 2.0,
            4: 2.3,
            5: 2.5,
            6: 2.7
        }
        size_factor = size_factors.get(household_input.household_size.value, 2.3)
        total_emissions *= (size_factor / household_input.household_size.value)
        
        return total_emissions
    
    def calculate_consumption(self, consumption_input: ConsumptionInput) -> float:
        """
        Calculate consumption-related src.carbon.emissions.
        
        Args:
            consumption_input: ConsumptionInput object
            
        Returns:
            Annual CO2e emissions in kg
        """
        total_emissions = 0.0
        
        # Calculate emissions for each consumption category
        clothing_factor = self.factors.get_consumption_factor("clothing")
        clothing_emissions = consumption_input.clothing_annual_spend_usd * clothing_factor
        total_emissions += clothing_emissions
        
        electronics_factor = self.factors.get_consumption_factor("electronics")
        electronics_emissions = consumption_input.electronics_annual_spend_usd * electronics_factor
        total_emissions += electronics_emissions
        
        furniture_factor = self.factors.get_consumption_factor("furniture")
        furniture_emissions = consumption_input.furniture_annual_spend_usd * furniture_factor
        total_emissions += furniture_emissions
        
        personal_care_factor = self.factors.get_consumption_factor("personal_care")
        personal_care_emissions = consumption_input.personal_care_annual_spend_usd * personal_care_factor
        total_emissions += personal_care_emissions
        
        entertainment_factor = self.factors.get_consumption_factor("entertainment")
        entertainment_emissions = consumption_input.entertainment_annual_spend_usd * entertainment_factor
        total_emissions += entertainment_emissions
        
        books_factor = self.factors.get_consumption_factor("books_magazines")
        books_emissions = consumption_input.books_magazines_annual_spend_usd * books_factor
        total_emissions += books_emissions
        
        # Apply sustainable consumption adjustments
        if consumption_input.sustainable_purchases_percentage > 0:
            total_emissions *= (1.0 - consumption_input.sustainable_purchases_percentage / 100.0 * 0.2)
        
        if consumption_input.second_hand_percentage > 0:
            total_emissions *= (1.0 - consumption_input.second_hand_percentage / 100.0 * 0.3)
        
        if consumption_input.repair_reuse_percentage > 0:
            total_emissions *= (1.0 - consumption_input.repair_reuse_percentage / 100.0 * 0.25)
        
        return total_emissions
    
    def calculate_waste(self, waste_input: WasteInput) -> float:
        """
        Calculate waste-related src.carbon.emissions.
        
        Args:
            waste_input: WasteInput object
            
        Returns:
            Annual CO2e emissions in kg
        """
        # Convert weekly to annual
        total_waste = waste_input.total_waste_kg_per_week * 52
        recycling = waste_input.recycling_kg_per_week * 52
        composting = waste_input.composting_kg_per_week * 52
        landfill = waste_input.landfill_kg_per_week * 52
        incineration = waste_input.incineration_kg_per_week * 52
        
        total_emissions = 0.0
        
        # Landfill emissions
        landfill_factor = self.factors.get_waste_factor(WasteDisposalMethod.LANDFILL)
        total_emissions += landfill * landfill_factor
        
        # Recycling emissions (usually negative)
        recycling_factor = self.factors.get_waste_factor(WasteDisposalMethod.RECYCLING)
        total_emissions += recycling * recycling_factor
        
        # Composting emissions
        composting_factor = self.factors.get_waste_factor(WasteDisposalMethod.COMPOSTING)
        total_emissions += composting * composting_factor
        
        # Incineration emissions
        incineration_factor = self.factors.get_waste_factor(WasteDisposalMethod.INCINERATION)
        total_emissions += incineration * incineration_factor
        
        # Apply waste reduction practices
        reduction_practices = {
            "reduce_plastic": 0.05,
            "buy_bulk": 0.03,
            "use_reusable": 0.04,
            "avoid_packaging": 0.06,
            "compost_home": 0.08
        }
        
        for practice in waste_input.waste_reduction_practices:
            if practice in reduction_practices:
                total_emissions *= (1.0 - reduction_practices[practice])
        
        # Upcycling practices
        upcycling_practices = {
            "repair_items": 0.05,
            "upcycle_furniture": 0.04,
            "reuse_containers": 0.03,
            "donate_clothes": 0.06
        }
        
        for practice in waste_input.upcycling_practices:
            if practice in upcycling_practices:
                total_emissions *= (1.0 - upcycling_practices[practice])
        
        return max(total_emissions, 0.0)  # Ensure non-negative
    
    def calculate_full_profile(self, profile: UserProfile) -> EmissionResult:
        """
        Calculate full carbon footprint for a user profile.
        
        Args:
            profile: UserProfile object with all input data
            
        Returns:
            EmissionResult object with complete breakdown
        """
        self.logger.info(f"Calculating carbon footprint for user: {profile.user_id}")
        
        category_emissions = CategoryEmissions()
        
        # Calculate each category if data is available
        if profile.transportation:
            category_emissions.transportation = self.calculate_transportation(
                [profile.transportation]  # Convert single input to list
            )
        
        if profile.energy:
            category_emissions.energy = self.calculate_energy(
                profile.energy, profile.country
            )
        
        if profile.food:
            category_emissions.food = self.calculate_food(profile.food)
        
        if profile.household:
            category_emissions.household = self.calculate_household(profile.household)
        
        if profile.consumption:
            category_emissions.consumption = self.calculate_consumption(profile.consumption)
        
        if profile.waste:
            category_emissions.waste = self.calculate_waste(profile.waste)
        
        # Calculate totals
        total_emissions = category_emissions.total()
        per_capita_emissions = self._calculate_per_capita(total_emissions, profile)
        
        # Identify highest impact categories
        highest_impact = self._get_highest_impact_categories(category_emissions)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(category_emissions, profile)
        
        # Calculate comparison to average
        comparison = self._get_comparison_to_average(category_emissions)
        
        result = EmissionResult(
            total_emissions_kg_co2e=total_emissions,
            category_breakdown=category_emissions,
            per_capita_emissions=per_capita_emissions,
            percentile_ranking=self._calculate_percentile(total_emissions),
            highest_impact_categories=highest_impact,
            recommendations=recommendations,
            comparison_to_average=comparison
        )
        
        self.logger.info(f"Calculation complete. Total emissions: {total_emissions:.2f} kg CO2e")
        
        return result
    
    def _calculate_per_capita(self, total_emissions: float, 
                             profile: UserProfile) -> float:
        """Calculate per capita emissions based on household size."""
        if profile.household and profile.household.household_size:
            return total_emissions / profile.household.household_size.value
        return total_emissions
    
    def _get_highest_impact_categories(self, 
                                       emissions: CategoryEmissions) -> List[Tuple[str, float]]:
        """Identify the highest impact categories."""
        categories = src.carbon.emissions.to_dict()
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        return sorted_categories[:3]  # Return top 3
    
    def _generate_recommendations(self, emissions: CategoryEmissions, 
                                 profile: UserProfile) -> List[Dict[str, Any]]:
        """
        Generate personalized recommendations for reducing src.carbon.emissions.
        """
        recommendations = []
        total = src.carbon.emissions.total()
        category_emissions = src.carbon.emissions.to_dict()
        
        # Transportation recommendations
        if src.carbon.emissions.transportation > total * 0.2:  # If transportation is >20% of total
            src.ai.recommendations.append({
                "category": "transportation",
                "priority": "high",
                "recommendation": "Consider using public transport, carpooling, or cycling more often.",
                "potential_savings": src.carbon.emissions.transportation * 0.25,
                "tips": [
                    "Walk or bike for trips under 5 km",
                    "Use public transport for commuting",
                    "Consider an electric or hybrid vehicle",
                    "Combine errands to reduce trips",
                    "Maintain proper tire pressure for fuel efficiency"
                ]
            })
        
        if profile.transportation and profile.transportation.mode in [
            TransportationMode.DOMESTIC_FLIGHT,
            TransportationMode.INTERNATIONAL_FLIGHT,
            TransportationMode.LONG_HAUL_FLIGHT
        ]:
            src.ai.recommendations.append({
                "category": "transportation",
                "priority": "high",
                "recommendation": "Reduce air travel or offset carbon emissions from flights.",
                "potential_savings": src.carbon.emissions.transportation * 0.30,
                "tips": [
                    "Choose direct flights when possible",
                    "Consider video conferencing instead of business travel",
                    "Purchase carbon offsets for unavoidable flights",
                    "Choose economy class (lower emissions per passenger)"
                ]
            })
        
        # Energy recommendations
        if src.carbon.emissions.energy > total * 0.25:
            src.ai.recommendations.append({
                "category": "energy",
                "priority": "high",
                "recommendation": "Improve home energy efficiency and consider renewable energy.",
                "potential_savings": src.carbon.emissions.energy * 0.30,
                "tips": [
                    "Switch to LED lighting",
                    "Install a programmable thermostat",
                    "Improve home insulation",
                    "Consider solar panels or green energy provider",
                    "Use energy-efficient appliances"
                ]
            })
        
        if profile.energy and profile.energy.renewable_percentage < 30:
            src.ai.recommendations.append({
                "category": "energy",
                "priority": "medium",
                "recommendation": "Increase your renewable energy usage.",
                "potential_savings": src.carbon.emissions.energy * 0.15,
                "tips": [
                    "Choose a green energy provider",
                    "Install solar panels if feasible",
                    "Consider community solar programs",
                    "Use renewable energy certificates"
                ]
            })
        
        # Food recommendations
        if src.carbon.emissions.food > total * 0.15:
            src.ai.recommendations.append({
                "category": "food",
                "priority": "medium",
                "recommendation": "Adopt a more sustainable diet with lower environmental impact.",
                "potential_savings": src.carbon.emissions.food * 0.25,
                "tips": [
                    "Reduce meat consumption, especially beef and lamb",
                    "Choose organic and locally produced foods",
                    "Reduce food waste by meal planning",
                    "Consider a plant-based diet",
                    "Buy seasonal produce"
                ]
            })
        
        if profile.food and profile.food.meat_per_week_kg > 1.0:
            src.ai.recommendations.append({
                "category": "food",
                "priority": "high",
                "recommendation": "Significantly reduce meat consumption.",
                "potential_savings": src.carbon.emissions.food * 0.30,
                "tips": [
                    "Try meatless Mondays",
                    "Replace beef with poultry or fish",
                    "Explore plant-based protein alternatives",
                    "Gradually transition to a flexitarian diet"
                ]
            })
        
        # Household recommendations
        if src.carbon.emissions.household > total * 0.15:
            src.ai.recommendations.append({
                "category": "household",
                "priority": "medium",
                "recommendation": "Optimize household water and energy usage.",
                "potential_savings": src.carbon.emissions.household * 0.20,
                "tips": [
                    "Fix leaky faucets and toilets",
                    "Use water-efficient fixtures",
                    "Wash clothes in cold water",
                    "Air dry clothes instead of using dryer",
                    "Install low-flow showerheads"
                ]
            })
        
        # Consumption recommendations
        if src.carbon.emissions.consumption > total * 0.15:
            src.ai.recommendations.append({
                "category": "consumption",
                "priority": "medium",
                "recommendation": "Adopt more sustainable consumption habits.",
                "potential_savings": src.carbon.emissions.consumption * 0.25,
                "tips": [
                    "Buy second-hand and vintage items",
                    "Choose quality over quantity",
                    "Repair and maintain items",
                    "Support sustainable brands",
                    "Reduce impulse purchases"
                ]
            })
        
        # Waste recommendations
        if src.carbon.emissions.waste > total * 0.05:
            src.ai.recommendations.append({
                "category": "waste",
                "priority": "low",
                "recommendation": "Improve waste management and reduction.",
                "potential_savings": src.carbon.emissions.waste * 0.30,
                "tips": [
                    "Recycle more and recycle correctly",
                    "Start composting food waste",
                    "Reduce single-use plastic",
                    "Buy products with minimal packaging",
                    "Practice the 3Rs: Reduce, Reuse, Recycle"
                ]
            })
        
        # General recommendations based on total emissions
        if total > 15000:
            src.ai.recommendations.append({
                "category": "general",
                "priority": "high",
                "recommendation": "Your carbon footprint is significantly above average. Consider a lifestyle audit.",
                "potential_savings": total * 0.20,
                "tips": [
                    "Conduct a home energy audit",
                    "Track your carbon footprint monthly",
                    "Set reduction goals",
                    "Join local environmental initiatives",
                    "Consider carbon offset programs"
                ]
            })
        elif total > 10000:
            src.ai.recommendations.append({
                "category": "general",
                "priority": "medium",
                "recommendation": "Your carbon footprint is above average. Start with high-impact changes.",
                "potential_savings": total * 0.15,
                "tips": [
                    "Focus on your highest impact categories",
                    "Make sustainable choices daily",
                    "Share rides when possible",
                    "Support renewable energy"
                ]
            })
        else:
            src.ai.recommendations.append({
                "category": "general",
                "priority": "low",
                "recommendation": "Great job! Your carbon footprint is below average. Keep it up!",
                "potential_savings": total * 0.05,
                "tips": [
                    "Continue monitoring your impact",
                    "Inspire others to reduce their footprint",
                    "Consider going carbon negative",
                    "Support environmental causes"
                ]
            })
        
        # Sort recommendations by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        src.ai.recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))
        
        return recommendations
    
    def _get_comparison_to_average(self, emissions: CategoryEmissions) -> Dict[str, float]:
        """Calculate comparison to average src.carbon.emissions."""
        averages = self.factors.get_average_emissions()
        category_emissions = src.carbon.emissions.to_dict()
        
        comparison = {}
        for category, avg_value in averages.items():
            if category in category_emissions and category != "total":
                comparison[category] = (category_emissions[category] / avg_value) - 1.0
        
        return comparison
    
    def _calculate_percentile(self, total_emissions: float) -> Optional[float]:
        """
        Calculate approximate percentile ranking based on global distribution.
        
        This is a simplified model assuming normal distribution of src.carbon.emissions.
        """
        # Global average and standard deviation (approximate)
        mean = 14100.0  # Average total emissions
        std_dev = 5000.0  # Approximate standard deviation
        
        if total_emissions < 0:
            return None
        
        # Calculate z-score
        z_score = (total_emissions - mean) / std_dev
        
        # Convert z-score to percentile using standard normal CDF
        # Using approximation for normal CDF
        def normal_cdf(x):
            # Approximation of normal CDF using error function
            import math
            return 0.5 * (1 + math.erf(x / math.sqrt(2)))
        
        percentile = normal_cdf(z_score)
        
        # Convert to percentage and clamp to [0, 100]
        percentile = max(0, min(100, percentile * 100))
        
        return percentile


# ============================================================================
# DATA VALIDATION AND UTILITY FUNCTIONS
# ============================================================================

class InputValidator:
    """Validate user inputs and handle missing/invalid data."""
    
    @staticmethod
    def validate_user_profile(profile: UserProfile) -> Tuple[bool, List[str]]:
        """
        Validate all inputs in a user profile.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate transportation
        if profile.transportation:
            try:
                if profile.transportation.distance_km < 0:
                    src.core.errors.append("Transportation distance cannot be negative")
                if profile.transportation.frequency_per_week < 0:
                    src.core.errors.append("Transportation frequency cannot be negative")
                if profile.transportation.occupancy <= 0:
                    src.core.errors.append("Transportation occupancy must be at least 1")
            except Exception as e:
                src.core.errors.append(f"Transportation validation error: {str(e)}")
        
        # Validate energy
        if profile.energy:
            try:
                if profile.energy.electricity_kwh < 0:
                    src.core.errors.append("Electricity consumption cannot be negative")
                if profile.energy.natural_gas_kwh < 0:
                    src.core.errors.append("Natural gas consumption cannot be negative")
                if profile.energy.heating_oil_liters < 0:
                    src.core.errors.append("Heating oil consumption cannot be negative")
                if not 0 <= profile.energy.renewable_percentage <= 100:
                    src.core.errors.append("Renewable percentage must be between 0 and 100")
            except Exception as e:
                src.core.errors.append(f"Energy validation error: {str(e)}")
        
        # Validate food
        if profile.food:
            try:
                if profile.food.meat_per_week_kg < 0:
                    src.core.errors.append("Meat consumption cannot be negative")
                if profile.food.dairy_per_week_kg < 0:
                    src.core.errors.append("Dairy consumption cannot be negative")
                if profile.food.eggs_per_week < 0:
                    src.core.errors.append("Eggs per week cannot be negative")
                if profile.food.fish_per_week_kg < 0:
                    src.core.errors.append("Fish consumption cannot be negative")
                if not 0 <= profile.food.organic_percentage <= 100:
                    src.core.errors.append("Organic percentage must be between 0 and 100")
            except Exception as e:
                src.core.errors.append(f"Food validation error: {str(e)}")
        
        # Validate household
        if profile.household:
            try:
                if profile.household.number_of_bedrooms < 0:
                    src.core.errors.append("Number of bedrooms cannot be negative")
                if profile.household.water_usage_liters_per_day < 0:
                    src.core.errors.append("Water usage cannot be negative")
            except Exception as e:
                src.core.errors.append(f"Household validation error: {str(e)}")
        
        # Validate consumption
        if profile.consumption:
            try:
                if profile.consumption.clothing_annual_spend_usd < 0:
                    src.core.errors.append("Clothing spend cannot be negative")
                if profile.consumption.electronics_annual_spend_usd < 0:
                    src.core.errors.append("Electronics spend cannot be negative")
                if not 0 <= profile.consumption.sustainable_purchases_percentage <= 100:
                    src.core.errors.append("Sustainable purchases percentage must be between 0 and 100")
            except Exception as e:
                src.core.errors.append(f"Consumption validation error: {str(e)}")
        
        # Validate waste
        if profile.waste:
            try:
                if profile.waste.total_waste_kg_per_week < 0:
                    src.core.errors.append("Total waste cannot be negative")
                if profile.waste.recycling_kg_per_week < 0:
                    src.core.errors.append("Recycling amount cannot be negative")
                if profile.waste.composting_kg_per_week < 0:
                    src.core.errors.append("Composting amount cannot be negative")
                if profile.waste.landfill_kg_per_week < 0:
                    src.core.errors.append("Landfill amount cannot be negative")
            except Exception as e:
                src.core.errors.append(f"Waste validation error: {str(e)}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def sanitize_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and clean input data."""
        sanitized = {}
        
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, str):
                sanitized[key] = value.strip()
            elif isinstance(value, (int, float)):
                sanitized[key] = max(0, value)
            else:
                sanitized[key] = value
        
        return sanitized


class DataPersistence:
    """Handle saving and loading of user data."""
    
    def __init__(self, data_dir: str = "user_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def save_profile(self, profile: UserProfile, filename: Optional[str] = None) -> str:
        """Save user profile to JSON file."""
        if filename is None:
            if profile.user_id:
                filename = f"{profile.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:
                filename = f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.data_dir / filename
        
        # Convert dataclass to dict
        data = asdict(profile)
        
        # Save to JSON
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return str(filepath)
    
    def load_profile(self, filename: str) -> UserProfile:
        """Load user profile from JSON file."""
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Profile file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Convert dict to UserProfile dataclass
        return self._dict_to_profile(data)
    
    def _dict_to_profile(self, data: Dict[str, Any]) -> UserProfile:
        """Convert dictionary to UserProfile object."""
        # This is a simplified conversion; for production, use a proper serializer
        profile = UserProfile(**data)
        return profile
    
    def list_profiles(self) -> List[Path]:
        """List all saved profiles."""
        return list(self.data_dir.glob("*.json"))


# ============================================================================
# REPORTING AND VISUALIZATION
# ============================================================================

class EmissionReporter:
    """Generate reports and visualizations from emission results."""
    
    @staticmethod
    def generate_text_report(result: EmissionResult) -> str:
        """Generate a formatted text src.reporting.report."""
        lines = []
        lines.append("=" * 60)
        lines.append("CARBON FOOTPRINT REPORT")
        lines.append("=" * 60)
        lines.append(f"Total Emissions: {result.total_emissions_kg_co2e:.2f} kg CO2e/year")
        lines.append(f"Per Capita: {result.per_capita_emissions:.2f} kg CO2e/year")
        
        if result.percentile_ranking is not None:
            lines.append(f"Percentile Ranking: {result.percentile_ranking:.1f}%")
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("CATEGORY BREAKDOWN")
        lines.append("-" * 60)
        
        breakdown = result.category_breakdown.to_dict()
        max_category_len = max(len(cat) for cat in breakdown.keys())
        
        for category, emissions in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
            percentage = (emissions / result.total_emissions_kg_co2e * 100) if result.total_emissions_kg_co2e > 0 else 0
            lines.append(f"{category.capitalize():{max_category_len}s}: {emissions:10.2f} kg CO2e ({percentage:5.1f}%)")
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("HIGHEST IMPACT CATEGORIES")
        lines.append("-" * 60)
        
        for i, (category, emissions) in enumerate(result.highest_impact_categories, 1):
            percentage = (emissions / result.total_emissions_kg_co2e * 100) if result.total_emissions_kg_co2e > 0 else 0
            lines.append(f"{i}. {category.capitalize()}: {emissions:.2f} kg CO2e ({percentage:.1f}%)")
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 60)
        
        for i, rec in enumerate(result.recommendations, 1):
            lines.append(f"\n{i}. [{rec['priority'].upper()}] {rec['recommendation']}")
            lines.append(f"   Potential savings: {rec['potential_savings']:.2f} kg CO2e/year")
            lines.append("   Tips:")
            for tip in rec.get('tips', [])[:3]:  # Show top 3 tips
                lines.append(f"   • {tip}")
        
        lines.append("")
        lines.append("=" * 60)
        lines.append("END OF REPORT")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_json_report(result: EmissionResult) -> str:
        """Generate a JSON src.reporting.report."""
        data = {
            "total_emissions_kg_co2e": result.total_emissions_kg_co2e,
            "per_capita_emissions": result.per_capita_emissions,
            "percentile_ranking": result.percentile_ranking,
            "category_breakdown": result.category_breakdown.to_dict(),
            "highest_impact_categories": result.highest_impact_categories,
            "comparison_to_average": result.comparison_to_average,
            "recommendations": result.recommendations,
            "timestamp": result.timestamp,
            "calculation_version": result.calculation_version
        }
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def get_chart_data(result: EmissionResult) -> Dict[str, Any]:
        """Prepare data for visualization charts."""
        breakdown = result.category_breakdown.to_dict()
        
        # Pie chart data
        pie_data = {
            "labels": [cat.capitalize() for cat in breakdown.keys()],
            "values": [emissions for emissions in breakdown.values()],
            "colors": ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
        }
        
        # Bar chart data (comparison to average)
        if result.comparison_to_average:
            categories = list(result.comparison_to_average.keys())
            values = [result.comparison_to_average[cat] * 100 for cat in categories]
            bar_data = {
                "labels": [cat.capitalize() for cat in categories],
                "values": values,
                "title": "Category Comparison to Average (%)"
            }
        else:
            bar_data = None
        
        # Top recommendations by potential savings
        if result.recommendations:
            rec_data = {
                "labels": [rec["category"].capitalize() for rec in result.recommendations[:5]],
                "values": [rec["potential_savings"] for rec in result.recommendations[:5]],
                "title": "Potential Savings by Category (kg CO2e/year)"
            }
        else:
            rec_data = None
        
        return {
            "pie_chart": pie_data,
            "bar_chart": bar_data,
            "recommendation_chart": rec_data,
            "summary": {
                "total_emissions": result.total_emissions_kg_co2e,
                "per_capita": result.per_capita_emissions,
                "percentile": result.percentile_ranking
            }
        }


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class CarbonFootprintApp:
    """Main application class for the carbon footprint calculator."""
    
    def __init__(self):
        """Initialize the application."""
        self.engine = CarbonFootprintEngine()
        self.validator = InputValidator()
        self.persistence = DataPersistence()
        self.reporter = EmissionReporter()
        self.logger = logging.getLogger(f"{__name__}.CarbonFootprintApp")
    
    def create_default_profile(self) -> UserProfile:
        """Create a default user profile with typical values."""
        return UserProfile(
            user_id="default_user",
            age=35,
            gender="prefer_not_to_say",
            country="US",
            transportation=TransportationInput(
                mode=TransportationMode.CAR_PETROL,
                distance_km=20.0,
                frequency_per_week=5,
                occupancy=1
            ),
            energy=EnergyInput(
                electricity_kwh=3000.0,
                natural_gas_kwh=0.0,
                heating_oil_liters=0.0,
                energy_source=EnergySource.MIXED,
                renewable_percentage=10.0
            ),
            food=FoodInput(
                diet_type=DietType.OMNIVORE,
                meat_per_week_kg=2.0,
                dairy_per_week_kg=2.0,
                eggs_per_week=5,
                fish_per_week_kg=0.5,
                fruits_vegetables_per_week_kg=7.0,
                grains_per_week_kg=5.0,
                processed_foods_per_week_kg=2.0
            ),
            household=HouseholdInput(
                household_size=HouseholdSize.COUPLE,
                number_of_bedrooms=2,
                water_usage_liters_per_day=300.0,
                heating_type="gas",
                cooling_type="central_air"
            ),
            consumption=ConsumptionInput(
                clothing_annual_spend_usd=2000.0,
                electronics_annual_spend_usd=3000.0,
                furniture_annual_spend_usd=1500.0,
                personal_care_annual_spend_usd=1000.0,
                entertainment_annual_spend_usd=2000.0,
                books_magazines_annual_spend_usd=500.0
            ),
            waste=WasteInput(
                total_waste_kg_per_week=10.0,
                recycling_kg_per_week=3.0,
                composting_kg_per_week=2.0,
                landfill_kg_per_week=4.0,
                incineration_kg_per_week=1.0
            )
        )
    
    def calculate_footprint(self, profile: UserProfile) -> EmissionResult:
        """
        Calculate carbon footprint for a user profile.
        
        Args:
            profile: UserProfile object
            
        Returns:
            EmissionResult object
        """
        # Validate the profile
        is_valid, errors = self.validator.validate_user_profile(profile)
        
        if not is_valid:
            self.logger.warning(f"Validation errors: {errors}")
            # Continue with calculation but log warnings
        
        # Calculate emissions
        result = self.engine.calculate_full_profile(profile)
        
        # Save the calculation
        self.persistence.save_profile(profile)
        
        return result
    
    def run_interactive(self):
        """Run the application in interactive mode."""
        print("\n" + "=" * 60)
        print("ECOBUDDY - Multi-Factor Carbon Footprint Engine")
        print("=" * 60 + "\n")
        
        print("This tool will help you estimate your personal carbon footprint.")
        print("You'll be asked about your transportation, energy use, diet, and more.")
        print("\nPress Enter to continue or type 'quit' to exit.")
        
        response = input("\n> ").strip().lower()
        if response == 'quit':
            return
        
        # Create a basic profile
        profile = UserProfile()
        
        print("\n" + "-" * 40)
        print("Let's start with some basic information")
        print("-" * 40)
        
        try:
            age = input("Your age (optional): ").strip()
            if age:
                profile.age = int(age)
            
            country = input("Your country (optional, for regional adjustments): ").strip()
            if country:
                profile.country = country
        except ValueError as e:
            print(f"Error: {e}")
        
        print("\n" + "-" * 40)
        print("Now, let's calculate your carbon footprint!")
        print("-" * 40)
        
        # Create a simple profile with minimal data
        # In a real app, you would collect all data through a UI
        
        # For demo, use default profile with user's age and country
        default_profile = self.create_default_profile()
        if profile.age:
            default_profile.age = profile.age
        if profile.country:
            default_profile.country = profile.country
        
        print("\nCalculating your carbon footprint...")
        result = self.calculate_footprint(default_profile)
        
        # Generate and display report
        report = self.reporter.generate_text_report(result)
        print("\n" + report)
        
        # Ask if user wants to save the report
        save = input("\nSave report to file? (y/n): ").strip().lower()
        if save == 'y':
            filename = f"carbon_report_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(filename, 'w') as f:
                f.write(report)
            print(f"Report saved to {filename}")
        
        print("\nThank you for using EcoBuddy!")


# ============================================================================
# TEST CASES
# ============================================================================

def run_tests():
    """Run test cases for the carbon footprint engine."""
    print("\n" + "=" * 60)
    print("RUNNING TESTS")
    print("=" * 60 + "\n")
    
    app = CarbonFootprintApp()
    engine = app.engine
    
    # Test 1: Basic transportation calculation
    print("Test 1: Transportation Calculation")
    print("-" * 40)
    
    car_input = TransportationInput(
        mode=TransportationMode.CAR_PETROL,
        distance_km=30.0,
        frequency_per_week=5,
        occupancy=1
    )
    
    emissions = engine.calculate_transportation([car_input])
    print(f"Car emissions (30km/day, 5 days/week): {emissions:.2f} kg CO2e/year")
    assert emissions > 0, "Transportation emissions should be positive"
    print("✓ Test passed\n")
    
    # Test 2: Energy calculation
    print("Test 2: Energy Calculation")
    print("-" * 40)
    
    energy_input = EnergyInput(
        electricity_kwh=3000.0,
        natural_gas_kwh=0.0,
        heating_oil_liters=0.0,
        energy_source=EnergySource.MIXED,
        renewable_percentage=10.0
    )
    
    emissions = engine.calculate_energy(energy_input)
    print(f"Energy emissions (3000 kWh/year, 10% renewable): {emissions:.2f} kg CO2e/year")
    assert emissions > 0, "Energy emissions should be positive"
    print("✓ Test passed\n")
    
    # Test 3: Food calculation
    print("Test 3: Food Calculation")
    print("-" * 40)
    
    food_input = FoodInput(
        diet_type=DietType.OMNIVORE,
        meat_per_week_kg=2.0,
        dairy_per_week_kg=2.0,
        eggs_per_week=5,
        fish_per_week_kg=0.5,
        fruits_vegetables_per_week_kg=7.0,
        grains_per_week_kg=5.0,
        processed_foods_per_week_kg=2.0
    )
    
    emissions = engine.calculate_food(food_input)
    print(f"Food emissions (omnivore diet): {emissions:.2f} kg CO2e/year")
    assert emissions > 0, "Food emissions should be positive"
    print("✓ Test passed\n")
    
    # Test 4: Full profile calculation
    print("Test 4: Full Profile Calculation")
    print("-" * 40)
    
    profile = app.create_default_profile()
    result = app.calculate_footprint(profile)
    
    print(f"Total emissions: {result.total_emissions_kg_co2e:.2f} kg CO2e/year")
    print(f"Per capita: {result.per_capita_emissions:.2f} kg CO2e/year")
    print(f"Highest impact categories: {result.highest_impact_categories}")
    print(f"Number of recommendations: {len(result.recommendations)}")
    
    assert result.total_emissions_kg_co2e > 0, "Total emissions should be positive"
    assert len(result.highest_impact_categories) > 0, "Should have highest impact categories"
    assert len(result.recommendations) > 0, "Should have recommendations"
    print("✓ Test passed\n")
    
    # Test 5: Validation
    print("Test 5: Input Validation")
    print("-" * 40)
    
    invalid_profile = UserProfile(
        age=200,  # Invalid age
        country="Test",
        transportation=TransportationInput(
            mode=TransportationMode.CAR_PETROL,
            distance_km=-10.0,  # Invalid negative distance
            frequency_per_week=5,
            occupancy=1
        )
    )
    
    is_valid, errors = app.validator.validate_user_profile(invalid_profile)
    print(f"Is valid: {is_valid}")
    print(f"Errors found: {len(errors)}")
    assert not is_valid, "Profile should be invalid"
    assert len(errors) > 0, "Should have validation errors"
    print("✓ Test passed\n")
    
    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60 + "\n")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the application."""
    print("\n" + "=" * 60)
    print("ECOBUDDY - Carbon Footprint Engine v1.0.0")
    print("=" * 60 + "\n")
    
    print("Select an option:")
    print("1. Run interactive calculator")
    print("2. Run tests")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == '1':
        app = CarbonFootprintApp()
        app.run_interactive()
    elif choice == '2':
        run_tests()
    else:
        print("Goodbye!")


if __name__ == "__main__":
    main()
