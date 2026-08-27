import pytest
from plugins.smart_city.freight_logistics import HeavyDutyTruckPhysics, DeliveryVanPhysics, FreightAgent
from plugins.smart_city.air_quality_dispersion import AirQualityGrid
from plugins.smart_city.road_network import CityGrid
from plugins.smart_city.pathfinding import AStarPathfinder

def test_heavy_truck_emissions():
    truck = HeavyDutyTruckPhysics()
    
    # Idle
    idle_res = truck.calculate_tick_emissions(0.0, 0.0, 1.0)
    assert idle_res["co2_kg"] > 0
    assert idle_res["nox_g"] > 0
    
    # Accel
    accel_res = truck.calculate_tick_emissions(15.0, 1.0, 1.0)
    assert accel_res["co2_kg"] > idle_res["co2_kg"]
    
def test_van_emissions():
    ev_van = DeliveryVanPhysics(is_ev=True)
    gas_van = DeliveryVanPhysics(is_ev=False)
    
    ev_res = ev_van.calculate_tick_emissions(15.0, 1.0, 1.0)
    gas_res = gas_van.calculate_tick_emissions(15.0, 1.0, 1.0)
    
    assert gas_res["nox_g"] > ev_res["nox_g"] # EV has 0 tailpipe NOx
    assert ev_res["pm25_g"] > 0 # EV still emits tire PM25

def test_freight_agent():
    city = CityGrid()
    n1 = city.add_intersection(0,0,"A")
    n2 = city.add_intersection(100,0,"B")
    city.add_road(n1.id, n2.id)
    
    pf = AStarPathfinder(city)
    agent = FreightAgent(n1.id, [n2.id], "HEAVY_TRUCK")
    
    agent.update_route(pf)
    assert len(agent.route) > 0
    
    agent.tick(1.0, city, pf)
    assert agent.speed_ms > 0
    assert agent.total_co2_kg > 0

def test_air_quality_dispersion():
    grid = AirQualityGrid(1000.0, 1000.0, cell_size_m=50.0)
    assert grid.cols == 20
    assert grid.rows == 20
    
    grid.add_emissions(500.0, 500.0, pm25_g=10.0, nox_g=50.0)
    
    pm, nox = grid.get_aqi_at(500.0, 500.0)
    assert pm > 0
    assert nox > 0
    
    # Tick to diffuse and blow with wind
    grid.wind_speed_m_s = 50.0 # Force a shift
    grid.tick_dispersion(dt_seconds=1.0)
    
    # It should decay slightly
    pm_new, _ = grid.get_aqi_at(500.0, 500.0)
    assert pm_new < pm
