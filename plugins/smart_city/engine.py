"""
Core Simulation Engine.
Manages the tick loop, agents, and overall city state.
"""

from typing import List, Dict
import random
import logging
from plugins.smart_city.road_network import CityGrid
from plugins.smart_city.pathfinding import AStarPathfinder
from plugins.smart_city.agents import CommuterAgent

logger = logging.getLogger(__name__)

class SmartCitySimulation:
    def __init__(self, blocks_x: int = 5, blocks_y: int = 5):
        self.city = CityGrid()
        self.city.build_manhattan_grid(blocks_x, blocks_y)
        self.pathfinder = AStarPathfinder(self.city)
        self.agents: List[CommuterAgent] = []
        self.sim_time_seconds = 0.0
        
        self.metrics = {
            "total_co2_kg": 0.0,
            "active_vehicles": 0,
            "finished_vehicles": 0
        }

    def spawn_random_traffic(self, count: int, ev_adoption_rate: float = 0.2):
        """Spawns vehicles with random start and end points in the city."""
        nodes = list(self.city.intersections.keys())
        if len(nodes) < 2:
            return
            
        for _ in range(count):
            start = random.choice(nodes)
            goal = random.choice(nodes)
            while goal == start:
                goal = random.choice(nodes)
                
            is_ev = random.random() < ev_adoption_rate
            agent = CommuterAgent(start, goal, is_ev)
            
            # Find initial route
            route, _ = self.pathfinder.find_fastest_route(start, goal)
            if route:
                agent.assign_route(route, self.city)
                self.agents.append(agent)
                
        logger.info(f"Spawned {count} agents. EV Rate: {ev_adoption_rate*100}%")

    def tick(self, dt_seconds: float = 1.0):
        """Advances the simulation by dt_seconds."""
        self.sim_time_seconds += dt_seconds
        
        active_count = 0
        tick_co2 = 0.0
        
        # We periodically reroute agents to avoid sudden traffic jams
        # (simulate Waze/Google Maps real-time routing)
        should_reroute = (int(self.sim_time_seconds) % 60 == 0)
        
        for agent in self.agents:
            if agent.finished:
                continue
                
            active_count += 1
            
            if should_reroute and agent.current_road:
                # Find route from end of current road to goal
                new_route, _ = self.pathfinder.find_fastest_route(agent.current_road.target.id, agent.goal_node_id)
                if new_route:
                    # Update remaining route
                    agent.route = [agent.current_road.id] + new_route
                    agent.route_index = 0
            
            prev_co2 = agent.total_co2_kg
            agent.tick(dt_seconds, self.city)
            tick_co2 += (agent.total_co2_kg - prev_co2)
            
        self.metrics["total_co2_kg"] += tick_co2
        self.metrics["active_vehicles"] = active_count
        self.metrics["finished_vehicles"] = len(self.agents) - active_count
