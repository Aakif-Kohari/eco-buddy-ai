"""
Autonomous Robo-Taxi Fleet.
Simulates ridesharing algorithms to optimize vehicle utilization,
reducing the total number of cars needed in the city.
"""

from typing import List, Dict, Optional
import uuid
import random
import logging
from plugins.smart_city.road_network import CityGrid, Road
from plugins.smart_city.pathfinding import AStarPathfinder
from plugins.smart_city.emissions_physics import EVVehicle

logger = logging.getLogger(__name__)

class RideRequest:
    def __init__(self, passenger_id: str, pickup_node: str, dropoff_node: str):
        self.passenger_id = passenger_id
        self.pickup_node = pickup_node
        self.dropoff_node = dropoff_node
        self.assigned = False
        self.picked_up = False
        self.completed = False

class RoboTaxi:
    def __init__(self, start_node: str):
        self.id = f"Taxi_{uuid.uuid4()}"
        self.physics = EVVehicle(mass_kg=2000.0) # Robotaxis are heavy (sensors)
        self.current_node = start_node
        
        self.current_road: Optional[Road] = None
        self.route: List[str] = []
        self.route_index = 0
        self.distance_on_current_road = 0.0
        self.speed_ms = 0.0
        
        self.current_request: Optional[RideRequest] = None
        self.state = "IDLE" # IDLE, DISPATCHED, ON_TRIP
        
        self.total_co2_kg = 0.0
        self.battery_kwh = 100.0
        
    def assign_request(self, request: RideRequest, pathfinder: AStarPathfinder):
        self.current_request = request
        self.state = "DISPATCHED"
        request.assigned = True
        
        # Route to pickup
        path, _ = pathfinder.find_fastest_route(self.current_node, request.pickup_node)
        if path:
            self.route = path
            self.route_index = 0
            
    def handle_pickup(self, pathfinder: AStarPathfinder):
        self.state = "ON_TRIP"
        self.current_request.picked_up = True
        self.current_node = self.current_request.pickup_node
        
        # Route to dropoff
        path, _ = pathfinder.find_fastest_route(self.current_node, self.current_request.dropoff_node)
        if path:
            self.route = path
            self.route_index = 0
            
    def handle_dropoff(self):
        self.state = "IDLE"
        self.current_request.completed = True
        self.current_node = self.current_request.dropoff_node
        self.current_request = None
        self.route = []
        self.route_index = 0
        
    def tick(self, dt_seconds: float, city: CityGrid, pathfinder: AStarPathfinder):
        if self.state == "IDLE" or not self.route:
            # Idle power draw for sensors and AC
            self.battery_kwh -= 0.5 * (dt_seconds / 3600.0)
            return
            
        if not self.current_road and self.route:
            self.current_road = city.roads[self.route[0]]
            self.current_road.add_vehicle(self.id)
            
        if not self.current_road: return
        
        target_speed = (self.current_road.speed_limit_kmh / 3.6) / self.current_road.get_congestion_factor()
        
        if self.speed_ms < target_speed:
            accel = 2.0
        elif self.speed_ms > target_speed:
            accel = -3.0
        else:
            accel = 0.0
            
        self.speed_ms = max(0.0, self.speed_ms + accel * dt_seconds)
        
        emissions = self.physics.calculate_tick_emissions(self.speed_ms, accel, dt_seconds)
        self.total_co2_kg += emissions["co2_kg"]
        self.distance_on_current_road += self.speed_ms * dt_seconds
        
        if self.distance_on_current_road >= self.current_road.length_meters:
            self.current_road.remove_vehicle(self.id)
            self.route_index += 1
            
            # Check if reached node
            target_node = self.current_road.target.id
            if self.state == "DISPATCHED" and target_node == self.current_request.pickup_node:
                self.current_road = None
                self.speed_ms = 0.0
                self.handle_pickup(pathfinder)
                return
            elif self.state == "ON_TRIP" and target_node == self.current_request.dropoff_node:
                self.current_road = None
                self.speed_ms = 0.0
                self.handle_dropoff()
                return
                
            if self.route_index < len(self.route):
                self.current_road = city.roads[self.route[self.route_index]]
                self.current_road.add_vehicle(self.id)
                self.distance_on_current_road = 0.0
            else:
                self.current_road = None

class FleetManager:
    def __init__(self, num_taxis: int, nodes: List[str]):
        self.taxis: List[RoboTaxi] = []
        for _ in range(num_taxis):
            start = random.choice(nodes)
            self.taxis.append(RoboTaxi(start))
            
        self.pending_requests: List[RideRequest] = []
        
    def request_ride(self, passenger_id: str, pickup: str, dropoff: str):
        req = RideRequest(passenger_id, pickup, dropoff)
        self.pending_requests.append(req)
        
    def tick(self, dt_seconds: float, city: CityGrid, pathfinder: AStarPathfinder):
        # Assign requests to idle taxis
        unassigned = [r for r in self.pending_requests if not r.assigned]
        idle_taxis = [t for t in self.taxis if t.state == "IDLE"]
        
        for req in unassigned:
            if not idle_taxis: break
            # Simplified: just pick random idle taxi (in reality, find closest)
            taxi = idle_taxis.pop(0)
            taxi.assign_request(req, pathfinder)
            
        # Clean completed
        self.pending_requests = [r for r in self.pending_requests if not r.completed]
        
        # Tick all taxis
        for taxi in self.taxis:
            taxi.tick(dt_seconds, city, pathfinder)
