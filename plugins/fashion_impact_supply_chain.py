"""
Global Supply Chain & Logistics Simulator for Textiles.
Models the transportation network of the fashion industry using Graph Theory.
Calculates the logistical carbon footprint by finding the shortest path 
(via Dijkstra's algorithm) across oceans, air, and rail networks.
"""

import math
import heapq
from typing import Dict, List, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SupplyChainNode:
    """Represents a geographic hub in the supply chain (e.g., Farm, Factory, Port)."""
    def __init__(self, node_id: str, country: str, node_type: str):
        self.id = node_id
        self.country = country
        self.node_type = node_type # e.g., 'EXTRACTION', 'SPINNING', 'DYEING', 'ASSEMBLY', 'RETAIL'
        self.edges: List['LogisticsRoute'] = []

class LogisticsRoute:
    """
    Represents a transportation route between two nodes.
    Includes distance and transport mode (which dictates emissions).
    """
    def __init__(self, target_node_id: str, distance_km: float, transport_mode: str):
        self.target_node_id = target_node_id
        self.distance_km = distance_km
        self.transport_mode = transport_mode
        
        # Emissions factors (kg CO2e per tonne-km)
        # Source: GHG Protocol / GLEC Framework averages
        self.emission_factors = {
            'OCEAN_FREIGHT': 0.015, # Slow steaming container ship (highly efficient)
            'AIR_FREIGHT': 1.250,   # Cargo plane (highly polluting)
            'RAIL': 0.022,          # Electric/Diesel rail
            'ROAD_TRUCK': 0.120     # Heavy Duty Diesel Truck
        }
        
    def get_emission_cost(self) -> float:
        """Returns the CO2 cost to move 1 tonne of cargo across this edge."""
        factor = self.emission_factors.get(self.transport_mode, 0.1)
        return self.distance_km * factor

