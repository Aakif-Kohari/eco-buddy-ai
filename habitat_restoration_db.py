"""
Habitat Restoration Database.
Manages a dataset of native plants, wildlife support metrics, and baseline habitat condition scores.
"""

from typing import Dict, Any, Optional

# Biodiversity Unit (BU) multipliers for different actions per square meter
# Higher BU = greater positive impact on local ecology
RESTORATION_ACTIONS = {
    "native_tree_planting": {
        "name": "Native Tree Planting",
        "bu_per_sqm": 0.5,
        "wildlife_support": ["birds", "mammals", "insects"],
        "description": "Planting indigenous tree species to restore canopy cover and provide long-term habitat.",
    },
    "pollinator_garden": {
        "name": "Pollinator Garden Creation",
        "bu_per_sqm": 0.3,
        "wildlife_support": ["bees", "butterflies", "insects"],
        "description": "Establishing diverse, pesticide-free flowering plants to support local pollinator populations.",
    },
    "invasive_removal": {
        "name": "Invasive Species Removal",
        "bu_per_sqm": 0.2,
        "wildlife_support": ["native_plants", "soil_health"],
        "description": "Clearing non-native invasive plants to allow native flora to regenerate naturally.",
    },
    "wetland_creation": {
        "name": "Small-Scale Wetland Creation",
        "bu_per_sqm": 0.8,
        "wildlife_support": ["amphibians", "birds", "aquatic_insects"],
        "description": "Digging or restoring small ponds/wetlands to support amphibious and aquatic life.",
    },
    "lawn_conversion": {
        "name": "Lawn to Meadow Conversion",
        "bu_per_sqm": 0.15,
        "wildlife_support": ["insects", "small_mammals", "birds"],
        "description": "Replacing resource-intensive turf grass with native grasses and wildflowers.",
    },
    "hedge_planting": {
        "name": "Native Hedge Planting",
        "bu_per_sqm": 0.25,
        "wildlife_support": ["birds", "mammals", "insects"],
        "description": "Planting dense, native shrub boundaries to provide shelter and foraging corridors.",
    },
}

# Baseline habitat condition scores (0.0 = degraded, 1.0 = pristine)
BASELINE_CONDITIONS = {
    "degraded_urban_lot": 0.2,
    "standard_suburban_lawn": 0.3,
    "abandoned_agricultural": 0.4,
    "managed_parkland": 0.6,
    "existing_woodland": 0.8,
}


class HabitatRestorationDB:
    """Provides access to biodiversity metrics and habitat condition data."""

    def __init__(self):
        self.actions = RESTORATION_ACTIONS
        self.baselines = BASELINE_CONDITIONS

    def get_action_details(self, action_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves details for a specific restoration action."""
        return self.actions.get(action_key.lower())

    def get_all_actions(self) -> list:
        """Returns a list of all available restoration action keys."""
        return list(self.actions.keys())

    def get_action_display_name(self, action_key: str) -> str:
        """Returns the human-readable name of the action."""
        details = self.get_action_details(action_key)
        return details["name"] if details else action_key.replace("_", " ").title()

    def get_baseline_score(self, condition_key: str) -> float:
        """Retrieves the baseline biodiversity score for a habitat condition."""
        return self.baselines.get(condition_key.lower(), 0.5)

    def get_all_baselines(self) -> list:
        """Returns a list of all available baseline condition keys."""
        return list(self.baselines.keys())
