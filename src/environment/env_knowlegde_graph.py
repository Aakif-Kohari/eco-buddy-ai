"""
Context-Aware Sustainability Decision Intelligence System
==========================================================
An advanced decision support system that provides intelligent, 
personalized sustainability recommendations based on user context,
behavior patterns, and environmental factors.

Author: EcoBuddy Team  
Version: 2.0.0
"""

import json
import math
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from pathlib import Path
import hashlib
import re
from collections import defaultdict, Counter
import heapq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS FOR CONTEXT-AWARE SYSTEM
# ============================================================================

class ContextType(Enum):
    """Types of context that influence decisions."""
    TEMPORAL = "temporal"
    GEOGRAPHIC = "geographic"
    PERSONAL = "personal"
    BEHAVIORAL = "behavioral"
    SOCIAL = "social"
    ECONOMIC = "economic"
    ENVIRONMENTAL = "environmental"
    SEASONAL = "seasonal"
    URGENCY = "urgency"
    HEALTH = "health"


class DecisionPriority(Enum):
    """Priority levels for decisions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"
    OPTIONAL = "optional"


class SustainabilityGoal(Enum):
    """Sustainability goals to optimize for."""
    CARBON_REDUCTION = "carbon_reduction"
    WASTE_REDUCTION = "waste_reduction"
    WATER_CONSERVATION = "water_conservation"
    ENERGY_EFFICIENCY = "energy_efficiency"
    SUSTAINABLE_CONSUMPTION = "sustainable_consumption"
    BIODIVERSITY = "biodiversity"
    CIRCULAR_ECONOMY = "circular_economy"
    SOCIAL_IMPACT = "social_impact"


class UserMood(Enum):
    """User mood states affecting decision context."""
    HAPPY = "happy"
    NEUTRAL = "neutral"
    STRESSED = "stressed"
    TIRED = "tired"
    MOTIVATED = "motivated"
    RELAXED = "relaxed"
    ANXIOUS = "anxious"
    BUSY = "busy"


class WeatherCondition(Enum):
    """Weather conditions affecting decisions."""
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    SNOWY = "snowy"
    STORMY = "stormy"
    FOGGY = "foggy"
    HOT = "hot"
    COLD = "cold"
    WINDY = "windy"


class DayType(Enum):
    """Types of days affecting context."""
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"
    WORK_FROM_HOME = "work_from_home"
    VACATION = "vacation"
    SPECIAL_EVENT = "special_event"


# ============================================================================
# DATA CLASSES FOR CONTEXT-AWARE SYSTEM
# ============================================================================

@dataclass
class TemporalContext:
    """Temporal context information."""
    timestamp: datetime = field(default_factory=datetime.now)
    day_of_week: int = field(default_factory=lambda: datetime.now().weekday())
    day_type: DayType = DayType.WEEKDAY
    hour: int = field(default_factory=lambda: datetime.now().hour)
    season: str = field(default_factory=lambda: _get_season())
    is_holiday: bool = False
    time_until_deadline: Optional[float] = None  # hours
    time_available: Optional[float] = None  # hours
    energy_level: float = 0.7  # 0-1 scale
    mood: UserMood = UserMood.NEUTRAL
    
    def __post_init__(self):
        if self.timestamp:
            self.day_of_week = self.timestamp.weekday()
            self.hour = self.timestamp.hour
            self.season = _get_season(self.timestamp)


@dataclass
class GeographicContext:
    """Geographic and location context."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    urban_rural: str = "urban"  # urban, suburban, rural
    terrain_type: str = "flat"  # flat, hilly, mountainous
    climate_zone: str = "temperate"  # tropical, temperate, arid, polar
    weather: WeatherCondition = WeatherCondition.SUNNY
    temperature_celsius: float = 20.0
    air_quality_index: float = 50.0  # 0-500 scale
    public_transport_availability: float = 0.5  # 0-1 scale
    bike_infrastructure_quality: float = 0.4  # 0-1 scale
    walkability_score: float = 0.6  # 0-1 scale
    green_space_access: float = 0.5  # 0-1 scale


@dataclass
class PersonalContext:
    """Personal preferences and constraints."""
    user_id: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    income_level: Optional[float] = None
    education_level: Optional[str] = None
    health_status: Optional[str] = None
    mobility_restrictions: List[str] = field(default_factory=list)
    dietary_restrictions: List[str] = field(default_factory=list)
    sustainability_attitude: float = 0.7  # 0-1 scale
    budget_constraints: bool = True
    time_constraints: bool = True
    risk_tolerance: float = 0.5  # 0-1 scale
    convenience_preference: float = 0.6  # 0-1 scale
    social_responsibility_level: float = 0.7  # 0-1 scale
    personal_goals: List[SustainabilityGoal] = field(default_factory=list)
    habits: Dict[str, float] = field(default_factory=dict)


@dataclass
class BehavioralContext:
    """User behavioral patterns."""
    recent_decisions: List[Dict[str, Any]] = field(default_factory=list)
    decision_history: List[Dict[str, Any]] = field(default_factory=list)
    current_activity: Optional[str] = None
    activity_intensity: float = 0.5  # 0-1 scale
    routine_deviation: float = 0.0  # 0-1 scale
    fatigue_level: float = 0.3  # 0-1 scale
    focus_level: float = 0.7  # 0-1 scale
    previous_success_rate: float = 0.8  # 0-1 scale
    learning_progress: Dict[str, float] = field(default_factory=dict)
    behavioral_patterns: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SocialContext:
    """Social and community context."""
    social_network_size: int = 50
    community_engagement: float = 0.5  # 0-1 scale
    influence_radius: float = 0.3  # 0-1 scale
    group_memberships: List[str] = field(default_factory=list)
    social_norms: Dict[str, float] = field(default_factory=dict)
    peer_influence_strength: float = 0.4  # 0-1 scale
    family_commitments: float = 0.5  # 0-1 scale
    social_support: float = 0.6  # 0-1 scale
    community_events: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class EconomicContext:
    """Economic conditions."""
    local_economy_health: float = 0.7  # 0-1 scale
    cost_sensitivity: float = 0.5  # 0-1 scale
    investment_ability: float = 0.4  # 0-1 scale
    subsidies_available: List[str] = field(default_factory=list)
    market_trends: Dict[str, float] = field(default_factory=dict)
    pricing_volatility: float = 0.3  # 0-1 scale
    job_security: float = 0.7  # 0-1 scale
    available_income: float = 0.0


@dataclass
class EnvironmentalContext:
    """Environmental conditions."""
    air_quality: float = 50.0  # AQI
    noise_pollution: float = 40.0  # dB
    light_pollution: float = 30.0  # arbitrary scale
    biodiversity_index: float = 0.5  # 0-1 scale
    water_quality: float = 0.7  # 0-1 scale
    soil_health: float = 0.6  # 0-1 scale
    ecosystem_services: float = 0.5  # 0-1 scale
    environmental_stressors: List[str] = field(default_factory=list)


@dataclass
class DecisionContext:
    """Complete decision context."""
    temporal: TemporalContext = field(default_factory=TemporalContext)
    geographic: GeographicContext = field(default_factory=GeographicContext)
    personal: PersonalContext = field(default_factory=PersonalContext)
    behavioral: BehavioralContext = field(default_factory=BehavioralContext)
    social: SocialContext = field(default_factory=SocialContext)
    economic: EconomicContext = field(default_factory=EconomicContext)
    environmental: EnvironmentalContext = field(default_factory=EnvironmentalContext)
    context_type: ContextType = ContextType.PERSONAL
    context_weight: float = 1.0
    
    def get_context_vector(self) -> Dict[str, float]:
        """Convert context to numerical vector for analysis."""
        vector = {}
        
        # Temporal features
        vector["hour"] = self.temporal.hour / 24.0
        vector["day_of_week"] = self.temporal.day_of_week / 7.0
        vector["energy_level"] = self.temporal.energy_level
        vector["is_weekend"] = 1.0 if self.temporal.day_type == DayType.WEEKEND else 0.0
        vector["is_holiday"] = 1.0 if self.temporal.is_holiday else 0.0
        
        # Geographic features
        vector["urban_rural"] = {"urban": 0.8, "suburban": 0.5, "rural": 0.2}.get(self.geographic.urban_rural, 0.5)
        vector["public_transport"] = self.geographic.public_transport_availability
        vector["bike_infrastructure"] = self.geographic.bike_infrastructure_quality
        vector["walkability"] = self.geographic.walkability_score
        vector["temperature"] = self.geographic.temperature_celsius / 40.0
        
        # Personal features
        vector["sustainability_attitude"] = self.personal.sustainability_attitude
        vector["risk_tolerance"] = self.personal.risk_tolerance
        vector["convenience_preference"] = self.personal.convenience_preference
        vector["social_responsibility"] = self.personal.social_responsibility_level
        
        # Behavioral features
        vector["routine_deviation"] = self.behavioral.routine_deviation
        vector["fatigue_level"] = self.behavioral.fatigue_level
        vector["focus_level"] = self.behavioral.focus_level
        
        # Social features
        vector["community_engagement"] = self.social.community_engagement
        vector["peer_influence"] = self.social.peer_influence_strength
        vector["social_support"] = self.social.social_support
        
        # Economic features
        vector["cost_sensitivity"] = self.economic.cost_sensitivity
        vector["investment_ability"] = self.economic.investment_ability
        
        # Environmental features
        vector["air_quality"] = 1.0 - (self.environmental.air_quality / 500.0)
        vector["biodiversity"] = self.environmental.biodiversity_index
        
        return vector


@dataclass
class DecisionOption:
    """A possible decision option with its attributes."""
    option_id: str
    name: str
    category: str
    description: str
    carbon_impact: float  # kg CO2e
    cost_impact: float  # monetary cost
    time_impact: float  # time in minutes
    health_impact: float  # 0-1 scale (positive)
    social_impact: float  # 0-1 scale (positive)
    environmental_impact: float  # 0-1 scale (positive)
    convenience_score: float  # 0-1 scale
    implementation_difficulty: float  # 0-1 scale
    immediate_impact: float  # 0-1 scale
    long_term_impact: float  # 0-1 scale
    prerequisites: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    sustainability_goals: List[SustainabilityGoal] = field(default_factory=list)
    contextual_factors: Dict[str, float] = field(default_factory=dict)
    
    def get_weighted_score(self, weights: Dict[str, float]) -> float:
        """Calculate weighted score based on context weights."""
        score = 0.0
        score += self.carbon_impact * weights.get("carbon", -0.3)
        score += self.cost_impact * weights.get("cost", -0.2)
        score += self.time_impact * weights.get("time", -0.1)
        score += self.health_impact * weights.get("health", 0.2)
        score += self.social_impact * weights.get("social", 0.15)
        score += self.environmental_impact * weights.get("environmental", 0.25)
        score += self.convenience_score * weights.get("convenience", 0.1)
        score -= self.implementation_difficulty * weights.get("difficulty", 0.1)
        return score


@dataclass
class DecisionResult:
    """Result of a decision recommendation."""
    recommended_option: DecisionOption
    alternatives: List[DecisionOption]
    score: float
    confidence: float
    context: DecisionContext
    reasoning: List[str] = field(default_factory=list)
    trade_offs: Dict[str, float] = field(default_factory=dict)
    expected_impact: Dict[str, float] = field(default_factory=dict)
    action_plan: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SustainabilityDecision:
    """A sustainability decision with all context."""
    decision_id: str
    user_id: str
    decision_type: str
    context: DecisionContext
    selected_option: Optional[DecisionOption] = None
    alternatives: List[DecisionOption] = field(default_factory=list)
    actual_outcome: Optional[Dict[str, Any]] = None
    feedback_score: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    learning_data: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# CONTEXT-AWARE DECISION ENGINE
