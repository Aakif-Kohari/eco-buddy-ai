"""
City-Wide Telemetry & Aggregation.
Provides the data pipeline for the Streamlit dashboard.
"""

from typing import Dict, Any
from plugins.smart_city.engine import SmartCitySimulation

class CityTelemetry:
    def __init__(self, engine: SmartCitySimulation):
        self.engine = engine
        
    def get_snapshot(self) -> Dict[str, Any]:
        """Returns a real-time JSON snapshot of the entire city state."""
        
        # Calculate road congestion
        road_data = []
        for road_id, road in self.engine.city.roads.items():
            road_data.append({
                "id": road_id,
                "source": [road.source.x, road.source.y],
                "target": [road.target.x, road.target.y],
                "vehicles": len(road.current_vehicles),
                "congestion_factor": round(road.get_congestion_factor(), 2)
            })
            
        # Agent data
        agent_data = []
        for agent in self.engine.agents:
            if not agent.finished and agent.current_road:
                # Interpolate position
                road = agent.current_road
                ratio = agent.distance_on_current_road / road.length_meters
                x = road.source.x + (road.target.x - road.source.x) * ratio
                y = road.source.y + (road.target.y - road.source.y) * ratio
                
                agent_data.append({
                    "id": agent.id,
                    "x": x,
                    "y": y,
                    "is_ev": agent.is_ev,
                    "speed_kmh": agent.speed_ms * 3.6
                })
                
        return {
            "time_seconds": self.engine.sim_time_seconds,
            "metrics": self.engine.metrics,
            "roads": road_data,
            "agents": agent_data
        }
