"""
Aviation Carbon Optimizer.
Calculates flight emissions based on distance, aircraft efficiency mock data, and cabin class multipliers.
"""

from typing import Dict, Any, List


class AviationCarbonOptimizer:
    """Optimizes and calculates carbon footprints for air travel."""

    # Base emission factor: kg CO2e per passenger-km
    BASE_EMISSION_FACTOR = 0.15

    # Cabin class multipliers (space and weight penalty)
    CLASS_MULTIPLIERS = {
        "economy": 1.0,
        "premium_economy": 1.6,
        "business": 3.0,
        "first": 4.0,
    }

    # Layover penalty multiplier (extra takeoff/landing cycles are highly emissive)
    LAYOVER_PENALTY = 1.25

    def __init__(self, distance_km: float, cabin_class: str, has_layover: bool):
        self.distance_km = max(100.0, distance_km)  # Minimum realistic flight distance
        self.cabin_class = cabin_class.lower()
        self.has_layover = has_layover

    def calculate_emissions(self) -> Dict[str, Any]:
        """Calculates the total carbon footprint of the flight."""
        base_emissions = self.distance_km * self.BASE_EMISSION_FACTOR
        class_multiplier = self.CLASS_MULTIPLIERS.get(self.cabin_class, 1.0)

        adjusted_emissions = base_emissions * class_multiplier

        if self.has_layover:
            adjusted_emissions *= self.LAYOVER_PENALTY
            routing_type = "With Layover"
        else:
            routing_type = "Direct"

        return {
            "distance_km": self.distance_km,
            "cabin_class": self.cabin_class.title(),
            "routing_type": routing_type,
            "base_emissions_kg": round(base_emissions, 2),
            "total_emissions_kg": round(adjusted_emissions, 2),
            "multiplier_applied": class_multiplier
            * (self.LAYOVER_PENALTY if self.has_layover else 1.0),
        }

    def compare_with_rail(self) -> Dict[str, Any]:
        """Compares the flight emissions with a hypothetical high-speed rail alternative."""
        # Rail is only viable for distances under ~1000 km
        if self.distance_km > 1000:
            return {
                "viable": False,
                "message": "Rail alternative not viable for distances over 1000 km.",
            }

        # Rail emission factor: ~0.04 kg CO2e per passenger-km
        rail_emissions = self.distance_km * 0.04
        flight_emissions = self.calculate_emissions()["total_emissions_kg"]

        savings_kg = flight_emissions - rail_emissions
        savings_pct = (
            (savings_kg / flight_emissions) * 100 if flight_emissions > 0 else 0
        )

        return {
            "viable": True,
            "flight_emissions_kg": round(flight_emissions, 2),
            "rail_emissions_kg": round(rail_emissions, 2),
            "savings_kg": round(savings_kg, 2),
            "savings_pct": round(savings_pct, 1),
        }

    def get_recommendations(self) -> List[str]:
        """Generates actionable recommendations for reducing aviation footprint."""
        recs = []
        if self.cabin_class in ["business", "first"]:
            recs.append(
                "✈️ **Cabin Class:** Downgrading to Economy can reduce your flight's carbon footprint by up to 75% due to space efficiency."
            )
        if self.has_layover:
            recs.append(
                "🛫 **Routing:** Choose direct flights whenever possible. Takeoffs and landings account for a significant portion of flight emissions."
            )
        if self.distance_km < 800:
            recs.append(
                "🚆 **Alternative:** For distances under 800km, high-speed rail is almost always a lower-carbon and often faster door-to-door alternative."
            )

        if not recs:
            recs.append(
                "🌟 **Good Choice:** You've selected a relatively efficient routing. Consider purchasing verified SAF or carbon offsets for this trip."
            )

        return recs
