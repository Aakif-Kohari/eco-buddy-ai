import pytest
from vehicle_emissions_data import VehicleEmissionsData
from route_planning_engine import RoutePlanningEngine
from logistics_optimization_service import LogisticsOptimizationService

class TestRouteOptimization:

    def test_graph_generation(self):
        graph = VehicleEmissionsData.generate_city_graph(num_nodes=5, seed=1)
        assert len(graph["nodes"]) == 5
        assert len(graph["edges"]) > 0
        assert "allowed_modes" in graph["edges"][0]

    def test_shortest_eco_path(self):
        # Create a hardcoded graph to test choice
        graph = {
            "nodes": ["A", "B", "C"],
            "edges": [
                {"source": "A", "target": "B", "distance_km": 10, "allowed_modes": ["ICE_VAN", "HEAVY_TRUCK"]},
                {"source": "A", "target": "C", "distance_km": 15, "allowed_modes": ["BICYCLE", "EV_VAN"]},
                {"source": "C", "target": "B", "distance_km": 5, "allowed_modes": ["E_BIKE"]},
            ]
        }
        
        # A->B direct = 10km * 0.25 (ICE_VAN) = 2.5 kg
        # A->C->B via BICYCLE/EV_VAN and E_BIKE:
        # A->C = 15km * 0.0 (BICYCLE) = 0
        # C->B = 5km * 0.005 (E_BIKE) = 0.025
        # Total A->C->B CO2 = 0.025, which is < 2.5!
        
        engine = RoutePlanningEngine(graph)
        result = engine.find_safest_eco_path("A", "B")
        
        assert result["status"] == "success"
        assert result["total_co2_kg"] == 0.025
        # Path should go A -> C, C -> B
        assert len(result["path"]) == 2
        assert result["path"][0]["mode"] == "BICYCLE"
        assert result["path"][1]["mode"] == "E_BIKE"

    def test_logistics_service(self):
        graph = VehicleEmissionsData.generate_city_graph(num_nodes=10, seed=4)
        engine = RoutePlanningEngine(graph)
        service = LogisticsOptimizationService(engine)
        
        service.add_delivery_job(graph["nodes"][0], graph["nodes"][1])
        service.add_delivery_job(graph["nodes"][1], graph["nodes"][2])
        
        res = service.optimize_fleet()
        assert res["jobs_processed"] == 2
        assert res["savings_percentage"] > 0
        assert res["total_co2_saved_kg"] > 0
