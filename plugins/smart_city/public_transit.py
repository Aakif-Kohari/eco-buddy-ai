"""
Public Transit Systems.
Models high-capacity buses and trains running on fixed schedules, pulling 
commuters out of single-occupancy vehicles to reduce city CO2.
"""

from typing import List
from plugins.smart_city.emissions_physics import VehiclePhysics
from plugins.smart_city.road_network import CityGrid, Road
from plugins.smart_city.pathfinding import AStarPathfinder
import logging

logger = logging.getLogger(__name__)

class BusPhysics(VehiclePhysics):
    def __init__(self):
        # 12,000 kg bus, large frontal area
        super().__init__(mass_kg=12000.0, frontal_area_m2=7.0, drag_coeff=0.6)
        self.engine_efficiency = 0.35 # Heavy duty diesel is more thermally efficient
        self.joules_per_liter = 38.6e6 # Diesel energy density
        self.co2_per_liter = 2.68 # Diesel CO2
        self.idle_fuel_l_per_sec = 0.001
        
    def calculate_tick_emissions(self, speed_ms: float, accel_ms2: float, dt_seconds: float) -> dict:
        if speed_ms <= 0.1 and accel_ms2 <= 0:
            fuel = self.idle_fuel_l_per_sec * dt_seconds
            return {"co2_kg": fuel * self.co2_per_liter}
            
        power = self.get_tractive_power_watts(speed_ms, accel_ms2)
        fuel = (power / self.engine_efficiency * dt_seconds) / self.joules_per_liter
        return {"co2_kg": fuel * self.co2_per_liter}

class TransitRoute:
    def __init__(self, name: str, stops: List[str]):
        self.name = name
        self.stops = stops # Intersection IDs
        
class CityBus:
    def __init__(self, route: TransitRoute, city: CityGrid):
        self.route = route
        self.physics = BusPhysics()
        self.capacity = 60
        self.current_passengers = 0
        self.total_co2_kg = 0.0
        
        # We need a pathfinder to navigate between stops
        self.pathfinder = AStarPathfinder(city)
        self.current_stop_index = 0
        self.path_to_next_stop: List[str] = []
        
        self._calculate_path_to_next_stop(city)
        
    def _calculate_path_to_next_stop(self, city: CityGrid):
        if len(self.route.stops) < 2:
            return
            
        current_stop = self.route.stops[self.current_stop_index]
        next_stop_index = (self.current_stop_index + 1) % len(self.route.stops)
        next_stop = self.route.stops[next_stop_index]
        
        path, _ = self.pathfinder.find_fastest_route(current_stop, next_stop)
        self.path_to_next_stop = path
        
    def board_passengers(self, waiting_count: int) -> int:
        """Returns number of passengers successfully boarded."""
        space = self.capacity - self.current_passengers
        boarded = min(waiting_count, space)
        self.current_passengers += boarded
        return boarded
        
    def alight_passengers(self, drop_off_ratio: float = 0.3):
        dropping = int(self.current_passengers * drop_off_ratio)
        self.current_passengers -= dropping
