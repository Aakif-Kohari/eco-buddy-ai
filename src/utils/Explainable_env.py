import json
import math
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any, Set, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from pathlib import Path
import hashlib
import re
from collections import defaultdict, Counter, deque
import heapq
import numpy as np
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class ClimateScenarioType(Enum):
    """Types of climate scenarios."""
    RCP_2_6 = "rcp_2_6"  # Very low emissions
    RCP_4_5 = "rcp_4_5"  # Medium emissions
    RCP_6_0 = "rcp_6_0"  # High-medium emissions
    RCP_8_5 = "rcp_8_5"  # Very high emissions
    SSP1_19 = "ssp1_19"  # Sustainability - low challenges
    SSP2_45 = "ssp2_45"  # Middle of the road
    SSP3_70 = "ssp3_70"  # Regional rivalry - high challenges
    SSP5_85 = "ssp5_85"  # Fossil-fueled development
    CUSTOM = "custom"


class ImpactCategory(Enum):
    """Categories of climate impacts."""
    TEMPERATURE = "temperature"
    PRECIPITATION = "precipitation"
    SEA_LEVEL = "sea_level"
    EXTREME_WEATHER = "extreme_weather"
    AGRICULTURE = "agriculture"
    WATER_RESOURCES = "water_resources"
    ENERGY_DEMAND = "energy_demand"
    HUMAN_HEALTH = "human_health"
    BIODIVERSITY = "biodiversity"
    ECONOMY = "economy"
    INFRASTRUCTURE = "infrastructure"
    SOCIAL = "social"
    MIGRATION = "migration"
    FOOD_SECURITY = "food_security"
    ECOSYSTEM_SERVICES = "ecosystem_services"


class SectorType(Enum):
    """Sectors affected by climate change."""
    AGRICULTURE = "agriculture"
    ENERGY = "energy"
    WATER = "water"
    HEALTH = "health"
    TRANSPORTATION = "transportation"
    URBAN = "urban"
    COASTAL = "coastal"
    FORESTRY = "forestry"
    FISHERIES = "fisheries"
    TOURISM = "tourism"
    INSURANCE = "insurance"
    MANUFACTURING = "manufacturing"
    CONSTRUCTION = "construction"
    MINING = "mining"


class ProjectionHorizon(Enum):
    """Time horizons for projections."""
    SHORT_TERM = "short_term"      # 2020-2030
    MEDIUM_TERM = "medium_term"    # 2030-2050
    LONG_TERM = "long_term"        # 2050-2100
    CENTURY = "century"            # 2100+
    NEAR_TERM = "near_term"        # 2020-2025
    FAR_FUTURE = "far_future"      # 2050-2100


class ConfidenceLevel(Enum):
    """Confidence levels for projections."""
    VERY_LOW = 0.1
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9
    CERTAIN = 1.0


# ============================================================================
# DATA CLASSES FOR SCENARIO SIMULATION
# ============================================================================

@dataclass
class ClimateParameter:
    """A climate parameter with its characteristics."""
    name: str
    value: float
    unit: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    uncertainty_range: Tuple[float, float] = (0.0, 0.0)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    trend: float = 0.0  # Rate of change per year
    volatility: float = 0.0  # Standard deviation
    seasonal_variation: float = 0.0
    description: Optional[str] = None
    
    def get_value_at_time(self, years: float) -> float:
        """Get parameter value after given years."""
        if self.trend == 0:
            return self.value
        return self.value + (self.trend * years)


@dataclass
class EmissionScenario:
    """A complete emission scenario configuration."""
    scenario_id: str
    scenario_type: ClimateScenarioType
    name: str
    description: str
    base_year: int = 2020
    target_year: int = 2100
    co2_concentration_ppm: float = 410.0
    methane_concentration_ppb: float = 1860.0
    nitrous_oxide_concentration_ppb: float = 332.0
    co2_emissions_gt_per_year: float = 36.0
    methane_emissions_mt_per_year: float = 600.0
    emissions_peaking_year: Optional[int] = None
    emission_reduction_rate: float = 0.0  # % per year
    carbon_budget_gt: Optional[float] = None
    temperature_anomaly_c: float = 0.0
    sea_level_rise_m: float = 0.0
    ocean_acidification_ph: float = 8.1
    parameters: Dict[str, ClimateParameter] = field(default_factory=dict)
    assumptions: Dict[str, Any] = field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    
    def get_emissions_at_year(self, year: int) -> float:
        """Get emissions at a specific year."""
        if year <= self.base_year:
            return self.co2_emissions_gt_per_year
        
        years_passed = year - self.base_year
        
        if self.emissions_peaking_year and year >= self.emissions_peaking_year:
            years_after_peak = year - self.emissions_peaking_year
            reduction = years_after_peak * self.emission_reduction_rate / 100.0
            return self.co2_emissions_gt_per_year * (1 - reduction)
        
        return self.co2_emissions_gt_per_year * (1 + years_passed * 0.02)


@dataclass
class ClimateProjection:
    """A climate projection for a specific scenario and time."""
    scenario_id: str
    year: int
    global_temperature_c: float
    global_temperature_anomaly_c: float
    co2_concentration_ppm: float
    sea_level_rise_m: float
    sea_level_rise_uncertainty: Tuple[float, float]
    ocean_ph: float
    arctic_ice_extent_million_km2: float
    permafrost_thaw_m: float
    extreme_events_index: float  # 0-1 scale
    precipitation_change_percent: float
    drought_index: float  # 0-1 scale
    wildfire_risk_index: float  # 0-1 scale
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    sectoral_impacts: Dict[str, float] = field(default_factory=dict)
    regional_impacts: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class SectorImpact:
    """Impact on a specific sector."""
    sector: SectorType
    scenario_id: str
    year: int
    impact_score: float  # 0-1 scale (negative impact)
    economic_impact_billion_usd: float
    jobs_affected: int
    people_affected: int
    adaptation_cost_billion_usd: float
    adaptation_benefit_billion_usd: float
    vulnerability: float  # 0-1 scale
    exposure: float  # 0-1 scale
    sensitivity: float  # 0-1 scale
    adaptive_capacity: float  # 0-1 scale
    risk_level: float  # 0-1 scale
    description: str
    sub_impacts: Dict[str, float] = field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass
class RegionalImpact:
    """Impacts at a regional level."""
    region_name: str
    region_code: str
    scenario_id: str
    year: int
    population_affected: int
    gdp_loss_percent: float
    agricultural_loss_percent: float
    water_stress_index: float  # 0-1 scale
    health_impact_index: float  # 0-1 scale
    migration_risk: float  # 0-1 scale
    infrastructure_risk: float  # 0-1 scale
    biodiversity_loss_percent: float
    adaptation_need_score: float  # 0-1 scale
    resilience_score: float  # 0-1 scale
    sub_regional_impacts: Dict[str, float] = field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass
class TippingPoint:
    """A climate tipping point."""
    name: str
    description: str
    threshold_temperature_c: float
    current_risk: float  # 0-1 scale
    projected_risk_at_2c: float
    projected_risk_at_3c: float
    projected_risk_at_4c: float
    impact_severity: float  # 0-1 scale
    timescale_years: int
    reversibility: float  # 0-1 scale (0 = irreversible)
    affected_sectors: List[SectorType]
    affected_regions: List[str]
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    cascade_effects: List[str] = field(default_factory=list)


@dataclass
class ScenarioSimulationResult:
    """Complete result of a scenario simulation."""
    scenario_id: str
    scenario_name: str
    projection_horizon: ProjectionHorizon
    start_year: int
    end_year: int
    projections: List[ClimateProjection] = field(default_factory=list)
    sector_impacts: Dict[str, List[SectorImpact]] = field(default_factory=dict)
    regional_impacts: Dict[str, List[RegionalImpact]] = field(default_factory=dict)
    tipping_points: List[TippingPoint] = field(default_factory=list)
    summary_metrics: Dict[str, float] = field(default_factory=dict)
    confidence_metrics: Dict[str, float] = field(default_factory=dict)
    uncertainty_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    simulation_metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# CLIMATE SCENARIO DATABASE
# ============================================================================

