"""
Vehicle Physics & Emissions Engine.
Calculates instantaneous fuel consumption and CO2 emissions using mechanical physics:
Aerodynamic drag, rolling resistance, inertial acceleration, and idling.
"""

import math
from typing import Dict, Any

class VehiclePhysics:
    """Base class for modeling physical energy consumption."""
    def __init__(self, mass_kg: float, frontal_area_m2: float, drag_coeff: float):
        self.mass_kg = mass_kg
        self.frontal_area_m2 = frontal_area_m2
        self.drag_coeff = drag_coeff
        self.air_density_kg_m3 = 1.225 # Sea level
        self.gravity = 9.81
        self.rolling_coeff = 0.015 # Typical asphalt
        
    def get_tractive_power_watts(self, speed_ms: float, accel_ms2: float, grade_percent: float = 0.0) -> float:
        """Calculates power required at the wheels."""
        if speed_ms <= 0 and accel_ms2 <= 0:
            return 0.0
            
        # 1. Aerodynamic Drag: F_aero = 0.5 * rho * Cd * A * v^2
        f_aero = 0.5 * self.air_density_kg_m3 * self.drag_coeff * self.frontal_area_m2 * (speed_ms ** 2)
        
        # 2. Rolling Resistance: F_roll = Crr * m * g * cos(theta)
        theta = math.atan(grade_percent / 100.0)
        f_roll = self.rolling_coeff * self.mass_kg * self.gravity * math.cos(theta)
        
        # 3. Grade Resistance: F_grade = m * g * sin(theta)
        f_grade = self.mass_kg * self.gravity * math.sin(theta)
        
        # 4. Inertial Acceleration: F_accel = m * a
        f_accel = self.mass_kg * accel_ms2
        
        total_force_newtons = f_aero + f_roll + f_grade + f_accel
        
        # Power = Force * Velocity
        power_watts = total_force_newtons * speed_ms
        return max(0.0, power_watts) # No regenerative braking in base model

class ICEVehicle(VehiclePhysics):
    """Internal Combustion Engine."""
    def __init__(self, mass_kg: float = 1500.0, engine_efficiency: float = 0.25):
        super().__init__(mass_kg, 2.2, 0.3)
        self.engine_efficiency = engine_efficiency
        # Gasoline energy density ~ 43.4 MJ/kg or ~ 34.2 MJ/Liter
        # CO2 from burning 1 Liter of gasoline ~ 2.31 kg CO2
        self.joules_per_liter = 34.2e6
        self.co2_per_liter = 2.31
        self.idle_fuel_l_per_sec = 0.0003 # ~1 liter per hour
        
    def calculate_tick_emissions(self, speed_ms: float, accel_ms2: float, dt_seconds: float) -> Dict[str, float]:
        if speed_ms <= 0.1 and accel_ms2 <= 0:
            # Idling
            fuel_used = self.idle_fuel_l_per_sec * dt_seconds
            co2 = fuel_used * self.co2_per_liter
            return {"co2_kg": co2, "nox_g": 0.05 * dt_seconds, "pm25_g": 0.01 * dt_seconds}
            
        wheel_power = self.get_tractive_power_watts(speed_ms, accel_ms2)
        engine_power = wheel_power / self.engine_efficiency
        energy_joules = engine_power * dt_seconds
        
        fuel_liters = energy_joules / self.joules_per_liter
        co2_kg = fuel_liters * self.co2_per_liter
        
        # NOx and PM2.5 scale with load
        nox = fuel_liters * 1.5 # grams
        pm25 = fuel_liters * 0.1 # grams
        
        return {"co2_kg": co2_kg, "nox_g": nox, "pm25_g": pm25}

class EVVehicle(VehiclePhysics):
    """Electric Vehicle."""
    def __init__(self, mass_kg: float = 1800.0, grid_carbon_intensity_kg_kwh: float = 0.4):
        super().__init__(mass_kg, 2.2, 0.25) # EVs often heavier but more aerodynamic
        self.motor_efficiency = 0.90
        self.grid_carbon = grid_carbon_intensity_kg_kwh
        self.regen_efficiency = 0.60
        
    def calculate_tick_emissions(self, speed_ms: float, accel_ms2: float, dt_seconds: float) -> Dict[str, float]:
        if speed_ms <= 0.1 and accel_ms2 <= 0:
            # EVs idle very efficiently (just AC/Electronics)
            kw_idle = 0.5 
            energy_kwh = (kw_idle / 3600) * dt_seconds
            return {"co2_kg": energy_kwh * self.grid_carbon, "nox_g": 0.0, "pm25_g": 0.0}
            
        wheel_power = self.get_tractive_power_watts(speed_ms, accel_ms2)
        
        # Regenerative braking
        if accel_ms2 < 0:
            # Recover some kinetic energy
            regen_power = abs(self.mass_kg * accel_ms2 * speed_ms) * self.regen_efficiency
            wheel_power = -regen_power
            
        battery_power_watts = wheel_power / self.motor_efficiency if wheel_power > 0 else wheel_power * self.motor_efficiency
        
        # If battery power is negative, we are charging (net negative emissions theoretically, or 0)
        energy_kwh = (battery_power_watts / 1000.0) * (dt_seconds / 3600.0)
        co2 = max(0.0, energy_kwh * self.grid_carbon)
        
        # EVs emit PM2.5 from tire wear!
        tire_pm25 = (speed_ms * dt_seconds / 1000.0) * 0.05 # 0.05g per km
        
        return {"co2_kg": co2, "nox_g": 0.0, "pm25_g": tire_pm25}
