"""
Sustainable Travel & Trip Impact Planner - Financial Analysis
Analyzes financial aspects of trips.
"""

import logging
from typing import List, Optional, Dict, Any

from travel.models import (
    Trip, FinancialAnalysis, TripLeg, AccommodationOption, Activity
)

logger = logging.getLogger(__name__)


class FinancialAnalyzer:
    """
    Analyzes financial aspects of trips.
    """
    
    def __init__(self):
        """Initialize the financial analyzer."""
        self.daily_food_costs = {
            'budget': 20.0,
            'moderate': 40.0,
            'luxury': 80.0
        }
        self.misc_percentage = 0.10  # 10% for miscellaneous expenses
        logger.info("Financial Analyzer initialized")
    
    def analyze_trip_cost(self, trip: Trip, food_budget: str = 'moderate') -> FinancialAnalysis:
        """
        Analyze trip costs.
        
        Args:
            trip: The trip to analyze
            food_budget: Food budget level ('budget', 'moderate', 'luxury')
        
        Returns:
            FinancialAnalysis: Cost analysis
        """
        analysis = FinancialAnalysis(
            trip_id=trip.id,
            trip_name=trip.name
        )
        
        # Calculate transport costs
        analysis.transport_cost = self._calculate_transport_cost(trip)
        
        # Calculate accommodation costs
        analysis.accommodation_cost = self._calculate_accommodation_cost(trip)
        
        # Calculate activity costs
        analysis.activity_cost = self._calculate_activity_cost(trip)
        
        # Calculate food costs
        analysis.food_cost = self._calculate_food_cost(trip, food_budget)
        
        # Calculate miscellaneous costs
        subtotal = (
            analysis.transport_cost +
            analysis.accommodation_cost +
            analysis.activity_cost +
            analysis.food_cost
        )
        analysis.misc_cost = subtotal * self.misc_percentage
        
        # Calculate total
        analysis.total_cost = subtotal + analysis.misc_cost
        
        # Calculate per person
        num_participants = len(trip.participants) or 1
        analysis.per_person_cost = analysis.total_cost / num_participants
        
        # Calculate per day
        analysis.cost_per_day = analysis.total_cost / (trip.duration_days or 1)
        
        # Calculate cost per km
        total_distance = sum(leg.distance_km for leg in trip.legs)
        analysis.cost_per_km = analysis.total_cost / total_distance if total_distance > 0 else 0
        
        return analysis
    
    def _calculate_transport_cost(self, trip: Trip) -> float:
        """Calculate total transportation cost."""
        total = 0.0
        
        for leg in trip.legs:
            if leg.selected_transportation:
                total += leg.selected_transportation.cost
            elif leg.transportation:
                total += leg.transportation[0].cost
        
        return total
    
    def _calculate_accommodation_cost(self, trip: Trip) -> float:
        """Calculate total accommodation cost."""
        total = 0.0
        
        for acc in trip.accommodation:
            total += acc.total_cost
        
        return total
    
    def _calculate_activity_cost(self, trip: Trip) -> float:
        """Calculate total activity cost."""
        total = 0.0
        
        for activity in trip.activities:
            total += activity.cost
        
        return total
    
    def _calculate_food_cost(self, trip: Trip, budget_level: str) -> float:
        """Calculate total food cost."""
        daily_cost = self.daily_food_costs.get(budget_level, 40.0)
        
        # Adjust for number of participants
        num_participants = len(trip.participants) or 1
        daily_cost *= num_participants
        
        # Calculate total for trip duration
        total_days = trip.duration_days or 1
        
        return daily_cost * total_days
    
    def compare_trip_costs(self, 
                          analysis1: FinancialAnalysis,
                          analysis2: FinancialAnalysis) -> Dict[str, Any]:
        """
        Compare costs of two trips.
        
        Args:
            analysis1: First analysis
            analysis2: Second analysis
        
        Returns:
            Dict: Comparison results
        """
        cost_diff = analysis1.total_cost - analysis2.total_cost
        cost_diff_pct = ((cost_diff / analysis1.total_cost) * 100) if analysis1.total_cost > 0 else 0
        
        return {
            'cost_difference': cost_diff,
            'cost_difference_percentage': cost_diff_pct,
            'cheaper_trip': analysis2.trip_name if cost_diff > 0 else analysis1.trip_name,
            'better_value': analysis2.trip_name if analysis2.per_person_cost < analysis1.per_person_cost else analysis1.trip_name,
            'cost_breakdown': {
                'trip1': {
                    'transport': analysis1.transport_cost,
                    'accommodation': analysis1.accommodation_cost,
                    'activities': analysis1.activity_cost,
                    'food': analysis1.food_cost,
                    'misc': analysis1.misc_cost
                },
                'trip2': {
                    'transport': analysis2.transport_cost,
                    'accommodation': analysis2.accommodation_cost,
                    'activities': analysis2.activity_cost,
                    'food': analysis2.food_cost,
                    'misc': analysis2.misc_cost
                }
            }
        }
    
    def calculate_potential_savings(self, 
                                   current_trip: Trip,
                                   alternative_trip: Trip) -> Dict[str, Any]:
        """
        Calculate potential savings from choosing alternative trip.
        
        Args:
            current_trip: Current/planned trip
            alternative_trip: Alternative trip
        
        Returns:
            Dict: Savings analysis
        """
        current_cost = self._calculate_total_cost(current_trip)
        alternative_cost = self._calculate_total_cost(alternative_trip)
        
        savings = current_cost - alternative_cost
        
        return {
            'current_cost': current_cost,
            'alternative_cost': alternative_cost,
            'potential_savings': savings,
            'savings_percentage': (savings / current_cost * 100) if current_cost > 0 else 0,
            'recommendation': 'Choose alternative' if savings > 0 else 'Stick with current plan'
        }
    
    def _calculate_total_cost(self, trip: Trip) -> float:
        """Calculate total cost of a trip."""
        transport = self._calculate_transport_cost(trip)
        accommodation = self._calculate_accommodation_cost(trip)
        activities = self._calculate_activity_cost(trip)
        food = self._calculate_food_cost(trip, 'moderate')
        
        subtotal = transport + accommodation + activities + food
        misc = subtotal * self.misc_percentage
        
        return subtotal + misc
    
    def get_cost_breakdown_percentage(self, analysis: FinancialAnalysis) -> Dict[str, float]:
        """
        Get cost breakdown as percentages.
        
        Args:
            analysis: Financial analysis
        
        Returns:
            Dict: Cost percentages
        """
        if analysis.total_cost == 0:
            return {}
        
        return {
            'transport': (analysis.transport_cost / analysis.total_cost) * 100,
            'accommodation': (analysis.accommodation_cost / analysis.total_cost) * 100,
            'activities': (analysis.activity_cost / analysis.total_cost) * 100,
            'food': (analysis.food_cost / analysis.total_cost) * 100,
            'misc': (analysis.misc_cost / analysis.total_cost) * 100
        }