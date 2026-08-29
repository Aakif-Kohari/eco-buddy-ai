"""
Sustainable Travel & Trip Impact Planner - Alternative Itineraries
Generates alternative trip configurations for different priorities.
"""

import logging
import copy
from typing import List, Optional, Dict, Any

from travel.models import (
    Trip, TripLeg, AlternativeItinerary, TransportationMode,
    AccommodationType, TripParticipant
)
from travel.transportation import TransportationAnalyzer
from travel.accommodation import AccommodationAnalyzer
from travel.environmental import EnvironmentalAnalyzer
from travel.financial import FinancialAnalyzer

logger = logging.getLogger(__name__)


class AlternativeGenerator:
    """
    Generates alternative trip itineraries based on different priorities.
    """
    
    def __init__(self):
        """Initialize the alternative generator."""
        self.transport_analyzer = TransportationAnalyzer()
        self.acc_analyzer = AccommodationAnalyzer()
        self.env_analyzer = EnvironmentalAnalyzer()
        self.fin_analyzer = FinancialAnalyzer()
        logger.info("Alternative Generator initialized")
    
    def generate_alternatives(self, trip: Trip) -> List[AlternativeItinerary]:
        """
        Generate alternative itineraries for a trip.
        
        Args:
            trip: The original trip
        
        Returns:
            List[AlternativeItinerary]: Alternative itineraries
        """
        alternatives = []
        
        # Lowest carbon alternative
        alternatives.append(self._generate_lowest_carbon(trip))
        
        # Lowest cost alternative
        alternatives.append(self._generate_lowest_cost(trip))
        
        # Fastest alternative
        alternatives.append(self._generate_fastest(trip))
        
        # Best overall sustainability
        alternatives.append(self._generate_best_sustainability(trip))
        
        # Eco-friendly (with eco-lodges, trains, etc.)
        alternatives.append(self._generate_eco_friendly(trip))
        
        # Balanced alternative
        alternatives.append(self._generate_balanced(trip))
        
        # Sort by sustainability score
        alternatives.sort(key=lambda x: x.sustainability_score, reverse=True)
        
        return alternatives
    
    def _generate_lowest_carbon(self, trip: Trip) -> AlternativeItinerary:
        """
        Generate lowest carbon itinerary.
        """
        alt = AlternativeItinerary(
            trip_id=trip.id,
            name=f"{trip.name} - Lowest Carbon",
            description="Optimized for minimum carbon emissions",
            focus="lowest_carbon"
        )
        
        # Deep copy original trip
        alt_trip = copy.deepcopy(trip)
        
        # Replace transportation with lowest carbon options
        for leg in alt_trip.legs:
            # Get lowest carbon option
            options = self.transport_analyzer.calculate_transportation_options(
                leg.origin,
                leg.destination,
                leg.distance_km,
                len(trip.participants)
            )
            
            if options:
                # Choose walking/cycling for short distances, train for long
                best_option = min(options, key=lambda x: x.carbon_emissions_kg)
                leg.selected_transportation = best_option
        
        # Replace accommodation with eco-lodges or low-impact options
        alt_trip.accommodation = self.acc_analyzer.get_eco_options(
            trip.destination,
            trip.duration_days,
            len(trip.participants)
        )
        
        # Calculate metrics
        alt_legs = [leg for leg in alt_trip.legs if leg.selected_transportation]
        alt.total_carbon_kg = sum(leg.selected_transportation.carbon_emissions_kg for leg in alt_legs)
        alt.total_cost = self._calculate_total_cost(alt_trip)
        alt.total_duration_hours = sum(leg.selected_transportation.travel_time_hours for leg in alt_legs)
        alt.sustainability_score = self._calculate_sustainability_score(alt_trip)
        
        # Calculate improvements
        original_carbon = trip.total_carbon_kg
        alt.improvement_over_original = {
            'carbon_reduction_percentage': ((original_carbon - alt.total_carbon_kg) / original_carbon * 100) if original_carbon > 0 else 0,
            'cost_change_percentage': ((alt.total_cost - trip.total_cost) / trip.total_cost * 100) if trip.total_cost > 0 else 0
        }
        
        return alt
    
    def _generate_lowest_cost(self, trip: Trip) -> AlternativeItinerary:
        """
        Generate lowest cost itinerary.
        """
        alt = AlternativeItinerary(
            trip_id=trip.id,
            name=f"{trip.name} - Lowest Cost",
            description="Optimized for minimum cost",
            focus="lowest_cost"
        )
        
        alt_trip = copy.deepcopy(trip)
        
        # Replace transportation with cheapest options
        for leg in alt_trip.legs:
            options = self.transport_analyzer.calculate_transportation_options(
                leg.origin,
                leg.destination,
                leg.distance_km,
                len(trip.participants)
            )
            
            if options:
                best_option = min(options, key=lambda x: x.cost)
                leg.selected_transportation = best_option
        
        # Replace accommodation with budget options
        acc_options = self.acc_analyzer.get_accommodation_options(
            trip.destination,
            trip.duration_days,
            len(trip.participants)
        )
        alt_trip.accommodation = [min(acc_options, key=lambda x: x.total_cost)]
        
        # Remove expensive activities
        alt_trip.activities = [a for a in alt_trip.activities if a.cost < 50]
        
        # Calculate metrics
        alt_legs = [leg for leg in alt_trip.legs if leg.selected_transportation]
        alt.total_carbon_kg = sum(leg.selected_transportation.carbon_emissions_kg for leg in alt_legs)
        alt.total_cost = self._calculate_total_cost(alt_trip)
        alt.total_duration_hours = sum(leg.selected_transportation.travel_time_hours for leg in alt_legs)
        alt.sustainability_score = self._calculate_sustainability_score(alt_trip)
        
        # Calculate improvements
        original_cost = trip.total_cost
        alt.improvement_over_original = {
            'cost_reduction_percentage': ((original_cost - alt.total_cost) / original_cost * 100) if original_cost > 0 else 0,
            'carbon_change_percentage': ((alt.total_carbon_kg - trip.total_carbon_kg) / trip.total_carbon_kg * 100) if trip.total_carbon_kg > 0 else 0
        }
        
        return alt
    
    def _generate_fastest(self, trip: Trip) -> AlternativeItinerary:
        """
        Generate fastest itinerary.
        """
        alt = AlternativeItinerary(
            trip_id=trip.id,
            name=f"{trip.name} - Fastest",
            description="Optimized for minimum travel time",
            focus="fastest"
        )
        
        alt_trip = copy.deepcopy(trip)
        
        # Replace transportation with fastest options
        for leg in alt_trip.legs:
            options = self.transport_analyzer.calculate_transportation_options(
                leg.origin,
                leg.destination,
                leg.distance_km,
                len(trip.participants)
            )
            
            if options:
                # For short distances, use car/taxi; for long, use flight
                if leg.distance_km < 100:
                    best_option = min([o for o in options if o.mode in [TransportationMode.CAR, TransportationMode.TAXI]], 
                                    key=lambda x: x.travel_time_hours, default=options[0])
                else:
                    best_option = min([o for o in options if o.mode in [TransportationMode.FLIGHT, TransportationMode.TRAIN]], 
                                    key=lambda x: x.travel_time_hours, default=options[0])
                leg.selected_transportation = best_option
        
        # Keep original accommodation (fastest trip still needs good sleep)
        
        # Calculate metrics
        alt_legs = [leg for leg in alt_trip.legs if leg.selected_transportation]
        alt.total_carbon_kg = sum(leg.selected_transportation.carbon_emissions_kg for leg in alt_legs)
        alt.total_cost = self._calculate_total_cost(alt_trip)
        alt.total_duration_hours = sum(leg.selected_transportation.travel_time_hours for leg in alt_legs)
        alt.sustainability_score = self._calculate_sustainability_score(alt_trip)
        
        alt.improvement_over_original = {
            'time_reduction_percentage': ((trip.get_total_duration_hours() - alt.total_duration_hours) / 
                                         trip.get_total_duration_hours() * 100) if trip.get_total_duration_hours() > 0 else 0
        }
        
        return alt
    
    def _generate_best_sustainability(self, trip: Trip) -> AlternativeItinerary:
        """
        Generate best overall sustainability itinerary.
        """
        alt = AlternativeItinerary(
            trip_id=trip.id,
            name=f"{trip.name} - Best Sustainability",
            description="Optimized for overall sustainability",
            focus="best_sustainability"
        )
        
        alt_trip = copy.deepcopy(trip)
        
        # Balanced approach: good carbon, cost, and comfort
        for leg in alt_trip.legs:
            options = self.transport_analyzer.calculate_transportation_options(
                leg.origin,
                leg.destination,
                leg.distance_km,
                len(trip.participants)
            )
            
            if options:
                # Choose train for long, public transit/electric for short
                if leg.distance_km > 500:
                    best_option = next((o for o in options if o.mode == TransportationMode.TRAIN), options[0])
                elif leg.distance_km > 100:
                    best_option = next((o for o in options if o.mode in [TransportationMode.ELECTRIC_VEHICLE, TransportationMode.BUS]), options[0])
                else:
                    best_option = next((o for o in options if o.mode in [TransportationMode.PUBLIC_TRANSIT, TransportationMode.CYCLING]), options[0])
                leg.selected_transportation = best_option
        
        # Mix of eco-lodge and comfortable accommodation
        eco_options = self.acc_analyzer.get_eco_options(
            trip.destination,
            trip.duration_days,
            len(trip.participants)
        )
        if eco_options:
            alt_trip.accommodation = [eco_options[0]]
        else:
            alt_trip.accommodation = [min(self.acc_analyzer.get_accommodation_options(
                trip.destination, trip.duration_days, len(trip.participants)), 
                key=lambda x: x.carbon_emissions_kg)]
        
        # Keep meaningful activities
        alt_trip.activities = [a for a in alt_trip.activities if a.carbon_emissions_kg < 10]
        
        # Calculate metrics
        alt_legs = [leg for leg in alt_trip.legs if leg.selected_transportation]
        alt.total_carbon_kg = sum(leg.selected_transportation.carbon_emissions_kg for leg in alt_legs)
        alt.total_cost = self._calculate_total_cost(alt_trip)
        alt.total_duration_hours = sum(leg.selected_transportation.travel_time_hours for leg in alt_legs)
        alt.sustainability_score = self._calculate_sustainability_score(alt_trip)
        
        return alt
    
    def _generate_eco_friendly(self, trip: Trip) -> AlternativeItinerary:
        """
        Generate eco-friendly itinerary.
        """
        alt = AlternativeItinerary(
            trip_id=trip.id,
            name=f"{trip.name} - Eco-Friendly",
            description="Optimized for eco-friendly choices",
            focus="eco_friendly"
        )
        
        alt_trip = copy.deepcopy(trip)
        
        # Use only sustainable transportation
        sustainable_modes = [
            TransportationMode.WALKING,
            TransportationMode.CYCLING,
            TransportationMode.PUBLIC_TRANSIT,
            TransportationMode.TRAIN,
            TransportationMode.ELECTRIC_VEHICLE
        ]
        
        for leg in alt_trip.legs:
            options = self.transport_analyzer.calculate_transportation_options(
                leg.origin,
                leg.destination,
                leg.distance_km,
                len(trip.participants)
            )
            
            sustainable_options = [o for o in options if o.mode in sustainable_modes]
            if sustainable_options:
                best_option = min(sustainable_options, key=lambda x: x.carbon_emissions_kg)
                leg.selected_transportation = best_option
            elif options:
                leg.selected_transportation = min(options, key=lambda x: x.carbon_emissions_kg)
        
        # Use only eco-certified accommodation
        alt_trip.accommodation = self.acc_analyzer.get_eco_options(
            trip.destination,
            trip.duration_days,
            len(trip.participants)
        )
        
        # Include nature and low-impact activities
        alt_trip.activities = [a for a in alt_trip.activities 
                              if a.type.value in ['nature', 'hiking', 'education', 'cultural']]
        
        # Calculate metrics
        alt_legs = [leg for leg in alt_trip.legs if leg.selected_transportation]
        alt.total_carbon_kg = sum(leg.selected_transportation.carbon_emissions_kg for leg in alt_legs)
        alt.total_cost = self._calculate_total_cost(alt_trip)
        alt.total_duration_hours = sum(leg.selected_transportation.travel_time_hours for leg in alt_legs)
        alt.sustainability_score = self._calculate_sustainability_score(alt_trip)
        
        return alt
    
    def _generate_balanced(self, trip: Trip) -> AlternativeItinerary:
        """
        Generate balanced itinerary (compromise between cost and sustainability).
        """
        alt = AlternativeItinerary(
            trip_id=trip.id,
            name=f"{trip.name} - Balanced",
            description="Optimized for balance of cost and sustainability",
            focus="balanced"
        )
        
        alt_trip = copy.deepcopy(trip)
        
        # Balanced transportation choices
        for leg in alt_trip.legs:
            options = self.transport_analyzer.calculate_transportation_options(
                leg.origin,
                leg.destination,
                leg.distance_km,
                len(trip.participants)
            )
            
            if options:
                # Find options with good balance of carbon and cost
                balanced_options = [o for o in options if o.carbon_emissions_kg < 0.15 and o.cost < 0.25 * leg.distance_km]
                if balanced_options:
                    # Choose the one with best carbon
                    best_option = min(balanced_options, key=lambda x: x.carbon_emissions_kg)
                else:
                    best_option = min(options, key=lambda x: x.carbon_emissions_kg + x.cost / 100)
                leg.selected_transportation = best_option
        
        # Balanced accommodation (good value, moderate sustainability)
        acc_options = self.acc_analyzer.get_accommodation_options(
            trip.destination,
            trip.duration_days,
            len(trip.participants)
        )
        if acc_options:
            # Choose option with good balance
            alt_trip.accommodation = [min(acc_options[:5], key=lambda x: x.carbon_emissions_kg * 0.5 + x.total_cost / 200)]
        
        # Keep reasonable activities
        alt_trip.activities = [a for a in alt_trip.activities if a.cost < 100]
        
        # Calculate metrics
        alt_legs = [leg for leg in alt_trip.legs if leg.selected_transportation]
        alt.total_carbon_kg = sum(leg.selected_transportation.carbon_emissions_kg for leg in alt_legs)
        alt.total_cost = self._calculate_total_cost(alt_trip)
        alt.total_duration_hours = sum(leg.selected_transportation.travel_time_hours for leg in alt_legs)
        alt.sustainability_score = self._calculate_sustainability_score(alt_trip)
        
        return alt
    
    def _calculate_total_cost(self, trip: Trip) -> float:
        """Calculate total cost of a trip."""
        transport = sum(leg.selected_transportation.cost for leg in trip.legs if leg.selected_transportation)
        accommodation = sum(acc.total_cost for acc in trip.accommodation)
        activities = sum(act.cost for act in trip.activities)
        food = len(trip.participants) * 40 * (trip.duration_days or 1)  # Moderate budget
        
        subtotal = transport + accommodation + activities + food
        misc = subtotal * 0.10
        
        return subtotal + misc
    
    def _calculate_sustainability_score(self, trip: Trip) -> float:
        """Calculate sustainability score for a trip."""
        # Simplified score based on carbon and cost
        carbon_score = max(0, 100 - (trip.total_carbon_kg / 10))
        cost_score = max(0, 100 - (trip.total_cost / 100))
        
        return (carbon_score + cost_score) / 2