# ============================================================================

class ContextAwareDecisionEngine:
    """Intelligent decision engine that considers multiple context dimensions."""
    
    def __init__(self):
        """Initialize the decision engine."""
        self.logger = logging.getLogger(f"{__name__}.ContextAwareDecisionEngine")
        self.context_weights = self._initialize_context_weights()
        self.decision_history = []
        self.learning_model = DecisionLearningModel()
        self.pattern_recognizer = BehavioralPatternRecognizer()
        self.recommendation_generator = RecommendationGenerator()
        self.impact_analyzer = ImpactAnalyzer()
        self.context_optimizer = ContextOptimizer()
        
        # Initialize option database
        self.option_database = self._initialize_option_database()
        self.carbon_engine = CarbonFootprintEngine()
    
    def _initialize_context_weights(self) -> Dict[str, float]:
        """Initialize default context weights."""
        return {
            "temporal": 0.15,
            "geographic": 0.20,
            "personal": 0.25,
            "behavioral": 0.15,
            "social": 0.10,
            "economic": 0.10,
            "environmental": 0.05
        }
    
    def _initialize_option_database(self) -> Dict[str, List[DecisionOption]]:
        """Initialize the database of decision options."""
        options = {
            "transportation": self._create_transportation_options(),
            "energy": self._create_energy_options(),
            "food": self._create_food_options(),
            "consumption": self._create_consumption_options(),
            "waste": self._create_waste_options(),
            "lifestyle": self._create_lifestyle_options()
        }
        return options
    
    def _create_transportation_options(self) -> List[DecisionOption]:
        """Create transportation decision options."""
        return [
            DecisionOption(
                option_id="walk_short_trip",
                name="Walk",
                category="transportation",
                description="Walk for short trips under 3km",
                carbon_impact=0.0,
                cost_impact=0.0,
                time_impact=30.0,
                health_impact=0.9,
                social_impact=0.2,
                environmental_impact=1.0,
                convenience_score=0.3,
                implementation_difficulty=0.4,
                immediate_impact=0.7,
                long_term_impact=0.8,
                tags=["active", "zero_emission", "healthy"],
                sustainability_goals=[SustainabilityGoal.CARBON_REDUCTION, 
                                     SustainabilityGoal.ENERGY_EFFICIENCY],
                contextual_factors={
                    "weather_sensitive": 0.8,
                    "distance_limited": 0.7,
                    "time_available": 0.5
                }
            ),
            DecisionOption(
                option_id="bike_medium_trip",
                name="Bicycle",
                category="transportation",
                description="Use bicycle for trips under 10km",
                carbon_impact=0.0,
                cost_impact=0.5,
                time_impact=25.0,
                health_impact=0.8,
                social_impact=0.3,
                environmental_impact=0.9,
                convenience_score=0.5,
                implementation_difficulty=0.5,
                immediate_impact=0.6,
                long_term_impact=0.8,
                tags=["active", "zero_emission", "healthy", "efficient"],
                sustainability_goals=[SustainabilityGoal.CARBON_REDUCTION,
                                     SustainabilityGoal.ENERGY_EFFICIENCY],
                contextual_factors={
                    "weather_sensitive": 0.7,
                    "distance_limited": 0.6,
                    "infrastructure_required": 0.8
                }
            ),
            DecisionOption(
                option_id="public_transport",
                name="Public Transport",
                category="transportation",
                description="Use bus, train, or subway",
                carbon_impact=0.5,
                cost_impact=2.0,
                time_impact=35.0,
                health_impact=0.3,
                social_impact=0.6,
                environmental_impact=0.7,
                convenience_score=0.6,
                implementation_difficulty=0.3,
                immediate_impact=0.8,
                long_term_impact=0.7,
                tags=["shared", "efficient", "urban"],
                sustainability_goals=[SustainabilityGoal.CARBON_REDUCTION],
                contextual_factors={
                    "urban_only": 0.8,
                    "schedule_dependent": 0.6,
                    "cost_effective": 0.7
                }
            ),
            DecisionOption(
                option_id="carpool",
                name="Carpool",
                category="transportation",
                description="Share ride with others",
                carbon_impact=0.4,
                cost_impact=1.5,
                time_impact=20.0,
                health_impact=0.1,
                social_impact=0.8,
                environmental_impact=0.6,
                convenience_score=0.5,
                implementation_difficulty=0.6,
                immediate_impact=0.7,
                long_term_impact=0.6,
                tags=["shared", "social", "community"],
                sustainability_goals=[SustainabilityGoal.CARBON_REDUCTION,
                                     SustainabilityGoal.SOCIAL_IMPACT],
                contextual_factors={
                    "network_required": 0.7,
                    "schedule_coordination": 0.8
                }
            ),
            DecisionOption(
                option_id="electric_car",
                name="Electric Vehicle",
                category="transportation",
                description="Use electric car for trips",
                carbon_impact=0.2,
                cost_impact=5.0,
                time_impact=15.0,
                health_impact=0.2,
                social_impact=0.5,
                environmental_impact=0.8,
                convenience_score=0.8,
                implementation_difficulty=0.7,
                immediate_impact=0.9,
                long_term_impact=0.9,
                tags=["modern", "efficient", "low_emission"],
                sustainability_goals=[SustainabilityGoal.CARBON_REDUCTION,
                                     SustainabilityGoal.ENERGY_EFFICIENCY],
                contextual_factors={
                    "charging_access": 0.8,
                    "range_limited": 0.6,
                    "investment_required": 0.9
                }
            )
        ]
    
    def _create_energy_options(self) -> List[DecisionOption]:
        """Create energy decision options."""
        return [
            DecisionOption(
                option_id="solar_panels",
                name="Install Solar Panels",
                category="energy",
                description="Install rooftop solar panels",
                carbon_impact=-5.0,
                cost_impact=50.0,
                time_impact=120.0,  # installation time in minutes
                health_impact=0.0,
                social_impact=0.6,
                environmental_impact=1.0,
                convenience_score=0.4,
                implementation_difficulty=0.8,
                immediate_impact=0.3,
                long_term_impact=0.9,
                tags=["renewable", "investment", "independence"],
                sustainability_goals=[SustainabilityGoal.CARBON_REDUCTION,
                                     SustainabilityGoal.ENERGY_EFFICIENCY],
                contextual_factors={
                    "sun_exposure": 0.9,
                    "roof_suitable": 0.8,
                    "investment_capacity": 0.9
                }
            ),
            DecisionOption(
                option_id="smart_thermostat",
                name="Install Smart Thermostat",
                category="energy",
                description="Install smart thermostat for heating/cooling",
                carbon_impact=-1.0,
                cost_impact=2.0,
                time_impact=60.0,
                health_impact=0.1,
                social_impact=0.2,
                environmental_impact=0.7,
                convenience_score=0.7,
                implementation_difficulty=0.4,
                immediate_impact=0.6,
                long_term_impact=0.7,
                tags=["smart", "efficient", "savings"],
                sustainability_goals=[SustainabilityGoal.ENERGY_EFFICIENCY,
                                     SustainabilityGoal.CARBON_REDUCTION],
                contextual_factors={
                    "technical_comfort": 0.6,
                    "home_ownership": 0.8
                }
            ),
            DecisionOption(
                option_id="led_lighting",
                name="Switch to LED",
                category="energy",
                description="Replace all bulbs with LEDs",
                carbon_impact=-0.5,
                cost_impact=0.5,
                time_impact=30.0,
                health_impact=0.0,
                social_impact=0.0,
                environmental_impact=0.5,
                convenience_score=0.9,
                implementation_difficulty=0.2,
                immediate_impact=0.8,
                long_term_impact=0.6,
                tags=["simple", "effective", "cost_saving"],
                sustainability_goals=[SustainabilityGoal.ENERGY_EFFICIENCY],
                contextual_factors={
                    "immediate_benefit": 0.9,
                    "low_effort": 0.9
                }
            )
        ]
    
    def _create_food_options(self) -> List[DecisionOption]:
        """Create food decision options."""
        return [
            DecisionOption(
                option_id="plant_based_meal",
                name="Choose Plant-Based Meal",
                category="food",
                description="Select a plant-based meal option",
                carbon_impact=-2.0,
                cost_impact=0.0,  # can be cheaper
                time_impact=0.0,
                health_impact=0.8,
                social_impact=0.3,
                environmental_impact=0.9,
                convenience_score=0.6,
                implementation_difficulty=0.3,
                immediate_impact=0.9,
                long_term_impact=0.7,
                tags=["healthy", "sustainable", "compassionate"],
                sustainability_goals=[SustainabilityGoal.CARBON_REDUCTION,
                                     SustainabilityGoal.SUSTAINABLE_CONSUMPTION],
                contextual_factors={
                    "dietary_flexibility": 0.7,
                    "availability": 0.8
                }
            ),
            DecisionOption(
                option_id="local_food",
                name="Buy Local Produce",
                category="food",
                description="Choose locally sourced food",
                carbon_impact=-1.0,
                cost_impact=0.2,
                time_impact=15.0,
                health_impact=0.6,
                social_impact=0.7,
                environmental_impact=0.7,
                convenience_score=0.4,
                implementation_difficulty=0.3,
                immediate_impact=0.7,
                long_term_impact=0.6,
                tags=["local", "community", "fresh"],
                sustainability_goals=[SustainabilityGoal.CARBON_REDUCTION,
                                     SustainabilityGoal.SOCIAL_IMPACT],
                contextual_factors={
                    "seasonality": 0.8,
                    "farmer_market_access": 0.7
                }
            ),
            DecisionOption(
                option_id="reduce_meat",
                name="Reduce Meat Consumption",
                category="food",
                description="Reduce meat consumption by 50%",
                carbon_impact=-3.0,
                cost_impact=-0.5,
                time_impact=0.0,
                health_impact=0.7,
                social_impact=0.4,
                environmental_impact=0.8,
                convenience_score=0.5,
                implementation_difficulty=0.5,
                immediate_impact=0.6,
                long_term_impact=0.8,
                tags=["gradual", "effective", "healthy"],
                sustainability_goals=[SustainabilityGoal.CARBON_REDUCTION,
                                     SustainabilityGoal.SUSTAINABLE_CONSUMPTION],
                contextual_factors={
                    "dietary_habit_strength": 0.8,
                    "social_support": 0.5
                }
            )
        ]
    
    def _create_consumption_options(self) -> List[DecisionOption]:
        """Create consumption decision options."""
        return [
            DecisionOption(
                option_id="buy_second_hand",
                name="Buy Second-Hand",
                category="consumption",
                description="Purchase second-hand items",
                carbon_impact=-2.0,
                cost_impact=-3.0,
                time_impact=30.0,
                health_impact=0.0,
                social_impact=0.5,
                environmental_impact=0.8,
                convenience_score=0.3,
                implementation_difficulty=0.4,
                immediate_impact=0.8,
                long_term_impact=0.6,
                tags=["circular", "cost_saving", "sustainable"],
                sustainability_goals=[SustainabilityGoal.CIRCULAR_ECONOMY,
                                     SustainabilityGoal.WASTE_REDUCTION],
                contextual_factors={
                    "item_availability": 0.6,
                    "quality_concern": 0.5
                }
            ),
            DecisionOption(
                option_id="repair_instead_replace",
                name="Repair Instead of Replace",
                category="consumption",
                description="Repair items instead of buying new",
                carbon_impact=-2.5,
                cost_impact=-1.0,
                time_impact=60.0,
                health_impact=0.0,
                social_impact=0.4,
                environmental_impact=0.8,
                convenience_score=0.3,
                implementation_difficulty=0.6,
                immediate_impact=0.7,
                long_term_impact=0.5,
                tags=["repair", "circular", "skill_building"],
                sustainability_goals=[SustainabilityGoal.CIRCULAR_ECONOMY,
                                     SustainabilityGoal.WASTE_REDUCTION],
                contextual_factors={
                    "skill_required": 0.8,
                    "repair_availability": 0.5
                }
            ),
            DecisionOption(
                option_id="rent_occasional",
                name="Rent Instead of Buy",
                category="consumption",
                description="Rent items for occasional use",
                carbon_impact=-1.5,
                cost_impact=-1.0,
                time_impact=15.0,
                health_impact=0.0,
                social_impact=0.4,
                environmental_impact=0.7,
                convenience_score=0.5,
                implementation_difficulty=0.3,
                immediate_impact=0.8,
                long_term_impact=0.4,
                tags=["sharing", "efficient", "cost_saving"],
                sustainability_goals=[SustainabilityGoal.CIRCULAR_ECONOMY,
                                     SustainabilityGoal.SUSTAINABLE_CONSUMPTION],
                contextual_factors={
                    "rental_access": 0.6,
                    "usage_frequency": 0.7
                }
            )
        ]
    
    def _create_waste_options(self) -> List[DecisionOption]:
        """Create waste decision options."""
        return [
            DecisionOption(
                option_id="composting",
                name="Start Composting",
                category="waste",
                description="Start composting organic waste",
                carbon_impact=-1.0,
                cost_impact=0.1,
                time_impact=20.0,
                health_impact=0.1,
                social_impact=0.5,
                environmental_impact=0.8,
                convenience_score=0.4,
                implementation_difficulty=0.5,
                immediate_impact=0.5,
                long_term_impact=0.7,
                tags=["circular", "garden", "soil_health"],
                sustainability_goals=[SustainabilityGoal.WASTE_REDUCTION,
                                     SustainabilityGoal.CIRCULAR_ECONOMY],
                contextual_factors={
                    "outdoor_space": 0.7,
                    "commitment_required": 0.6
                }
            ),
            DecisionOption(
                option_id="zero_waste_shopping",
                name="Zero Waste Shopping",
                category="waste",
                description="Shop with zero-waste practices",
                carbon_impact=-0.8,
                cost_impact=0.0,
                time_impact=25.0,
                health_impact=0.0,
                social_impact=0.6,
                environmental_impact=0.7,
                convenience_score=0.3,
                implementation_difficulty=0.5,
                immediate_impact=0.6,
                long_term_impact=0.5,
                tags=["plastic_free", "conscious", "reusable"],
                sustainability_goals=[SustainabilityGoal.WASTE_REDUCTION],
                contextual_factors={
                    "store_access": 0.5,
                    "planning_required": 0.7
                }
            )
        ]
    
    def _create_lifestyle_options(self) -> List[DecisionOption]:
        """Create lifestyle decision options."""
        return [
            DecisionOption(
                option_id="volunteer_environmental",
                name="Volunteer for Environmental Cause",
                category="lifestyle",
                description="Participate in environmental volunteering",
                carbon_impact=0.0,
                cost_impact=0.0,
                time_impact=120.0,
                health_impact=0.6,
                social_impact=0.9,
                environmental_impact=0.4,
                convenience_score=0.2,
                implementation_difficulty=0.3,
                immediate_impact=0.2,
                long_term_impact=0.7,
                tags=["community", "action", "impact"],
                sustainability_goals=[SustainabilityGoal.SOCIAL_IMPACT,
                                     SustainabilityGoal.ENVIRONMENTAL],
                contextual_factors={
                    "time_available": 0.8,
                    "social_comfort": 0.6
                }
            ),
            DecisionOption(
                option_id="environmental_education",
                name="Learn About Sustainability",
                category="lifestyle",
                description="Educate yourself about sustainability",
                carbon_impact=0.0,
                cost_impact=0.0,
                time_impact=45.0,
                health_impact=0.5,
                social_impact=0.4,
                environmental_impact=0.3,
                convenience_score=0.6,
                implementation_difficulty=0.1,
                immediate_impact=0.1,
                long_term_impact=0.8,
                tags=["education", "awareness", "empowerment"],
                sustainability_goals=[SustainabilityGoal.ENVIRONMENTAL,
                                     SustainabilityGoal.SOCIAL_IMPACT],
                contextual_factors={
                    "learning_style": 0.7,
                    "resource_access": 0.8
                }
            ),
            DecisionOption(
                option_id="advocate_sustainability",
                name="Advocate for Sustainability",
                category="lifestyle",
                description="Speak up for sustainability in community",
                carbon_impact=0.0,
                cost_impact=0.0,
                time_impact=90.0,
                health_impact=0.3,
                social_impact=0.9,
                environmental_impact=0.5,
                convenience_score=0.2,
                implementation_difficulty=0.6,
                immediate_impact=0.3,
                long_term_impact=0.9,
                tags=["advocacy", "community", "change"],
                sustainability_goals=[SustainabilityGoal.SOCIAL_IMPACT,
                                     SustainabilityGoal.ENVIRONMENTAL],
                contextual_factors={
                    "confidence_level": 0.7,
                    "community_receptivity": 0.6
                }
            )
        ]
    
    def get_decision_options(self, category: Optional[str] = None) -> List[DecisionOption]:
        """Get decision options for a category."""
        if category and category in self.option_database:
            return self.option_database[category]
        all_options = []
        for options in self.option_database.values():
            all_options.extend(options)
        return all_options
    
    def analyze_context(self, context: DecisionContext) -> Dict[str, float]:
        """
        Analyze the context and return relevance scores for different decision types.
        """
        analysis = {
            "transportation_ready": 0.0,
            "energy_ready": 0.0,
            "food_ready": 0.0,
            "consumption_ready": 0.0,
            "waste_ready": 0.0,
            "lifestyle_ready": 0.0
        }
        
        # Temporal analysis
        hour = context.temporal.hour
        day_type = context.temporal.day_type
        
        # Transportation readiness
        if 6 <= hour <= 9 or 16 <= hour <= 19:  # Commute hours
            analysis["transportation_ready"] += 0.3
        if context.geographic.public_transport_availability > 0.5:
            analysis["transportation_ready"] += 0.2
        if context.geographic.walkability_score > 0.6:
            analysis["transportation_ready"] += 0.2
        if context.personal.sustainability_attitude > 0.6:
            analysis["transportation_ready"] += 0.2
        if context.behavioral.fatigue_level < 0.4:
            analysis["transportation_ready"] += 0.1
        
        # Energy readiness
        if context.personal.home_ownership:
            analysis["energy_ready"] += 0.3
        if context.economic.investment_ability > 0.5:
            analysis["energy_ready"] += 0.2
        if context.personal.sustainability_attitude > 0.7:
            analysis["energy_ready"] += 0.2
        if context.personal.risk_tolerance > 0.6:
            analysis["energy_ready"] += 0.2
        if context.temporal.season in ["spring", "summer"]:
            analysis["energy_ready"] += 0.1
        
        # Food readiness
        if 11 <= hour <= 13 or 18 <= hour <= 20:  # Meal times
            analysis["food_ready"] += 0.3
        if context.personal.sustainability_attitude > 0.5:
            analysis["food_ready"] += 0.2
        if len(context.personal.dietary_restrictions) == 0:
            analysis["food_ready"] += 0.2
        if context.temporal.energy_level > 0.5:
            analysis["food_ready"] += 0.2
        if context.behavioral.focus_level > 0.6:
            analysis["food_ready"] += 0.1
        
        # Consumption readiness
        if day_type in [DayType.WEEKEND, DayType.VACATION]:
            analysis["consumption_ready"] += 0.3
        if context.economic.available_income > 0:
            analysis["consumption_ready"] += 0.2
        if context.personal.sustainability_attitude > 0.6:
            analysis["consumption_ready"] += 0.2
        if context.behavioral.routine_deviation < 0.3:
            analysis["consumption_ready"] += 0.2
        if context.personal.convenience_preference > 0.5:
            analysis["consumption_ready"] += 0.1
        
        # Waste readiness
        if context.personal.sustainability_attitude > 0.6:
            analysis["waste_ready"] += 0.3
        if context.environmental.air_quality > 50:  # Poor air quality
            analysis["waste_ready"] += 0.2
        if context.personal.risk_tolerance > 0.4:
            analysis["waste_ready"] += 0.2
        if context.geographic.urban_rural == "rural":
            analysis["waste_ready"] += 0.2
        if context.personal.social_responsibility_level > 0.6:
            analysis["waste_ready"] += 0.1
        
        # Lifestyle readiness
        if context.temporal.time_available and context.temporal.time_available > 60:
            analysis["lifestyle_ready"] += 0.3
        if context.social.community_engagement > 0.5:
            analysis["lifestyle_ready"] += 0.2
        if context.personal.sustainability_attitude > 0.7:
            analysis["lifestyle_ready"] += 0.2
        if context.behavioral.fatigue_level < 0.3:
            analysis["lifestyle_ready"] += 0.2
        if context.temporal.mood in [UserMood.MOTIVATED, UserMood.HAPPY]:
            analysis["lifestyle_ready"] += 0.1
        
        # Normalize
        for key in analysis:
            analysis[key] = min(1.0, analysis[key])
        
        return analysis
    
    def recommend_decision(self, context: DecisionContext, 
                          category: Optional[str] = None,
                          top_n: int = 3) -> DecisionResult:
        """
        Recommend a decision based on the given context.
        """
        self.logger.info(f"Generating recommendations for user: {context.personal.user_id}")
        
        # Get available options
        if category:
            options = self.get_decision_options(category)
        else:
            options = self.get_decision_options()
        
        # Analyze context
        context_analysis = self.analyze_context(context)
        
        # Score each option
        scored_options = []
        for option in options:
            score = self._score_option(option, context, context_analysis)
            scored_options.append((score, option))
        
        # Sort by score
        scored_options.sort(key=lambda x: x[0], reverse=True)
        
        # Get top options
        top_options = scored_options[:top_n]
        best_option = top_options[0][1] if top_options else None
        best_score = top_options[0][0] if top_options else 0.0
        
        # Generate reasoning
        reasoning = self._generate_reasoning(best_option, context, context_analysis)
        
        # Calculate confidence
        confidence = self._calculate_confidence(best_score, context)
        
        # Generate action plan
        action_plan = self._generate_action_plan(best_option, context)
        
        # Calculate expected impact
        expected_impact = self.impact_analyzer.calculate_expected_impact(
            best_option, context
        )
        
        # Calculate trade-offs
        trade_offs = self._calculate_trade_offs(best_option, context)
        
        result = DecisionResult(
            recommended_option=best_option,
            alternatives=[option for _, option in top_options[1:]],
            score=best_score,
            confidence=confidence,
            context=context,
            reasoning=reasoning,
            trade_offs=trade_offs,
            expected_impact=expected_impact,
            action_plan=action_plan
        )
        
        # Store decision in history
        self.decision_history.append(result)
        
        # Update learning model
        self.learning_model.update_from_decision(result)
        
        return result
    
    def _score_option(self, option: DecisionOption, context: DecisionContext,
                     context_analysis: Dict[str, float]) -> float:
        """
        Score a decision option based on context.
        """
        score = 0.0
        
        # Context readiness weight
        category_key = f"{option.category}_ready"
        readiness = context_analysis.get(category_key, 0.5)
        score += readiness * 0.2
        
        # Sustainability alignment
        goal_alignment = self._calculate_goal_alignment(option, context)
        score += goal_alignment * 0.25
        
        # Feasibility
        feasibility = self._calculate_feasibility(option, context)
        score += feasibility * 0.2
        
        # Impact potential
        impact_potential = self._calculate_impact_potential(option, context)
        score += impact_potential * 0.2
        
        # Personal relevance
        personal_relevance = self._calculate_personal_relevance(option, context)
        score += personal_relevance * 0.15
        
        return score
    
    def _calculate_goal_alignment(self, option: DecisionOption, 
                                 context: DecisionContext) -> float:
        """Calculate how well the option aligns with user's sustainability goals."""
        if not context.personal.personal_goals:
            return 0.5
        
        alignment = 0.0
        for goal in option.sustainability_goals:
            if goal in context.personal.personal_goals:
                alignment += 1.0
        
        return min(1.0, alignment / max(1, len(option.sustainability_goals)))
    
    def _calculate_feasibility(self, option: DecisionOption, 
                              context: DecisionContext) -> float:
        """Calculate feasibility of implementing the option."""
        factors = []
        
        # Time feasibility
        if context.temporal.time_available:
            time_needed = option.time_impact / 60.0  # Convert to hours
            time_available = context.temporal.time_available
            if time_needed <= time_available:
                factors.append(1.0)
            else:
                factors.append(time_available / max(time_needed, 1))
        
        # Cost feasibility
        if context.economic.available_income:
            cost = option.cost_impact
            income = context.economic.available_income
            if cost <= income * 0.1:  # Less than 10% of available income
                factors.append(1.0)
            else:
                factors.append(max(0, 1.0 - (cost / income)))
        
        # Skill feasibility
        if option.implementation_difficulty < 0.3:
            factors.append(1.0)
        elif option.implementation_difficulty < 0.6:
            if context.personal.education_level in ["bachelors", "masters", "doctorate"]:
                factors.append(0.8)
            else:
                factors.append(0.6)
        else:
            factors.append(0.4)
        
        # Resource feasibility
        for prerequisite in option.prerequisites:
            if prerequisite == "outdoor_space" and context.geographic.urban_rural == "urban":
                factors.append(0.3)
            elif prerequisite == "home_ownership" and not context.personal.home_ownership:
                factors.append(0.2)
        
        return statistics.mean(factors) if factors else 0.5
    
    def _calculate_impact_potential(self, option: DecisionOption, 
                                   context: DecisionContext) -> float:
        """Calculate the potential impact of the option."""
        # Immediate impact
        immediate = option.immediate_impact
        
        # Long-term impact
        long_term = option.long_term_impact
        
        # Carbon impact (negative is good)
        carbon_impact = 1.0 - min(1.0, abs(option.carbon_impact) / 10.0)
        
        # Environmental impact
        environmental = option.environmental_impact
        
        # Social impact
        social = option.social_impact
        
        # Weighted combination
        impact = (immediate * 0.2 + long_term * 0.3 + carbon_impact * 0.2 +
                 environmental * 0.15 + social * 0.15)
        
        return min(1.0, impact)
    
    def _calculate_personal_relevance(self, option: DecisionOption, 
                                     context: DecisionContext) -> float:
        """Calculate personal relevance of the option."""
        relevance = 0.0
        
        # Lifestyle compatibility
        if context.personal.habits:
            habit_match = sum(1 for tag in option.tags if tag in context.personal.habits)
            relevance += habit_match / max(len(option.tags), 1) * 0.3
        
        # Social relevance
        if context.social.community_engagement > 0.5:
            relevance += 0.2
        
        # Health relevance
        if context.personal.health_status and option.health_impact > 0.5:
            relevance += 0.2
        
        # Economic relevance
        if option.cost_impact < 0:  # Cost saving
            relevance += 0.1
        
        # Convenience relevance
        if context.personal.convenience_preference > 0.5:
            relevance += option.convenience_score * 0.2
        
        return min(1.0, relevance)
    
    def _generate_reasoning(self, option: DecisionOption, context: DecisionContext,
                           context_analysis: Dict[str, float]) -> List[str]:
        """Generate reasoning for the recommendation."""
        reasoning = []
        
        # Temporal reasoning
        hour = context.temporal.hour
        if 6 <= hour <= 9:
            reasoning.append(f"Morning time is ideal for {option.category} decisions")
        elif 18 <= hour <= 22:
            reasoning.append(f"Evening is suitable for {option.category} planning")
        
        # Geographic reasoning
        if context.geographic.public_transport_availability > 0.7:
            reasoning.append("Excellent public transport infrastructure supports this decision")
        if context.geographic.walkability_score > 0.7:
            reasoning.append("High walkability score makes this a practical option")
        
        # Personal reasoning
        if context.personal.sustainability_attitude > 0.7:
            reasoning.append("Your strong sustainability commitment makes this a good fit")
        if option.cost_impact < 0 and context.economic.cost_sensitivity > 0.5:
            reasoning.append("This option provides cost savings which aligns with your budget concerns")
        
        # Behavioral reasoning
        if context.behavioral.previous_success_rate > 0.7:
            reasoning.append("Your track record suggests you'll successfully implement this")
        if context.behavioral.fatigue_level < 0.3:
            reasoning.append("You seem well-rested and ready for this commitment")
        
        # Social reasoning
        if context.social.community_engagement > 0.6:
            reasoning.append("Your community engagement will support this initiative")
        
        # Environmental reasoning
        if option.environmental_impact > 0.7:
            reasoning.append("This option has strong environmental benefits")
        
        # Carbon impact reasoning
        if option.carbon_impact < -1.0:
            reasoning.append(f"Significant carbon reduction of {abs(option.carbon_impact):.1f} kg CO2e")
        
        # Add generic reasoning if not enough specific reasons
        if len(reasoning) < 3:
            reasoning.append(f"This {option.category} option balances sustainability with practical considerations")
            reasoning.append(f"The {option.name} is well-suited to your current situation")
            reasoning.append("Implementation has been shown to be effective for similar contexts")
        
        return reasoning[:6]  # Limit to top 6 reasons
    
    def _calculate_confidence(self, score: float, context: DecisionContext) -> float:
        """Calculate confidence in the recommendation."""
        base_confidence = score
        
        # Adjust based on context quality
        context_quality = 0.5
        if context.personal.user_id:
            context_quality += 0.1
        if context.geographic.latitude and context.geographic.longitude:
            context_quality += 0.1
        if context.behavioral.decision_history:
            context_quality += 0.1
        
        # Adjust based on data completeness
        data_completeness = 0.7
        context_vector = context.get_context_vector()
        non_zero = sum(1 for v in context_vector.values() if v > 0)
        data_completeness += non_zero / len(context_vector) * 0.3
        
        confidence = (base_confidence * 0.6 + context_quality * 0.2 + data_completeness * 0.2)
        return min(1.0, confidence)
    
    def _calculate_trade_offs(self, option: DecisionOption, 
                             context: DecisionContext) -> Dict[str, float]:
        """Calculate trade-offs associated with the option."""
        trade_offs = {
            "carbon_vs_cost": option.carbon_impact / max(abs(option.cost_impact), 0.01),
            "time_vs_benefit": option.time_impact / max(option.environmental_impact, 0.01),
            "convenience_vs_impact": 1.0 - (option.convenience_score / max(option.environmental_impact, 0.01))
        }
        
        # Normalize
        for key in trade_offs:
            trade_offs[key] = max(-1.0, min(1.0, trade_offs[key]))
        
        return trade_offs
    
    def _generate_action_plan(self, option: DecisionOption, 
                             context: DecisionContext) -> List[Dict[str, Any]]:
        """Generate an actionable plan for implementation."""
        plan = []
        
        # Step 1: Preparation
        plan.append({
            "step": 1,
            "action": f"Gather information about {option.name}",
            "time_estimate": "15 minutes",
            "resources": ["Research materials", "Online resources"],
            "priority": "high"
        })
        
        # Step 2: Planning
        plan.append({
            "step": 2,
            "action": f"Create a plan for implementing {option.name}",
            "time_estimate": "30 minutes",
            "resources": ["Calendar", "Budget", "Support network"],
            "priority": "high"
        })
        
        # Step 3: Execution
        plan.append({
            "step": 3,
            "action": f"Begin implementation of {option.name}",
            "time_estimate": f"{option.time_impact:.0f} minutes",
            "resources": ["Materials", "Tools", "Help if needed"],
            "priority": "medium"
        })
        
        # Step 4: Monitoring
        plan.append({
            "step": 4,
            "action": f"Track the impact of your {option.category} decision",
            "time_estimate": "Weekly check-ins",
            "resources": ["Tracking tool", "Journal"],
            "priority": "medium"
        })
        
        # Step 5: Adjustment
        plan.append({
            "step": 5,
            "action": "Adjust approach based on results and feedback",
            "time_estimate": "Ongoing",
            "resources": ["Feedback", "Learning resources"],
            "priority": "low"
        })
        
        return plan