class GlobalSupplyChainGraph:
    """
    Graph Data Structure managing the global logistics network.
    Implements a custom Dijkstra's algorithm to compute the carbon-optimal 
    or distance-optimal supply chain paths.
    """
    def __init__(self):
        self.nodes: Dict[str, SupplyChainNode] = {}
        self._build_default_network()
        
    def add_node(self, node_id: str, country: str, node_type: str):
        self.nodes[node_id] = SupplyChainNode(node_id, country, node_type)
        
    def add_edge(self, source_id: str, target_id: str, distance_km: float, transport_mode: str):
        if source_id in self.nodes and target_id in self.nodes:
            self.nodes[source_id].edges.append(LogisticsRoute(target_id, distance_km, transport_mode))
            # Treat as directed graph. To make undirected, add reverse edge.
        else:
            logger.error(f"Cannot add edge: Nodes {source_id} or {target_id} missing.")

    def _build_default_network(self):
        """Pre-populates a realistic global textile supply chain network."""
        # 1. Extraction / Farming Nodes
        self.add_node("FARM_INDIA", "India", "EXTRACTION") # Cotton
        self.add_node("PETRO_CHINA", "China", "EXTRACTION") # Polyester
        self.add_node("WOOL_AUS", "Australia", "EXTRACTION") # Wool
        
        # 2. Spinning / Processing Nodes
        self.add_node("SPIN_BANGLADESH", "Bangladesh", "SPINNING")
        self.add_node("SPIN_CHINA", "China", "SPINNING")
        self.add_node("SPIN_ITALY", "Italy", "SPINNING")
        
        # 3. Assembly / Garment Factories
        self.add_node("ASSEMBLE_VIETNAM", "Vietnam", "ASSEMBLY")
        self.add_node("ASSEMBLE_BANGLADESH", "Bangladesh", "ASSEMBLY")
        self.add_node("ASSEMBLE_MEXICO", "Mexico", "ASSEMBLY")
        
        # 4. Retail / Destination Nodes
        self.add_node("RETAIL_USA", "USA", "RETAIL")
        self.add_node("RETAIL_EU", "Germany", "RETAIL")
        
        # --- Create Edges (Logistics Routes) ---
        
        # India Cotton -> Bangladesh Spinning (Truck)
        self.add_edge("FARM_INDIA", "SPIN_BANGLADESH", 1200.0, "ROAD_TRUCK")
        # India Cotton -> China Spinning (Ocean)
        self.add_edge("FARM_INDIA", "SPIN_CHINA", 4500.0, "OCEAN_FREIGHT")
        
        # Australia Wool -> Italy Spinning (Ocean)
        self.add_edge("WOOL_AUS", "SPIN_ITALY", 15000.0, "OCEAN_FREIGHT")
        # Australia Wool -> China Spinning (Ocean)
        self.add_edge("WOOL_AUS", "SPIN_CHINA", 7500.0, "OCEAN_FREIGHT")
        
        # China Petro -> China Spinning (Rail)
        self.add_edge("PETRO_CHINA", "SPIN_CHINA", 1000.0, "RAIL")
        
        # Spinning -> Assembly
        self.add_edge("SPIN_BANGLADESH", "ASSEMBLE_BANGLADESH", 50.0, "ROAD_TRUCK")
        self.add_edge("SPIN_CHINA", "ASSEMBLE_VIETNAM", 2000.0, "RAIL")
        self.add_edge("SPIN_ITALY", "ASSEMBLE_MEXICO", 9500.0, "OCEAN_FREIGHT")
        
        # Fast Fashion Nightmare: Air Freight from Bangladesh to Assembly in Mexico
        self.add_edge("SPIN_BANGLADESH", "ASSEMBLE_MEXICO", 14000.0, "AIR_FREIGHT")
        
        # Assembly -> Retail
        self.add_edge("ASSEMBLE_VIETNAM", "RETAIL_USA", 13000.0, "OCEAN_FREIGHT")
        
        # We need a dummy retail node to represent the fast air link
        self.add_node("RETAIL_USA_FAST", "USA", "RETAIL")
        self.add_edge("ASSEMBLE_VIETNAM", "RETAIL_USA_FAST", 13000.0, "AIR_FREIGHT") # Same dest, diff mode
        
        self.add_edge("ASSEMBLE_BANGLADESH", "RETAIL_EU", 8000.0, "OCEAN_FREIGHT")
        self.add_edge("ASSEMBLE_MEXICO", "RETAIL_USA", 2500.0, "ROAD_TRUCK")

    def find_lowest_carbon_path(self, start_node_id: str, end_node_id: str) -> Dict[str, Any]:
        """
        Executes Dijkstra's Algorithm to find the supply chain route with the lowest
        total carbon emissions (CO2 cost).
        
        Returns:
            Dict detailing the path, total km, and total kg CO2e per tonne of cargo.
        """
        if start_node_id not in self.nodes or end_node_id not in self.nodes:
            raise ValueError("Start or End node not found in graph.")
            
        # Priority Queue: (cumulative_co2_cost, node_id, path_history, cumulative_km)
        pq = [(0.0, start_node_id, [start_node_id], 0.0)]
        
        # Track minimum cost to reach each node to avoid loops/suboptimal paths
        min_cost_map = {node_id: float('inf') for node_id in self.nodes}
        min_cost_map[start_node_id] = 0.0
        
        best_path = None
        best_cost = float('inf')
        best_km = 0.0
        
        while pq:
            current_cost, current_node_id, path, current_km = heapq.heappop(pq)
            
            # If we reached the destination, check if it's the absolute best
            if current_node_id == end_node_id or current_node_id.startswith(end_node_id):
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_path = path
                    best_km = current_km
                continue
                
            # Stop exploring if we already found a cheaper route to this node
            if current_cost > min_cost_map[current_node_id]:
                continue
                
            node = self.nodes[current_node_id]
            for edge in node.edges:
                edge_co2_cost = edge.get_emission_cost()
                new_cost = current_cost + edge_co2_cost
                
                if new_cost < min_cost_map[edge.target_node_id]:
                    min_cost_map[edge.target_node_id] = new_cost
                    new_path = list(path)
                    new_path.append(edge.target_node_id)
                    heapq.heappush(pq, (new_cost, edge.target_node_id, new_path, current_km + edge.distance_km))
                    
        if not best_path:
            return {"error": "No valid logistics route found."}
            
        return {
            "start_node": start_node_id,
            "end_node": end_node_id,
            "optimal_path": best_path,
            "total_distance_km": round(best_km, 2),
            "logistics_carbon_kg_per_tonne": round(best_cost, 2)
        }
        
    def calculate_garment_transport_footprint(self, path_result: Dict[str, Any], garment_weight_kg: float) -> float:
        """Converts the per-tonne route cost to the specific garment's impact."""
        if "error" in path_result:
            return 0.0
            
        # Cost is kg CO2e per 1 Tonne (1000 kg).
        # We need to scale it down to the garment's weight
        weight_tonnes = garment_weight_kg / 1000.0
        return path_result["logistics_carbon_kg_per_tonne"] * weight_tonnes
