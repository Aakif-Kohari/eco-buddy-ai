"""
Advanced IoT Device Models for the Smart Grid Simulator.
Expands the physical simulation with thermodynamic models and wind generation.
"""

from typing import Dict, Any
import math
import random
import time
import logging
from plugins.smart_grid.devices import IoTDevice, DeviceState

logger = logging.getLogger(__name__)

class SmartWaterHeater(IoTDevice):
    """
    Thermodynamic model of an electric water heater.
    Consumes power to raise water temperature. Loses heat to the environment over time.
    """
    def __init__(self, name: str, max_power_kw: float = 4.5, tank_volume_liters: float = 200.0):
        super().__init__(name, "WATER_HEATER", max_power_kw)
        self.tank_volume_liters = tank_volume_liters
        self.current_temp_c = 50.0
        self.target_temp_c = 60.0
        self.min_temp_c = 45.0
        # Specific heat of water: 4.184 kJ/(kg*C)
        self.specific_heat_kj_kg_c = 4.184
        self.ambient_temp_c = 20.0
        self.insulation_r_value = 15.0
        self.is_heating = False

    def tick(self, time_delta_seconds: float, external_conditions: Dict[str, Any]) -> DeviceState:
        if not self.is_connected:
            self._update_state(0.0, "OFF")
            return self.current_state

        # Calculate heat loss to ambient environment
        temp_diff = self.current_temp_c - self.ambient_temp_c
        heat_loss_rate = temp_diff / self.insulation_r_value # Simplified loss rate
        self.current_temp_c -= heat_loss_rate * (time_delta_seconds / 3600.0)

        # Hot water draw simulation (random small draws in morning/evening)
        time_struct = time.localtime(self.current_state.timestamp + time_delta_seconds)
        hour = time_struct.tm_hour
        draw_liters = 0.0
        if (7 <= hour <= 9) or (18 <= hour <= 21):
            if random.random() < 0.1: # 10% chance per tick to draw water
                draw_liters = random.uniform(5.0, 20.0)
                # Mixing with cold inlet water (15C)
                mass_ratio = draw_liters / self.tank_volume_liters
                self.current_temp_c = (self.current_temp_c * (1 - mass_ratio)) + (15.0 * mass_ratio)

        power_kw = 0.0
        status = "IDLE"

        # Thermostat logic
        if self.current_temp_c < self.min_temp_c:
            self.is_heating = True
        elif self.current_temp_c >= self.target_temp_c:
            self.is_heating = False

        if self.is_heating:
            power_kw = self.max_power_kw
            status = "HEATING"
            # Energy added = Power (kW) * Time (s) = kJ
            energy_kj = power_kw * time_delta_seconds
            # Mass of water in kg roughly equals volume in liters
            temp_rise = energy_kj / (self.tank_volume_liters * self.specific_heat_kj_kg_c)
            self.current_temp_c += temp_rise

        self._update_state(power_kw, status, tank_temp_c=round(self.current_temp_c, 1))
        return self.current_state


class WindTurbine(IoTDevice):
    """
    Renewable energy producer. Power output depends on wind speed and a power curve.
    """
    def __init__(self, name: str, max_power_kw: float = 10.0, cut_in_speed_m_s: float = 3.0, cut_out_speed_m_s: float = 25.0):
        super().__init__(name, "WIND_PRODUCER", max_power_kw)
        self.cut_in_speed_m_s = cut_in_speed_m_s
        self.cut_out_speed_m_s = cut_out_speed_m_s
        # Rated speed is where it hits max power
        self.rated_speed_m_s = 12.0

    def tick(self, time_delta_seconds: float, external_conditions: Dict[str, Any]) -> DeviceState:
        if not self.is_connected:
            return self.current_state

        wind_speed = external_conditions.get("wind_speed_m_s", 5.0)
        
        # Add turbulence
        wind_speed *= random.uniform(0.8, 1.2)
        power_kw = 0.0
        status = "IDLE"

        if self.cut_in_speed_m_s <= wind_speed <= self.cut_out_speed_m_s:
            if wind_speed >= self.rated_speed_m_s:
                power_kw = self.max_power_kw
            else:
                # Simplified cubic power curve between cut-in and rated
                ratio = (wind_speed - self.cut_in_speed_m_s) / (self.rated_speed_m_s - self.cut_in_speed_m_s)
                power_kw = self.max_power_kw * (ratio ** 3.0)
            
            status = "GENERATING"
        elif wind_speed > self.cut_out_speed_m_s:
            status = "BRAKED_HIGH_WIND"

        # Represent generation as negative power
        self._update_state(-power_kw, status, wind_speed=round(wind_speed, 1))
        return self.current_state


class SmartPoolPump(IoTDevice):
    """
    Flexible load. Needs to run for X hours a day to filter the pool, but can be scheduled anytime.
    """
    def __init__(self, name: str, max_power_kw: float = 1.5, required_hours_per_day: float = 6.0):
        super().__init__(name, "POOL_PUMP", max_power_kw)
        self.required_hours_per_day = required_hours_per_day
        self.hours_run_today = 0.0
        self.is_running = False
        self.last_day = -1

    def tick(self, time_delta_seconds: float, external_conditions: Dict[str, Any]) -> DeviceState:
        if not self.is_connected:
            self._update_state(0.0, "OFF")
            return self.current_state

        current_time = self.current_state.timestamp + time_delta_seconds
        time_struct = time.localtime(current_time)
        current_day = time_struct.tm_yday

        # Reset accumulator at midnight
        if current_day != self.last_day:
            self.hours_run_today = 0.0
            self.last_day = current_day

        power_kw = 0.0
        status = "IDLE"

        # Simple standalone logic if not commanded by optimizer
        # Run aggressively in the morning if we haven't hit our quota
        if self.is_running:
            power_kw = self.max_power_kw
            status = "PUMPING"
            self.hours_run_today += (time_delta_seconds / 3600.0)

        # Auto-shutoff if quota met
        if self.hours_run_today >= self.required_hours_per_day:
            self.is_running = False
            status = "QUOTA_MET"

        self._update_state(power_kw, status, run_hours=round(self.hours_run_today, 2))
        return self.current_state
