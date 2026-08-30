"""
Sustainable Travel & Trip Impact Planner - Trip Comparisons
Compares multiple trips and itineraries.
"""

import logging
import statistics
from typing import List, Optional, Dict, Any

from travel.models import (
    Trip, TripComparison, AlternativeItinerary,
    ComparisonMetric
)
from travel.environmental import EnvironmentalAnalyzer
from travel.financial import FinancialAnalyzer

logger = logging.getLogger(__name__)


class TripComparator:
    """
    Compares multiple trips and itineraries.
    """
    
    def __init__(self):
        """Initialize the trip comparator."""
        self.env_analyzer = EnvironmentalAnalyzer()
        self.fin_analyzer = FinancialAnalyzer()
        logger.info("Trip Comparator initialized")
    
    def compare_trips(self, trips: List[Trip]) -> TripComparison:
        """
        Compare multiple trips.
        
        Args:
            trips: List of trips to compare
        
        Returns:
            TripComparison: Comparison results
        """
        if len(trips) < 2:
            return TripComparison(
                trips=trips,
                comparison_type="single"
            )
        
        comparison = TripComparison(
            trips=trips,
            comparison_type="multi"
        )
        
        # Calculate metrics for each trip
        trip_metrics = []
        for trip in trips:
            env_impact = self.env_analyzer.calculate_trip_impact(trip)
            fin_analysis = self.fin_analyzer.analyze_trip_cost(trip)
            
            metrics = {
                'name': trip.name,
                'carbon_kg': env_impact.total_carbon_kg,
                'cost': fin_analysis.total_cost,
                'duration_hours': trip.get_total_duration_hours(),
                'sustainability_score': env_impact.overall_environmental_score,
                'per_person_cost': fin_analysis.per_person_cost,
                'participants': len(trip.participants)
            }
            trip_metrics.append(metrics)
        
        # Find best in each category
        if trip_metrics:
            # Best overall (highest sustainability score with reasonable cost)
            best_overall = max(trip_metrics, key=lambda x: x['sustainability_score'] * 0.6 - (x['cost'] / 1000) * 0.4)
            comparison.best_overall = best_overall['name']
            
            # Best environmental
            best_env = min(trip_metrics, key=lambda x: x['carbon_kg'])
            comparison.best_environmental = best_env['name']
            
            # Best financial
            best_fin = min(trip_metrics, key=lambda x: x['cost'])
            comparison.best_financial = best_fin['name']
            
            # Best time
            best_time = min(trip_metrics, key=lambda x: x['duration_hours'])
            comparison.best_time = best_time['name']
        
        # Create rankings
        comparison.rankings = self._create_rankings(trip_metrics)
        
        return comparison
    
    def _create_rankings(self, metrics: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Create rankings for each metric.
        
        Args:
            metrics: List of trip metrics
        
        Returns:
            Dict: Rankings
        """
        rankings = {
            'sustainability': [],
            'carbon': [],
            'cost': [],
            'time': [],
            'value': []  # Best value for money
        }
        
        if not metrics:
            return rankings
        
        # Sort and rank
        # Sustainability (highest first)
        sorted_sust = sorted(metrics, key=lambda x: x['sustainability_score'], reverse=True)
        rankings['sustainability'] = [m['name'] for m in sorted_sust]
        
        # Carbon (lowest first)
        sorted_carbon = sorted(metrics, key=lambda x: x['carbon_kg'])
        rankings['carbon'] = [m['name'] for m in sorted_carbon]
        
        # Cost (lowest first)
        sorted_cost = sorted(metrics, key=lambda x: x['cost'])
        rankings['cost'] = [m['name'] for m in sorted_cost]
        
        # Time (shortest first)
        sorted_time = sorted(metrics, key=lambda x: x['duration_hours'])
        rankings['time'] = [m['name'] for m in sorted_time]
        
        # Value (sustainability score per dollar)
        sorted_value = sorted(metrics, key=lambda x: x['sustainability_score'] / (x['cost'] + 1), reverse=True)
        rankings['value'] = [m['name'] for m in sorted_value]
        
        return rankings
    
    def compare_itineraries(self, 
                           itineraries: List[AlternativeItinerary]) -> Dict[str, Any]:
        """
        Compare alternative itineraries.
        
        Args:
            itineraries: List of alternatives
        
        Returns:
            Dict: Comparison results
        """
        if len(itineraries) < 2:
            return {'message': 'Need at least 2 itineraries to compare'}
        
        comparison = {
            'itineraries': [i.name for i in itineraries],
            'metrics': {},
            'best': {}
        }
        
        for metric in ['total_carbon_kg', 'total_cost', 'total_duration_hours', 'sustainability_score']:
            values = [getattr(i, metric) for i in itineraries]
            
            comparison['metrics'][metric] = {
                'values': values,
                'min': min(values),
                'max': max(values),
                'average': statistics.mean(values) if values else 0
            }
            
            # Determine best
            if metric == 'sustainability_score':
                best_idx = values.index(max(values))
            else:
                best_idx = values.index(min(values))
            
            comparison['best'][metric] = {
                'itinerary': itineraries[best_idx].name,
                'value': values[best_idx]
            }
        
        # Calculate improvement potential
        best_sust = min(itineraries, key=lambda x: x.total_carbon_kg)
        worst_sust = max(itineraries, key=lambda x: x.total_carbon_kg)
        
        comparison['improvement_potential'] = {
            'carbon_reduction_potential': ((worst_sust.total_carbon_kg - best_sust.total_carbon_kg) / 
                                          worst_sust.total_carbon_kg * 100) if worst_sust.total_carbon_kg > 0 else 0,
            'cost_savings_potential': ((worst_sust.total_cost - best_sust.total_cost) / 
                                       worst_sust.total_cost * 100) if worst_sust.total_cost > 0 else 0
        }
        
        return comparison
    
    def get_recommendation(self, comparison: TripComparison) -> Dict[str, Any]:
        """
        Get recommendation based on comparison.
        
        Args:
            comparison: Trip comparison
        
        Returns:
            Dict: Recommendation
        """
        if not comparison.trips:
            return {'message': 'No trips to compare'}
        
        # Find the best trip based on user preferences
        # Default: balance of sustainability and cost
        
        recommendations = []
        
        # Sustainability-focused
        if comparison.best_environmental:
            recommendations.append({
                'focus': 'sustainability',
                'trip': comparison.best_environmental,
                'reason': 'Lowest carbon emissions of all options',
                'suggestion': 'Choose this trip for the best environmental impact'
            })
        
        # Budget-focused
        if comparison.best_financial:
            recommendations.append({
                'focus': 'budget',
                'trip': comparison.best_financial,
                'reason': 'Lowest cost of all options',
                'suggestion': 'Choose this trip for the best value'
            })
        
        # Time-focused
        if comparison.best_time:
            recommendations.append({
                'focus': 'time',
                'trip': comparison.best_time,
                'reason': 'Shortest travel time of all options',
                'suggestion': 'Choose this trip if you are time-constrained'
            })
        
        # Overall
        if comparison.best_overall:
            recommendations.append({
                'focus': 'overall',
                'trip': comparison.best_overall,
                'reason': 'Best balance of sustainability, cost, and time',
                'suggestion': 'This is the most balanced option overall'
            })
        
        return {
            'recommendations': recommendations,
            'best_overall': comparison.best_overall,
            'rankings': comparison.rankings
        }