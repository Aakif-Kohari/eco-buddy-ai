"""
A* (A-Star) Pathfinding Engine.
Calculates optimal routes through the CityGrid considering live traffic congestion.
"""

import heapq
from typing import List, Dict, Optional, Tuple
from plugins.smart_city.road_network import CityGrid, Intersection, Road

class AStarPathfinder:
    def __init__(self, city: CityGrid):
        self.city = city
        
    def _heuristic(self, node_a: Intersection, node_b: Intersection, max_speed_kmh: float = 100.0) -> float:
        """
        Admissible heuristic: straight-line distance divided by max possible speed.
        Returns time in seconds.
        """
        dist_m = node_a.get_distance_to(node_b)
        max_speed_ms = max_speed_kmh / 3.6
        return dist_m / max_speed_ms
        
    def find_fastest_route(self, start_id: str, goal_id: str) -> Tuple[List[str], float]:
        """
        Finds the route that minimizes travel time (considering live congestion).
        Returns: (List of Road IDs, Estimated Travel Time in seconds)
        """
        if start_id not in self.city.intersections or goal_id not in self.city.intersections:
            return [], float('inf')
            
        start_node = self.city.intersections[start_id]
        goal_node = self.city.intersections[goal_id]
        
        # Priority Queue: (f_score, tie_breaker, current_node_id)
        # f_score = g_score (actual time from start) + h_score (estimated time to goal)
        open_set = []
        heapq.heappush(open_set, (0.0, 0, start_id))
        
        # Keep track of paths: came_from[node_id] = (previous_node_id, road_taken_id)
        came_from: Dict[str, Tuple[str, str]] = {}
        
        # Cost from start along best known path
        g_score = {node_id: float('inf') for node_id in self.city.intersections}
        g_score[start_id] = 0.0
        
        tie_breaker = 0
        
        while open_set:
            _, _, current_id = heapq.heappop(open_set)
            
            if current_id == goal_id:
                # Reconstruct path
                path_roads = []
                curr = current_id
                while curr in came_from:
                    prev, road_id = came_from[curr]
                    path_roads.append(road_id)
                    curr = prev
                path_roads.reverse()
                return path_roads, g_score[goal_id]
                
            current_node = self.city.intersections[current_id]
            
            for road in current_node.connected_roads:
                # We only want outgoing roads
                if road.source.id != current_id:
                    continue
                    
                neighbor = road.target
                tentative_g = g_score[current_id] + road.get_travel_time_seconds()
                
                if tentative_g < g_score[neighbor.id]:
                    came_from[neighbor.id] = (current_id, road.id)
                    g_score[neighbor.id] = tentative_g
                    
                    h = self._heuristic(neighbor, goal_node)
                    f_score = tentative_g + h
                    
                    tie_breaker += 1
                    heapq.heappush(open_set, (f_score, tie_breaker, neighbor.id))
                    
        # No path found
        return [], float('inf')
