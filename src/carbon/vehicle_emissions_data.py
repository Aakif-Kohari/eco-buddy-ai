import random

class VehicleEmissionsData:
    """
    Simulates a database of vehicle models and transport modes,
    each with distinct carbon intensity factors (kg CO2e per km)
    and operational efficiencies.
    """
    
    MODES = {
        "BICYCLE": {"co2_per_km": 0.0, "speed_kmh": 15, "cost_per_km": 0.05},
        "E_BIKE": {"co2_per_km": 0.005, "speed_kmh": 25, "cost_per_km": 0.10},
        "EV_VAN": {"co2_per_km": 0.04, "speed_kmh": 40, "cost_per_km": 0.25},
        "ICE_VAN": {"co2_per_km": 0.25, "speed_kmh": 45, "cost_per_km": 0.35},
        "HEAVY_TRUCK": {"co2_per_km": 0.85, "speed_kmh": 35, "cost_per_km": 0.90},
        "RAIL": {"co2_per_km": 0.02, "speed_kmh": 60, "cost_per_km": 0.15},
    }
    
    @staticmethod
    def get_factor(mode: str) -> float:
        return VehicleEmissionsData.MODES.get(mode, {}).get("co2_per_km", 0.5)

    @staticmethod
    def get_speed(mode: str) -> float:
        return VehicleEmissionsData.MODES.get(mode, {}).get("speed_kmh", 30)

    @staticmethod
    def get_cost(mode: str) -> float:
        return VehicleEmissionsData.MODES.get(mode, {}).get("cost_per_km", 0.5)

    @staticmethod
    def generate_city_graph(num_nodes: int = 10, seed: int = 42):
        """
        Generates a mock graph of city nodes with varied distances and allowed modes.
        """
        random.seed(seed)
        nodes = [f"Node_{i}" for i in range(num_nodes)]
        edges = []
        
        # Ensure it's somewhat connected
        for i in range(num_nodes):
            for j in range(i+1, num_nodes):
                if random.random() > 0.6: # 40% chance of direct path
                    distance = random.uniform(2.0, 50.0)
                    # Exclude heavy trucks for very short inner city paths
                    modes = list(VehicleEmissionsData.MODES.keys())
                    if distance < 5:
                        modes.remove("HEAVY_TRUCK")
                        modes.remove("RAIL")
                    
                    allowed_modes = random.sample(modes, k=random.randint(1, len(modes)))
                    edges.append({
                        "source": nodes[i],
                        "target": nodes[j],
                        "distance_km": round(distance, 2),
                        "allowed_modes": allowed_modes
                    })
        return {"nodes": nodes, "edges": edges}
