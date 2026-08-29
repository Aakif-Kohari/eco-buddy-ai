"""
Event Footprint Calculator.
Estimates emissions based on guest count, catering choices, travel distances, and venue energy usage.
"""

from typing import Dict, Any, List


class EventFootprintCalculator:
    """Calculates the total carbon footprint of a planned event."""

    # Emission factors (kg CO2e per unit)
    CATERING_FACTORS = {
        "vegan": 0.5,
        "vegetarian": 1.2,
        "poultry": 2.5,
        "beef_heavy": 5.0,
    }

    TRAVEL_FACTORS = {
        "walking_biking": 0.0,
        "public_transit": 0.1,
        "carpool": 0.15,
        "single_occupancy_vehicle": 0.25,
        "flight_short": 0.35,
    }

    VENUE_FACTORS = {
        "renewable_energy": 0.05,
        "standard_grid": 0.2,
        "outdoor_natural": 0.01,
    }

    WASTE_FACTORS = {
        "zero_waste_compost": 0.1,
        "standard_recycling": 0.3,
        "landfill_heavy": 0.8,
    }

    def __init__(
        self,
        guest_count: int,
        catering_type: str,
        avg_travel_distance_km: float,
        travel_mode: str,
        venue_type: str,
        waste_management: str,
        duration_hours: float,
    ):
        """
        Initializes the calculator with event parameters.
        Ensures all numeric inputs are non-negative to prevent calculation errors.
        """
        self.guest_count = max(0, guest_count)
        self.catering_type = catering_type.lower()
        self.avg_travel_distance_km = max(0.0, avg_travel_distance_km)
        self.travel_mode = travel_mode.lower()
        self.venue_type = venue_type.lower()
        self.waste_management = waste_management.lower()
        self.duration_hours = max(0.1, duration_hours)

    def calculate_footprint(self) -> Dict[str, Any]:
        """Calculates the detailed carbon footprint of the event."""
        if self.guest_count == 0:
            return self._zero_guest_result()

        # 1. Catering emissions
        catering_factor = self.CATERING_FACTORS.get(self.catering_type, 2.0)
        catering_emissions = self.guest_count * catering_factor

        # 2. Travel emissions (round trip assumed)
        travel_factor = self.TRAVEL_FACTORS.get(self.travel_mode, 0.25)
        travel_emissions = (
            self.guest_count * (self.avg_travel_distance_km * 2) * travel_factor
        )

        # 3. Venue emissions (per guest per hour)
        venue_factor = self.VENUE_FACTORS.get(self.venue_type, 0.2)
        venue_emissions = self.guest_count * self.duration_hours * venue_factor

        # 4. Waste emissions (per guest)
        waste_factor = self.WASTE_FACTORS.get(self.waste_management, 0.3)
        waste_emissions = self.guest_count * waste_factor

        total_emissions = (
            catering_emissions + travel_emissions + venue_emissions + waste_emissions
        )

        return {
            "guest_count": self.guest_count,
            "total_emissions_kg": round(total_emissions, 2),
            "per_guest_emissions_kg": round(total_emissions / self.guest_count, 2),
            "breakdown": {
                "catering_kg": round(catering_emissions, 2),
                "travel_kg": round(travel_emissions, 2),
                "venue_kg": round(venue_emissions, 2),
                "waste_kg": round(waste_emissions, 2),
            },
            "green_swaps": self._generate_green_swaps(),
        }

    def _zero_guest_result(self) -> Dict[str, Any]:
        """Returns a zero-emission result for virtual or cancelled events."""
        return {
            "guest_count": 0,
            "total_emissions_kg": 0.0,
            "per_guest_emissions_kg": 0.0,
            "breakdown": {
                "catering_kg": 0.0,
                "travel_kg": 0.0,
                "venue_kg": 0.0,
                "waste_kg": 0.0,
            },
            "green_swaps": [
                "Consider hosting a virtual event to maintain zero emissions!"
            ],
        }

    def _generate_green_swaps(self) -> List[str]:
        """Generates actionable recommendations to reduce the event's footprint."""
        swaps = []
        if self.catering_type in ["beef_heavy", "poultry"]:
            swaps.append(
                "🥗 **Catering:** Switch to a plant-based or vegetarian menu to reduce catering emissions by up to 70%."
            )
        if self.travel_mode in ["single_occupancy_vehicle", "flight_short"]:
            swaps.append(
                "🚌 **Travel:** Encourage carpooling, public transit, or choose a venue closer to the majority of guests."
            )
        if self.venue_type == "standard_grid":
            swaps.append(
                "⚡ **Venue:** Look for venues powered by 100% renewable energy or outdoor natural settings."
            )
        if self.waste_management == "landfill_heavy":
            swaps.append(
                "♻️ **Waste:** Implement a zero-waste policy with composting and strict recycling stations."
            )

        if not swaps:
            swaps.append(
                "🌟 **Excellent!** Your event is already planned with top-tier sustainable choices."
            )

        return swaps
