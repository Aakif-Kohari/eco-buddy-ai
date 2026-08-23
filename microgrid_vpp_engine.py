"""
Enterprise Microgrid & Virtual Power Plant (VPP) Dispatch Engine
Manages distributed energy resource (DER) telemetry, battery storage (BESS) dispatching,
peak shaving algorithms, and grid carbon intensity arbitrage.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import datetime

@dataclass
class DistributedEnergyResource:
    asset_id: str
    asset_name: str
    asset_type: str  # 'SOLAR_PV', 'BESS', 'WIND_TURBINE', 'EV_BIDIRECTIONAL'
    capacity_kw: float
    current_output_kw: float
    state_of_charge_pct: float
    operating_status: str
    carbon_offset_kg_per_hr: float

@dataclass
class MicrogridDispatchProfile:
    microgrid_id: str
    facility_name: str
    location: str
    grid_connection_status: str
    total_capacity_kw: float
    current_load_kw: float
    renewable_fraction_pct: float
    peak_shaving_savings_usd: float
    assets: List[DistributedEnergyResource]
    last_dispatched_at: str

class MicrogridVppEngine:
    def __init__(self):
        self.facilities: Dict[str, MicrogridDispatchProfile] = {}
        self._initialize_default_data()

    def _initialize_default_data(self):
        sample_assets = [
            DistributedEnergyResource(
                asset_id="DER-BESS-01",
                asset_name="Tesla Megapack 2XL Battery Bank",
                asset_type="BESS",
                capacity_kw=2500.0,
                current_output_kw=1200.0,
                state_of_charge_pct=88.5,
                operating_status="DISPATCHING",
                carbon_offset_kg_per_hr=450.0
            ),
            DistributedEnergyResource(
                asset_id="DER-SOLAR-02",
                asset_name="Rooftop Bifacial Solar PV Array",
                asset_type="SOLAR_PV",
                capacity_kw=1800.0,
                current_output_kw=1650.0,
                state_of_charge_pct=100.0,
                operating_status="MAX_GENERATION",
                carbon_offset_kg_per_hr=620.0
            ),
            DistributedEnergyResource(
                asset_id="DER-V2G-03",
                asset_name="Fleet EV Bidirectional Charging Hub",
                asset_type="EV_BIDIRECTIONAL",
                capacity_kw=800.0,
                current_output_kw=350.0,
                state_of_charge_pct=72.0,
                operating_status="GRID_STABILIZING",
                carbon_offset_kg_per_hr=130.0
            )
        ]

        facility = MicrogridDispatchProfile(
            microgrid_id="GRID-VPP-701",
            facility_name="Apex Enterprise Sustainability Campus",
            location="Austin, Texas",
            grid_connection_status="ISLANDED_OPTIMIZED",
            total_capacity_kw=5100.0,
            current_load_kw=2800.0,
            renewable_fraction_pct=94.2,
            peak_shaving_savings_usd=14250.00,
            assets=sample_assets,
            last_dispatched_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.facilities[facility.microgrid_id] = facility

    def calculate_vpp_efficiency(self, assets: List[DistributedEnergyResource]) -> float:
        if not assets:
            return 0.0
        total_capacity = sum(a.capacity_kw for a in assets)
        if total_capacity <= 0:
            return 0.0
        active_output = sum(a.current_output_kw for a in assets)
        return round((active_output / total_capacity) * 100.0, 2)

    def register_facility_profile(
        self,
        microgrid_id: str,
        facility_name: str,
        location: str,
        current_load_kw: float,
        assets: List[DistributedEnergyResource]
    ) -> MicrogridDispatchProfile:
        total_capacity = sum(a.capacity_kw for a in assets)
        renewable_gen = sum(a.current_output_kw for a in assets if a.asset_type in ['SOLAR_PV', 'WIND_TURBINE', 'BESS'])
        ren_fraction = (renewable_gen / current_load_kw) * 100.0 if current_load_kw > 0 else 100.0

        profile = MicrogridDispatchProfile(
            microgrid_id=microgrid_id,
            facility_name=facility_name,
            location=location,
            grid_connection_status="GRID_TIED_OPTIMIZED",
            total_capacity_kw=round(total_capacity, 2),
            current_load_kw=round(current_load_kw, 2),
            renewable_fraction_pct=min(100.0, round(ren_fraction, 2)),
            peak_shaving_savings_usd=8500.0,
            assets=assets,
            last_dispatched_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.facilities[microgrid_id] = profile
        return profile

    def get_all_facilities() -> List[MicrogridDispatchProfile]:
        return list(self.facilities.values())