# ============================================================================
# LEARNING AND OPTIMIZATION COMPONENTS
# ============================================================================

class DecisionLearningModel:
    """Machine learning model for improving decision recommendations."""
    
    def __init__(self):
        """Initialize the learning model."""
        self.logger = logging.getLogger(f"{__name__}.DecisionLearningModel")
        self.decision_history = []
        self.context_patterns = defaultdict(list)
        self.success_patterns = defaultdict(list)
        self.user_preferences = defaultdict(lambda: defaultdict(float))
        self.option_performance = defaultdict(lambda: defaultdict(float))
        
    def update_from_decision(self, decision_result: DecisionResult):
        """Update learning model from a decision."""
        self.decision_history.append(decision_result)
        
        # Extract features
        context = decision_result.context
        option = decision_result.recommended_option
        
        # Store context patterns
        context_key = self._extract_context_key(context)
        self.context_patterns[context_key].append({
            "option": option.option_id,
            "score": decision_result.score,
            "timestamp": decision_result.timestamp
        })
        
        # Update user preferences
        for goal in context.personal.personal_goals:
            self.user_preferences[goal.value][option.category] += 0.1
        
        # Update option performance
        self.option_performance[option.category][option.option_id] += 0.05
        
        # Limit history
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-500:]
        
        # Cap data structures
        for key in self.context_patterns:
            if len(self.context_patterns[key]) > 100:
                self.context_patterns[key] = self.context_patterns[key][-50:]
    
    def _extract_context_key(self, context: DecisionContext) -> str:
        """Extract a key for context pattern matching."""
        components = [
            context.temporal.season,
            context.temporal.day_type.value,
            context.geographic.urban_rural,
            context.personal.sustainability_attitude > 0.7,
            context.behavioral.fatigue_level < 0.3
        ]
        return "_".join(str(c) for c in components)
    
    def predict_success(self, option: DecisionOption, context: DecisionContext) -> float:
        """Predict success probability for an option in a context."""
        context_key = self._extract_context_key(context)
        
        # Check for similar contexts
        similar_decisions = self.context_patterns.get(context_key, [])
        if similar_decisions:
            scores = [d["score"] for d in similar_decisions]
            return statistics.mean(scores)
        
        # Use user preference as fallback
        preferences = []
        for goal in context.personal.personal_goals:
            pref = self.user_preferences[goal.value].get(option.category, 0.3)
            preferences.append(pref)
        
        return statistics.mean(preferences) if preferences else 0.5
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Get suggestions for optimizing recommendations."""
        suggestions = []
        
        # Analyze option performance
        for category, options in self.option_performance.items():
            best_option = max(options.items(), key=lambda x: x[1])
            worst_option = min(options.items(), key=lambda x: x[1])
            
            if best_option[1] - worst_option[1] > 0.5:
                suggestions.append({
                    "category": category,
                    "best_option": best_option[0],
                    "worst_option": worst_option[0],
                    "improvement_potential": best_option[1] - worst_option[1]
                })
        
        return sorted(suggestions, key=lambda x: x["improvement_potential"], reverse=True)


class BehavioralPatternRecognizer:
    """Recognize patterns in user behavior for better recommendations."""
    
    def __init__(self):
        """Initialize the pattern recognizer."""
        self.patterns = []
        self.activity_sequences = []
        self.routine_detection = {}
    
    def analyze_behavior(self, behavioral_context: BehavioralContext) -> Dict[str, Any]:
        """Analyze behavioral patterns."""
        analysis = {
            "routine_strength": 0.5,
            "change_readiness": 0.5,
            "preferred_timing": "morning",
            "decision_style": "deliberate",
            "risk_appetite": 0.5
        }
        
        # Analyze decision history
        if behavioral_context.decision_history:
            times = [d.get("time", "morning") for d in behavioral_context.decision_history[-10:]]
            if times:
                common_time = max(set(times), key=times.count)
                analysis["preferred_timing"] = common_time
            
            # Analyze decision style
            quick_decisions = sum(1 for d in behavioral_context.decision_history[-20:] 
                                if d.get("decision_time_seconds", 60) < 30)
            if quick_decisions > 10:
                analysis["decision_style"] = "intuitive"
        
        # Analyze routine deviation
        if behavioral_context.routine_deviation > 0.6:
            analysis["routine_strength"] = 0.3
            analysis["change_readiness"] = 0.7
        else:
            analysis["routine_strength"] = 0.7
            analysis["change_readiness"] = 0.3
        
        # Analyze risk tolerance
        if behavioral_context.fatigue_level < 0.3 and behavioral_context.focus_level > 0.7:
            analysis["risk_appetite"] = 0.7
        else:
            analysis["risk_appetite"] = 0.4
        
        return analysis
    
    def detect_context_switch(self, current_context: DecisionContext) -> bool:
        """Detect if context has switched significantly."""
        # Compare with previous context
        if not hasattr(self, 'last_context'):
            self.last_context = current_context
            return False
        
        # Calculate context change
        change_score = self._calculate_change_score(self.last_context, current_context)
        self.last_context = current_context
        
        return change_score > 0.3
    
    def _calculate_change_score(self, old: DecisionContext, new: DecisionContext) -> float:
        """Calculate how much context has changed."""
        changes = []
        
        # Temporal changes
        if old.temporal.day_type != new.temporal.day_type:
            changes.append(0.3)
        if abs(old.temporal.hour - new.temporal.hour) > 4:
            changes.append(0.2)
        
        # Geographic changes (if available)
        if old.geographic.latitude and new.geographic.latitude:
            distance = self._haversine_distance(
                old.geographic.latitude, old.geographic.longitude,
                new.geographic.latitude, new.geographic.longitude
            )
            if distance > 10:  # More than 10km
                changes.append(0.3)
        
        # Behavioral changes
        if old.behavioral.routine_deviation != new.behavioral.routine_deviation:
            changes.append(abs(old.behavioral.routine_deviation - new.behavioral.routine_deviation))
        
        # Personal changes
        if old.personal.sustainability_attitude != new.personal.sustainability_attitude:
            changes.append(abs(old.personal.sustainability_attitude - new.personal.sustainability_attitude) / 0.2)
        
        return min(1.0, sum(changes) / max(1, len(changes)))
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points on Earth."""
        if not all([lat1, lon1, lat2, lon2]):
            return 0.0
        R = 6371  # Earth's radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c