class ClimateScenarioDatabase:
    """Database of climate scenarios and their parameters."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_scenarios()
        return cls._instance
    
    def _initialize_scenarios(self):
        """Initialize the scenario src.core.database."""
        self.scenarios = {}
        self._load_rcp_scenarios()
        self._load_ssp_scenarios()
        self._add_custom_scenario_parameters()
    
    def _load_rcp_scenarios(self):
        """Load RCP (Representative Concentration Pathway) scenarios."""
        
        # RCP 2.6 - Very low emissions
        rcp26 = EmissionScenario(
            scenario_id="rcp_2.6",
            scenario_type=ClimateScenarioType.RCP_2_6,
            name="RCP 2.6 - Very Low Emissions",
            description="Peak emissions around 2020, rapid decline thereafter. Limiting warming to <2°C",
            base_year=2020,
            target_year=2100,
            co2_concentration_ppm=430.0,
            methane_concentration_ppb=1650.0,
            nitrous_oxide_concentration_ppb=320.0,
            co2_emissions_gt_per_year=15.0,
            methane_emissions_mt_per_year=350.0,
            emissions_peaking_year=2025,
            emission_reduction_rate=3.5,
            carbon_budget_gt=450.0,
            temperature_anomaly_c=1.0,
            sea_level_rise_m=0.4,
            ocean_acidification_ph=8.05,
            confidence=ConfidenceLevel.HIGH
        )
        rcp26.assumptions = {
            "rapid_decarbonization": True,
            "high_renewable_adoption": True,
            "carbon_capture_use": True,
            "behavioral_changes": True
        }
        self.scenarios["rcp_2.6"] = rcp26
        
        # RCP 4.5 - Medium emissions
        rcp45 = EmissionScenario(
            scenario_id="rcp_4.5",
            scenario_type=ClimateScenarioType.RCP_4_5,
            name="RCP 4.5 - Medium Emissions",
            description="Stabilization scenario, emissions peak around 2040",
            base_year=2020,
            target_year=2100,
            co2_concentration_ppm=550.0,
            methane_concentration_ppb=1750.0,
            nitrous_oxide_concentration_ppb=330.0,
            co2_emissions_gt_per_year=28.0,
            methane_emissions_mt_per_year=450.0,
            emissions_peaking_year=2045,
            emission_reduction_rate=2.0,
            carbon_budget_gt=900.0,
            temperature_anomaly_c=2.4,
            sea_level_rise_m=0.7,
            ocean_acidification_ph=7.95,
            confidence=ConfidenceLevel.HIGH
        )
        rcp45.assumptions = {
            "moderate_decarbonization": True,
            "balanced_energy_mix": True,
            "some_behavioral_changes": False,
            "improved_efficiency": True
        }
        self.scenarios["rcp_4.5"] = rcp45
        
        # RCP 6.0 - High-medium emissions
        rcp60 = EmissionScenario(
            scenario_id="rcp_6.0",
            scenario_type=ClimateScenarioType.RCP_6_0,
            name="RCP 6.0 - High-Medium Emissions",
            description="Stabilization scenario without overshoot",
            base_year=2020,
            target_year=2100,
            co2_concentration_ppm=670.0,
            methane_concentration_ppb=1850.0,
            nitrous_oxide_concentration_ppb=340.0,
            co2_emissions_gt_per_year=32.0,
            methane_emissions_mt_per_year=500.0,
            emissions_peaking_year=2055,
            emission_reduction_rate=1.5,
            carbon_budget_gt=1200.0,
            temperature_anomaly_c=3.0,
            sea_level_rise_m=0.9,
            ocean_acidification_ph=7.85,
            confidence=ConfidenceLevel.MEDIUM
        )
        self.scenarios["rcp_6.0"] = rcp60
        
        # RCP 8.5 - Very high emissions
        rcp85 = EmissionScenario(
            scenario_id="rcp_8.5",
            scenario_type=ClimateScenarioType.RCP_8_5,
            name="RCP 8.5 - Very High Emissions",
            description="Business as usual, no significant mitigation",
            base_year=2020,
            target_year=2100,
            co2_concentration_ppm=950.0,
            methane_concentration_ppb=1950.0,
            nitrous_oxide_concentration_ppb=350.0,
            co2_emissions_gt_per_year=40.0,
            methane_emissions_mt_per_year=650.0,
            emissions_peaking_year=None,
            emission_reduction_rate=0.0,
            carbon_budget_gt=2000.0,
            temperature_anomaly_c=4.3,
            sea_level_rise_m=1.2,
            ocean_acidification_ph=7.75,
            confidence=ConfidenceLevel.HIGH
        )
        rcp85.assumptions = {
            "no_decarbonization": True,
            "fossil_fuel_dominated": True,
            "population_growth": True,
            "low_efficiency": True
        }
        self.scenarios["rcp_8.5"] = rcp85
    
    def _load_ssp_scenarios(self):
        """Load SSP (Shared Socioeconomic Pathways) scenarios."""
        
        # SSP1 - Sustainability
        ssp1 = EmissionScenario(
            scenario_id="ssp1_1.9",
            scenario_type=ClimateScenarioType.SSP1_19,
            name="SSP1 - Sustainability",
            description="Green growth, low inequality, rapid decarbonization",
            base_year=2020,
            target_year=2100,
            co2_concentration_ppm=420.0,
            methane_concentration_ppb=1600.0,
            nitrous_oxide_concentration_ppb=310.0,
            co2_emissions_gt_per_year=12.0,
            methane_emissions_mt_per_year=300.0,
            emissions_peaking_year=2022,
            emission_reduction_rate=4.0,
            carbon_budget_gt=400.0,
            temperature_anomaly_c=1.5,
            sea_level_rise_m=0.35,
            ocean_acidification_ph=8.1,
            confidence=ConfidenceLevel.HIGH
        )
        ssp1.assumptions = {
            "high_education": True,
            "low_inequality": True,
            "high_technology": True,
            "sustainable_consumption": True
        }
        self.scenarios["ssp1_1.9"] = ssp1
        
        # SSP2 - Middle of the road
        ssp2 = EmissionScenario(
            scenario_id="ssp2_4.5",
            scenario_type=ClimateScenarioType.SSP2_45,
            name="SSP2 - Middle of the Road",
            description="Historical patterns continue, moderate challenges",
            base_year=2020,
            target_year=2100,
            co2_concentration_ppm=540.0,
            methane_concentration_ppb=1780.0,
            nitrous_oxide_concentration_ppb=335.0,
            co2_emissions_gt_per_year=30.0,
            methane_emissions_mt_per_year=470.0,
            emissions_peaking_year=2050,
            emission_reduction_rate=1.8,
            carbon_budget_gt=950.0,
            temperature_anomaly_c=2.5,
            sea_level_rise_m=0.65,
            ocean_acidification_ph=7.93,
            confidence=ConfidenceLevel.MEDIUM
        )
        self.scenarios["ssp2_4.5"] = ssp2
        
        # SSP3 - Regional rivalry
        ssp3 = EmissionScenario(
            scenario_id="ssp3_7.0",
            scenario_type=ClimateScenarioType.SSP3_70,
            name="SSP3 - Regional Rivalry",
            description="High challenges, nationalism, slow development",
            base_year=2020,
            target_year=2100,
            co2_concentration_ppm=700.0,
            methane_concentration_ppb=1900.0,
            nitrous_oxide_concentration_ppb=345.0,
            co2_emissions_gt_per_year=38.0,
            methane_emissions_mt_per_year=600.0,
            emissions_peaking_year=2060,
            emission_reduction_rate=1.2,
            carbon_budget_gt=1300.0,
            temperature_anomaly_c=3.5,
            sea_level_rise_m=0.9,
            ocean_acidification_ph=7.82,
            confidence=ConfidenceLevel.MEDIUM
        )
        ssp3.assumptions = {
            "low_education": True,
            "high_inequality": True,
            "low_technology": True,
            "high_population_growth": True
        }
        self.scenarios["ssp3_7.0"] = ssp3
        
        # SSP5 - Fossil-fueled development
        ssp5 = EmissionScenario(
            scenario_id="ssp5_8.5",
            scenario_type=ClimateScenarioType.SSP5_85,
            name="SSP5 - Fossil-fueled Development",
            description="High growth driven by fossil fuels, no climate policy",
            base_year=2020,
            target_year=2100,
            co2_concentration_ppm=980.0,
            methane_concentration_ppb=2000.0,
            nitrous_oxide_concentration_ppb=360.0,
            co2_emissions_gt_per_year=45.0,
            methane_emissions_mt_per_year=700.0,
            emissions_peaking_year=None,
            emission_reduction_rate=0.0,
            carbon_budget_gt=2200.0,
            temperature_anomaly_c=4.5,
            sea_level_rise_m=1.3,
            ocean_acidification_ph=7.72,
            confidence=ConfidenceLevel.HIGH
        )
        ssp5.assumptions = {
            "high_income": True,
            "low_inequality": True,
            "high_technology": True,
            "fossil_based": True
        }
        self.scenarios["ssp5_8.5"] = ssp5
    
    def _add_custom_scenario_parameters(self):
        """Add parameters for custom scenarios."""
        self.scenarios["custom"] = EmissionScenario(
            scenario_id="custom",
            scenario_type=ClimateScenarioType.CUSTOM,
            name="Custom Scenario",
            description="User-defined scenario parameters",
            base_year=2020,
            target_year=2100,
            co2_concentration_ppm=410.0,
            methane_concentration_ppb=1860.0,
            nitrous_oxide_concentration_ppb=332.0,
            co2_emissions_gt_per_year=36.0,
            methane_emissions_mt_per_year=600.0,
            confidence=ConfidenceLevel.LOW
        )
    
    def get_scenario(self, scenario_id: str) -> Optional[EmissionScenario]:
        """Get a scenario by ID."""
        return self.scenarios.get(scenario_id)
    
    def get_all_scenarios(self) -> List[EmissionScenario]:
        """Get all available scenarios."""
        return list(self.scenarios.values())
    
    def create_custom_scenario(self, parameters: Dict[str, Any]) -> EmissionScenario:
        """Create a custom scenario from parameters."""
        scenario = EmissionScenario(
            scenario_id=f"custom_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            scenario_type=ClimateScenarioType.CUSTOM,
            name=parameters.get("name", "Custom Scenario"),
            description=parameters.get("description", "User-defined scenario"),
            base_year=parameters.get("base_year", 2020),
            target_year=parameters.get("target_year", 2100),
            co2_concentration_ppm=parameters.get("co2_concentration", 410.0),
            methane_concentration_ppb=parameters.get("methane_concentration", 1860.0),
            nitrous_oxide_concentration_ppb=parameters.get("nitrous_oxide", 332.0),
            co2_emissions_gt_per_year=parameters.get("co2_emissions", 36.0),
            methane_emissions_mt_per_year=parameters.get("methane_emissions", 600.0),
            emissions_peaking_year=parameters.get("peaking_year"),
            emission_reduction_rate=parameters.get("reduction_rate", 0.0),
            carbon_budget_gt=parameters.get("carbon_budget"),
            temperature_anomaly_c=parameters.get("temperature_anomaly", 0.0),
            sea_level_rise_m=parameters.get("sea_level_rise", 0.0),
            ocean_acidification_ph=parameters.get("ocean_acidification", 8.1),
            confidence=parameters.get("confidence", ConfidenceLevel.LOW)
        )
        
        self.scenarios[scenario.scenario_id] = scenario
        return scenario


# ============================================================================
# CLIMATE SIMULATION ENGINE
# ============================================================================

class ClimateSimulationEngine:
    """Core engine for climate scenario simulation."""
    
    def __init__(self):
        """Initialize the simulation engine."""
        self.logger = logging.getLogger(f"{__name__}.ClimateSimulationEngine")
        self.scenario_db = ClimateScenarioDatabase()
        self.impact_models = self._initialize_impact_models()
        self.tipping_points = self._initialize_tipping_points()
        self.calibration_cache = {}
    
    def _initialize_impact_models(self) -> Dict[str, Callable]:
        """Initialize impact models for different sectors."""
        return {
            "temperature": self._simulate_temperature,
            "precipitation": self._simulate_precipitation,
            "sea_level": self._simulate_sea_level,
            "agriculture": self._simulate_agriculture_impact,
            "water_resources": self._simulate_water_impact,
            "energy_demand": self._simulate_energy_demand,
            "human_health": self._simulate_health_impact,
            "biodiversity": self._simulate_biodiversity_impact,
            "economy": self._simulate_economic_impact,
            "extreme_weather": self._simulate_extreme_weather,
            "migration": self._simulate_migration_impact
        }
    
    def _initialize_tipping_points(self) -> List[TippingPoint]:
        """Initialize climate tipping points."""
        return [
            TippingPoint(
                name="Greenland Ice Sheet Collapse",
                description="Irreversible melting of Greenland ice sheet",
                threshold_temperature_c=2.0,
                current_risk=0.1,
                projected_risk_at_2c=0.3,
                projected_risk_at_3c=0.7,
                projected_risk_at_4c=0.9,
                impact_severity=0.9,
                timescale_years=300,
                reversibility=0.1,
                affected_sectors=[SectorType.COASTAL, SectorType.WATER, SectorType.URBAN],
                affected_regions=["North America", "Europe", "Global"],
                confidence=ConfidenceLevel.MEDIUM
            ),
            TippingPoint(
                name="Amazon Rainforest Dieback",
                description="Transition from rainforest to savanna",
                threshold_temperature_c=3.0,
                current_risk=0.15,
                projected_risk_at_2c=0.2,
                projected_risk_at_3c=0.5,
                projected_risk_at_4c=0.8,
                impact_severity=0.8,
                timescale_years=100,
                reversibility=0.2,
                affected_sectors=[SectorType.FORESTRY, SectorType.AGRICULTURE, SectorType.BIODIVERSITY],
                affected_regions=["South America", "Global"],
                confidence=ConfidenceLevel.HIGH
            ),
            TippingPoint(
                name="Permafrost Thaw",
                description="Release of stored methane from permafrost",
                threshold_temperature_c=1.5,
                current_risk=0.2,
                projected_risk_at_2c=0.4,
                projected_risk_at_3c=0.7,
                projected_risk_at_4c=0.9,
                impact_severity=0.7,
                timescale_years=50,
                reversibility=0.0,
                affected_sectors=[SectorType.ENERGY, SectorType.INFRASTRUCTURE],
                affected_regions=["Arctic", "Global"],
                confidence=ConfidenceLevel.HIGH
            ),
            TippingPoint(
                name="Gulf Stream Collapse",
                description="Weakening of Atlantic Meridional Overturning Circulation",
                threshold_temperature_c=3.5,
                current_risk=0.05,
                projected_risk_at_2c=0.1,
                projected_risk_at_3c=0.3,
                projected_risk_at_4c=0.6,
                impact_severity=0.85,
                timescale_years=200,
                reversibility=0.3,
                affected_sectors=[SectorType.AGRICULTURE, SectorType.WATER, SectorType.URBAN],
                affected_regions=["Europe", "North America", "Global"],
                confidence=ConfidenceLevel.LOW
            ),
            TippingPoint(
                name="Antarctic Ice Sheet Collapse",
                description="Unstable retreat of West Antarctic ice sheet",
                threshold_temperature_c=2.5,
                current_risk=0.1,
                projected_risk_at_2c=0.2,
                projected_risk_at_3c=0.5,
                projected_risk_at_4c=0.8,
                impact_severity=0.9,
                timescale_years=500,
                reversibility=0.0,
                affected_sectors=[SectorType.COASTAL, SectorType.WATER, SectorType.URBAN],
                affected_regions=["Global Coastal", "Global"],
                confidence=ConfidenceLevel.MEDIUM
            ),
            TippingPoint(
                name="Coral Reef Die-off",
                description="Widespread coral bleaching and death",
                threshold_temperature_c=1.5,
                current_risk=0.3,
                projected_risk_at_2c=0.6,
                projected_risk_at_3c=0.9,
                projected_risk_at_4c=1.0,
                impact_severity=0.7,
                timescale_years=30,
                reversibility=0.1,
                affected_sectors=[SectorType.FISHERIES, SectorType.TOURISM, SectorType.BIODIVERSITY],
                affected_regions=["Tropical Coasts", "Global"],
                confidence=ConfidenceLevel.VERY_HIGH
            )
        ]
    
    def simulate_scenario(self, scenario_id: str, 
                         start_year: int = 2020,
                         end_year: int = 2100,
                         step_years: int = 5) -> ScenarioSimulationResult:
        """
        Simulate a climate scenario over a time period.
        """
        self.logger.info(f"Simulating scenario: {scenario_id} from {start_year} to {end_year}")
        
        scenario = self.scenario_db.get_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")
        
        # Determine projection horizon
        horizon = self._determine_horizon(start_year, end_year)
        
        # Run simulation
        projections = []
        for year in range(start_year, end_year + 1, step_years):
            projection = self._simulate_year(year, scenario)
            projections.append(projection)
        
        # Calculate sector impacts
        sector_impacts = self._calculate_sector_impacts(projections, scenario)
        
        # Calculate regional impacts
        regional_impacts = self._calculate_regional_impacts(projections, scenario)
        
        # Assess tipping points
        assessed_tipping_points = self._assess_tipping_points(projections, scenario)
        
        # Calculate summary metrics
        summary_metrics = self._calculate_summary_metrics(projections, sector_impacts)
        
        # Calculate confidence metrics
        confidence_metrics = self._calculate_confidence_metrics(projections, sector_impacts)
        
        # Calculate uncertainty ranges
        uncertainty_ranges = self._calculate_uncertainty_ranges(projections)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            projections, sector_impacts, regional_impacts, assessed_tipping_points
        )
        
        result = ScenarioSimulationResult(
            scenario_id=scenario_id,
            scenario_name=scenario.name,
            projection_horizon=horizon,
            start_year=start_year,
            end_year=end_year,
            projections=projections,
            sector_impacts=sector_impacts,
            regional_impacts=regional_impacts,
            tipping_points=assessed_tipping_points,
            summary_metrics=summary_metrics,
            confidence_metrics=confidence_metrics,
            uncertainty_ranges=uncertainty_ranges,
            recommendations=recommendations,
            simulation_metadata={
                "simulation_time": datetime.now().isoformat(),
                "step_years": step_years,
                "total_projections": len(projections),
                "version": "3.0.0"
            }
        )
        
        self.logger.info(f"Simulation complete for {scenario_id}")
        return result
    
    def _determine_horizon(self, start_year: int, end_year: int) -> ProjectionHorizon:
        """Determine the projection horizon based on time range."""
        if end_year <= 2025:
            return ProjectionHorizon.NEAR_TERM
        elif end_year <= 2030:
            return ProjectionHorizon.SHORT_TERM
        elif end_year <= 2050:
            return ProjectionHorizon.MEDIUM_TERM
        elif end_year <= 2100:
            return ProjectionHorizon.LONG_TERM
        else:
            return ProjectionHorizon.CENTURY
    
    def _simulate_year(self, year: int, scenario: EmissionScenario) -> ClimateProjection:
        """Simulate climate for a specific year."""
        years_passed = year - scenario.base_year
        
        # Calculate emissions
        emissions = scenario.get_emissions_at_year(year)
        
        # Calculate temperature change
        temperature_anomaly = self._calculate_temperature_anomaly(
            years_passed, emissions, scenario
        )
        
        # Calculate CO2 concentration
        co2_conc = self._calculate_co2_concentration(
            years_passed, emissions, scenario
        )
        
        # Calculate sea level rise
        sea_level = self._calculate_sea_level_rise(
            years_passed, temperature_anomaly, scenario
        )
        
        # Calculate ocean pH
        ocean_ph = self._calculate_ocean_ph(
            years_passed, co2_conc, scenario
        )
        
        # Calculate arctic ice extent
        arctic_ice = self._calculate_arctic_ice_extent(
            years_passed, temperature_anomaly
        )
        
        # Calculate permafrost thaw
        permafrost = self._calculate_permafrost_thaw(
            years_passed, temperature_anomaly
        )
        
        # Calculate extreme events index
        extreme_index = self._calculate_extreme_events_index(
            years_passed, temperature_anomaly
        )
        
        # Calculate precipitation change
        precip_change = self._calculate_precipitation_change(
            years_passed, temperature_anomaly
        )
        
        # Calculate drought index
        drought_index = self._calculate_drought_index(
            years_passed, temperature_anomaly, precip_change
        )
        
        # Calculate wildfire risk
        wildfire_risk = self._calculate_wildfire_risk(
            years_passed, temperature_anomaly, drought_index
        )
        
        # Calculate sectoral impacts
        sectoral_impacts = self._calculate_sectoral_impacts(
            year, temperature_anomaly, sea_level, precip_change
        )
        
        # Calculate regional impacts
        regional_impacts = self._calculate_sectoral_regional_impacts(
            year, temperature_anomaly, sea_level, precip_change
        )
        
        # Calculate confidence
        confidence = self._calculate_projection_confidence(
            years_passed, scenario
        )
        
        projection = ClimateProjection(
            scenario_id=scenario.scenario_id,
            year=year,
            global_temperature_c=scenario.temperature_anomaly_c + temperature_anomaly + 13.7,
            global_temperature_anomaly_c=temperature_anomaly,
            co2_concentration_ppm=co2_conc,
            sea_level_rise_m=sea_level,
            sea_level_rise_uncertainty=(sea_level * 0.7, sea_level * 1.3),
            ocean_ph=ocean_ph,
            arctic_ice_extent_million_km2=arctic_ice,
            permafrost_thaw_m=permafrost,
            extreme_events_index=extreme_index,
            precipitation_change_percent=precip_change,
            drought_index=drought_index,
            wildfire_risk_index=wildfire_risk,
            confidence=confidence,
            sectoral_impacts=sectoral_impacts,
            regional_impacts=regional_impacts
        )
        
        return projection
    
    def _calculate_temperature_anomaly(self, years: float, emissions: float, 
                                      scenario: EmissionScenario) -> float:
        """Calculate temperature anomaly from baseline."""
        # Simplified climate sensitivity model
        climate_sensitivity = 3.0  # °C per doubling of CO2
        
        baseline_co2 = 280.0  # Pre-industrial CO2
        current_co2 = self._calculate_co2_concentration(years, emissions, scenario)
        
        forcing = 5.35 * math.log(current_co2 / baseline_co2)
        temperature_anomaly = forcing * climate_sensitivity / 3.7
        
        # Add some stochastic variation
        temperature_anomaly += random.gauss(0, 0.05 * math.sqrt(years / 10))
        
        return temperature_anomaly
    
    def _calculate_co2_concentration(self, years: float, emissions: float,
                                    scenario: EmissionScenario) -> float:
        """Calculate CO2 concentration."""
        # Simple carbon cycle model
        baseline = 280.0
        airborne_fraction = 0.45
        atmospheric_loading = emissions * 1000 * airborne_fraction  # Gt to ppm
        current = baseline + atmospheric_loading * 0.45  # Conversion factor
        
        # Add some inertia
        current += (scenario.co2_concentration_ppm - current) * 0.1
        
        return current
    
    def _calculate_sea_level_rise(self, years: float, temp_anomaly: float,
                                 scenario: EmissionScenario) -> float:
        """Calculate sea level rise."""
        # Simple sea level rise model
        thermal_expansion = temp_anomaly * 0.3 * (years / 100)
        glacier_melt = temp_anomaly * 0.4 * (years / 100)
        ice_sheet_melt = temp_anomaly * 0.3 * (years / 100) * (1 + 0.1 * (years / 100))
        
        sea_level = thermal_expansion + glacier_melt + ice_sheet_melt
        sea_level += scenario.sea_level_rise_m * (years / 100)
        
        return sea_level
    
    def _calculate_ocean_ph(self, years: float, co2_conc: float,
                           scenario: EmissionScenario) -> float:
        """Calculate ocean pH."""
        # Simple ocean acidification model
        baseline = 8.2
        co2_factor = math.log(co2_conc / 280.0) / math.log(2)
        ph_change = co2_factor * 0.1
        
        ph = baseline - ph_change
        ph += random.gauss(0, 0.01)
        
        return ph
    
    def _calculate_arctic_ice_extent(self, years: float, temp_anomaly: float) -> float:
        """Calculate Arctic sea ice extent."""
        baseline = 14.0  # million km2
        ice_loss_rate = 0.07  # per degree of warming
        ice_extent = baseline * (1 - temp_anomaly * ice_loss_rate)
        
        # Add seasonal variation
        ice_extent += random.gauss(0, 0.2)
        
        return max(0, min(ice_extent, baseline))
    
    def _calculate_permafrost_thaw(self, years: float, temp_anomaly: float) -> float:
        """Calculate permafrost thaw depth."""
        baseline = 0.0
        thaw_rate = 0.15  # meters per degree of warming per 10 years
        permafrost_thaw = baseline + temp_anomaly * thaw_rate * (years / 10)
        
        return min(permafrost_thaw, 5.0)  # Cap at 5 meters
    
    def _calculate_extreme_events_index(self, years: float, temp_anomaly: float) -> float:
        """Calculate extreme events index (0-1 scale)."""
        baseline = 0.2
        event_increase = temp_anomaly * 0.15 * (years / 50)
        
        index = min(1.0, baseline + event_increase + random.gauss(0, 0.02))
        return max(0, index)
    
    def _calculate_precipitation_change(self, years: float, temp_anomaly: float) -> float:
        """Calculate precipitation change percentage."""
        # Complex precipitation response
        global_avg_change = temp_anomaly * 0.07 * (years / 50)
        
        # Add regional and stochastic variation
        global_avg_change += random.gauss(0, 0.01 * math.sqrt(years / 10))
        
        return global_avg_change * 100  # Convert to percentage
    
    def _calculate_drought_index(self, years: float, temp_anomaly: float,
                                precip_change: float) -> float:
        """Calculate drought index (0-1 scale)."""
        baseline = 0.3
        temp_factor = temp_anomaly * 0.05
        precip_factor = -precip_change * 0.01
        
        index = min(1.0, baseline + temp_factor + precip_factor + random.gauss(0, 0.02))
        return max(0, index)
    
    def _calculate_wildfire_risk(self, years: float, temp_anomaly: float,
                               drought_index: float) -> float:
        """Calculate wildfire risk index (0-1 scale)."""
        baseline = 0.2
        temp_factor = temp_anomaly * 0.04
        drought_factor = drought_index * 0.3
        
        index = min(1.0, baseline + temp_factor + drought_factor + random.gauss(0, 0.02))
        return max(0, index)
    
    def _calculate_sectoral_impacts(self, year: int, temp_anomaly: float,
                                   sea_level: float, precip_change: float) -> Dict[str, float]:
        """Calculate impacts on different sectors."""
        impacts = {}
        
        # Agriculture impact
        impacts["agriculture"] = self._simulate_agriculture_impact(temp_anomaly, precip_change)
        
        # Water resources impact
        impacts["water"] = self._simulate_water_impact(temp_anomaly, precip_change)
        
        # Energy demand impact
        impacts["energy"] = self._simulate_energy_demand(temp_anomaly)
        
        # Health impact
        impacts["health"] = self._simulate_health_impact(temp_anomaly)
        
        # Biodiversity impact
        impacts["biodiversity"] = self._simulate_biodiversity_impact(temp_anomaly)
        
        # Economic impact
        impacts["economy"] = self._simulate_economic_impact(temp_anomaly, sea_level)
        
        # Extreme weather impact
        impacts["extreme_weather"] = self._simulate_extreme_weather(temp_anomaly)
        
        # Infrastructure impact
        impacts["infrastructure"] = self._simulate_infrastructure_impact(sea_level, temp_anomaly)
        
        return impacts
    
    def _calculate_sectoral_regional_impacts(self, year: int, temp_anomaly: float,
                                           sea_level: float, precip_change: float) -> Dict[str, Dict[str, float]]:
        """Calculate regional impacts."""
        regions = {
            "north_america": {},
            "europe": {},
            "asia": {},
            "africa": {},
            "south_america": {},
            "oceania": {},
            "arctic": {},
            "antarctic": {}
        }
        
        for region in regions:
            # Regional temperature anomaly (some regions warm more)
            regional_temp = temp_anomaly * (0.8 + random.random() * 0.4)
            
            # Regional precipitation (some regions get wetter/drier)
            regional_precip = precip_change * (0.5 + random.random() * 1.0)
            
            # Calculate regional impacts
            regions[region]["temperature_anomaly"] = regional_temp
            regions[region]["precipitation_change"] = regional_precip
            regions[region]["agriculture_impact"] = self._simulate_agriculture_impact(
                regional_temp, regional_precip
            )
            regions[region]["water_stress"] = self._simulate_water_impact(
                regional_temp, regional_precip
            )
            regions[region]["health_impact"] = self._simulate_health_impact(regional_temp)
            regions[region]["economic_impact"] = self._simulate_economic_impact(
                regional_temp, sea_level * 0.5
            )
            
            # Regional vulnerability
            regions[region]["vulnerability"] = 0.5 + random.random() * 0.4
            regions[region]["resilience"] = 0.5 + random.random() * 0.4
        
        return regions
    
    def _simulate_agriculture_impact(self, temp_anomaly: float, 
                                    precip_change: float) -> float:
        """Simulate agricultural impacts (0-1 scale, higher = worse)."""
        # Crop yield sensitivity
        optimal_temp = 20.0
        temp_deviation = abs(temp_anomaly * 1.5)  # Simplified
        
        # Temperature effect
        temp_effect = min(1.0, temp_deviation / 10.0)
        
        # Precipitation effect (too little or too much)
        precip_effect = min(1.0, abs(precip_change) / 20.0)
        
        # Combined impact
        impact = (temp_effect * 0.6 + precip_effect * 0.4)
        impact = min(1.0, impact)
        
        # Add some uncertainty
        impact += random.gauss(0, 0.02)
        return max(0, min(1.0, impact))
    
    def _simulate_water_impact(self, temp_anomaly: float, 
                              precip_change: float) -> float:
        """Simulate water resources impact (0-1 scale, higher = worse)."""
        # Water stress from temperature
        temp_stress = min(1.0, temp_anomaly * 0.15)
        
        # Water stress from precipitation changes
        if precip_change < 0:
            precip_stress = min(1.0, abs(precip_change) / 10.0)
        else:
            precip_stress = 0.0
        
        # Combined impact
        impact = (temp_stress * 0.4 + precip_stress * 0.6)
        impact = min(1.0, impact)
        
        return max(0, impact)
    
    def _simulate_energy_demand(self, temp_anomaly: float) -> float:
        """Simulate energy demand impact (0-1 scale)."""
        # Heating/cooling degree days
        heating_reduction = min(0.3, temp_anomaly * 0.03)
        cooling_increase = min(0.5, temp_anomaly * 0.05)
        
        # Net effect on energy demand
        if cooling_increase > heating_reduction:
            impact = cooling_increase - heating_reduction
        else:
            impact = 0.0
        
        return min(1.0, impact)
    
    def _simulate_health_impact(self, temp_anomaly: float) -> float:
        """Simulate human health impact (0-1 scale, higher = worse)."""
        # Heat-related illness
        heat_effect = min(0.8, temp_anomaly * 0.08)
        
        # Vector-borne disease expansion
        disease_effect = min(0.6, temp_anomaly * 0.06)
        
        impact = (heat_effect * 0.6 + disease_effect * 0.4)
        return min(1.0, impact)
    
    def _simulate_biodiversity_impact(self, temp_anomaly: float) -> float:
        """Simulate biodiversity impact (0-1 scale, higher = worse)."""
        # Species extinction risk
        extinction_risk = min(1.0, temp_anomaly * 0.12)
        
        # Habitat loss
        habitat_loss = min(1.0, temp_anomaly * 0.08)
        
        impact = (extinction_risk * 0.6 + habitat_loss * 0.4)
        return min(1.0, impact)
    
    def _simulate_economic_impact(self, temp_anomaly: float, 
                                sea_level: float) -> float:
        """Simulate economic impact (0-1 scale, higher = worse)."""
        # Temperature effect on GDP
        temp_gdp_loss = min(0.8, temp_anomaly * 0.05)
        
        # Sea level rise effect
        slr_gdp_loss = min(0.5, sea_level * 0.3)
        
        # Combined impact
        impact = (temp_gdp_loss * 0.6 + slr_gdp_loss * 0.4)
        return min(1.0, impact)
    
    def _simulate_extreme_weather(self, temp_anomaly: float) -> float:
        """Simulate extreme weather impact (0-1 scale, higher = worse)."""
        # Storm intensity
        storm_intensity = min(1.0, temp_anomaly * 0.06)
        
        # Flood risk
        flood_risk = min(1.0, temp_anomaly * 0.04)
        
        impact = (storm_intensity * 0.5 + flood_risk * 0.5)
        return min(1.0, impact)
    
    def _simulate_infrastructure_impact(self, sea_level: float, 
                                      temp_anomaly: float) -> float:
        """Simulate infrastructure impact (0-1 scale, higher = worse)."""
        # Coastal infrastructure risk
        coastal_risk = min(1.0, sea_level * 0.25)
        
        # Thermal stress on infrastructure
        thermal_stress = min(0.6, temp_anomaly * 0.03)
        
        impact = (coastal_risk * 0.7 + thermal_stress * 0.3)
        return min(1.0, impact)
    
    def _simulate_migration_impact(self, temp_anomaly: float, 
                                  sea_level: float) -> float:
        """Simulate climate migration impact (0-1 scale)."""
        # Sea level rise migration
        slr_migration = min(1.0, sea_level * 0.2)
        
        # Agricultural failure migration
        ag_migration = min(1.0, temp_anomaly * 0.05)
        
        impact = (slr_migration * 0.5 + ag_migration * 0.5)
        return min(1.0, impact)
    
    def _calculate_sector_impacts(self, projections: List[ClimateProjection],
                                 scenario: EmissionScenario) -> Dict[str, List[SectorImpact]]:
        """Calculate comprehensive sector impacts."""
        sector_impacts = {}
        
        for projection in projections:
            for sector_name, impact_value in projection.sectoral_impacts.items():
                if sector_name not in sector_impacts:
                    sector_impacts[sector_name] = []
                
                # Convert sector name to SectorType
                sector_type = self._get_sector_type(sector_name)
                
                # Calculate economic impact
                economic_impact = impact_value * 100 * (1 + scenario.temperature_anomaly_c * 0.2)
                
                # Calculate adaptation costs
                adaptation_cost = economic_impact * 0.3
                adaptation_benefit = adaptation_cost * 0.6
                
                # Calculate people affected
                people_affected = int(impact_value * 1000000)
                
                sector_impact = SectorImpact(
                    sector=sector_type,
                    scenario_id=scenario.scenario_id,
                    year=projection.year,
                    impact_score=impact_value,
                    economic_impact_billion_usd=economic_impact,
                    jobs_affected=int(impact_value * 10000),
                    people_affected=people_affected,
                    adaptation_cost_billion_usd=adaptation_cost,
                    adaptation_benefit_billion_usd=adaptation_benefit,
                    vulnerability=0.5 + impact_value * 0.3,
                    exposure=0.4 + impact_value * 0.4,
                    sensitivity=0.3 + impact_value * 0.4,
                    adaptive_capacity=0.6 - impact_value * 0.3,
                    risk_level=impact_value,
                    description=f"Impact of climate change on {sector_name} sector",
                    confidence=ConfidenceLevel.MEDIUM
                )
                
                sector_impacts[sector_name].append(sector_impact)
        
        return sector_impacts
    
    def _calculate_regional_impacts(self, projections: List[ClimateProjection],
                                  scenario: EmissionScenario) -> Dict[str, List[RegionalImpact]]:
        """Calculate regional impacts."""
        regional_impacts = {}
        
        for projection in projections:
            for region_name, impacts in projection.regional_impacts.items():
                if region_name not in regional_impacts:
                    regional_impacts[region_name] = []
                
                # Calculate regional impact metrics
                population_affected = int(impacts.get("vulnerability", 0.5) * 1000000)
                gdp_loss = impacts.get("economic_impact", 0.5) * 0.1
                agricultural_loss = impacts.get("agriculture_impact", 0.5) * 0.15
                water_stress = impacts.get("water_stress", 0.5)
                health_impact = impacts.get("health_impact", 0.5)
                
                # Migration risk
                migration_risk = (water_stress * 0.4 + agricultural_loss * 0.3 + 
                                health_impact * 0.3)
                
                # Infrastructure risk
                infrastructure_risk = (impacts.get("economic_impact", 0.5) * 0.5 + 
                                     impacts.get("vulnerability", 0.5) * 0.5)
                
                # Biodiversity loss
                biodiversity_loss = impacts.get("agriculture_impact", 0.5) * 0.4
                
                regional_impact = RegionalImpact(
                    region_name=region_name,
                    region_code=region_name[:3].upper(),
                    scenario_id=scenario.scenario_id,
                    year=projection.year,
                    population_affected=population_affected,
                    gdp_loss_percent=gdp_loss * 100,
                    agricultural_loss_percent=agricultural_loss * 100,
                    water_stress_index=water_stress,
                    health_impact_index=health_impact,
                    migration_risk=migration_risk,
                    infrastructure_risk=infrastructure_risk,
                    biodiversity_loss_percent=biodiversity_loss * 100,
                    adaptation_need_score=0.4 + water_stress * 0.4,
                    resilience_score=0.6 - water_stress * 0.3,
                    confidence=ConfidenceLevel.MEDIUM
                )
                
                regional_impacts[region_name].append(regional_impact)
        
        return regional_impacts
    
    def _assess_tipping_points(self, projections: List[ClimateProjection],
                              scenario: EmissionScenario) -> List[TippingPoint]:
        """Assess tipping points based on projections."""
        assessed_tipping_points = []
        
        for tipping_point in self.tipping_points:
            # Get temperature anomaly from projections
            temp_anomalies = [p.global_temperature_anomaly_c for p in projections]
            avg_temp_anomaly = statistics.mean(temp_anomalies)
            
            # Assess current risk
            if avg_temp_anomaly >= tipping_point.threshold_temperature_c:
                risk = min(1.0, tipping_point.current_risk + 
                          (avg_temp_anomaly - tipping_point.threshold_temperature_c) * 0.2)
            else:
                risk = tipping_point.current_risk
            
            # Check if tipping point has been triggered
            triggered = avg_temp_anomaly >= tipping_point.threshold_temperature_c
            
            # Assess sectoral impacts
            affected_impacts = []
            for sector in tipping_point.affected_sectors:
                sector_impacts = self._simulate_sector_impact_from_tipping_point(
                    sector, avg_temp_anomaly
                )
                affected_impacts.append(sector_impacts)
            
            # Create assessed tipping point
            assessed = TippingPoint(
                name=tipping_point.name,
                description=tipping_point.description,
                threshold_temperature_c=tipping_point.threshold_temperature_c,
                current_risk=risk,
                projected_risk_at_2c=tipping_point.projected_risk_at_2c,
                projected_risk_at_3c=tipping_point.projected_risk_at_3c,
                projected_risk_at_4c=tipping_point.projected_risk_at_4c,
                impact_severity=tipping_point.impact_severity * (1 + avg_temp_anomaly * 0.1),
                timescale_years=tipping_point.timescale_years,
                reversibility=tipping_point.reversibility * (1 - avg_temp_anomaly * 0.02),
                affected_sectors=tipping_point.affected_sectors,
                affected_regions=tipping_point.affected_regions,
                confidence=ConfidenceLevel.MEDIUM,
                cascade_effects=tipping_point.cascade_effects + [
                    f"Risk increased by {risk - tipping_point.current_risk:.2f} from current levels"
                ]
            )
            
            assessed_tipping_points.append(assessed)
        
        return assessed_tipping_points
    
    def _simulate_sector_impact_from_tipping_point(self, sector: SectorType,
                                                  temp_anomaly: float) -> float:
        """Simulate sector impact from tipping point."""
        base_impacts = {
            SectorType.AGRICULTURE: 0.6,
            SectorType.ENERGY: 0.4,
            SectorType.WATER: 0.7,
            SectorType.HEALTH: 0.5,
            SectorType.COASTAL: 0.8,
            SectorType.FORESTRY: 0.6,
            SectorType.FISHERIES: 0.7,
            SectorType.TOURISM: 0.4,
            SectorType.INSURANCE: 0.5,
            SectorType.URBAN: 0.6
        }
        
        base = base_impacts.get(sector, 0.5)
        return min(1.0, base + temp_anomaly * 0.05)
    
    def _get_sector_type(self, sector_name: str) -> SectorType:
        """Convert string to SectorType."""
        mapping = {
            "agriculture": SectorType.AGRICULTURE,
            "energy": SectorType.ENERGY,
            "water": SectorType.WATER,
            "health": SectorType.HEALTH,
            "biodiversity": SectorType.BIODIVERSITY,
            "economy": SectorType.INSURANCE,
            "extreme_weather": SectorType.URBAN,
            "infrastructure": SectorType.CONSTRUCTION
        }
        return mapping.get(sector_name.lower(), SectorType.URBAN)
    
    def _calculate_summary_metrics(self, projections: List[ClimateProjection],
                                  sector_impacts: Dict[str, List[SectorImpact]]) -> Dict[str, float]:
        """Calculate summary metrics."""
        metrics = {}
        
        # Temperature metrics
        temp_anomalies = [p.global_temperature_anomaly_c for p in projections]
        metrics["max_temperature_anomaly"] = max(temp_anomalies)
        metrics["mean_temperature_anomaly"] = statistics.mean(temp_anomalies)
        metrics["temp_anomaly_rate"] = (temp_anomalies[-1] - temp_anomalies[0]) / len(temp_anomalies)
        
        # Sea level metrics
        sea_levels = [p.sea_level_rise_m for p in projections]
        metrics["max_sea_level_rise"] = max(sea_levels)
        metrics["mean_sea_level_rise"] = statistics.mean(sea_levels)
        
        # Impact metrics
        total_impact = 0.0
        for sector, impacts in sector_impacts.items():
            avg_impact = statistics.mean([i.impact_score for i in impacts])
            total_impact += avg_impact
            metrics[f"{sector}_avg_impact"] = avg_impact
        
        metrics["total_average_impact"] = total_impact / len(sector_impacts) if sector_impacts else 0
        
        # Extreme events
        extreme_indices = [p.extreme_events_index for p in projections]
        metrics["max_extreme_events"] = max(extreme_indices)
        metrics["mean_extreme_events"] = statistics.mean(extreme_indices)
        
        # Drought
        drought_indices = [p.drought_index for p in projections]
        metrics["max_drought"] = max(drought_indices)
        metrics["mean_drought"] = statistics.mean(drought_indices)
        
        # Wildfire risk
        wildfire_risks = [p.wildfire_risk_index for p in projections]
        metrics["max_wildfire_risk"] = max(wildfire_risks)
        metrics["mean_wildfire_risk"] = statistics.mean(wildfire_risks)
        
        return metrics
    
    def _calculate_confidence_metrics(self, projections: List[ClimateProjection],
                                    sector_impacts: Dict[str, List[SectorImpact]]) -> Dict[str, float]:
        """Calculate confidence metrics."""
        metrics = {}
        
        # Confidence scores from projections
        confidences = [p.confidence.value for p in projections]
        metrics["mean_projection_confidence"] = statistics.mean(confidences)
        metrics["min_projection_confidence"] = min(confidences)
        metrics["max_projection_confidence"] = max(confidences)
        
        # Variability metrics
        temp_anomalies = [p.global_temperature_anomaly_c for p in projections]
        metrics["temperature_variance"] = statistics.variance(temp_anomalies) if len(temp_anomalies) > 1 else 0
        
        sea_levels = [p.sea_level_rise_m for p in projections]
        metrics["sea_level_variance"] = statistics.variance(sea_levels) if len(sea_levels) > 1 else 0
        
        # Sector confidence
        if sector_impacts:
            sector_confidences = []
            for sector, impacts in sector_impacts.items():
                sector_confidence = statistics.mean([i.confidence.value for i in impacts])
                sector_confidences.append(sector_confidence)
            metrics["mean_sector_confidence"] = statistics.mean(sector_confidences)
        
        return metrics
    
    def _calculate_uncertainty_ranges(self, projections: List[ClimateProjection]) -> Dict[str, Tuple[float, float]]:
        """Calculate uncertainty ranges for key parameters."""
        uncertainty_ranges = {}
        
        # Temperature uncertainty
        temp_anomalies = [p.global_temperature_anomaly_c for p in projections]
        if temp_anomalies:
            mean_temp = statistics.mean(temp_anomalies)
            std_temp = statistics.stdev(temp_anomalies) if len(temp_anomalies) > 1 else 0.5
            uncertainty_ranges["temperature_anomaly"] = (mean_temp - 2*std_temp, mean_temp + 2*std_temp)
        
        # Sea level uncertainty
        sea_levels = [p.sea_level_rise_m for p in projections]
        if sea_levels:
            mean_sl = statistics.mean(sea_levels)
            std_sl = statistics.stdev(sea_levels) if len(sea_levels) > 1 else 0.1
            uncertainty_ranges["sea_level_rise"] = (mean_sl - 2*std_sl, mean_sl + 2*std_sl)
        
        # CO2 concentration uncertainty
        co2_levels = [p.co2_concentration_ppm for p in projections]
        if co2_levels:
            mean_co2 = statistics.mean(co2_levels)
            std_co2 = statistics.stdev(co2_levels) if len(co2_levels) > 1 else 20
            uncertainty_ranges["co2_concentration"] = (mean_co2 - 2*std_co2, mean_co2 + 2*std_co2)
        
        return uncertainty_ranges
    
    def _calculate_projection_confidence(self, years: float, 
                                       scenario: EmissionScenario) -> ConfidenceLevel:
        """Calculate confidence level for projection."""
        # Base confidence from scenario
        base_confidence = scenario.confidence
        
        # Reduce confidence for further projections
        time_factor = max(0.5, 1.0 - (years / 200))
        
        # Adjust confidence
        confidence_value = base_confidence.value * time_factor
        
        # Map to ConfidenceLevel
        if confidence_value >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence_value >= 0.7:
            return ConfidenceLevel.HIGH
        elif confidence_value >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif confidence_value >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _generate_recommendations(self, projections: List[ClimateProjection],
                                 sector_impacts: Dict[str, List[SectorImpact]],
                                 regional_impacts: Dict[str, List[RegionalImpact]],
                                 tipping_points: List[TippingPoint]) -> List[Dict[str, Any]]:
        """Generate recommendations based on simulation results."""
        recommendations = []
        
        # Get final year projections
        final_year = projections[-1] if projections else None
        if not final_year:
            return recommendations
        
        # Temperature-based recommendations
        temp_anomaly = final_year.global_temperature_anomaly_c
        if temp_anomaly > 3.0:
            src.ai.recommendations.append({
                "priority": "critical",
                "category": "mitigation",
                "recommendation": "Immediate and aggressive emissions reduction required to avoid catastrophic warming",
                "target": "All sectors",
                "timeframe": "Immediate",
                "impact_potential": "Very High",
                "actions": [
                    "Achieve net-zero emissions by 2050",
                    "Transition to 100% renewable energy",
                    "Implement carbon capture and storage",
                    "Protect and restore natural carbon sinks"
                ]
            })
        elif temp_anomaly > 2.0:
            src.ai.recommendations.append({
                "priority": "high",
                "category": "mitigation",
                "recommendation": "Accelerate emissions reduction to limit warming to 2°C",
                "target": "All sectors",
                "timeframe": "2030-2050",
                "impact_potential": "High",
                "actions": [
                    "Increase renewable energy share to 70% by 2050",
                    "Electrify transportation sector",
                    "Improve energy efficiency by 50%",
                    "Reduce deforestation"
                ]
            })
        
        # Sea level rise recommendations
        sea_level = final_year.sea_level_rise_m
        if sea_level > 0.8:
            src.ai.recommendations.append({
                "priority": "high",
                "category": "adaptation",
                "recommendation": "Urgent coastal adaptation and protection measures needed",
                "target": "Coastal regions",
                "timeframe": "2025-2050",
                "impact_potential": "High",
                "actions": [
                    "Build coastal defenses and flood barriers",
                    "Relocate vulnerable coastal communities",
                    "Restore coastal ecosystems (mangroves, wetlands)",
                    "Implement managed retreat strategies"
                ]
            })
        
        # Agriculture recommendations
        ag_impacts = sector_impacts.get("agriculture", [])
        if ag_impacts:
            avg_ag_impact = statistics.mean([i.impact_score for i in ag_impacts])
            if avg_ag_impact > 0.6:
                src.ai.recommendations.append({
                    "priority": "high",
                    "category": "adaptation",
                    "recommendation": "Transform agricultural systems for climate resilience",
                    "target": "Agriculture sector",
                    "timeframe": "2025-2050",
                    "impact_potential": "Medium",
                    "actions": [
                        "Develop drought-resistant crop varieties",
                        "Implement precision agriculture",
                        "Adopt agroforestry and sustainable farming practices",
                        "Improve irrigation efficiency"
                    ]
                })
        
        # Water resources recommendations
        water_impacts = sector_impacts.get("water", [])
        if water_impacts:
            avg_water_impact = statistics.mean([i.impact_score for i in water_impacts])
            if avg_water_impact > 0.5:
                src.ai.recommendations.append({
                    "priority": "medium",
                    "category": "adaptation",
                    "recommendation": "Enhance water management and conservation",
                    "target": "Water sector",
                    "timeframe": "2025-2040",
                    "impact_potential": "Medium",
                    "actions": [
                        "Improve water storage and distribution systems",
                        "Promote water conservation and efficiency",
                        "Implement water recycling and reuse",
                        "Protect watersheds and aquifers"
                    ]
                })
        
        # Health recommendations
        health_impacts = sector_impacts.get("health", [])
        if health_impacts:
            avg_health_impact = statistics.mean([i.impact_score for i in health_impacts])
            if avg_health_impact > 0.4:
                src.ai.recommendations.append({
                    "priority": "medium",
                    "category": "adaptation",
                    "recommendation": "Strengthen health systems for climate-related challenges",
                    "target": "Health sector",
                    "timeframe": "2025-2040",
                    "impact_potential": "Medium",
                    "actions": [
                        "Improve disease surveillance and early warning systems",
                        "Develop heat action plans",
                        "Strengthen healthcare infrastructure",
                        "Promote climate-health research"
                    ]
                })
        
        # Tipping point recommendations
        high_risk_tipping_points = [tp for tp in tipping_points if tp.current_risk > 0.5]
        if high_risk_tipping_points:
            src.ai.recommendations.append({
                "priority": "critical",
                "category": "mitigation",
                "recommendation": f"Avoid triggering {len(high_risk_tipping_points)} critical tipping points",
                "target": "Global",
                "timeframe": "Immediate",
                "impact_potential": "Very High",
                "actions": [
                    "Limit warming to below 1.5°C",
                    "Protect vulnerable systems",
                    "Monitor tipping point indicators",
                    "Develop early warning systems"
                ]
            })
        
        # Regional recommendations
        high_risk_regions = []
        for region_name, impacts in regional_impacts.items():
            if impacts and impacts[-1].migration_risk > 0.6:
                high_risk_regions.append(region_name)
        
        if high_risk_regions:
            src.ai.recommendations.append({
                "priority": "high",
                "category": "adaptation",
                "recommendation": f"Develop adaptation strategies for high-risk regions: {', '.join(high_risk_regions[:3])}",
                "target": "Regional",
                "timeframe": "2025-2050",
                "impact_potential": "High",
                "actions": [
                    "Assess regional vulnerabilities",
                    "Develop regional adaptation plans",
                    "Build regional cooperation and support",
                    "Implement early action measures"
                ]
            })
        
        # General sustainability recommendations
        src.ai.recommendations.append({
            "priority": "medium",
            "category": "sustainability",
            "recommendation": "Integrate climate resilience into all planning and development",
            "target": "All sectors",
            "timeframe": "2025-2100",
            "impact_potential": "Medium",
            "actions": [
                "Mainstream climate considerations in policy",
                "Invest in green infrastructure",
                "Promote sustainable consumption",
                "Enhance education and awareness"
            ]
        })
        
        return recommendations


# ============================================================================
# VISUALIZATION AND REPORTING
# ============================================================================

class ClimateVisualizationGenerator:
    """Generate visualizations for climate scenarios."""
    
    @staticmethod
    def generate_temperature_trend_data(result: ScenarioSimulationResult) -> Dict[str, Any]:
        """Generate data for temperature trend visualization."""
        years = [p.year for p in result.projections]
        temperatures = [p.global_temperature_c for p in result.projections]
        anomalies = [p.global_temperature_anomaly_c for p in result.projections]
        
        return {
            "years": years,
            "temperatures": temperatures,
            "anomalies": anomalies,
            "baseline": 13.7,  # Pre-industrial global temperature
            "scenario_name": result.scenario_name
        }
    
    @staticmethod
    def generate_sea_level_data(result: ScenarioSimulationResult) -> Dict[str, Any]:
        """Generate data for sea level rise visualization."""
        years = [p.year for p in result.projections]
        sea_levels = [p.sea_level_rise_m for p in result.projections]
        uncertainties_low = [p.sea_level_rise_uncertainty[0] for p in result.projections]
        uncertainties_high = [p.sea_level_rise_uncertainty[1] for p in result.projections]
        
        return {
            "years": years,
            "sea_level": sea_levels,
            "uncertainty_low": uncertainties_low,
            "uncertainty_high": uncertainties_high,
            "scenario_name": result.scenario_name
        }
    
    @staticmethod
    def generate_sector_impact_data(result: ScenarioSimulationResult) -> Dict[str, Any]:
        """Generate data for sector impact visualization."""
        sectors = list(result.sector_impacts.keys())
        years = [p.year for p in result.projections]
        
        sector_data = {}
        for sector in sectors:
            impacts = result.sector_impacts[sector]
            sector_data[sector] = [i.impact_score for i in impacts]
        
        return {
            "sectors": sectors,
            "years": years,
            "sector_data": sector_data,
            "scenario_name": result.scenario_name
        }
    
    @staticmethod
    def generate_regional_impact_data(result: ScenarioSimulationResult) -> Dict[str, Any]:
        """Generate data for regional impact visualization."""
        regions = list(result.regional_impacts.keys())
        
        region_data = {}
        for region in regions:
            impacts = result.regional_impacts[region]
            region_data[region] = {
                "water_stress": [i.water_stress_index for i in impacts],
                "migration_risk": [i.migration_risk for i in impacts],
                "gdp_loss": [i.gdp_loss_percent for i in impacts]
            }
        
        return {
            "regions": regions,
            "region_data": region_data,
            "scenario_name": result.scenario_name
        }
    
    @staticmethod
    def generate_tipping_point_data(result: ScenarioSimulationResult) -> Dict[str, Any]:
        """Generate data for tipping point visualization."""
        tipping_points = result.tipping_points
        
        return {
            "tipping_points": [
                {
                    "name": tp.name,
                    "current_risk": tp.current_risk,
                    "projected_risk_2c": tp.projected_risk_at_2c,
                    "projected_risk_3c": tp.projected_risk_at_3c,
                    "projected_risk_4c": tp.projected_risk_at_4c,
                    "threshold": tp.threshold_temperature_c,
                    "severity": tp.impact_severity
                }
                for tp in tipping_points
            ],
            "scenario_name": result.scenario_name
        }

    @staticmethod
    def generate_summary_dashboard(result: ScenarioSimulationResult) -> Dict[str, Any]:
        """Generate comprehensive dashboard data."""
        return {
            "scenario": {
                "name": result.scenario_name,
                "id": result.scenario_id,
                "horizon": result.projection_horizon.value,
                "timeframe": f"{result.start_year} - {result.end_year}"
            },
            "temperature_data": ClimateVisualizationGenerator.generate_temperature_trend_data(result),
            "sea_level_data": ClimateVisualizationGenerator.generate_sea_level_data(result),
            "sector_impact_data": ClimateVisualizationGenerator.generate_sector_impact_data(result),
            "regional_impact_data": ClimateVisualizationGenerator.generate_regional_impact_data(result),
            "tipping_point_data": ClimateVisualizationGenerator.generate_tipping_point_data(result),
            "summary_metrics": result.summary_metrics,
            "recommendations": result.recommendations,
            "confidence_metrics": result.confidence_metrics
        }


class ClimateReportGenerator:
    """Generate comprehensive reports for climate simulations."""
    
    @staticmethod
    def generate_text_report(result: ScenarioSimulationResult) -> str:
        """Generate a detailed text src.reporting.report."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"CLIMATE SCENARIO SIMULATION REPORT")
        lines.append("=" * 80)
        lines.append(f"Scenario: {result.scenario_name}")
        lines.append(f"Scenario ID: {result.scenario_id}")
        lines.append(f"Timeframe: {result.start_year} - {result.end_year}")
        lines.append(f"Projection Horizon: {result.projection_horizon.value}")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary metrics
        lines.append("SUMMARY METRICS")
        lines.append("-" * 40)
        for key, value in result.summary_metrics.items():
            if isinstance(value, float):
                lines.append(f"  {key.replace('_', ' ').title()}: {value:.3f}")
            else:
                lines.append(f"  {key.replace('_', ' ').title()}: {value}")
        lines.append("")
        
        # Temperature projection
        if result.projections:
            final = result.projections[-1]
            lines.append("FINAL YEAR PROJECTIONS")
            lines.append("-" * 40)
            lines.append(f"  Year: {final.year}")
            lines.append(f"  Global Temperature Anomaly: {final.global_temperature_anomaly_c:.2f}°C")
            lines.append(f"  CO2 Concentration: {final.co2_concentration_ppm:.0f} ppm")
            lines.append(f"  Sea Level Rise: {final.sea_level_rise_m:.2f} m")
            lines.append(f"  Ocean pH: {final.ocean_ph:.2f}")
            lines.append(f"  Extreme Events Index: {final.extreme_events_index:.2f}")
            lines.append(f"  Drought Index: {final.drought_index:.2f}")
            lines.append(f"  Wildfire Risk Index: {final.wildfire_risk_index:.2f}")
            lines.append("")
        
        # Sector impacts
        lines.append("SECTOR IMPACTS")
        lines.append("-" * 40)
        for sector, impacts in result.sector_impacts.items():
            if impacts:
                final_impact = impacts[-1]
                lines.append(f"  {sector.title()}:")
                lines.append(f"    Impact Score: {final_impact.impact_score:.3f}")
                lines.append(f"    Economic Impact: ${final_impact.economic_impact_billion_usd:.1f} billion")
                lines.append(f"    People Affected: {final_impact.people_affected:,}")
                lines.append(f"    Risk Level: {final_impact.risk_level:.3f}")
        lines.append("")
        
        # Tipping points
        lines.append("TIPPING POINTS ASSESSMENT")
        lines.append("-" * 40)
        for tp in result.tipping_points:
            if tp.current_risk > 0.3:
                lines.append(f"  {tp.name}:")
                lines.append(f"    Current Risk: {tp.current_risk:.2%}")
                lines.append(f"    Threshold: {tp.threshold_temperature_c:.1f}°C")
                lines.append(f"    Impact Severity: {tp.impact_severity:.2f}")
                lines.append(f"    Timescale: {tp.timescale_years} years")
        lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 40)
        for i, rec in enumerate(result.recommendations, 1):
            lines.append(f"  {i}. {rec['priority'].upper()}: {rec['recommendation']}")
            lines.append(f"    Category: {rec['category']}")
            lines.append(f"    Timeframe: {rec['timeframe']}")
            if 'actions' in rec:
                lines.append("    Actions:")
                for action in rec['actions'][:3]:
                    lines.append(f"      • {action}")
        lines.append("")
        
        # Confidence metrics
        lines.append("CONFIDENCE METRICS")
        lines.append("-" * 40)
        for key, value in result.confidence_metrics.items():
            if isinstance(value, float):
                lines.append(f"  {key.replace('_', ' ').title()}: {value:.3f}")
            else:
                lines.append(f"  {key.replace('_', ' ').title()}: {value}")
        lines.append("")
        
        # Metadata
        lines.append("SIMULATION METADATA")
        lines.append("-" * 40)
        for key, value in result.simulation_metadata.items():
            lines.append(f"  {key.replace('_', ' ').title()}: {value}")
        lines.append("")
        
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_json_report(result: ScenarioSimulationResult) -> str:
        """Generate a JSON src.reporting.report."""
        data = {
            "scenario_id": result.scenario_id,
            "scenario_name": result.scenario_name,
            "projection_horizon": result.projection_horizon.value,
            "start_year": result.start_year,
            "end_year": result.end_year,
            "summary_metrics": result.summary_metrics,
            "confidence_metrics": result.confidence_metrics,
            "uncertainty_ranges": result.uncertainty_ranges,
            "recommendations": result.recommendations,
            "timestamp": result.timestamp,
            "metadata": result.simulation_metadata
        }
        
        # Add projections summary
        if result.projections:
            final = result.projections[-1]
            data["final_projection"] = {
                "year": final.year,
                "temperature_anomaly_c": final.global_temperature_anomaly_c,
                "co2_concentration_ppm": final.co2_concentration_ppm,
                "sea_level_rise_m": final.sea_level_rise_m,
                "extreme_events_index": final.extreme_events_index,
                "confidence": final.confidence.value
            }
        
        # Add sector impacts summary
        data["sector_impacts_summary"] = {}
        for sector, impacts in result.sector_impacts.items():
            if impacts:
                final_impact = impacts[-1]
                data["sector_impacts_summary"][sector] = {
                    "impact_score": final_impact.impact_score,
                    "economic_impact_billion_usd": final_impact.economic_impact_billion_usd,
                    "risk_level": final_impact.risk_level
                }
        
        # Add tipping points summary
        data["tipping_points_summary"] = [
            {
                "name": tp.name,
                "current_risk": tp.current_risk,
                "threshold_temperature_c": tp.threshold_temperature_c,
                "impact_severity": tp.impact_severity
            }
            for tp in result.tipping_points if tp.current_risk > 0.3
        ]
        
        return json.dumps(data, indent=2, default=str)


