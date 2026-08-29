"""
Grid Intensity and Weather Forecaster.
Provides predictive models for carbon intensity (gCO2eq/kWh) and solar irradiance,
crucial for the Optimizer to schedule heavy loads during low-carbon windows.
"""

import math
import time
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class SmartGridForecaster:
    """
    Simulates ML-based time-series forecasting for grid parameters.
    In a production system, this would interface with WattTime, ElectricityMaps, 
    or run local ARIMA/LSTM src.notifications.models. For the simulation, we use deterministic 
    harmonic oscillations combined with Perlin noise approximations.
    """
    
    def __init__(self, region: str = "DEFAULT"):
        self.region = region
        # Base carbon intensity depends on the region's energy mix
        self.base_carbon_intensity = self._get_regional_baseline()
        
    def _get_regional_baseline(self) -> float:
        baselines = {
            "US-CA": 200.0, # High solar penetration
            "US-TX": 400.0, # Wind + Gas
            "FR": 50.0,     # Nuclear heavy
            "DE": 350.0,    # Coal + Renewables
            "IN": 700.0     # Coal heavy
        }
        return baselines.get(self.region, 300.0)

    def predict_carbon_intensity(self, start_timestamp: float, horizon_hours: int = 24, resolution_minutes: int = 15) -> List[Dict[str, Any]]:
        """
        Generates a forecast of grid carbon intensity (gCO2eq/kWh).
        Simulates the typical "duck curve" where intensity drops mid-day due to solar,
        and spikes in the evening when solar drops and residential demand peaks.
        """
        predictions = []
        num_steps = (horizon_hours * 60) // resolution_minutes
        
        for step in range(num_steps):
            target_ts = start_timestamp + (step * resolution_minutes * 60)
            
            # Extract hour of day (0.0 to 23.99)
            time_struct = time.localtime(target_ts)
            hour_of_day = time_struct.tm_hour + (time_struct.tm_min / 60.0)
            
            # Mid-day solar dip (10 AM to 4 PM)
            # Modeling using a negative Gaussian curve centered at 13:00 (1 PM)
            solar_dip = -0.4 * math.exp(-0.1 * ((hour_of_day - 13.0) ** 2))
            
            # Evening demand spike (6 PM to 10 PM)
            # Modeling using a positive Gaussian curve centered at 20:00 (8 PM)
            evening_spike = 0.3 * math.exp(-0.2 * ((hour_of_day - 20.0) ** 2))
            
            # Nighttime baseline (steady state)
            
            # Combine factors and apply to baseline
            multiplier = 1.0 + solar_dip + evening_spike
            
            # Add some pseudo-random noise (±5%) based on the timestamp to make it realistic
            noise = 1.0 + (math.sin(target_ts / 3600.0) * 0.05)
            
            final_intensity = self.base_carbon_intensity * multiplier * noise
            
            # Ensure it doesn't go below theoretical minimums (e.g., hydro/nuclear baseload)
            final_intensity = max(final_intensity, 10.0)
            
            predictions.append({
                "timestamp": target_ts,
                "hour_of_day": round(hour_of_day, 2),
                "predicted_g_co2_per_kwh": round(final_intensity, 2)
            })
            
        return predictions

    def predict_solar_irradiance(self, start_timestamp: float, horizon_hours: int = 24, resolution_minutes: int = 15) -> List[Dict[str, Any]]:
        """
        Generates a forecast of solar irradiance (W/m2).
        Crucial for predicting when the local battery should charge from solar instead of the grid.
        """
        predictions = []
        num_steps = (horizon_hours * 60) // resolution_minutes
        
        for step in range(num_steps):
            target_ts = start_timestamp + (step * resolution_minutes * 60)
            time_struct = time.localtime(target_ts)
            hour_of_day = time_struct.tm_hour + (time_struct.tm_min / 60.0)
            
            # Sun rises around 6 AM, sets around 6 PM (simplified for equator/spring)
            if 6.0 <= hour_of_day <= 18.0:
                # Half-sine wave peaking at noon (12:00)
                # Normalize time between 0 and PI
                normalized_time = (hour_of_day - 6.0) / 12.0 * math.pi
                
                # Max irradiance ~ 1000 W/m2 on a clear day
                base_irradiance = math.sin(normalized_time) * 1000.0
                
                # Add simulated cloud cover passing by
                # Low frequency sine wave to simulate large cloud banks
                cloud_cover = (math.sin(target_ts / 7200.0) + 1.0) / 2.0 # 0.0 to 1.0
                # Clouds reduce irradiance by up to 60%
                cloud_reduction = 1.0 - (cloud_cover * 0.6)
                
                final_irradiance = base_irradiance * cloud_reduction
            else:
                final_irradiance = 0.0
                
            predictions.append({
                "timestamp": target_ts,
                "hour_of_day": round(hour_of_day, 2),
                "predicted_irradiance_w_m2": round(max(0.0, final_irradiance), 2)
            })
            
        return predictions
