"""
Enterprise Industrial Carbon Capture, Utilization & Storage (CCUS) Engine
Provides real-time flue gas CO2 absorption telemetry, direct air capture (DAC) operational monitoring,
geological sequestration site tracking, and Scope 1 industrial carbon mitigation analytics.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import datetime

@dataclass
class CcusCaptureUnit:
    unit_id: str
    unit_name: str
    technology_type: str  # 'AMINE_SOLVENT_ABSORPTION', 'DIRECT_AIR_CAPTURE_DAC', 'CRYOGENIC_FRACTIONATION', 'MEMBRANE_SEPARATION'
    flue_gas_flow_rate_m3_hr: float
    co2_concentration_pct: float
    capture_efficiency_pct: float
    daily_co2_captured_metric_tons: float
    parasitic_energy_penalty_mwh_per_ton: float
    solvent_degradation_rate_ppm: float
    operating_status: str

@dataclass
class IndustrialPlantCcusProfile:
    facility_id: str
    facility_name: str
    industry_sector: str  # 'CEMENT_MANUFACTURING', 'STEEL_PRODUCTION', 'CHEMICAL_REFINERY', 'POWER_GENERATION'
    location: str
    annual_gross_emissions_tons: float
    annual_net_captured_tons: float
    sequestration_method: str  # 'DEEP_SALINE_AQUIFER', 'MINERAL_CARBONATION', 'ENHANCED_OIL_RECOVERY_EOR', 'E-FUEL_SYNTHESIS'
    net_carbon_tax_offset_usd: float
    units: List[CcusCaptureUnit]
    last_audited_at: str

class IndustrialCcusEngine:
    def __init__(self):
        self.facilities: Dict[str, IndustrialPlantCcusProfile] = {}
        self._initialize_default_data()

    def _initialize_default_data(self):
        sample_units = [
            CcusCaptureUnit(
                unit_id="CCUS-UNIT-01",
                unit_name="Amine Solvent Flue Gas Absorber Column A",
                technology_type="AMINE_SOLVENT_ABSORPTION",
                flue_gas_flow_rate_m3_hr=120000.0,
                co2_concentration_pct=14.5,
                capture_efficiency_pct=92.8,
                daily_co2_captured_metric_tons=480.0,
                parasitic_energy_penalty_mwh_per_ton=2.4,
                solvent_degradation_rate_ppm=0.8,
                operating_status="OPTIMAL_ABSORPTION"
            ),
            CcusCaptureUnit(
                unit_id="CCUS-UNIT-02",
                unit_name="Modular Direct Air Capture (DAC) Collector Array",
                technology_type="DIRECT_AIR_CAPTURE_DAC",
                flue_gas_flow_rate_m3_hr=450000.0,
                co2_concentration_pct=0.04,
                capture_efficiency_pct=88.0,
                daily_co2_captured_metric_tons=125.0,
                parasitic_energy_penalty_mwh_per_ton=1.8,
                solvent_degradation_rate_ppm=0.1,
                operating_status="THERMAL_DESORPTION"
            )
        ]

        plant = IndustrialPlantCcusProfile(
            facility_id="PLANT-CCUS-901",
            facility_name="Apex Green Cement & Materials Facility",
            industry_sector="CEMENT_MANUFACTURING",
            location="Houston, Texas",
            annual_gross_emissions_tons=450000.0,
            annual_net_captured_tons=380000.0,
            sequestration_method="DEEP_SALINE_AQUIFER",
            net_carbon_tax_offset_usd=32300000.0,
            units=sample_units,
            last_audited_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.facilities[plant.facility_id] = plant

    def calculate_total_capture(self, units: List[CcusCaptureUnit]) -> float:
        if not units:
            return 0.0
        return round(sum(u.daily_co2_captured_metric_tons for u in units), 2)

    def register_facility_profile(
        self,
        facility_id: str,
        facility_name: str,
        industry_sector: str,
        location: str,
        annual_emissions: float,
        units: List[CcusCaptureUnit]
    ) -> IndustrialPlantCcusProfile:
        daily_captured = sum(u.daily_co2_captured_metric_tons for u in units)
        annual_captured = daily_captured * 365.0
        tax_offset = annual_captured * 85.0  # 45Q tax credit equivalent ($85/ton)

        profile = IndustrialPlantCcusProfile(
            facility_id=facility_id,
            facility_name=facility_name,
            industry_sector=industry_sector,
            location=location,
            annual_gross_emissions_tons=annual_emissions,
            annual_net_captured_tons=round(annual_captured, 2),
            sequestration_method="MINERAL_CARBONATION",
            net_carbon_tax_offset_usd=round(tax_offset, 2),
            units=units,
            last_audited_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.facilities[facility_id] = profile
        return profile
