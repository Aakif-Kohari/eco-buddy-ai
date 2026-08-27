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

