"""
Smart City Building Physics & Emissions Simulator.
Models thermodynamics and HVAC energy consumption for thousands of 
commercial and residential buildings across the city grid.
"""

from typing import Dict, List, Optional
import math
import random
import logging
from plugins.smart_city.road_network import CityGrid

logger = logging.getLogger(__name__)

class BuildingMaterial:
    def __init__(self, name: str, u_value_w_m2k: float, embodied_carbon_kg_m2: float):
        self.name = name
        # U-value: Thermal transmittance (Watts per square meter-Kelvin). Lower is better insulation.
        self.u_value_w_m2k = u_value_w_m2k
        self.embodied_carbon_kg_m2 = embodied_carbon_kg_m2

class HVACSystem:
    def __init__(self, system_type: str, cop_heating: float, eer_cooling: float):
        self.system_type = system_type
        # Coefficient of Performance (Heating)
        self.cop_heating = cop_heating
        # Energy Efficiency Ratio (Cooling)
        self.eer_cooling = eer_cooling

class Building:
    """
    Physical and thermodynamic model of a city building.
    """
    def __init__(self, building_id: str, node_id: str, building_type: str, floor_area_m2: float, floors: int):
        self.id = building_id
        self.node_id = node_id # Which intersection it is nearest to
        self.building_type = building_type # RESIDENTIAL, COMMERCIAL, INDUSTRIAL
        self.floor_area_m2 = floor_area_m2
        self.floors = floors
        
        self.total_volume_m3 = self.floor_area_m2 * 3.0 * self.floors # Assume 3m per floor
        self.surface_area_m2 = (self.floor_area_m2 * 2) + (math.sqrt(self.floor_area_m2) * 4 * 3.0 * self.floors)
        
        self.internal_temp_c = 21.0
        self.target_temp_c = 21.0
        
        # Thermodynamics
        self.material = BuildingMaterial("Standard Brick", 2.0, 50.0)
        self.hvac = HVACSystem("Standard Heat Pump", 3.0, 3.0)
        self.heat_capacity_j_k = self.total_volume_m3 * 1.2 * 1005 # Air mass * specific heat
        
        self.current_power_kw = 0.0
        self.cumulative_energy_kwh = 0.0
        
    def upgrade_insulation(self, new_material: BuildingMaterial):
        """Retrofits the building to improve thermal efficiency."""
        self.material = new_material
        
    def upgrade_hvac(self, new_hvac: HVACSystem):
        """Upgrades the heating/cooling system."""
        self.hvac = new_hvac
        
    def tick_thermodynamics(self, dt_seconds: float, outside_temp_c: float, solar_irradiance_w_m2: float) -> float:
        """
        Calculates heat loss/gain and HVAC power required to maintain target temperature.
        Returns energy consumed in kWh for this tick.
        """
        # 1. Conductive Heat Transfer through walls (Q = U * A * dT)
        temp_diff = outside_temp_c - self.internal_temp_c
        conductive_heat_flow_w = self.material.u_value_w_m2k * self.surface_area_m2 * temp_diff
        
        # 2. Solar Heat Gain (simplified: windows are 15% of surface area, SHGC of 0.4)
        solar_gain_w = (self.surface_area_m2 * 0.15) * solar_irradiance_w_m2 * 0.4
        
        # 3. Internal Heat Gain (People, appliances, lighting)
        # Assume 10W per m2 for residential, 25W per m2 for commercial
        internal_load_w_m2 = 25.0 if self.building_type == "COMMERCIAL" else 10.0
        internal_gain_w = self.floor_area_m2 * self.floors * internal_load_w_m2
        
        # Total natural heat flux (Watts)
        net_natural_flux_w = conductive_heat_flow_w + solar_gain_w + internal_gain_w
        
        # Calculate HVAC intervention required
        # If natural flux pushes temp away from target, HVAC must oppose it
        hvac_cooling_needed_w = 0.0
        hvac_heating_needed_w = 0.0
        
        # Simplified thermostat logic: Maintain exactly target temp
        # If flux is positive, we need cooling. If negative, heating.
        if net_natural_flux_w > 0:
            hvac_cooling_needed_w = net_natural_flux_w
        else:
            hvac_heating_needed_w = abs(net_natural_flux_w)
            
        # Convert thermal demand to electrical power using COP/EER
        electrical_power_w = 0.0
        if hvac_cooling_needed_w > 0:
            electrical_power_w = hvac_cooling_needed_w / self.hvac.eer_cooling
        elif hvac_heating_needed_w > 0:
            electrical_power_w = hvac_heating_needed_w / self.hvac.cop_heating
            
        # Add baseline baseload (lights, servers, fridges)
        baseload_w = self.floor_area_m2 * self.floors * (15.0 if self.building_type == "COMMERCIAL" else 5.0)
        electrical_power_w += baseload_w
        
        self.current_power_kw = electrical_power_w / 1000.0
        
        # Energy consumed (kWh) = kW * hours
        energy_kwh = self.current_power_kw * (dt_seconds / 3600.0)
        self.cumulative_energy_kwh += energy_kwh
        
        return energy_kwh

class CityZoning:
    """Manages the generation and updating of all buildings in the city."""
    def __init__(self, grid: CityGrid):
        self.grid = grid
        self.buildings: List[Building] = []
        
    def generate_city_buildings(self, count: int = 1000):
        """Randomly zones and builds the city's infrastructure."""
        nodes = list(self.grid.intersections.keys())
        if not nodes:
            return
            
        for i in range(count):
            node_id = random.choice(nodes)
            
            # 70% Residential, 20% Commercial, 10% Industrial
            roll = random.random()
            if roll < 0.7:
                b_type = "RESIDENTIAL"
                area = random.uniform(100.0, 500.0)
                floors = random.randint(1, 4)
            elif roll < 0.9:
                b_type = "COMMERCIAL"
                area = random.uniform(500.0, 5000.0)
                floors = random.randint(3, 20)
            else:
                b_type = "INDUSTRIAL"
                area = random.uniform(2000.0, 10000.0)
                floors = 1
                
            building = Building(f"Bldg_{i}", node_id, b_type, area, floors)
            
            # Apply some random modern retrofits to ~20% of buildings
            if random.random() < 0.2:
                better_insulation = BuildingMaterial("Triple Glaze & Foam", 0.5, 80.0)
                better_hvac = HVACSystem("High-Eff Heat Pump", 4.5, 4.5)
                building.upgrade_insulation(better_insulation)
                building.upgrade_hvac(better_hvac)
                
            self.buildings.append(building)
            
        logger.info(f"Generated {count} buildings across the city.")
        
    def tick_all_buildings(self, dt_seconds: float, outside_temp_c: float, solar_w_m2: float) -> float:
        """
        Updates thermodynamics for all buildings.
        Returns total city-wide energy consumption for this tick (kWh).
        """
        total_kwh = 0.0
        for building in self.buildings:
            total_kwh += building.tick_thermodynamics(dt_seconds, outside_temp_c, solar_w_m2)
        return total_kwh