class RecommendationGenerator:
    """Generate personalized recommendations."""
    
    def __init__(self):
        """Initialize the recommendation generator."""
        self.recommendation_templates = self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize recommendation templates."""
        return {
            "transportation": [
                "Based on your commute pattern, consider {option} to reduce emissions",
                "Your location has excellent {option} infrastructure",
                "Try {option} for your daily commute to save money and reduce carbon"
            ],
            "energy": [
                "Your home is well-suited for {option} given your energy consumption",
                "Considering your location, {option} would be a smart investment",
                "Start with {option} for immediate energy savings"
            ],
            "food": [
                "Given your dietary preferences, {option} would be a great fit",
                "Try {option} to make your meals more sustainable",
                "Your eating habits suggest {option} is achievable"
            ],
            "consumption": [
                "Based on your shopping patterns, {option} makes sense",
                "Your budget-conscious approach aligns well with {option}",
                "Consider {option} for sustainable consumption"
            ],
            "waste": [
                "Your household waste pattern suggests {option} would help",
                "With your available space, {option} is practical",
                "Start reducing waste with {option}"
            ],
            "lifestyle": [
                "Your community engagement makes {option} a natural fit",
                "Based on your interests, {option} would be rewarding",
                "Your values align well with {option}"
            ]
        }
    
    def generate_recommendation(self, option: DecisionOption, 
                               context: DecisionContext) -> str:
        """Generate a personalized recommendation text."""
        templates = self.recommendation_templates.get(
            option.category, 
            ["Consider {option} for a more sustainable lifestyle"]
        )
        
        # Select appropriate template based on context
        template = random.choice(templates)
        
        # Personalize the recommendation
        recommendation = template.format(option=option.name)
        
        # Add personal touch
        if context.personal.user_id:
            recommendation = f"Hey {context.personal.user_id}, {recommendation}"
        
        # Add timing
        if context.temporal.day_type == DayType.WEEKEND:
            recommendation += " This weekend is perfect to get started!"
        elif context.temporal.hour < 12:
            recommendation += " Great time to plan this for today!"
        
        return recommendation


class ImpactAnalyzer:
    """Analyze expected impacts of decisions."""
    
    def calculate_expected_impact(self, option: DecisionOption, 
                                 context: DecisionContext) -> Dict[str, float]:
        """Calculate expected impact of a decision."""
        impact = {
            "carbon_reduction": 0.0,
            "cost_savings": 0.0,
            "time_savings": 0.0,
            "health_improvement": 0.0,
            "social_benefit": 0.0,
            "environmental_benefit": 0.0
        }
        
        # Carbon impact
        if option.carbon_impact < 0:
            impact["carbon_reduction"] = abs(option.carbon_impact) * 365
        
        # Cost impact
        if option.cost_impact < 0:
            impact["cost_savings"] = abs(option.cost_impact) * 12  # Monthly savings
        
        # Time impact
        if option.time_impact < 0:
            impact["time_savings"] = abs(option.time_impact) * 12  # Annual time savings
        
        # Health impact
        impact["health_improvement"] = option.health_impact * 0.3
        
        # Social impact
        impact["social_benefit"] = option.social_impact * 0.2
        
        # Environmental impact
        impact["environmental_benefit"] = option.environmental_impact * 0.4
        
        return impact


class ContextOptimizer:
    """Optimize context for better decision outcomes."""
    
    def __init__(self):
        """Initialize the context optimizer."""
        self.optimization_history = []
    
    def optimize_context(self, context: DecisionContext) -> DecisionContext:
        """Optimize the context for better decision making."""
        optimized = context
        
        # Temporal optimization
        if context.temporal.energy_level < 0.4:
            # Suggest better timing
            optimized.temporal.mood = UserMood.MOTIVATED
            optimized.temporal.energy_level = 0.7
        
        # Geographic optimization
        if context.geographic.public_transport_availability < 0.3:
            # Suggest alternatives
            if context.geographic.walkability_score > 0.6:
                optimized.geographic.public_transport_availability = 0.5
        
        # Personal optimization
        if context.personal.sustainability_attitude < 0.5:
            # Encourage attitude improvement
            optimized.personal.sustainability_attitude = 0.6
        
        # Behavioral optimization
        if context.behavioral.fatigue_level > 0.6:
            # Suggest rest before decisions
            optimized.behavioral.fatigue_level = 0.4
        
        return optimized
    
    def suggest_context_improvements(self, context: DecisionContext) -> List[str]:
        """Suggest improvements to the context."""
        suggestions = []
        
        # Temporal improvements
        if context.temporal.energy_level < 0.5:
            suggestions.append("Consider making decisions when you're more energized")
        if context.temporal.mood in [UserMood.STRESSED, UserMood.ANXIOUS]:
            suggestions.append("Take a moment to relax before making important decisions")
        
        # Geographic improvements
        if context.geographic.public_transport_availability < 0.3:
            suggestions.append("Explore public transport options in your area")
        if context.geographic.bike_infrastructure_quality < 0.3:
            suggestions.append("Consider advocating for better bike infrastructure")
        
        # Personal improvements
        if context.personal.sustainability_attitude < 0.5:
            suggestions.append("Learn more about sustainability to increase motivation")
        if context.personal.risk_tolerance < 0.3:
            suggestions.append("Start with low-risk sustainable actions to build confidence")
        
        # Behavioral improvements
        if context.behavioral.fatigue_level > 0.6:
            suggestions.append("Get adequate rest before implementing new changes")
        if context.behavioral.routine_deviation > 0.7:
            suggestions.append("Establish a consistent routine for sustainability habits")
        
        return suggestions[:5]  # Return top 5 suggestions


# ============================================================================
# SMART DECISION ORCHESTRATOR
# ============================================================================

class SmartDecisionOrchestrator:
    """
    Orchestrates the entire decision intelligence system.
    """
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.engine = ContextAwareDecisionEngine()
        self.logger = logging.getLogger(f"{__name__}.SmartDecisionOrchestrator")
        self.decision_history = []
        self.user_profiles = {}
    
    def process_decision_request(self, user_id: str, 
                                context: DecisionContext,
                                category: Optional[str] = None) -> DecisionResult:
        """
        Process a decision request and return recommendations.
        """
        self.logger.info(f"Processing decision request for user: {user_id}")
        
        # Set user ID in context
        context.personal.user_id = user_id
        
        # Get user profile if exists
        if user_id in self.user_profiles:
            profile = self.user_profiles[user_id]
            self._enrich_context_from_profile(context, profile)
        
        # Optimize context
        optimized_context = self.engine.context_optimizer.optimize_context(context)
        
        # Get recommendations
        result = self.engine.recommend_decision(optimized_context, category)
        
        # Add context improvement suggestions
        improvements = self.engine.context_optimizer.suggest_context_improvements(
            optimized_context
        )
        
        # Store decision
        decision = SustainabilityDecision(
            decision_id=f"dec_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=user_id,
            decision_type=category or "general",
            context=optimized_context,
            selected_option=result.recommended_option,
            alternatives=result.alternatives
        )
        
        self.decision_history.append(decision)
        
        # Generate enhanced result
        result.reasoning.extend(improvements[:2])
        
        return result
    
    def _enrich_context_from_profile(self, context: DecisionContext, 
                                    profile: Dict[str, Any]):
        """Enrich context with user profile data."""
        if "preferences" in profile:
            context.personal.sustainability_attitude = profile["preferences"].get(
                "sustainability_attitude", context.personal.sustainability_attitude
            )
            context.personal.risk_tolerance = profile["preferences"].get(
                "risk_tolerance", context.personal.risk_tolerance
            )
        
        if "location" in profile:
            context.geographic.city = profile["location"].get("city", context.geographic.city)
            context.geographic.country = profile["location"].get("country", context.geographic.country)
        
        if "goals" in profile:
            context.personal.personal_goals = profile["goals"]
    
    def create_user_profile(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a user profile."""
        profile = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "preferences": preferences,
            "decision_history": [],
            "progress": {}
        }
        
        self.user_profiles[user_id] = profile
        return profile
    
    def get_decision_history(self, user_id: str, limit: int = 10) -> List[SustainabilityDecision]:
        """Get decision history for a user."""
        user_decisions = [d for d in self.decision_history if d.user_id == user_id]
        return user_decisions[-limit:]
    
    def get_impact_summary(self, user_id: str) -> Dict[str, float]:
        """Get summary of impacts from user's decisions."""
        user_decisions = [d for d in self.decision_history if d.user_id == user_id]
        
        summary = {
            "total_carbon_saved": 0.0,
            "total_cost_saved": 0.0,
            "total_decisions": len(user_decisions),
            "success_rate": 0.0,
            "top_impact_categories": {}
        }
        
        if not user_decisions:
            return summary
        
        # Calculate impacts
        for decision in user_decisions:
            if decision.selected_option and hasattr(decision, 'actual_outcome'):
                outcome = decision.actual_outcome or {}
                summary["total_carbon_saved"] += outcome.get("carbon_saved", 0)
                summary["total_cost_saved"] += outcome.get("cost_saved", 0)
        
        # Calculate success rate
        successes = sum(1 for d in user_decisions if d.feedback_score and d.feedback_score >= 0.7)
        summary["success_rate"] = successes / len(user_decisions) if user_decisions else 0
        
        # Calculate top impact categories
        category_impacts = defaultdict(float)
        for decision in user_decisions:
            if decision.selected_option:
                category_impacts[decision.selected_option.category] += 1
        
        summary["top_impact_categories"] = dict(
            sorted(category_impacts.items(), key=lambda x: x[1], reverse=True)[:3]
        )
        
        return summary


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_season(timestamp: Optional[datetime] = None) -> str:
    """Get the season for a given date."""
    if timestamp is None:
        timestamp = datetime.now()
    
    month = timestamp.month
    if 3 <= month <= 5:
        return "spring"
    elif 6 <= month <= 8:
        return "summer"
    elif 9 <= month <= 11:
        return "autumn"
    else:
        return "winter"


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================

