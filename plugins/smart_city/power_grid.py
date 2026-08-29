"""
City Power Grid & Energy Mix Simulator.
Balances the real-time electrical load (from EV chargers and Buildings) 
against generation sources (Solar, Wind, Coal, Gas) to calculate the dynamic Carbon Intensity.
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class PowerPlant:
    def __init__(self, name: str, plant_type: str, max_capacity_mw: float, carbon_intensity_kg_kwh: float):
        self.name = name
        self.plant_type = plant_type # RENEWABLE, FOSSIL, NUCLEAR
        self.max_capacity_mw = max_capacity_mw
        self.carbon_intensity_kg_kwh = carbon_intensity_kg_kwh
        
        self.current_output_mw = 0.0
        self.dispatch_priority = 0 # Lower is dispatched first

class CityPowerGrid:
    """
    Manages the dispatch of power plants to meet the city's instantaneous electrical load.
    Renewables are dispatched first (Priority 0), then Nuclear (Priority 1), then Fossil (Priority 2+).
    """
    def __init__(self):
        self.plants: List[PowerPlant] = []
        self.current_load_mw = 0.0
        self.current_carbon_intensity = 0.0
        self._setup_default_grid()
        
    def _setup_default_grid(self):
        # Base Load / Renewables (Dispatch Priority 0)
        solar = PowerPlant("City Solar Array", "RENEWABLE", 50.0, 0.0)
        solar.dispatch_priority = 0
        
        wind = PowerPlant("Offshore Wind", "RENEWABLE", 100.0, 0.0)
        wind.dispatch_priority = 0
        
        nuclear = PowerPlant("Nuclear Station", "NUCLEAR", 200.0, 0.01)
        nuclear.dispatch_priority = 1
        
        # Peaker Plants (Fossil, dispatched last)
        gas_cc = PowerPlant("Combined Cycle Gas", "FOSSIL", 300.0, 0.45)
        gas_cc.dispatch_priority = 2
        
        coal = PowerPlant("Legacy Coal", "FOSSIL", 400.0, 1.05)
        coal.dispatch_priority = 3
        
        self.plants.extend([solar, wind, nuclear, gas_cc, coal])
        self.plants.sort(key=lambda p: p.dispatch_priority)
        
    def update_renewables(self, solar_irradiance_w_m2: float, wind_speed_m_s: float):
        """Modulates maximum renewable capacity based on weather."""
        for plant in self.plants:
            if plant.name == "City Solar Array":
                # Max output at 1000 W/m2
                plant.current_output_mw = plant.max_capacity_mw * min(1.0, solar_irradiance_w_m2 / 1000.0)
            elif plant.name == "Offshore Wind":
                # Max output at 12 m/s
                if wind_speed_m_s < 3.0 or wind_speed_m_s > 25.0:
                    plant.current_output_mw = 0.0 # Cut in / Cut out
                else:
                    plant.current_output_mw = plant.max_capacity_mw * min(1.0, (wind_speed_m_s - 3.0) / 9.0)
                    
    def balance_grid(self, total_demand_kw: float) -> Dict[str, Any]:
        """
        Dispatches power plants to meet the demand.
        Returns the instantaneous carbon intensity of the grid.
        """
        self.current_load_mw = total_demand_kw / 1000.0
        remaining_demand_mw = self.current_load_mw
        
        total_carbon_kg_h = 0.0
        
        # We assume renewables (Priority 0) are already outputting whatever weather allows
        for plant in self.plants:
            if plant.dispatch_priority == 0:
                # Must-take generation
                output = plant.current_output_mw
                remaining_demand_mw = max(0.0, remaining_demand_mw - output)
                
            else:
                # Dispatchable generation
                if remaining_demand_mw > 0:
                    dispatch_amount = min(plant.max_capacity_mw, remaining_demand_mw)
                    plant.current_output_mw = dispatch_amount
                    remaining_demand_mw -= dispatch_amount
                else:
                    plant.current_output_mw = 0.0
                    
            # Calculate carbon contribution
            # Output MW * 1000 = kW (which is kWh over an hour).
            # Carbon is kg CO2 per kWh.
            kwh_in_an_hour = plant.current_output_mw * 1000.0
            total_carbon_kg_h += kwh_in_an_hour * plant.carbon_intensity_kg_kwh
            
        if self.current_load_mw > 0:
            # Average carbon intensity for the whole grid mix
            self.current_carbon_intensity = total_carbon_kg_h / (self.current_load_mw * 1000.0)
        else:
            self.current_carbon_intensity = 0.0
            
        if remaining_demand_mw > 0.1:
            logger.warning(f"BLACKOUT WARNING: Demand exceeded generation by {remaining_demand_mw:.2f} MW")
            
        return {
            "demand_mw": round(self.current_load_mw, 2),
            "carbon_intensity_kg_kwh": round(self.current_carbon_intensity, 4),
            "shortfall_mw": round(remaining_demand_mw, 2),
            "mix": {p.name: round(p.current_output_mw, 2) for p in self.plants}
        }
