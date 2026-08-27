"""
src.lifestyle.seasonal_eco_recommendations.py
====================================
Season-Based Eco Recommendations Module
Version: 1.0.0

This module provides sustainability recommendations based on seasons:
- Seasonal weather adaptation
- Energy usage optimization
- Seasonal food and diet suggestions
- Travel and activity recommendations
- Conservation and nature-based activities
- Holiday and event-specific guidance

Author: Carbon Footprint Team
Date: 2026-08-27
"""

import json
import logging
import math
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import random
from decimal import Decimal, ROUND_HALF_UP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Season(Enum):
    """Enumeration of seasons."""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"
    ALL_YEAR = "all_year"


class Hemisphere(Enum):
    """Enumeration of hemispheres."""
    NORTHERN = "northern"
    SOUTHERN = "southern"
    EQUATORIAL = "equatorial"


class RecommendationCategory(Enum):
    """Enumeration of recommendation categories."""
    ENERGY = "energy"
    FOOD = "food"
    TRAVEL = "travel"
    CONSERVATION = "conservation"
    WEATHER_ADAPTATION = "weather_adaptation"
    HOLIDAYS = "holidays"
    GARDENING = "gardening"
    WATER = "water"
    WASTE = "waste"
    TRANSPORTATION = "transportation"
    HOME_MAINTENANCE = "home_maintenance"
    HEALTH = "health"
    SHOPPING = "shopping"
    OUTDOOR_ACTIVITIES = "outdoor_activities"


