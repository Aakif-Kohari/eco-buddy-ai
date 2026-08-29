"""
Sustainable Travel & Trip Impact Planner - Environmental Analysis
Calculates comprehensive environmental impact of trips.
"""

import logging
import statistics
from typing import List, Optional, Dict, Any

from travel.models import (
    Trip, EnvironmentalImpact, TransportationMode
)

logger = logging.getLogger(__name__)


class EnvironmentalAnalyzer:
    """
    Analyzes environmental impact of trips.
    """
    
    def __init__(self):
        """Initialize the environmental analyzer."""
        self.carbon_benchmarks = self._initialize_carbon_benchmarks()
        self.sustainability_weights = {
            'carbon': 0.35,
            'energy': 0.25,
            'water': 0.20,
            'waste': 0.20
        }
        logger.info("Environmental Analyzer initialized")
    
    def _initialize_carbon_benchmarks(self) -> Dict[str, float]:
        """Initialize carbon benchmarks (kg CO2e per km)."""
        return {
            'walking': 0.0,
            'cycling': 0.0,
            'public_transit': 0.05,
            'train': 0.04,
            'bus': 0.06,
            'car': 0.18,
            'carpool': 0.09,
            'electric_vehicle': 0.05,
            'hybrid_vehicle': 0.10,
            'flight': 0.25,
            'ferry': 0.12,
            'taxi': 0.20,
            'rideshare': 0.15
        }
    
    def calculate_trip_impact(self, trip: Trip) -> EnvironmentalImpact:
        """
        Calculate comprehensive environmental impact for a trip.
        
        Args:
            trip: The trip to analyze
        
        Returns:
            EnvironmentalImpact: Impact analysis
        """
        impact = EnvironmentalImpact(
            trip_id=trip.id,
            trip_name=trip.name
        )
        
        # Calculate transport impact
        transport_impact = self._calculate_transport_impact(trip)
        impact.transport_carbon_kg = transport_impact['carbon']
        impact.transport_energy_kwh = transport_impact['energy']
        
        # Calculate accommodation impact
        acc_impact = self._calculate_accommodation_impact(trip)
        impact.accommodation_carbon_kg = acc_impact['carbon']
        impact.accommodation_energy_kwh = acc_impact['energy']
        impact.accommodation_water_liters = acc_impact['water']
        impact.accommodation_waste_kg = acc_impact['waste']
        
        # Calculate activity impact
        impact.activity_carbon_kg = self._calculate_activity_impact(trip)
        
        # Calculate totals
        impact.total_carbon_kg = (
            impact.transport_carbon_kg +
            impact.accommodation_carbon_kg +
            impact.activity_carbon_kg
        )
        
        impact.total_energy_kwh = (
            impact.transport_energy_kwh +
            impact.accommodation_energy_kwh
        )
        
        impact.total_water_liters = impact.accommodation_water_liters
        impact.total_waste_kg = impact.accommodation_waste_kg
        
        # Calculate per person metrics
        num_participants = len(trip.participants) or 1
        
        impact.per_person_carbon_kg = impact.total_carbon_kg / num_participants
        impact.per_person_energy_kwh = impact.total_energy_kwh / num_participants
        impact.per_person_water_liters = impact.total_water_liters / num_participants
        
        # Calculate scores
        impact.carbon_score = self._calculate_carbon_score(impact)
        impact.energy_score = self._calculate_energy_score(impact)
        impact.water_score = self._calculate_water_score(impact)
        impact.waste_score = self._calculate_waste_score(impact)
        
        impact.overall_environmental_score = (
            impact.carbon_score * self.sustainability_weights['carbon'] +
            impact.energy_score * self.sustainability_weights['energy'] +
            impact.water_score * self.sustainability_weights['water'] +
            impact.waste_score * self.sustainability_weights['waste']
        )
        
        return impact
    
    def _calculate_transport_impact(self, trip: Trip) -> Dict[str, float]:
        """
        Calculate transportation impact.
        """
        carbon = 0.0
        energy = 0.0
        
        for leg in trip.legs:
            if leg.selected_transportation:
                transport = leg.selected_transportation
                carbon += transport.carbon_emissions_kg
                energy += transport.energy_consumption_kwh
            elif leg.transportation:
                transport = leg.transportation[0]
                carbon += transport.carbon_emissions_kg
                energy += transport.energy_consumption_kwh
        
        return {
            'carbon': carbon,
            'energy': energy
        }
    
    def _calculate_accommodation_impact(self, trip: Trip) -> Dict[str, float]:
        """
        Calculate accommodation impact.
        """
        carbon = 0.0
        energy = 0.0
        water = 0.0
        waste = 0.0
        
        for acc in trip.accommodation:
            carbon += acc.carbon_emissions_kg
            energy += acc.energy_usage_kwh
            water += acc.water_usage_liters
            waste += acc.waste_generation_kg
        
        return {
            'carbon': carbon,
            'energy': energy,
            'water': water,
            'waste': waste
        }
    
    def _calculate_activity_impact(self, trip: Trip) -> float:
        """
        Calculate activity carbon impact.
        """
        total_carbon = 0.0
        
        for activity in trip.activities:
            total_carbon += activity.carbon_emissions_kg
        
        return total_carbon
    
    def _calculate_carbon_score(self, impact: EnvironmentalImpact) -> float:
        """
        Calculate carbon score (0-100, higher is better).
        """
        # Base on per person carbon emissions
        carbon_per_km = impact.per_person_carbon_kg / (impact.trip_distance_km or 1)
        
        if carbon_per_km <= 0:
            return 100
        elif carbon_per_km <= 0.02:  # Walking/cycling level
            return 90
        elif carbon_per_km <= 0.05:  # Public transit/train
            return 75
        elif carbon_per_km <= 0.10:  # Electric/hybrid
            return 60
        elif carbon_per_km <= 0.15:  # Car/rideshare
            return 40
        elif carbon_per_km <= 0.20:  # Taxi/flight
            return 20
        else:
            return 10
    
    def _calculate_energy_score(self, impact: EnvironmentalImpact) -> float:
        """
        Calculate energy score (0-100, higher is better).
        """
        # Base on total energy consumption
        energy_per_km = impact.total_energy_kwh / (impact.trip_distance_km or 1)
        
        if energy_per_km <= 0:
            return 100
        elif energy_per_km <= 0.1:
            return 90
        elif energy_per_km <= 0.3:
            return 70
        elif energy_per_km <= 0.5:
            return 50
        elif energy_per_km <= 0.8:
            return 30
        else:
            return 10
    
    def _calculate_water_score(self, impact: EnvironmentalImpact) -> float:
        """
        Calculate water score (0-100, higher is better).
        """
        # Base on water consumption per person
        water_per_night = impact.per_person_water_liters / (impact.trip_duration_days or 1)
        
        if water_per_night <= 0:
            return 100
        elif water_per_night <= 50:  # Camping level
            return 90
        elif water_per_night <= 100:  # Hostel level
            return 70
        elif water_per_night <= 150:  # Hotel level
            return 50
        elif water_per_night <= 200:  # Resort level
            return 30
        else:
            return 10
    
    def _calculate_waste_score(self, impact: EnvironmentalImpact) -> float:
        """
        Calculate waste score (0-100, higher is better).
        """
        # Base on waste per person
        waste_per_night = impact.total_waste_kg / (impact.trip_duration_days or 1)
        
        if waste_per_night <= 0:
            return 100
        elif waste_per_night <= 0.2:
            return 90
        elif waste_per_night <= 0.5:
            return 70
        elif waste_per_night <= 0.8:
            return 50
        elif waste_per_night <= 1.0:
            return 30
        else:
            return 10
    
    def get_sustainability_grade(self, score: float) -> str:
        """
        Get sustainability grade based on score.
        
        Args:
            score: Sustainability score (0-100)
        
        Returns:
            str: Grade
        """
        if score >= 80:
            return "Excellent"
        elif score >= 65:
            return "Good"
        elif score >= 50:
            return "Fair"
        elif score >= 35:
            return "Poor"
        else:
            return "Needs Improvement"
    
    def compare_environmental_impact(self, 
                                    impact1: EnvironmentalImpact,
                                    impact2: EnvironmentalImpact) -> Dict[str, Any]:
        """
        Compare environmental impact of two trips.
        
        Args:
            impact1: First impact analysis
            impact2: Second impact analysis
        
        Returns:
            Dict: Comparison results
        """
        carbon_diff = impact1.total_carbon_kg - impact2.total_carbon_kg
        carbon_diff_pct = ((carbon_diff / impact1.total_carbon_kg) * 100) if impact1.total_carbon_kg > 0 else 0
        
        return {
            'carbon_difference_kg': carbon_diff,
            'carbon_difference_percentage': carbon_diff_pct,
            'better_overall': impact1.trip_name if impact1.overall_environmental_score > impact2.overall_environmental_score else impact2.trip_name,
            'better_carbon': impact1.trip_name if impact1.total_carbon_kg < impact2.total_carbon_kg else impact2.trip_name,
            'scores': {
                'trip1': impact1.overall_environmental_score,
                'trip2': impact2.overall_environmental_score
            }
        }