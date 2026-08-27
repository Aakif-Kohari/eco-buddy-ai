"""
src.lifestyle.travel_comparison_tool.py
====================================
Travel Choices Comparison Tool
Version: 1.0.0

This module provides comprehensive journey comparison functionality including:
- Environmental impact assessment of different transportation modes
- Distance-based carbon emissions calculations
- Travel time and cost comparisons
- Multi-modal journey planning
- Visual-friendly comparison outputs

Author: Carbon Footprint Team
Date: 2026-08-27
"""

import json
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TransportationMode(Enum):
    """Enumeration of transportation modes."""
    WALKING = "walking"
    CYCLING = "cycling"
    ELECTRIC_BICYCLE = "electric_bicycle"
    CAR_PETROL = "car_petrol"
    CAR_DIESEL = "car_diesel"
    CAR_HYBRID = "car_hybrid"
    CAR_ELECTRIC = "car_electric"
    CAR_PLUGIN_HYBRID = "car_plugin_hybrid"
    MOTORCYCLE_PETROL = "motorcycle_petrol"
    MOTORCYCLE_ELECTRIC = "motorcycle_electric"
    BUS_DIESEL = "bus_diesel"
    BUS_ELECTRIC = "bus_electric"
    TRAIN_DIESEL = "train_diesel"
    TRAIN_ELECTRIC = "train_electric"
    HIGH_SPEED_RAIL = "high_speed_rail"
    METRO_SUBWAY = "metro_subway"
    TRAM_LIGHT_RAIL = "tram_light_rail"
    DOMESTIC_FLIGHT = "domestic_flight"
    INTERNATIONAL_FLIGHT = "international_flight"
    FERRY = "ferry"
    HIGH_SPEED_FERRY = "high_speed_ferry"
    RIDE_SHARE = "ride_share"
    CARPOOL = "carpool"
    VANPOOL = "vanpool"
    SCOOTER_SHARE = "scooter_share"
    BIKE_SHARE = "bike_share"
    TAXI = "taxi"
    RIDE_HAILING_ELECTRIC = "ride_hailing_electric"
    RIDE_HAILING_HYBRID = "ride_hailing_hybrid"


class JourneyPurpose(Enum):
    """Enumeration of journey purposes."""
    COMMUTING = "commuting"
    LEISURE = "leisure"
    BUSINESS = "business"
    SHOPPING = "shopping"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    SOCIAL = "social"
    TOURISM = "tourism"
    EMERGENCY = "emergency"
    FREIGHT = "freight"


@dataclass
class TransportEmissionFactor:
    """Data class for transportation emission factors."""
    mode: TransportationMode
    co2_per_km_kg: float
    co2_per_hour_kg: float
    occupancy_factor: float = 1.0
    emission_factor_year: int = 2024
    source: str = "default"
    confidence_level: float = 0.85
    additional_ghg: Dict[str, float] = field(default_factory=dict)
    energy_consumption_kwh_km: Optional[float] = None
    fuel_efficiency_l_km: Optional[float] = None


@dataclass
class JourneySegment:
    """Data class for a journey segment."""
    start_location: str
    end_location: str
    distance_km: float
    duration_minutes: float
    mode: TransportationMode
    cost_usd: float = 0.0
    road_conditions: str = "normal"
    terrain_type: str = "mixed"
    elevation_change_m: float = 0.0
    weather_conditions: str = "clear"
    traffic_conditions: str = "normal"
    occupancy: int = 1
    emission_factor: Optional[TransportEmissionFactor] = None


@dataclass
class JourneyComparison:
    """Data class for journey comparison results."""
    journey_id: str
    segments: List[JourneySegment]
    total_distance_km: float
    total_duration_minutes: float
    total_co2_kg: float
    total_cost_usd: float
    emission_per_km_kg: float
    emission_per_hour_kg: float
    cost_per_km_usd: float
    cost_per_hour_usd: float
    comparison_date: datetime
    primary_mode: TransportationMode
    secondary_modes: List[TransportationMode] = field(default_factory=list)
    efficiency_score: float = 0.0
    environmental_score: float = 0.0
    cost_score: float = 0.0
    time_score: float = 0.0
    comfort_score: float = 0.5
    reliability_score: float = 0.5
    recommendations: List[str] = field(default_factory=list)


@dataclass
class JourneySummary:
    """Data class for aggregated journey summary."""
    total_journeys: int
    total_distance_km: float
    total_duration_hours: float
    total_co2_emissions_kg: float
    total_cost_usd: float
    average_co2_per_km_kg: float
    average_co2_per_hour_kg: float
    average_cost_per_km_usd: float
    mode_distribution: Dict[TransportationMode, float]
    period_start: datetime
    period_end: datetime
    environmental_impact_rating: str
    recommendations: List[str] = field(default_factory=list)


