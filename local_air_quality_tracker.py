"""
Local Air Quality Tracker.
Estimates the localized PM2.5 and NOx impact of a user's transport and energy choices on their specific neighborhood.
"""

from typing import Dict, Any
from environmental_justice_mapper import EnvironmentalJusticeMapper


class LocalAirQualityTracker:
    """Calculates the marginal local pollution impact of specific user activities."""

    # Marginal emission factors for local pollutants (grams per unit)
    POLLUTANT_FACTORS = {
        "ice_car_mile": {"pm25_g": 0.05, "nox_g": 0.30},
        "ev_car_mile": {
            "pm25_g": 0.01,
            "nox_g": 0.02,
        },  # Tire/brake wear + grid marginal
        "gas_generator_hour": {"pm25_g": 2.5, "nox_g": 8.0},
        "wood_burning_hour": {"pm25_g": 15.0, "nox_g": 5.0},
    }

    def __init__(self, mapper: EnvironmentalJusticeMapper):
        self.mapper = mapper

    def calculate_activity_impact(
        self, zip_code: str, activity: str, quantity: float
    ) -> Dict[str, Any]:
        """
        Calculates the additional pollutant load from a specific activity.

        Args:
            zip_code: The region where the activity occurs.
            activity: The type of activity (e.g., "ice_car_mile").
            quantity: The amount of the activity (e.g., miles, hours).
        """
        region = self.mapper.get_region_profile(zip_code)
        if not region:
            raise ValueError("Unknown zip code")

        factors = self.POLLUTANT_FACTORS.get(activity)
        if not factors:
            raise ValueError("Unknown activity type")

        added_pm25 = factors["pm25_g"] * quantity
        added_nox = factors["nox_g"] * quantity

        # Calculate new estimated local levels (simplified linear addition for demonstration)
        # In reality, dispersion models are non-linear, but this shows marginal contribution
        new_pm25 = region["baseline_pm25"] + (
            added_pm25 / 1000.0
        )  # Convert g to µg/m³ (simplified)
        new_nox = region["baseline_nox"] + (added_nox / 1000.0)

        return {
            "region_name": region["region_name"],
            "activity": activity.replace("_", " ").title(),
            "quantity": quantity,
            "added_pm25_g": round(added_pm25, 3),
            "added_nox_g": round(added_nox, 3),
            "estimated_new_pm25": round(new_pm25, 2),
            "estimated_new_nox": round(new_nox, 2),
            "baseline_ej_index": region["ej_index"],
            "vulnerability_level": self.mapper.assess_vulnerability_level(
                region["ej_index"]
            ),
        }

    def generate_mitigation_tips(self, impact_data: Dict[str, Any]) -> list:
        """Generates localized advocacy or mitigation tips based on the impact and vulnerability."""
        tips = []
        ej_index = impact_data["baseline_ej_index"]

        if ej_index > 60:
            tips.append(
                "📢 **Advocacy:** Your community has a high EJ index. Consider joining local clean air coalitions to advocate for stricter industrial zoning and better public transit."
            )

        if "car" in impact_data["activity"].lower():
            tips.append(
                "🚲 **Mobility:** Replace short car trips with walking, cycling, or public transit to directly reduce neighborhood NOx and PM2.5 levels."
            )

        if (
            "generator" in impact_data["activity"].lower()
            or "wood" in impact_data["activity"].lower()
        ):
            tips.append(
                "🔥 **Heating/Power:** If possible, transition to electric heat pumps or connect to the grid to eliminate localized particulate matter from combustion."
            )

        tips.append(
            "🌳 **Greening:** Support or participate in local tree-planting initiatives. Tree canopy naturally filters PM2.5 and reduces urban heat island effects."
        )

        return tips
