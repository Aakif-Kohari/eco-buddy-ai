"""
src.lifestyle.lifestyle_input_validator.py
====================================
Carbon Footprint Lifestyle Input Validator
Version: 1.0.0

This module provides comprehensive validation for extreme lifestyle input values
to prevent unrealistic data from affecting carbon footprint calculations.
It validates all lifestyle parameters including dietary habits, transportation,
energy usage, waste management, and other carbon-impacting behaviors.

Author: Carbon Footprint Team
Date: 2026-08-27
"""

import re
import math
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from decimal import Decimal, ROUND_HALF_UP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Enumeration for validation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LifestyleCategory(Enum):
    """Enumeration for lifestyle input categories."""
    DIETARY = "dietary"
    TRANSPORTATION = "transportation"
    ENERGY = "energy"
    WASTE = "waste"
    WATER = "water"
    SHOPPING = "shopping"
    TRAVEL = "travel"
    HOUSING = "housing"
    HEALTH = "health"
    EDUCATION = "education"
    EMPLOYMENT = "employment"
    RECREATION = "recreation"
    COMMUNICATION = "communication"
    FINANCE = "finance"
    AGRICULTURE = "agriculture"


@dataclass
class ValidationRule:
    """Data class for validation rules."""
    field_name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    regex_pattern: Optional[str] = None
    custom_validator: Optional[callable] = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    message: str = ""
    category: LifestyleCategory = LifestyleCategory.DIETARY


@dataclass
class ValidationResult:
    """Data class for validation results."""
    is_valid: bool
    field_name: str
    value: Any
    severity: ValidationSeverity
    message: str
    suggestions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LifestyleProfile:
    """Data class representing a complete lifestyle profile."""
    profile_id: str
    user_id: str
    timestamp: datetime
    dietary: Dict[str, Any]
    transportation: Dict[str, Any]
    energy: Dict[str, Any]
    waste: Dict[str, Any]
    water: Dict[str, Any]
    shopping: Dict[str, Any]
    travel: Dict[str, Any]
    housing: Dict[str, Any]
    health: Dict[str, Any]
    education: Dict[str, Any]
    employment: Dict[str, Any]
    recreation: Dict[str, Any]
    communication: Dict[str, Any]
    finance: Dict[str, Any]
    agriculture: Dict[str, Any]


