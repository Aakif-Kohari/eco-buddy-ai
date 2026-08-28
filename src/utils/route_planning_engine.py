from src.carbon.vehicle_emissions_data import VehicleEmissionsData
from typing import Dict, List, Any
import math
import heapq

class RoutePlanningEngine:
    """
    Calculates the most sustainable optimal path across a logistical network.
    Instead of optimizing strictly for Time or Distance, it optimizes for minimal 
    Carbon footprint by evaluating mode combinations.
    """
    
    def __init__(self, graph_data: Dict[str, Any]):
        self.nodes = graph_data["nodes"]
        self.edges = graph_data["edges"]
        self.adj_list = self._build_adj_list()
        
    def _build_adj_list(self) -> Dict[str, List]:
        adj = {node: [] for node in self.nodes}
        for edge in self.edges:
            u, v = edge["source"], edge["target"]
            adj[u].append((v, edge["distance_km"], edge["allowed_modes"]))
            adj[v].append((u, edge["distance_km"], edge["allowed_modes"])) # Undirected
        return adj

    def find_safest_eco_path(self, start: str, end: str) -> Dict[str, Any]:
        """
        Uses Dijkstra's algorithm prioritizing lowest CO2e src.carbon.emissions.
        """
        if start not in self.adj_list or end not in self.adj_list:
            return {"status": "error", "message": "Invalid nodes"}

        # Priority Queue: (cumulative_co2, current_node, cumulative_dist, path)
        pq = [(0, start, 0, [])]
        visited = set()
        
        while pq:
            cum_co2, curr, cum_dist, path = heapq.heappop(pq)
            
            if curr == end:
                return {
                    "status": "success",
                    "path": path,
                    "total_co2_kg": round(cum_co2, 3),
                    "total_dist_km": round(cum_dist, 2)
                }
                
            if curr in visited:
                continue
                
            visited.add(curr)
            
            for neighbor, distance, modes in self.adj_list[curr]:
                if neighbor not in visited:
                    # Find the most eco-friendly mode for this segment
                    best_mode = None
                    lowest_segment_co2 = float('inf')
                    
                    for mode in modes:
                        segment_co2 = distance * VehicleEmissionsData.get_factor(mode)
                        if segment_co2 < lowest_segment_co2:
                            lowest_segment_co2 = segment_co2
                            best_mode = mode
                            
                    new_path = path.copy()
                    new_path.append({
                        "from": curr,
                        "to": neighbor,
                        "distance_km": distance,
                        "mode": best_mode,
                        "co2_kg": round(lowest_segment_co2, 4)
                    })
                    
                    heapq.heappush(pq, (cum_co2 + lowest_segment_co2, neighbor, cum_dist + distance, new_path))
                    
        return {"status": "error", "message": "No path found"}
