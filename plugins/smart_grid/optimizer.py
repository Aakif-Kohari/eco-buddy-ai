"""
Smart Grid Optimizer Engine.
Uses forecasted data and device states to solve a scheduling optimization problem.
Goal: Minimize carbon footprint and cost by shifting deferrable loads (EV, Battery)
to times of high solar generation or low grid carbon intensity.
"""

import time
import logging
from typing import List, Dict, Any, Optional

from plugins.smart_grid.devices import IoTDevice, EVCharger, BatterySystem, SmartHVAC
from plugins.smart_grid.forecaster import SmartGridForecaster

logger = logging.getLogger(__name__)

class GridOptimizer:
    """
    Mathematical scheduler for Smart Home energy assets.
    Implements a greedy forward-looking algorithm to place flexible loads in the 
    lowest-carbon timeslots.
    """
    
    def __init__(self, forecaster: SmartGridForecaster):
        self.forecaster = forecaster
        self.devices: List[IoTDevice] = []
        self.optimization_horizon_hours = 12
        self.resolution_minutes = 15
        
    def register_device(self, device: IoTDevice):
        self.devices.append(device)
        logger.info(f"Optimizer registered device: {device.name}")

    def run_optimization(self, current_timestamp: float) -> Dict[str, Any]:
        """
        Executes the optimization routine.
        1. Fetch forecasts (solar + grid intensity).
        2. Identify inflexible baseline loads (HVAC, normal consumption).
        3. Identify flexible/deferrable loads (EV Charging).
        4. Optimize Battery dispatch (charge from solar, discharge during peak grid carbon).
        5. Generate the dispatch schedule and issue immediate commands.
        """
        logger.info("Running Grid Optimization cycle...")
        
        # 1. Fetch Forecasts
        grid_forecast = self.forecaster.predict_carbon_intensity(
            current_timestamp, self.optimization_horizon_hours, self.resolution_minutes)
        solar_forecast = self.forecaster.predict_solar_irradiance(
            current_timestamp, self.optimization_horizon_hours, self.resolution_minutes)
            
        # Combine into timeslots
        timeslots = []
        for i in range(len(grid_forecast)):
            timeslots.append({
                "timestamp": grid_forecast[i]["timestamp"],
                "hour_of_day": grid_forecast[i]["hour_of_day"],
                "grid_co2": grid_forecast[i]["predicted_g_co2_per_kwh"],
                "solar_w": solar_forecast[i]["predicted_irradiance_w_m2"],
                "planned_load_kw": 0.0,
                "planned_generation_kw": 0.0,
                "assignments": []
            })
            
        # 2. Extract Device States
        ev_chargers = [d for d in self.devices if isinstance(d, EVCharger)]
        batteries = [d for d in self.devices if isinstance(d, BatterySystem)]
        hvacs = [d for d in self.devices if isinstance(d, SmartHVAC)]
        
        # 3. Optimize EV Charging (Deferrable Load)
        # For simplicity, we use a greedy approach: sort timeslots by carbon intensity ascending
        sorted_slots = sorted(timeslots, key=lambda x: x["grid_co2"])
        
        for ev in ev_chargers:
            if ev.car_connected and not ev.is_charging:
                # Calculate how many timeslots we need to reach the target
                remaining_kwh = ev.session_target_kwh - ev.session_delivered_kwh
                if remaining_kwh > 0.01:
                    kw_per_slot = ev.max_power_kw
                    kwh_per_slot = kw_per_slot * (self.resolution_minutes / 60.0)
                    slots_needed = int(remaining_kwh // kwh_per_slot) + 1
                    
                    # Pick the best 'slots_needed' timeslots from our sorted low-carbon list
                    best_slots = sorted_slots[:slots_needed]
                    
                    # Are we currently in one of the best slots?
                    current_slot = timeslots[0]
                    should_charge_now = any(s["timestamp"] == current_slot["timestamp"] for s in best_slots)
                    
                    if should_charge_now:
                        ev.start_charging()
                        logger.info(f"Optimizer: Started EV Charger {ev.name} (Optimal window).")
                    else:
                        ev.pause_charging()
                        logger.info(f"Optimizer: Paused EV Charger {ev.name} (Waiting for lower carbon).")

        # 4. Optimize Battery Dispatch
        # Simple heuristic:
        # If solar is high and grid carbon is high -> Discharge to offset home load
        # If solar is high and grid carbon is low -> Charge from solar
        # If solar is low and grid carbon is low -> Charge from grid (cheap/clean)
        # If solar is low and grid carbon is high -> Discharge to offset grid
        
        current_solar = timeslots[0]["solar_w"]
        current_grid_co2 = timeslots[0]["grid_co2"]
        
        # Calculate thresholds dynamically based on the 12-hour forecast
        avg_co2 = sum(s["grid_co2"] for s in timeslots) / len(timeslots)
        
        for batt in batteries:
            # Prevent rapid cycling by adding a small deadband
            if current_solar > 400.0:
                # Good solar generation
                if batt.current_charge_kwh < batt.capacity_kwh * 0.95:
                    batt.set_mode("CHARGE")
                else:
                    batt.set_mode("IDLE")
            else:
                # Low solar. Evaluate grid intensity
                if current_grid_co2 > avg_co2 * 1.1: # 10% above average (Dirty grid)
                    if batt.current_charge_kwh > batt.min_charge_kwh * 1.1:
                        batt.set_mode("DISCHARGE")
                    else:
                        batt.set_mode("IDLE")
                elif current_grid_co2 < avg_co2 * 0.9: # 10% below average (Clean grid)
                    if batt.current_charge_kwh < batt.capacity_kwh * 0.8: # Leave room for solar
                        batt.set_mode("CHARGE")
                    else:
                        batt.set_mode("IDLE")
                else:
                    batt.set_mode("IDLE")

        # Compile optimization report
        report = {
            "timestamp": current_timestamp,
            "forecast_horizon_hours": self.optimization_horizon_hours,
            "avg_forecasted_co2": round(avg_co2, 2),
            "current_co2": round(current_grid_co2, 2),
            "ev_commands": [{"device": ev.name, "charging": ev.is_charging} for ev in ev_chargers],
            "battery_commands": [{"device": b.name, "mode": b.target_mode} for b in batteries]
        }
        
        return report
