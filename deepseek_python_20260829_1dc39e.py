"""
Sustainable Travel & Trip Impact Planner - Accommodation Analysis
Analyzes accommodation options and environmental impact.
"""

import logging
from typing import List, Optional, Dict, Any

from travel.models import AccommodationType, AccommodationOption

logger = logging.getLogger(__name__)


class AccommodationAnalyzer:
    """
    Analyzes accommodation options and calculates environmental impact.
    """
    
    def __init__(self):
        """Initialize the accommodation analyzer."""
        self.impact_factors = self._initialize_impact_factors()
        self.cost_factors = self._initialize_cost_factors()
        logger.info("Accommodation Analyzer initialized")
    
    def _initialize_impact_factors(self) -> Dict[AccommodationType, Dict[str, float]]:
        """
        Initialize impact factors for accommodation types.
        Factors are per night per person.
        """
        return {
            AccommodationType.HOTEL: {
                'carbon_kg': 5.0,
                'water_liters': 200.0,
                'energy_kwh': 20.0,
                'waste_kg': 1.0
            },
            AccommodationType.RESORT: {
                'carbon_kg': 8.0,
                'water_liters': 300.0,
                'energy_kwh': 30.0,
                'waste_kg': 1.5
            },
            AccommodationType.HOSTEL: {
                'carbon_kg': 3.0,
                'water_liters': 100.0,
                'energy_kwh': 10.0,
                'waste_kg': 0.5
            },
            AccommodationType.AIRBNB: {
                'carbon_kg': 4.0,
                'water_liters': 150.0,
                'energy_kwh': 15.0,
                'waste_kg': 0.8
            },
            AccommodationType.CAMPING: {
                'carbon_kg': 1.0,
                'water_liters': 50.0,
                'energy_kwh': 5.0,
                'waste_kg': 0.3
            },
            AccommodationType.GLAMPING: {
                'carbon_kg': 2.0,
                'water_liters': 80.0,
                'energy_kwh': 8.0,
                'waste_kg': 0.4
            },
            AccommodationType.RV: {
                'carbon_kg': 4.5,
                'water_liters': 120.0,
                'energy_kwh': 18.0,
                'waste_kg': 0.7
            },
            AccommodationType.VACATION_RENTAL: {
                'carbon_kg': 4.5,
                'water_liters': 160.0,
                'energy_kwh': 18.0,
                'waste_kg': 0.8
            },
            AccommodationType.BED_BREAKFAST: {
                'carbon_kg': 4.0,
                'water_liters': 140.0,
                'energy_kwh': 15.0,
                'waste_kg': 0.7
            },
            AccommodationType.LODGE: {
                'carbon_kg': 5.5,
                'water_liters': 180.0,
                'energy_kwh': 22.0,
                'waste_kg': 0.9
            },
            AccommodationType.CABIN: {
                'carbon_kg': 3.5,
                'water_liters': 120.0,
                'energy_kwh': 12.0,
                'waste_kg': 0.6
            },
            AccommodationType.APARTMENT: {
                'carbon_kg': 4.0,
                'water_liters': 150.0,
                'energy_kwh': 15.0,
                'waste_kg': 0.8
            },
            AccommodationType.HOUSE: {
                'carbon_kg': 6.0,
                'water_liters': 200.0,
                'energy_kwh': 25.0,
                'waste_kg': 1.0
            },
            AccommodationType.ECO_LODGE: {
                'carbon_kg': 1.5,
                'water_liters': 60.0,
                'energy_kwh': 6.0,
                'waste_kg': 0.3
            },
            AccommodationType.COMMUNITY: {
                'carbon_kg': 2.0,
                'water_liters': 70.0,
                'energy_kwh': 8.0,
                'waste_kg': 0.4
            },
            AccommodationType.OTHER: {
                'carbon_kg': 4.0,
                'water_liters': 150.0,
                'energy_kwh': 15.0,
                'waste_kg': 0.8
            }
        }
    
    def _initialize_cost_factors(self) -> Dict[AccommodationType, float]:
        """Initialize cost factors (USD per night)."""
        return {
            AccommodationType.HOTEL: 150.0,
            AccommodationType.RESORT: 300.0,
            AccommodationType.HOSTEL: 40.0,
            AccommodationType.AIRBNB: 80.0,
            AccommodationType.CAMPING: 20.0,
            AccommodationType.GLAMPING: 60.0,
            AccommodationType.RV: 70.0,
            AccommodationType.VACATION_RENTAL: 100.0,
            AccommodationType.BED_BREAKFAST: 90.0,
            AccommodationType.LODGE: 120.0,
            AccommodationType.CABIN: 75.0,
            AccommodationType.APARTMENT: 85.0,
            AccommodationType.HOUSE: 150.0,
            AccommodationType.ECO_LODGE: 60.0,
            AccommodationType.COMMUNITY: 30.0,
            AccommodationType.OTHER: 80.0
        }
    
    def get_accommodation_options(self, 
                                 destination: str,
                                 nights: int,
                                 num_guests: int = 2) -> List[AccommodationOption]:
        """
        Get accommodation options for a destination.
        
        Args:
            destination: Destination location
            nights: Number of nights
            num_guests: Number of guests
        
        Returns:
            List[AccommodationOption]: Available options
        """
        options = []
        
        for acc_type in AccommodationType:
            option = self._calculate_option(acc_type, destination, nights, num_guests)
            options.append(option)
        
        # Sort by sustainability score (carbon emissions)
        options.sort(key=lambda x: x.carbon_emissions_kg)
        
        return options
    
    def _calculate_option(self, 
                         acc_type: AccommodationType,
                         destination: str,
                         nights: int,
                         num_guests: int) -> AccommodationOption:
        """
        Calculate a single accommodation option.
        """
        # Get impact factors
        factors = self.impact_factors.get(acc_type, self.impact_factors[AccommodationType.OTHER])
        
        # Calculate per night per person impacts
        carbon_per_night = factors['carbon_kg'] * num_guests
        water_per_night = factors['water_liters'] * num_guests
        energy_per_night = factors['energy_kwh'] * num_guests
        waste_per_night = factors['waste_kg'] * num_guests
        
        # Calculate total impacts
        total_carbon = carbon_per_night * nights
        total_water = water_per_night * nights
        total_energy = energy_per_night * nights
        total_waste = waste_per_night * nights
        
        # Calculate cost
        cost_per_night = self.cost_factors.get(acc_type, 80.0) * num_guests
        total_cost = cost_per_night * nights
        
        return AccommodationOption(
            type=acc_type,
            name=f"{acc_type.value.replace('_', ' ').title()} in {destination}",
            nights=nights,
            cost_per_night=cost_per_night,
            total_cost=total_cost,
            carbon_emissions_kg=total_carbon,
            water_usage_liters=total_water,
            energy_usage_kwh=total_energy,
            waste_generation_kg=total_waste,
            rating=self._get_rating(acc_type),
            eco_certified=acc_type in [AccommodationType.ECO_LODGE, AccommodationType.COMMUNITY],
            notes=self._get_notes(acc_type, num_guests)
        )
    
    def _get_rating(self, acc_type: AccommodationType) -> float:
        """Get rating for accommodation type."""
        ratings = {
            AccommodationType.HOTEL: 4.0,
            AccommodationType.RESORT: 4.5,
            AccommodationType.HOSTEL: 3.5,
            AccommodationType.AIRBNB: 4.2,
            AccommodationType.CAMPING: 3.8,
            AccommodationType.GLAMPING: 4.3,
            AccommodationType.RV: 3.6,
            AccommodationType.VACATION_RENTAL: 4.1,
            AccommodationType.BED_BREAKFAST: 4.3,
            AccommodationType.LODGE: 4.0,
            AccommodationType.CABIN: 4.2,
            AccommodationType.APARTMENT: 4.0,
            AccommodationType.HOUSE: 4.1,
            AccommodationType.ECO_LODGE: 4.6,
            AccommodationType.COMMUNITY: 3.7,
            AccommodationType.OTHER: 3.5
        }
        return ratings.get(acc_type, 4.0)
    
    def _get_notes(self, acc_type: AccommodationType, num_guests: int) -> str:
        """Get notes for accommodation type."""
        notes = {
            AccommodationType.HOTEL: "Standard hotel with good amenities. Consider eco-certified options.",
            AccommodationType.RESORT: "Luxury resort. High resource usage.",
            AccommodationType.HOSTEL: "Budget-friendly shared accommodation. Lower impact per person.",
            AccommodationType.AIRBNB: "Home-sharing. Often more sustainable than hotels.",
            AccommodationType.CAMPING: "Very low impact. Connect with nature.",
            AccommodationType.GLAMPING: "Camping with amenities. Moderate impact.",
            AccommodationType.RV: "Mobile home. Consider fuel efficiency.",
            AccommodationType.VACATION_RENTAL: "Full apartment. Can be very efficient with groups.",
            AccommodationType.BED_BREAKFAST: "Local and often sustainable. Good for couples.",
            AccommodationType.LODGE: "Nature-focused. Check for eco-certification.",
            AccommodationType.CABIN: "Rustic and low impact. Good for families.",
            AccommodationType.APARTMENT: "City apartment. Efficient for longer stays.",
            AccommodationType.HOUSE: "Full house. Good for large groups.",
            AccommodationType.ECO_LODGE: "Certified sustainable. Best environmental choice.",
            AccommodationType.COMMUNITY: "Community-based. Supports local economy.",
            AccommodationType.OTHER: "Varies by specific property."
        }
        base_note = notes.get(acc_type, "Standard accommodation option.")
        
        if num_guests > 2:
            base_note += f" Suitable for {num_guests} guests."
        
        return base_note
    
    def get_eco_options(self, 
                       destination: str,
                       nights: int,
                       num_guests: int = 2) -> List[AccommodationOption]:
        """
        Get only eco-friendly accommodation options.
        
        Args:
            destination: Destination location
            nights: Number of nights
            num_guests: Number of guests
        
        Returns:
            List[AccommodationOption]: Eco-friendly options
        """
        options = self.get_accommodation_options(destination, nights, num_guests)
        eco_options = [opt for opt in options if opt.eco_certified]
        
        # Filter for truly low-impact options
        filtered = [opt for opt in eco_options if opt.carbon_emissions_kg < 10 * nights]
        
        return filtered if filtered else [opt for opt in options if opt.type in [AccommodationType.CAMPING, AccommodationType.ECO_LODGE]]
    
    def compare_accommodation(self, 
                             options: List[AccommodationOption]) -> Dict[str, Any]:
        """
        Compare accommodation options.
        
        Args:
            options: List of accommodation options
        
        Returns:
            Dict: Comparison results
        """
        if not options:
            return {'message': 'No options to compare'}
        
        best_carbon = min(options, key=lambda x: x.carbon_emissions_kg)
        best_cost = min(options, key=lambda x: x.total_cost)
        best_eco = min(options, key=lambda x: x.carbon_emissions_kg / x.nights)  # Per night
        
        # Calculate averages
        avg_carbon = sum(o.carbon_emissions_kg for o in options) / len(options)
        avg_cost = sum(o.total_cost for o in options) / len(options)
        
        return {
            'total_options': len(options),
            'best_carbon': best_carbon.type.value,
            'best_carbon_kg': best_carbon.carbon_emissions_kg,
            'best_cost': best_cost.type.value,
            'best_cost_amount': best_cost.total_cost,
            'best_eco': best_eco.type.value,
            'average_carbon_kg': avg_carbon,
            'average_cost': avg_cost,
            'recommendation': 'Choose eco-lodge or camping for lowest impact, or hostel for budget option.'
        }