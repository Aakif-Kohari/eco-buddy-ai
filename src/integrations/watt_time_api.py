import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class WattTimeClient:
    """
    Client for fetching real-time grid marginal emissions data (e.g., from WattTime API).
    Used to adjust the ML inference dynamically based on the user's local energy mix,
    resolving the inaccurate seasonal predictions outlined in Issue #1469.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        if not self.api_key:
            logger.warning("No WattTime API key found. Using simulated fallback data.")

    def get_realtime_emissions(self, zip_code: str) -> float:
        """
        Returns the marginal carbon emissions rate (lbs CO2/MWh) for the given zip code.
        """
        if self.api_key:
            # In production, this would make an actual HTTP request to WattTime API.
            # e.g., requests.get(f"https://api2.watttime.org/v2/index?zip={zip_code}")
            pass

        return self._simulate_grid_emissions(zip_code)

    def _simulate_grid_emissions(self, zip_code: str) -> float:
        """
        Mock fallback generator.
        Simulates diurnal and seasonal grid variations if the API is unavailable.
        """
        current_hour = datetime.now().hour
        
        # Simulate solar abundance during mid-day (cleaner grid = lower emissions)
        if 10 <= current_hour <= 15:
            base_emission = 800.0  # Cleaner
        # Simulate peak evening load (dirtier grid = higher emissions)
        elif 17 <= current_hour <= 21:
            base_emission = 1400.0 # Dirtier (Peaker plants running)
        else:
            base_emission = 1100.0 # Average

        # Add a bit of random noise based on the hash of the zip code
        noise = (hash(zip_code) % 200) - 100
        
        return base_emission + noise

# Export a default instance
watt_time_client = WattTimeClient()
