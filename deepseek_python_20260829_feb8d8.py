"""
Sustainable Travel & Trip Impact Planner - Data Models
Comprehensive models for travel planning and analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Set
import uuid
import json


class TransportationMode(Enum):
    """Transportation modes for trip legs."""
    WALKING = "walking"
    CYCLING = "cycling"
    PUBLIC_TRANSIT = "public_transit"
    TRAIN = "train"
    BUS = "bus"
    CAR = "car"
    CARPOOL = "carpool"
    ELECTRIC_VEHICLE = "electric_vehicle"
    HYBRID_VEHICLE = "hybrid_vehicle"
    FLIGHT = "flight"
    FERRY = "ferry"
    TAXI = "taxi"
    RIDESHARE = "rideshare"
    SCOOTER = "scooter"
    MOTORBIKE = "motorbike"
    SHUTTLE = "shuttle"
    OTHER = "other"


class AccommodationType(Enum):
    """Types of accommodation."""
    HOTEL = "hotel"
    RESORT = "resort"
    HOSTEL = "hostel"
    AIRBNB = "airbnb"
    CAMPING = "camping"
    GLAMPING = "glamping"
    RV = "rv"
    VACATION_RENTAL = "vacation_rental"
    BED_BREAKFAST = "bed_breakfast"
    LODGE = "lodge"
    CABIN = "cabin"
    APARTMENT = "apartment"
    HOUSE = "house"
    ECO_LODGE = "eco_lodge"
    COMMUNITY = "community"
    OTHER = "other"


class ActivityType(Enum):
    """Types of trip activities."""
    SIGHTSEEING = "sightseeing"
    HIKING = "hiking"
    BEACH = "beach"
    MUSEUM = "museum"
    SHOPPING = "shopping"
    DINING = "dining"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    WELLNESS = "wellness"
    EDUCATION = "education"
    VOLUNTEER = "volunteer"
    BUSINESS = "business"
    RELAXATION = "relaxation"
    ADVENTURE = "adventure"
    CULTURAL = "cultural"
    NATURE = "nature"
    FESTIVAL = "festival"
    OTHER = "other"


class TripStatus(Enum):
    """Status of a trip."""
    PLANNED = "planned"
    BOOKED = "booked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ComparisonMetric(Enum):
    """Metrics for trip comparison."""
    CARBON = "carbon"
    COST = "cost"
    TIME = "time"
    ENERGY = "energy"
    WATER = "water"
    WASTE = "waste"
    OVERALL = "overall"


@dataclass
class TripParticipant:
    """Represents a participant in a trip."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    age: int = 0
    user_id: str = ""
    is_adult: bool = True
    preferences: Dict[str, Any] = field(default_factory=dict)
    dietary_restrictions: List[str] = field(default_factory=list)
    mobility_requirements: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'user_id': self.user_id,
            'is_adult': self.is_adult,
            'preferences': self.preferences,
            'dietary_restrictions': self.dietary_restrictions,
            'mobility_requirements': self.mobility_requirements
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TripParticipant':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            age=data.get('age', 0),
            user_id=data.get('user_id', ''),
            is_adult=data.get('is_adult', True),
            preferences=data.get('preferences', {}),
            dietary_restrictions=data.get('dietary_restrictions', []),
            mobility_requirements=data.get('mobility_requirements', [])
        )


@dataclass
class TransportationOption:
    """Transportation option for a trip leg."""
    mode: TransportationMode = TransportationMode.CAR
    distance_km: float = 0.0
    travel_time_hours: float = 0.0
    cost: float = 0.0
    carbon_emissions_kg: float = 0.0
    energy_consumption_kwh: float = 0.0
    passengers: int = 1
    is_shared: bool = False
    provider: str = ""
    booking_reference: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'mode': self.mode.value,
            'distance_km': self.distance_km,
            'travel_time_hours': self.travel_time_hours,
            'cost': self.cost,
            'carbon_emissions_kg': self.carbon_emissions_kg,
            'energy_consumption_kwh': self.energy_consumption_kwh,
            'passengers': self.passengers,
            'is_shared': self.is_shared,
            'provider': self.provider,
            'booking_reference': self.booking_reference,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransportationOption':
        return cls(
            mode=TransportationMode(data.get('mode', 'car')),
            distance_km=data.get('distance_km', 0.0),
            travel_time_hours=data.get('travel_time_hours', 0.0),
            cost=data.get('cost', 0.0),
            carbon_emissions_kg=data.get('carbon_emissions_kg', 0.0),
            energy_consumption_kwh=data.get('energy_consumption_kwh', 0.0),
            passengers=data.get('passengers', 1),
            is_shared=data.get('is_shared', False),
            provider=data.get('provider', ''),
            booking_reference=data.get('booking_reference', ''),
            notes=data.get('notes', '')
        )


