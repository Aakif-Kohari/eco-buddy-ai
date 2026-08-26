"""
City Economics & Carbon Pricing Engine.
Simulates congestion pricing, carbon taxes on businesses and fuel,
and tolls to mathematically nudge agents toward public transit or EVs.
"""

from typing import Dict, List
import logging
from plugins.smart_city.population_demographics import Citizen
from plugins.smart_city.road_network import CityGrid
from plugins.smart_city.engine import SmartCitySimulation

logger = logging.getLogger(__name__)

class TollBooth:
    def __init__(self, road_id: str, base_fee_usd: float):
        self.road_id = road_id
        self.base_fee_usd = base_fee_usd
        self.active = True
        
    def calculate_fee(self, is_ev: bool, is_heavy_freight: bool, congestion_factor: float) -> float:
        if not self.active: return 0.0
        
        # Surge pricing based on congestion
        fee = self.base_fee_usd * congestion_factor
        
        # EV discount, Freight premium
        if is_ev:
            fee *= 0.5
        if is_heavy_freight:
            fee *= 3.0
            
        return fee

class CarbonTaxPolicy:
    def __init__(self, tax_per_ton_usd: float = 50.0):
        self.tax_per_ton_usd = tax_per_ton_usd
        self.revenue_usd = 0.0
        
    def apply_tax(self, co2_kg: float) -> float:
        tons = co2_kg / 1000.0
        tax = tons * self.tax_per_ton_usd
        self.revenue_usd += tax
        return tax

class CityEconomics:
    def __init__(self, city_grid: CityGrid):
        self.grid = city_grid
        self.tolls: Dict[str, TollBooth] = {}
        self.carbon_tax = CarbonTaxPolicy(100.0) # Aggressive $100/ton tax
        self.total_tolls_collected = 0.0
        self.citizen_wallets: Dict[str, float] = {}
        
    def register_citizen(self, citizen: Citizen, starting_balance: float = 1000.0):
        self.citizen_wallets[citizen.id] = starting_balance
        
    def add_toll(self, road_id: str, base_fee: float):
        self.tolls[road_id] = TollBooth(road_id, base_fee)
        
    def process_vehicle_crossing(self, road_id: str, citizen_id: str, is_ev: bool, is_heavy: bool, congestion: float):
        if road_id in self.tolls:
            fee = self.tolls[road_id].calculate_fee(is_ev, is_heavy, congestion)
            self.total_tolls_collected += fee
            
            if citizen_id in self.citizen_wallets:
                self.citizen_wallets[citizen_id] -= fee
                
    def apply_fuel_tax(self, citizen_id: str, liters_purchased: float, gas_price_usd: float = 1.0, tax_rate: float = 0.5):
        cost = liters_purchased * (gas_price_usd + tax_rate)
        if citizen_id in self.citizen_wallets:
            self.citizen_wallets[citizen_id] -= cost
            
    def get_city_revenue(self) -> float:
        return self.total_tolls_collected + self.carbon_tax.revenue_usd
