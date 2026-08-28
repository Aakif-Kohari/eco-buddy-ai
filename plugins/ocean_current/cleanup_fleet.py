"""
Autonomous Ocean Cleanup Fleet Model.
Simulates autonomous vessels that sweep the ocean gyres to extract macro and microplastics.
"""

from typing import List
import math
from plugins.ocean_current.particle_tracker import LagrangianTracker
from plugins.ocean_current.degradation_model import PlasticParticle

class CleanupVessel:
    def __init__(self, vid: str, lat: float, lon: float, sweep_width_m: float, speed_ms: float):
        self.id = vid
        self.lat = lat
        self.lon = lon
        self.sweep_width_m = sweep_width_m
        self.speed_ms = speed_ms
        
        self.extracted_mass_kg = 0.0
        self.capacity_kg = 50000.0 # 50 tons
        
        # Simple AI state
        self.target_lat = None
        self.target_lon = None
        
    def set_target(self, lat: float, lon: float):
        self.target_lat = lat
        self.target_lon = lon
        
    def move(self, dt_seconds: float):
        if self.target_lat is None or self.target_lon is None:
            return
            
        # Very simple straight-line movement towards target
        R = 6371000.0
        
        # Haversine distance approx
        dlat = self.target_lat - self.lat
        dlon = self.target_lon - self.lon
        
        # Avoid div zero
        if abs(dlat) < 0.001 and abs(dlon) < 0.001:
            self.target_lat = None
            self.target_lon = None
            return
            
        # Normalize direction
        mag = math.sqrt(dlat**2 + dlon**2)
        dir_lat = dlat / mag
        dir_lon = dlon / mag
        
        # Move
        dist_m = self.speed_ms * dt_seconds
        
        # Convert dist to deg (rough approx)
        dlat_deg = (dist_m * dir_lat) / R * (180.0 / math.pi)
        dlon_deg = (dist_m * dir_lon) / (R * math.cos(math.radians(self.lat))) * (180.0 / math.pi)
        
        self.lat += dlat_deg
        self.lon += dlon_deg

class FleetManager:
    def __init__(self, tracker: LagrangianTracker):
        self.tracker = tracker
        self.vessels: List[CleanupVessel] = []
        
    def add_vessel(self, vessel: CleanupVessel):
        self.vessels.append(vessel)
        
    def tick_cleanup(self, dt_seconds: float):
        """
        Moves the fleet and extracts plastic that falls within their sweep area.
        """
        for vessel in self.vessels:
            if vessel.extracted_mass_kg >= vessel.capacity_kg:
                # Full! Return to port (simplified: just stops)
                vessel.target_lat = None
                continue
                
            # If no target, pick the largest plastic particle nearby
            if vessel.target_lat is None:
                best_p = None
                best_mass = 0.0
                for p in self.tracker.particles:
                    if not p.sunk and p.current_mass_kg > best_mass:
                        # Only target if reasonably close (e.g., same gyre)
                        if abs(p.lat - vessel.lat) < 20 and abs(p.lon - vessel.lon) < 20:
                            best_mass = p.current_mass_kg
                            best_p = p
                            
                if best_p:
                    vessel.set_target(best_p.lat, best_p.lon)
                    
            # Move vessel
            vessel.move(dt_seconds)
            
            # Sweep! (Find plastics within a highly simplified bounding box of the sweep width)
            # 1 degree of lat is ~111km
            sweep_deg = (vessel.sweep_width_m / 111000.0)
            
            extracted_this_tick = []
            for p in self.tracker.particles:
                if p.sunk: continue
                
                if abs(p.lat - vessel.lat) < sweep_deg and abs(p.lon - vessel.lon) < sweep_deg:
                    # Captured!
                    space_left = vessel.capacity_kg - vessel.extracted_mass_kg
                    if p.current_mass_kg <= space_left:
                        vessel.extracted_mass_kg += p.current_mass_kg
                        p.current_mass_kg = 0.0
                        extracted_this_tick.append(p)
                    else:
                        vessel.extracted_mass_kg += space_left
                        p.current_mass_kg -= space_left
                        
            # Remove fully extracted particles from the tracker
            if extracted_this_tick:
                self.tracker.particles = [p for p in self.tracker.particles if p.current_mass_kg > 0]