class RecommendationPriority(Enum):
    """Enumeration of recommendation priorities."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


class ImpactLevel(Enum):
    """Enumeration of impact levels."""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class SeasonalRecommendation:
    """Data class for seasonal src.ai.recommendations."""
    recommendation_id: str
    category: RecommendationCategory
    title: str
    description: str
    season: Season
    priority: RecommendationPriority
    impact_level: ImpactLevel
    estimated_savings: Dict[str, float]  # e.g., {"co2_kg": 50, "water_liters": 100}
    implementation_difficulty: int  # 1-10
    time_required: str  # e.g., "30 minutes", "2 hours"
    cost_estimate_usd: float
    tips: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    related_actions: List[str] = field(default_factory=list)
    regional_variations: Dict[str, str] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    verification_method: Optional[str] = None


@dataclass
class SeasonalFoodGuide:
    """Data class for seasonal food guide."""
    season: Season
    vegetables: List[Dict[str, str]]
    fruits: List[Dict[str, str]]
    herbs: List[str]
    recipes: List[Dict[str, Any]]
    preservation_tips: List[str]
    nutritional_highlights: List[str]
    local_sourcing_tips: List[str]


@dataclass
class SeasonalEnergyGuide:
    """Data class for seasonal energy guide."""
    season: Season
    heating_tips: List[str]
    cooling_tips: List[str]
    lighting_tips: List[str]
    insulation_tips: List[str]
    appliance_tips: List[str]
    expected_savings_percent: float
    renewable_energy_tips: List[str]
    smart_home_suggestions: List[str]


@dataclass
class SeasonalActivityGuide:
    """Data class for seasonal activities."""
    season: Season
    indoor_activities: List[Dict[str, str]]
    outdoor_activities: List[Dict[str, str]]
    conservation_activities: List[Dict[str, str]]
    community_activities: List[Dict[str, str]]
    family_friendly: List[Dict[str, str]]
    safety_tips: List[str]
    required_gear: List[str]


@dataclass
class SeasonalHolidayGuide:
    """Data class for seasonal holiday guide."""
    holiday_name: str
    season: Season
    sustainable_celebration_tips: List[str]
    eco_gift_ideas: List[str]
    waste_reduction_tips: List[str]
    carbon_friendly_travel: List[str]
    local_traditions: List[str]
    meal_planning: List[str]


@dataclass
class SeasonalWeatherGuide:
    """Data class for seasonal weather adaptation."""
    season: Season
    average_temperature_range: Tuple[float, float]
    weather_patterns: List[str]
    climate_adaptation_tips: List[str]
    emergency_preparedness: List[str]
    home_protection_tips: List[str]
    health_advisory: List[str]
    resource_conservation: List[str]


class SeasonDetector:
    """
    Detects current season based on date and hemisphere.
    """
    
    def __init__(self):
        self._season_boundaries = {
            Hemisphere.NORTHERN: {
                Season.SPRING: (3, 20, 6, 20),
                Season.SUMMER: (6, 21, 9, 22),
                Season.AUTUMN: (9, 23, 12, 20),
                Season.WINTER: (12, 21, 3, 19)
            },
            Hemisphere.SOUTHERN: {
                Season.SPRING: (9, 23, 12, 20),
                Season.SUMMER: (12, 21, 3, 19),
                Season.AUTUMN: (3, 20, 6, 20),
                Season.WINTER: (6, 21, 9, 22)
            },
            Hemisphere.EQUATORIAL: {
                Season.SPRING: (1, 1, 12, 31),
                Season.SUMMER: (1, 1, 12, 31),
                Season.AUTUMN: (1, 1, 12, 31),
                Season.WINTER: (1, 1, 12, 31)
            }
        }
    
    def detect_season(self, target_date: Optional[date] = None, 
                     hemisphere: Hemisphere = Hemisphere.NORTHERN) -> Season:
        """
        Detects the season for a given date and hemisphere.
        
        Args:
            target_date: Date to check (defaults to today)
            hemisphere: Hemisphere for season calculation
            
        Returns:
            Season enum
        """
        if target_date is None:
            target_date = date.today()
        
        # Equatorial regions have minimal seasonal variation
        if hemisphere == Hemisphere.EQUATORIAL:
            return Season.ALL_YEAR
        
        month = target_date.month
        day = target_date.day
        
        boundaries = self._season_boundaries[hemisphere]
        
        for season, (start_month, start_day, end_month, end_day) in boundaries.items():
            if self._is_date_in_range(target_date, start_month, start_day, end_month, end_day):
                return season
        
        # Fallback to approximate season
        if month in [12, 1, 2]:
            return Season.WINTER
        elif month in [3, 4, 5]:
            return Season.SPRING
        elif month in [6, 7, 8]:
            return Season.SUMMER
        else:
            return Season.AUTUMN
    
    def _is_date_in_range(self, target_date: date, start_month: int, start_day: int,
                         end_month: int, end_day: int) -> bool:
        """
        Checks if a date falls within a season range.
        
        Args:
            target_date: Date to check
            start_month: Season start month
            start_day: Season start day
            end_month: Season end month
            end_day: Season end day
            
        Returns:
            True if date is in range
        """
        # Handle date ranges that cross year boundaries (e.g., winter)
        if start_month <= end_month:
            # Same year range
            start_date = date(target_date.year, start_month, start_day)
            end_date = date(target_date.year, end_month, end_day)
            return start_date <= target_date <= end_date
        else:
            # Cross-year range (e.g., Dec 21 to Mar 19)
            if target_date.month >= start_month or target_date.month <= end_month:
                return True
            return False
    
    def get_season_weeks(self, season: Season, hemisphere: Hemisphere = Hemisphere.NORTHERN) -> int:
        """
        Gets the approximate number of weeks in a season.
        
        Args:
            season: Season enum
            hemisphere: Hemisphere
            
        Returns:
            Number of weeks
        """
        if hemisphere == Hemisphere.EQUATORIAL:
            return 52
        
        season_weeks = {
            Season.SPRING: 13,
            Season.SUMMER: 13,
            Season.AUTUMN: 13,
            Season.WINTER: 13
        }
        
        return season_weeks.get(season, 13)
    
    def get_monthly_season_transition(self, month: int, 
                                     hemisphere: Hemisphere = Hemisphere.NORTHERN) -> Dict[str, float]:
        """
        Gets seasonal transition probabilities for a given month.
        
        Args:
            month: Month number (1-12)
            hemisphere: Hemisphere
            
        Returns:
            Dictionary with season probabilities
        """
        if hemisphere == Hemisphere.EQUATORIAL:
            return {Season.ALL_YEAR.value: 1.0}
        
        # Northern hemisphere seasonal transitions
        if hemisphere == Hemisphere.NORTHERN:
            transitions = {
                1: {Season.WINTER.value: 0.9, Season.SPRING.value: 0.1},
                2: {Season.WINTER.value: 0.7, Season.SPRING.value: 0.3},
                3: {Season.WINTER.value: 0.3, Season.SPRING.value: 0.7},
                4: {Season.SPRING.value: 0.9, Season.SUMMER.value: 0.1},
                5: {Season.SPRING.value: 0.7, Season.SUMMER.value: 0.3},
                6: {Season.SPRING.value: 0.2, Season.SUMMER.value: 0.8},
                7: {Season.SUMMER.value: 0.9, Season.AUTUMN.value: 0.1},
                8: {Season.SUMMER.value: 0.7, Season.AUTUMN.value: 0.3},
                9: {Season.SUMMER.value: 0.2, Season.AUTUMN.value: 0.8},
                10: {Season.AUTUMN.value: 0.9, Season.WINTER.value: 0.1},
                11: {Season.AUTUMN.value: 0.7, Season.WINTER.value: 0.3},
                12: {Season.AUTUMN.value: 0.2, Season.WINTER.value: 0.8}
            }
        else:  # Southern hemisphere
            # Reverse the seasons (offset by 6 months)
            transitions = {
                1: {Season.SUMMER.value: 0.9, Season.AUTUMN.value: 0.1},
                2: {Season.SUMMER.value: 0.7, Season.AUTUMN.value: 0.3},
                3: {Season.SUMMER.value: 0.2, Season.AUTUMN.value: 0.8},
                4: {Season.AUTUMN.value: 0.9, Season.WINTER.value: 0.1},
                5: {Season.AUTUMN.value: 0.7, Season.WINTER.value: 0.3},
                6: {Season.AUTUMN.value: 0.2, Season.WINTER.value: 0.8},
                7: {Season.WINTER.value: 0.9, Season.SPRING.value: 0.1},
                8: {Season.WINTER.value: 0.7, Season.SPRING.value: 0.3},
                9: {Season.WINTER.value: 0.2, Season.SPRING.value: 0.8},
                10: {Season.SPRING.value: 0.9, Season.SUMMER.value: 0.1},
                11: {Season.SPRING.value: 0.7, Season.SUMMER.value: 0.3},
                12: {Season.SPRING.value: 0.2, Season.SUMMER.value: 0.8}
            }
        
        return transitions.get(month, {Season.ALL_YEAR.value: 1.0})


class SeasonalRecommendationEngine:
    """
    Main engine for generating seasonal src.ai.recommendations.
    """
    
    def __init__(self):
        self._season_detector = SeasonDetector()
        self._recommendations = self._initialize_recommendations()
        self._food_guides = self._initialize_food_guides()
        self._energy_guides = self._initialize_energy_guides()
        self._activity_guides = self._initialize_activity_guides()
        self._holiday_guides = self._initialize_holiday_guides()
        self._weather_guides = self._initialize_weather_guides()
    
    def _initialize_recommendations(self) -> Dict[Season, List[SeasonalRecommendation]]:
        """
        Initializes seasonal src.ai.recommendations.
        
        Returns:
            Dictionary mapping seasons to recommendation lists
        """
        recommendations = {
            Season.SPRING: [],
            Season.SUMMER: [],
            Season.AUTUMN: [],
            Season.WINTER: [],
            Season.ALL_YEAR: []
        }
        
        # SPRING RECOMMENDATIONS
        spring_recs = [
            SeasonalRecommendation(
                recommendation_id="SPR001",
                category=RecommendationCategory.GARDENING,
                title="Start a Spring Garden",
                description="Plant native flowers and vegetables to support local pollinators and reduce food miles.",
                season=Season.SPRING,
                priority=RecommendationPriority.HIGH,
                impact_level=ImpactLevel.HIGH,
                estimated_savings={"co2_kg": 50, "water_liters": 1000},
                implementation_difficulty=3,
                time_required="3-5 hours initial setup",
                cost_estimate_usd=50,
                tips=[
                    "Choose plants that are native to your region",
                    "Start with easy-to-grow vegetables like tomatoes and lettuce",
                    "Companion planting can naturally deter pests",
                    "Water plants in the morning to reduce evaporation"
                ],
                resources=["https://nativeplantfinder.org", "https://gardening.org"],
                related_actions=["Compost kitchen scraps", "Set up a rain barrel"]
            ),
            SeasonalRecommendation(
                recommendation_id="SPR002",
                category=RecommendationCategory.ENERGY,
                title="Spring Energy Audit",
                description="Conduct a home energy audit to identify areas for improvement as weather warms up.",
                season=Season.SPRING,
                priority=RecommendationPriority.HIGH,
                impact_level=ImpactLevel.HIGH,
                estimated_savings={"co2_kg": 200, "energy_kwh": 500},
                implementation_difficulty=2,
                time_required="2-4 hours",
                cost_estimate_usd=25,
                tips=[
                    "Check for air leaks around windows and doors",
                    "Inspect insulation in attic and walls",
                    "Test HVAC system efficiency",
                    "Look for drafts and seal them"
                ],
                resources=["https://energy.gov/audit", "https://homeenergy.org"],
                related_actions=["Switch to LED bulbs", "Install a smart thermostat"]
            ),
            SeasonalRecommendation(
                recommendation_id="SPR003",
                category=RecommendationCategory.FOOD,
                title="Embrace Spring Seasonal Eating",
                description="Choose fresh spring produce like asparagus, strawberries, and leafy greens.",
                season=Season.SPRING,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"co2_kg": 30, "food_miles": 500},
                implementation_difficulty=1,
                time_required="Weekly planning",
                cost_estimate_usd=10,
                tips=[
                    "Visit local farmers markets",
                    "Buy in season for better flavor and nutrition",
                    "Preserve excess produce for later",
                    "Start a herb garden on your windowsill"
                ],
                resources=["https://seasonalfoodguide.org", "https://localharvest.org"],
                related_actions=["Compost food scraps", "Plan meals around seasonal produce"]
            ),
            SeasonalRecommendation(
                recommendation_id="SPR004",
                category=RecommendationCategory.WATER,
                title="Spring Rainwater Collection",
                description="Set up a rain barrel system to collect water for your garden.",
                season=Season.SPRING,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"water_liters": 5000},
                implementation_difficulty=4,
                time_required="4-6 hours",
                cost_estimate_usd=150,
                tips=[
                    "Place barrel under a downspout",
                    "Install a diverter to control flow",
                    "Add a screen to keep debris out",
                    "Use collected water within 2 weeks to prevent stagnation"
                ],
                resources=["https://rainwaterharvesting.org"],
                related_actions=["Install water-efficient fixtures", "Mulch garden beds"]
            ),
            SeasonalRecommendation(
                recommendation_id="SPR005",
                category=RecommendationCategory.TRANSPORTATION,
                title="Spring Bicycle Tune-Up",
                description="Get your bicycle ready for spring and summer commuting to reduce car src.carbon.emissions.",
                season=Season.SPRING,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"co2_kg": 100, "fuel_liters": 50},
                implementation_difficulty=2,
                time_required="1-2 hours",
                cost_estimate_usd=40,
                tips=[
                    "Check tire pressure and tread",
                    "Lubricate chain and moving parts",
                    "Test brakes and gears",
                    "Clean and inspect for wear"
                ],
                resources=["https://bicyclemaintenance.org"],
                related_actions=["Plan bike-safe routes", "Join a bike commuter group"]
            )
        ]
        
        # SUMMER RECOMMENDATIONS
        summer_recs = [
            SeasonalRecommendation(
                recommendation_id="SUM001",
                category=RecommendationCategory.ENERGY,
                title="Maximize Summer Energy Efficiency",
                description="Reduce cooling costs with smart strategies and energy-efficient practices.",
                season=Season.SUMMER,
                priority=RecommendationPriority.HIGH,
                impact_level=ImpactLevel.VERY_HIGH,
                estimated_savings={"co2_kg": 300, "energy_kwh": 800},
                implementation_difficulty=3,
                time_required="3-5 hours",
                cost_estimate_usd=100,
                tips=[
                    "Set thermostat to 78°F (25.5°C) when home",
                    "Use ceiling fans to feel cooler",
                    "Close blinds during peak sun hours",
                    "Cook outdoors to reduce indoor heat",
                    "Use a programmable thermostat"
                ],
                resources=["https://energy.gov/cooling", "https://summerenergy.org"],
                related_actions=["Install solar panels", "Plant shade trees"],
                regional_variations={
                    "desert": "Consider evaporative coolers",
                    "humid": "Use dehumidifiers to improve comfort"
                }
            ),
            SeasonalRecommendation(
                recommendation_id="SUM002",
                category=RecommendationCategory.CONSERVATION,
                title="Summer Water Conservation",
                description="Reduce water usage during peak summer months with smart practices.",
                season=Season.SUMMER,
                priority=RecommendationPriority.HIGH,
                impact_level=ImpactLevel.HIGH,
                estimated_savings={"water_liters": 20000},
                implementation_difficulty=2,
                time_required="2-3 hours",
                cost_estimate_usd=30,
                tips=[
                    "Water garden early morning or late evening",
                    "Use drip irrigation systems",
                    "Collect shower warm-up water for plants",
                    "Fix leaky faucets and irrigation",
                    "Use mulch to retain moisture"
                ],
                resources=["https://waterconservation.org"],
                related_actions=["Install rain barrels", "Choose drought-resistant plants"]
            ),
            SeasonalRecommendation(
                recommendation_id="SUM003",
                category=RecommendationCategory.TRAVEL,
                title="Eco-Friendly Summer Travel",
                description="Plan sustainable summer vacations with lower carbon footprint.",
                season=Season.SUMMER,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"co2_kg": 500},
                implementation_difficulty=4,
                time_required="2-4 weeks planning",
                cost_estimate_usd=200,
                tips=[
                    "Choose destinations closer to home",
                    "Use trains instead of flights when possible",
                    "Stay in eco-friendly accommodations",
                    "Support local businesses at destinations",
                    "Offset your travel carbon emissions"
                ],
                resources=["https://ecotravel.org", "https://responsibletravel.com"],
                related_actions=["Pack light", "Use public transport"]
            ),
            SeasonalRecommendation(
                recommendation_id="SUM004",
                category=RecommendationCategory.FOOD,
                title="Summer Fresh Eating",
                description="Enjoy abundant summer produce while reducing your food carbon footprint.",
                season=Season.SUMMER,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"co2_kg": 40, "food_miles": 800},
                implementation_difficulty=1,
                time_required="Weekly planning",
                cost_estimate_usd=15,
                tips=[
                    "Visit U-pick farms for fresh berries",
                    "Can and preserve summer fruits",
                    "Make refreshing summer salads",
                    "Freeze excess produce for winter"
                ],
                resources=["https://summerfoodguide.org"],
                related_actions=["Start a container garden", "Join a CSA"]
            ),
            SeasonalRecommendation(
                recommendation_id="SUM005",
                category=RecommendationCategory.OUTDOOR_ACTIVITIES,
                title="Outdoor Nature Connection",
                description="Engage in nature-based activities that foster environmental awareness.",
                season=Season.SUMMER,
                priority=RecommendationPriority.LOW,
                impact_level=ImpactLevel.LOW,
                estimated_savings={},
                implementation_difficulty=1,
                time_required="Flexible",
                cost_estimate_usd=0,
                tips=[
                    "Go on nature walks with family",
                    "Participate in citizen science projects",
                    "Volunteer for beach or park cleanups",
                    "Learn about local flora and fauna"
                ],
                resources=["https://nature.org", "https://citizenscience.org"],
                related_actions=["Download nature identification apps", "Start a nature journal"]
            )
        ]
        
        # AUTUMN RECOMMENDATIONS
        autumn_recs = [
            SeasonalRecommendation(
                recommendation_id="AUT001",
                category=RecommendationCategory.HOME_MAINTENANCE,
                title="Autumn Home Weatherization",
                description="Prepare your home for winter while maximizing energy efficiency.",
                season=Season.AUTUMN,
                priority=RecommendationPriority.HIGH,
                impact_level=ImpactLevel.HIGH,
                estimated_savings={"co2_kg": 250, "energy_kwh": 600},
                implementation_difficulty=4,
                time_required="6-8 hours",
                cost_estimate_usd=200,
                tips=[
                    "Seal windows and doors with weatherstripping",
                    "Add insulation to attic and walls",
                    "Clean gutters and downspouts",
                    "Check heating system efficiency",
                    "Install storm windows or thermal curtains"
                ],
                resources=["https://energy.gov/weatherization"],
                related_actions=["Schedule furnace maintenance", "Add programmable thermostat"]
            ),
            SeasonalRecommendation(
                recommendation_id="AUT002",
                category=RecommendationCategory.WASTE,
                title="Autumn Leaf Management",
                description="Sustainable leaf management for garden health and waste reduction.",
                season=Season.AUTUMN,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"waste_kg": 100},
                implementation_difficulty=2,
                time_required="2-4 hours weekly",
                cost_estimate_usd=20,
                tips=[
                    "Leave some leaves for wildlife habitat",
                    "Compost leaves for garden mulch",
                    "Use leaves as natural fertilizer",
                    "Create leaf mold for soil improvement",
                    "Avoid sending leaves to landfill"
                ],
                resources=["https://composting.org"],
                related_actions=["Start a compost pile", "Use leaves as mulch"]
            ),
            SeasonalRecommendation(
                recommendation_id="AUT003",
                category=RecommendationCategory.FOOD,
                title="Autumn Harvest Preservation",
                description="Preserve fall harvest to enjoy year-round and reduce winter food miles.",
                season=Season.AUTUMN,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"co2_kg": 60, "food_waste_kg": 50},
                implementation_difficulty=3,
                time_required="5-10 hours",
                cost_estimate_usd=50,
                tips=[
                    "Can tomatoes and apples",
                    "Freeze vegetables and fruits",
                    "Make jams and preserves",
                    "Store root vegetables in cool dark place",
                    "Dry herbs for winter use"
                ],
                resources=["https://preservingfood.org"],
                related_actions=["Plan winter meals", "Share preserved food with neighbors"]
            ),
            SeasonalRecommendation(
                recommendation_id="AUT004",
                category=RecommendationCategory.TRANSPORTATION,
                title="Prepare for Winter Travel",
                description="Prepare sustainable winter transportation alternatives.",
                season=Season.AUTUMN,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"co2_kg": 150},
                implementation_difficulty=3,
                time_required="3-5 hours",
                cost_estimate_usd=100,
                tips=[
                    "Install winter tires for safety",
                    "Plan public transit winter routes",
                    "Prepare emergency car kit",
                    "Consider carpooling options",
                    "Check battery and cold-weather performance"
                ],
                resources=["https://wintertravel.org"],
                related_actions=["Join carpool group", "Plan remote work days"]
            ),
            SeasonalRecommendation(
                recommendation_id="AUT005",
                category=RecommendationCategory.CONSERVATION,
                title="Support Migratory Birds",
                description="Help migratory birds during their autumn migration with habitat support.",
                season=Season.AUTUMN,
                priority=RecommendationPriority.LOW,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"biodiversity_impact": 0.8},
                implementation_difficulty=2,
                time_required="2-3 hours",
                cost_estimate_usd=30,
                tips=[
                    "Install bird feeders and water sources",
                    "Plant native berry-producing shrubs",
                    "Reduce outdoor lighting during migration",
                    "Keep cats indoors during migration season",
                    "Join citizen science bird tracking"
                ],
                resources=["https://birdconservation.org"],
                related_actions=["Create wildlife habitat garden", "Participate in bird counts"]
            )
        ]
        
        # WINTER RECOMMENDATIONS
        winter_recs = [
            SeasonalRecommendation(
                recommendation_id="WIN001",
                category=RecommendationCategory.ENERGY,
                title="Winter Energy Efficiency",
                description="Maximize winter energy efficiency and reduce heating costs.",
                season=Season.WINTER,
                priority=RecommendationPriority.HIGH,
                impact_level=ImpactLevel.VERY_HIGH,
                estimated_savings={"co2_kg": 400, "energy_kwh": 1000},
                implementation_difficulty=3,
                time_required="4-6 hours",
                cost_estimate_usd=150,
                tips=[
                    "Set thermostat to 68°F (20°C) when home",
                    "Use programmable thermostat for setbacks",
                    "Open curtains during day for solar heat",
                    "Close curtains at night to retain heat",
                    "Use space heaters for occupied rooms only",
                    "Seal drafty doors and windows"
                ],
                resources=["https://energy.gov/winter"],
                related_actions=["Add insulation", "Install smart thermostat"]
            ),
            SeasonalRecommendation(
                recommendation_id="WIN002",
                category=RecommendationCategory.HOLIDAYS,
                title="Sustainable Winter Holidays",
                description="Celebrate winter holidays with reduced environmental impact.",
                season=Season.WINTER,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"co2_kg": 100, "waste_kg": 50},
                implementation_difficulty=2,
                time_required="Variable",
                cost_estimate_usd=50,
                tips=[
                    "Use LED holiday lights",
                    "Choose real trees that can be composted",
                    "Give eco-friendly and experience gifts",
                    "Use reusable gift wrap",
                    "Plan sustainable holiday meals",
                    "Compost food waste"
                ],
                resources=["https://greenholidays.org"],
                related_actions=["Make homemade gifts", "Donate to charities"]
            ),
            SeasonalRecommendation(
                recommendation_id="WIN003",
                category=RecommendationCategory.FOOD,
                title="Winter Comfort Food with Low Impact",
                description="Enjoy nourishing winter meals while minimizing environmental impact.",
                season=Season.WINTER,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"co2_kg": 35, "food_miles": 600},
                implementation_difficulty=2,
                time_required="Weekly planning",
                cost_estimate_usd=20,
                tips=[
                    "Cook in batches to save energy",
                    "Choose root vegetables in season",
                    "Make hearty soups and stews",
                    "Use preserved foods from autumn",
                    "Slow cook using retained heat"
                ],
                resources=["https://winterfoodguide.org"],
                related_actions=["Use pressure cookers", "Plan meals around available produce"]
            ),
            SeasonalRecommendation(
                recommendation_id="WIN004",
                category=RecommendationCategory.WATER,
                title="Winter Water Conservation",
                description="Prevent winter water waste and protect your plumbing.",
                season=Season.WINTER,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"water_liters": 10000},
                implementation_difficulty=3,
                time_required="3-4 hours",
                cost_estimate_usd=50,
                tips=[
                    "Insulate exposed pipes",
                    "Check for leaks before freezing",
                    "Drain outdoor faucets",
                    "Collect snow melt for plants",
                    "Reduce hot water usage"
                ],
                resources=["https://winterwater.org"],
                related_actions=["Insulate water heater", "Fix leaks promptly"]
            ),
            SeasonalRecommendation(
                recommendation_id="WIN005",
                category=RecommendationCategory.HEALTH,
                title="Winter Wellness with Low Impact",
                description="Stay healthy during winter with sustainable wellness practices.",
                season=Season.WINTER,
                priority=RecommendationPriority.LOW,
                impact_level=ImpactLevel.LOW,
                estimated_savings={},
                implementation_difficulty=1,
                time_required="Daily",
                cost_estimate_usd=10,
                tips=[
                    "Get outdoor exercise during daylight",
                    "Maintain vitamin D levels naturally",
                    "Use essential oils for indoor air quality",
                    "Practice mindfulness indoors",
                    "Connect virtually to reduce travel"
                ],
                resources=["https://winterwellness.org"],
                related_actions=["Create indoor exercise routine", "Start meditation practice"]
            )
        ]
        
        # ALL-YEAR RECOMMENDATIONS
        all_year_recs = [
            SeasonalRecommendation(
                recommendation_id="ALL001",
                category=RecommendationCategory.ENERGY,
                title="Install Solar Panels",
                description="Generate clean energy year-round with solar panel installation.",
                season=Season.ALL_YEAR,
                priority=RecommendationPriority.HIGH,
                impact_level=ImpactLevel.VERY_HIGH,
                estimated_savings={"co2_kg": 2000, "energy_kwh": 5000},
                implementation_difficulty=8,
                time_required="2-4 weeks",
                cost_estimate_usd=10000,
                tips=[
                    "Get multiple quotes from installers",
                    "Check available incentives and rebates",
                    "Consider battery storage options",
                    "Choose high-efficiency panels",
                    "Monitor system performance regularly"
                ],
                resources=["https://solar.org", "https://energy.gov/solar"],
                related_actions=["Add smart home monitoring", "Switch to electric appliances"]
            ),
            SeasonalRecommendation(
                recommendation_id="ALL002",
                category=RecommendationCategory.WASTE,
                title="Zero Waste Lifestyle",
                description="Reduce waste generation throughout the year with sustainable habits.",
                season=Season.ALL_YEAR,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.HIGH,
                estimated_savings={"waste_kg": 300},
                implementation_difficulty=4,
                time_required="Ongoing",
                cost_estimate_usd=20,
                tips=[
                    "Use reusable bags and containers",
                    "Avoid single-use plastics",
                    "Compost food waste",
                    "Buy in bulk to reduce packaging",
                    "Repair items instead of replacing"
                ],
                resources=["https://zerowaste.org"],
                related_actions=["Start a compost bin", "Shop at bulk stores"]
            ),
            SeasonalRecommendation(
                recommendation_id="ALL003",
                category=RecommendationCategory.TRANSPORTATION,
                title="Switch to Electric Vehicle",
                description="Transition to electric vehicle for year-round sustainable transportation.",
                season=Season.ALL_YEAR,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.VERY_HIGH,
                estimated_savings={"co2_kg": 3000, "fuel_liters": 1500},
                implementation_difficulty=7,
                time_required="1-3 months research",
                cost_estimate_usd=35000,
                tips=[
                    "Research available models and range",
                    "Check charging infrastructure availability",
                    "Consider used EV options",
                    "Install home charging station",
                    "Plan for winter range reduction"
                ],
                resources=["https://electricvehicles.org"],
                related_actions=["Install solar panels", "Join EV community"]
            ),
            SeasonalRecommendation(
                recommendation_id="ALL004",
                category=RecommendationCategory.SHOPPING,
                title="Sustainable Shopping Year-Round",
                description="Make environmentally conscious shopping choices all year.",
                season=Season.ALL_YEAR,
                priority=RecommendationPriority.MEDIUM,
                impact_level=ImpactLevel.MODERATE,
                estimated_savings={"co2_kg": 200},
                implementation_difficulty=2,
                time_required="Ongoing",
                cost_estimate_usd=0,
                tips=[
                    "Buy quality items that last longer",
                    "Support sustainable brands",
                    "Research product lifespans",
                    "Consider second-hand options",
                    "Avoid impulse purchases"
                ],
                resources=["https://sustainableshopping.org"],
                related_actions=["Create shopping list", "Research products before buying"]
            )
        ]
        
        recommendations[Season.SPRING] = spring_recs
        recommendations[Season.SUMMER] = summer_recs
        recommendations[Season.AUTUMN] = autumn_recs
        recommendations[Season.WINTER] = winter_recs
        recommendations[Season.ALL_YEAR] = all_year_recs
        
        return recommendations
    
    def _initialize_food_guides(self) -> Dict[Season, SeasonalFoodGuide]:
        return {}