def demonstrate_system():
    """Demonstrate the context-aware sustainability decision system."""
    print("\n" + "=" * 70)
    print("CONTEXT-AWARE SUSTAINABILITY DECISION INTELLIGENCE SYSTEM")
    print("=" * 70 + "\n")
    
    # Initialize orchestrator
    orchestrator = SmartDecisionOrchestrator()
    
    # Create user profile
    user_profile = orchestrator.create_user_profile(
        "user123",
        {
            "sustainability_attitude": 0.8,
            "risk_tolerance": 0.6,
            "convenience_preference": 0.5,
            "budget_constraints": True,
            "time_constraints": True
        }
    )
    print(f"✓ User profile created for: {user_profile['user_id']}")
    
    # Create a rich context
    context = DecisionContext(
        temporal=TemporalContext(
            timestamp=datetime.now(),
            day_type=DayType.WEEKDAY,
            hour=8,
            energy_level=0.8,
            mood=UserMood.MOTIVATED,
            time_available=60
        ),
        geographic=GeographicContext(
            country="US",
            city="San Francisco",
            urban_rural="urban",
            public_transport_availability=0.7,
            bike_infrastructure_quality=0.6,
            walkability_score=0.8,
            temperature_celsius=18.0,
            weather=WeatherCondition.SUNNY
        ),
        personal=PersonalContext(
            age=32,
            occupation="Software Engineer",
            sustainability_attitude=0.8,
            personal_goals=[
                SustainabilityGoal.CARBON_REDUCTION,
                SustainabilityGoal.ENERGY_EFFICIENCY
            ],
            home_ownership=True
        ),
        economic=EconomicContext(
            available_income=5000,
            cost_sensitivity=0.5,
            investment_ability=0.7
        )
    )
    
    print("✓ Context created successfully")
    
    # Process decision request for transportation
    print("\n" + "-" * 60)
    print("TRANSPORTATION DECISION RECOMMENDATION")
    print("-" * 60 + "\n")
    
    result = orchestrator.process_decision_request("user123", context, "transportation")
    
    print(f"Recommended: {result.recommended_option.name}")
    print(f"Score: {result.score:.2f}")
    print(f"Confidence: {result.confidence:.2%}")
    print("\nReasoning:")
    for reason in result.reasoning[:5]:
        print(f"  • {reason}")
    
    print(f"\nAction Plan:")
    for step in result.action_plan[:3]:
        print(f"  {step['step']}. {step['action']}")
        print(f"     Time: {step['time_estimate']}")
    
    # Process another decision for energy
    print("\n" + "-" * 60)
    print("ENERGY DECISION RECOMMENDATION")
    print("-" * 60 + "\n")
    
    context.temporal.hour = 14
    result2 = orchestrator.process_decision_request("user123", context, "energy")
    
    print(f"Recommended: {result2.recommended_option.name}")
    print(f"Score: {result2.score:.2f}")
    print(f"Confidence: {result2.confidence:.2%}")
    
    # Show impact summary
    print("\n" + "-" * 60)
    print("IMPACT SUMMARY")
    print("-" * 60 + "\n")
    
    summary = orchestrator.get_impact_summary("user123")
    print(f"Total decisions: {summary['total_decisions']}")
    print(f"Success rate: {summary['success_rate']:.1%}")
    print(f"Top impact categories: {summary['top_impact_categories']}")
    
    # Context improvements
    print("\n" + "-" * 60)
    print("CONTEXT IMPROVEMENT SUGGESTIONS")
    print("-" * 60 + "\n")
    
    improvements = orchestrator.engine.context_optimizer.suggest_context_improvements(context)
    for suggestion in improvements[:5]:
        print(f"  • {suggestion}")
    
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70 + "\n")


