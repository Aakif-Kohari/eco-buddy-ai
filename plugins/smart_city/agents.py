"""
Autonomous Commuter Agents.
Simulates AI-driven vehicles navigating the city, updating speeds, and reacting to traffic.
"""

import uuid
from typing import List, Dict, Optional
from plugins.smart_city.emissions_physics import ICEVehicle, EVVehicle
from plugins.smart_city.road_network import CityGrid, Road

class CommuterAgent:
    def __init__(self, start_node_id: str, goal_node_id: str, is_ev: bool = False):
        self.id = str(uuid.uuid4())
        self.start_node_id = start_node_id
        self.goal_node_id = goal_node_id
        self.current_road: Optional[Road] = None
        self.distance_on_current_road = 0.0
        
        self.route: List[str] = [] # List of Road IDs
        self.route_index = 0
        
        self.speed_ms = 0.0
        self.accel_ms2 = 0.0
        
        self.is_ev = is_ev
        self.physics = EVVehicle() if is_ev else ICEVehicle()
        
        self.total_co2_kg = 0.0
        self.total_travel_time = 0.0
        self.finished = False

    def assign_route(self, route_road_ids: List[str], city: CityGrid):
        self.route = route_road_ids
        self.route_index = 0
        if self.route:
            first_road = city.roads[self.route[0]]
            self._enter_road(first_road)
            
    def _enter_road(self, road: Road):
        self.current_road = road
        self.distance_on_current_road = 0.0
        self.current_road.add_vehicle(self.id)
        
    def tick(self, dt_seconds: float, city: CityGrid):
        if self.finished or not self.current_road:
            return
            
        self.total_travel_time += dt_seconds
            
        # Car-following logic (simplified)
        # Determine target speed based on road limit and congestion
        congestion = self.current_road.get_congestion_factor()
        speed_limit_ms = self.current_road.speed_limit_kmh / 3.6
        
        # Heavy congestion = slow crawl
        target_speed_ms = speed_limit_ms / congestion
        
        # Determine acceleration
        if self.speed_ms < target_speed_ms:
            self.accel_ms2 = 2.0 # Moderate acceleration
        elif self.speed_ms > target_speed_ms:
            self.accel_ms2 = -3.0 # Braking
        else:
            self.accel_ms2 = 0.0
            
        # Update speed
        self.speed_ms += self.accel_ms2 * dt_seconds
        self.speed_ms = max(0.0, self.speed_ms)
        
        # Calculate emissions for this tick
        emissions = self.physics.calculate_tick_emissions(self.speed_ms, self.accel_ms2, dt_seconds)
        self.total_co2_kg += emissions["co2_kg"]
        
        # Move forward
        distance_moved = self.speed_ms * dt_seconds
        self.distance_on_current_road += distance_moved
        
        # Check if we reached the end of the road
        if self.distance_on_current_road >= self.current_road.length_meters:
            self.current_road.remove_vehicle(self.id)
            self.route_index += 1
            
            if self.route_index < len(self.route):
                next_road_id = self.route[self.route_index]
                next_road = city.roads[next_road_id]
                self._enter_road(next_road)
            else:
                self.finished = True
                self.current_road = None
                self.speed_ms = 0.0
