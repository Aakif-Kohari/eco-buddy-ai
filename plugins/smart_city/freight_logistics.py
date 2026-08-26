"""
Smart City Freight & Logistics Simulator.
Models the macroscopic impact of heavy-duty trucks and last-mile delivery vans
on city congestion and emissions.
"""

from typing import List, Dict, Optional
import math
import random
import uuid
import logging
from plugins.smart_city.road_network import CityGrid, Road
from plugins.smart_city.pathfinding import AStarPathfinder
from plugins.smart_city.emissions_physics import VehiclePhysics

logger = logging.getLogger(__name__)

class HeavyDutyTruckPhysics(VehiclePhysics):
    """Class 8 Semi-Truck with massive payload."""
    def __init__(self, empty_weight_kg: float = 15000.0, payload_kg: float = 20000.0):
        total_mass = empty_weight_kg + payload_kg
        super().__init__(mass_kg=total_mass, frontal_area_m2=10.0, drag_coeff=0.8)
        self.engine_efficiency = 0.40 # Heavy diesel is efficient but massive
        self.joules_per_liter = 38.6e6
        self.co2_per_liter = 2.68
        
    def calculate_tick_emissions(self, speed_ms: float, accel_ms2: float, dt_seconds: float) -> Dict[str, float]:
        if speed_ms <= 0.1 and accel_ms2 <= 0:
            fuel = 0.002 * dt_seconds # Idles at 2 liters/hour
            return {"co2_kg": fuel * self.co2_per_liter, "nox_g": 0.5 * dt_seconds, "pm25_g": 0.1 * dt_seconds}
            
        power = self.get_tractive_power_watts(speed_ms, accel_ms2)
        fuel = (power / self.engine_efficiency * dt_seconds) / self.joules_per_liter
        
        # Heavy trucks emit huge NOx
        nox = fuel * 5.0
        pm25 = fuel * 0.8
        return {"co2_kg": fuel * self.co2_per_liter, "nox_g": nox, "pm25_g": pm25}

class DeliveryVanPhysics(VehiclePhysics):
    """Last-mile delivery van (e.g., Amazon, UPS)."""
    def __init__(self, is_ev: bool = False):
        super().__init__(mass_kg=4000.0, frontal_area_m2=5.0, drag_coeff=0.45)
        self.is_ev = is_ev
        if not is_ev:
            self.engine_efficiency = 0.28
            self.joules_per_liter = 34.2e6
            self.co2_per_liter = 2.31
        else:
            self.motor_efficiency = 0.85
            self.grid_carbon = 0.4 # kg CO2/kWh
            self.regen_efficiency = 0.5
            
    def calculate_tick_emissions(self, speed_ms: float, accel_ms2: float, dt_seconds: float) -> Dict[str, float]:
        if self.is_ev:
            if speed_ms <= 0.1 and accel_ms2 <= 0:
                return {"co2_kg": (1.0/3600)*dt_seconds*self.grid_carbon, "nox_g": 0.0, "pm25_g": 0.0}
            
            power = self.get_tractive_power_watts(speed_ms, accel_ms2)
            if accel_ms2 < 0:
                power = -abs(self.mass_kg * accel_ms2 * speed_ms) * self.regen_efficiency
                
            energy_kwh = (power / self.motor_efficiency / 1000.0) * (dt_seconds / 3600.0) if power > 0 else (power * self.motor_efficiency / 1000.0) * (dt_seconds / 3600.0)
            co2 = max(0.0, energy_kwh * self.grid_carbon)
            return {"co2_kg": co2, "nox_g": 0.0, "pm25_g": 0.1} # Higher PM25 due to weight
        else:
            if speed_ms <= 0.1 and accel_ms2 <= 0:
                return {"co2_kg": (0.0008*dt_seconds)*self.co2_per_liter, "nox_g": 0.1*dt_seconds, "pm25_g": 0.02*dt_seconds}
                
            power = self.get_tractive_power_watts(speed_ms, accel_ms2)
            fuel = (power / self.engine_efficiency * dt_seconds) / self.joules_per_liter
            return {"co2_kg": fuel * self.co2_per_liter, "nox_g": fuel * 2.0, "pm25_g": fuel * 0.2}

class FreightDepot:
    def __init__(self, node_id: str, depot_type: str):
        self.node_id = node_id
        self.depot_type = depot_type # DISTRIBUTION_CENTER, RETAIL_STORE, RESIDENTIAL_HUB

class FreightAgent:
    def __init__(self, start_node: str, route_nodes: List[str], vehicle_type: str):
        self.id = f"Freight_{uuid.uuid4()}"
        self.start_node = start_node
        self.stops = route_nodes
        self.current_stop_index = 0
        
        self.vehicle_type = vehicle_type
        if vehicle_type == "HEAVY_TRUCK":
            self.physics = HeavyDutyTruckPhysics()
        elif vehicle_type == "EV_VAN":
            self.physics = DeliveryVanPhysics(is_ev=True)
        else:
            self.physics = DeliveryVanPhysics(is_ev=False)
            
        self.route: List[str] = []
        self.route_index = 0
        self.current_road: Optional[Road] = None
        self.distance_on_current_road = 0.0
        self.speed_ms = 0.0
        
        self.total_co2_kg = 0.0
        self.total_nox_g = 0.0
        self.total_pm25_g = 0.0
        self.finished = False

    def update_route(self, pathfinder: AStarPathfinder):
        if self.current_stop_index < len(self.stops):
            goal = self.stops[self.current_stop_index]
            start = self.current_road.target.id if self.current_road else self.start_node
            path, _ = pathfinder.find_fastest_route(start, goal)
            if path:
                self.route = path
                self.route_index = 0
            else:
                self.finished = True
        else:
            self.finished = True

    def tick(self, dt_seconds: float, city: CityGrid, pathfinder: AStarPathfinder):
        if self.finished: return
        
        if not self.current_road and self.route:
            self.current_road = city.roads[self.route[0]]
            self.current_road.add_vehicle(self.id)
            
        if not self.current_road: return
        
        speed_limit = self.current_road.speed_limit_kmh / 3.6
        congestion = self.current_road.get_congestion_factor()
        
        target_speed = speed_limit / congestion
        
        # Heavy trucks accelerate slower
        accel_cap = 1.0 if self.vehicle_type == "HEAVY_TRUCK" else 2.0
        if self.speed_ms < target_speed:
            accel = accel_cap
        elif self.speed_ms > target_speed:
            accel = -2.0
        else:
            accel = 0.0
            
        self.speed_ms = max(0.0, self.speed_ms + accel * dt_seconds)
        
        emissions = self.physics.calculate_tick_emissions(self.speed_ms, accel, dt_seconds)
        self.total_co2_kg += emissions["co2_kg"]
        self.total_nox_g += emissions["nox_g"]
        self.total_pm25_g += emissions["pm25_g"]
        
        self.distance_on_current_road += self.speed_ms * dt_seconds
        
        if self.distance_on_current_road >= self.current_road.length_meters:
            self.current_road.remove_vehicle(self.id)
            self.route_index += 1
            
            # Check if we reached the current stop
            if self.current_road.target.id == self.stops[self.current_stop_index]:
                self.current_stop_index += 1
                self.update_route(pathfinder)
                self.current_road = None
                self.speed_ms = 0.0
                return
                
            if self.route_index < len(self.route):
                self.current_road = city.roads[self.route[self.route_index]]
                self.current_road.add_vehicle(self.id)
                self.distance_on_current_road = 0.0
            else:
                self.current_road = None
                self.finished = True