def run_integration_tests():
    """Run integration tests for the system."""
    print("\n" + "=" * 60)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 60 + "\n")
    
    # Test 1: Decision engine initialization
    print("Test 1: Engine Initialization")
    engine = ContextAwareDecisionEngine()
    assert engine.option_database is not None
    assert len(engine.get_decision_options()) > 0
    print("✓ Engine initialized successfully")
    
    # Test 2: Context analysis
    print("\nTest 2: Context Analysis")
    context = DecisionContext()
    analysis = engine.analyze_context(context)
    assert len(analysis) == 6
    assert all(0 <= v <= 1 for v in analysis.values())
    print("✓ Context analysis works correctly")
    
    # Test 3: Recommendation generation
    print("\nTest 3: Recommendation Generation")
    result = engine.recommend_decision(context)
    assert result.recommended_option is not None
    assert len(result.reasoning) > 0
    assert len(result.action_plan) > 0
    print(f"✓ Generated recommendation: {result.recommended_option.name}")
    
    # Test 4: Learning model
    print("\nTest 4: Learning Model")
    model = DecisionLearningModel()
    model.update_from_decision(result)
    success_rate = model.predict_success(result.recommended_option, context)
    assert 0 <= success_rate <= 1
    print(f"✓ Learning model prediction: {success_rate:.2%}")
    
    # Test 5: Impact analysis
    print("\nTest 5: Impact Analysis")
    analyzer = ImpactAnalyzer()
    impact = analyzer.calculate_expected_impact(result.recommended_option, context)
    assert "carbon_reduction" in impact
    assert "cost_savings" in impact
    print("✓ Impact analysis works correctly")
    
    # Test 6: Pattern recognition
    print("\nTest 6: Pattern Recognition")
    recognizer = BehavioralPatternRecognizer()
    analysis = recognizer.analyze_behavior(BehavioralContext())
    assert "routine_strength" in analysis
    assert "change_readiness" in analysis
    print("✓ Pattern recognition works correctly")
    
    # Test 7: Full orchestrator
    print("\nTest 7: Orchestrator")
    orchestrator = SmartDecisionOrchestrator()
    orchestrator.create_user_profile("test_user", {"sustainability_attitude": 0.7})
    result = orchestrator.process_decision_request("test_user", context)
    assert result.recommended_option is not None
    print("✓ Orchestrator works correctly")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60 + "\n")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the context-aware system."""
    print("\n" + "=" * 70)
    print("ECOBUDDY - Context-Aware Sustainability Decision Intelligence System")
    print("Version 2.0.0")
    print("=" * 70 + "\n")
    
    print("Select an option:")
    print("1. Run demonstration")
    print("2. Run integration tests")
    print("3. Interactive decision assistant")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        demonstrate_system()
    elif choice == '2':
        run_integration_tests()
    elif choice == '3':
        print("\nInteractive mode coming soon!")
        print("Please run the demonstration for now.")
    else:
        print("Goodbye!")


if __name__ == "__main__":
    main()


"""
Environmental Anomaly Detection and Early Warning Framework
============================================================

A comprehensive framework for detecting environmental anomalies and providing
early warnings using statistical methods, machine learning, and time series analysis.

Author: AI Assistant
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings
import json
import logging
from scipy import stats
from scipy.signal import find_peaks, savgol_filter
from scipy.stats import zscore, median_abs_deviation
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.svm import OneClassSVM
from sklearn.neighbors import LocalOutlierFactor
from sklearn.decomposition import PCA
from sklearn.covariance import EllipticEnvelope
import joblib
import os
from collections import deque
import threading
import time
import pickle
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnomalySeverity(Enum):
    """Anomaly severity levels."""
    NORMAL = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AnomalyType(Enum):
    """Types of environmental anomalies."""
    TEMPERATURE_SPIKE = "temperature_spike"
    TEMPERATURE_DROP = "temperature_drop"
    PRESSURE_ANOMALY = "pressure_anomaly"
    HUMIDITY_ANOMALY = "humidity_anomaly"
    AIR_QUALITY_DEGRADATION = "air_quality_degradation"
    WIND_SPEED_ANOMALY = "wind_speed_anomaly"
    PRECIPITATION_ANOMALY = "precipitation_anomaly"
    MULTIVARIATE_ANOMALY = "multivariate_anomaly"
    SEASONAL_ANOMALY = "seasonal_anomaly"
    TREND_SHIFT = "trend_shift"


@dataclass
class AnomalyReport:
    """Data structure for anomaly reports."""
    timestamp: datetime
    parameter: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    value: float
    expected_value: float
    threshold: float
    confidence_score: float
    description: str
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EarlyWarning:
    """Data structure for early warnings."""
    timestamp: datetime
    parameter: str
    predicted_anomaly_type: AnomalyType
    predicted_severity: AnomalySeverity
    prediction_time_horizon: int  # hours ahead
    current_trend: str
    risk_score: float
    confidence: float
    mitigation_strategies: List[str]
    affected_areas: List[str]


