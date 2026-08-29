"""
Home Agriculture Tracker.
Calculates the carbon footprint avoided by growing specific vegetables/herbs at home versus purchasing them industrially.
"""

from typing import Dict, Any, List


class HomeAgricultureTracker:
    """Estimates emissions avoided through home food production."""

    # Mock emission factors for industrial production + transport (kg CO2e per kg of produce)
    INDUSTRIAL_FACTORS = {
        "tomatoes": 1.5,
        "lettuce": 2.0,
        "carrots": 0.4,
        "potatoes": 0.3,
        "herbs": 3.0,
        "berries": 2.5,
    }

    # Average yield per square meter per year (kg)
    YIELD_PER_SQM = {
        "tomatoes": 5.0,
        "lettuce": 3.0,
        "carrots": 4.0,
        "potatoes": 3.5,
        "herbs": 1.0,
        "berries": 2.0,
    }

    def __init__(
        self, garden_area_sqm: float, crops_grown: List[str], composting: bool
    ):
        self.garden_area_sqm = max(0.0, garden_area_sqm)
        self.crops_grown = [crop.lower() for crop in crops_grown]
        self.composting = composting

    def calculate_avoided_emissions(self) -> Dict[str, Any]:
        """Calculates the total carbon footprint avoided by home growing."""
        total_avoided_kg = 0.0
        crop_breakdown = {}

        # Distribute garden area evenly among chosen crops for simplicity
        area_per_crop = (
            self.garden_area_sqm / len(self.crops_grown) if self.crops_grown else 0.0
        )

        for crop in self.crops_grown:
            if crop in self.INDUSTRIAL_FACTORS:
                yield_kg = area_per_crop * self.YIELD_PER_SQM[crop]
                avoided_kg = yield_kg * self.INDUSTRIAL_FACTORS[crop]
                total_avoided_kg += avoided_kg
                crop_breakdown[crop] = round(avoided_kg, 2)

        return {
            "garden_area_sqm": self.garden_area_sqm,
            "crops_grown": self.crops_grown,
            "total_avoided_emissions_kg": round(total_avoided_kg, 2),
            "crop_breakdown_kg": crop_breakdown,
        }

    def get_regeneration_score(
        self, avoided_emissions_kg: float, sequestered_kg: float
    ) -> float:
        """
        Calculates a 'Regeneration Score' from 0-100.
        Based on a mock benchmark of 50 kg CO2e avoided/sequestered per year for a 'highly regenerative' small yard.
        """
        total_positive_impact = avoided_emissions_kg + sequestered_kg
        benchmark = 50.0

        score = (total_positive_impact / benchmark) * 100
        return min(100.0, max(0.0, round(score, 1)))
