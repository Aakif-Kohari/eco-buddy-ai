import pytest
from plugins.smart_city.road_network import CityGrid
from plugins.smart_city.building_emissions import CityZoning, Building, BuildingMaterial, HVACSystem
from plugins.smart_city.power_grid import CityPowerGrid
from plugins.smart_city.population_demographics import DemographicsEngine, Citizen

def test_building_thermodynamics():
    # Single building tests
    b = Building("B1", "Node1", "RESIDENTIAL", 200.0, 2)
    
    # 21 C inside, 21 C outside = no conductive heat flow
    # Assuming no solar, only internal gain (which is positive)
    # The HVAC should need to cool the building.
    energy_kwh = b.tick_thermodynamics(3600.0, outside_temp_c=21.0, solar_irradiance_w_m2=0.0)
    assert energy_kwh > 0
    assert b.current_power_kw > 0
    
    # Very cold outside: -10 C
    energy_cold = b.tick_thermodynamics(3600.0, outside_temp_c=-10.0, solar_irradiance_w_m2=0.0)
    assert energy_cold > energy_kwh # Should require more power to heat

def test_building_upgrades():
    b1 = Building("B1", "Node1", "RESIDENTIAL", 200.0, 2)
    b2 = Building("B2", "Node1", "RESIDENTIAL", 200.0, 2) # Identical baseline
    
    better_insulation = BuildingMaterial("Foam", 0.1, 100.0)
    b2.upgrade_insulation(better_insulation)
    
    # Cold weather test
    e1 = b1.tick_thermodynamics(3600.0, -10.0, 0.0)
    e2 = b2.tick_thermodynamics(3600.0, -10.0, 0.0)
    
    assert e2 < e1 # Better insulation = less energy
    
def test_city_zoning():
    city = CityGrid()
    city.add_intersection(0,0,"A")
    city.add_intersection(10,0,"B")
    
    zoning = CityZoning(city)
    zoning.generate_city_buildings(100)
    
    assert len(zoning.buildings) == 100
    total_kwh = zoning.tick_all_buildings(3600.0, 30.0, 500.0) # Hot sunny day
    assert total_kwh > 0

def test_power_grid_renewables():
    grid = CityPowerGrid()
    
    # At night, zero solar
    grid.update_renewables(0.0, 10.0)
    solar_plant = next(p for p in grid.plants if p.name == "City Solar Array")
    assert solar_plant.current_output_mw == 0.0
    
    # Full sun
    grid.update_renewables(1000.0, 10.0)
    assert solar_plant.current_output_mw == 50.0
    
    # Extreme wind (cut out)
    grid.update_renewables(500.0, 30.0) # 30 m/s is hurricane
    wind_plant = next(p for p in grid.plants if p.name == "Offshore Wind")
    assert wind_plant.current_output_mw == 0.0

def test_power_grid_balancing():
    grid = CityPowerGrid()
    grid.update_renewables(1000.0, 12.0) # 50 MW solar + 100 MW wind = 150 MW free
    
    # Demand 100 MW
    res = grid.balance_grid(100_000.0) # kW
    assert res["demand_mw"] == 100.0
    assert res["shortfall_mw"] == 0.0
    # Carbon should be 0 because 150 MW renewables > 100 MW demand
    assert res["carbon_intensity_kg_kwh"] == 0.0
    
    # Demand 300 MW (150 from renewables, need 150 from nuclear)
    res2 = grid.balance_grid(300_000.0)
    assert res2["mix"]["Nuclear Station"] > 0
    assert res2["mix"]["Legacy Coal"] == 0.0 # Shouldn't need coal yet
    assert res2["carbon_intensity_kg_kwh"] > 0.0
    
    # Demand 1200 MW (Blackout!)
    res3 = grid.balance_grid(1_200_000.0)
    assert res3["shortfall_mw"] > 0.0
    assert res3["mix"]["Legacy Coal"] == 400.0 # Maxed out

def test_demographics_engine():
    nodes = ["A", "B", "C"]
    engine = DemographicsEngine()
    engine.generate_population(1000, nodes)
    
    assert len(engine.citizens) == 1000
    assert 0.0 <= engine.get_ev_adoption_rate() <= 1.0
    assert 0.0 <= engine.get_transit_ridership_rate() <= 1.0
    
    # Check bounds of schedules
    c = engine.citizens[0]
    assert 25200 <= c.commute_departure_time <= 32400
    assert 57600 <= c.return_departure_time <= 64800
