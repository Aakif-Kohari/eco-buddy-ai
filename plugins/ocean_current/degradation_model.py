"""
Photodegradation & Buoyancy Model.
Simulates how macro-plastics break down into micro-plastics over time due to UV,
and how biofouling causes them to sink out of the surface layer.
"""

import math

class PlasticParticle:
    def __init__(self, pid: str, lat: float, lon: float, mass_kg: float, is_microplastic: bool = False):
        self.id = pid
        self.lat = lat
        self.lon = lon
        
        self.original_mass_kg = mass_kg
        self.current_mass_kg = mass_kg
        self.is_microplastic = is_microplastic
        
        self.age_days = 0.0
        self.sunk = False
        
        # Depth in meters (0 is surface)
        self.depth_m = 0.0
        
    def tick_degradation(self, dt_days: float, uv_index: float, surface_temp_c: float):
        """
        Updates the physical state of the plastic based on environmental factors.
        """
        if self.sunk:
            return
            
        self.age_days += dt_days
        
        # 1. Photodegradation (UV breaks down polymer chains)
        # Macroplastics shed microplastics, losing mass.
        if not self.is_microplastic:
            # Shedding rate increases with UV and temperature
            base_shed_rate = 0.0001 # 0.01% of mass per day
            temp_factor = max(0.1, surface_temp_c / 15.0)
            uv_factor = max(0.1, uv_index / 5.0)
            
            shed_amount = self.current_mass_kg * base_shed_rate * temp_factor * uv_factor * dt_days
            self.current_mass_kg = max(0.0, self.current_mass_kg - shed_amount)
            
            if self.current_mass_kg < (self.original_mass_kg * 0.05):
                # If 95% degraded, we consider the remnant itself a microplastic
                self.is_microplastic = True
                
        # 2. Biofouling (Algae/Barnacles attach to the plastic)
        # Microplastics biofoul faster due to high surface-area-to-volume ratio
        biofoul_rate = 0.05 if self.is_microplastic else 0.01
        biofoul_accumulation = self.age_days * biofoul_rate * (surface_temp_c / 20.0)
        
        # 3. Buoyancy loss
        # Most ocean plastics (PE, PP) start positively buoyant
        if biofoul_accumulation > 10.0: # Arbitrary threshold
            self.depth_m += 0.5 * dt_days # Sink 0.5m per day
            
        if self.depth_m > 10.0:
            # Sunk out of the surface Ekman layer
            self.sunk = True