class ExtremeValueDetector:
    """
    Detects extreme values in lifestyle inputs using statistical methods.
    """
    
    def __init__(self):
        self._threshold_multiplier = 3.0
        self._historical_data = {}
        self._extreme_thresholds = {
            'daily_meat_consumption_kg': (0.0, 2.5),
            'daily_fruit_consumption_kg': (0.0, 3.0),
            'daily_vegetable_consumption_kg': (0.0, 4.0),
            'daily_water_consumption_liters': (0.5, 15.0),
            'daily_milk_consumption_liters': (0.0, 3.0),
            'weekly_eggs_consumed': (0, 42),
            'monthly_red_meat_kg': (0.0, 15.0),
            'monthly_poultry_kg': (0.0, 20.0),
            'monthly_fish_kg': (0.0, 15.0),
            'annual_vehicle_miles': (0, 100000),
            'annual_flights_taken': (0, 365),
            'annual_flight_hours': (0, 8760),
            'monthly_electricity_kwh': (0, 50000),
            'monthly_natural_gas_therms': (0, 3000),
            'monthly_heating_oil_gallons': (0, 2000),
            'annual_waste_generated_kg': (0, 50000),
            'annual_recycling_percentage': (0, 100),
            'daily_plastic_usage_kg': (0.0, 5.0),
            'monthly_water_usage_gallons': (0, 1000000),
            'daily_shower_minutes': (0, 120),
            'annual_clothing_purchases': (0, 1000),
            'monthly_electronics_purchases': (0, 100),
            'annual_home_square_footage': (0, 50000),
            'number_of_household_members': (0, 50),
            'daily_commute_miles': (0, 500),
            'weekly_public_transit_trips': (0, 200),
            'monthly_ride_share_trips': (0, 500),
            'annual_domestic_trips': (0, 365),
            'annual_international_trips': (0, 200),
            'annual_hotel_nights': (0, 3650),
            'daily_screen_time_hours': (0, 24),
            'daily_internet_usage_gb': (0, 1000),
            'monthly_data_usage_tb': (0, 100),
            'annual_healthcare_visits': (0, 1000),
            'monthly_prescriptions': (0, 100),
            'annual_education_hours': (0, 8760),
            'daily_work_hours': (0, 24),
            'annual_vacation_days': (0, 365),
            'monthly_entertainment_expenses_usd': (0, 100000),
            'annual_dining_out_meals': (0, 3650),
            'monthly_coffee_consumption_cups': (0, 1000),
            'daily_alcohol_consumption_units': (0, 50),
            'weekly_smoking_packs': (0, 50),
            'annual_paper_usage_kg': (0, 5000),
            'monthly_cleaning_products_liters': (0, 1000),
            'annual_gardening_expenses_usd': (0, 100000),
            'monthly_pet_food_kg': (0, 500),
            'annual_charitable_donations_usd': (0, 10000000)
        }
    
    def detect_extreme_value(self, field_name: str, value: Any) -> Tuple[bool, str]:
        """
        Detects if a value is extreme for a given field.
        
        Args:
            field_name: Name of the lifestyle field
            value: Value to check
            
        Returns:
            Tuple of (is_extreme, message)
        """
        if field_name in self._extreme_thresholds:
            min_val, max_val = self._extreme_thresholds[field_name]
            
            if isinstance(value, (int, float)):
                if value < min_val:
                    return True, f"Value {value} is below minimum threshold of {min_val}"
                if value > max_val:
                    return True, f"Value {value} exceeds maximum threshold of {max_val}"
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, (int, float)):
                        if item < min_val or item > max_val:
                            return True, f"Item {item} is outside range [{min_val}, {max_val}]"
        
        return False, "Value within acceptable range"
    
    def get_recommended_range(self, field_name: str) -> Tuple[float, float]:
        """
        Gets the recommended range for a field.
        
        Args:
            field_name: Name of the lifestyle field
            
        Returns:
            Tuple of (min, max) recommended values
        """
        if field_name in self._extreme_thresholds:
            return self._extreme_thresholds[field_name]
        return (0.0, float('inf'))


