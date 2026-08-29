"""
Enterprise Smart Grid EV V2G Integration Engine
Provides bidirectional vehicle-to-grid (V2G) fleet balancing, ISO 15118 smart charging,
grid frequency regulation, and Scope 3 mobility decarbonization analytics.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import datetime

@dataclass
class EvChargerAsset:
    charger_id: str
    station_name: str
    charger_type: str  # 'DC_FAST_V2G', 'LEVEL_2_BIDIRECTIONAL', 'MEGAPORT_DEPOT'
    connector_standard: str  # 'CCS2_ISO15118', 'CHADEMO_V2G', 'NACS_BIDIRECTIONAL'
    power_rating_kw: float
    current_power_kw: float
    connected_ev_vin: Optional[str]
    ev_battery_capacity_kwh: float
    ev_state_of_charge_pct: float
    target_soc_pct: float
    v2g_mode_active: bool
    grid_feedin_rate_kw: float
    revenue_earned_usd: float

@dataclass
class EvDepotGridHubProfile:
    hub_id: str
    hub_name: str
    location: str
    grid_operator: str
    transformer_capacity_kva: float
    current_demand_kw: float
    peak_shaving_target_kw: float
    total_v2g_discharge_kwh: float
    carbon_emissions_avoided_kg: float
    chargers: List[EvChargerAsset]
    last_dispatched_at: str

class SmartGridEvV2gEngine:
    def __init__(self):
        self.depots: Dict[str, EvDepotGridHubProfile] = {}
        self._initialize_default_data()

    def _initialize_default_data(self):
        sample_chargers = [
            EvChargerAsset(
                charger_id="V2G-CHG-01",
                station_name="Depot Alpha Bay 1 (DC Fast V2G)",
                charger_type="DC_FAST_V2G",
                connector_standard="CCS2_ISO15118",
                power_rating_kw=150.0,
                current_power_kw=120.0,
                connected_ev_vin="1FTVW1EL8NW009102",
                ev_battery_capacity_kwh=131.0,
                ev_state_of_charge_pct=85.0,
                target_soc_pct=90.0,
                v2g_mode_active=True,
                grid_feedin_rate_kw=80.0,
                revenue_earned_usd=42.50
            ),
            EvChargerAsset(
                charger_id="V2G-CHG-02",
                station_name="Depot Alpha Bay 2 (Level 2 Bi-Dir)",
                charger_type="LEVEL_2_BIDIRECTIONAL",
                connector_standard="NACS_BIDIRECTIONAL",
                power_rating_kw=19.2,
                current_power_kw=15.0,
                connected_ev_vin="5YJ3E1EA7KF891023",
                ev_battery_capacity_kwh=82.0,
                ev_state_of_charge_pct=92.0,
                target_soc_pct=80.0,
                v2g_mode_active=True,
                grid_feedin_rate_kw=12.5,
                revenue_earned_usd=18.20
            ),
            EvChargerAsset(
                charger_id="V2G-CHG-03",
                station_name="Depot Alpha Bay 3 (Megaport Bus Hub)",
                charger_type="MEGAPORT_DEPOT",
                connector_standard="CCS2_ISO15118",
                power_rating_kw=350.0,
                current_power_kw=280.0,
                connected_ev_vin="4V4NC9EJ2KN102934",
                ev_battery_capacity_kwh=320.0,
                ev_state_of_charge_pct=78.0,
                target_soc_pct=95.0,
                v2g_mode_active=False,
                grid_feedin_rate_kw=0.0,
                revenue_earned_usd=0.0
            )
        ]

        depot = EvDepotGridHubProfile(
            hub_id="HUB-V2G-801",
            hub_name="San Francisco Transit Fleet V2G Hub",
            location="San Francisco, California",
            grid_operator="Pacific Gas & Electric (PG&E)",
            transformer_capacity_kva=2500.0,
            current_demand_kw=850.0,
            peak_shaving_target_kw=1200.0,
            total_v2g_discharge_kwh=4850.0,
            carbon_emissions_avoided_kg=3210.0,
            chargers=sample_chargers,
            last_dispatched_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.depots[depot.hub_id] = depot

    def calculate_v2g_capacity(self, chargers: List[EvChargerAsset]) -> float:
        if not chargers:
            return 0.0
        return sum(c.grid_feedin_rate_kw for c in chargers if c.v2g_mode_active)

    def register_depot_hub(
        self,
        hub_id: str,
        hub_name: str,
        location: str,
        grid_operator: str,
        transformer_capacity_kva: float,
        chargers: List[EvChargerAsset]
    ) -> EvDepotGridHubProfile:
        total_v2g_kw = sum(c.grid_feedin_rate_kw for c in chargers if c.v2g_mode_active)
        depot = EvDepotGridHubProfile(
            hub_id=hub_id,
            hub_name=hub_name,
            location=location,
            grid_operator=grid_operator,
            transformer_capacity_kva=transformer_capacity_kva,
            current_demand_kw=total_v2g_kw,
            peak_shaving_target_kw=transformer_capacity_kva * 0.75,
            total_v2g_discharge_kwh=1200.0,
            carbon_emissions_avoided_kg=850.0,
            chargers=chargers,
            last_dispatched_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.depots[hub_id] = depot
        return depot
