"""Thermodynamic simulation engine for Industrial Symbiosis & Waste Heat Recovery.
"""

import math
from src.environment.industrial_symbiosis_types import (
    IndustrialStreamParameters,
    HeatRecoveryResult,
    HeatSourceStreamType,
    HeatRecoveryTechnology,
)


class IndustrialSymbiosisEngine:
    """Calculates enthalpy transfer, heat exchanger pinch dynamics, and avoided Scope 1 emissions."""

    # Specific heat capacities cp (kJ / kg * K)
    SPECIFIC_HEATS = {
        HeatSourceStreamType.FLUE_GAS_HIGH_TEMP: 1.08,
        HeatSourceStreamType.BOILER_BLOWDOWN: 4.22,
        HeatSourceStreamType.COMPRESSOR_COOLING_AIR: 1.005,
        HeatSourceStreamType.INDUSTRIAL_EFFLUENT: 4.18,
        HeatSourceStreamType.DATA_CENTER_EXHAUST: 1.006,
    }

    # Recovery technology thermal/electrical efficiencies
    TECH_EFFICIENCY = {
        HeatRecoveryTechnology.ORGANIC_RANKINE_CYCLE: 0.18,      # Thermal to Electricity
        HeatRecoveryTechnology.PLATE_HEAT_EXCHANGER: 0.88,      # Thermal to Thermal
        HeatRecoveryTechnology.ABSORPTION_CHILLER: 0.72,        # Thermal to Cooling (COP)
        HeatRecoveryTechnology.HEAT_PIPE_ECONOMIZER: 0.78,      # Thermal to Pre-heat
    }

    # Capital expenditure estimates ($ / kW recovered capacity)
    CAPEX_PER_KW = {
        HeatRecoveryTechnology.ORGANIC_RANKINE_CYCLE: 1800.0,
        HeatRecoveryTechnology.PLATE_HEAT_EXCHANGER: 220.0,
        HeatRecoveryTechnology.ABSORPTION_CHILLER: 650.0,
        HeatRecoveryTechnology.HEAT_PIPE_ECONOMIZER: 340.0,
    }

    @classmethod
    def calculate_heat_recovery(cls, params: IndustrialStreamParameters) -> HeatRecoveryResult:
        cp = cls.SPECIFIC_HEATS.get(params.stream_type, 1.05)
        tech_eff = cls.TECH_EFFICIENCY.get(params.recovery_tech, 0.80)
        capex_rate = cls.CAPEX_PER_KW.get(params.recovery_tech, 400.0)

        # Thermal power: Q_dot = m_dot * cp * delta_T (kW = kg/s * kJ/kg-K * K)
        delta_t = max(0.0, params.inlet_temperature_c - params.target_outlet_temperature_c)
        q_available_kw = params.mass_flow_rate_kg_s * cp * delta_t

        q_recovered_kw = q_available_kw * tech_eff

        # Annual energy recovery (MWh)
        annual_recovered_mwh = (q_recovered_kw * params.annual_operating_hours) / 1000.0

        # Avoided emissions (metric tons CO2e)
        # Avoided fuel energy = Recovered MWh * 1000 kWh * intensity
        avoided_co2_kg = annual_recovered_mwh * 1000.0 * params.avoided_fuel_carbon_intensity_kg_co2_kwh
        avoided_co2_metric_tons = avoided_co2_kg / 1000.0

        # Financial savings (assuming $0.065 / kWh equivalent thermal fuel value)
        annual_savings_usd = annual_recovered_mwh * 1000.0 * 0.065

        # Payback years
        total_capex = q_recovered_kw * capex_rate
        payback_years = total_capex / max(1.0, annual_savings_usd)

        return HeatRecoveryResult(
            facility_name=params.facility_name,
            thermal_power_available_kw=round(q_available_kw, 1),
            thermal_power_recovered_kw=round(q_recovered_kw, 1),
            annual_energy_recovered_mwh=round(annual_recovered_mwh, 1),
            annual_avoided_emissions_metric_tons=round(avoided_co2_metric_tons, 2),
            annual_cost_savings_usd=round(annual_savings_usd, 2),
            estimated_payback_years=round(payback_years, 2),
            system_thermal_efficiency_pct=round(tech_eff * 100.0, 1),
        )