@dataclass
class AccommodationOption:
    """Accommodation option for a trip."""
    type: AccommodationType = AccommodationType.HOTEL
    name: str = ""
    nights: int = 1
    cost_per_night: float = 0.0
    total_cost: float = 0.0
    carbon_emissions_kg: float = 0.0
    water_usage_liters: float = 0.0
    energy_usage_kwh: float = 0.0
    waste_generation_kg: float = 0.0
    rating: float = 0.0
    eco_certified: bool = False
    booking_reference: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value,
            'name': self.name,
            'nights': self.nights,
            'cost_per_night': self.cost_per_night,
            'total_cost': self.total_cost,
            'carbon_emissions_kg': self.carbon_emissions_kg,
            'water_usage_liters': self.water_usage_liters,
            'energy_usage_kwh': self.energy_usage_kwh,
            'waste_generation_kg': self.waste_generation_kg,
            'rating': self.rating,
            'eco_certified': self.eco_certified,
            'booking_reference': self.booking_reference,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccommodationOption':
        return cls(
            type=AccommodationType(data.get('type', 'hotel')),
            name=data.get('name', ''),
            nights=data.get('nights', 1),
            cost_per_night=data.get('cost_per_night', 0.0),
            total_cost=data.get('total_cost', 0.0),
            carbon_emissions_kg=data.get('carbon_emissions_kg', 0.0),
            water_usage_liters=data.get('water_usage_liters', 0.0),
            energy_usage_kwh=data.get('energy_usage_kwh', 0.0),
            waste_generation_kg=data.get('waste_generation_kg', 0.0),
            rating=data.get('rating', 0.0),
            eco_certified=data.get('eco_certified', False),
            booking_reference=data.get('booking_reference', ''),
            notes=data.get('notes', '')
        )


@dataclass
class Activity:
    """Activity during a trip."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    type: ActivityType = ActivityType.SIGHTSEEING
    description: str = ""
    duration_hours: float = 1.0
    cost: float = 0.0
    carbon_emissions_kg: float = 0.0
    location: str = ""
    booking_required: bool = False
    booking_reference: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'description': self.description,
            'duration_hours': self.duration_hours,
            'cost': self.cost,
            'carbon_emissions_kg': self.carbon_emissions_kg,
            'location': self.location,
            'booking_required': self.booking_required,
            'booking_reference': self.booking_reference,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Activity':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            type=ActivityType(data.get('type', 'sightseeing')),
            description=data.get('description', ''),
            duration_hours=data.get('duration_hours', 1.0),
            cost=data.get('cost', 0.0),
            carbon_emissions_kg=data.get('carbon_emissions_kg', 0.0),
            location=data.get('location', ''),
            booking_required=data.get('booking_required', False),
            booking_reference=data.get('booking_reference', ''),
            notes=data.get('notes', '')
        )


@dataclass
class TripLeg:
    """
    Represents a leg of a trip.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    origin: str = ""
    destination: str = ""
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    transportation: List[TransportationOption] = field(default_factory=list)
    selected_transportation: Optional[TransportationOption] = None
    distance_km: float = 0.0
    order: int = 0
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'origin': self.origin,
            'destination': self.destination,
            'departure_time': self.departure_time.isoformat() if self.departure_time else None,
            'arrival_time': self.arrival_time.isoformat() if self.arrival_time else None,
            'transportation': [t.to_dict() for t in self.transportation],
            'selected_transportation': self.selected_transportation.to_dict() if self.selected_transportation else None,
            'distance_km': self.distance_km,
            'order': self.order,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TripLeg':
        leg = cls(
            id=data.get('id', str(uuid.uuid4())),
            origin=data.get('origin', ''),
            destination=data.get('destination', ''),
            departure_time=datetime.fromisoformat(data['departure_time']) if data.get('departure_time') else None,
            arrival_time=datetime.fromisoformat(data['arrival_time']) if data.get('arrival_time') else None,
            distance_km=data.get('distance_km', 0.0),
            order=data.get('order', 0),
            notes=data.get('notes', '')
        )
        
        for transport_data in data.get('transportation', []):
            leg.transportation.append(TransportationOption.from_dict(transport_data))
        
        if data.get('selected_transportation'):
            leg.selected_transportation = TransportationOption.from_dict(data['selected_transportation'])
        
        return leg


