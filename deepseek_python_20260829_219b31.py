"""
Sustainable Travel & Trip Impact Planner - Recommendations
Personalized travel recommendations based on user preferences.
"""

import logging
from typing import List, Optional, Dict, Any

from travel.models import (
    Trip, TripRecommendation, TransportationMode,
    AccommodationType, TripParticipant
)

logger = logging.getLogger(__name__)


class TravelRecommendationEngine:
    """
    Generates personalized travel recommendations.
    """
    
    def __init__(self):
        """Initialize the recommendation engine."""
        logger.info("Travel Recommendation Engine initialized")
    
    def generate_recommendations(self, 
                                 trip: Trip,
                                 user_context: Dict[str, Any]) -> List[TripRecommendation]:
        """
        Generate personalized recommendations for a trip.
        
        Args:
            trip: The trip
            user_context: User preferences and goals
        
        Returns:
            List[TripRecommendation]: Recommendations
        """
        recommendations = []
        
        # Transportation recommendations
        transport_recs = self._generate_transport_recommendations(trip, user_context)
        recommendations.extend(transport_recs)
        
        # Accommodation recommendations
        acc_recs = self._generate_accommodation_recommendations(trip, user_context)
        recommendations.extend(acc_recs)
        
        # Activity recommendations
        activity_recs = self._generate_activity_recommendations(trip, user_context)
        recommendations.extend(activity_recs)
        
        # Sustainability recommendations
        sust_recs = self._generate_sustainability_recommendations(trip, user_context)
        recommendations.extend(sust_recs)
        
        # Budget recommendations
        budget_recs = self._generate_budget_recommendations(trip, user_context)
        recommendations.extend(budget_recs)
        
        return recommendations
    
    def _generate_transport_recommendations(self, 
                                           trip: Trip,
                                           user_context: Dict[str, Any]) -> List[TripRecommendation]:
        """
        Generate transportation recommendations.
        """
        recommendations = []
        
        preferences = user_context.get('preferences', {})
        preferred_transport = preferences.get('transport_mode', [])
        
        for leg in trip.legs:
            if not leg.transportation:
                continue
            
            # Check if user has preferred modes
            if preferred_transport:
                preferred_options = [
                    opt for opt in leg.transportation 
                    if opt.mode.value in preferred_transport
                ]
                
                if preferred_options:
                    best_preferred = min(preferred_options, key=lambda x: x.carbon_emissions_kg)
                    rec = TripRecommendation(
                        user_id=user_context.get('user_id', ''),
                        trip_id=trip.id,
                        recommendation_type='transportation',
                        reason=f"Based on your preference for {best_preferred.mode.value} transportation",
                        confidence=0.8,
                        transport_suggestions=[
                            f"Use {best_preferred.mode.value} for leg from {leg.origin} to {leg.destination}"
                        ]
                    )
                    recommendations.append(rec)
            
            # Recommend lower carbon alternatives
            if leg.transportation:
                current_carbon = leg.selected_transportation.carbon_emissions_kg if leg.selected_transportation else leg.transportation[0].carbon_emissions_kg
                lower_carbon_options = [opt for opt in leg.transportation if opt.carbon_emissions_kg < current_carbon * 0.7]
                
                if lower_carbon_options:
                    best_lower = min(lower_carbon_options, key=lambda x: x.carbon_emissions_kg)
                    rec = TripRecommendation(
                        user_id=user_context.get('user_id', ''),
                        trip_id=trip.id,
                        recommendation_type='sustainable_transport',
                        reason=f"Reduce emissions by using {best_lower.mode.value} instead",
                        confidence=0.9,
                        transport_suggestions=[
                            f"Consider {best_lower.mode.value} for leg from {leg.origin} to {leg.destination}",
                            f"This would save approximately {current_carbon - best_lower.carbon_emissions_kg:.1f}kg CO2e"
                        ]
                    )
                    recommendations.append(rec)
        
        return recommendations
    
    def _generate_accommodation_recommendations(self, 
                                               trip: Trip,
                                               user_context: Dict[str, Any]) -> List[TripRecommendation]:
        """
        Generate accommodation recommendations.
        """
        recommendations = []
        
        if not trip.accommodation:
            return recommendations
        
        current_acc = trip.accommodation[0]
        
        # Recommend eco-certified accommodation
        if not current_acc.eco_certified:
            eco_options = [acc for acc in trip.accommodation if acc.eco_certified]
            
            if eco_options:
                best_eco = min(eco_options, key=lambda x: x.carbon_emissions_kg)
                rec = TripRecommendation(
                    user_id=user_context.get('user_id', ''),
                    trip_id=trip.id,
                    recommendation_type='accommodation',
                    reason="Choose eco-certified accommodation for lower environmental impact",
                    confidence=0.85,
                    accommodation_suggestions=[
                        f"Consider {best_eco.type.value.replace('_', ' ').title()} instead",
                        f"This would save approximately {current_acc.carbon_emissions_kg - best_eco.carbon_emissions_kg:.1f}kg CO2e"
                    ],
                    estimated_savings={
                        'carbon': current_acc.carbon_emissions_kg - best_eco.carbon_emissions_kg
                    }
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _generate_activity_recommendations(self, 
                                          trip: Trip,
                                          user_context: Dict[str, Any]) -> List[TripRecommendation]:
        """
        Generate activity recommendations.
        """
        recommendations = []
        
        if not trip.activities:
            return recommendations
        
        # Recommend low-impact activities
        high_impact_activities = [a for a in trip.activities if a.carbon_emissions_kg > 10]
        
        if high_impact_activities:
            rec = TripRecommendation(
                user_id=user_context.get('user_id', ''),
                trip_id=trip.id,
                recommendation_type='activities',
                reason="Some activities have high environmental impact",
                confidence=0.7,
                activity_suggestions=[
                    f"Consider replacing {a.name} with a lower-impact alternative" 
                    for a in high_impact_activities[:2]
                ]
            )
            recommendations.append(rec)
        
        # Recommend nature/educational activities based on user goals
        if user_context.get('goals'):
            rec = TripRecommendation(
                user_id=user_context.get('user_id', ''),
                trip_id=trip.id,
                recommendation_type='activities',
                reason="These activities align with your sustainability goals",
                confidence=0.8,
                activity_suggestions=[
                    "Consider visiting local nature reserves",
                    "Include educational tours about sustainability",
                    "Try volunteering activities"
                ]
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _generate_sustainability_recommendations(self, 
                                                trip: Trip,
                                                user_context: Dict[str, Any]) -> List[TripRecommendation]:
        """
        Generate sustainability recommendations.
        """
        recommendations = []
        
        # Check if trip is sustainable
        if trip.sustainability_score < 50:
            rec = TripRecommendation(
                user_id=user_context.get('user_id', ''),
                trip_id=trip.id,
                recommendation_type='sustainability',
                reason="Your trip has low sustainability score. Consider these improvements",
                confidence=0.9,
                transport_suggestions=[
                    "Use trains instead of flights for long distances",
                    "Use public transit instead of taxis",
                    "Walk or cycle for short trips"
                ],
                accommodation_suggestions=[
                    "Choose eco-lodges or hostels with green certifications",
                    "Limit hotel changes to reduce transport"
                ],
                activity_suggestions=[
                    "Choose local and cultural activities",
                    "Avoid activities with high energy consumption"
                ],
                estimated_savings={
                    'carbon': trip.total_carbon_kg * 0.3
                }
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _generate_budget_recommendations(self, 
                                        trip: Trip,
                                        user_context: Dict[str, Any]) -> List[TripRecommendation]:
        """
        Generate budget recommendations.
        """
        recommendations = []
        
        budget = user_context.get('budget')
        if not budget:
            return recommendations
        
        if trip.total_cost > budget:
            rec = TripRecommendation(
                user_id=user_context.get('user_id', ''),
                trip_id=trip.id,
                recommendation_type='budget',
                reason=f"Trip cost (${trip.total_cost:.2f}) exceeds budget (${budget:.2f})",
                confidence=0.9,
                transport_suggestions=[
                    "Use budget transportation options (bus, public transit)",
                    "Consider fewer or shorter legs"
                ],
                accommodation_suggestions=[
                    "Choose hostels or budget hotels",
                    "Limit luxury amenities"
                ],
                activity_suggestions=[
                    "Look for free activities and attractions",
                    "Limit paid tours and excursions"
                ],
                estimated_savings={
                    'cost': trip.total_cost - budget
                }
            )
            recommendations.append(rec)
        elif trip.total_cost < budget * 0.5:
            rec = TripRecommendation(
                user_id=user_context.get('user_id', ''),
                trip_id=trip.id,
                recommendation_type='upgrade',
                reason="You have budget for some upgrades while staying within budget",
                confidence=0.7,
                transport_suggestions=[
                    "Consider upgrading to higher comfort options",
                    "Add an extra destination"
                ],
                accommodation_suggestions=[
                    "Choose a higher-rated hotel",
                    "Extend your stay"
                ],
                activity_suggestions=[
                    "Add more premium experiences"
                ]
            )
            recommendations.append(rec)
        
        return recommendations