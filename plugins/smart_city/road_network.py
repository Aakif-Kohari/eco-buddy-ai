"""
Smart City Road Network & Spatial Graph.
Defines intersections (Nodes) and roads (Edges) to create a navigable city grid.
"""

from typing import Dict, List, Optional, Tuple
import math
import logging
import uuid

logger = logging.getLogger(__name__)

class Intersection:
    """A node in the road network where vehicles can change directions."""
    def __init__(self, x: float, y: float, name: str = ""):
        self.id = str(uuid.uuid4())
        self.x = x
        self.y = y
        self.name = name or f"Node_{self.id[:6]}"
        self.connected_roads: List['Road'] = []
        
    def add_road(self, road: 'Road'):
        if road not in self.connected_roads:
            self.connected_roads.append(road)

    def get_distance_to(self, other: 'Intersection') -> float:
        """Euclidean distance in meters."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

class Road:
    """A directed edge connecting two intersections."""
    def __init__(self, source: Intersection, target: Intersection, lanes: int = 1, speed_limit_kmh: float = 50.0):
        self.id = str(uuid.uuid4())
        self.source = source
        self.target = target
        self.lanes = lanes
        self.speed_limit_kmh = speed_limit_kmh
        self.length_meters = source.get_distance_to(target)
        
        # Traffic tracking
        self.current_vehicles: List[str] = []
        self.base_capacity = self.length_meters / 6.0 * self.lanes # Assume 6m per car space
        
        # Link back to nodes
        self.source.add_road(self)
        self.target.add_road(self)
        
    def get_congestion_factor(self) -> float:
        """Returns a multiplier (>= 1.0) for travel time based on traffic density."""
        if self.base_capacity <= 0:
            return 1.0
        utilization = len(self.current_vehicles) / self.base_capacity
        
        # BPR (Bureau of Public Roads) congestion function
        # T = T0 * (1 + alpha * (V/C)^beta)
        alpha = 0.15
        beta = 4.0
        return 1.0 + alpha * (utilization ** beta)
        
    def get_travel_time_seconds(self) -> float:
        """Estimated time to traverse the road currently."""
        speed_limit_ms = self.speed_limit_kmh / 3.6
        free_flow_time = self.length_meters / speed_limit_ms
        return free_flow_time * self.get_congestion_factor()
        
    def add_vehicle(self, vehicle_id: str):
        if vehicle_id not in self.current_vehicles:
            self.current_vehicles.append(vehicle_id)
            
    def remove_vehicle(self, vehicle_id: str):
        if vehicle_id in self.current_vehicles:
            self.current_vehicles.remove(vehicle_id)

class CityGrid:
    """Manages the entire spatial topology of the city."""
    def __init__(self):
        self.intersections: Dict[str, Intersection] = {}
        self.roads: Dict[str, Road] = {}
        
    def add_intersection(self, x: float, y: float, name: str = "") -> Intersection:
        node = Intersection(x, y, name)
        self.intersections[node.id] = node
        return node
        
    def add_road(self, source_id: str, target_id: str, lanes: int = 1, speed_limit_kmh: float = 50.0) -> Optional[Road]:
        if source_id not in self.intersections or target_id not in self.intersections:
            logger.error("Cannot add road: Source or Target intersection missing.")
            return None
            
        src = self.intersections[source_id]
        tgt = self.intersections[target_id]
        
        road = Road(src, tgt, lanes, speed_limit_kmh)
        self.roads[road.id] = road
        return road
        
    def build_manhattan_grid(self, blocks_x: int, blocks_y: int, block_size_meters: float = 200.0):
        """Generates a standard grid-pattern city."""
        nodes = {}
        # Create Nodes
        for i in range(blocks_x):
            for j in range(blocks_y):
                x = i * block_size_meters
                y = j * block_size_meters
                node = self.add_intersection(x, y, name=f"St_{i}_Ave_{j}")
                nodes[(i, j)] = node
                
        # Create Edges (Bidirectional roads)
        for i in range(blocks_x):
            for j in range(blocks_y):
                curr = nodes[(i, j)]
                # Right
                if i < blocks_x - 1:
                    right = nodes[(i + 1, j)]
                    self.add_road(curr.id, right.id, 2, 40.0)
                    self.add_road(right.id, curr.id, 2, 40.0)
                # Up
                if j < blocks_y - 1:
                    up = nodes[(i, j + 1)]
                    self.add_road(curr.id, up.id, 2, 40.0)
                    self.add_road(up.id, curr.id, 2, 40.0)
