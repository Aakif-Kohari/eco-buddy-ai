"""
Biodiversity Net Gain Calculator.
Calculates the ecological value added by specific restoration actions based on area, habitat type, and management duration.
"""

from typing import Dict, Any, List
from habitat_restoration_db import HabitatRestorationDB


class BiodiversityNetGainCalculator:
    """Calculates the Biodiversity Net Gain (BNG) percentage and score for restoration projects."""

    def __init__(self, baseline_condition: str, total_area_sqm: float):
        self.db = HabitatRestorationDB()
        self.baseline_condition = baseline_condition.lower()
        self.total_area_sqm = max(0.0, total_area_sqm)
        self.baseline_score = self.db.get_baseline_score(self.baseline_condition)
        self.actions_logged: List[Dict[str, Any]] = []

    def add_restoration_action(
        self, action_key: str, area_sqm: float, management_years: int
    ) -> bool:
        """
        Adds a restoration action to the project.

        Args:
            action_key: The type of action (e.g., 'native_tree_planting').
            area_sqm: The area in square meters dedicated to this action.
            management_years: How many years the area will be actively managed/maintained.
        """
        details = self.db.get_action_details(action_key)
        if not details:
            return False

        if area_sqm > self.total_area_sqm:
            # Allow it but maybe warn in UI, for now we just log it
            pass

        # BNG formula simplification:
        # Gain = (BU per sqm * area) * (1 + (management_years * 0.1))
        # Longer management increases the certainty and value of the gain.
        management_multiplier = 1.0 + (management_years * 0.1)
        biodiversity_units_gained = (
            details["bu_per_sqm"] * area_sqm * management_multiplier
        )

        self.actions_logged.append(
            {
                "action_key": action_key,
                "action_name": details["name"],
                "area_sqm": area_sqm,
                "management_years": management_years,
                "bu_gained": round(biodiversity_units_gained, 2),
                "wildlife_support": details["wildlife_support"],
            }
        )

        return True

    def calculate_net_gain(self) -> Dict[str, Any]:
        """Calculates the overall Biodiversity Net Gain for the project."""
        if self.total_area_sqm == 0:
            return self._empty_result()

        total_bu_gained = sum(action["bu_gained"] for action in self.actions_logged)

        # Post-development biodiversity value = Baseline Score + (Total BU Gained / Total Area)
        # This is a simplified metric units approach
        avg_bu_per_sqm = total_bu_gained / self.total_area_sqm
        post_development_score = min(
            1.0, self.baseline_score + (avg_bu_per_sqm / 10.0)
        )  # Normalized scaling

        # BNG Percentage = ((Post - Pre) / Pre) * 100
        if self.baseline_score == 0:
            bng_percentage = 100.0 if post_development_score > 0 else 0.0
        else:
            bng_percentage = (
                (post_development_score - self.baseline_score) / self.baseline_score
            ) * 100.0

        # Aggregate wildlife supported
        all_wildlife = set()
        for action in self.actions_logged:
            all_wildlife.update(action["wildlife_support"])

        return {
            "baseline_condition": self.baseline_condition.replace("_", " ").title(),
            "baseline_score": self.baseline_score,
            "total_area_sqm": self.total_area_sqm,
            "total_bu_gained": round(total_bu_gained, 2),
            "post_development_score": round(post_development_score, 3),
            "bng_percentage": round(bng_percentage, 1),
            "wildlife_supported": list(all_wildlife),
            "action_breakdown": self.actions_logged,
            "is_positive_gain": bng_percentage > 0.0,
        }

    def _empty_result(self) -> Dict[str, Any]:
        """Returns an empty result structure."""
        return {
            "baseline_condition": self.baseline_condition.replace("_", " ").title(),
            "baseline_score": self.baseline_score,
            "total_area_sqm": 0.0,
            "total_bu_gained": 0.0,
            "post_development_score": self.baseline_score,
            "bng_percentage": 0.0,
            "wildlife_supported": [],
            "action_breakdown": [],
            "is_positive_gain": False,
        }

    def get_recommendations(self) -> List[str]:
        """Provides suggestions for improving the BNG score."""
        recs = []
        if not self.actions_logged:
            recs.append(
                "🌱 **Start Small:** Even converting a small patch of lawn to a pollinator garden creates a positive net gain."
            )
            return recs

        # Check for diversity
        all_wildlife = set()
        for action in self.actions_logged:
            all_wildlife.update(action["wildlife_support"])

        if len(all_wildlife) < 3:
            recs.append(
                "🦋 **Increase Diversity:** Add a different type of action (e.g., a small pond or native hedge) to support a wider range of wildlife."
            )

        # Check management duration
        low_management = [a for a in self.actions_logged if a["management_years"] < 3]
        if low_management:
            recs.append(
                "⏳ **Long-term Commitment:** Increasing the management duration of your plantings significantly boosts their biodiversity unit value over time."
            )

        if not recs:
            recs.append(
                "🌟 **Excellent Plan!** Your project is well-diversified and committed to long-term ecological management."
            )

        return recs