class EmissionFactorDatabase:
    """
    Database of emission factors for different transportation modes.
    """
    
    def __init__(self):
        self._emission_factors = self._initialize_emission_factors()
        self._last_updated = datetime.now()
    
    def _initialize_emission_factors(self) -> Dict[TransportationMode, TransportEmissionFactor]:
        """
        Initializes emission factors for all transportation modes.
        
        Returns:
            Dictionary mapping modes to emission factors
        """
        factors = {}
        
        # Walking and cycling have zero direct emissions
        factors[TransportationMode.WALKING] = TransportEmissionFactor(
            mode=TransportationMode.WALKING,
            co2_per_km_kg=0.0,
            co2_per_hour_kg=0.0,
            occupancy_factor=1.0,
            source="IPCC Guidelines, 2024"
        )
        
        factors[TransportationMode.CYCLING] = TransportEmissionFactor(
            mode=TransportationMode.CYCLING,
            co2_per_km_kg=0.0,
            co2_per_hour_kg=0.0,
            occupancy_factor=1.0,
            source="IPCC Guidelines, 2024"
        )
        
        factors[TransportationMode.ELECTRIC_BICYCLE] = TransportEmissionFactor(
            mode=TransportationMode.ELECTRIC_BICYCLE,
            co2_per_km_kg=0.012,
            co2_per_hour_kg=0.025,
            occupancy_factor=1.0,
            source="EU E-bike Study, 2023",
            energy_consumption_kwh_km=0.012
        )
        
        # Cars
        factors[TransportationMode.CAR_PETROL] = TransportEmissionFactor(
            mode=TransportationMode.CAR_PETROL,
            co2_per_km_kg=0.180,
            co2_per_hour_kg=2.160,
            occupancy_factor=0.6,
            source="US EPA, 2024",
            fuel_efficiency_l_km=0.075
        )
        
        factors[TransportationMode.CAR_DIESEL] = TransportEmissionFactor(
            mode=TransportationMode.CAR_DIESEL,
            co2_per_km_kg=0.155,
            co2_per_hour_kg=1.860,
            occupancy_factor=0.6,
            source="US EPA, 2024",
            fuel_efficiency_l_km=0.065
        )
        
        factors[TransportationMode.CAR_HYBRID] = TransportEmissionFactor(
            mode=TransportationMode.CAR_HYBRID,
            co2_per_km_kg=0.095,
            co2_per_hour_kg=1.140,
            occupancy_factor=0.6,
            source="US EPA, 2024",
            fuel_efficiency_l_km=0.045
        )
        
        factors[TransportationMode.CAR_ELECTRIC] = TransportEmissionFactor(
            mode=TransportationMode.CAR_ELECTRIC,
            co2_per_km_kg=0.035,
            co2_per_hour_kg=0.420,
            occupancy_factor=0.6,
            source="US EPA, 2024",
            energy_consumption_kwh_km=0.200
        )
        
        factors[TransportationMode.CAR_PLUGIN_HYBRID] = TransportEmissionFactor(
            mode=TransportationMode.CAR_PLUGIN_HYBRID,
            co2_per_km_kg=0.060,
            co2_per_hour_kg=0.720,
            occupancy_factor=0.6,
            source="US EPA, 2024",
            energy_consumption_kwh_km=0.160
        )
        
        factors[TransportationMode.MOTORCYCLE_PETROL] = TransportEmissionFactor(
            mode=TransportationMode.MOTORCYCLE_PETROL,
            co2_per_km_kg=0.090,
            co2_per_hour_kg=1.080,
            occupancy_factor=0.7,
            source="EU Motorcycle Study, 2023",
            fuel_efficiency_l_km=0.040
        )
        
        factors[TransportationMode.MOTORCYCLE_ELECTRIC] = TransportEmissionFactor(
            mode=TransportationMode.MOTORCYCLE_ELECTRIC,
            co2_per_km_kg=0.020,
            co2_per_hour_kg=0.240,
            occupancy_factor=0.7,
            source="EU Motorcycle Study, 2023",
            energy_consumption_kwh_km=0.100
        )
        
        # Bus
        factors[TransportationMode.BUS_DIESEL] = TransportEmissionFactor(
            mode=TransportationMode.BUS_DIESEL,
            co2_per_km_kg=0.820,
            co2_per_hour_kg=9.840,
            occupancy_factor=0.5,
            source="US DOT, 2024",
            fuel_efficiency_l_km=0.350
        )
        
        factors[TransportationMode.BUS_ELECTRIC] = TransportEmissionFactor(
            mode=TransportationMode.BUS_ELECTRIC,
            co2_per_km_kg=0.150,
            co2_per_hour_kg=1.800,
            occupancy_factor=0.5,
            source="US DOT, 2024",
            energy_consumption_kwh_km=1.100
        )
        
        # Train
        factors[TransportationMode.TRAIN_DIESEL] = TransportEmissionFactor(
            mode=TransportationMode.TRAIN_DIESEL,
            co2_per_km_kg=0.120,
            co2_per_hour_kg=1.440,
            occupancy_factor=0.4,
            source="EU Rail Study, 2023",
            fuel_efficiency_l_km=0.050
        )
        
        factors[TransportationMode.TRAIN_ELECTRIC] = TransportEmissionFactor(
            mode=TransportationMode.TRAIN_ELECTRIC,
            co2_per_km_kg=0.025,
            co2_per_hour_kg=0.300,
            occupancy_factor=0.4,
            source="EU Rail Study, 2023",
            energy_consumption_kwh_km=0.180
        )
        
        factors[TransportationMode.HIGH_SPEED_RAIL] = TransportEmissionFactor(
            mode=TransportationMode.HIGH_SPEED_RAIL,
            co2_per_km_kg=0.035,
            co2_per_hour_kg=0.420,
            occupancy_factor=0.5,
            source="UIC, 2024",
            energy_consumption_kwh_km=0.250
        )
        
        factors[TransportationMode.METRO_SUBWAY] = TransportEmissionFactor(
            mode=TransportationMode.METRO_SUBWAY,
            co2_per_km_kg=0.020,
            co2_per_hour_kg=0.240,
            occupancy_factor=0.6,
            source="UITP, 2024",
            energy_consumption_kwh_km=0.140
        )
        
        factors[TransportationMode.TRAM_LIGHT_RAIL] = TransportEmissionFactor(
            mode=TransportationMode.TRAM_LIGHT_RAIL,
            co2_per_km_kg=0.030,
            co2_per_hour_kg=0.360,
            occupancy_factor=0.5,
            source="UITP, 2024",
            energy_consumption_kwh_km=0.200
        )
        
        # Aviation
        factors[TransportationMode.DOMESTIC_FLIGHT] = TransportEmissionFactor(
            mode=TransportationMode.DOMESTIC_FLIGHT,
            co2_per_km_kg=0.250,
            co2_per_hour_kg=0.175,
            occupancy_factor=0.8,
            source="ICAO, 2024",
            additional_ghg={"NOx": 0.00025, "contrail": 0.00010}
        )
        
        factors[TransportationMode.INTERNATIONAL_FLIGHT] = TransportEmissionFactor(
            mode=TransportationMode.INTERNATIONAL_FLIGHT,
            co2_per_km_kg=0.300,
            co2_per_hour_kg=0.210,
            occupancy_factor=0.82,
            source="ICAO, 2024",
            additional_ghg={"NOx": 0.00030, "contrail": 0.00015}
        )
        
        # Water transport
        factors[TransportationMode.FERRY] = TransportEmissionFactor(
            mode=TransportationMode.FERRY,
            co2_per_km_kg=0.180,
            co2_per_hour_kg=2.160,
            occupancy_factor=0.5,
            source="IMO, 2024",
            fuel_efficiency_l_km=0.080
        )
        
        factors[TransportationMode.HIGH_SPEED_FERRY] = TransportEmissionFactor(
            mode=TransportationMode.HIGH_SPEED_FERRY,
            co2_per_km_kg=0.250,
            co2_per_hour_kg=3.000,
            occupancy_factor=0.5,
            source="IMO, 2024",
            fuel_efficiency_l_km=0.120
        )
        
        # Ride sharing
        factors[TransportationMode.RIDE_SHARE] = TransportEmissionFactor(
            mode=TransportationMode.RIDE_SHARE,
            co2_per_km_kg=0.120,
            co2_per_hour_kg=1.440,
            occupancy_factor=0.3,
            source="Industry Average, 2024"
        )
        
        factors[TransportationMode.CARPOOL] = TransportEmissionFactor(
            mode=TransportationMode.CARPOOL,
            co2_per_km_kg=0.060,
            co2_per_hour_kg=0.720,
            occupancy_factor=0.8,
            source="Industry Average, 2024"
        )
        
        factors[TransportationMode.VANPOOL] = TransportEmissionFactor(
            mode=TransportationMode.VANPOOL,
            co2_per_km_kg=0.080,
            co2_per_hour_kg=0.960,
            occupancy_factor=0.7,
            source="Industry Average, 2024"
        )
        
        factors[TransportationMode.SCOOTER_SHARE] = TransportEmissionFactor(
            mode=TransportationMode.SCOOTER_SHARE,
            co2_per_km_kg=0.010,
            co2_per_hour_kg=0.120,
            occupancy_factor=0.9,
            source="Industry Average, 2024"
        )
        
        factors[TransportationMode.BIKE_SHARE] = TransportEmissionFactor(
            mode=TransportationMode.BIKE_SHARE,
            co2_per_km_kg=0.000,
            co2_per_hour_kg=0.000,
            occupancy_factor=0.9,
            source="Industry Average, 2024"
        )
        
        factors[TransportationMode.TAXI] = TransportEmissionFactor(
            mode=TransportationMode.TAXI,
            co2_per_km_kg=0.200,
            co2_per_hour_kg=2.400,
            occupancy_factor=0.4,
            source="Industry Average, 2024"
        )
        
        factors[TransportationMode.RIDE_HAILING_ELECTRIC] = TransportEmissionFactor(
            mode=TransportationMode.RIDE_HAILING_ELECTRIC,
            co2_per_km_kg=0.040,
            co2_per_hour_kg=0.480,
            occupancy_factor=0.4,
            source="Industry Average, 2024"
        )
        
        factors[TransportationMode.RIDE_HAILING_HYBRID] = TransportEmissionFactor(
            mode=TransportationMode.RIDE_HAILING_HYBRID,
            co2_per_km_kg=0.080,
            co2_per_hour_kg=0.960,
            occupancy_factor=0.4,
            source="Industry Average, 2024"
        )
        
        return factors
    
    def get_emission_factor(self, mode: TransportationMode) -> Optional[TransportEmissionFactor]:
        """
        Gets the emission factor for a specific transportation mode.
        
        Args:
            mode: TransportationMode enum
            
        Returns:
            TransportEmissionFactor object or None
        """
        return self._emission_factors.get(mode)
    
    def get_emission_factor_per_km(self, mode: TransportationMode, 
                                  occupancy: int = 1) -> float:
        """
        Gets the CO2 emission per kilometer for a specific mode and occupancy.
        
        Args:
            mode: TransportationMode enum
            occupancy: Number of passengers
            
        Returns:
            CO2 emissions per kilometer in kg
        """
        factor = self.get_emission_factor(mode)
        if not factor:
            raise ValueError(f"Emission factor not found for mode: {mode}")
        
        return factor.co2_per_km_kg / max(occupancy, factor.occupancy_factor)
    
    def get_emission_factor_per_hour(self, mode: TransportationMode) -> float:
        """
        Gets the CO2 emission per hour for a specific mode.
        
        Args:
            mode: TransportationMode enum
            
        Returns:
            CO2 emissions per hour in kg
        """
        factor = self.get_emission_factor(mode)
        if not factor:
            raise ValueError(f"Emission factor not found for mode: {mode}")
        
        return factor.co2_per_hour_kg


