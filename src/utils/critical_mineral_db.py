"""
Critical Mineral Database.
Manages a dataset of mineral compositions, extraction carbon costs, and certified recycling recovery rates.
"""

from typing import Dict, Any, List

# Dataset of common consumer electronics and their critical mineral content (in grams per device)
# Also includes the carbon cost of virgin mining (kg CO2e per gram) and recycling recovery rate (%)
DEVICE_MINERAL_PROFILES = {
    "smartphone": {
        "name": "Smartphone",
        "minerals": {
            "lithium": {
                "weight_g": 0.034,
                "virgin_carbon_kg_per_g": 0.015,
                "recovery_rate_pct": 50.0,
            },
            "cobalt": {
                "weight_g": 0.008,
                "virgin_carbon_kg_per_g": 0.025,
                "recovery_rate_pct": 70.0,
            },
            "gold": {
                "weight_g": 0.030,
                "virgin_carbon_kg_per_g": 0.500,
                "recovery_rate_pct": 95.0,
            },
            "copper": {
                "weight_g": 15.0,
                "virgin_carbon_kg_per_g": 0.004,
                "recovery_rate_pct": 90.0,
            },
        },
    },
    "laptop": {
        "name": "Laptop",
        "minerals": {
            "lithium": {
                "weight_g": 0.050,
                "virgin_carbon_kg_per_g": 0.015,
                "recovery_rate_pct": 50.0,
            },
            "cobalt": {
                "weight_g": 0.015,
                "virgin_carbon_kg_per_g": 0.025,
                "recovery_rate_pct": 70.0,
            },
            "gold": {
                "weight_g": 0.050,
                "virgin_carbon_kg_per_g": 0.500,
                "recovery_rate_pct": 95.0,
            },
            "copper": {
                "weight_g": 25.0,
                "virgin_carbon_kg_per_g": 0.004,
                "recovery_rate_pct": 90.0,
            },
            "rare_earth": {
                "weight_g": 0.020,
                "virgin_carbon_kg_per_g": 0.100,
                "recovery_rate_pct": 30.0,
            },
        },
    },
    "tablet": {
        "name": "Tablet",
        "minerals": {
            "lithium": {
                "weight_g": 0.040,
                "virgin_carbon_kg_per_g": 0.015,
                "recovery_rate_pct": 50.0,
            },
            "gold": {
                "weight_g": 0.040,
                "virgin_carbon_kg_per_g": 0.500,
                "recovery_rate_pct": 95.0,
            },
            "copper": {
                "weight_g": 20.0,
                "virgin_carbon_kg_per_g": 0.004,
                "recovery_rate_pct": 90.0,
            },
        },
    },
    "smartwatch": {
        "name": "Smartwatch",
        "minerals": {
            "lithium": {
                "weight_g": 0.010,
                "virgin_carbon_kg_per_g": 0.015,
                "recovery_rate_pct": 50.0,
            },
            "cobalt": {
                "weight_g": 0.003,
                "virgin_carbon_kg_per_g": 0.025,
                "recovery_rate_pct": 70.0,
            },
            "gold": {
                "weight_g": 0.010,
                "virgin_carbon_kg_per_g": 0.500,
                "recovery_rate_pct": 95.0,
            },
        },
    },
}


class CriticalMineralDB:
    """Manages access to critical mineral composition and impact data."""

    def __init__(self):
        self.profiles = DEVICE_MINERAL_PROFILES

    def get_device_profile(self, device_key: str) -> Dict[str, Any]:
        """Retrieves the mineral profile for a given device key."""
        return self.profiles.get(device_key.lower())

    def get_all_devices(self) -> List[str]:
        """Returns a list of all available device keys."""
        return list(self.profiles.keys())

    def get_device_display_name(self, device_key: str) -> str:
        """Returns the human-readable name of the device."""
        profile = self.get_device_profile(device_key)
        return profile["name"] if profile else device_key.replace("_", " ").title()
