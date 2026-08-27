import pytest
from plugins.smart_city.road_network import CityGrid, Intersection, Road
from plugins.smart_city.pathfinding import AStarPathfinder
from plugins.smart_city.emissions_physics import ICEVehicle, EVVehicle
from plugins.smart_city.engine import SmartCitySimulation
from plugins.smart_city.traffic_lights import TrafficLight
from plugins.smart_city.public_transit import CityBus, TransitRoute

def test_road_network_creation():
    city = CityGrid()
    n1 = city.add_intersection(0.0, 0.0, "A")
    n2 = city.add_intersection(100.0, 0.0, "B")
    
    assert n1.id in city.intersections
    assert n1.get_distance_to(n2) == 100.0
    
    r = city.add_road(n1.id, n2.id, lanes=2, speed_limit_kmh=50.0)
    assert r is not None
    assert r.length_meters == 100.0
    assert r.base_capacity > 0
    
def test_congestion_factor():
    city = CityGrid()
    n1 = city.add_intersection(0, 0)
    n2 = city.add_intersection(100, 0)
    road = city.add_road(n1.id, n2.id, lanes=1)
    
    assert road.get_congestion_factor() == 1.0 # Empty
    
    # Fill road to capacity
    for i in range(int(road.base_capacity)):
        road.add_vehicle(f"v_{i}")
        
    assert road.get_congestion_factor() > 1.0
    assert road.get_travel_time_seconds() > (road.length_meters / (50/3.6))

def test_astar_pathfinding():
    city = CityGrid()
    city.build_manhattan_grid(3, 3) # 9 nodes
    
    pf = AStarPathfinder(city)
    
    # Path from (0,0) to (2,2)
    start_id = list(city.intersections.values())[0].id
    # We know nodes are ordered, but let's just find the exact keys
    # Actually nodes dict inside build is local. Let's find by coords.
    start = None
    end = None
    for n in city.intersections.values():
        if n.x == 0 and n.y == 0: start = n
        if n.x == 400 and n.y == 400: end = n
        
    path, time = pf.find_fastest_route(start.id, end.id)
    assert len(path) > 0
    assert time > 0
    
def test_ice_emissions():
    ice = ICEVehicle()
    
    # Idling
    res_idle = ice.calculate_tick_emissions(0.0, 0.0, 1.0)
    assert res_idle["co2_kg"] > 0
    assert res_idle["nox_g"] > 0
    
    # Accel
    res_accel = ice.calculate_tick_emissions(10.0, 2.0, 1.0)
    assert res_accel["co2_kg"] > res_idle["co2_kg"]

def test_ev_emissions():
    ev = EVVehicle()
    
    # Accel
    res_accel = ev.calculate_tick_emissions(10.0, 2.0, 1.0)
    assert res_accel["co2_kg"] > 0
    
    # Regen braking
    res_brake = ev.calculate_tick_emissions(10.0, -2.0, 1.0)
    assert res_brake["co2_kg"] == 0.0 # Energy goes back to battery

def test_engine_tick():
    engine = SmartCitySimulation(blocks_x=2, blocks_y=2)
    engine.spawn_random_traffic(10, ev_adoption_rate=0.5)
    
    assert len(engine.agents) == 10
    
    # Tick simulation
    for _ in range(5):
        engine.tick(1.0)
        
    assert engine.sim_time_seconds == 5.0
    assert engine.metrics["total_co2_kg"] > 0

def test_traffic_lights():
    city = CityGrid()
    n1 = city.add_intersection(0,0)
    n2 = city.add_intersection(100,0)
    r1 = city.add_road(n2.id, n1.id)
    
    light = TrafficLight(n1)
    
    assert light.cycle_time_seconds == 60.0
    
    light.tick(30.0)
    assert light.current_time_in_cycle == 30.0
    
def test_city_bus():
    city = CityGrid()
    city.build_manhattan_grid(2,2)
    nodes = list(city.intersections.keys())
    
    route = TransitRoute("Line 1", [nodes[0], nodes[3]])
    bus = CityBus(route, city)
    
    assert bus.capacity == 60
    bus.board_passengers(20)
    assert bus.current_passengers == 20
    
    bus.alight_passengers(0.5)
    assert bus.current_passengers == 10
