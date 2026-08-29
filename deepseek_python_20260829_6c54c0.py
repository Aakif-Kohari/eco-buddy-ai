"""
Sustainable Travel & Trip Impact Planner - Group Travel
Analyzes group travel metrics and shared impacts.
"""

import logging
from typing import List, Optional, Dict, Any

from travel.models import (
    Trip, GroupTravelMetrics, TripParticipant,
    TransportationOption, AccommodationOption
)

logger = logging.getLogger(__name__)


class GroupTravelAnalyzer:
    """
    Analyzes group travel metrics and shared benefits.
    """
    
    def __init__(self):
        """Initialize the group travel analyzer."""
        logger.info("Group Travel Analyzer initialized")
    
    def analyze_group_trip(self, trip: Trip) -> GroupTravelMetrics:
        """
        Analyze group travel metrics for a trip.
        
        Args:
            trip: The trip to analyze
        
        Returns:
            GroupTravelMetrics: Group travel metrics
        """
        num_travelers = len(trip.participants) or 1
        
        metrics = GroupTravelMetrics(
            trip_id=trip.id,
            num_travelers=num_travelers
        )
        
        # Calculate total impact
        metrics.total_carbon_kg = self._calculate_total_carbon(trip)
        metrics.total_cost = self._calculate_total_cost(trip)
        
        # Calculate per person impact
        metrics.per_person_carbon_kg = metrics.total_carbon_kg / num_travelers
        metrics.per_person_cost = metrics.total_cost / num_travelers
        
        # Calculate shared savings
        metrics.shared_transport_savings = self._calculate_transport_savings(trip)
        metrics.shared_accommodation_savings = self._calculate_accommodation_savings(trip)
        metrics.total_savings = metrics.shared_transport_savings + metrics.shared_accommodation_savings
        
        # Calculate efficiency ratio
        individual_carbon = self._calculate_individual_carbon(trip)
        if individual_carbon > 0:
            metrics.efficiency_ratio = metrics.total_carbon_kg / individual_carbon
        else:
            metrics.efficiency_ratio = 1.0
        
        return metrics
    
    def _calculate_total_carbon(self, trip: Trip) -> float:
        """Calculate total carbon emissions for the trip."""
        total = 0.0
        
        # Transportation
        for leg in trip.legs:
            if leg.selected_transportation:
                total += leg.selected_transportation.carbon_emissions_kg
            elif leg.transportation:
                total += leg.transportation[0].carbon_emissions_kg
        
        # Accommodation
        for acc in trip.accommodation:
            total += acc.carbon_emissions_kg
        
        # Activities
        for activity in trip.activities:
            total += activity.carbon_emissions_kg
        
        return total
    
    def _calculate_total_cost(self, trip: Trip) -> float:
        """Calculate total cost for the trip."""
        total = 0.0
        
        # Transportation
        for leg in trip.legs:
            if leg.selected_transportation:
                total += leg.selected_transportation.cost
            elif leg.transportation:
                total += leg.transportation[0].cost
        
        # Accommodation
        for acc in trip.accommodation:
            total += acc.total_cost
        
        # Activities
        for activity in trip.activities:
            total += activity.cost
        
        return total
    
    def _calculate_transport_savings(self, trip: Trip) -> float:
        """
        Calculate savings from shared transportation.
        """
        total_savings = 0.0
        num_travelers = len(trip.participants) or 1
        
        for leg in trip.legs:
            if leg.selected_transportation and leg.selected_transportation.is_shared:
                # Calculate savings per extra person
                base_cost = leg.selected_transportation.cost
                if num_travelers > 1:
                    # Shared transport typically saves ~30% per additional person
                    savings_per_person = base_cost * 0.30 * (num_travelers - 1)
                    total_savings += savings_per_person
        
        return total_savings
    
    def _calculate_accommodation_savings(self, trip: Trip) -> float:
        """
        Calculate savings from shared accommodation.
        """
        total_savings = 0.0
        num_travelers = len(trip.participants) or 1
        
        for acc in trip.accommodation:
            if num_travelers > 1:
                # Shared accommodation typically saves ~40% vs single occupancy
                base_cost = acc.total_cost
                savings_per_extra = base_cost * 0.40 * (num_travelers - 1) / num_travelers
                total_savings += savings_per_extra
        
        return total_savings
    
    def _calculate_individual_carbon(self, trip: Trip) -> float:
        """
        Calculate carbon if everyone traveled individually.
        """
        total = 0.0
        num_travelers = len(trip.participants) or 1
        
        for leg in trip.legs:
            if leg.selected_transportation:
                # Assuming individual travel would use car or taxi
                individual_carbon = leg.selected_transportation.carbon_emissions_kg * 1.5
                total += individual_carbon * num_travelers
        
        return total
    
    def compare_group_sizes(self, 
                           trip: Trip,
                           sizes: List[int] = [1, 2, 4, 6, 8]) -> List[Dict[str, Any]]:
        """
        Compare impacts for different group sizes.
        
        Args:
            trip: The trip
            sizes: List of group sizes to compare
        
        Returns:
            List[Dict]: Comparison results
        """
        results = []
        
        original_participants = trip.participants.copy()
        
        for size in sizes:
            # Create new participants list
            participants = []
            for i in range(size):
                participants.append(
                    TripParticipant(
                        name=f"Traveler {i+1}",
                        age=30,
                        is_adult=True
                    )
                )
            
            trip.participants = participants
            
            # Calculate metrics
            metrics = self.analyze_group_trip(trip)
            
            results.append({
                'group_size': size,
                'total_carbon_kg': metrics.total_carbon_kg,
                'total_cost': metrics.total_cost,
                'per_person_carbon_kg': metrics.per_person_carbon_kg,
                'per_person_cost': metrics.per_person_cost,
                'total_savings': metrics.total_savings,
                'savings_per_person': metrics.total_savings / size if size > 0 else 0,
                'efficiency_ratio': metrics.efficiency_ratio
            })
        
        # Restore original participants
        trip.participants = original_participants
        
        return results
    
    def get_group_recommendation(self, trip: Trip) -> Dict[str, Any]:
        """
        Get recommendations for group travel.
        
        Args:
            trip: The trip
        
        Returns:
            Dict: Recommendations
        """
        num_travelers = len(trip.participants)
        metrics = self.analyze_group_trip(trip)
        
        recommendations = []
        
        # Transportation recommendations
        if num_travelers >= 3:
            recommendations.append("Consider carpooling or renting a van for significant savings")
            recommendations.append("Public transit passes often offer group discounts")
        
        if num_travelers >= 2:
            recommendations.append("Shared accommodation can reduce costs by up to 40%")
        
        # Cost recommendations
        if metrics.per_person_cost > 200:
            recommendations.append("Consider group packages or discounts for activities")
        
        if metrics.shared_transport_savings > 0:
            recommendations.append(f"Shared transportation saves ${metrics.shared_transport_savings:.2f}")
        
        # Environmental recommendations
        if num_travelers >= 4:
            recommendations.append("Group travel reduces per-person carbon footprint significantly")
        
        return {
            'group_size': num_travelers,
            'per_person_savings': metrics.total_savings / num_travelers if num_travelers > 0 else 0,
            'efficiency_ratio': metrics.efficiency_ratio,
            'recommendations': recommendations,
            'best_for': self._determine_best_group_type(trip)
        }
    
    def _determine_best_group_type(self, trip: Trip) -> str:
        """
        Determine the best group type for the trip.
        
        Args:
            trip: The trip
        
        Returns:
            str: Group type recommendation
        """
        num_travelers = len(trip.participants)
        total_distance = sum(leg.distance_km for leg in trip.legs)
        
        if num_travelers == 1:
            return "solo_travel"
        elif num_travelers == 2:
            return "couples_travel"
        elif num_travelers <= 4:
            return "small_group"
        elif num_travelers <= 6:
            return "medium_group"
        else:
            return "large_group"