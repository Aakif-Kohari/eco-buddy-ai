"""
Lagrangian Particle Tracking Engine.
Moves thousands of plastic particles through the ocean using the Eulerian velocity field.
"""

import math
from typing import List, Dict
import logging
from plugins.ocean_current.world_map import WorldMapGrid
from plugins.ocean_current.fluid_dynamics import OceanCurrentSolver
from plugins.ocean_current.degradation_model import PlasticParticle

logger = logging.getLogger(__name__)

class LagrangianTracker:
    def __init__(self, grid: WorldMapGrid, solver: OceanCurrentSolver):
        self.grid = grid
        self.solver = solver
        self.particles: List[PlasticParticle] = []
        
        # Earth radius in meters
        self.R = 6371000.0
        
    def add_particle(self, particle: PlasticParticle):
        if self.grid.is_ocean(particle.lat, particle.lon):
            self.particles.append(particle)
        else:
            logger.warning(f"Cannot spawn particle {particle.id} on land.")
            
    def tick(self, dt_seconds: float, uv_index: float, surface_temp_c: float):
        """
        Advances all particles. Uses Euler integration for advection.
        """
        dt_days = dt_seconds / 86400.0
        
        for p in self.particles:
            if p.sunk:
                continue
                
            p.tick_degradation(dt_days, uv_index, surface_temp_c)
            if p.sunk:
                continue
                
            # Get velocity at current position
            u, v = self.solver.get_velocity(p.lat, p.lon)
            
            # Windage (Stokes drift / Wind leeway)
            # Plastics floating on the surface are pushed by the wind, not just the current
            # We assume a constant prevailing Westerly wind (blowing East) in mid-latitudes
            # and Trade winds (blowing West) near the equator.
            wind_u = 0.0
            if -30 < p.lat < 30:
                wind_u = -2.0 # Trade winds
            elif 30 <= p.lat <= 60 or -60 <= p.lat <= -30:
                wind_u = 2.0 # Westerlies
                
            # Leeway is typically 1-3% of wind speed for floating objects
            leeway_u = wind_u * 0.02
            
            total_u = u + leeway_u
            total_v = v
            
            # Convert m/s to degrees per second
            # dlat = V / R
            # dlon = U / (R * cos(lat))
            lat_rad = math.radians(p.lat)
            dlat_rad = (total_v * dt_seconds) / self.R
            dlon_rad = (total_u * dt_seconds) / (self.R * math.cos(lat_rad))
            
            dlat_deg = math.degrees(dlat_rad)
            dlon_deg = math.degrees(dlon_rad)
            
            new_lat = p.lat + dlat_deg
            new_lon = p.lon + dlon_deg
            
            # Wrap longitude
            if new_lon > 180: new_lon -= 360
            if new_lon < -180: new_lon += 360
            
            # Clamp latitude
            new_lat = max(-89.9, min(89.9, new_lat))
            
            # Check for beaching (hitting land)
            if self.grid.is_ocean(new_lat, new_lon):
                p.lat = new_lat
                p.lon = new_lon
            else:
                # Beached! Stays at current valid ocean position
                pass
                
    def get_gyre_accumulation(self) -> Dict[str, float]:
        """
        Calculates mass in known Garbage Patch locations.
        """
        patches = {
            "Great Pacific Garbage Patch": {"lat_range": (20, 40), "lon_range": (-155, -135)},
            "North Atlantic Garbage Patch": {"lat_range": (22, 38), "lon_range": (-70, -30)},
            "Indian Ocean Garbage Patch": {"lat_range": (-40, -20), "lon_range": (50, 100)}
        }
        
        results = {name: 0.0 for name in patches}
        
        for p in self.particles:
            if p.sunk: continue
            
            for patch_name, bounds in patches.items():
                min_lat, max_lat = bounds["lat_range"]
                min_lon, max_lon = bounds["lon_range"]
                
                if min_lat <= p.lat <= max_lat and min_lon <= p.lon <= max_lon:
                    results[patch_name] += p.current_mass_kg
                    
        return results
