"""
Sequestration Calculator.
Estimates carbon sequestered in soil through backyard composting, perennial planting, and lawn-to-garden conversion.
"""

from typing import Dict, Any


class SequestrationCalculator:
    """Models soil carbon drawdown from regenerative backyard practices."""

    # Mock sequestration rates (kg CO2e sequestered per year)
    COMPOSTING_RATE_PER_HOUSEHOLD = 25.0  # Avoids landfill methane + builds soil carbon
    LAWN_CONVERSION_RATE_PER_SQM = (
        0.5  # Converting turf grass to diverse perennial garden
    )
    PERENNIAL_PLANTING_BONUS = (
        10.0  # Flat bonus for adding fruit trees or deep-rooted perennials
    )

    def __init__(
        self, composting: bool, lawn_converted_sqm: float, has_perennials: bool
    ):
        self.composting = composting
        self.lawn_converted_sqm = max(0.0, lawn_converted_sqm)
        self.has_perennials = has_perennials

    def calculate_sequestration(self) -> Dict[str, Any]:
        """Calculates total estimated annual carbon sequestration."""
        compost_sequestration = (
            self.COMPOSTING_RATE_PER_HOUSEHOLD if self.composting else 0.0
        )
        lawn_sequestration = self.lawn_converted_sqm * self.LAWN_CONVERSION_RATE_PER_SQM
        perennial_sequestration = (
            self.PERENNIAL_PLANTING_BONUS if self.has_perennials else 0.0
        )

        total_sequestered = (
            compost_sequestration + lawn_sequestration + perennial_sequestration
        )

        return {
            "composting_kg": round(compost_sequestration, 2),
            "lawn_conversion_kg": round(lawn_sequestration, 2),
            "perennials_kg": round(perennial_sequestration, 2),
            "total_sequestered_kg": round(total_sequestered, 2),
        }

    def get_practice_recommendations(self) -> list:
        """Generates tips for improving backyard sequestration."""
        recs = []
        if not self.composting:
            recs.append(
                "🗑️ **Start Composting:** Diverting food scraps from the landfill prevents methane emissions and creates carbon-rich soil amendments."
            )
        if self.lawn_converted_sqm < 5.0:
            recs.append(
                "🌱 **Convert Lawn:** Replacing even a small patch of turf grass with native plants or vegetables significantly increases soil carbon storage."
            )
        if not self.has_perennials:
            recs.append(
                "🌳 **Plant Perennials:** Adding fruit trees, berry bushes, or deep-rooted native perennials builds long-term, stable soil carbon."
            )

        if not recs:
            recs.append(
                "🌟 **Excellent!** Your backyard is already a model of regenerative practice."
            )

        return recs