class TravelComparisonEngine:
    """
    Main engine for comparing different travel choices.
    """
    
    def __init__(self):
        self._emission_db = EmissionFactorDatabase()
        self._comparison_history: List[JourneyComparison] = []
        self._journey_segments: List[JourneySegment] = []
        
        # Average speeds for different modes (km/h)
        self._average_speeds = {
            TransportationMode.WALKING: 5.0,
            TransportationMode.CYCLING: 15.0,
            TransportationMode.ELECTRIC_BICYCLE: 25.0,
            TransportationMode.CAR_PETROL: 50.0,
            TransportationMode.CAR_DIESEL: 50.0,
            TransportationMode.CAR_HYBRID: 50.0,
            TransportationMode.CAR_ELECTRIC: 50.0,
            TransportationMode.CAR_PLUGIN_HYBRID: 50.0,
            TransportationMode.MOTORCYCLE_PETROL: 45.0,
            TransportationMode.MOTORCYCLE_ELECTRIC: 45.0,
            TransportationMode.BUS_DIESEL: 25.0,
            TransportationMode.BUS_ELECTRIC: 25.0,
            TransportationMode.TRAIN_DIESEL: 70.0,
            TransportationMode.TRAIN_ELECTRIC: 80.0,
            TransportationMode.HIGH_SPEED_RAIL: 300.0,
            TransportationMode.METRO_SUBWAY: 40.0,
            TransportationMode.TRAM_LIGHT_RAIL: 25.0,
            TransportationMode.DOMESTIC_FLIGHT: 700.0,
            TransportationMode.INTERNATIONAL_FLIGHT: 850.0,
            TransportationMode.FERRY: 30.0,
            TransportationMode.HIGH_SPEED_FERRY: 60.0,
            TransportationMode.RIDE_SHARE: 35.0,
            TransportationMode.CARPOOL: 45.0,
            TransportationMode.VANPOOL: 40.0,
            TransportationMode.SCOOTER_SHARE: 20.0,
            TransportationMode.BIKE_SHARE: 12.0,
            TransportationMode.TAXI: 35.0,
            TransportationMode.RIDE_HAILING_ELECTRIC: 35.0,
            TransportationMode.RIDE_HAILING_HYBRID: 35.0
        }
        
        # Cost per kilometer for different modes (USD)
        self._cost_per_km = {
            TransportationMode.WALKING: 0.0,
            TransportationMode.CYCLING: 0.0,
            TransportationMode.ELECTRIC_BICYCLE: 0.02,
            TransportationMode.CAR_PETROL: 0.20,
            TransportationMode.CAR_DIESEL: 0.18,
            TransportationMode.CAR_HYBRID: 0.15,
            TransportationMode.CAR_ELECTRIC: 0.08,
            TransportationMode.CAR_PLUGIN_HYBRID: 0.12,
            TransportationMode.MOTORCYCLE_PETROL: 0.10,
            TransportationMode.MOTORCYCLE_ELECTRIC: 0.05,
            TransportationMode.BUS_DIESEL: 0.15,
            TransportationMode.BUS_ELECTRIC: 0.12,
            TransportationMode.TRAIN_DIESEL: 0.10,
            TransportationMode.TRAIN_ELECTRIC: 0.08,
            TransportationMode.HIGH_SPEED_RAIL: 0.25,
            TransportationMode.METRO_SUBWAY: 0.10,
            TransportationMode.TRAM_LIGHT_RAIL: 0.12,
            TransportationMode.DOMESTIC_FLIGHT: 0.30,
            TransportationMode.INTERNATIONAL_FLIGHT: 0.25,
            TransportationMode.FERRY: 0.20,
            TransportationMode.HIGH_SPEED_FERRY: 0.35,
            TransportationMode.RIDE_SHARE: 0.25,
            TransportationMode.CARPOOL: 0.08,
            TransportationMode.VANPOOL: 0.10,
            TransportationMode.SCOOTER_SHARE: 0.15,
            TransportationMode.BIKE_SHARE: 0.05,
            TransportationMode.TAXI: 0.40,
            TransportationMode.RIDE_HAILING_ELECTRIC: 0.30,
            TransportationMode.RIDE_HAILING_HYBRID: 0.35
        }
    
    def compare_modes(self, distance_km: float, 
                     modes: List[TransportationMode],
                     occupancy: int = 1,
                     terrain: str = "mixed",
                     weather: str = "clear") -> Dict[TransportationMode, Dict[str, float]]:
        """
        Compares multiple transportation modes for the same journey.
        
        Args:
            distance_km: Journey distance in kilometers
            modes: List of transportation modes to compare
            occupancy: Number of passengers
            terrain: Terrain type (flat, hilly, mixed)
            weather: Weather conditions (clear, rain, snow)
            
        Returns:
            Dictionary with comparison results for each mode
        """
        comparison_results = {}
        
        for mode in modes:
            # Get emission factors
            emission_km = self._emission_db.get_emission_factor_per_km(mode, occupancy)
            emission_hour = self._emission_db.get_emission_factor_per_hour(mode)
            
            # Calculate emissions
            total_emissions_kg = emission_km * distance_km
            
            # Calculate duration
            avg_speed = self._average_speeds.get(mode, 30.0)
            duration_hours = distance_km / avg_speed
            duration_minutes = duration_hours * 60
            
            # Adjust for terrain and weather
            terrain_factors = {
                "flat": 1.0,
                "hilly": 1.15,
                "mixed": 1.05
            }
            weather_factors = {
                "clear": 1.0,
                "rain": 1.15,
                "snow": 1.25
            }
            
            terrain_factor = terrain_factors.get(terrain, 1.0)
            weather_factor = weather_factors.get(weather, 1.0)
            
            duration_minutes *= terrain_factor * weather_factor
            
            # Calculate cost
            cost_per_km = self._cost_per_km.get(mode, 0.15)
            total_cost = cost_per_km * distance_km
            
            # Calculate efficiency scores
            emissions_per_passenger = total_emissions_kg / occupancy
            
            comparison_results[mode] = {
                "distance_km": distance_km,
                "duration_minutes": duration_minutes,
                "duration_hours": duration_hours,
                "total_emissions_kg": total_emissions_kg,
                "emissions_per_passenger_kg": emissions_per_passenger,
                "emissions_per_km_kg": emission_km,
                "total_cost_usd": total_cost,
                "cost_per_passenger_usd": total_cost / occupancy,
                "avg_speed_kmh": avg_speed,
                "terrain_factor": terrain_factor,
                "weather_factor": weather_factor,
                "co2_per_km": emission_km,
                "co2_per_hour": emission_hour,
                "energy_score": self._calculate_energy_score(emission_km),
                "environmental_score": self._calculate_environmental_score(total_emissions_kg, distance_km),
                "cost_score": self._calculate_cost_score(total_cost, distance_km),
                "time_score": self._calculate_time_score(duration_minutes, distance_km)
            }
        
        return comparison_results
    
    def _calculate_energy_score(self, emission_per_km: float) -> float:
        """
        Calculates energy efficiency score (0-1).
        
        Args:
            emission_per_km: CO2 emissions per kilometer
            
        Returns:
            Energy score between 0 and 1
        """
        # Baseline: 0.1 kg/km is considered efficient
        if emission_per_km <= 0.01:
            return 1.0
        elif emission_per_km >= 0.5:
            return 0.0
        else:
            return 1.0 - (emission_per_km - 0.01) / 0.49
    
    def _calculate_environmental_score(self, total_emissions: float, distance: float) -> float:
        """
        Calculates environmental impact score (0-1).
        
        Args:
            total_emissions: Total CO2 emissions in kg
            distance: Distance in kilometers
            
        Returns:
            Environmental score between 0 and 1
        """
        # Baseline: 10 kg per 100 km is considered good
        emissions_per_100km = (total_emissions / distance) * 100 if distance > 0 else 0
        
        if emissions_per_100km <= 2.5:
            return 1.0
        elif emissions_per_100km >= 30:
            return 0.0
        else:
            return 1.0 - (emissions_per_100km - 2.5) / 27.5
    
    def _calculate_cost_score(self, total_cost: float, distance: float) -> float:
        """
        Calculates cost efficiency score (0-1).
        
        Args:
            total_cost: Total journey cost in USD
            distance: Distance in kilometers
            
        Returns:
            Cost score between 0 and 1
        """
        cost_per_km = total_cost / distance if distance > 0 else 0
        
        if cost_per_km <= 0.05:
            return 1.0
        elif cost_per_km >= 0.50:
            return 0.0
        else:
            return 1.0 - (cost_per_km - 0.05) / 0.45
    
    def _calculate_time_score(self, duration_minutes: float, distance: float) -> float:
        """
        Calculates time efficiency score (0-1).
        
        Args:
            duration_minutes: Journey duration in minutes
            distance: Distance in kilometers
            
        Returns:
            Time score between 0 and 1
        """
        avg_speed = (distance / duration_minutes) * 60 if duration_minutes > 0 else 0
        
        if avg_speed >= 80:
            return 1.0
        elif avg_speed <= 10:
            return 0.0
        else:
            return (avg_speed - 10) / 70
    
    def calculate_comparison_summary(self, results: Dict[TransportationMode, Dict[str, float]]) -> Dict[str, Any]:
        """
        Creates a summary of mode comparison results.
        
        Args:
            results: Comparison results from compare_modes
            
        Returns:
            Dictionary with summary statistics
        """
        if not results:
            return {}
        
        summary = {
            "best_for_environment": None,
            "best_for_cost": None,
            "best_for_time": None,
            "best_overall": None,
            "environmental_ranking": [],
            "cost_ranking": [],
            "time_ranking": [],
            "recommendations": []
        }
        
        # Find best for each category
        best_env = min(results.items(), key=lambda x: x[1]['total_emissions_kg'])
        best_cost = min(results.items(), key=lambda x: x[1]['total_cost_usd'])
        best_time = min(results.items(), key=lambda x: x[1]['duration_minutes'])
        
        summary['best_for_environment'] = {
            'mode': best_env[0].value,
            'emissions_kg': best_env[1]['total_emissions_kg']
        }
        
        summary['best_for_cost'] = {
            'mode': best_cost[0].value,
            'cost_usd': best_cost[1]['total_cost_usd']
        }
        
        summary['best_for_time'] = {
            'mode': best_time[0].value,
            'duration_minutes': best_time[1]['duration_minutes']
        }
        
        # Calculate composite score for overall best
        for mode, data in results.items():
            composite_score = (
                data['environmental_score'] * 0.4 +
                data['cost_score'] * 0.3 +
                data['time_score'] * 0.2 +
                data['energy_score'] * 0.1
            )
            data['composite_score'] = composite_score
        
        best_overall = max(results.items(), key=lambda x: x[1]['composite_score'])
        summary['best_overall'] = {
            'mode': best_overall[0].value,
            'composite_score': best_overall[1]['composite_score']
        }
        
        # Create rankings
        env_ranking = sorted(results.items(), key=lambda x: x[1]['total_emissions_kg'])
        cost_ranking = sorted(results.items(), key=lambda x: x[1]['total_cost_usd'])
        time_ranking = sorted(results.items(), key=lambda x: x[1]['duration_minutes'])
        
        summary['environmental_ranking'] = [(mode.value, data['total_emissions_kg']) for mode, data in env_ranking]
        summary['cost_ranking'] = [(mode.value, data['total_cost_usd']) for mode, data in cost_ranking]
        summary['time_ranking'] = [(mode.value, data['duration_minutes']) for mode, data in time_ranking]
        
        # Generate recommendations
        recommendations = []
        
        if best_overall[1]['environmental_score'] > 0.8:
            src.ai.recommendations.append(f"Best overall: {best_overall[0].value} provides excellent environmental performance")
        else:
            # Suggest low emission option
            emission_avg = sum(data['total_emissions_kg'] for data in results.values()) / len(results)
            low_emission_mode = min(results.items(), key=lambda x: x[1]['total_emissions_kg'])
            if low_emission_mode[1]['total_emissions_kg'] < emission_avg * 0.5:
                src.ai.recommendations.append(f"Consider {low_emission_mode[0].value} to reduce emissions by {int((1 - low_emission_mode[1]['total_emissions_kg']/emission_avg) * 100)}%")
        
        # Cost recommendation
        cost_avg = sum(data['total_cost_usd'] for data in results.values()) / len(results)
        low_cost_mode = min(results.items(), key=lambda x: x[1]['total_cost_usd'])
        if low_cost_mode[1]['total_cost_usd'] < cost_avg * 0.8:
            src.ai.recommendations.append(f"{low_cost_mode[0].value} is the most cost-effective option")
        
        # Time recommendation
        time_avg = sum(data['duration_minutes'] for data in results.values()) / len(results)
        fastest_mode = min(results.items(), key=lambda x: x[1]['duration_minutes'])
        if fastest_mode[1]['duration_minutes'] < time_avg * 0.8:
            src.ai.recommendations.append(f"{fastest_mode[0].value} is the fastest option")
        
        summary['recommendations'] = recommendations
        
        return summary
    
    def create_multi_modal_journey(self, segments: List[JourneySegment]) -> JourneyComparison:
        """
        Creates a comparison for a multi-modal journey.
        
        Args:
            segments: List of journey segments
            
        Returns:
            JourneyComparison object
        """
        if not segments:
            raise ValueError("No journey segments provided")
        
        total_distance = sum(seg.distance_km for seg in segments)
        total_duration = sum(seg.duration_minutes for seg in segments)
        total_emissions = 0.0
        total_cost = sum(seg.cost_usd for seg in segments)
        
        # Calculate emissions for each segment
        for segment in segments:
            emission_factor = self._emission_db.get_emission_factor(segment.mode)
            if emission_factor:
                segment_emissions = emission_factor.co2_per_km_kg * segment.distance_km
                segment.emission_factor = emission_factor
                total_emissions += segment_emissions
        
        # Calculate metrics
        emission_per_km = total_emissions / total_distance if total_distance > 0 else 0
        emission_per_hour = total_emissions / (total_duration / 60) if total_duration > 0 else 0
        cost_per_km = total_cost / total_distance if total_distance > 0 else 0
        cost_per_hour = total_cost / (total_duration / 60) if total_duration > 0 else 0
        
        # Determine primary and secondary modes
        mode_frequency = {}
        for seg in segments:
            mode_frequency[seg.mode] = mode_frequency.get(seg.mode, 0) + seg.distance_km
        
        sorted_modes = sorted(mode_frequency.items(), key=lambda x: x[1], reverse=True)
        primary_mode = sorted_modes[0][0] if sorted_modes else None
        secondary_modes = [mode for mode, _ in sorted_modes[1:4]]
        
        # Calculate scores
        environmental_score = self._calculate_environmental_score(total_emissions, total_distance)
        cost_score = self._calculate_cost_score(total_cost, total_distance)
        time_score = self._calculate_time_score(total_duration, total_distance)
        energy_score = self._calculate_energy_score(emission_per_km)
        
        # Generate recommendations
        recommendations = []
        if environmental_score < 0.5:
            src.ai.recommendations.append("Consider alternative modes with lower emissions")
        if cost_score < 0.5:
            src.ai.recommendations.append("Look for more cost-effective transportation options")
        if time_score < 0.5:
            src.ai.recommendations.append("Consider faster transportation options")
        
        comparison = JourneyComparison(
            journey_id=f"J-{datetime.now().strftime('%Y%m%d')}-{random.randint(100, 999)}",
            segments=segments,
            total_distance_km=total_distance,
            total_duration_minutes=total_duration,
            total_co2_kg=total_emissions,
            total_cost_usd=total_cost,
            emission_per_km_kg=emission_per_km,
            emission_per_hour_kg=emission_per_hour,
            cost_per_km_usd=cost_per_km,
            cost_per_hour_usd=cost_per_hour,
            comparison_date=datetime.now(),
            primary_mode=primary_mode if primary_mode else TransportationMode.WALKING,
            secondary_modes=secondary_modes,
            environmental_score=environmental_score,
            cost_score=cost_score,
            time_score=time_score,
            efficiency_score=(environmental_score + cost_score + time_score) / 3,
            recommendations=recommendations
        )
        
        self._comparison_history.append(comparison)
        return comparison


