"""
Sustainable Travel & Trip Impact Planner - Transportation Analysis
Analyzes transportation options for trip legs.
"""

import logging
import math
from typing import List, Optional, Dict, Any, Tuple

from travel.models import (
    TransportationMode, TransportationOption, TripLeg
)

logger = logging.getLogger(__name__)


class TransportationAnalyzer:
    """
    Analyzes transportation options and calculates environmental impact.
    """
    
    def __init__(self):
        """Initialize the transportation analyzer."""
        self.emission_factors = self._initialize_emission_factors()
        self.energy_factors = self._initialize_energy_factors()
        self.speed_factors = self._initialize_speed_factors()
        self.cost_factors = self._initialize_cost_factors()
        logger.info("Transportation Analyzer initialized")
    
    def _initialize_emission_factors(self) -> Dict[TransportationMode, float]:
        """Initialize carbon emission factors (kg CO2e per km)."""
        return {
            TransportationMode.WALKING: 0.0,
            TransportationMode.CYCLING: 0.0,
            TransportationMode.PUBLIC_TRANSIT: 0.05,
            TransportationMode.TRAIN: 0.04,
            TransportationMode.BUS: 0.06,
            TransportationMode.CAR: 0.18,
            TransportationMode.CARPOOL: 0.09,  # Per person when 2+ people
            TransportationMode.ELECTRIC_VEHICLE: 0.05,
            TransportationMode.HYBRID_VEHICLE: 0.10,
            TransportationMode.FLIGHT: 0.25,
            TransportationMode.FERRY: 0.12,
            TransportationMode.TAXI: 0.20,
            TransportationMode.RIDESHARE: 0.15,
            TransportationMode.SCOOTER: 0.04,
            TransportationMode.MOTORBIKE: 0.08,
            TransportationMode.SHUTTLE: 0.07,
            TransportationMode.OTHER: 0.15
        }
    
    def _initialize_energy_factors(self) -> Dict[TransportationMode, float]:
        """Initialize energy consumption factors (kWh per km)."""
        return {
            TransportationMode.WALKING: 0.0,
            TransportationMode.CYCLING: 0.0,
            TransportationMode.PUBLIC_TRANSIT: 0.3,
            TransportationMode.TRAIN: 0.2,
            TransportationMode.BUS: 0.4,
            TransportationMode.CAR: 0.8,
            TransportationMode.CARPOOL: 0.4,
            TransportationMode.ELECTRIC_VEHICLE: 0.2,
            TransportationMode.HYBRID_VEHICLE: 0.5,
            TransportationMode.FLIGHT: 1.2,
            TransportationMode.FERRY: 0.6,
            TransportationMode.TAXI: 0.9,
            TransportationMode.RIDESHARE: 0.7,
            TransportationMode.SCOOTER: 0.1,
            TransportationMode.MOTORBIKE: 0.3,
            TransportationMode.SHUTTLE: 0.4,
            TransportationMode.OTHER: 0.6
        }
    
    def _initialize_speed_factors(self) -> Dict[TransportationMode, float]:
        """Initialize average speed factors (km/h)."""
        return {
            TransportationMode.WALKING: 5.0,
            TransportationMode.CYCLING: 18.0,
            TransportationMode.PUBLIC_TRANSIT: 25.0,
            TransportationMode.TRAIN: 80.0,
            TransportationMode.BUS: 40.0,
            TransportationMode.CAR: 60.0,
            TransportationMode.CARPOOL: 60.0,
            TransportationMode.ELECTRIC_VEHICLE: 55.0,
            TransportationMode.HYBRID_VEHICLE: 55.0,
            TransportationMode.FLIGHT: 800.0,
            TransportationMode.FERRY: 30.0,
            TransportationMode.TAXI: 45.0,
            TransportationMode.RIDESHARE: 40.0,
            TransportationMode.SCOOTER: 25.0,
            TransportationMode.MOTORBIKE: 50.0,
            TransportationMode.SHUTTLE: 35.0,
            TransportationMode.OTHER: 45.0
        }
    
    def _initialize_cost_factors(self) -> Dict[TransportationMode, float]:
        """Initialize cost factors (USD per km)."""
        return {
            TransportationMode.WALKING: 0.0,
            TransportationMode.CYCLING: 0.01,
            TransportationMode.PUBLIC_TRANSIT: 0.15,
            TransportationMode.TRAIN: 0.20,
            TransportationMode.BUS: 0.12,
            TransportationMode.CAR: 0.30,
            TransportationMode.CARPOOL: 0.15,
            TransportationMode.ELECTRIC_VEHICLE: 0.12,
            TransportationMode.HYBRID_VEHICLE: 0.20,
            TransportationMode.FLIGHT: 0.50,
            TransportationMode.FERRY: 0.25,
            TransportationMode.TAXI: 1.00,
            TransportationMode.RIDESHARE: 0.60,
            TransportationMode.SCOOTER: 0.15,
            TransportationMode.MOTORBIKE: 0.20,
            TransportationMode.SHUTTLE: 0.18,
            TransportationMode.OTHER: 0.25
        }
    
    def calculate_transportation_options(self, 
                                        origin: str,
                                        destination: str,
                                        distance_km: float,
                                        passengers: int = 1) -> List[TransportationOption]:
        """
        Calculate transportation options for a trip leg.
        
        Args:
            origin: Origin location
            destination: Destination location
            distance_km: Distance in kilometers
            passengers: Number of passengers
        
        Returns:
            List[TransportationOption]: Available options
        """
        options = []
        
        for mode in TransportationMode:
            # Skip walking for long distances
            if mode == TransportationMode.WALKING and distance_km > 20:
                continue
            
            # Skip cycling for very long distances
            if mode == TransportationMode.CYCLING and distance_km > 100:
                continue
            
            option = self._calculate_option(mode, distance_km, passengers)
            options.append(option)
        
        # Sort by sustainability score (carbon emissions)
        options.sort(key=lambda x: x.carbon_emissions_kg)
        
        return options
    
    def _calculate_option(self, 
                         mode: TransportationMode,
                         distance_km: float,
                         passengers: int) -> TransportationOption:
        """
        Calculate a single transportation option.
        """
        # Get factors
        emission_factor = self.emission_factors.get(mode, 0.15)
        energy_factor = self.energy_factors.get(mode, 0.5)
        speed = self.speed_factors.get(mode, 45.0)
        cost_factor = self.cost_factors.get(mode, 0.25)
        
        # Calculate emissions
        carbon_emissions = emission_factor * distance_km
        
        # Adjust for passengers (carpool/rideshare benefits)
        if mode in [TransportationMode.CARPOOL, TransportationMode.RIDESHARE] and passengers > 1:
            carbon_emissions = carbon_emissions / passengers
        
        # Calculate energy
        energy_consumption = energy_factor * distance_km
        
        # Calculate time
        travel_time_hours = distance_km / speed if speed > 0 else 0
        
        # Calculate cost
        cost = cost_factor * distance_km
        
        # Additional cost adjustments
        if mode == TransportationMode.FLIGHT:
            cost += 50  # Base airport fees
        
        if mode == TransportationMode.TRAIN:
            cost += 10  # Base station fees
        
        return TransportationOption(
            mode=mode,
            distance_km=distance_km,
            travel_time_hours=travel_time_hours,
            cost=cost,
            carbon_emissions_kg=carbon_emissions,
            energy_consumption_kwh=energy_consumption,
            passengers=passengers,
            is_shared=mode in [TransportationMode.CARPOOL, TransportationMode.RIDESHARE, TransportationMode.PUBLIC_TRANSIT],
            provider=self._get_provider(mode),
            notes=self._get_notes(mode, passengers)
        )
    
    def _get_provider(self, mode: TransportationMode) -> str:
        """Get default provider for transportation mode."""
        providers = {
            TransportationMode.PUBLIC_TRANSIT: "Local Transit Authority",
            TransportationMode.TRAIN: "National Rail",
            TransportationMode.BUS: "Intercity Bus",
            TransportationMode.FLIGHT: "Airline",
            TransportationMode.FERRY: "Ferry Service",
            TransportationMode.TAXI: "Taxi Service",
            TransportationMode.RIDESHARE: "Rideshare App",
            TransportationMode.SHUTTLE: "Shuttle Service"
        }
        return providers.get(mode, "")
    
    def _get_notes(self, mode: TransportationMode, passengers: int) -> str:
        """Get notes for transportation option."""
        notes = {
            TransportationMode.WALKING: "Zero carbon emissions. Great for short distances.",
            TransportationMode.CYCLING: "Zero carbon emissions. Healthy and sustainable.",
            TransportationMode.PUBLIC_TRANSIT: "Reduced emissions per passenger.",
            TransportationMode.TRAIN: "One of the most sustainable long-distance options.",
            TransportationMode.BUS: "Efficient for intercity travel.",
            TransportationMode.CAR: "Convenient but high emissions.",
            TransportationMode.CARPOOL: f"Shares emissions with {passengers-1} other passengers.",
            TransportationMode.ELECTRIC_VEHICLE: "Low emissions with renewable energy.",
            TransportationMode.HYBRID_VEHICLE: "Better fuel efficiency than conventional cars.",
            TransportationMode.FLIGHT: "Highest carbon impact. Consider alternatives.",
            TransportationMode.FERRY: "Moderate impact for water crossings.",
            TransportationMode.TAXI: "Convenient but expensive with moderate emissions.",
            TransportationMode.RIDESHARE: f"Shared ride with {passengers-1} other passengers.",
            TransportationMode.SCOOTER: "Efficient for short urban trips.",
            TransportationMode.MOTORBIKE: "More efficient than cars for solo travel.",
            TransportationMode.SHUTTLE: "Shared service with moderate emissions."
        }
        return notes.get(mode, "")
    
    def analyze_leg(self, leg: TripLeg, passengers: int = 1) -> Dict[str, Any]:
        """
        Analyze a trip leg and provide transportation options.
        
        Args:
            leg: Trip leg
            passengers: Number of passengers
        
        Returns:
            Dict: Analysis results
        """
        distance = leg.distance_km
        
        if distance == 0 and leg.origin and leg.destination:
            # Try to estimate distance (simplified)
            distance = self._estimate_distance(leg.origin, leg.destination)
            leg.distance_km = distance
        
        # Generate options
        options = self.calculate_transportation_options(
            leg.origin,
            leg.destination,
            distance,
            passengers
        )
        
        leg.transportation = options
        
        # Find best options
        best_carbon = min(options, key=lambda x: x.carbon_emissions_kg)
        best_time = min(options, key=lambda x: x.travel_time_hours)
        best_cost = min(options, key=lambda x: x.cost)
        
        return {
            'distance_km': distance,
            'total_options': len(options),
            'best_carbon': best_carbon,
            'best_time': best_time,
            'best_cost': best_cost,
            'all_options': options
        }
    
    def _estimate_distance(self, origin: str, destination: str) -> float:
        """
        Estimate distance between two locations.
        
        Returns:
            float: Estimated distance in km
        """
        # Simplified estimation based on common routes
        # In production, this would use a geocoding/distance API
        
        common_routes = {
            ('New York', 'Boston'): 340,
            ('New York', 'Washington DC'): 360,
            ('New York', 'Chicago'): 1200,
            ('New York', 'Los Angeles'): 4000,
            ('Los Angeles', 'San Francisco'): 600,
            ('Chicago', 'Detroit'): 450,
            ('Chicago', 'Toronto'): 800,
            ('London', 'Paris'): 450,
            ('London', 'Berlin'): 930,
            ('Paris', 'Berlin'): 1050,
            ('Paris', 'Rome'): 1100,
            ('Berlin', 'Rome'): 1180,
            ('Tokyo', 'Osaka'): 400,
            ('Tokyo', 'Seoul'): 1160,
            ('Seoul', 'Tokyo'): 1160,
            ('Beijing', 'Shanghai'): 1050,
            ('Shanghai', 'Hong Kong'): 1200,
            ('Singapore', 'Kuala Lumpur'): 350,
            ('Sydney', 'Melbourne'): 870,
            ('Rio de Janeiro', 'Sao Paulo'): 430,
            ('Mexico City', 'Cancun'): 1300
        }
        
        # Try exact match
        key = (origin, destination)
        if key in common_routes:
            return common_routes[key]
        
        # Try reverse
        rev_key = (destination, origin)
        if rev_key in common_routes:
            return common_routes[rev_key]
        
        # Default estimate
        return 100.0
    
    def get_emission_comparison(self, options: List[TransportationOption]) -> Dict[str, Any]:
        """
        Compare emissions of different transportation options.
        
        Args:
            options: List of transportation options
        
        Returns:
            Dict: Comparison results
        """
        if not options:
            return {'message': 'No options to compare'}
        
        min_carbon = min(options, key=lambda x: x.carbon_emissions_kg)
        max_carbon = max(options, key=lambda x: x.carbon_emissions_kg)
        
        return {
            'min_carbon': min_carbon.mode.value,
            'min_carbon_kg': min_carbon.carbon_emissions_kg,
            'max_carbon': max_carbon.mode.value,
            'max_carbon_kg': max_carbon.carbon_emissions_kg,
            'difference_kg': max_carbon.carbon_emissions_kg - min_carbon.carbon_emissions_kg,
            'difference_percentage': ((max_carbon.carbon_emissions_kg - min_carbon.carbon_emissions_kg) / 
                                     max_carbon.carbon_emissions_kg * 100) if max_carbon.carbon_emissions_kg > 0 else 0,
            'lowest_carbon_mode': min_carbon.mode.value,
            'recommendation': 'Choose the lowest carbon option to reduce your impact.'
        }