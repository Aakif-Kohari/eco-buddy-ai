"""
Master Smart Grid Simulation Engine.
Instantiates all devices, the broker, the forecaster, and the optimizer.
Manages the simulation clock and orchestrates the tick cycle.
"""

import asyncio
import time
import math
import logging
from typing import List, Dict, Any

from plugins.smart_grid.devices import SolarPanel, BatterySystem, EVCharger, SmartHVAC, SmartAppliance
from plugins.smart_grid.telemetry import MessageBroker, TelemetryEngine
from plugins.smart_grid.forecaster import SmartGridForecaster
from plugins.smart_grid.optimizer import GridOptimizer

logger = logging.getLogger(__name__)

class SmartGridSimulation:
    """
    The orchestrator for the entire Smart Grid subsystem.
    Can be run in real-time mode (1 second = 1 second) or accelerated 
    time-travel mode (1 second = 1 hour) for backtesting algorithms.
    """
    def __init__(self, region: str = "US-CA", speed_multiplier: float = 1.0):
        self.region = region
        self.speed_multiplier = speed_multiplier
        
        # Core Infrastructure
        self.broker = MessageBroker()
        self.telemetry = TelemetryEngine(self.broker)
        self.forecaster = SmartGridForecaster(region=self.region)
        self.optimizer = GridOptimizer(self.forecaster)
        
        # State
        self.is_running = False
        self.sim_time = time.time()
        self.real_start_time = time.time()
        self.devices = []
        
        self._setup_default_home()
        
    def _setup_default_home(self):
        """Initializes a standard smart home topology."""
        # 1. Solar Array (5kW)
        solar = SolarPanel("Roof Solar Array", max_power_kw=5.0, efficiency=0.22, area_m2=25.0)
        
        # 2. Battery Wall (13.5 kWh, like a Tesla Powerwall)
        battery = BatterySystem("Home Battery", capacity_kwh=13.5, max_charge_kw=5.0, max_discharge_kw=5.0)
        
        # 3. EV Charger (Level 2, 7.2kW)
        ev = EVCharger("Garage EVSE", max_power_kw=7.2)
        ev.plug_in_car(target_kwh=40.0) # EV needs 40 kWh to reach target charge
        
        # 4. HVAC System
        hvac = SmartHVAC("Central AC", max_power_kw=3.5, target_temp_c=22.0)
        hvac.current_indoor_temp_c = 24.0 # Slightly warm to start
        
        # 5. Dishwasher
        dishwasher = SmartAppliance("Dishwasher", max_power_kw=1.5)
        
        # Register everywhere
        for dev in [solar, battery, ev, hvac, dishwasher]:
            self.devices.append(dev)
            self.telemetry.register_device(dev)
            self.optimizer.register_device(dev)

    async def run_simulation(self, duration_real_seconds: float = 60.0):
        """
        Executes the simulation loop for a specified real-world duration.
        """
        logger.info(f"Starting Smart Grid Simulation in {self.region} at {self.speed_multiplier}x speed.")
        self.is_running = True
        
        # Start the background telemetry service
        await self.telemetry.start()
        
        # Setup a subscriber to calculate total net grid power
        self.net_power_kw = 0.0
        
        async def on_device_state(topic: str, payload: Dict[str, Any]):
            # This is a bit of a race condition in a real system, but fine for simulation
            # We recalculate net power by summing all devices
            total = sum(d.current_state.power_kw for d in self.devices if d.is_connected)
            self.net_power_kw = total
            
        await self.broker.subscribe("home/devices/#", on_device_state)
        
        # Main Simulation Tick Loop
        tick_interval_real_sec = 0.5
        ticks_passed = 0
        
        start_time = time.time()
        while self.is_running and (time.time() - start_time) < duration_real_seconds:
            # Advance simulation time
            delta_sim_sec = tick_interval_real_sec * self.speed_multiplier
            self.sim_time += delta_sim_sec
            
            # 1. Update Environmental Conditions
            # Get current solar and outdoor temp based on sim time
            time_struct = time.localtime(self.sim_time)
            hour_of_day = time_struct.tm_hour + (time_struct.tm_min / 60.0)
            
            # Simple solar curve for tick interpolation
            solar_irradiance = 0.0
            if 6.0 <= hour_of_day <= 18.0:
                normalized = (hour_of_day - 6.0) / 12.0 * math.pi
                solar_irradiance = math.sin(normalized) * 1000.0
                
            outdoor_temp = 15.0 + (math.sin((hour_of_day - 8.0) / 24.0 * math.pi * 2) * 10.0)
            
            conditions = {
                "solar_irradiance_w_m2": max(0.0, solar_irradiance),
                "outdoor_temperature_c": outdoor_temp
            }
            
            # 2. Tick all devices physical models
            for dev in self.devices:
                dev.tick(delta_sim_sec, conditions)
                
            # 3. Run Optimizer (every 10 simulated minutes)
            if ticks_passed % max(1, int(600 / (delta_sim_sec + 0.001))) == 0:
                self.optimizer.run_optimization(self.sim_time)
                
            ticks_passed += 1
            await asyncio.sleep(tick_interval_real_sec)
            
        # Cleanup
        self.is_running = False
        await self.telemetry.stop()
        logger.info("Simulation completed gracefully.")