class LifestyleInputValidator:
    """
    Main validator class for lifestyle inputs.
    Validates all lifestyle parameters against extreme values.
    """
    
    def __init__(self):
        self.extreme_detector = ExtremeValueDetector()
        self.validation_rules = self._initialize_validation_rules()
        self.validation_history = []
        self._max_validation_history = 10000
    
    def _initialize_validation_rules(self) -> Dict[str, List[ValidationRule]]:
        """
        Initializes validation rules for all lifestyle categories.
        
        Returns:
            Dictionary mapping categories to lists of validation rules
        """
        rules = {}
        
        # DIETARY RULES
        dietary_rules = [
            ValidationRule(
                field_name="daily_meat_consumption_kg",
                min_value=0.0,
                max_value=2.5,
                message="Daily meat consumption should be between 0 and 2.5 kg",
                category=LifestyleCategory.DIETARY
            ),
            ValidationRule(
                field_name="daily_fruit_consumption_kg",
                min_value=0.0,
                max_value=3.0,
                message="Daily fruit consumption should be between 0 and 3 kg",
                category=LifestyleCategory.DIETARY
            ),
            ValidationRule(
                field_name="daily_vegetable_consumption_kg",
                min_value=0.0,
                max_value=4.0,
                message="Daily vegetable consumption should be between 0 and 4 kg",
                category=LifestyleCategory.DIETARY
            ),
            ValidationRule(
                field_name="daily_water_consumption_liters",
                min_value=0.5,
                max_value=15.0,
                message="Daily water consumption should be between 0.5 and 15 liters",
                category=LifestyleCategory.DIETARY
            ),
            ValidationRule(
                field_name="daily_milk_consumption_liters",
                min_value=0.0,
                max_value=3.0,
                message="Daily milk consumption should be between 0 and 3 liters",
                category=LifestyleCategory.DIETARY
            ),
            ValidationRule(
                field_name="weekly_eggs_consumed",
                min_value=0,
                max_value=42,
                message="Weekly egg consumption should be between 0 and 42 eggs",
                category=LifestyleCategory.DIETARY
            ),
            ValidationRule(
                field_name="monthly_red_meat_kg",
                min_value=0.0,
                max_value=15.0,
                message="Monthly red meat consumption should be between 0 and 15 kg",
                category=LifestyleCategory.DIETARY
            ),
            ValidationRule(
                field_name="monthly_poultry_kg",
                min_value=0.0,
                max_value=20.0,
                message="Monthly poultry consumption should be between 0 and 20 kg",
                category=LifestyleCategory.DIETARY
            ),
            ValidationRule(
                field_name="monthly_fish_kg",
                min_value=0.0,
                max_value=15.0,
                message="Monthly fish consumption should be between 0 and 15 kg",
                category=LifestyleCategory.DIETARY
            ),
            ValidationRule(
                field_name="dietary_preference",
                allowed_values=["omnivore", "pescatarian", "vegetarian", "vegan", "flexitarian"],
                message="Dietary preference must be one of: omnivore, pescatarian, vegetarian, vegan, flexitarian",
                category=LifestyleCategory.DIETARY
            ),
            ValidationRule(
                field_name="daily_sugar_consumption_grams",
                min_value=0.0,
                max_value=200.0,
                message="Daily sugar consumption should be between 0 and 200 grams",
                category=LifestyleCategory.DIETARY
            ),
            ValidationRule(
                field_name="daily_salt_consumption_grams",
                min_value=0.0,
                max_value=25.0,
                message="Daily salt consumption should be between 0 and 25 grams",
                category=LifestyleCategory.DIETARY
            ),
        ]
        rules[LifestyleCategory.DIETARY.value] = dietary_rules
        
        # TRANSPORTATION RULES
        transportation_rules = [
            ValidationRule(
                field_name="annual_vehicle_miles",
                min_value=0,
                max_value=100000,
                message="Annual vehicle miles should be between 0 and 100,000",
                category=LifestyleCategory.TRANSPORTATION
            ),
            ValidationRule(
                field_name="annual_flights_taken",
                min_value=0,
                max_value=365,
                message="Annual flights should be between 0 and 365",
                category=LifestyleCategory.TRANSPORTATION
            ),
            ValidationRule(
                field_name="annual_flight_hours",
                min_value=0,
                max_value=8760,
                message="Annual flight hours should be between 0 and 8760",
                category=LifestyleCategory.TRANSPORTATION
            ),
            ValidationRule(
                field_name="daily_commute_miles",
                min_value=0,
                max_value=500,
                message="Daily commute miles should be between 0 and 500",
                category=LifestyleCategory.TRANSPORTATION
            ),
            ValidationRule(
                field_name="weekly_public_transit_trips",
                min_value=0,
                max_value=200,
                message="Weekly public transit trips should be between 0 and 200",
                category=LifestyleCategory.TRANSPORTATION
            ),
            ValidationRule(
                field_name="monthly_ride_share_trips",
                min_value=0,
                max_value=500,
                message="Monthly ride-share trips should be between 0 and 500",
                category=LifestyleCategory.TRANSPORTATION
            ),
            ValidationRule(
                field_name="annual_domestic_trips",
                min_value=0,
                max_value=365,
                message="Annual domestic trips should be between 0 and 365",
                category=LifestyleCategory.TRANSPORTATION
            ),
            ValidationRule(
                field_name="annual_international_trips",
                min_value=0,
                max_value=200,
                message="Annual international trips should be between 0 and 200",
                category=LifestyleCategory.TRANSPORTATION
            ),
            ValidationRule(
                field_name="annual_hotel_nights",
                min_value=0,
                max_value=3650,
                message="Annual hotel nights should be between 0 and 3650",
                category=LifestyleCategory.TRANSPORTATION
            ),
            ValidationRule(
                field_name="vehicle_fuel_efficiency_mpg",
                min_value=5.0,
                max_value=150.0,
                message="Vehicle fuel efficiency should be between 5 and 150 MPG",
                category=LifestyleCategory.TRANSPORTATION
            ),
        ]
        rules[LifestyleCategory.TRANSPORTATION.value] = transportation_rules
        
        # ENERGY RULES
        energy_rules = [
            ValidationRule(
                field_name="monthly_electricity_kwh",
                min_value=0,
                max_value=50000,
                message="Monthly electricity usage should be between 0 and 50,000 kWh",
                category=LifestyleCategory.ENERGY
            ),
            ValidationRule(
                field_name="monthly_natural_gas_therms",
                min_value=0,
                max_value=3000,
                message="Monthly natural gas usage should be between 0 and 3,000 therms",
                category=LifestyleCategory.ENERGY
            ),
            ValidationRule(
                field_name="monthly_heating_oil_gallons",
                min_value=0,
                max_value=2000,
                message="Monthly heating oil usage should be between 0 and 2,000 gallons",
                category=LifestyleCategory.ENERGY
            ),
            ValidationRule(
                field_name="solar_panel_ownership",
                allowed_values=[True, False],
                message="Solar panel ownership must be True or False",
                category=LifestyleCategory.ENERGY
            ),
            ValidationRule(
                field_name="energy_efficient_appliances",
                allowed_values=[True, False],
                message="Energy efficient appliances must be True or False",
                category=LifestyleCategory.ENERGY
            ),
            ValidationRule(
                field_name="smart_thermostat_installed",
                allowed_values=[True, False],
                message="Smart thermostat installed must be True or False",
                category=LifestyleCategory.ENERGY
            ),
            ValidationRule(
                field_name="daily_hours_of_electricity_usage",
                min_value=0,
                max_value=24,
                message="Daily hours of electricity usage should be between 0 and 24",
                category=LifestyleCategory.ENERGY
            ),
        ]
        rules[LifestyleCategory.ENERGY.value] = energy_rules
        
        # WASTE RULES
        waste_rules = [
            ValidationRule(
                field_name="annual_waste_generated_kg",
                min_value=0,
                max_value=50000,
                message="Annual waste generated should be between 0 and 50,000 kg",
                category=LifestyleCategory.WASTE
            ),
            ValidationRule(
                field_name="annual_recycling_percentage",
                min_value=0,
                max_value=100,
                message="Recycling percentage should be between 0 and 100",
                category=LifestyleCategory.WASTE
            ),
            ValidationRule(
                field_name="daily_plastic_usage_kg",
                min_value=0.0,
                max_value=5.0,
                message="Daily plastic usage should be between 0 and 5 kg",
                category=LifestyleCategory.WASTE
            ),
            ValidationRule(
                field_name="composting_practice",
                allowed_values=[True, False],
                message="Composting practice must be True or False",
                category=LifestyleCategory.WASTE
            ),
            ValidationRule(
                field_name="monthly_e_waste_kg",
                min_value=0.0,
                max_value=500.0,
                message="Monthly e-waste should be between 0 and 500 kg",
                category=LifestyleCategory.WASTE
            ),
            ValidationRule(
                field_name="annual_hazardous_waste_kg",
                min_value=0.0,
                max_value=1000.0,
                message="Annual hazardous waste should be between 0 and 1000 kg",
                category=LifestyleCategory.WASTE
            ),
        ]
        rules[LifestyleCategory.WASTE.value] = waste_rules
        
        # WATER RULES
        water_rules = [
            ValidationRule(
                field_name="monthly_water_usage_gallons",
                min_value=0,
                max_value=1000000,
                message="Monthly water usage should be between 0 and 1,000,000 gallons",
                category=LifestyleCategory.WATER
            ),
            ValidationRule(
                field_name="daily_shower_minutes",
                min_value=0,
                max_value=120,
                message="Daily shower duration should be between 0 and 120 minutes",
                category=LifestyleCategory.WATER
            ),
            ValidationRule(
                field_name="rainwater_harvesting",
                allowed_values=[True, False],
                message="Rainwater harvesting must be True or False",
                category=LifestyleCategory.WATER
            ),
            ValidationRule(
                field_name="greywater_recycling",
                allowed_values=[True, False],
                message="Greywater recycling must be True or False",
                category=LifestyleCategory.WATER
            ),
            ValidationRule(
                field_name="low_flow_fixtures",
                allowed_values=[True, False],
                message="Low flow fixtures must be True or False",
                category=LifestyleCategory.WATER
            ),
        ]
        rules[LifestyleCategory.WATER.value] = water_rules
        
        # SHOPPING RULES
        shopping_rules = [
            ValidationRule(
                field_name="annual_clothing_purchases",
                min_value=0,
                max_value=1000,
                message="Annual clothing purchases should be between 0 and 1000 items",
                category=LifestyleCategory.SHOPPING
            ),
            ValidationRule(
                field_name="monthly_electronics_purchases",
                min_value=0,
                max_value=100,
                message="Monthly electronics purchases should be between 0 and 100 items",
                category=LifestyleCategory.SHOPPING
            ),
            ValidationRule(
                field_name="annual_dining_out_meals",
                min_value=0,
                max_value=3650,
                message="Annual dining out meals should be between 0 and 3650",
                category=LifestyleCategory.SHOPPING
            ),
            ValidationRule(
                field_name="monthly_coffee_consumption_cups",
                min_value=0,
                max_value=1000,
                message="Monthly coffee consumption should be between 0 and 1000 cups",
                category=LifestyleCategory.SHOPPING
            ),
            ValidationRule(
                field_name="annual_paper_usage_kg",
                min_value=0.0,
                max_value=5000.0,
                message="Annual paper usage should be between 0 and 5000 kg",
                category=LifestyleCategory.SHOPPING
            ),
            ValidationRule(
                field_name="monthly_cleaning_products_liters",
                min_value=0.0,
                max_value=1000.0,
                message="Monthly cleaning products should be between 0 and 1000 liters",
                category=LifestyleCategory.SHOPPING
            ),
        ]
        rules[LifestyleCategory.SHOPPING.value] = shopping_rules
        
        # TRAVEL RULES
        travel_rules = [
            ValidationRule(
                field_name="annual_domestic_trips",
                min_value=0,
                max_value=365,
                message="Annual domestic trips should be between 0 and 365",
                category=LifestyleCategory.TRAVEL
            ),
            ValidationRule(
                field_name="annual_international_trips",
                min_value=0,
                max_value=200,
                message="Annual international trips should be between 0 and 200",
                category=LifestyleCategory.TRAVEL
            ),
            ValidationRule(
                field_name="annual_hotel_nights",
                min_value=0,
                max_value=3650,
                message="Annual hotel nights should be between 0 and 3650",
                category=LifestyleCategory.TRAVEL
            ),
            ValidationRule(
                field_name="preferred_accommodation",
                allowed_values=["hotel", "hostel", "airbnb", "camping", "luxury_resort", "eco_lodge"],
                message="Preferred accommodation must be one of: hotel, hostel, airbnb, camping, luxury_resort, eco_lodge",
                category=LifestyleCategory.TRAVEL
            ),
        ]
        rules[LifestyleCategory.TRAVEL.value] = travel_rules
        
        # HOUSING RULES
        housing_rules = [
            ValidationRule(
                field_name="annual_home_square_footage",
                min_value=0,
                max_value=50000,
                message="Home square footage should be between 0 and 50,000",
                category=LifestyleCategory.HOUSING
            ),
            ValidationRule(
                field_name="number_of_household_members",
                min_value=0,
                max_value=50,
                message="Number of household members should be between 0 and 50",
                category=LifestyleCategory.HOUSING
            ),
            ValidationRule(
                field_name="home_insulation_rating",
                min_value=0.0,
                max_value=100.0,
                message="Home insulation rating should be between 0 and 100",
                category=LifestyleCategory.HOUSING
            ),
            ValidationRule(
                field_name="home_ownership_status",
                allowed_values=["owned", "rented", "shared", "other"],
                message="Home ownership status must be one of: owned, rented, shared, other",
                category=LifestyleCategory.HOUSING
            ),
        ]
        rules[LifestyleCategory.HOUSING.value] = housing_rules
        
        # HEALTH RULES
        health_rules = [
            ValidationRule(
                field_name="annual_healthcare_visits",
                min_value=0,
                max_value=1000,
                message="Annual healthcare visits should be between 0 and 1000",
                category=LifestyleCategory.HEALTH
            ),
            ValidationRule(
                field_name="monthly_prescriptions",
                min_value=0,
                max_value=100,
                message="Monthly prescriptions should be between 0 and 100",
                category=LifestyleCategory.HEALTH
            ),
            ValidationRule(
                field_name="daily_alcohol_consumption_units",
                min_value=0,
                max_value=50,
                message="Daily alcohol consumption should be between 0 and 50 units",
                category=LifestyleCategory.HEALTH
            ),
            ValidationRule(
                field_name="weekly_smoking_packs",
                min_value=0,
                max_value=50,
                message="Weekly smoking should be between 0 and 50 packs",
                category=LifestyleCategory.HEALTH
            ),
            ValidationRule(
                field_name="daily_exercise_minutes",
                min_value=0,
                max_value=1440,
                message="Daily exercise minutes should be between 0 and 1440",
                category=LifestyleCategory.HEALTH
            ),
        ]
        rules[LifestyleCategory.HEALTH.value] = health_rules
        
        # EDUCATION RULES
        education_rules = [
            ValidationRule(
                field_name="annual_education_hours",
                min_value=0,
                max_value=8760,
                message="Annual education hours should be between 0 and 8760",
                category=LifestyleCategory.EDUCATION
            ),
            ValidationRule(
                field_name="highest_education_level",
                allowed_values=["high_school", "bachelors", "masters", "phd", "professional"],
                message="Education level must be one of: high_school, bachelors, masters, phd, professional",
                category=LifestyleCategory.EDUCATION
            ),
        ]
        rules[LifestyleCategory.EDUCATION.value] = education_rules
        
        # EMPLOYMENT RULES
        employment_rules = [
            ValidationRule(
                field_name="daily_work_hours",
                min_value=0,
                max_value=24,
                message="Daily work hours should be between 0 and 24",
                category=LifestyleCategory.EMPLOYMENT
            ),
            ValidationRule(
                field_name="annual_vacation_days",
                min_value=0,
                max_value=365,
                message="Annual vacation days should be between 0 and 365",
                category=LifestyleCategory.EMPLOYMENT
            ),
            ValidationRule(
                field_name="work_from_home_days_per_week",
                min_value=0,
                max_value=7,
                message="Work from home days per week should be between 0 and 7",
                category=LifestyleCategory.EMPLOYMENT
            ),
        ]
        rules[LifestyleCategory.EMPLOYMENT.value] = employment_rules
        
        # RECREATION RULES
        recreation_rules = [
            ValidationRule(
                field_name="monthly_entertainment_expenses_usd",
                min_value=0,
                max_value=100000,
                message="Monthly entertainment expenses should be between 0 and 100,000 USD",
                category=LifestyleCategory.RECREATION
            ),
            ValidationRule(
                field_name="annual_gardening_expenses_usd",
                min_value=0,
                max_value=100000,
                message="Annual gardening expenses should be between 0 and 100,000 USD",
                category=LifestyleCategory.RECREATION
            ),
            ValidationRule(
                field_name="monthly_pet_food_kg",
                min_value=0.0,
                max_value=500.0,
                message="Monthly pet food should be between 0 and 500 kg",
                category=LifestyleCategory.RECREATION
            ),
        ]
        rules[LifestyleCategory.RECREATION.value] = recreation_rules
        
        # COMMUNICATION RULES
        communication_rules = [
            ValidationRule(
                field_name="daily_screen_time_hours",
                min_value=0,
                max_value=24,
                message="Daily screen time should be between 0 and 24 hours",
                category=LifestyleCategory.COMMUNICATION
            ),
            ValidationRule(
                field_name="daily_internet_usage_gb",
                min_value=0,
                max_value=1000,
                message="Daily internet usage should be between 0 and 1000 GB",
                category=LifestyleCategory.COMMUNICATION
            ),
            ValidationRule(
                field_name="monthly_data_usage_tb",
                min_value=0,
                max_value=100,
                message="Monthly data usage should be between 0 and 100 TB",
                category=LifestyleCategory.COMMUNICATION
            ),
        ]
        rules[LifestyleCategory.COMMUNICATION.value] = communication_rules
        
        # FINANCE RULES
        finance_rules = [
            ValidationRule(
                field_name="annual_charitable_donations_usd",
                min_value=0,
                max_value=10000000,
                message="Annual charitable donations should be between 0 and 10,000,000 USD",
                category=LifestyleCategory.FINANCE
            ),
            ValidationRule(
                field_name="monthly_investment_amount_usd",
                min_value=0,
                max_value=100000000,
                message="Monthly investment amount should be between 0 and 100,000,000 USD",
                category=LifestyleCategory.FINANCE
            ),
        ]
        rules[LifestyleCategory.FINANCE.value] = finance_rules
        
        # AGRICULTURE RULES
        agriculture_rules = [
            ValidationRule(
                field_name="annual_fertilizer_usage_kg",
                min_value=0.0,
                max_value=100000.0,
                message="Annual fertilizer usage should be between 0 and 100,000 kg",
                category=LifestyleCategory.AGRICULTURE
            ),
            ValidationRule(
                field_name="annual_pesticide_usage_liters",
                min_value=0.0,
                max_value=10000.0,
                message="Annual pesticide usage should be between 0 and 10,000 liters",
                category=LifestyleCategory.AGRICULTURE
            ),
            ValidationRule(
                field_name="farm_size_acres",
                min_value=0.0,
                max_value=100000.0,
                message="Farm size should be between 0 and 100,000 acres",
                category=LifestyleCategory.AGRICULTURE
            ),
        ]
        rules[LifestyleCategory.AGRICULTURE.value] = agriculture_rules
        
        return rules
    
    def validate_field(self, field_name: str, value: Any, category: Optional[str] = None) -> ValidationResult:
        """
        Validates a single field against its validation rules.
        
        Args:
            field_name: Name of the field to validate
            value: Value to validate
            category: Optional category to restrict validation to
            
        Returns:
            ValidationResult object
        """
        # Find applicable rules
        applicable_rules = []
        if category and category in self.validation_rules:
            applicable_rules = [rule for rule in self.validation_rules[category] if rule.field_name == field_name]
        else:
            for cat_rules in self.validation_rules.values():
                for rule in cat_rules:
                    if rule.field_name == field_name:
                        applicable_rules.append(rule)
        
        if not applicable_rules:
            # No specific rule found, use extreme value detection
            is_extreme, message = self.extreme_detector.detect_extreme_value(field_name, value)
            severity = ValidationSeverity.WARNING if is_extreme else ValidationSeverity.INFO
            return ValidationResult(
                is_valid=not is_extreme,
                field_name=field_name,
                value=value,
                severity=severity,
                message=message if is_extreme else "No validation rule found for this field"
            )
        
        # Apply all applicable rules
        for rule in applicable_rules:
            result = self._apply_rule(rule, value)
            if not result.is_valid:
                return result
        
        return ValidationResult(
            is_valid=True,
            field_name=field_name,
            value=value,
            severity=ValidationSeverity.INFO,
            message="Validation passed"
        )
    
    def _apply_rule(self, rule: ValidationRule, value: Any) -> ValidationResult:
        """
        Applies a single validation rule to a value.
        
        Args:
            rule: ValidationRule to apply
            value: Value to validate
            
        Returns:
            ValidationResult object
        """
        suggestions = []
        
        # Check if value exists
        if value is None:
            return ValidationResult(
                is_valid=False,
                field_name=rule.field_name,
                value=value,
                severity=ValidationSeverity.ERROR,
                message=f"Value for {rule.field_name} is required",
                suggestions=["Provide a valid value"]
            )
        
        # Type checking
        if rule.min_value is not None or rule.max_value is not None:
            if not isinstance(value, (int, float)):
                return ValidationResult(
                    is_valid=False,
                    field_name=rule.field_name,
                    value=value,
                    severity=ValidationSeverity.ERROR,
                    message=f"Value for {rule.field_name} must be numeric",
                    suggestions=[f"Provide a numeric value between {rule.min_value} and {rule.max_value}"]
                )
        
        # Range validation
        if rule.min_value is not None and value < rule.min_value:
            suggestions.append(f"Value should be at least {rule.min_value}")
            return ValidationResult(
                is_valid=False,
                field_name=rule.field_name,
                value=value,
                severity=rule.severity,
                message=rule.message or f"Value {value} is below minimum of {rule.min_value}",
                suggestions=suggestions
            )
        
        if rule.max_value is not None and value > rule.max_value:
            suggestions.append(f"Value should be at most {rule.max_value}")
            return ValidationResult(
                is_valid=False,
                field_name=rule.field_name,
                value=value,
                severity=rule.severity,
                message=rule.message or f"Value {value} exceeds maximum of {rule.max_value}",
                suggestions=suggestions
            )
        
        # Allowed values validation
        if rule.allowed_values is not None and value not in rule.allowed_values:
            suggestions.append(f"Value should be one of: {', '.join(map(str, rule.allowed_values))}")
            return ValidationResult(
                is_valid=False,
                field_name=rule.field_name,
                value=value,
                severity=ValidationSeverity.ERROR,
                message=f"Value {value} is not allowed",
                suggestions=suggestions
            )
        
        # Regex pattern validation
        if rule.regex_pattern is not None and isinstance(value, str):
            if not re.match(rule.regex_pattern, value):
                suggestions.append(f"Value should match pattern: {rule.regex_pattern}")
                return ValidationResult(
                    is_valid=False,
                    field_name=rule.field_name,
                    value=value,
                    severity=ValidationSeverity.ERROR,
                    message=f"Value {value} does not match required pattern",
                    suggestions=suggestions
                )
        
        # Custom validator
        if rule.custom_validator is not None:
            try:
                custom_result = rule.custom_validator(value)
                if custom_result is not None and not custom_result:
                    return ValidationResult(
                        is_valid=False,
                        field_name=rule.field_name,
                        value=value,
                        severity=ValidationSeverity.ERROR,
                        message="Custom validation failed",
                        suggestions=["Review the custom validation requirements"]
                    )
            except Exception as e:
                logger.error(f"Custom validator for {rule.field_name} raised error: {str(e)}")
                return ValidationResult(
                    is_valid=False,
                    field_name=rule.field_name,
                    value=value,
                    severity=ValidationSeverity.ERROR,
                    message=f"Custom validation error: {str(e)}",
                    suggestions=["Contact support for assistance"]
                )
        
        # Additional extreme value detection
        is_extreme, extreme_msg = self.extreme_detector.detect_extreme_value(rule.field_name, value)
        if is_extreme:
            return ValidationResult(
                is_valid=False,
                field_name=rule.field_name,
                value=value,
                severity=ValidationSeverity.WARNING,
                message=extreme_msg,
                suggestions=["Review the entered value for accuracy"]
            )
            
        return ValidationResult(
            is_valid=True,
            field_name=rule.field_name,
            value=value,
            severity=ValidationSeverity.INFO
        )