class DataPreprocessor:
    """
    Data preprocessing class for environmental data.
    Handles missing values, outliers, normalization, and feature engineering.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.scalers = {}
        self.rolling_windows = self.config.get('rolling_windows', [1, 3, 6, 12, 24])
        self.outlier_method = self.config.get('outlier_method', 'iqr')
        self.normalization_method = self.config.get('normalization_method', 'standard')
        
    def handle_missing_values(self, df: pd.DataFrame, method: str = 'interpolate') -> pd.DataFrame:
        """
        Handle missing values in the dataset.
        
        Args:
            df: Input dataframe
            method: Method to handle missing values ('interpolate', 'ffill', 'bfill', 'drop')
            
        Returns:
            DataFrame with handled missing values
        """
        df_clean = df.copy()
        
        if method == 'interpolate':
            df_clean = df_clean.interpolate(method='time', limit_area='inside')
            df_clean = df_clean.bfill().ffill()
        elif method == 'ffill':
            df_clean = df_clean.ffill()
        elif method == 'bfill':
            df_clean = df_clean.bfill()
        elif method == 'drop':
            df_clean = df_clean.dropna()
        else:
            raise ValueError(f"Unknown method: {method}")
            
        logger.info(f"Handled missing values using {method} method")
        return df_clean
    
    def remove_outliers(self, df: pd.DataFrame, method: str = None) -> pd.DataFrame:
        """
        Remove outliers from the dataset.
        
        Args:
            df: Input dataframe
            method: Outlier removal method ('iqr', 'zscore', 'mad')
            
        Returns:
            DataFrame with outliers removed
        """
        method = method or self.outlier_method
        df_clean = df.copy()
        
        for column in df_clean.select_dtypes(include=[np.number]).columns:
            if method == 'iqr':
                Q1 = df_clean[column].quantile(0.25)
                Q3 = df_clean[column].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df_clean[column] = df_clean[column].clip(lower_bound, upper_bound)
                
            elif method == 'zscore':
                z_scores = np.abs(zscore(df_clean[column].values))
                threshold = self.config.get('zscore_threshold', 3)
                df_clean[column] = df_clean[column].mask(z_scores > threshold, df_clean[column].mean())
                
            elif method == 'mad':
                median = df_clean[column].median()
                mad = median_abs_deviation(df_clean[column].values)
                threshold = self.config.get('mad_threshold', 3)
                df_clean[column] = df_clean[column].mask(
                    np.abs(df_clean[column] - median) > threshold * mad,
                    median
                )
                
        logger.info(f"Removed outliers using {method} method")
        return df_clean
    
    def normalize_data(self, df: pd.DataFrame, method: str = None) -> pd.DataFrame:
        """
        Normalize the data.
        
        Args:
            df: Input dataframe
            method: Normalization method ('standard', 'minmax', 'robust')
            
        Returns:
            Normalized dataframe
        """
        method = method or self.normalization_method
        df_norm = df.copy()
        numeric_cols = df_norm.select_dtypes(include=[np.number]).columns
        
        if method == 'standard':
            for col in numeric_cols:
                scaler = StandardScaler()
                df_norm[col] = scaler.fit_transform(df_norm[[col]].values)
                self.scalers[f'{col}_scaler'] = scaler
                
        elif method == 'minmax':
            for col in numeric_cols:
                min_val = df_norm[col].min()
                max_val = df_norm[col].max()
                df_norm[col] = (df_norm[col] - min_val) / (max_val - min_val)
                
        elif method == 'robust':
            for col in numeric_cols:
                median = df_norm[col].median()
                q1 = df_norm[col].quantile(0.25)
                q3 = df_norm[col].quantile(0.75)
                iqr = q3 - q1
                df_norm[col] = (df_norm[col] - median) / iqr if iqr != 0 else df_norm[col]
                
        logger.info(f"Normalized data using {method} method")
        return df_norm
    
    def create_features(self, df: pd.DataFrame, target_col: str = None) -> pd.DataFrame:
        """
        Create additional features from the data.
        
        Args:
            df: Input dataframe
            target_col: Target column for lag features
            
        Returns:
            DataFrame with additional features
        """
        df_features = df.copy()
        
        # Add rolling statistics
        for window in self.rolling_windows:
            for col in df_features.select_dtypes(include=[np.number]).columns:
                df_features[f'{col}_rolling_mean_{window}'] = df_features[col].rolling(window=window).mean()
                df_features[f'{col}_rolling_std_{window}'] = df_features[col].rolling(window=window).std()
                df_features[f'{col}_rolling_min_{window}'] = df_features[col].rolling(window=window).min()
                df_features[f'{col}_rolling_max_{window}'] = df_features[col].rolling(window=window).max()
        
        # Add lag features
        if target_col:
            for lag in [1, 3, 6, 12, 24]:
                df_features[f'{target_col}_lag_{lag}'] = df_features[target_col].shift(lag)
        
        # Add rate of change features
        for col in df_features.select_dtypes(include=[np.number]).columns:
            df_features[f'{col}_diff_1'] = df_features[col].diff()
            df_features[f'{col}_diff_3'] = df_features[col].diff(3)
            df_features[f'{col}_pct_change'] = df_features[col].pct_change()
        
        # Add time-based features
        if 'timestamp' in df_features.columns:
            df_features['hour'] = df_features['timestamp'].dt.hour
            df_features['day_of_week'] = df_features['timestamp'].dt.dayofweek
            df_features['month'] = df_features['timestamp'].dt.month
            df_features['quarter'] = df_features['timestamp'].dt.quarter
            df_features['is_weekend'] = df_features['timestamp'].dt.dayofweek.isin([5, 6]).astype(int)
            df_features['day_of_year'] = df_features['timestamp'].dt.dayofyear
            df_features['week_of_year'] = df_features['timestamp'].dt.isocalendar().week
        
        logger.info("Created additional features")
        return df_features


class AnomalyDetector(ABC):
    """
    Abstract base class for anomaly detection algorithms.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None
        self.threshold = config.get('threshold', 0.95)
        
    @abstractmethod
    def fit(self, data: pd.DataFrame) -> None:
        """Fit the anomaly detection model."""
        pass
    
    @abstractmethod
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies in the data."""
        pass
    
    @abstractmethod
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores for the data."""
        pass


class StatisticalAnomalyDetector(AnomalyDetector):
    """
    Statistical methods for anomaly detection.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.method = self.config.get('method', 'zscore')
        self.window_size = self.config.get('window_size', 30)
        self.upper_threshold = self.config.get('upper_threshold', 3.0)
        self.lower_threshold = self.config.get('lower_threshold', 3.0)
        self.seasonal_period = self.config.get('seasonal_period', 24)
        
    def fit(self, data: pd.DataFrame) -> None:
        """Fit statistical model parameters."""
        self.data_stats = {}
        
        for col in data.select_dtypes(include=[np.number]).columns:
            self.data_stats[col] = {
                'mean': data[col].mean(),
                'std': data[col].std(),
                'median': data[col].median(),
                'mad': median_abs_deviation(data[col].values),
                'q1': data[col].quantile(0.25),
                'q3': data[col].quantile(0.75),
                'min': data[col].min(),
                'max': data[col].max(),
                'seasonal_pattern': self._compute_seasonal_pattern(data, col)
            }
            
        logger.info("Statistical model fitted successfully")
    
    def _compute_seasonal_pattern(self, data: pd.DataFrame, col: str) -> np.ndarray:
        """Compute seasonal pattern for a column."""
        if len(data) < self.seasonal_period * 2:
            return np.array([])
            
        # Compute average pattern for each period
        n_periods = len(data) // self.seasonal_period
        if n_periods < 1:
            return np.array([])
            
        pattern = np.zeros(self.seasonal_period)
        for i in range(self.seasonal_period):
            values = data[col].iloc[i::self.seasonal_period]
            if len(values) > 0:
                pattern[i] = values.mean()
                
        return pattern
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using statistical methods."""
        reports = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            stats_info = self.data_stats.get(col, {})
            
            for idx, value in enumerate(values):
                if idx < len(data):
                    timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                    
                    if self.method == 'zscore':
                        zscore_value = (value - stats_info.get('mean', 0)) / (stats_info.get('std', 1) + 1e-10)
                        if abs(zscore_value) > self.upper_threshold:
                            reports.append(self._create_anomaly_report(
                                timestamp, col, value, zscore_value, 
                                'zscore_anomaly', AnomalySeverity.MEDIUM
                            ))
                    elif self.method == 'mad':
                        mad_score = (value - stats_info.get('median', 0)) / (stats_info.get('mad', 1) + 1e-10)
                        if abs(mad_score) > self.upper_threshold:
                            reports.append(self._create_anomaly_report(
                                timestamp, col, value, mad_score,
                                'mad_anomaly', AnomalySeverity.MEDIUM
                            ))
                    elif self.method == 'iqr':
                        q1 = stats_info.get('q1', 0)
                        q3 = stats_info.get('q3', 0)
                        iqr = q3 - q1
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr
                        
                        if value < lower_bound or value > upper_bound:
                            severity = AnomalySeverity.HIGH if abs(value - stats_info.get('median', 0)) > 3 * iqr else AnomalySeverity.MEDIUM
                            reports.append(self._create_anomaly_report(
                                timestamp, col, value, (value - stats_info.get('median', 0)) / (iqr + 1e-10),
                                'iqr_anomaly', severity
                            ))
                            
        return reports
    
    def _create_anomaly_report(self, timestamp, col, value, score, anomaly_type, severity):
        """Create an anomaly report."""
        return AnomalyReport(
            timestamp=timestamp or datetime.now(),
            parameter=col,
            anomaly_type=AnomalyType.TEMPERATURE_SPIKE,  # Placeholder
            severity=severity,
            value=float(value),
            expected_value=float(self.data_stats.get(col, {}).get('mean', value)),
            threshold=float(self.upper_threshold),
            confidence_score=min(1.0, abs(score) / self.upper_threshold),
            description=f"Statistical anomaly detected in {col} with score {score:.2f}",
            recommendations=["Investigate data source", "Check sensor calibration"],
            metadata={'score': score, 'method': self.method}
        )
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores for the data."""
        scores = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            stats_info = self.data_stats.get(col, {})
            
            if self.method == 'zscore':
                col_scores = (values - stats_info.get('mean', 0)) / (stats_info.get('std', 1) + 1e-10)
            elif self.method == 'mad':
                col_scores = (values - stats_info.get('median', 0)) / (stats_info.get('mad', 1) + 1e-10)
            else:
                col_scores = np.zeros_like(values)
                
            scores.append(np.abs(col_scores))
            
        return np.column_stack(scores) if scores else np.array([])


class MachineLearningAnomalyDetector(AnomalyDetector):
    """
    Machine learning-based anomaly detection.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.algorithm = self.config.get('algorithm', 'isolation_forest')
        self.contamination = self.config.get('contamination', 0.1)
        self.n_estimators = self.config.get('n_estimators', 100)
        self.feature_columns = self.config.get('feature_columns', [])
        self.scaler = StandardScaler()
        
    def fit(self, data: pd.DataFrame) -> None:
        """Fit the machine learning model."""
        features = self._prepare_features(data)
        
        if self.algorithm == 'isolation_forest':
            self.model = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                random_state=42
            )
        elif self.algorithm == 'one_class_svm':
            self.model = OneClassSVM(
                nu=self.contamination,
                kernel='rbf',
                gamma='auto'
            )
        elif self.algorithm == 'local_outlier_factor':
            self.model = LocalOutlierFactor(
                contamination=self.contamination,
                novelty=True
            )
        elif self.algorithm == 'elliptic_envelope':
            self.model = EllipticEnvelope(
                contamination=self.contamination,
                random_state=42
            )
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
            
        self.model.fit(features)
        logger.info(f"ML model {self.algorithm} fitted successfully")
    
    def _prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare features for the model."""
        if self.feature_columns:
            features = data[self.feature_columns].values
        else:
            features = data.select_dtypes(include=[np.number]).values
            
        # Handle missing values
        features = np.nan_to_num(features, nan=0.0)
        
        # Scale features
        features = self.scaler.fit_transform(features)
        
        return features
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using ML model."""
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
            
        features = self._prepare_features(data)
        predictions = self.model.predict(features)
        scores = self.model.score_samples(features) if hasattr(self.model, 'score_samples') else None
        
        reports = []
        for idx, pred in enumerate(predictions):
            if pred == -1:  # Anomaly
                timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                severity = self._determine_severity(scores[idx] if scores is not None else 0)
                
                reports.append(AnomalyReport(
                    timestamp=timestamp or datetime.now(),
                    parameter="multivariate",
                    anomaly_type=AnomalyType.MULTIVARIATE_ANOMALY,
                    severity=severity,
                    value=float(scores[idx] if scores is not None else 0),
                    expected_value=0.0,
                    threshold=0.0,
                    confidence_score=1.0 if scores is None else min(1.0, abs(scores[idx])),
                    description=f"ML-based anomaly detected by {self.algorithm}",
                    recommendations=["Check all environmental parameters", "Validate sensor data"],
                    metadata={'algorithm': self.algorithm, 'prediction': int(pred)}
                ))
                
        return reports
    
    def _determine_severity(self, score: float) -> AnomalySeverity:
        """Determine severity based on anomaly score."""
        if abs(score) > 0.8:
            return AnomalySeverity.CRITICAL
        elif abs(score) > 0.6:
            return AnomalySeverity.HIGH
        elif abs(score) > 0.4:
            return AnomalySeverity.MEDIUM
        elif abs(score) > 0.2:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.NORMAL
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores."""
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
            
        features = self._prepare_features(data)
        
        if hasattr(self.model, 'score_samples'):
            return -self.model.score_samples(features)
        else:
            predictions = self.model.predict(features)
            return np.where(predictions == -1, 1.0, 0.0)


class TimeSeriesAnomalyDetector(AnomalyDetector):
    """
    Time series-based anomaly detection using decomposition and forecasting.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.method = self.config.get('method', 'stl_decomposition')
        self.forecast_horizon = self.config.get('forecast_horizon', 24)
        self.confidence_interval = self.config.get('confidence_interval', 0.95)
        self.trend_window = self.config.get('trend_window', 30)
        self.seasonal_period = self.config.get('seasonal_period', 24)
        
    def fit(self, data: pd.DataFrame) -> None:
        """Fit time series models."""
        self.time_series_stats = {}
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            n = len(values)
            
            # Store basic statistics
            self.time_series_stats[col] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'trend': self._compute_trend(values),
                'seasonal': self._compute_seasonal(values),
                'residual': self._compute_residual(values),
                'acf': self._compute_acf(values),
                'pacf': self._compute_pacf(values)
            }
            
        logger.info("Time series model fitted successfully")
    
    def _compute_trend(self, values: np.ndarray) -> np.ndarray:
        """Compute trend component using smoothing."""
        if len(values) < self.trend_window:
            return np.zeros_like(values)
        return savgol_filter(values, window_length=min(self.trend_window, len(values)-1), polyorder=3)
    
    def _compute_seasonal(self, values: np.ndarray) -> np.ndarray:
        """Compute seasonal component."""
        if len(values) < self.seasonal_period * 2:
            return np.zeros_like(values)
            
        n = len(values)
        seasonal = np.zeros(n)
        for i in range(self.seasonal_period):
            indices = range(i, n, self.seasonal_period)
            if len(indices) > 0:
                seasonal[indices] = np.mean(values[indices]) - np.mean(values)
                
        return seasonal
    
    def _compute_residual(self, values: np.ndarray) -> np.ndarray:
        """Compute residual component."""
        trend = self._compute_trend(values)
        seasonal = self._compute_seasonal(values)
        return values - trend - seasonal
    
    def _compute_acf(self, values: np.ndarray, nlags: int = 20) -> np.ndarray:
        """Compute autocorrelation function."""
        n = len(values)
        mean = np.mean(values)
        var = np.var(values)
        if var == 0:
            return np.zeros(nlags + 1)
            
        acf = np.zeros(nlags + 1)
        for lag in range(nlags + 1):
            if lag < n:
                acf[lag] = np.corrcoef(values[:-lag] if lag > 0 else values, 
                                      values[lag:] if lag > 0 else values)[0, 1]
        return acf
    
    def _compute_pacf(self, values: np.ndarray, nlags: int = 20) -> np.ndarray:
        """Compute partial autocorrelation function."""
        n = len(values)
        pacf = np.zeros(nlags + 1)
        pacf[0] = 1.0
        
        if n > 1:
            for lag in range(1, min(nlags + 1, n)):
                # Simple approximation using OLS
                y = values[lag:]
                X = np.column_stack([values[i:-(lag-i)] for i in range(lag+1)])
                if X.shape[0] > 0:
                    try:
                        coeff = np.linalg.lstsq(X, y, rcond=None)[0]
                        pacf[lag] = coeff[-1]
                    except:
                        pacf[lag] = 0
                        
        return pacf
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using time series analysis."""
        reports = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            stats = self.time_series_stats.get(col, {})
            
            if len(values) < 2:
                continue
                
            # Decompose time series
            trend = self._compute_trend(values)
            seasonal = self._compute_seasonal(values)
            residual = values - trend - seasonal
            
            # Calculate anomaly scores
            residual_std = np.std(residual)
            z_scores = np.abs(residual / (residual_std + 1e-10))
            
            # Detect anomalies
            threshold = stats.norm.ppf(self.confidence_interval)
            
            for idx, z_score in enumerate(z_scores):
                if z_score > threshold:
                    timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                    
                    severity = self._determine_severity(z_score)
                    
                    reports.append(AnomalyReport(
                        timestamp=timestamp or datetime.now(),
                        parameter=col,
                        anomaly_type=AnomalyType.SEASONAL_ANOMALY if abs(seasonal[idx]) > 0.5 * abs(values[idx]) else AnomalyType.TREND_SHIFT,
                        severity=severity,
                        value=float(values[idx]),
                        expected_value=float(trend[idx] + seasonal[idx]),
                        threshold=float(threshold * residual_std),
                        confidence_score=min(1.0, z_score / (threshold * 2)),
                        description=f"Time series anomaly detected in {col} with z-score {z_score:.2f}",
                        recommendations=["Check for sudden environmental changes", "Validate with other sensors"],
                        metadata={
                            'z_score': float(z_score),
                            'trend': float(trend[idx]),
                            'seasonal': float(seasonal[idx]),
                            'residual': float(residual[idx])
                        }
                    ))
                    
        return reports
    
    def _determine_severity(self, z_score: float) -> AnomalySeverity:
        """Determine severity based on z-score."""
        if z_score > 6.0:
            return AnomalySeverity.CRITICAL
        elif z_score > 4.0:
            return AnomalySeverity.HIGH
        elif z_score > 3.0:
            return AnomalySeverity.MEDIUM
        elif z_score > 2.0:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.NORMAL
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores based on residuals."""
        scores = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            trend = self._compute_trend(values)
            seasonal = self._compute_seasonal(values)
            residual = values - trend - seasonal
            
            residual_std = np.std(residual) + 1e-10
            col_scores = np.abs(residual / residual_std)
            scores.append(col_scores)
            
        return np.column_stack(scores) if scores else np.array([])


