"""
Intelligent Traffic Light Controllers.
Models dynamic signal timings to optimize traffic flow and reduce idling emissions.
"""

from typing import Dict, List
import logging
from plugins.smart_city.road_network import Intersection, Road

logger = logging.getLogger(__name__)

class TrafficLight:
    """Controls flow at a specific intersection."""
    def __init__(self, intersection: Intersection):
        self.intersection = intersection
        
        # Determine incoming roads
        self.incoming_roads: List[Road] = []
        for road in self.intersection.connected_roads:
            if road.target.id == self.intersection.id:
                self.incoming_roads.append(road)
                
        self.cycle_time_seconds = 60.0
        self.current_time_in_cycle = 0.0
        
        # State: which road ID has the green light
        self.active_green_road_id = None
        
        if self.incoming_roads:
            self.active_green_road_id = self.incoming_roads[0].id
            
    def get_green_time_allocation(self) -> Dict[str, float]:
        """Dynamic phase allocation based on queue lengths."""
        allocation = {}
        total_vehicles = 0
        
        for road in self.incoming_roads:
            total_vehicles += len(road.current_vehicles)
            
        if total_vehicles == 0:
            # Even split
            split = self.cycle_time_seconds / max(1, len(self.incoming_roads))
            for road in self.incoming_roads:
                allocation[road.id] = split
            return allocation
            
        # Proportional split based on traffic volume
        min_green = 10.0
        remaining_time = self.cycle_time_seconds - (min_green * len(self.incoming_roads))
        
        for road in self.incoming_roads:
            ratio = len(road.current_vehicles) / total_vehicles
            allocation[road.id] = min_green + (remaining_time * ratio)
            
        return allocation

    def tick(self, dt_seconds: float):
        if not self.incoming_roads:
            return
            
        self.current_time_in_cycle += dt_seconds
        if self.current_time_in_cycle >= self.cycle_time_seconds:
            self.current_time_in_cycle = 0.0
            
        allocation = self.get_green_time_allocation()
        
        # Determine which road should be green based on current time in cycle
        cumulative_time = 0.0
        for road_id, duration in allocation.items():
            cumulative_time += duration
            if self.current_time_in_cycle <= cumulative_time:
                self.active_green_road_id = road_id
                return
                
    def is_green(self, road_id: str) -> bool:
        return self.active_green_road_id == road_id
