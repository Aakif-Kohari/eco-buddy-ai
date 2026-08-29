import pytest
from plugins.smart_city.economics import CityEconomics, TollBooth, CarbonTaxPolicy
from plugins.smart_city.autonomous_fleet import FleetManager, RoboTaxi, RideRequest
from plugins.smart_city.population_demographics import Citizen
from plugins.smart_city.road_network import CityGrid
from plugins.smart_city.pathfinding import AStarPathfinder

def test_city_economics():
    city = CityGrid()
    econ = CityEconomics(city)
    
    citizen = Citizen("C1", "Node1", "Node2", "MIDDLE")
    econ.register_citizen(citizen, 100.0)
    
    econ.add_toll("Road_1", 5.0)
    
    # Process crossing
    econ.process_vehicle_crossing("Road_1", "C1", is_ev=False, is_heavy=False, congestion=1.0)
    assert econ.citizen_wallets["C1"] == 95.0
    assert econ.total_tolls_collected == 5.0
    
    # Process EV crossing (discounted)
    econ.process_vehicle_crossing("Road_1", "C1", is_ev=True, is_heavy=False, congestion=1.0)
    assert econ.citizen_wallets["C1"] == 92.5
    
    # Carbon Tax
    tax = econ.carbon_tax.apply_tax(2000.0) # 2 tons
    assert tax == 200.0 # $100/ton
    assert econ.get_city_revenue() == 207.5

def test_autonomous_fleet():
    city = CityGrid()
    n1 = city.add_intersection(0,0,"A")
    n2 = city.add_intersection(100,0,"B")
    city.add_road(n1.id, n2.id)
    
    pf = AStarPathfinder(city)
    
    fleet = FleetManager(num_taxis=1, nodes=[n1.id])
    taxi = fleet.taxis[0]
    
    assert taxi.state == "IDLE"
    
    fleet.request_ride("Pass1", n1.id, n2.id)
    assert len(fleet.pending_requests) == 1
    
    fleet.tick(1.0, city, pf)
    assert taxi.state == "ON_TRIP" or taxi.state == "DISPATCHED"
    
    for _ in range(10):
        fleet.tick(1.0, city, pf)
        
    assert taxi.battery_kwh < 100.0