class TravelLogger:
    """
    Logs and tracks travel history for users.
    """
    
    def __init__(self):
        self._travel_history: Dict[str, List[JourneyComparison]] = {}
        self._journey_summaries: Dict[str, JourneySummary] = {}
    
    def log_journey(self, user_id: str, comparison: JourneyComparison) -> None:
        """
        Logs a journey for a user.
        
        Args:
            user_id: User identifier
            comparison: JourneyComparison object
        """
        if user_id not in self._travel_history:
            self._travel_history[user_id] = []
        
        self._travel_history[user_id].append(comparison)
        self._update_summary(user_id)
    
    def _update_summary(self, user_id: str) -> None:
        """
        Updates the journey summary for a user.
        
        Args:
            user_id: User identifier
        """
        if user_id not in self._travel_history:
            return
        
        journeys = self._travel_history[user_id]
        
        if not journeys:
            return
        
        # Calculate totals
        total_journeys = len(journeys)
        total_distance = sum(j.total_distance_km for j in journeys)
        total_duration = sum(j.total_duration_minutes for j in journeys) / 60
        total_emissions = sum(j.total_co2_kg for j in journeys)
        total_cost = sum(j.total_cost_usd for j in journeys)
        
        # Calculate averages
        avg_co2_per_km = total_emissions / total_distance if total_distance > 0 else 0
        avg_co2_per_hour = total_emissions / total_duration if total_duration > 0 else 0
        avg_cost_per_km = total_cost / total_distance if total_distance > 0 else 0
        
        # Calculate mode distribution
        mode_distribution = {}
        for journey in journeys:
            for segment in journey.segments:
                mode_distribution[segment.mode] = mode_distribution.get(segment.mode, 0) + segment.distance_km
        
        # Determine environmental impact rating
        if avg_co2_per_km < 0.05:
            rating = "Excellent"
        elif avg_co2_per_km < 0.10:
            rating = "Good"
        elif avg_co2_per_km < 0.20:
            rating = "Moderate"
        else:
            rating = "Poor"
        
        # Generate recommendations
        recommendations = []
        if avg_co2_per_km > 0.15:
            src.ai.recommendations.append("Consider using more sustainable transport options")
        if total_emissions > 1000:
            src.ai.recommendations.append("Consider offsetting your travel emissions")
        if total_distance > 10000:
            src.ai.recommendations.append("Try combining trips or using public transport more often")
        
        period_start = min(j.comparison_date for j in journeys)
        period_end = max(j.comparison_date for j in journeys)
        
        summary = JourneySummary(
            total_journeys=total_journeys,
            total_distance_km=total_distance,
            total_duration_hours=total_duration,
            total_co2_emissions_kg=total_emissions,
            total_cost_usd=total_cost,
            average_co2_per_km_kg=avg_co2_per_km,
            average_co2_per_hour_kg=avg_co2_per_hour,
            average_cost_per_km_usd=avg_cost_per_km,
            mode_distribution=mode_distribution,
            period_start=period_start,
            period_end=period_end,
            environmental_impact_rating=rating,
            recommendations=recommendations
        )
        
        self._journey_summaries[user_id] = summary
    
    def get_user_summary(self, user_id: str) -> Optional[JourneySummary]:
        """
        Gets the journey summary for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            JourneySummary object or None
        """
        return self._journey_summaries.get(user_id)
    
    def get_user_journeys(self, user_id: str) -> List[JourneyComparison]:
        """
        Gets all logged journeys for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of JourneyComparison objects
        """
        return self._travel_history.get(user_id, [])
    
    def get_journey_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Gets detailed journey statistics for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with journey statistics
        """
        summary = self.get_user_summary(user_id)
        if not summary:
            return {"message": "No travel data found for this user"}
        
        return {
            "total_journeys": summary.total_journeys,
            "total_distance_km": summary.total_distance_km,
            "total_duration_hours": summary.total_duration_hours,
            "total_co2_emissions_kg": summary.total_co2_emissions_kg,
            "total_cost_usd": summary.total_cost_usd,
            "average_co2_per_km_kg": summary.average_co2_per_km_kg,
            "average_co2_per_hour_kg": summary.average_co2_per_hour_kg,
            "average_cost_per_km_usd": summary.average_cost_per_km_usd,
            "environmental_impact_rating": summary.environmental_impact_rating,
            "top_modes_used": sorted(
                summary.mode_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "recommendations": summary.recommendations
        }


class TravelComparisonTool:
    """
    Main class for the travel comparison tool.
    """
    
    def __init__(self):
        self.comparison_engine = TravelComparisonEngine()
        self.travel_logger = TravelLogger()
        self._emission_db = EmissionFactorDatabase()
    
    def compare_transport_options(self, distance_km: float, 
                                 modes: List[TransportationMode],
                                 occupancy: int = 1) -> Dict[str, Any]:
        """
        Compares different transport options for a journey.
        
        Args:
            distance_km: Journey distance in kilometers
            modes: List of transportation modes to compare
            occupancy: Number of passengers
            
        Returns:
            Dictionary with comparison results
        """
        results = self.comparison_engine.compare_modes(distance_km, modes, occupancy)
        summary = self.comparison_engine.calculate_comparison_summary(results)
        
        # Format results for display
        formatted_results = {}
        for mode, data in results.items():
            formatted_results[mode.value] = {
                "distance_km": data['distance_km'],
                "duration_minutes": round(data['duration_minutes'], 1),
                "duration_hours": round(data['duration_hours'], 2),
                "co2_emissions_kg": round(data['total_emissions_kg'], 2),
                "emissions_per_passenger_kg": round(data['emissions_per_passenger_kg'], 2),
                "co2_per_km_kg": round(data['emissions_per_km_kg'], 3),
                "total_cost_usd": round(data['total_cost_usd'], 2),
                "cost_per_passenger_usd": round(data['cost_per_passenger_usd'], 2),
                "avg_speed_kmh": round(data['avg_speed_kmh'], 1),
                "environmental_score": round(data['environmental_score'] * 100, 1),
                "cost_score": round(data['cost_score'] * 100, 1),
                "time_score": round(data['time_score'] * 100, 1),
                "energy_score": round(data['energy_score'] * 100, 1),
                "composite_score": round(data.get('composite_score', 0) * 100, 1)
            }
        
        return {
            "journey_distance_km": distance_km,
            "occupancy": occupancy,
            "comparison_results": formatted_results,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
    
    def log_travel_choice(self, user_id: str, distance_km: float, 
                         modes: List[TransportationMode],
                         occupancy: int = 1) -> Dict[str, Any]:
        """
        Logs a travel choice and returns comparison results.
        
        Args:
            user_id: User identifier
            distance_km: Journey distance in kilometers
            modes: List of transportation modes to compare
            occupancy: Number of passengers
            
        Returns:
            Dictionary with logged journey results
        """
        # Get comparison
        comparison_results = self.compare_transport_options(distance_km, modes, occupancy)
        
        # Create journey comparison for logging
        segments = []
        for mode in modes:
            segment = JourneySegment(
                start_location="start",
                end_location="end",
                distance_km=distance_km,
                duration_minutes=comparison_results['comparison_results'][mode.value]['duration_minutes'],
                mode=mode,
                cost_usd=comparison_results['comparison_results'][mode.value]['total_cost_usd'],
                occupancy=occupancy,
                emission_factor=self._emission_db.get_emission_factor(mode)
            )
            segments.append(segment)
        
        # Create multi-modal journey
        journey_comparison = self.comparison_engine.create_multi_modal_journey(segments)
        
        # Log the journey
        self.travel_logger.log_journey(user_id, journey_comparison)
        
        return {
            "user_id": user_id,
            "journey_id": journey_comparison.journey_id,
            "comparison": comparison_results,
            "logged_journey": {
                "total_emissions_kg": journey_comparison.total_co2_kg,
                "total_cost_usd": journey_comparison.total_cost_usd,
                "total_duration_minutes": journey_comparison.total_duration_minutes,
                "emissions_per_km_kg": journey_comparison.emission_per_km_kg,
                "environmental_score": journey_comparison.environmental_score,
                "recommendations": journey_comparison.recommendations
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_travel_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Gets travel statistics for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with travel statistics
        """
        return self.travel_logger.get_journey_statistics(user_id)
    
    def generate_travel_report(self, user_id: str) -> str:
        """
        Generates a detailed travel report for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Formatted report as string
        """
        stats = self.get_travel_statistics(user_id)
        
        if "message" in stats:
            return stats["message"]
        
        report = []
        src.reporting.report.append("=" * 70)
        src.reporting.report.append(f"  TRAVEL IMPACT REPORT - USER: {user_id}")
        src.reporting.report.append("=" * 70)
        src.reporting.report.append(f"  Period: {self.travel_logger.get_user_summary(user_id).period_start.strftime('%Y-%m-%d')} to {self.travel_logger.get_user_summary(user_id).period_end.strftime('%Y-%m-%d')}")
        src.reporting.report.append("")
        src.reporting.report.append("  📊 TRAVEL SUMMARY")
        src.reporting.report.append(f"    Total Journeys: {stats['total_journeys']}")
        src.reporting.report.append(f"    Total Distance: {stats['total_distance_km']:,.1f} km")
        src.reporting.report.append(f"    Total Travel Time: {stats['total_duration_hours']:.1f} hours")
        src.reporting.report.append(f"    Total CO2 Emissions: {stats['total_co2_emissions_kg']:,.0f} kg")
        src.reporting.report.append(f"    Total Travel Cost: ${stats['total_cost_usd']:,.2f}")
        src.reporting.report.append("")
        src.reporting.report.append("  📈 KEY METRICS")
        src.reporting.report.append(f"    Average CO2 per km: {stats['average_co2_per_km_kg']:.3f} kg/km")
        src.reporting.report.append(f"    Average CO2 per hour: {stats['average_co2_per_hour_kg']:.2f} kg/hour")
        src.reporting.report.append(f"    Average Cost per km: ${stats['average_cost_per_km_usd']:.3f}")
        src.reporting.report.append(f"    Environmental Rating: {stats['environmental_impact_rating']}")
        src.reporting.report.append("")
        src.reporting.report.append("  🚗 MOST USED MODES")
        for mode, distance in stats['top_modes_used']:
            src.reporting.report.append(f"    {mode.value.replace('_', ' ').title()}: {distance:,.0f} km")
        src.reporting.report.append("")
        src.reporting.report.append("  💡 RECOMMENDATIONS")
        for i, rec in enumerate(stats['recommendations'], 1):
            src.reporting.report.append(f"    {i}. {rec}")
        src.reporting.report.append("")
        src.reporting.report.append("=" * 70)
        
        return "\n".join(report)


