"""
Advanced Microplastics Shedding Simulator.
Models the hydrodynamic release of synthetic microfibers during domestic laundering.
Variables include water temperature, spin speed, detergent chemistry, and fabric age.
"""

import math
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MicroplasticSheddingModel:
    """
    Mathematical model to estimate microplastic pollution from washing synthetic textiles.
    Based on empirical studies of polyester, nylon, and acrylic shedding rates.
    """
    
    def __init__(self):
        # Base shedding rates (mg of microfibers per kg of fabric per wash)
        self.base_shed_rates_mg_kg = {
            'Polyester (Virgin)': 120.0,
            'Polyester (Recycled)': 140.0, # Recycled often has shorter staple fibers, shedding slightly more
            'Nylon': 90.0,
            'Acrylic': 250.0,
            'Elastane/Spandex': 50.0
        }
        
    def _calculate_temperature_modifier(self, temp_celsius: int) -> float:
        """Higher temperatures degrade fibers faster, increasing shedding."""
        if temp_celsius <= 30:
            return 1.0 # Baseline for cold wash
        elif temp_celsius <= 40:
            return 1.15
        elif temp_celsius <= 60:
            return 1.45
        else:
            return 2.0 # Boiling / heavy sanitization
            
    def _calculate_spin_speed_modifier(self, rpm: int) -> float:
        """Higher mechanical agitation (RPM) increases friction and shedding."""
        if rpm <= 800:
            return 1.0 # Gentle cycle
        elif rpm <= 1000:
            return 1.2
        elif rpm <= 1200:
            return 1.5
        else:
            return 1.8 # Heavy duty spin
            
    def _calculate_age_modifier(self, total_washes_so_far: int) -> float:
        """
        Shedding follows a decay curve. New garments shed the most in their first 5 washes
        (removing loose fibers from manufacturing), then plateau to a steady state.
        """
        if total_washes_so_far == 0:
            return 3.0 # First wash sheds heavily
        elif total_washes_so_far <= 5:
            # Exponential decay for the first few washes
            return 1.0 + (2.0 * math.exp(-0.4 * total_washes_so_far))
        else:
            return 1.0 # Steady state
            
    def simulate_lifetime_shedding(self, 
                                   garment_weight_kg: float, 
                                   material_blend: Dict[str, float],
                                   washes_per_year: int = 12,
                                   lifespan_years: float = 2.0,
                                   wash_temp_c: int = 40,
                                   spin_speed_rpm: int = 1000,
                                   has_guppyfriend_bag: bool = False) -> Dict[str, Any]:
        """
        Simulates the total microplastic mass shed over the garment's entire lifetime.
        
        Returns:
            Dict containing total mass shed, particle count estimate, and risk level.
        """
        total_washes = int(washes_per_year * lifespan_years)
        temp_mod = self._calculate_temperature_modifier(wash_temp_c)
        spin_mod = self._calculate_spin_speed_modifier(spin_speed_rpm)
        
        # Filtration mitigation
        # A Guppyfriend washing bag or washing machine filter catches ~90% of fibers
        filtration_efficiency = 0.10 if has_guppyfriend_bag else 1.0
        
        total_shed_mg = 0.0
        yearly_shed_profile = []
        
        for wash_idx in range(total_washes):
            wash_shed_mg = 0.0
            age_mod = self._calculate_age_modifier(wash_idx)
            
            for material, percentage in material_blend.items():
                if material in self.base_shed_rates_mg_kg:
                    base_rate = self.base_shed_rates_mg_kg[material]
                    mass_kg = garment_weight_kg * percentage
                    
                    # Compute shed for this specific wash
                    shed_amount = base_rate * mass_kg * temp_mod * spin_mod * age_mod * filtration_efficiency
                    wash_shed_mg += shed_amount
                    
            total_shed_mg += wash_shed_mg
            
            # Record yearly aggregates
            if wash_idx % washes_per_year == 0:
                yearly_shed_profile.append({
                    "year": (wash_idx // washes_per_year) + 1,
                    "cumulative_shed_mg": round(total_shed_mg, 2)
                })

        # Convert mg to grams for final output
        total_shed_grams = total_shed_mg / 1000.0
        
        # Estimate particle count (assuming average microfiber weighs 0.000005 grams)
        particle_count_estimate = int(total_shed_grams / 0.000005) if total_shed_grams > 0 else 0
        
        risk_level = "None"
        if total_shed_grams > 5.0:
            risk_level = "Severe"
        elif total_shed_grams > 1.0:
            risk_level = "High"
        elif total_shed_grams > 0.1:
            risk_level = "Moderate"
        elif total_shed_grams > 0.0:
            risk_level = "Low"

        return {
            "total_microplastics_grams": round(total_shed_grams, 3),
            "estimated_particle_count": particle_count_estimate,
            "risk_severity": risk_level,
            "yearly_profile": yearly_shed_profile,
            "total_lifetime_washes": total_washes
        }
