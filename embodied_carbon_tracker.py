"""
Embodied Carbon Tracker.
Manages a dataset of common appliances, their initial manufacturing carbon footprint, and recycling recovery values.
"""

from typing import Dict, Any, Optional


class EmbodiedCarbonTracker:
    """Provides data on the embodied carbon and end-of-life value of household appliances."""

    # Mock dataset: embodied carbon (kg), new efficiency multiplier, expected lifespan, recycling avoidance (kg)
    APPLIANCE_DATABASE = {
        "refrigerator": {
            "name": "Refrigerator",
            "embodied_carbon_kg": 600.0,
            "new_efficiency_multiplier": 0.75,  # New models use 25% less energy
            "expected_lifespan_years": 15,
            "recycling_avoidance_kg": 150.0,  # Carbon saved by recycling vs landfill
        },
        "washing_machine": {
            "name": "Washing Machine",
            "embodied_carbon_kg": 400.0,
            "new_efficiency_multiplier": 0.80,
            "expected_lifespan_years": 10,
            "recycling_avoidance_kg": 100.0,
        },
        "dishwasher": {
            "name": "Dishwasher",
            "embodied_carbon_kg": 350.0,
            "new_efficiency_multiplier": 0.70,
            "expected_lifespan_years": 10,
            "recycling_avoidance_kg": 90.0,
        },
        "hvac_system": {
            "name": "HVAC System",
            "embodied_carbon_kg": 1500.0,
            "new_efficiency_multiplier": 0.60,
            "expected_lifespan_years": 15,
            "recycling_avoidance_kg": 300.0,
        },
        "television": {
            "name": "Television",
            "embodied_carbon_kg": 250.0,
            "new_efficiency_multiplier": 0.85,
            "expected_lifespan_years": 8,
            "recycling_avoidance_kg": 60.0,
        },
    }

    def __init__(self, grid_carbon_intensity: float = 0.4):
        """
        Args:
            grid_carbon_intensity: kg CO2e per kWh (used to calculate operational carbon).
        """
        self.database = self.APPLIANCE_DATABASE
        self.grid_carbon_intensity = grid_carbon_intensity

    def get_appliance_specs(self, appliance_type: str) -> Optional[Dict[str, Any]]:
        """Retrieves specifications for a given appliance type."""
        return self.database.get(appliance_type.lower())

    def get_all_appliance_types(self) -> list:
        """Returns a list of all supported appliance types."""
        return list(self.database.keys())

    def get_appliance_display_name(self, appliance_type: str) -> str:
        """Returns the human-readable name of the appliance."""
        specs = self.get_appliance_specs(appliance_type)
        return specs["name"] if specs else appliance_type.replace("_", " ").title()