# ============ EXAMPLE USAGE AND TESTING FUNCTIONS ============

def test_travel_comparison_tool():
    """
    Test function for the travel comparison tool.
    """
    print("\n" + "=" * 70)
    print("  TRAVEL COMPARISON TOOL TEST")
    print("=" * 70)
    
    # Initialize tool
    tool = TravelComparisonTool()
    
    # Test 1: Compare different modes for a single journey
    print("\n📊 TEST 1: COMPARE TRANSPORTATION MODES")
    print("-" * 70)
    
    distance = 50  # kilometers
    modes_to_compare = [
        TransportationMode.CAR_PETROL,
        TransportationMode.CAR_ELECTRIC,
        TransportationMode.BUS_DIESEL,
        TransportationMode.TRAIN_ELECTRIC,
        TransportationMode.DOMESTIC_FLIGHT,
        TransportationMode.CYCLING
    ]
    
    results = tool.compare_transport_options(distance, modes_to_compare, occupancy=2)
    
    print(f"Journey Distance: {distance} km")
    print(f"Occupancy: 2 passengers")
    print("\nComparison Results:")
    print("-" * 50)
    
    for mode_name, data in results['comparison_results'].items():
        print(f"\n{mode_name.replace('_', ' ').title()}:")
        print(f"  Duration: {data['duration_minutes']} minutes ({data['duration_hours']} hours)")
        print(f"  CO2 Emissions: {data['co2_emissions_kg']} kg")
        print(f"  Emissions per passenger: {data['emissions_per_passenger_kg']} kg")
        print(f"  Cost: ${data['total_cost_usd']}")
        print(f"  Environmental Score: {data['environmental_score']}%")
        print(f"  Composite Score: {data['composite_score']}%")
    
    # Show summary
    print("\n📋 SUMMARY")
    print("-" * 50)
    summary = results['summary']
    print(f"Best for Environment: {summary['best_for_environment']['mode']} ({summary['best_for_environment']['emissions_kg']:.2f} kg)")
    print(f"Best for Cost: {summary['best_for_cost']['mode']} (${summary['best_for_cost']['cost_usd']:.2f})")
    print(f"Best for Time: {summary['best_for_time']['mode']} ({summary['best_for_time']['duration_minutes']:.1f} minutes)")
    print(f"Best Overall: {summary['best_overall']['mode']} (Score: {summary['best_overall']['composite_score']:.2f})")
    
    print("\nRecommendations:")
    for rec in summary['recommendations']:
        print(f"  • {rec}")
    
    # Test 2: Log a travel choice
    print("\n📊 TEST 2: LOG TRAVEL CHOICE")
    print("-" * 70)
    
    user_id = "user_test_001"
    logged_result = tool.log_travel_choice(user_id, 25, 
                                         [TransportationMode.CAR_PETROL, 
                                          TransportationMode.BUS_DIESEL,
                                          TransportationMode.CYCLING],
                                         occupancy=1)
    
    print(f"Logged journey for user: {user_id}")
    print(f"Journey ID: {logged_result['journey_id']}")
    print(f"Total CO2: {logged_result['logged_journey']['total_emissions_kg']} kg")
    print(f"Total Cost: ${logged_result['logged_journey']['total_cost_usd']}")
    
    # Test 3: Get travel statistics
    print("\n📊 TEST 3: TRAVEL STATISTICS")
    print("-" * 70)
    
    # Log a few more journeys
    tool.log_travel_choice(user_id, 100, [TransportationMode.TRAIN_ELECTRIC, 
                                         TransportationMode.CAR_ELECTRIC],
                          occupancy=2)
    tool.log_travel_choice(user_id, 15, [TransportationMode.CYCLING, 
                                         TransportationMode.BUS_DIESEL],
                          occupancy=1)
    
    stats = tool.get_travel_statistics(user_id)
    print(f"Total Journeys: {stats['total_journeys']}")
    print(f"Total Distance: {stats['total_distance_km']:.1f} km")
    print(f"Total CO2: {stats['total_co2_emissions_kg']:.0f} kg")
    print(f"Environmental Rating: {stats['environmental_impact_rating']}")
    print(f"Top Modes:")
    for mode, distance in stats['top_modes_used']:
        print(f"  • {mode.value}: {distance:.0f} km")
    
    # Test 4: Generate report
    print("\n📊 TEST 4: GENERATE TRAVEL REPORT")
    print("-" * 70)
    
    report = tool.generate_travel_report(user_id)
    print(report)
    
    # Test 5: Multi-modal journey
    print("\n📊 TEST 5: MULTI-MODAL JOURNEY")
    print("-" * 70)
    
    segments = [
        JourneySegment(
            start_location="Home",
            end_location="Train Station",
            distance_km=5,
            duration_minutes=20,
            mode=TransportationMode.CYCLING,
            cost_usd=0.0
        ),
        JourneySegment(
            start_location="Train Station",
            end_location="City Center",
            distance_km=40,
            duration_minutes=35,
            mode=TransportationMode.TRAIN_ELECTRIC,
            cost_usd=12.50
        ),
        JourneySegment(
            start_location="City Center",
            end_location="Workplace",
            distance_km=3,
            duration_minutes=10,
            mode=TransportationMode.WALKING,
            cost_usd=0.0
        )
    ]
    
    multi_modal = tool.comparison_engine.create_multi_modal_journey(segments)
    print(f"Multi-modal Journey ID: {multi_modal.journey_id}")
    print(f"Total Distance: {multi_modal.total_distance_km:.1f} km")
    print(f"Total Duration: {multi_modal.total_duration_minutes:.1f} minutes")
    print(f"Total CO2: {multi_modal.total_co2_kg:.2f} kg")
    print(f"Total Cost: ${multi_modal.total_cost_usd:.2f}")
    print(f"Environmental Score: {multi_modal.environmental_score * 100:.1f}%")
    print(f"Primary Mode: {multi_modal.primary_mode.value}")
    print(f"Secondary Modes: {[m.value for m in multi_modal.secondary_modes]}")
    print("\nRecommendations:")
    for rec in multi_modal.recommendations:
        print(f"  • {rec}")
    
    print("\n" + "=" * 70)
    print("✅ Travel comparison tool test completed successfully!")
    print("=" * 70)


def main():
    """Main function to run the travel comparison tool."""
    test_travel_comparison_tool()


if __name__ == "__main__":
    main()