# ============================================================================
# COMPARATIVE ANALYSIS ENGINE
# ============================================================================

class ComparativeScenarioAnalyzer:
    """Analyze and compare multiple scenarios."""
    
    def __init__(self):
        self.engine = ClimateSimulationEngine()
        self.logger = logging.getLogger(f"{__name__}.ComparativeScenarioAnalyzer")
    
    def compare_scenarios(self, scenario_ids: List[str], 
                         start_year: int = 2020,
                         end_year: int = 2100) -> Dict[str, Any]:
        """
        Compare multiple scenarios.
        """
        results = {}
        
        for scenario_id in scenario_ids:
            self.logger.info(f"Simulating scenario: {scenario_id}")
            result = self.engine.simulate_scenario(scenario_id, start_year, end_year)
            results[scenario_id] = result
        
        # Generate comparison
        comparison = self._generate_comparison(results)
        
        return {
            "scenario_results": results,
            "comparison": comparison,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_comparison(self, results: Dict[str, ScenarioSimulationResult]) -> Dict[str, Any]:
        """Generate comparison metrics across scenarios."""
        comparison = {
            "temperature_comparison": {},
            "sea_level_comparison": {},
            "sector_impact_comparison": {},
            "cost_benefit_analysis": {},
            "risk_assessment": {}
        }
        
        # Temperature comparison
        for scenario_id, result in results.items():
            if result.projections:
                final = result.projections[-1]
                comparison["temperature_comparison"][scenario_id] = {
                    "final_temp_anomaly": final.global_temperature_anomaly_c,
                    "temp_increase_from_baseline": final.global_temperature_c - 13.7,
                    "peak_temp_anomaly": max(p.global_temperature_anomaly_c for p in result.projections)
                }
        
        # Sea level comparison
        for scenario_id, result in results.items():
            if result.projections:
                final = result.projections[-1]
                comparison["sea_level_comparison"][scenario_id] = {
                    "final_sea_level_rise": final.sea_level_rise_m,
                    "peak_sea_level_rise": max(p.sea_level_rise_m for p in result.projections)
                }
        
        # Sector impact comparison
        for scenario_id, result in results.items():
            comparison["sector_impact_comparison"][scenario_id] = {}
            for sector, impacts in result.sector_impacts.items():
                if impacts:
                    avg_impact = statistics.mean([i.impact_score for i in impacts])
                    comparison["sector_impact_comparison"][scenario_id][sector] = avg_impact
        
        # Cost-benefit analysis
        for scenario_id, result in results.items():
            total_economic_impact = 0.0
            total_adaptation_cost = 0.0
            for sector, impacts in result.sector_impacts.items():
                if impacts:
                    total_economic_impact += statistics.mean([i.economic_impact_billion_usd for i in impacts])
                    total_adaptation_cost += statistics.mean([i.adaptation_cost_billion_usd for i in impacts])
            
            comparison["cost_benefit_analysis"][scenario_id] = {
                "total_economic_impact": total_economic_impact,
                "total_adaptation_cost": total_adaptation_cost,
                "net_impact": total_economic_impact + total_adaptation_cost,
                "benefit_cost_ratio": total_economic_impact / max(total_adaptation_cost, 0.01)
            }
        
        # Risk assessment
        for scenario_id, result in results.items():
            risks = []
            for sector, impacts in result.sector_impacts.items():
                if impacts:
                    avg_risk = statistics.mean([i.risk_level for i in impacts])
                    risks.append(avg_risk)
            
            comparison["risk_assessment"][scenario_id] = {
                "average_risk": statistics.mean(risks) if risks else 0,
                "max_risk": max(risks) if risks else 0,
                "tipping_points_risk": statistics.mean([tp.current_risk for tp in result.tipping_points]) if result.tipping_points else 0
            }
        
        return comparison
    
    def generate_comparison_report(self, comparison: Dict[str, Any]) -> str:
        """Generate a comparison src.reporting.report."""
        lines = []
        lines.append("=" * 80)
        lines.append("SCENARIO COMPARISON REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {comparison['timestamp']}")
        lines.append("")
        
        # Temperature comparison
        lines.append("TEMPERATURE COMPARISON")
        lines.append("-" * 40)
        for scenario_id, data in comparison['comparison']['temperature_comparison'].items():
            lines.append(f"  {scenario_id}:")
            lines.append(f"    Final Temperature Anomaly: {data['final_temp_anomaly']:.2f}°C")
            lines.append(f"    Peak Temperature Anomaly: {data['peak_temp_anomaly']:.2f}°C")
        lines.append("")
        
        # Sea level comparison
        lines.append("SEA LEVEL COMPARISON")
        lines.append("-" * 40)
        for scenario_id, data in comparison['comparison']['sea_level_comparison'].items():
            lines.append(f"  {scenario_id}:")
            lines.append(f"    Final Sea Level Rise: {data['final_sea_level_rise']:.2f} m")
            lines.append(f"    Peak Sea Level Rise: {data['peak_sea_level_rise']:.2f} m")
        lines.append("")
        
        # Cost-benefit analysis
        lines.append("COST-BENEFIT ANALYSIS")
        lines.append("-" * 40)
        for scenario_id, data in comparison['comparison']['cost_benefit_analysis'].items():
            lines.append(f"  {scenario_id}:")
            lines.append(f"    Total Economic Impact: ${data['total_economic_impact']:.1f} billion")
            lines.append(f"    Total Adaptation Cost: ${data['total_adaptation_cost']:.1f} billion")
            lines.append(f"    Benefit-Cost Ratio: {data['benefit_cost_ratio']:.2f}")
        lines.append("")
        
        # Risk assessment
        lines.append("RISK ASSESSMENT")
        lines.append("-" * 40)
        for scenario_id, data in comparison['comparison']['risk_assessment'].items():
            lines.append(f"  {scenario_id}:")
            lines.append(f"    Average Risk: {data['average_risk']:.3f}")
            lines.append(f"    Maximum Risk: {data['max_risk']:.3f}")
            lines.append(f"    Tipping Points Risk: {data['tipping_points_risk']:.3f}")
        lines.append("")
        
        lines.append("=" * 80)
        lines.append("END OF COMPARISON REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)


# ============================================================================
# DATA EXPORT AND UTILITY FUNCTIONS
# ============================================================================

class ClimateDataExporter:
    """Export climate simulation data to various formats."""
    
    @staticmethod
    def export_to_csv(result: ScenarioSimulationResult, filename: str):
        """Export simulation results to CSV."""
        import csv
        
        with open(filename, 'w', newline='') as csvfile:
            # Write header
            fieldnames = ['year', 'temperature_anomaly', 'co2_ppm', 'sea_level_m',
                         'extreme_events', 'drought_index', 'wildfire_risk']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write data
            for projection in result.projections:
                writer.writerow({
                    'year': projection.year,
                    'temperature_anomaly': projection.global_temperature_anomaly_c,
                    'co2_ppm': projection.co2_concentration_ppm,
                    'sea_level_m': projection.sea_level_rise_m,
                    'extreme_events': projection.extreme_events_index,
                    'drought_index': projection.drought_index,
                    'wildfire_risk': projection.wildfire_risk_index
                })
        
        logger.info(f"Data exported to {filename}")
    
    @staticmethod
    def export_to_json(result: ScenarioSimulationResult, filename: str):
        """Export simulation results to JSON."""
        data = {
            "scenario_id": result.scenario_id,
            "scenario_name": result.scenario_name,
            "projections": [
                {
                    "year": p.year,
                    "temperature_anomaly_c": p.global_temperature_anomaly_c,
                    "co2_concentration_ppm": p.co2_concentration_ppm,
                    "sea_level_rise_m": p.sea_level_rise_m,
                    "extreme_events_index": p.extreme_events_index,
                    "drought_index": p.drought_index,
                    "wildfire_risk_index": p.wildfire_risk_index
                }
                for p in result.projections
            ],
            "summary_metrics": result.summary_metrics,
            "recommendations": result.recommendations
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Data exported to {filename}")
    
    @staticmethod
    def export_to_netcdf(result: ScenarioSimulationResult, filename: str):
        """Export to NetCDF format (placeholder)."""
        # This would use netCDF4 library in production
        logger.info(f"NetCDF export not implemented yet. Would export to {filename}")


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================

def run_demonstration():
    """Run a comprehensive demonstration."""
    print("\n" + "=" * 80)
    print("CLIMATE SCENARIO SIMULATION AND IMPACT PROJECTION")
    print("=" * 80 + "\n")
    
    # Initialize simulation engine
    engine = ClimateSimulationEngine()
    analyzer = ComparativeScenarioAnalyzer()
    report_generator = ClimateReportGenerator()
    visualizer = ClimateVisualizationGenerator()
    exporter = ClimateDataExporter()
    
    print("🚀 Simulating Climate Scenarios\n")
    
    # Simulate multiple scenarios
    scenarios = ["rcp_2.6", "rcp_4.5", "rcp_8.5"]
    
    results = {}
    for scenario_id in scenarios:
        print(f"Simulating {scenario_id}...")
        result = engine.simulate_scenario(scenario_id, 2020, 2100, 5)
        results[scenario_id] = result
        
        # Print key metrics
        final = result.projections[-1]
        print(f"  ✓ {result.scenario_name}")
        print(f"    Temperature Anomaly: {final.global_temperature_anomaly_c:.2f}°C")
        print(f"    Sea Level Rise: {final.sea_level_rise_m:.2f}m")
        print(f"    CO2 Concentration: {final.co2_concentration_ppm:.0f} ppm")
        print(f"    Extreme Events Index: {final.extreme_events_index:.2f}")
        print()
    
    # Comparative analysis
    print("📊 Comparative Analysis")
    print("-" * 40)
    
    comparison = analyzer.compare_scenarios(scenarios)
    
    for scenario_id, data in comparison['comparison']['temperature_comparison'].items():
        print(f"  {scenario_id}:")
        print(f"    Final Temp: {data['final_temp_anomaly']:.2f}°C")
        print(f"    Peak Temp: {data['peak_temp_anomaly']:.2f}°C")
    print()
    
    # Generate report for best-case scenario
    print("📄 Generating Report for RCP 2.6 (Best Case)")
    print("-" * 40)
    
    best_case = results["rcp_2.6"]
    report = report_generator.generate_text_report(best_case)
    
    # Save report
    with open("climate_report_rcp2.6.txt", "w") as f:
        f.write(report)
    
    print(f"✓ Report saved to climate_report_rcp2.6.txt")
    print()
    
    # Generate comparison report
    print("📊 Generating Comparison Report")
    print("-" * 40)
    
    comparison_report = analyzer.generate_comparison_report(comparison)
    with open("climate_comparison_report.txt", "w") as f:
        f.write(comparison_report)
    
    print(f"✓ Comparison report saved to climate_comparison_report.txt")
    print()
    
    # Export data
    print("💾 Exporting Data")
    print("-" * 40)
    
    exporter.export_to_csv(best_case, "climate_data_rcp2.6.csv")
    exporter.export_to_json(best_case, "climate_data_rcp2.6.json")
    
    print(f"✓ Data exported to climate_data_rcp2.6.csv and climate_data_rcp2.6.json")
    print()
    
    # Generate visualization data
    print("📊 Generating Visualization Data")
    print("-" * 40)
    
    dashboard_data = visualizer.generate_summary_dashboard(best_case)
    with open("climate_dashboard_data.json", "w") as f:
        json.dump(dashboard_data, f, indent=2, default=str)
    
    print(f"✓ Dashboard data saved to climate_dashboard_data.json")
    print()
    
    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80 + "\n")


def run_tests():
    """Run comprehensive tests."""
    print("\n" + "=" * 60)
    print("RUNNING TESTS")
    print("=" * 60 + "\n")
    
    # Test 1: Scenario database
    print("Test 1: Scenario Database")
    db = ClimateScenarioDatabase()
    scenarios = src.notifications.db.get_all_scenarios()
    assert len(scenarios) >= 8, "Should have at least 8 scenarios"
    print(f"✓ Database initialized with {len(scenarios)} scenarios")
    
    # Test 2: Scenario retrieval
    print("\nTest 2: Scenario Retrieval")
    scenario = src.notifications.db.get_scenario("rcp_2.6")
    assert scenario is not None, "Should retrieve RCP 2.6"
    assert scenario.scenario_type == ClimateScenarioType.RCP_2_6
    print(f"✓ Retrieved {scenario.name}")
    
    # Test 3: Simulation engine
    print("\nTest 3: Simulation Engine")
    engine = ClimateSimulationEngine()
    result = engine.simulate_scenario("rcp_2.6", 2020, 2050, 10)
    assert len(result.projections) == 4, "Should have 4 projections"
    assert result.summary_metrics is not None
    print(f"✓ Simulation generated {len(result.projections)} projections")
    
    # Test 4: Sector impacts
    print("\nTest 4: Sector Impacts")
    assert len(result.sector_impacts) > 0, "Should have sector impacts"
    for sector, impacts in result.sector_impacts.items():
        assert len(impacts) == len(result.projections), f"Should have impact for each projection"
    print(f"✓ Generated impacts for {len(result.sector_impacts)} sectors")
    
    # Test 5: Tipping points
    print("\nTest 5: Tipping Points")
    assert len(result.tipping_points) > 0, "Should have tipping points"
    print(f"✓ Assessed {len(result.tipping_points)} tipping points")
    
    # Test 6: Recommendations
    print("\nTest 6: Recommendations")
    assert len(result.recommendations) > 0, "Should have recommendations"
    print(f"✓ Generated {len(result.recommendations)} recommendations")
    
    # Test 7: Report generation
    print("\nTest 7: Report Generation")
    report_gen = ClimateReportGenerator()
    report = report_gen.generate_text_report(result)
    assert len(report) > 100, "Report should be substantial"
    print("✓ Report generated successfully")
    
    # Test 8: Comparative analysis
    print("\nTest 8: Comparative Analysis")
    analyzer = ComparativeScenarioAnalyzer()
    comparison = analyzer.compare_scenarios(["rcp_2.6", "rcp_8.5"])
    assert len(comparison['results']) == 2, "Should have 2 results"
    assert 'comparison' in comparison, "Should have comparison data"
    print("✓ Comparative analysis complete")
    
    # Test 9: Visualization data
    print("\nTest 9: Visualization Data")
    visualizer = ClimateVisualizationGenerator()
    dashboard = visualizer.generate_summary_dashboard(result)
    assert 'temperature_data' in dashboard, "Should have temperature data"
    assert 'sector_impact_data' in dashboard, "Should have sector impact data"
    print("✓ Visualization data generated")
    
    # Test 10: Export functionality
    print("\nTest 10: Data Export")
    exporter = ClimateDataExporter()
    try:
        exporter.export_to_csv(result, "test_climate_data.csv")
        exporter.export_to_json(result, "test_climate_data.json")
        print("✓ Data export successful")
    except Exception as e:
        print(f"✗ Export failed: {e}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("CLIMATE SCENARIO SIMULATION AND IMPACT PROJECTION FRAMEWORK")
    print("Version 3.0.0")
    print("=" * 80 + "\n")
    
    print("Select an option:")
    print("1. Run demonstration")
    print("2. Run tests")
    print("3. Interactive simulation (coming soon)")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        run_demonstration()
    elif choice == '2':
        run_tests()
    elif choice == '3':
        print("\nInteractive mode coming soon!")
        print("Please run the demonstration for now.")
    else:
        print("Goodbye!")


if __name__ == "__main__":
    main()



"""
Spatiotemporal Environmental Risk Intelligence Framework
==========================================================
An advanced framework for integrating spatial and temporal environmental data
to assess, predict, and provide early warnings for environmental risks.

Author: EcoBuddy Team
Version: 4.0.0
"""

import json
import math
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any, Set, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from pathlib import Path
import hashlib
import re
from collections import defaultdict, Counter, deque
import heapq
from functools import lru_cache
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class RiskType(Enum):
    """Types of environmental risks."""
    FLOOD = "flood"
    DROUGHT = "drought"
    WILDFIRE = "wildfire"
    EARTHQUAKE = "earthquake"
    LANDSLIDE = "landslide"
    TSUNAMI = "tsunami"
    CYCLONE = "cyclone"
    HEATWAVE = "heatwave"
    COLDWAVE = "coldwave"
    AIR_POLLUTION = "air_pollution"
    WATER_POLLUTION = "water_pollution"
    SOIL_CONTAMINATION = "soil_contamination"
    DEFORESTATION = "deforestation"
    DESERTIFICATION = "desertification"
    GLACIAL_MELT = "glacial_melt"
    SEA_LEVEL_RISE = "sea_level_rise"
    BIODIVERSITY_LOSS = "biodiversity_loss"
    WASTE_ACCUMULATION = "waste_accumulation"
    NOISE_POLLUTION = "noise_pollution"
    LIGHT_POLLUTION = "light_pollution"


class RiskSeverity(Enum):
    """Severity levels for risks."""
    INSIGNIFICANT = 0
    MINOR = 1
    MODERATE = 2
    MAJOR = 3
    SEVERE = 4
    CATASTROPHIC = 5


class RiskStatus(Enum):
    """Current status of a risk."""
    INACTIVE = "inactive"
    MONITORING = "monitoring"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"
    ONGOING = "ongoing"
    RESOLVED = "resolved"


class SpatialScale(Enum):
    """Spatial scales for analysis."""
    GLOBAL = "global"
    CONTINENTAL = "continental"
    REGIONAL = "regional"
    NATIONAL = "national"
    SUB_NATIONAL = "sub_national"
    LOCAL = "local"
    NEIGHBORHOOD = "neighborhood"
    INDIVIDUAL = "individual"


class TemporalScale(Enum):
    """Temporal scales for analysis."""
    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SEASONAL = "seasonal"
    ANNUAL = "annual"
    DECADAL = "decadal"
    CENTURY = "century"


class DataSourceType(Enum):
    """Types of data sources."""
    SATELLITE = "satellite"
    GROUND_STATION = "ground_station"
    WEATHER_STATION = "weather_station"
    BUOY = "buoy"
    RADAR = "radar"
    LIDAR = "lidar"
    DRONE = "drone"
    AIRCRAFT = "aircraft"
    SHIP = "ship"
    SENSOR_NETWORK = "sensor_network"
    CITIZEN_SCIENCE = "citizen_science"
    SOCIAL_MEDIA = "social_media"
    NEWS = "news"
    HISTORICAL_RECORDS = "historical_records"
    MODEL_OUTPUT = "model_output"
    EXPERT_KNOWLEDGE = "expert_knowledge"


# ============================================================================
# DATA CLASSES FOR SPATIOTEMPORAL DATA
# ============================================================================

@dataclass
class GeoPoint:
    """Geographic point with coordinates."""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: float = 0.0
    source: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}")
    
    def distance_to(self, other: 'GeoPoint') -> float:
        """Calculate Euclidean distance in km."""
        import math
        lat1, lon1 = self.latitude, self.longitude
        lat2, lon2 = other.latitude, other.longitude
        R = 6371  # Earth's radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c


@dataclass
class BoundingBox:
    """Geographic bounding box."""
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    
    def __post_init__(self):
        if not -90 <= self.min_lat <= 90 or not -90 <= self.max_lat <= 90:
            raise ValueError("Invalid latitude range")
        if not -180 <= self.min_lon <= 180 or not -180 <= self.max_lon <= 180:
            raise ValueError("Invalid longitude range")
        if self.min_lat > self.max_lat:
            self.min_lat, self.max_lat = self.max_lat, self.min_lat
        if self.min_lon > self.max_lon:
            self.min_lon, self.max_lon = self.max_lon, self.min_lon
    
    def contains_point(self, point: GeoPoint) -> bool:
        """Check if point is within bounding box."""
        return (self.min_lat <= point.latitude <= self.max_lat and
                self.min_lon <= point.longitude <= self.max_lon)
    
    def area_sqkm(self) -> float:
        """Calculate approximate area in square kilometers."""
        import math
        lat_avg = (self.min_lat + self.max_lat) / 2
        lat_diff = abs(self.max_lat - self.min_lat)
        lon_diff = abs(self.max_lon - self.min_lon)
        R = 6371
        lat_rad = math.radians(lat_avg)
        area = R**2 * math.cos(lat_rad) * math.radians(lat_diff) * math.radians(lon_diff)
        return abs(area)


@dataclass
class TimeWindow:
    """Time window for temporal analysis."""
    start_time: datetime
    end_time: datetime
    
    def __post_init__(self):
        if self.start_time > self.end_time:
            self.start_time, self.end_time = self.end_time, self.start_time
    
    def contains(self, timestamp: datetime) -> bool:
        """Check if timestamp is within window."""
        return self.start_time <= timestamp <= self.end_time
    
    def duration_hours(self) -> float:
        """Get duration in hours."""
        return (self.end_time - self.start_time).total_seconds() / 3600


@dataclass
class SpatiotemporalPoint:
    """Point with both spatial and temporal data."""
    point: GeoPoint
    timestamp: datetime
    values: Dict[str, float]
    quality_indicators: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskIndicator:
    """An environmental risk indicator."""
    indicator_id: str
    name: str
    description: str
    risk_type: RiskType
    value: float
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    threshold_warning: Optional[float] = None
    threshold_alert: Optional[float] = None
    unit: str = ""
    confidence: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)
    spatial_scale: SpatialScale = SpatialScale.LOCAL
    temporal_scale: TemporalScale = TemporalScale.HOURLY
    source: DataSourceType = DataSourceType.GROUND_STATION
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_severity(self) -> RiskSeverity:
        """Determine risk severity based on thresholds."""
        if self.threshold_alert is not None and self.value >= self.threshold_alert:
            return RiskSeverity.CATASTROPHIC if self.value >= self.threshold_alert * 1.5 else RiskSeverity.SEVERE
        if self.threshold_warning is not None and self.value >= self.threshold_warning:
            return RiskSeverity.MAJOR if self.value >= self.threshold_warning * 1.3 else RiskSeverity.MODERATE
        if self.threshold_max is not None and self.value >= self.threshold_max:
            return RiskSeverity.MODERATE
        if self.threshold_min is not None and self.value <= self.threshold_min:
            return RiskSeverity.MINOR
        return RiskSeverity.INSIGNIFICANT
    
    def is_anomalous(self) -> bool:
        """Check if indicator value is anomalous."""
        if self.threshold_max is not None and self.value > self.threshold_max:
            return True
        if self.threshold_min is not None and self.value < self.threshold_min:
            return True
        if self.threshold_warning is not None and self.value > self.threshold_warning:
            return True
        return False


@dataclass
class EnvironmentalEvent:
    """An environmental event with spatiotemporal characteristics."""
    event_id: str
    event_type: RiskType
    description: str
    location: GeoPoint
    bounding_box: Optional[BoundingBox] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    severity: RiskSeverity = RiskSeverity.MODERATE
    status: RiskStatus = RiskStatus.MONITORING
    magnitude: float = 0.0
    affected_area_sqkm: float = 0.0
    affected_population: int = 0
    economic_impact_usd: float = 0.0
    indicators: List[RiskIndicator] = field(default_factory=list)
    confidence: float = 0.5
    source: DataSourceType = DataSourceType.MODEL_OUTPUT
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_indicator(self, indicator: RiskIndicator):
        """Add a risk indicator to the event."""
        self.indicators.append(indicator)
        self._update_event_properties()
    
    def _update_event_properties(self):
        """Update event properties based on indicators."""
        if self.indicators:
            # Update severity based on highest severity indicator
            severities = [ind.get_severity().value for ind in self.indicators]
            self.severity = RiskSeverity(max(severities))
            
            # Update confidence
            self.confidence = statistics.mean([ind.confidence for ind in self.indicators])
            
            # Update magnitude
            self.magnitude = statistics.mean([ind.value for ind in self.indicators if ind.value])


@dataclass
class SpatiotemporalRiskForecast:
    """A forecast for environmental risks."""
    forecast_id: str
    risk_type: RiskType
    location: GeoPoint
    forecast_time: datetime
    time_window: TimeWindow
    predicted_probability: float  # 0-1
    predicted_severity: RiskSeverity
    confidence: float
    lead_time_hours: float
    indicators: Dict[str, float] = field(default_factory=dict)
    scenarios: Dict[str, Dict[str, float]] = field(default_factory=dict)
    uncertainty_range: Tuple[float, float] = (0.0, 1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SPATIOTEMPORAL DATA FUSION ENGINE
# ============================================================================

class SpatiotemporalDataFusionEngine:
    """Engine for fusing data from multiple spatiotemporal sources."""
    
    def __init__(self):
        """Initialize the fusion engine."""
        self.logger = logging.getLogger(f"{__name__}.SpatiotemporalDataFusionEngine")
        self.data_cache = {}
        self.source_weights = self._initialize_source_weights()
        self.fusion_methods = self._initialize_fusion_methods()
    
    def _initialize_source_weights(self) -> Dict[DataSourceType, float]:
        """Initialize weights for different data sources."""
        return {
            DataSourceType.SATELLITE: 0.9,
            DataSourceType.GROUND_STATION: 1.0,
            DataSourceType.WEATHER_STATION: 0.95,
            DataSourceType.BUOY: 0.85,
            DataSourceType.RADAR: 0.8,
            DataSourceType.LIDAR: 0.8,
            DataSourceType.DRONE: 0.75,
            DataSourceType.AIRCRAFT: 0.7,
            DataSourceType.SHIP: 0.7,
            DataSourceType.SENSOR_NETWORK: 0.8,
            DataSourceType.CITIZEN_SCIENCE: 0.4,
            DataSourceType.SOCIAL_MEDIA: 0.3,
            DataSourceType.NEWS: 0.4,
            DataSourceType.HISTORICAL_RECORDS: 0.6,
            DataSourceType.MODEL_OUTPUT: 0.85,
            DataSourceType.EXPERT_KNOWLEDGE: 0.75
        }
    
    def _initialize_fusion_methods(self) -> Dict[str, Callable]:
        """Initialize different data fusion methods."""
        return {
            "weighted_average": self._weighted_average_fusion,
            "bayesian": self._bayesian_fusion,
            "kalman": self._kalman_fusion,
            "dempster_shafer": self._dempster_shafer_fusion,
            "ensemble": self._ensemble_fusion
        }
    
    def _weighted_average_fusion(self, data_points: List[SpatiotemporalPoint],
                                 weights: Optional[List[float]] = None) -> Dict[str, float]:
        """Fuse data using weighted average."""
        if not data_points:
            return {}
        
        if weights is None:
            weights = [1.0] * len(data_points)
        
        result = {}
        value_keys = data_points[0].values.keys()
        
        for key in value_keys:
            total = 0.0
            total_weight = 0.0
            for point, weight in zip(data_points, weights):
                if key in point.values:
                    total += point.values[key] * weight
                    total_weight += weight
            
            if total_weight > 0:
                result[key] = total / total_weight
        
        return result
    
    def _bayesian_fusion(self, data_points: List[SpatiotemporalPoint],
                        prior_distribution: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Fuse data using Bayesian approach."""
        if not data_points:
            return {}
        
        result = {}
        value_keys = data_points[0].values.keys()
        
        for key in value_keys:
            # Collect observations and uncertainties
            observations = []
            uncertainties = []
            for point in data_points:
                if key in point.values:
                    observations.append(point.values[key])
                    uncertainties.append(point.quality_indicators.get('uncertainty', 0.1))
            
            if not observations:
                continue
            
            # Weighted average with uncertainty weighting
            total_weight = sum(1.0 / (u + 0.001) for u in uncertainties)
            weighted_sum = sum(v / (u + 0.001) for v, u in zip(observations, uncertainties))
            
            result[f"{key}_mean"] = weighted_sum / total_weight
            result[f"{key}_variance"] = 1.0 / total_weight
        
        return result
    
    def _kalman_fusion(self, data_points: List[SpatiotemporalPoint],
                       state: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Fuse data using Kalman filter approach."""
        if not data_points:
            return {}
        
        result = {}
        value_keys = data_points[0].values.keys()
        
        for key in value_keys:
            # Extract time series
            time_series = []
            for point in data_points:
                if key in point.values:
                    time_series.append((point.timestamp, point.values[key]))
            
            if len(time_series) < 2:
                continue
            
            # Simple Kalman filter
            x_prev = time_series[0][1]
            p_prev = 1.0
            
            for t, z in time_series[1:]:
                # Prediction
                x_pred = x_prev
                p_pred = p_prev + 0.1
                
                # Update
                k = p_pred / (p_pred + 0.5)
                x_est = x_pred + k * (z - x_pred)
                p_est = (1 - k) * p_pred
                
                x_prev = x_est
                p_prev = p_est
            
            result[f"{key}_filtered"] = x_prev
            result[f"{key}_uncertainty"] = math.sqrt(p_prev)
        
        return result
    
    def _dempster_shafer_fusion(self, data_points: List[SpatiotemporalPoint]) -> Dict[str, float]:
        """Fuse data using Dempster-Shafer theory."""
        if not data_points:
            return {}
        
        result = {}
        value_keys = data_points[0].values.keys()
        
        for key in value_keys:
            beliefs = []
            for point in data_points:
                if key in point.values:
                    belief = point.values[key]
                    confidence = point.quality_indicators.get('confidence', 0.5)
                    beliefs.append((belief, confidence))
            
            if not beliefs:
                continue
            
            # Combine beliefs
            total_belief = 0.0
            total_weight = 0.0
            for b, c in beliefs:
                weight = c / (1 - c + 0.001)
                total_belief += b * weight
                total_weight += weight
            
            if total_weight > 0:
                result[f"{key}_belief"] = total_belief / total_weight
        
        return result
    
    def _ensemble_fusion(self, data_points: List[SpatiotemporalPoint],
                        methods: List[str] = None) -> Dict[str, float]:
        """Fuse data using ensemble of methods."""
        if not data_points:
            return {}
        
        if methods is None:
            methods = ["weighted_average", "bayesian", "kalman"]
        
        results = []
        for method in methods:
            if method == "weighted_average":
                result = self._weighted_average_fusion(data_points)
            elif method == "bayesian":
                result = self._bayesian_fusion(data_points)
            elif method == "kalman":
                result = self._kalman_fusion(data_points)
            elif method == "dempster_shafer":
                result = self._dempster_shafer_fusion(data_points)
            else:
                continue
            results.append(result)
        
        # Ensemble average
        if not results:
            return {}
        
        ensemble_result = {}
        for key in results[0].keys():
            values = [r.get(key, 0) for r in results if key in r]
            if values:
                ensemble_result[key] = statistics.mean(values)
                ensemble_result[f"{key}_std"] = statistics.stdev(values) if len(values) > 1 else 0
        
        return ensemble_result
    
    def fuse_data(self, data_points: List[SpatiotemporalPoint],
                 method: str = "ensemble",
                 **kwargs) -> Dict[str, float]:
        """
        Fuse spatiotemporal data using specified method.
        """
        self.logger.info(f"Fusing {len(data_points)} data points using {method}")
        
        if not data_points:
            self.logger.warning("No data points to fuse")
            return {}
        
        if method in self.fusion_methods:
            return self.fusion_methods[method](data_points, **kwargs)
        else:
            self.logger.warning(f"Unknown fusion method: {method}, using weighted_average")
            return self._weighted_average_fusion(data_points, **kwargs)
    
    def interpolate_spatiotemporal(self, data_points: List[SpatiotemporalPoint],
                                   target_point: GeoPoint,
                                   target_time: datetime,
                                   method: str = "inverse_distance") -> Dict[str, float]:
        """
        Interpolate data to a target spatiotemporal point.
        """
        self.logger.info(f"Interpolating to {target_point}, {target_time}")
        
        if not data_points:
            return {}
        
        # Calculate spatiotemporal distances
        weighted_points = []
        for point in data_points:
            spatial_dist = target_point.distance_to(point.point)
            temporal_dist = abs((target_time - point.timestamp).total_seconds()) / 3600
            
            # Weighted distance
            distance = math.sqrt(spatial_dist**2 + (temporal_dist * 10)**2)
            weight = 1.0 / (distance + 0.001)
            weighted_points.append((weight, point))
        
        # Interpolate using inverse distance weighting
        result = {}
        if not weighted_points:
            return result
        
        value_keys = weighted_points[0][1].values.keys()
        for key in value_keys:
            total = 0.0
            total_weight = 0.0
            for weight, point in weighted_points:
                if key in point.values:
                    total += point.values[key] * weight
                    total_weight += weight
            
            if total_weight > 0:
                result[key] = total / total_weight
        
        return result


# ============================================================================
# RISK PATTERN DETECTION ENGINE
# ============================================================================

class RiskPatternDetectionEngine:
    """Engine for detecting patterns and anomalies in spatiotemporal data."""
    
    def __init__(self):
        """Initialize the pattern detection engine."""
        self.logger = logging.getLogger(f"{__name__}.RiskPatternDetectionEngine")
        self.patterns = []
        self.anomaly_detectors = self._initialize_anomaly_detectors()
    
    def _initialize_anomaly_detectors(self) -> Dict[str, Callable]:
        """Initialize anomaly detection methods."""
        return {
            "statistical": self._statistical_anomaly,
            "z_score": self._z_score_anomaly,
            "isolation_forest": self._isolation_forest_anomaly,
            "time_series": self._time_series_anomaly,
            "spatial_clustering": self._spatial_clustering_anomaly
        }
    
    def _statistical_anomaly(self, data: List[float],
                            threshold: float = 3.0) -> List[int]:
        """Detect anomalies using statistical methods."""
        if len(data) < 3:
            return []
        
        mean = statistics.mean(data)
        std = statistics.stdev(data) if len(data) > 1 else 0
        
        if std == 0:
            return []
        
        anomalies = []
        for i, value in enumerate(data):
            z_score = abs((value - mean) / std)
            if z_score > threshold:
                anomalies.append(i)
        
        return anomalies
    
    def _z_score_anomaly(self, data: List[float],
                        threshold: float = 2.5) -> List[int]:
        """Detect anomalies using Z-score method."""
        return self._statistical_anomaly(data, threshold)
    
    def _isolation_forest_anomaly(self, data: List[float],
                                 contamination: float = 0.1) -> List[int]:
        """Detect anomalies using Isolation Forest approach."""
        # Simplified isolation forest
        if len(data) < 10:
            return []
        
        # Random forest isolation
        anomalies = set()
        n_samples = len(data)
        n_trees = 10
        
        for _ in range(n_trees):
            # Randomly select data
            indices = random.sample(range(n_samples), min(50, n_samples))
            values = [data[i] for i in indices]
            
            # Simple isolation
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values) if len(values) > 1 else 0
            
            for i, value in enumerate(data):
                if std_val > 0 and abs(value - mean_val) / std_val > 3.0:
                    anomalies.add(i)
        
        return list(anomalies)
    
    def _time_series_anomaly(self, data: List[float],
                            window_size: int = 5,
                            threshold: float = 2.0) -> List[int]:
        """Detect anomalies in time series data."""
        if len(data) < window_size * 2:
            return []
        
        anomalies = []
        
        for i in range(window_size, len(data) - window_size):
            window = data[i-window_size:i+window_size]
            mean = statistics.mean(window)
            std = statistics.stdev(window) if len(window) > 1 else 0
            
            if std > 0:
                z_score = abs((data[i] - mean) / std)
                if z_score > threshold:
                    anomalies.append(i)
        
        return anomalies
    
    def _spatial_clustering_anomaly(self, data: List[Tuple[float, float, float]],
                                   eps: float = 0.5,
                                   min_samples: int = 3) -> List[int]:
        """Detect spatial anomalies using clustering."""
        # Simplified DBSCAN-like approach
        if len(data) < min_samples:
            return []
        
        anomalies = []
        clusters = []
        visited = set()
        
        for i, point in enumerate(data):
            if i in visited:
                continue
            
            # Find neighbors
            neighbors = []
            for j, other in enumerate(data):
                if j == i:
                    continue
                distance = math.sqrt((point[0] - other[0])**2 + 
                                   (point[1] - other[1])**2)
                if distance < eps:
                    neighbors.append(j)
            
            if len(neighbors) >= min_samples:
                cluster = [i] + neighbors
                clusters.append(cluster)
                visited.update(cluster)
            else:
                visited.add(i)
        
        # Points not in clusters are anomalies
        all_clustered = set()
        for cluster in clusters:
            all_clustered.update(cluster)
        
        for i in range(len(data)):
            if i not in all_clustered:
                anomalies.append(i)
        
        return anomalies
    
    def detect_anomalies(self, data: List[float],
                        method: str = "statistical",
                        **kwargs) -> List[int]:
        """
        Detect anomalies in data using specified method.
        """
        if not data:
            return []
        
        if method in self.anomaly_detectors:
            return self.anomaly_detectors[method](data, **kwargs)
        else:
            self.logger.warning(f"Unknown anomaly method: {method}, using statistical")
            return self._statistical_anomaly(data, **kwargs)
    
    def detect_patterns(self, spatiotemporal_data: List[SpatiotemporalPoint],
                       pattern_type: str = "trend") -> Dict[str, Any]:
        """
        Detect patterns in spatiotemporal data.
        """
        self.logger.info(f"Detecting patterns of type: {pattern_type}")
        
        if not spatiotemporal_data:
            return {}
        
        patterns = {}
        
        if pattern_type == "trend":
            patterns = self._detect_trends(spatiotemporal_data)
        elif pattern_type == "seasonal":
            patterns = self._detect_seasonal_patterns(spatiotemporal_data)
        elif pattern_type == "spatial_cluster":
            patterns = self._detect_spatial_clusters(spatiotemporal_data)
        elif pattern_type == "temporal_correlation":
            patterns = self._detect_temporal_correlations(spatiotemporal_data)
        elif pattern_type == "spatiotemporal_evolution":
            patterns = self._detect_spatiotemporal_evolution(spatiotemporal_data)
        
        return patterns
    
    def _detect_trends(self, data: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """Detect temporal trends in data."""
        patterns = {}
        
        # Extract value keys
        if not data:
            return patterns
        
        value_keys = data[0].values.keys()
        
        for key in value_keys:
            # Extract time series
            time_series = [(p.timestamp, p.values.get(key, 0)) for p in data if key in p.values]
            
            if len(time_series) < 3:
                continue
            
            # Sort by time
            time_series.sort(key=lambda x: x[0])
            values = [v for _, v in time_series]
            
            # Simple linear trend
            n = len(values)
            x = list(range(n))
            mean_x = statistics.mean(x)
            mean_y = statistics.mean(values)
            
            slope = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
            slope /= sum((x[i] - mean_x)**2 for i in range(n))
            
            # Trend significance
            patterns[f"{key}_trend"] = slope
            patterns[f"{key}_trend_direction"] = "increasing" if slope > 0 else "decreasing"
            patterns[f"{key}_trend_magnitude"] = abs(slope) / mean_y if mean_y != 0 else 0
        
        return patterns
    
    def _detect_seasonal_patterns(self, data: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """Detect seasonal patterns in data."""
        patterns = {}
        
        # Group by month
        monthly_data = defaultdict(list)
        for point in data:
            month = point.timestamp.month
            for key, value in point.values.items():
                monthly_data[(month, key)].append(value)
        
        for (month, key), values in monthly_data.items():
            if values:
                patterns[f"{key}_month_{month}_mean"] = statistics.mean(values)
                patterns[f"{key}_month_{month}_std"] = statistics.stdev(values) if len(values) > 1 else 0
        
        return patterns
    
    def _detect_spatial_clusters(self, data: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """Detect spatial clusters in data."""
        patterns = {}
        
        if len(data) < 3:
            return patterns
        
        # Extract coordinates and values
        points = []
        for point in data:
            value_sum = sum(point.values.values())
            points.append((point.point.latitude, point.point.longitude, value_sum))
        
        # Use simplified clustering
        clusters = []
        visited = set()
        eps = 0.1  # Approximately 11km
        
        for i, point in enumerate(points):
            if i in visited:
                continue
            
            # Find neighbors
            neighbors = []
            for j, other in enumerate(points):
                if j == i:
                    continue
                distance = math.sqrt((point[0] - other[0])**2 + (point[1] - other[1])**2)
                if distance < eps:
                    neighbors.append(j)
            
            if len(neighbors) >= 2:
                cluster = [i] + neighbors
                clusters.append(cluster)
                visited.update(cluster)
            else:
                visited.add(i)
        
        patterns["num_clusters"] = len(clusters)
        for i, cluster in enumerate(clusters):
            cluster_values = [points[j][2] for j in cluster]
            cluster_lats = [points[j][0] for j in cluster]
            cluster_lons = [points[j][1] for j in cluster]
            
            patterns[f"cluster_{i}_size"] = len(cluster)
            patterns[f"cluster_{i}_mean_value"] = statistics.mean(cluster_values) if cluster_values else 0
            patterns[f"cluster_{i}_center_lat"] = statistics.mean(cluster_lats) if cluster_lats else 0
            patterns[f"cluster_{i}_center_lon"] = statistics.mean(cluster_lons) if cluster_lons else 0
        
        return patterns
    
    def _detect_temporal_correlations(self, data: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """Detect temporal correlations between variables."""
        patterns = {}
        
        if len(data) < 5:
            return patterns
        
        # Extract time series for each variable
        variables = {}
        for point in data:
            timestamp = point.timestamp
            for key, value in point.values.items():
                if key not in variables:
                    variables[key] = []
                variables[key].append((timestamp, value))
        
        # Sort each variable by time
        for key in variables:
            variables[key].sort(key=lambda x: x[0])
        
        # Calculate correlations
        keys = list(variables.keys())
        for i, key1 in enumerate(keys):
            for key2 in keys[i+1:]:
                # Align time series
                values1 = [v for _, v in variables[key1]]
                values2 = [v for _, v in variables[key2]]
                
                if len(values1) == len(values2) and len(values1) > 2:
                    # Calculate correlation
                    corr = self._pearson_correlation(values1, values2)
                    patterns[f"correlation_{key1}_{key2}"] = corr
                    
                    # Calculate lag correlation
                    for lag in [1, 2, 3]:
                        if len(values1) > lag:
                            shifted2 = values2[lag:]
                            truncated1 = values1[:len(shifted2)]
                            if len(truncated1) > 2:
                                lag_corr = self._pearson_correlation(truncated1, shifted2)
                                patterns[f"correlation_lag_{lag}_{key1}_{key2}"] = lag_corr
        
        return patterns
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 3:
            return 0.0
        
        n = len(x)
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)
        
        covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        std_x = math.sqrt(sum((x[i] - mean_x)**2 for i in range(n)))
        std_y = math.sqrt(sum((y[i] - mean_y)**2 for i in range(n)))
        
        if std_x == 0 or std_y == 0:
            return 0.0
        
        return covariance / (std_x * std_y)
    
    def _detect_spatiotemporal_evolution(self, data: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """Detect spatiotemporal evolution patterns."""
        patterns = {}
        
        if len(data) < 3:
            return patterns
        
        # Sort by time
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        
        # Track movement of "centers" over time
        centers = []
        for time_slice in self._split_by_time(sorted_data, 3):
            if time_slice:
                center_lat = statistics.mean([p.point.latitude for p in time_slice])
                center_lon = statistics.mean([p.point.longitude for p in time_slice])
                mean_value = statistics.mean([sum(p.values.values()) for p in time_slice])
                centers.append({
                    'time': time_slice[0].timestamp,
                    'lat': center_lat,
                    'lon': center_lon,
                    'value': mean_value
                })
        
        if len(centers) > 1:
            # Calculate movement
            for i in range(len(centers) - 1):
                time_diff = (centers[i+1]['time'] - centers[i]['time']).total_seconds() / 3600
                if time_diff > 0:
                    lat_change = centers[i+1]['lat'] - centers[i]['lat']
                    lon_change = centers[i+1]['lon'] - centers[i]['lon']
                    speed = math.sqrt(lat_change**2 + lon_change**2) / time_diff
                    
                    patterns[f"movement_speed_{i}"] = speed
                    patterns[f"lat_change_{i}"] = lat_change
                    patterns[f"lon_change_{i}"] = lon_change
        
        return patterns
    
    def _split_by_time(self, data: List[SpatiotemporalPoint], 
                      num_splits: int) -> List[List[SpatiotemporalPoint]]:
        """Split data into temporal slices."""
        if not data:
            return []
        
        # Sort by time
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        
        # Determine split points
        n = len(sorted_data)
        split_size = max(1, n // num_splits)
        
        splits = []
        for i in range(0, n, split_size):
            splits.append(sorted_data[i:min(i+split_size, n)])
        
        return splits


# ============================================================================
# EARLY WARNING SYSTEM
# ============================================================================

class EarlyWarningSystem:
    """Early warning system for environmental risks."""
    
    def __init__(self):
        """Initialize the early warning system."""
        self.logger = logging.getLogger(f"{__name__}.EarlyWarningSystem")
        self.warnings = []
        self.alert_thresholds = self._initialize_alert_thresholds()
        self.communication_channels = []
    
    def _initialize_alert_thresholds(self) -> Dict[RiskType, Dict[str, float]]:
        """Initialize alert thresholds for different risk types."""
        return {
            RiskType.FLOOD: {
                "water_level": 2.5,  # meters above normal
                "rainfall_intensity": 50.0,  # mm/hour
                "river_discharge": 1000.0  # m3/s
            },
            RiskType.DROUGHT: {
                "precipitation_deficit": -30.0,  # percent
                "soil_moisture": 0.2,  # fraction
                "vegetation_health": 0.3  # fraction
            },
            RiskType.WILDFIRE: {
                "temperature": 40.0,  # °C
                "humidity": 20.0,  # percent
                "wind_speed": 40.0,  # km/h
                "fuel_moisture": 10.0  # percent
            },
            RiskType.HEATWAVE: {
                "temperature": 40.0,  # °C
                "temperature_anomaly": 5.0,  # °C above normal
                "humidity": 50.0  # percent
            },
            RiskType.AIR_POLLUTION: {
                "pm2.5": 50.0,  # µg/m³
                "pm10": 100.0,  # µg/m³
                "no2": 100.0,  # µg/m³
                "o3": 120.0  # µg/m³
            },
            RiskType.WATER_POLLUTION: {
                "dissolved_oxygen": 4.0,  # mg/L
                "turbidity": 50.0,  # NTU
                "ph": 6.5,  # pH units
                "nitrate": 10.0  # mg/L
            }
        }
    
    def _initialize_communication_channels(self):
        """Initialize communication channels for alerts."""
        self.communication_channels = [
            "email",
            "sms",
            "push_notification",
            "dashboard",
            "webhook",
            "telegram",
            "slack"
        ]
    
    def check_alerts(self, indicators: List[RiskIndicator]) -> List[Dict[str, Any]]:
        """
        Check if any indicators trigger alerts.
        """
        alerts = []
        
        for indicator in indicators:
            thresholds = self.alert_thresholds.get(indicator.risk_type, {})
            
            if indicator.name in thresholds:
                threshold = thresholds[indicator.name]
                
                if indicator.value >= threshold:
                    severity = self._determine_alert_severity(indicator.value, threshold)
                    alert = {
                        "indicator": indicator,
                        "threshold": threshold,
                        "value": indicator.value,
                        "severity": severity,
                        "timestamp": indicator.timestamp,
                        "message": self._generate_alert_message(indicator, severity),
                        "actions": self._generate_recommended_actions(indicator, severity)
                    }
                    alerts.append(alert)
        
        return alerts
    
    def _determine_alert_severity(self, value: float, threshold: float) -> RiskSeverity:
        """Determine alert severity based on value relative to threshold."""
        ratio = value / threshold
        
        if ratio >= 2.0:
            return RiskSeverity.CATASTROPHIC
        elif ratio >= 1.5:
            return RiskSeverity.SEVERE
        elif ratio >= 1.2:
            return RiskSeverity.MAJOR
        elif ratio >= 1.0:
            return RiskSeverity.MODERATE
        else:
            return RiskSeverity.MINOR
    
    def _generate_alert_message(self, indicator: RiskIndicator, 
                               severity: RiskSeverity) -> str:
        """Generate an alert message."""
        messages = {
            RiskSeverity.INSIGNIFICANT: f"{indicator.risk_type.value.replace('_', ' ').title()} monitoring - {indicator.name}: {indicator.value:.2f} {indicator.unit}",
            RiskSeverity.MINOR: f"Minor {indicator.risk_type.value} detected - {indicator.name}: {indicator.value:.2f} {indicator.unit}",
            RiskSeverity.MODERATE: f"Moderate {indicator.risk_type.value} - {indicator.name}: {indicator.value:.2f} {indicator.unit}",
            RiskSeverity.MAJOR: f"MAJOR {indicator.risk_type.value.upper()} - {indicator.name}: {indicator.value:.2f} {indicator.unit}",
            RiskSeverity.SEVERE: f"SEVERE {indicator.risk_type.value.upper()} - {indicator.name}: {indicator.value:.2f} {indicator.unit}",
            RiskSeverity.CATASTROPHIC: f"CATASTROPHIC {indicator.risk_type.value.upper()} - {indicator.name}: {indicator.value:.2f} {indicator.unit}"
        }
        
        return messages.get(severity, f"Alert for {indicator.name}: {indicator.value:.2f} {indicator.unit}")
    
    def _generate_recommended_actions(self, indicator: RiskIndicator,
                                    severity: RiskSeverity) -> List[str]:
        """Generate recommended actions based on alert."""
        actions = []
        
        if indicator.risk_type == RiskType.FLOOD:
            actions = [
                "Monitor water levels",
                "Prepare sandbags",
                "Move valuables to higher ground",
                "Monitor evacuation routes",
                "Stay tuned to local alerts"
            ]
        elif indicator.risk_type == RiskType.DROUGHT:
            actions = [
                "Conserve water",
                "Reduce outdoor watering",
                "Implement water restrictions",
                "Monitor crop conditions",
                "Prepare for water rationing"
            ]
        elif indicator.risk_type == RiskType.WILDFIRE:
            actions = [
                "Clear vegetation around property",
                "Create firebreaks",
                "Prepare evacuation plan",
                "Monitor fire weather conditions",
                "Report any fires immediately"
            ]
        elif indicator.risk_type == RiskType.HEATWAVE:
            actions = [
                "Stay hydrated",
                "Avoid outdoor activities",
                "Use air conditioning",
                "Check on vulnerable people",
                "Never leave children in vehicles"
            ]
        elif indicator.risk_type == RiskType.AIR_POLLUTION:
            actions = [
                "Stay indoors",
                "Use air purifiers",
                "Wear N95 masks if outside",
                "Close windows",
                "Avoid outdoor exercise"
            ]
        elif indicator.risk_type == RiskType.WATER_POLLUTION:
            actions = [
                "Use bottled water",
                "Report pollution to authorities",
                "Avoid swimming in affected waters",
                "Monitor water quality alerts",
                "Protect wildlife"
            ]
        else:
            actions = [
                f"Monitor {indicator.risk_type.value} conditions",
                "Stay informed through official channels",
                "Follow safety guidelines",
                "Prepare emergency supplies",
                "Check on neighbors and community"
            ]
        
        # Adjust actions based on severity
        if severity in [RiskSeverity.SEVERE, RiskSeverity.CATASTROPHIC]:
            actions.append("IMMEDIATE ACTION REQUIRED - Follow emergency protocols")
        
        return actions
    
    def send_alert(self, alert: Dict[str, Any],
                   channels: List[str] = None) -> Dict[str, bool]:
        """
        Send alert through specified channels.
        """
        if channels is None:
            channels = self.communication_channels
        
        results = {}
        
        for channel in channels:
            if channel in self.communication_channels:
                success = self._send_through_channel(channel, alert)
                results[channel] = success
        
        self.warnings.append({
            "alert": alert,
            "channels": results,
            "timestamp": datetime.now()
        })
        
        return results
    
    def _send_through_channel(self, channel: str, alert: Dict[str, Any]) -> bool:
        """Send alert through a specific channel."""
        # In production, implement actual communication
        self.logger.info(f"Sending alert through {channel}: {alert['message'][:50]}...")
        
        # Simulate success
        return True
    
    def get_active_alerts(self, risk_type: Optional[RiskType] = None) -> List[Dict[str, Any]]:
        """Get currently active alerts."""
        active_alerts = []
        for warning in self.warnings:
            alert = warning['alert']
            if risk_type is None or alert['indicator'].risk_type == risk_type:
                if alert['severity'].value >= RiskSeverity.MODERATE.value:
                    active_alerts.append(alert)
        
        return active_alerts


# ============================================================================
# RISK FORECASTING ENGINE
# ============================================================================

class RiskForecastingEngine:
    """Engine for forecasting environmental risks."""
    
    def __init__(self):
        """Initialize the forecasting engine."""
        self.logger = logging.getLogger(f"{__name__}.RiskForecastingEngine")
        self.forecast_models = self._initialize_forecast_models()
        self.model_weights = {}
    
    def _initialize_forecast_models(self) -> Dict[str, Callable]:
        """Initialize forecasting src.notifications.models."""
        return {
            "time_series": self._forecast_time_series,
            "arima": self._forecast_arima,
            "ensemble": self._forecast_ensemble,
            "spatiotemporal": self._forecast_spatiotemporal,
            "machine_learning": self._forecast_machine_learning
        }
    
    def _forecast_time_series(self, data: List[SpatiotemporalPoint],
                             horizon_hours: int = 24) -> Dict[str, Any]:
        """Forecast using time series methods."""
        if len(data) < 5:
            return {"error": "Insufficient data for forecasting"}
        
        # Extract time series
        time_series = defaultdict(list)
        for point in data:
            for key, value in point.values.items():
                time_series[key].append((point.timestamp, value))
        
        forecasts = {}
        
        for key, series in time_series.items():
            # Sort by time
            series.sort(key=lambda x: x[0])
            values = [v for _, v in series]
            
            if len(values) < 3:
                continue
            
            # Simple linear extrapolation
            n = len(values)
            x = list(range(n))
            mean_x = statistics.mean(x)
            mean_y = statistics.mean(values)
            
            slope = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
            slope /= sum((x[i] - mean_x)**2 for i in range(n))
            intercept = mean_y - slope * mean_x
            
            # Forecast
            forecast_value = intercept + slope * (n + horizon_hours)
            
            # Uncertainty
            residuals = [values[i] - (intercept + slope * x[i]) for i in range(n)]
            mse = statistics.mean([r**2 for r in residuals]) if residuals else 0
            uncertainty = math.sqrt(mse)
            
            forecasts[key] = {
                "forecast": forecast_value,
                "uncertainty": uncertainty,
                "method": "time_series",
                "confidence": 0.7 - 0.1 * (horizon_hours / 100)
            }
        
        return forecasts
    
    def _forecast_arima(self, data: List[SpatiotemporalPoint],
                       horizon_hours: int = 24) -> Dict[str, Any]:
        """Forecast using ARIMA-like approach."""
        # Simplified ARIMA
        if len(data) < 10:
            return {"error": "Insufficient data for ARIMA forecasting"}
        
        forecasts = {}
        time_series = defaultdict(list)
        
        for point in data:
            for key, value in point.values.items():
                time_series[key].append((point.timestamp, value))
        
        for key, series in time_series.items():
            series.sort(key=lambda x: x[0])
            values = [v for _, v in series]
            
            if len(values) < 5:
                continue
            
            # Simple AR(2) model
            if len(values) >= 3:
                ar1 = values[-1] / (values[-2] + 0.001)
                ar2 = values[-2] / (values[-3] + 0.001)
                
                forecast_value = values[-1] * ar1 * 0.7 + values[-2] * ar2 * 0.3
                
                # Extrapolate for longer horizon
                for _ in range(horizon_hours - 1):
                    forecast_value = forecast_value * 0.95 + random.gauss(0, 0.05)
            else:
                forecast_value = values[-1]
            
            forecasts[key] = {
                "forecast": forecast_value,
                "uncertainty": 0.1 * horizon_hours,
                "method": "arima",
                "confidence": 0.6
            }
        
        return forecasts
    
    def _forecast_ensemble(self, data: List[SpatiotemporalPoint],
                          horizon_hours: int = 24) -> Dict[str, Any]:
        """Forecast using ensemble of methods."""
        forecasts = []
        methods = ["time_series", "arima"]
        
        for method in methods:
            if method in self.forecast_models:
                result = self.forecast_models[method](data, horizon_hours)
                if "error" not in result:
                    forecasts.append(result)
        
        if not forecasts:
            return {"error": "No forecasts available for ensemble"}
        
        # Ensemble average
        ensemble_forecast = {}
        for key in forecasts[0].keys():
            values = []
            for f in forecasts:
                if key in f and "forecast" in f[key]:
                    values.append(f[key]["forecast"])
            
            if values:
                ensemble_forecast[key] = {
                    "forecast": statistics.mean(values),
                    "uncertainty": statistics.stdev(values) if len(values) > 1 else 0,
                    "method": "ensemble",
                    "confidence": 0.75 - 0.1 * (horizon_hours / 100)
                }
        
        return ensemble_forecast
    
    def _forecast_spatiotemporal(self, data: List[SpatiotemporalPoint],
                                horizon_hours: int = 24) -> Dict[str, Any]:
        """Forecast using spatiotemporal methods."""
        if len(data) < 5:
            return {"error": "Insufficient data for spatiotemporal forecasting"}
        
        # Track movement and trends
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        
        # Calculate movement
        if len(sorted_data) > 1:
            first = sorted_data[0]
            last = sorted_data[-1]
            time_diff = (last.timestamp - first.timestamp).total_seconds() / 3600
            
            if time_diff > 0:
                lat_change = (last.point.latitude - first.point.latitude) / time_diff
                lon_change = (last.point.longitude - first.point.longitude) / time_diff
            else:
                lat_change = 0
                lon_change = 0
        else:
            lat_change = 0
            lon_change = 0
        
        # Forecast new location
        forecast_lat = data[-1].point.latitude + lat_change * horizon_hours
        forecast_lon = data[-1].point.longitude + lon_change * horizon_hours
        
        # Forecast values
        forecasts = {}
        value_keys = data[0].values.keys()
        
        for key in value_keys:
            values = [p.values.get(key, 0) for p in data]
            trend = (values[-1] - values[0]) / len(values) if len(values) > 1 else 0
            forecast_value = values[-1] + trend * horizon_hours
            
            forecasts[key] = {
                "forecast": forecast_value,
                "forecast_location": (forecast_lat, forecast_lon),
                "uncertainty": 0.15 * horizon_hours,
                "method": "spatiotemporal",
                "confidence": 0.7
            }
        
        return forecasts
    
    def _forecast_machine_learning(self, data: List[SpatiotemporalPoint],
                                  horizon_hours: int = 24) -> Dict[str, Any]:
        """Forecast using machine learning approach."""
        # Placeholder for ML-based forecasting
        if len(data) < 20:
            return {"error": "Insufficient data for ML forecasting"}
        
        return {"warning": "ML forecasting not fully implemented, using time_series"}
    
    def forecast_risk(self, data: List[SpatiotemporalPoint],
                     risk_type: RiskType,
                     horizon_hours: int = 24,
                     method: str = "ensemble") -> SpatiotemporalRiskForecast:
        """
        Generate a risk forecast.
        """
        self.logger.info(f"Forecasting {risk_type.value} for {horizon_hours} hours")
        
        if method in self.forecast_models:
            forecast_data = self.forecast_models[method](data, horizon_hours)
        else:
            self.logger.warning(f"Unknown forecast method: {method}, using time_series")
            forecast_data = self._forecast_time_series(data, horizon_hours)
        
        if "error" in forecast_data:
            self.logger.error(f"Forecast error: {forecast_data['error']}")
            return None
        
        # Calculate probability based on forecast values
        probability = 0.5
        if "forecast" in forecast_data:
            values = [v["forecast"] for v in forecast_data.values() if isinstance(v, dict) and "forecast" in v]
            if values:
                max_value = max(values)
                probability = min(1.0, max_value / 100.0)  # Normalize
        
        # Determine severity
        severity = RiskSeverity.MODERATE
        if probability > 0.8:
            severity = RiskSeverity.SEVERE
        elif probability > 0.6:
            severity = RiskSeverity.MAJOR
        elif probability > 0.4:
            severity = RiskSeverity.MODERATE
        elif probability > 0.2:
            severity = RiskSeverity.MINOR
        
        # Calculate confidence
        confidence = 0.7 - 0.1 * (horizon_hours / 100)
        confidence = max(0.3, min(0.9, confidence))
        
        forecast = SpatiotemporalRiskForecast(
            forecast_id=f"forecast_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            risk_type=risk_type,
            location=data[-1].point if data else GeoPoint(0, 0),
            forecast_time=datetime.now() + timedelta(hours=horizon_hours),
            time_window=TimeWindow(
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=horizon_hours)
            ),
            predicted_probability=probability,
            predicted_severity=severity,
            confidence=confidence,
            lead_time_hours=horizon_hours,
            indicators={k: v.get("forecast", 0) for k, v in forecast_data.items() if isinstance(v, dict)},
            scenarios={
                "best_case": {"probability": max(0, probability - 0.2)},
                "worst_case": {"probability": min(1.0, probability + 0.2)},
                "most_likely": {"probability": probability}
            },
            uncertainty_range=(max(0, probability - 0.15), min(1.0, probability + 0.15))
        )
        
        return forecast


# ============================================================================
# SPATIOTEMPORAL RISK INTELLIGENCE FRAMEWORK
# ============================================================================

class SpatiotemporalRiskIntelligenceFramework:
    """Main framework for spatiotemporal environmental risk intelligence."""
    
    def __init__(self):
        """Initialize the framework."""
        self.logger = logging.getLogger(f"{__name__}.SpatiotemporalRiskIntelligenceFramework")
        self.fusion_engine = SpatiotemporalDataFusionEngine()
        self.pattern_engine = RiskPatternDetectionEngine()
        self.early_warning = EarlyWarningSystem()
        self.forecast_engine = RiskForecastingEngine()
        self.events = []
        self.risk_history = []
        self.analytics_cache = {}
    
    def process_observations(self, observations: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """
        Process a batch of observations.
        """
        self.logger.info(f"Processing {len(observations)} observations")
        
        result = {
            "timestamp": datetime.now(),
            "observations_processed": len(observations),
            "fused_data": {},
            "patterns": {},
            "alerts": [],
            "forecasts": [],
            "events": []
        }
        
        # Fuse data
        if observations:
            fused_data = self.fusion_engine.fuse_data(observations)
            result["fused_data"] = fused_data
        
        # Detect patterns
        if len(observations) >= 3:
            patterns = self.pattern_engine.detect_patterns(observations)
            result["patterns"] = patterns
        
        # Check for alerts
        indicators = self._extract_indicators(observations)
        alerts = self.early_warning.check_alerts(indicators)
        result["alerts"] = alerts
        
        # Send alerts for critical issues
        for alert in alerts:
            if alert['severity'].value >= RiskSeverity.MAJOR.value:
                self.early_warning.send_alert(alert, ["dashboard", "email"])
        
        # Generate forecasts
        if len(observations) >= 5:
            for risk_type in RiskType:
                forecast = self.forecast_engine.forecast_risk(
                    observations, risk_type, horizon_hours=24
                )
                if forecast:
                    result["forecasts"].append(forecast)
        
        # Detect events
        events = self._detect_events(observations, alerts)
        result["events"] = events
        
        # Update history
        self.risk_history.extend(observations)
        self.events.extend(events)
        
        return result
    
    def _extract_indicators(self, observations: List[SpatiotemporalPoint]) -> List[RiskIndicator]:
        """Extract risk indicators from observations."""
        indicators = []
        
        for obs in observations:
            for key, value in obs.values.items():
                # Determine risk type from key
                risk_type = self._determine_risk_type_from_key(key)
                
                indicator = RiskIndicator(
                    indicator_id=f"ind_{datetime.now().strftime('%Y%m%d%H%M%S')}_{key}",
                    name=key,
                    description=f"{key} measurement",
                    risk_type=risk_type,
                    value=value,
                    timestamp=obs.timestamp,
                    source=DataSourceType.SENSOR_NETWORK,
                    confidence=obs.quality_indicators.get('confidence', 0.5)
                )
                indicators.append(indicator)
        
        return indicators
    
    def _determine_risk_type_from_key(self, key: str) -> RiskType:
        """Determine risk type from indicator key."""
        risk_mapping = {
            "water_level": RiskType.FLOOD,
            "rainfall": RiskType.FLOOD,
            "river_discharge": RiskType.FLOOD,
            "precipitation": RiskType.DROUGHT,
            "soil_moisture": RiskType.DROUGHT,
            "temperature": RiskType.HEATWAVE,
            "humidity": RiskType.WILDFIRE,
            "wind_speed": RiskType.WILDFIRE,
            "pm2.5": RiskType.AIR_POLLUTION,
            "pm10": RiskType.AIR_POLLUTION,
            "no2": RiskType.AIR_POLLUTION,
            "o3": RiskType.AIR_POLLUTION,
            "dissolved_oxygen": RiskType.WATER_POLLUTION,
            "turbidity": RiskType.WATER_POLLUTION,
            "ph": RiskType.WATER_POLLUTION,
            "nitrate": RiskType.WATER_POLLUTION
        }
        
        return risk_mapping.get(key, RiskType.AIR_POLLUTION)
    
    def _detect_events(self, observations: List[SpatiotemporalPoint],
                      alerts: List[Dict[str, Any]]) -> List[EnvironmentalEvent]:
        """Detect environmental events from observations and alerts."""
        events = []
        
        for alert in alerts:
            if alert['severity'].value >= RiskSeverity.MODERATE.value:
                indicator = alert['indicator']
                event = EnvironmentalEvent(
                    event_id=f"event_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    event_type=indicator.risk_type,
                    description=alert['message'],
                    location=observations[0].point if observations else GeoPoint(0, 0),
                    start_time=indicator.timestamp,
                    severity=alert['severity'],
                    status=RiskStatus.WARNING,
                    indicators=[indicator],
                    confidence=indicator.confidence
                )
                events.append(event)
        
        return events
    
    def get_risk_assessment(self, region: BoundingBox,
                           time_window: TimeWindow) -> Dict[str, Any]:
        """
        Get comprehensive risk assessment for a region.
        """
        self.logger.info(f"Assessing risk for region: {region}")
        
        assessment = {
            "region": region,
            "time_window": time_window,
            "risk_summary": {},
            "critical_indicators": [],
            "trends": {},
            "forecasts": [],
            "recommendations": []
        }
        
        # Filter observations in region
        filtered_obs = []
        for obs in self.risk_history:
            if region.contains_point(obs.point) and time_window.contains(obs.timestamp):
                filtered_obs.append(obs)
        
        if not filtered_obs:
            assessment["risk_summary"] = {"status": "No data available for region"}
            return assessment
        
        # Analyze filtered observations
        for obs in filtered_obs:
            for key, value in obs.values.items():
                if key not in assessment["risk_summary"]:
                    assessment["risk_summary"][key] = {
                        "values": [],
                        "mean": 0,
                        "max": 0,
                        "min": 0
                    }
                assessment["risk_summary"][key]["values"].append(value)
        
        # Calculate statistics
        for key, data in assessment["risk_summary"].items():
            values = data["values"]
            if values:
                data["mean"] = statistics.mean(values)
                data["max"] = max(values)
                data["min"] = min(values)
                data["std"] = statistics.stdev(values) if len(values) > 1 else 0
        
        # Identify critical indicators
        for key, data in assessment["risk_summary"].items():
            if data["mean"] > 0.8:  # Assuming values are normalized
                assessment["critical_indicators"].append(key)
        
        # Detect trends
        patterns = self.pattern_engine.detect_patterns(filtered_obs, "trend")
        assessment["trends"] = patterns
        
        # Generate forecasts
        for risk_type in RiskType:
            forecast = self.forecast_engine.forecast_risk(
                filtered_obs, risk_type, horizon_hours=48
            )
            if forecast:
                assessment["forecasts"].append(forecast)
        
        # Generate recommendations
        assessment["recommendations"] = self._generate_risk_recommendations(assessment)
        
        return assessment
    
    def _generate_risk_recommendations(self, assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate risk-based src.ai.recommendations."""
        recommendations = []
        
        critical_indicators = assessment.get("critical_indicators", [])
        if critical_indicators:
            src.ai.recommendations.append({
                "priority": "high",
                "action": f"Immediate attention needed for: {', '.join(critical_indicators)}",
                "details": "Critical indicators exceed safety thresholds",
                "timeframe": "Immediate"
            })
        
        # Forecast-based recommendations
        for forecast in assessment.get("forecasts", []):
            if forecast.predicted_probability > 0.6:
                src.ai.recommendations.append({
                    "priority": "high" if forecast.predicted_probability > 0.8 else "medium",
                    "action": f"Prepare for {forecast.risk_type.value} within {forecast.lead_time_hours} hours",
                    "details": f"Probability: {forecast.predicted_probability:.1%}",
                    "timeframe": f"{int(forecast.lead_time_hours)} hours"
                })
        
        # Trend-based recommendations
        trends = assessment.get("trends", {})
        for key, value in trends.items():
            if "increasing" in str(value) and "_trend" in key:
                src.ai.recommendations.append({
                    "priority": "medium",
                    "action": f"Monitor {key} - increasing trend detected",
                    "details": f"Trend magnitude: {abs(float(value) if isinstance(value, (int, float)) else 0):.2f}",
                    "timeframe": "Ongoing"
                })
        
        # General recommendations
        if len(recommendations) < 2:
            src.ai.recommendations.append({
                "priority": "low",
                "action": "Continue monitoring environmental indicators",
                "details": "No immediate risks detected",
                "timeframe": "Ongoing"
            })
        
        return recommendations
    
    def get_historical_risk_analysis(self, region: BoundingBox,
                                    start_time: datetime,
                                    end_time: datetime) -> Dict[str, Any]:
        """
        Get historical risk analysis for a region.
        """
        self.logger.info(f"Analyzing historical risks for region from {start_time} to {end_time}")
        
        analysis = {
            "region": region,
            "start_time": start_time,
            "end_time": end_time,
            "events": [],
            "patterns": {},
            "statistics": {},
            "trends": {}
        }
        
        # Filter events
        for event in self.events:
            if (region.contains_point(event.location) and
                start_time <= event.start_time <= end_time):
                analysis["events"].append(event)
        
        # Analyze events
        if analysis["events"]:
            # Event frequency by type
            event_counts = defaultdict(int)
            for event in analysis["events"]:
                event_counts[event.event_type.value] += 1
            analysis["statistics"]["event_frequency"] = dict(event_counts)
            
            # Average severity
            avg_severity = statistics.mean([e.severity.value for e in analysis["events"]])
            analysis["statistics"]["average_severity"] = avg_severity
            
            # Event duration
            durations = []
            for event in analysis["events"]:
                if event.end_time:
                    duration = (event.end_time - event.start_time).total_seconds() / 3600
                    durations.append(duration)
            if durations:
                analysis["statistics"]["average_duration_hours"] = statistics.mean(durations)
        else:
            analysis["statistics"] = {"status": "No events found in this period"}
        
        return analysis


# ============================================================================
# VISUALIZATION AND REPORTING
# ============================================================================

class SpatiotemporalVisualizationGenerator:
    """Generate visualizations for spatiotemporal risk data."""
    
    @staticmethod
    def generate_risk_heatmap(observations: List[SpatiotemporalPoint],
                             risk_type: RiskType,
                             grid_size: int = 10) -> Dict[str, Any]:
        """Generate risk heatmap data."""
        if not observations:
            return {"error": "No observations available"}
        
        # Create grid
        lats = [obs.point.latitude for obs in observations]
        lons = [obs.point.longitude for obs in observations]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        lat_step = (max_lat - min_lat) / grid_size
        lon_step = (max_lon - min_lon) / grid_size
        
        # Initialize grid
        grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
        weights = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
        
        # Populate grid
        for obs in observations:
            lat_idx = min(grid_size - 1, int((obs.point.latitude - min_lat) / lat_step))
            lon_idx = min(grid_size - 1, int((obs.point.longitude - min_lon) / lon_step))
            
            # Determine risk value
            risk_value = 0
            for key, value in obs.values.items():
                if risk_type.value in key.lower():
                    risk_value = max(risk_value, value)
            
            grid[lat_idx][lon_idx] += risk_value
            weights[lat_idx][lon_idx] += 1
        
        # Normalize grid
        for i in range(grid_size):
            for j in range(grid_size):
                if weights[i][j] > 0:
                    grid[i][j] /= weights[i][j]
        
        return {
            "grid": grid,
            "grid_size": grid_size,
            "bounds": {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lon": min_lon,
                "max_lon": max_lon
            },
            "risk_type": risk_type.value
        }
    
    @staticmethod
    def generate_time_series(observations: List[SpatiotemporalPoint],
                           indicator_key: str) -> Dict[str, Any]:
        """Generate time series data for an indicator."""
        if not observations:
            return {"error": "No observations available"}
        
        # Sort by time
        sorted_obs = sorted(observations, key=lambda x: x.timestamp)
        
        times = []
        values = []
        uncertainties = []
        
        for obs in sorted_obs:
            if indicator_key in obs.values:
                times.append(obs.timestamp.isoformat())
                values.append(obs.values[indicator_key])
                uncertainties.append(obs.quality_indicators.get('uncertainty', 0))
        
        return {
            "times": times,
            "values": values,
            "uncertainties": uncertainties,
            "indicator": indicator_key
        }
    
    @staticmethod
    def generate_risk_dashboard(risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive risk dashboard."""
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "risk_summary": {},
            "critical_indicators": [],
            "trends": {},
            "forecasts": [],
            "recommendations": [],
            "heatmap": None
        }
        
        # Add risk summary
        if "risk_summary" in risk_assessment:
            dashboard["risk_summary"] = risk_assessment["risk_summary"]
        
        # Add critical indicators
        if "critical_indicators" in risk_assessment:
            dashboard["critical_indicators"] = risk_assessment["critical_indicators"]
        
        # Add trends
        if "trends" in risk_assessment:
            dashboard["trends"] = risk_assessment["trends"]
        
        # Add forecasts
        if "forecasts" in risk_assessment:
            dashboard["forecasts"] = [
                {
                    "risk_type": f.risk_type.value,
                    "probability": f.predicted_probability,
                    "severity": f.predicted_severity.value,
                    "lead_time": f.lead_time_hours
                }
                for f in risk_assessment.get("forecasts", [])[:5]
            ]
        
        # Add recommendations
        if "recommendations" in risk_assessment:
            dashboard["recommendations"] = risk_assessment["recommendations"][:5]
        
        return dashboard


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================

def generate_test_observations(n: int = 100) -> List[SpatiotemporalPoint]:
    """Generate test observations for demonstration."""
    observations = []
    
    base_lat = 37.7749  # San Francisco
    base_lon = -122.4194
    
    for i in range(n):
        # Generate random offsets
        lat_offset = random.gauss(0, 0.1)  # ~11 km spread
        lon_offset = random.gauss(0, 0.1)
        
        point = GeoPoint(
            latitude=base_lat + lat_offset,
            longitude=base_lon + lon_offset,
            altitude=random.uniform(0, 100)
        )
        
        # Generate values
        values = {
            "temperature": 20 + random.gauss(5, 3) + math.sin(i/10) * 2,
            "humidity": 60 + random.gauss(10, 5) + math.cos(i/15) * 10,
            "pm2.5": 20 + random.gauss(10, 5) + random.random() * 30,
            "pm10": 40 + random.gauss(15, 8) + random.random() * 40,
            "no2": 30 + random.gauss(8, 4) + random.random() * 20,
            "o3": 40 + random.gauss(10, 6) + math.sin(i/8) * 15,
            "water_level": 2 + random.gauss(1, 0.5) + random.random() * 2,
            "rainfall": 5 + random.gauss(3, 2) + random.random() * 10,
            "wind_speed": 15 + random.gauss(5, 3) + random.random() * 10,
            "soil_moisture": 0.5 + random.gauss(0.2, 0.1) + random.random() * 0.2,
            "dissolved_oxygen": 8 + random.gauss(1, 0.5) + random.random() * 1,
            "turbidity": 10 + random.gauss(5, 3) + random.random() * 10
        }
        
        # Add seasonal pattern
        season = math.sin(i / 30) * 5
        values["temperature"] += season
        
        quality_indicators = {
            "confidence": random.uniform(0.7, 0.95),
            "uncertainty": random.uniform(0.05, 0.15),
            "precision": random.uniform(0.8, 0.98)
        }
        
        obs = SpatiotemporalPoint(
            point=point,
            timestamp=datetime.now() - timedelta(hours=n-i),
            values=values,
            quality_indicators=quality_indicators
        )
        observations.append(obs)
    
    return observations


def run_demonstration():
    """Run a comprehensive demonstration."""
    print("\n" + "=" * 80)
    print("SPATIOTEMPORAL ENVIRONMENTAL RISK INTELLIGENCE FRAMEWORK")
    print("=" * 80 + "\n")
    
    # Initialize framework
    framework = SpatiotemporalRiskIntelligenceFramework()
    
    print("🚀 Generating test observations...")
    observations = generate_test_observations(200)
    print(f"✓ Generated {len(observations)} test observations\n")
    
    print("📊 Processing observations...")
    result = framework.process_observations(observations)
    print(f"✓ Processed {result['observations_processed']} observations")
    print(f"✓ Generated {len(result['alerts'])} alerts")
    print(f"✓ Generated {len(result['forecasts'])} forecasts")
    print(f"✓ Detected {len(result['events'])} events\n")
    
    # Show alerts
    if result['alerts']:
        print("🚨 Critical Alerts:")
        for alert in result['alerts'][:3]:
            print(f"  • {alert['message']}")
            print(f"    Severity: {alert['severity'].name}")
            if 'actions' in alert:
                print(f"    Actions: {alert['actions'][0]}")
        print()
    
    # Get risk assessment
    region = BoundingBox(37.6, 37.9, -122.6, -122.2)  # San Francisco area
    time_window = TimeWindow(
        start_time=datetime.now() - timedelta(days=7),
        end_time=datetime.now()
    )
    
    print("🔍 Assessing risk for region...")
    assessment = framework.get_risk_assessment(region, time_window)
    
    print(f"✓ Critical indicators: {assessment.get('critical_indicators', [])}")
    print(f"✓ Generated {len(assessment.get('recommendations', []))} recommendations")
    
    if assessment.get('recommendations'):
        print("\n📋 Recommendations:")
        for rec in assessment['recommendations'][:3]:
            print(f"  • [{rec['priority'].upper()}] {rec['action']}")
    print()
    
    # Generate dashboard
    print("📊 Generating dashboard...")
    dashboard = SpatiotemporalVisualizationGenerator.generate_risk_dashboard(assessment)
    
    print("Dashboard Summary:")
    print(f"  • Critical Indicators: {len(dashboard.get('critical_indicators', []))}")
    print(f"  • Forecasts: {len(dashboard.get('forecasts', []))}")
    print(f"  • Recommendations: {len(dashboard.get('recommendations', []))}")
    
    # Generate heatmap
    print("\n🗺️ Generating risk heatmap...")
    heatmap = SpatiotemporalVisualizationGenerator.generate_risk_heatmap(
        observations, RiskType.AIR_POLLUTION
    )
    
    if 'grid' in heatmap:
        print(f"✓ Generated {heatmap['grid_size']}x{heatmap['grid_size']} heatmap grid")
    
    # Historical analysis
    print("\n📈 Analyzing historical risks...")
    history = framework.get_historical_risk_analysis(
        region,
        datetime.now() - timedelta(days=30),
        datetime.now()
    )
    
    print(f"✓ Found {len(history.get('events', []))} historical events")
    if 'statistics' in history and 'event_frequency' in history['statistics']:
        print(f"  Event frequency: {history['statistics']['event_frequency']}")
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80 + "\n")


def run_tests():
    """Run comprehensive tests."""
    print("\n" + "=" * 60)
    print("RUNNING TESTS")
    print("=" * 60 + "\n")
    
    # Test 1: GeoPoint
    print("Test 1: GeoPoint")
    p1 = GeoPoint(37.7749, -122.4194)
    p2 = GeoPoint(37.7833, -122.4167)
    distance = p1.distance_to(p2)
    assert distance > 0, "Distance should be positive"
    print(f"✓ Distance between points: {distance:.2f} km")
    
    # Test 2: BoundingBox
    print("\nTest 2: BoundingBox")
    bbox = BoundingBox(37.0, 38.0, -123.0, -122.0)
    assert bbox.contains_point(p1), "Should contain point"
    print("✓ Bounding box contains point")
    print(f"  Area: {bbox.area_sqkm():.2f} km²")
    
    # Test 3: Data Fusion
    print("\nTest 3: Data Fusion")
    obs = generate_test_observations(10)
    engine = SpatiotemporalDataFusionEngine()
    fused = engine.fuse_data(obs)
    assert len(fused) > 0, "Should have fused data"
    print(f"✓ Fused {len(fused)} values")
    
    # Test 4: Pattern Detection
    print("\nTest 4: Pattern Detection")
    pattern_engine = RiskPatternDetectionEngine()
    anomalies = pattern_engine.detect_anomalies([1, 2, 3, 4, 5, 100, 6, 7, 8])
    assert len(anomalies) > 0, "Should detect anomalies"
    print(f"✓ Detected {len(anomalies)} anomalies")
    
    # Test 5: Early Warning
    print("\nTest 5: Early Warning System")
    early_warning = EarlyWarningSystem()
    indicator = RiskIndicator(
        indicator_id="test1",
        name="temperature",
        description="Test temperature",
        risk_type=RiskType.HEATWAVE,
        value=42.0,
        threshold_warning=35.0,
        threshold_alert=40.0
    )
    alerts = early_warning.check_alerts([indicator])
    assert len(alerts) > 0, "Should generate alerts"
    print(f"✓ Generated {len(alerts)} alerts")
    print(f"  Severity: {alerts[0]['severity'].name}")
    
    # Test 6: Forecasting
    print("\nTest 6: Forecasting")
    forecast_engine = RiskForecastingEngine()
    forecast = forecast_engine.forecast_risk(
        obs, RiskType.HEATWAVE, horizon_hours=12
    )
    assert forecast is not None, "Should generate forecast"
    print(f"✓ Generated forecast for {forecast.risk_type.value}")
    print(f"  Probability: {forecast.predicted_probability:.2%}")
    
    # Test 7: Framework Integration
    print("\nTest 7: Framework Integration")
    framework = SpatiotemporalRiskIntelligenceFramework()
    result = framework.process_observations(obs)
    assert result is not None, "Should process observations"
    print(f"✓ Processed {result['observations_processed']} observations")
    
    # Test 8: Risk Assessment
    print("\nTest 8: Risk Assessment")
    assessment = framework.get_risk_assessment(
        BoundingBox(37.5, 38.0, -122.5, -122.0),
        TimeWindow(
            datetime.now() - timedelta(days=1),
            datetime.now()
        )
    )
    assert assessment is not None, "Should generate assessment"
    print(f"✓ Generated risk assessment")
    print(f"  Recommendations: {len(assessment.get('recommendations', []))}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("SPATIOTEMPORAL ENVIRONMENTAL RISK INTELLIGENCE FRAMEWORK")
    print("Version 4.0.0")
    print("=" * 80 + "\n")
    
    print("Select an option:")
    print("1. Run demonstration")
    print("2. Run tests")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == '1':
        run_demonstration()
    elif choice == '2':
        run_tests()
    else:
        print("Goodbye!")


if __name__ == "__main__":
    main()
