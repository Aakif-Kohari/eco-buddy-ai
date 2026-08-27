"""
IoT Device Models for the Smart Grid Simulator.
Defines the base interfaces and concrete implementations of various energy
consumers, producers, and storage systems found in a modern smart home.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import uuid
import time
import random
import logging

logger = logging.getLogger(__name__)

@dataclass
class DeviceState:
    """Represents the current operational state of a device."""
    timestamp: float = field(default_factory=time.time)
    power_kw: float = 0.0
    status: str = "OFF"
    metadata: Dict[str, Any] = field(default_factory=dict)

class IoTDevice(ABC):
    """
    Abstract base class for all Smart Grid devices.
    Enforces a common interface for telemetry reporting and state management.
    """
    def __init__(self, name: str, device_type: str, max_power_kw: float):
        self.id = str(uuid.uuid4())
        self.name = name
        self.device_type = device_type
        self.max_power_kw = max_power_kw
        self.is_connected = True
        self.current_state = DeviceState()
        self.history: List[DeviceState] = []
        logger.debug(f"Initialized {self.device_type} Device: {self.name} ({self.id})")

    def connect(self):
        self.is_connected = True
        logger.info(f"{self.name} connected to grid.")

    def disconnect(self):
        self.is_connected = False
        self._update_state(0.0, "OFF")
        logger.info(f"{self.name} disconnected from grid.")

    def _update_state(self, power_kw: float, status: str, **kwargs):
        """Internal method to update device state and log history."""
        if not self.is_connected and status != "OFF":
            logger.warning(f"Cannot update state: {self.name} is disconnected.")
            return

        # Cap power to max physical limit
        if power_kw > self.max_power_kw:
            power_kw = self.max_power_kw
        elif power_kw < -self.max_power_kw:
            power_kw = -self.max_power_kw # For bidirectional devices like batteries

        new_state = DeviceState(
            timestamp=time.time(),
            power_kw=power_kw,
            status=status,
            metadata=kwargs
        )
        self.current_state = new_state
        self.history.append(new_state)

        # Prevent unbounded memory growth in long-running sims
        if len(self.history) > 10000:
            self.history.pop(0)

    @abstractmethod
    def tick(self, time_delta_seconds: float, external_conditions: Dict[str, Any]) -> DeviceState:
        """
        Advances the simulation by time_delta_seconds.
        Must be implemented by concrete subclasses.
        Returns the new state.
        """
        pass

    def get_telemetry(self) -> Dict[str, Any]:
        """Formats the current state into a JSON-serializable telemetry payload."""
        return {
            "device_id": self.id,
            "name": self.name,
            "type": self.device_type,
            "connected": self.is_connected,
            "timestamp": self.current_state.timestamp,
            "power_kw": self.current_state.power_kw,
            "status": self.current_state.status,
            "metrics": self.current_state.metadata
        }


class SolarPanel(IoTDevice):
    """
    Renewable energy producer. Power output depends on solar irradiance and efficiency.
    """
    def __init__(self, name: str, max_power_kw: float, efficiency: float = 0.20, area_m2: float = 20.0):
        super().__init__(name, "SOLAR_PRODUCER", max_power_kw)
        self.efficiency = efficiency
        self.area_m2 = area_m2
        self.degradation_factor = 1.0 # Degrades over years in a real simulation

    def tick(self, time_delta_seconds: float, external_conditions: Dict[str, Any]) -> DeviceState:
        if not self.is_connected:
            return self.current_state

        # Irradiance in W/m2 (e.g. 1000 W/m2 at noon on a clear day)
        irradiance_w_m2 = external_conditions.get("solar_irradiance_w_m2", 0.0)
        
        # Add some random cloud cover noise (±5%)
        noise = random.uniform(0.95, 1.05)
        effective_irradiance = irradiance_w_m2 * noise

        # Calculate theoretical power in kW
        generated_w = effective_irradiance * self.area_m2 * self.efficiency * self.degradation_factor
        generated_kw = generated_w / 1000.0

        # Cap at inverter/panel max rating
        actual_kw = min(generated_kw, self.max_power_kw)

        status = "GENERATING" if actual_kw > 0.01 else "IDLE"
        
        # We represent generation as negative power consumption for grid math
        self._update_state(-actual_kw, status, irradiance=irradiance_w_m2, efficiency=self.efficiency)
        return self.current_state


class BatterySystem(IoTDevice):
    """
    Energy storage system. Can charge (consume) or discharge (produce) power.
    Has constraints on capacity, charge/discharge rates, and Depth of Discharge (DoD).
    """
    def __init__(self, name: str, capacity_kwh: float, max_charge_kw: float, max_discharge_kw: float):
        # We set max_power_kw to the higher of charge/discharge limits
        super().__init__(name, "BATTERY_STORAGE", max(max_charge_kw, max_discharge_kw))
        self.capacity_kwh = capacity_kwh
        self.max_charge_kw = max_charge_kw
        self.max_discharge_kw = max_discharge_kw
        
        self.current_charge_kwh = capacity_kwh * 0.5 # Start at 50%
        self.min_charge_kwh = capacity_kwh * 0.1 # Protect battery health (10% DoD limit)
        self.target_mode = "IDLE" # "CHARGE", "DISCHARGE", "IDLE"

    def set_mode(self, mode: str):
        if mode in ["CHARGE", "DISCHARGE", "IDLE"]:
            self.target_mode = mode
            logger.info(f"Battery {self.name} mode set to {mode}")
        else:
            logger.error(f"Invalid battery mode: {mode}")

    def tick(self, time_delta_seconds: float, external_conditions: Dict[str, Any]) -> DeviceState:
        if not self.is_connected:
            return self.current_state

        hours_passed = time_delta_seconds / 3600.0
        power_kw = 0.0
        status = "IDLE"

        if self.target_mode == "CHARGE":
            # Can we charge?
            space_available = self.capacity_kwh - self.current_charge_kwh
            if space_available > 0.01:
                # Max power we can draw
                power_kw = min(self.max_charge_kw, space_available / hours_passed)
                self.current_charge_kwh += power_kw * hours_passed
                status = "CHARGING"

        elif self.target_mode == "DISCHARGE":
            # Can we discharge?
            energy_available = self.current_charge_kwh - self.min_charge_kwh
            if energy_available > 0.01:
                # Max power we can provide (represented as negative)
                discharge_kw = min(self.max_discharge_kw, energy_available / hours_passed)
                power_kw = -discharge_kw
                self.current_charge_kwh -= discharge_kw * hours_passed
                status = "DISCHARGING"

        state_of_charge = (self.current_charge_kwh / self.capacity_kwh) * 100.0
        self._update_state(power_kw, status, soc_percent=round(state_of_charge, 2))
        return self.current_state


class EVCharger(IoTDevice):
    """
    Heavy consumer. Represents an Electric Vehicle charging at home.
    Typically requires a continuous block of high power, making it a prime 
    target for smart scheduling (e.g., charging at 2 AM when wind power is high).
    """
    def __init__(self, name: str, max_power_kw: float = 7.2):
        super().__init__(name, "EV_CHARGER", max_power_kw)
        self.car_connected = False
        self.session_target_kwh = 0.0
        self.session_delivered_kwh = 0.0
        self.is_charging = False

    def plug_in_car(self, target_kwh: float):
        self.car_connected = True
        self.session_target_kwh = target_kwh
        self.session_delivered_kwh = 0.0
        self.is_charging = False
        logger.info(f"Car plugged into {self.name}, needs {target_kwh} kWh.")

    def unplug_car(self):
        self.car_connected = False
        self.is_charging = False
        self._update_state(0.0, "UNPLUGGED")
        logger.info(f"Car unplugged from {self.name}.")

    def start_charging(self):
        if self.car_connected and self.session_delivered_kwh < self.session_target_kwh:
            self.is_charging = True
            logger.info(f"EV Charger {self.name} started charging.")

    def pause_charging(self):
        self.is_charging = False
        logger.info(f"EV Charger {self.name} paused.")

    def tick(self, time_delta_seconds: float, external_conditions: Dict[str, Any]) -> DeviceState:
        if not self.is_connected or not self.car_connected:
            self._update_state(0.0, "UNPLUGGED" if not self.car_connected else "IDLE")
            return self.current_state

        hours_passed = time_delta_seconds / 3600.0
        power_kw = 0.0
        status = "PLUGGED_IDLE"

        if self.is_charging:
            remaining_kwh = self.session_target_kwh - self.session_delivered_kwh
            if remaining_kwh > 0.01:
                power_kw = min(self.max_power_kw, remaining_kwh / hours_passed)
                self.session_delivered_kwh += power_kw * hours_passed
                status = "CHARGING"
            else:
                self.is_charging = False
                status = "COMPLETE"

        progress = (self.session_delivered_kwh / self.session_target_kwh * 100.0) if self.session_target_kwh > 0 else 0.0
        self._update_state(power_kw, status, progress_percent=round(progress, 2))
        return self.current_state


class SmartHVAC(IoTDevice):
    """
    Heating, Ventilation, and Air Conditioning.
    A continuous load that modulates based on indoor/outdoor temperature differential.
    """
    def __init__(self, name: str, max_power_kw: float, target_temp_c: float = 22.0):
        super().__init__(name, "HVAC_SYSTEM", max_power_kw)
        self.target_temp_c = target_temp_c
        self.current_indoor_temp_c = 22.0
        self.insulation_factor = 0.95 # Higher means less temperature drift
        self.is_active = True

    def set_target_temp(self, temp_c: float):
        self.target_temp_c = temp_c
        logger.info(f"HVAC target temperature set to {temp_c}°C.")

    def toggle(self, state: bool):
        self.is_active = state

    def tick(self, time_delta_seconds: float, external_conditions: Dict[str, Any]) -> DeviceState:
        if not self.is_connected or not self.is_active:
            self._update_state(0.0, "OFF", temp=round(self.current_indoor_temp_c, 1))
            return self.current_state

        outdoor_temp_c = external_conditions.get("outdoor_temperature_c", 20.0)
        
        # Natural thermal drift
        temp_diff = outdoor_temp_c - self.current_indoor_temp_c
        drift = temp_diff * (1.0 - self.insulation_factor) * (time_delta_seconds / 3600.0)
        self.current_indoor_temp_c += drift

        power_kw = 0.0
        status = "FAN_ONLY"

        # HVAC Logic (Simplified Proportional Control)
        error = self.target_temp_c - self.current_indoor_temp_c
        
        if abs(error) > 0.5: # Deadband of 0.5 degrees
            # Demand power proportional to error
            demand_kw = abs(error) * 1.5 
            power_kw = min(demand_kw, self.max_power_kw)
            
            # Effect of HVAC running
            cooling_or_heating_effect = (power_kw / 1.5) * (time_delta_seconds / 3600.0)
            if error > 0:
                self.current_indoor_temp_c += cooling_or_heating_effect
                status = "HEATING"
            else:
                self.current_indoor_temp_c -= cooling_or_heating_effect
                status = "COOLING"

        self._update_state(power_kw, status, indoor_temp=round(self.current_indoor_temp_c, 1), target_temp=self.target_temp_c)
        return self.current_state

class SmartAppliance(IoTDevice):
    """
    Discrete load appliance (e.g., Dishwasher, Washing Machine, Dryer).
    Runs a specific program cycle with varying power phases over time.
    """
    def __init__(self, name: str, max_power_kw: float):
        super().__init__(name, "SMART_APPLIANCE", max_power_kw)
        # Define a standard cycle profile (List of (duration_seconds, power_multiplier))
        self.cycle_profile = [
            (900, 0.2),  # Fill / pre-wash: 15 mins at 20% power
            (1800, 1.0), # Main heat/wash: 30 mins at 100% power
            (900, 0.5),  # Rinse: 15 mins at 50% power
            (1200, 0.1)  # Dry/Spin: 20 mins at 10% power
        ]
        self.current_phase_index = -1
        self.phase_time_elapsed = 0.0
        self.is_running = False

    def start_cycle(self):
        if not self.is_running:
            self.is_running = True
            self.current_phase_index = 0
            self.phase_time_elapsed = 0.0
            logger.info(f"Appliance {self.name} started cycle.")

    def tick(self, time_delta_seconds: float, external_conditions: Dict[str, Any]) -> DeviceState:
        if not self.is_connected or not self.is_running:
            self._update_state(0.0, "OFF")
            return self.current_state

        if self.current_phase_index >= len(self.cycle_profile):
            self.is_running = False
            self._update_state(0.0, "FINISHED")
            return self.current_state

        phase_duration, power_multiplier = self.cycle_profile[self.current_phase_index]
        self.phase_time_elapsed += time_delta_seconds

        power_kw = self.max_power_kw * power_multiplier
        status = f"PHASE_{self.current_phase_index + 1}"

        if self.phase_time_elapsed >= phase_duration:
            # Move to next phase
            overflow = self.phase_time_elapsed - phase_duration
            self.current_phase_index += 1
            self.phase_time_elapsed = overflow

        self._update_state(power_kw, status, phase=self.current_phase_index + 1, total_phases=len(self.cycle_profile))
        return self.current_state
