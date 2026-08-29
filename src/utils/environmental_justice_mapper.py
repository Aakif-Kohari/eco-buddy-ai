"""
Environmental Justice Mapper.
Manages a mock dataset of regional EJ indices, demographic vulnerability scores, and baseline pollution levels.
"""

from typing import Dict, Any, Optional

# Mock dataset of regional Environmental Justice metrics
# EJ Index: 0-100 (100 = highest vulnerability/disadvantage)
# Baseline PM2.5: µg/m³
REGIONAL_EJ_DATA = {
    "90210": {
        "region_name": "Beverly Hills, CA",
        "ej_index": 15,
        "demographic_vulnerability_score": 20,
        "baseline_pm25": 8.5,
        "baseline_nox": 15.0,
        "tree_canopy_pct": 35.0,
    },
    "10001": {
        "region_name": "Manhattan, NY",
        "ej_index": 45,
        "demographic_vulnerability_score": 50,
        "baseline_pm25": 12.0,
        "baseline_nox": 35.0,
        "tree_canopy_pct": 15.0,
    },
    "60614": {
        "region_name": "Lincoln Park, Chicago, IL",
        "ej_index": 25,
        "demographic_vulnerability_score": 30,
        "baseline_pm25": 10.5,
        "baseline_nox": 25.0,
        "tree_canopy_pct": 25.0,
    },
    "77001": {
        "region_name": "Downtown Houston, TX",
        "ej_index": 75,
        "demographic_vulnerability_score": 80,
        "baseline_pm25": 18.0,
        "baseline_nox": 45.0,
        "tree_canopy_pct": 10.0,
    },
    "98101": {
        "region_name": "Downtown Seattle, WA",
        "ej_index": 30,
        "demographic_vulnerability_score": 35,
        "baseline_pm25": 7.0,
        "baseline_nox": 20.0,
        "tree_canopy_pct": 20.0,
    },
}


class EnvironmentalJusticeMapper:
    """Provides access to and analysis of regional Environmental Justice data."""

    def __init__(self):
        self.data = REGIONAL_EJ_DATA

    def get_region_profile(self, zip_code: str) -> Optional[Dict[str, Any]]:
        """Retrieves the EJ profile for a specific zip code."""
        return self.data.get(zip_code)

    def get_all_regions(self) -> list:
        """Returns a list of all available zip codes."""
        return list(self.data.keys())

    def get_region_display_name(self, zip_code: str) -> str:
        """Returns the human-readable name of the region."""
        profile = self.get_region_profile(zip_code)
        return profile["region_name"] if profile else f"Unknown Region ({zip_code})"

    def assess_vulnerability_level(self, ej_index: int) -> str:
        """Categorizes the vulnerability level based on the EJ index."""
        if ej_index <= 30:
            return "Low Vulnerability"
        elif ej_index <= 60:
            return "Moderate Vulnerability"
        else:
            return "High Vulnerability (Priority for Mitigation)"
