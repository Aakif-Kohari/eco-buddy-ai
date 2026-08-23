import math
from dataclasses import dataclass
from typing import Dict, Any, Tuple

# Constants for Battery Chemistry (Lithium-Ion typical degradation profiles)
# Degradation happens via cycle aging (usage) and calendar aging (time)
CYCLE_DEGRADATION_FACTOR = 0.00018  # Capacity lost per full charge cycle
CALENDAR_DEGRADATION_FACTOR = 0.015 # Capacity lost per year regardless of use
OPTIMAL_CAPACITY_THRESHOLD = 0.80   # Batteries below 80% are considered degraded

@dataclass
class DeviceSpec:
    name: str
    battery_capacity_mah: float
    embodied_carbon_kg: float
    battery_replacement_carbon_kg: float
    recyclability_percent: float

# Extensive database of hardware specifications for LCA (Life Cycle Assessment)
HARDWARE_SPECS = {
    "Smartphone": DeviceSpec("Smartphone", 3500, 60.0, 8.0, 85.0),
    "Tablet": DeviceSpec("Tablet", 8000, 120.0, 15.0, 80.0),
    "Laptop": DeviceSpec("Laptop", 50000, 350.0, 45.0, 75.0),
    "Desktop_PC": DeviceSpec("Desktop_PC", 0, 500.0, 0.0, 60.0), # No battery
    "Smart_TV_4K": DeviceSpec("Smart_TV_4K", 0, 400.0, 0.0, 50.0), # No battery
}

class DeviceLifecycleEngine:
    """
    Advanced mathematical engine for simulating hardware degradation, 
    embodied carbon amortization, and E-Waste metrics over time.
    """

    def __init__(self, device_type: str, current_age_years: float, daily_charge_cycles: float):
        if device_type not in HARDWARE_SPECS:
            raise ValueError(f"Unknown device type: {device_type}")
            
        self.spec = HARDWARE_SPECS[device_type]
        self.age_years = float(current_age_years)
        self.daily_cycles = float(daily_charge_cycles)

    def calculate_battery_health(self, future_years: float = 0.0) -> float:
        """
        Calculates the current or future battery health percentage (0.0 to 1.0).
        Uses a combined linear model of cycle aging and calendar aging.
        """
        if self.spec.battery_capacity_mah == 0:
            return 1.0 # Devices without batteries don't degrade in this specific way
            
        total_age = self.age_years + future_years
        total_cycles = self.daily_cycles * 365 * total_age
        
        cycle_degradation = total_cycles * CYCLE_DEGRADATION_FACTOR
        calendar_degradation = total_age * CALENDAR_DEGRADATION_FACTOR
        
        health = 1.0 - (cycle_degradation + calendar_degradation)
        return max(0.0, min(1.0, health))

    def get_amortized_carbon(self, include_new_battery: bool = False) -> float:
        """
        Calculates the amortized embodied carbon per year of ownership.
        Keeping a device longer spreads its massive manufacturing footprint over more years.
        """
        total_carbon = self.spec.embodied_carbon_kg
        if include_new_battery:
            total_carbon += self.spec.battery_replacement_carbon_kg
            
        # Avoid division by zero for brand new devices, assume 1st year is ongoing
        effective_years = max(1.0, self.age_years)
        return total_carbon / effective_years

    def simulate_upgrade_vs_repair(self) -> Dict[str, Any]:
        """
        Runs a simulation to determine if the user should:
        1. Keep the device as is.
        2. Replace the battery to extend lifespan.
        3. Buy a brand new device.
        Returns the carbon mathematically saved by choosing repair over replacement.
        """
        current_health = self.calculate_battery_health()
        
        # Scenario A: Buy a new device now (resets age, adds massive embodied carbon)
        carbon_cost_new_device = self.spec.embodied_carbon_kg
        
        # Scenario B: Replace battery and keep for 2 more years
        carbon_cost_battery = self.spec.battery_replacement_carbon_kg
        
        # Scenario C: Do nothing and keep using (0 carbon cost, but bad user experience)
        carbon_cost_nothing = 0.0
        
        recommendation = "Keep using your device."
        carbon_savings_kg = 0.0
        
        if self.spec.battery_capacity_mah > 0:
            if current_health < OPTIMAL_CAPACITY_THRESHOLD:
                # Mathematically, replacing a battery is almost always better than buying new
                carbon_savings_kg = carbon_cost_new_device - carbon_cost_battery
                recommendation = f"Your battery health is degraded (~{int(current_health*100)}%). REPLACE THE BATTERY instead of upgrading. This saves {carbon_savings_kg:.1f} kg of CO2e!"
            else:
                carbon_savings_kg = carbon_cost_new_device
                recommendation = f"Your battery is healthy (~{int(current_health*100)}%). DO NOT UPGRADE yet. Keeping it saves {carbon_savings_kg:.1f} kg CO2e in manufacturing costs."
        else:
            # Desktop/TVs
            if self.age_years < 7.0:
                carbon_savings_kg = carbon_cost_new_device
                recommendation = f"DO NOT UPGRADE your {self.spec.name}. Extending its life past {int(self.age_years)} years saves {carbon_savings_kg:.1f} kg CO2e."
            else:
                recommendation = f"Your {self.spec.name} is {int(self.age_years)} years old. If upgrading, ensure it is recycled to recover {self.spec.recyclability_percent}% of materials."

        return {
            "current_health_percent": current_health * 100,
            "amortized_annual_carbon": self.get_amortized_carbon(),
            "recommendation": recommendation,
            "carbon_saved_by_not_upgrading": carbon_savings_kg,
            "e_waste_kg_prevented": self.spec.embodied_carbon_kg * 0.05 # rough proxy for physical mass based on carbon density
        }

    def generate_lifecycle_report(self) -> Dict[str, Any]:
        """Generates a full telemetry report for the UI."""
        return {
            "device": self.spec.name,
            "age_years": self.age_years,
            "battery_health": self.calculate_battery_health() * 100,
            "amortized_carbon_per_year": self.get_amortized_carbon(),
            "total_embodied_carbon": self.spec.embodied_carbon_kg,
            "recyclability": self.spec.recyclability_percent,
            "upgrade_analysis": self.simulate_upgrade_vs_repair()
        }