@dataclass
class Trip:
    """
    Represents a complete trip.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    user_id: str = ""
    household_id: Optional[str] = None
    status: TripStatus = TripStatus.PLANNED
    
    # Trip details
    origin: str = ""
    destination: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: int = 0
    
    # Components
    legs: List[TripLeg] = field(default_factory=list)
    accommodation: List[AccommodationOption] = field(default_factory=list)
    activities: List[Activity] = field(default_factory=list)
    participants: List[TripParticipant] = field(default_factory=list)
    
    # Impact metrics
    total_carbon_kg: float = 0.0
    total_energy_kwh: float = 0.0
    total_water_liters: float = 0.0
    total_waste_kg: float = 0.0
    total_cost: float = 0.0
    
    # Sustainability score
    sustainability_score: float = 0.0  # 0-100
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'household_id': self.household_id,
            'status': self.status.value,
            'origin': self.origin,
            'destination': self.destination,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'duration_days': self.duration_days,
            'legs': [l.to_dict() for l in self.legs],
            'accommodation': [a.to_dict() for a in self.accommodation],
            'activities': [a.to_dict() for a in self.activities],
            'participants': [p.to_dict() for p in self.participants],
            'total_carbon_kg': self.total_carbon_kg,
            'total_energy_kwh': self.total_energy_kwh,
            'total_water_liters': self.total_water_liters,
            'total_waste_kg': self.total_waste_kg,
            'total_cost': self.total_cost,
            'sustainability_score': self.sustainability_score,
            'recommendations': self.recommendations,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'notes': self.notes,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trip':
        trip = cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            description=data.get('description', ''),
            user_id=data.get('user_id', ''),
            household_id=data.get('household_id'),
            status=TripStatus(data.get('status', 'planned')),
            origin=data.get('origin', ''),
            destination=data.get('destination', ''),
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
            end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None,
            duration_days=data.get('duration_days', 0),
            total_carbon_kg=data.get('total_carbon_kg', 0.0),
            total_energy_kwh=data.get('total_energy_kwh', 0.0),
            total_water_liters=data.get('total_water_liters', 0.0),
            total_waste_kg=data.get('total_waste_kg', 0.0),
            total_cost=data.get('total_cost', 0.0),
            sustainability_score=data.get('sustainability_score', 0.0),
            recommendations=data.get('recommendations', []),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now(),
            notes=data.get('notes', ''),
            tags=data.get('tags', [])
        )
        
        # Load legs
        for leg_data in data.get('legs', []):
            trip.legs.append(TripLeg.from_dict(leg_data))
        
        # Load accommodation
        for acc_data in data.get('accommodation', []):
            trip.accommodation.append(AccommodationOption.from_dict(acc_data))
        
        # Load activities
        for activity_data in data.get('activities', []):
            trip.activities.append(Activity.from_dict(activity_data))
        
        # Load participants
        for participant_data in data.get('participants', []):
            trip.participants.append(TripParticipant.from_dict(participant_data))
        
        return trip
    
    def get_total_distance(self) -> float:
        """Get total trip distance in km."""
        return sum(leg.distance_km for leg in self.legs)
    
    def get_total_duration_hours(self) -> float:
        """Get total trip duration in hours."""
        total = 0.0
        for leg in self.legs:
            if leg.selected_transportation:
                total += leg.selected_transportation.travel_time_hours
            elif leg.transportation:
                total += leg.transportation[0].travel_time_hours
        return total
    
    def get_transportation_modes(self) -> List[str]:
        """Get all transportation modes used."""
        modes = []
        for leg in self.legs:
            if leg.selected_transportation:
                modes.append(leg.selected_transportation.mode.value)
            elif leg.transportation:
                modes.append(leg.transportation[0].mode.value)
        return modes


@dataclass
class EnvironmentalImpact:
    """
    Comprehensive environmental impact of a trip.
    """
    trip_id: str = ""
    trip_name: str = ""
    
    # Carbon emissions
    transport_carbon_kg: float = 0.0
    accommodation_carbon_kg: float = 0.0
    activity_carbon_kg: float = 0.0
    total_carbon_kg: float = 0.0
    
    # Energy consumption
    transport_energy_kwh: float = 0.0
    accommodation_energy_kwh: float = 0.0
    total_energy_kwh: float = 0.0
    
    # Water usage
    accommodation_water_liters: float = 0.0
    total_water_liters: float = 0.0
    
    # Waste generation
    accommodation_waste_kg: float = 0.0
    total_waste_kg: float = 0.0
    
    # Per person metrics
    per_person_carbon_kg: float = 0.0
    per_person_energy_kwh: float = 0.0
    per_person_water_liters: float = 0.0
    
    # Scores
    carbon_score: float = 0.0  # 0-100 (lower is better)
    energy_score: float = 0.0
    water_score: float = 0.0
    waste_score: float = 0.0
    overall_environmental_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'trip_id': self.trip_id,
            'trip_name': self.trip_name,
            'transport_carbon_kg': self.transport_carbon_kg,
            'accommodation_carbon_kg': self.accommodation_carbon_kg,
            'activity_carbon_kg': self.activity_carbon_kg,
            'total_carbon_kg': self.total_carbon_kg,
            'transport_energy_kwh': self.transport_energy_kwh,
            'accommodation_energy_kwh': self.accommodation_energy_kwh,
            'total_energy_kwh': self.total_energy_kwh,
            'accommodation_water_liters': self.accommodation_water_liters,
            'total_water_liters': self.total_water_liters,
            'accommodation_waste_kg': self.accommodation_waste_kg,
            'total_waste_kg': self.total_waste_kg,
            'per_person_carbon_kg': self.per_person_carbon_kg,
            'per_person_energy_kwh': self.per_person_energy_kwh,
            'per_person_water_liters': self.per_person_water_liters,
            'carbon_score': self.carbon_score,
            'energy_score': self.energy_score,
            'water_score': self.water_score,
            'waste_score': self.waste_score,
            'overall_environmental_score': self.overall_environmental_score
        }


@dataclass
class FinancialAnalysis:
    """
    Comprehensive financial analysis of a trip.
    """
    trip_id: str = ""
    trip_name: str = ""
    
    # Cost breakdown
    transport_cost: float = 0.0
    accommodation_cost: float = 0.0
    activity_cost: float = 0.0
    food_cost: float = 0.0
    misc_cost: float = 0.0
    total_cost: float = 0.0
    
    # Per person
    per_person_cost: float = 0.0
    
    # Savings
    potential_savings: float = 0.0
    savings_percentage: float = 0.0
    
    # Budget
    budget: float = 0.0
    under_budget: float = 0.0
    over_budget: float = 0.0
    
    # Cost efficiency
    cost_per_day: float = 0.0
    cost_per_km: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'trip_id': self.trip_id,
            'trip_name': self.trip_name,
            'transport_cost': self.transport_cost,
            'accommodation_cost': self.accommodation_cost,
            'activity_cost': self.activity_cost,
            'food_cost': self.food_cost,
            'misc_cost': self.misc_cost,
            'total_cost': self.total_cost,
            'per_person_cost': self.per_person_cost,
            'potential_savings': self.potential_savings,
            'savings_percentage': self.savings_percentage,
            'budget': self.budget,
            'under_budget': self.under_budget,
            'over_budget': self.over_budget,
            'cost_per_day': self.cost_per_day,
            'cost_per_km': self.cost_per_km
        }


@dataclass
class AlternativeItinerary:
    """
    Alternative trip itinerary with different focus.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trip_id: str = ""
    name: str = ""
    description: str = ""
    focus: str = ""  # lowest_carbon, lowest_cost, fastest, etc.
    
    # Components
    legs: List[TripLeg] = field(default_factory=list)
    accommodation: List[AccommodationOption] = field(default_factory=list)
    activities: List[Activity] = field(default_factory=list)
    
    # Metrics
    total_carbon_kg: float = 0.0
    total_cost: float = 0.0
    total_duration_hours: float = 0.0
    sustainability_score: float = 0.0
    
    # Comparison
    improvement_over_original: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'trip_id': self.trip_id,
            'name': self.name,
            'description': self.description,
            'focus': self.focus,
            'legs': [l.to_dict() for l in self.legs],
            'accommodation': [a.to_dict() for a in self.accommodation],
            'activities': [a.to_dict() for a in self.activities],
            'total_carbon_kg': self.total_carbon_kg,
            'total_cost': self.total_cost,
            'total_duration_hours': self.total_duration_hours,
            'sustainability_score': self.sustainability_score,
            'improvement_over_original': self.improvement_over_original
        }


