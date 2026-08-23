"""
Enterprise Landfill Methane Emissions Telemetry & Energy Recovery Engine
Provides real-time CH4 fugitive emissions modeling, gas wellhead vacuum optimization,
RNG (Renewable Natural Gas) pipeline grid injection telemetry, and EPA Subpart HH compliance tracking.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import datetime

@dataclass
class GasWellheadSensor:
    well_id: str
    well_name: str
    methane_concentration_pct: float
    carbon_dioxide_pct: float
    oxygen_pct: float
    flow_rate_cfm: float
    vacuum_pressure_inches_wcat: float
    temperature_celsius: float
    well_status: str  # 'OPTIMAL_EXTRACTION', 'AIR_INTRUSION_RISK', 'LOW_CH4_WARNING', 'OFFLINE'

@dataclass
class LandfillGasRecoveryFacility:
    facility_id: str
    facility_name: str
    location: str
    total_landfill_area_acres: float
    waste_in_place_metric_tons: float
    ch4_fugitive_emissions_kg_hr: float
    rng_production_mcf_day: float
    flared_ch4_volume_cfm: float
    carbon_credits_generated_usd: float
    wellheads: List[GasWellheadSensor]
    last_calibrated_at: str

class LandfillMethaneEngine:
    def __init__(self):
        self.facilities: Dict[str, LandfillGasRecoveryFacility] = {}
        self._initialize_default_data()

    def _initialize_default_data(self):
        sample_wells = [
            GasWellheadSensor(
                well_id="WELL-CH4-01",
                well_name="Sector A North Wellhead 14",
                methane_concentration_pct=56.4,
                carbon_dioxide_pct=41.2,
                oxygen_pct=0.4,
                flow_rate_cfm=145.0,
                vacuum_pressure_inches_wcat=-12.5,
                temperature_celsius=38.2,
                well_status="OPTIMAL_EXTRACTION"
            ),
            GasWellheadSensor(
                well_id="WELL-CH4-02",
                well_name="Sector B West Wellhead 09",
                methane_concentration_pct=52.1,
                carbon_dioxide_pct=43.8,
                oxygen_pct=1.8,
                flow_rate_cfm=98.0,
                vacuum_pressure_inches_wcat=-8.2,
                temperature_celsius=41.0,
                well_status="AIR_INTRUSION_RISK"
            ),
            GasWellheadSensor(
                well_id="WELL-CH4-03",
                well_name="Sector C South Deep Extraction Well 22",
                methane_concentration_pct=58.9,
                carbon_dioxide_pct=39.5,
                oxygen_pct=0.2,
                flow_rate_cfm=210.0,
                vacuum_pressure_inches_wcat=-16.0,
                temperature_celsius=36.5,
                well_status="OPTIMAL_EXTRACTION"
            )
        ]

        facility = LandfillGasRecoveryFacility(
            facility_id="LF-CH4-401",
            facility_name="Apex EcoLandfill Renewable Natural Gas Plant",
            location="Phoenix, Arizona",
            total_landfill_area_acres=420.0,
            waste_in_place_metric_tons=12500000.0,
            ch4_fugitive_emissions_kg_hr=85.4,
            rng_production_mcf_day=3200.0,
            flared_ch4_volume_cfm=450.0,
            carbon_credits_generated_usd=18500.00,
            wellheads=sample_wells,
            last_calibrated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.facilities[facility.facility_id] = facility

    def calculate_total_ch4_flow_cfm(self, wellheads: List[GasWellheadSensor]) -> float:
        if not wellheads:
            return 0.0
        return round(sum(w.flow_rate_cfm * (w.methane_concentration_pct / 100.0) for w in wellheads), 2)

    def calculate_rng_energy_equivalent_mmbtu(self, rng_mcf_day: float) -> float:
        # 1 MCF of pipeline quality RNG is ~1.028 MMBtu
        return round(rng_mcf_day * 1.028, 2)

    def register_landfill_facility(
        self,
        facility_id: str,
        facility_name: str,
        location: str,
        area_acres: float,
        waste_tons: float,
        wellheads: List[GasWellheadSensor]
    ) -> LandfillGasRecoveryFacility:
        ch4_flow = sum(w.flow_rate_cfm * (w.methane_concentration_pct / 100.0) for w in wellheads)
        rng_est = ch4_flow * 1.44  # Daily MCF estimation factor
        credits = rng_est * 15.0  # $15/MCF RNG RINs & carbon offsets

        profile = LandfillGasRecoveryFacility(
            facility_id=facility_id,
            facility_name=facility_name,
            location=location,
            total_landfill_area_acres=area_acres,
            waste_in_place_metric_tons=waste_tons,
            ch4_fugitive_emissions_kg_hr=round(area_acres * 0.25, 2),
            rng_production_mcf_day=round(rng_est, 2),
            flared_ch4_volume_cfm=200.0,
            carbon_credits_generated_usd=round(credits, 2),
            wellheads=wellheads,
            last_calibrated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.facilities[facility_id] = profile
        return profile
