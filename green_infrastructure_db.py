"""
Green Infrastructure Database.
Manages a dataset of mitigation strategies, including installation costs, maintenance requirements, and cooling efficiency metrics.
"""

from typing import Dict, Any, Optional

# Mock dataset for green infrastructure options
# cooling_effect_c: Temperature reduction per unit (sqm or tree)
# cost_per_unit_usd: Installation cost
# maintenance_annual_pct: Annual maintenance cost as % of installation
# lifespan_years: Expected functional lifespan
GREEN_INFRASTRUCTURE_OPTIONS = {
    "green_roof_extensive": {
        "name": "Extensive Green Roof",
        "unit": "sqm",
        "cooling_effect_c": 0.05,  # Degrees C reduction per sqm
        "cost_per_unit_usd": 150.0,
        "maintenance_annual_pct": 0.02,
        "lifespan_years": 40,
        "description": "Lightweight vegetated roof layer providing insulation and stormwater management.",
    },
    "mature_tree_canopy": {
        "name": "Mature Tree Planting",
        "unit": "tree",
        "cooling_effect_c": 1.5,  # Degrees C reduction per mature tree
        "cost_per_unit_usd": 500.0,
        "maintenance_annual_pct": 0.05,
        "lifespan_years": 50,
        "description": "Planting large, native shade trees to provide direct shading and evapotranspiration.",
    },
    "permeable_pavement": {
        "name": "Permeable Pavement",
        "unit": "sqm",
        "cooling_effect_c": 0.02,
        "cost_per_unit_usd": 120.0,
        "maintenance_annual_pct": 0.01,
        "lifespan_years": 20,
        "description": "Porous paving materials that reduce surface heat retention and manage runoff.",
    },
    "vertical_green_wall": {
        "name": "Vertical Green Wall",
        "unit": "sqm",
        "cooling_effect_c": 0.08,
        "cost_per_unit_usd": 400.0,
        "maintenance_annual_pct": 0.10,
        "lifespan_years": 15,
        "description": "Vegetated wall systems that cool building facades and improve local air quality.",
    },
    "rain_garden": {
        "name": "Rain Garden",
        "unit": "sqm",
        "cooling_effect_c": 0.04,
        "cost_per_unit_usd": 80.0,
        "maintenance_annual_pct": 0.03,
        "lifespan_years": 25,
        "description": "Shallow depressed areas planted with native vegetation to capture and filter runoff.",
    },
}


class GreenInfrastructureDB:
    """Provides access to green infrastructure specifications and metrics."""

    def __init__(self):
        self.options = GREEN_INFRASTRUCTURE_OPTIONS

    def get_option_details(self, option_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves specifications for a specific green infrastructure option."""
        return self.options.get(option_key.lower())

    def get_all_options(self) -> list:
        """Returns a list of all available green infrastructure option keys."""
        return list(self.options.keys())

    def get_option_display_name(self, option_key: str) -> str:
        """Returns the human-readable name of the option."""
        details = self.get_option_details(option_key)
        return details["name"] if details else option_key.replace("_", " ").title()