@dataclass
class GroupTravelMetrics:
    """
    Group travel metrics for trip analysis.
    """
    trip_id: str = ""
    num_travelers: int = 1
    
    # Total impact
    total_carbon_kg: float = 0.0
    total_cost: float = 0.0
    
    # Per person
    per_person_carbon_kg: float = 0.0
    per_person_cost: float = 0.0
    
    # Shared savings
    shared_transport_savings: float = 0.0
    shared_accommodation_savings: float = 0.0
    total_savings: float = 0.0
    
    # Efficiency
    efficiency_ratio: float = 0.0  # impact per person / total impact
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'trip_id': self.trip_id,
            'num_travelers': self.num_travelers,
            'total_carbon_kg': self.total_carbon_kg,
            'total_cost': self.total_cost,
            'per_person_carbon_kg': self.per_person_carbon_kg,
            'per_person_cost': self.per_person_cost,
            'shared_transport_savings': self.shared_transport_savings,
            'shared_accommodation_savings': self.shared_accommodation_savings,
            'total_savings': self.total_savings,
            'efficiency_ratio': self.efficiency_ratio
        }


@dataclass
class TripComparison:
    """
    Comparison between multiple trips or itineraries.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trips: List[Trip] = field(default_factory=list)
    itineraries: List[AlternativeItinerary] = field(default_factory=list)
    comparison_type: str = ""  # environmental, financial, time, overall
    
    # Results
    best_overall: str = ""
    best_environmental: str = ""
    best_financial: str = ""
    best_time: str = ""
    
    # Rankings
    rankings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'trips': [t.to_dict() for t in self.trips],
            'itineraries': [i.to_dict() for i in self.itineraries],
            'comparison_type': self.comparison_type,
            'best_overall': self.best_overall,
            'best_environmental': self.best_environmental,
            'best_financial': self.best_financial,
            'best_time': self.best_time,
            'rankings': self.rankings,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class TravelHistory:
    """
    User travel history tracking.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    trips: List[Trip] = field(default_factory=list)
    
    # Aggregated metrics
    total_trips: int = 0
    total_distance_km: float = 0.0
    total_carbon_kg: float = 0.0
    total_cost: float = 0.0
    total_duration_days: int = 0
    
    # Averages
    avg_carbon_per_trip: float = 0.0
    avg_cost_per_trip: float = 0.0
    avg_duration_days: float = 0.0
    
    # Trends
    carbon_trend: float = 0.0  # Percentage change
    cost_trend: float = 0.0
    
    # Most common
    most_common_transport: str = ""
    most_common_destination: str = ""
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'trips': [t.to_dict() for t in self.trips],
            'total_trips': self.total_trips,
            'total_distance_km': self.total_distance_km,
            'total_carbon_kg': self.total_carbon_kg,
            'total_cost': self.total_cost,
            'total_duration_days': self.total_duration_days,
            'avg_carbon_per_trip': self.avg_carbon_per_trip,
            'avg_cost_per_trip': self.avg_cost_per_trip,
            'avg_duration_days': self.avg_duration_days,
            'carbon_trend': self.carbon_trend,
            'cost_trend': self.cost_trend,
            'most_common_transport': self.most_common_transport,
            'most_common_destination': self.most_common_destination,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class TripRecommendation:
    """
    Personalized trip recommendation.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    trip_id: str = ""
    recommendation_type: str = ""  # sustainable, budget, balanced, etc.
    reason: str = ""
    confidence: float = 0.0
    
    # Specific suggestions
    transport_suggestions: List[str] = field(default_factory=list)
    accommodation_suggestions: List[str] = field(default_factory=list)
    activity_suggestions: List[str] = field(default_factory=list)
    
    # Impact
    estimated_savings: Dict[str, float] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'trip_id': self.trip_id,
            'recommendation_type': self.recommendation_type,
            'reason': self.reason,
            'confidence': self.confidence,
            'transport_suggestions': self.transport_suggestions,
            'accommodation_suggestions': self.accommodation_suggestions,
            'activity_suggestions': self.activity_suggestions,
            'estimated_savings': self.estimated_savings,
            'created_at': self.created_at.isoformat()
        }