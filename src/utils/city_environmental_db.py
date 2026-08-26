"""
City Environmental Database.
Stores and manages environmental profiles for major cities.
"""

from typing import Dict, Any, Optional

# Mock database of city environmental profiles
# grid_intensity: kg CO2e per kWh
# heating_degree_days: annual average
# cooling_degree_days: annual average
# transit_score: 0-100 (100 is excellent public transit)
# housing_efficiency_factor: 0.5 to 1.5 (1.0 is average, <1.0 is better)
CITY_PROFILES = {
    "new_york": {
        "name": "New York, USA",
        "grid_intensity": 0.28,
        "heating_degree_days": 4500,
        "cooling_degree_days": 1200,
        "transit_score": 85,
        "housing_efficiency_factor": 0.9,
        "climate_zone": "Humid Continental",
    },
    "london": {
        "name": "London, UK",
        "grid_intensity": 0.21,
        "heating_degree_days": 3800,
        "cooling_degree_days": 300,
        "transit_score": 90,
        "housing_efficiency_factor": 0.85,
        "climate_zone": "Temperate Oceanic",
    },
    "tokyo": {
        "name": "Tokyo, Japan",
        "grid_intensity": 0.46,
        "heating_degree_days": 2800,
        "cooling_degree_days": 1800,
        "transit_score": 95,
        "housing_efficiency_factor": 0.95,
        "climate_zone": "Humid Subtropical",
    },
    "sydney": {
        "name": "Sydney, Australia",
        "grid_intensity": 0.75,
        "heating_degree_days": 1500,
        "cooling_degree_days": 1600,
        "transit_score": 70,
        "housing_efficiency_factor": 1.1,
        "climate_zone": "Humid Subtropical",
    },
    "berlin": {
        "name": "Berlin, Germany",
        "grid_intensity": 0.34,
        "heating_degree_days": 4200,
        "cooling_degree_days": 400,
        "transit_score": 88,
        "housing_efficiency_factor": 0.8,
        "climate_zone": "Temperate Oceanic",
    },
    "mumbai": {
        "name": "Mumbai, India",
        "grid_intensity": 0.71,
        "heating_degree_days": 200,
        "cooling_degree_days": 3500,
        "transit_score": 65,
        "housing_efficiency_factor": 1.2,
        "climate_zone": "Tropical Wet and Dry",
    },
    "san_francisco": {
        "name": "San Francisco, USA",
        "grid_intensity": 0.18,
        "heating_degree_days": 3100,
        "cooling_degree_days": 500,
        "transit_score": 80,
        "housing_efficiency_factor": 0.9,
        "climate_zone": "Mediterranean",
    },
    "toronto": {
        "name": "Toronto, Canada",
        "grid_intensity": 0.05,
        "heating_degree_days": 5500,
        "cooling_degree_days": 900,
        "transit_score": 75,
        "housing_efficiency_factor": 0.85,
        "climate_zone": "Humid Continental",
    },
}


class CityEnvironmentalDB:
    """Manages access to city environmental profiles."""

    def __init__(self):
        self.profiles = CITY_PROFILES

    def get_city_profile(self, city_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves the environmental profile for a given city key."""
        return self.profiles.get(city_key.lower().replace(" ", "_"))

    def get_all_cities(self) -> list:
        """Returns a list of all available city keys."""
        return list(self.profiles.keys())

    def get_city_display_name(self, city_key: str) -> str:
        """Returns the human-readable name of the city."""
        profile = self.get_city_profile(city_key)
        return profile["name"] if profile else city_key.replace("_", " ").title()