class EnsembleAnomalyDetector(AnomalyDetector):
    """
    Ensemble approach combining multiple anomaly detection methods.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.detectors = []
        self.weights = self.config.get('weights', [])
        self.voting_method = self.config.get('voting_method', 'weighted')
        self._initialize_detectors()
        
    def _initialize_detectors(self) -> None:
        """Initialize individual detectors."""
        detector_configs = self.config.get('detectors', [
            {'type': 'statistical', 'method': 'zscore'},
            {'type': 'statistical', 'method': 'mad'},
            {'type': 'machine_learning', 'algorithm': 'isolation_forest'},
            {'type': 'time_series', 'method': 'stl_decomposition'}
        ])
        
        for config in detector_configs:
            detector_type = config.get('type')
            if detector_type == 'statistical':
                detector = StatisticalAnomalyDetector(config)
            elif detector_type == 'machine_learning':
                detector = MachineLearningAnomalyDetector(config)
            elif detector_type == 'time_series':
                detector = TimeSeriesAnomalyDetector(config)
            else:
                continue
                
            self.detectors.append(detector)
            
        if not self.weights:
            self.weights = [1.0 / len(self.detectors)] * len(self.detectors)
            
    def fit(self, data: pd.DataFrame) -> None:
        """Fit all detectors."""
        for detector in self.detectors:
            detector.fit(data)
        logger.info("All ensemble detectors fitted successfully")
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using ensemble approach."""
        all_reports = []
        detector_scores = []
        
        for detector in self.detectors:
            reports = detector.detect(data)
            all_reports.extend(reports)
            
            # Get scores for voting
            scores = detector.predict_score(data)
            if scores.size > 0:
                detector_scores.append(scores.mean(axis=1))
                
        # Apply ensemble voting
        if detector_scores and self.voting_method == 'weighted':
            ensemble_scores = np.average(detector_scores, weights=self.weights, axis=0)
            
            # Create ensemble reports
            for idx, score in enumerate(ensemble_scores):
                if score > self.threshold:
                    timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                    all_reports.append(AnomalyReport(
                        timestamp=timestamp or datetime.now(),
                        parameter="ensemble",
                        anomaly_type=AnomalyType.MULTIVARIATE_ANOMALY,
                        severity=self._determine_severity(score),
                        value=float(score),
                        expected_value=0.0,
                        threshold=float(self.threshold),
                        confidence_score=min(1.0, score / self.threshold),
                        description=f"Ensemble anomaly detected with score {score:.2f}",
                        recommendations=["Verify with multiple data sources", "Cross-check all parameters"],
                        metadata={'ensemble_score': float(score), 'n_detectors': len(self.detectors)}
                    ))
                    
        return all_reports
    
    def _determine_severity(self, score: float) -> AnomalySeverity:
        """Determine severity based on ensemble score."""
        if score > 0.8 * self.threshold:
            return AnomalySeverity.CRITICAL
        elif score > 0.6 * self.threshold:
            return AnomalySeverity.HIGH
        elif score > 0.4 * self.threshold:
            return AnomalySeverity.MEDIUM
        elif score > 0.2 * self.threshold:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.NORMAL
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores using ensemble."""
        scores = []
        
        for detector in self.detectors:
            detector_scores = detector.predict_score(data)
            if detector_scores.size > 0:
                scores.append(detector_scores)
                
        if scores:
            weighted_scores = np.average(scores, weights=self.weights, axis=0)
            return weighted_scores
        else:
            return np.array([])


class EarlyWarningSystem:
    """
    Early warning system for environmental anomalies.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.historical_data = deque(maxlen=self.config.get('history_length', 1000))
        self.warning_thresholds = self.config.get('warning_thresholds', {})
        self.trend_analysis_window = self.config.get('trend_window', 24)
        self.forecast_horizons = self.config.get('forecast_horizons', [1, 3, 6, 12, 24])
        self.detector = None
        self.monitoring_active = False
        self.monitoring_thread = None
        self.warning_history = deque(maxlen=100)
        self.alert_callbacks = []
        
    def initialize_detector(self, detector_type: str = 'ensemble', **kwargs) -> None:
        """Initialize the anomaly detector."""
        config = self.config.copy()
        config.update(kwargs)
        
        if detector_type == 'statistical':
            self.detector = StatisticalAnomalyDetector(config)
        elif detector_type == 'machine_learning':
            self.detector = MachineLearningAnomalyDetector(config)
        elif detector_type == 'time_series':
            self.detector = TimeSeriesAnomalyDetector(config)
        elif detector_type == 'ensemble':
            self.detector = EnsembleAnomalyDetector(config)
        else:
            raise ValueError(f"Unknown detector type: {detector_type}")
            
        logger.info(f"Initialized {detector_type} detector for early warning system")
    
    def fit(self, data: pd.DataFrame) -> None:
        """Fit the detector with historical data."""
        if self.detector is None:
            raise ValueError("Detector not initialized. Call initialize_detector() first.")
            
        self.detector.fit(data)
        self.historical_data.extend(data.values.tolist())
        logger.info("Early warning system fitted with historical data")
    
    def detect_anomalies(self, data: pd.DataFrame) -> Tuple[List[AnomalyReport], List[EarlyWarning]]:
        """
        Detect anomalies and generate early warnings.
        
        Returns:
            Tuple of (anomaly_reports, early_warnings)
        """
        if self.detector is None:
            raise ValueError("Detector not initialized. Call initialize_detector() first.")
            
        # Detect anomalies
        anomaly_reports = self.detector.detect(data)
        
        # Generate early warnings
        early_warnings = self._generate_early_warnings(data, anomaly_reports)
        
        # Update historical data
        self.historical_data.extend(data.values.tolist())
        self.warning_history.extend(early_warnings)
        
        # Trigger alerts
        self._trigger_alerts(anomaly_reports, early_warnings)
        
        return anomaly_reports, early_warnings
    
    def _generate_early_warnings(self, data: pd.DataFrame, anomalies: List[AnomalyReport]) -> List[EarlyWarning]:
        """Generate early warnings based
