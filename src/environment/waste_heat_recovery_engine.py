"""Thermodynamics and Economic Optimization Engine for Waste Heat Recovery (WHR).

Implements:
- First Law sensible heat recovery (Q = m * Cp * deltaT)
- Second Law Exergy / Carnot maximum efficiency limit (eta_carnot = 1 - T_sink/T_source)
- Organic Rankine Cycle (ORC) working fluid expander isentropic efficiency
- Heat Exchanger minimum pinch point delta T constraint
- Scope 1 & 2 fossil fuel and grid displacement carbon math
"""

from typing import List, Dict
from src.environment.waste_heat_recovery_types import (
    IndustrialPlantParameters,
    WorkingFluid,
    RecoveryApplication,
    HeatPinchPoint,
    WasteHeatRecoveryResult,
)


class WasteHeatRecoveryEngine:
    # Specific heat capacity of flue gases (~1.08 kJ/kg.K)
    CP_FLUE_GAS = 1.08

    FLUID_ORC_EFFICIENCY = {
        WorkingFluid.R245FA: 0.16,
        WorkingFluid.CYCLOPENTANE: 0.22,
        WorkingFluid.SOLKATHERM_SES36: 0.18,
        WorkingFluid.WATER_STEAM: 0.24,
    }

    TURNKEY_CAPEX_PER_KW_ELEC = {
        RecoveryApplication.ORC_ELECTRICITY: 2400.0,
        RecoveryApplication.DISTRICT_HEATING: 650.0,
        RecoveryApplication.ABSORPTION_CHILLING: 1200.0,
        RecoveryApplication.STEAM_INJECTION: 950.0,
    }

    @classmethod
    def calculate_recovery(cls, params: IndustrialPlantParameters) -> WasteHeatRecoveryResult:
        # Minimum exhaust discharge temperature to avoid acid condensation (acid dew point ~ 130°C)
        min_stack_temp_c = 135.0
        delta_t_flue = max(0.0, params.exhaust_gas_temp_c - min_stack_temp_c)

        # Thermal heat recovered (kW_th)
        recoverable_thermal_kw = params.exhaust_mass_flow_kg_s * cls.CP_FLUE_GAS * delta_t_flue

        # Carnot limit (Kelvin)
        t_source_k = params.exhaust_gas_temp_c + 273.15
        t_sink_k = params.ambient_sink_temp_c + 273.15
        carnot_limit = 1.0 - (t_sink_k / max(t_sink_k + 1.0, t_source_k))

        if params.application == RecoveryApplication.ORC_ELECTRICITY:
            fluid_eff = cls.FLUID_ORC_EFFICIENCY.get(params.working_fluid, 0.18)
            gross_elec_kw = recoverable_thermal_kw * fluid_eff
            net_thermal_eff = fluid_eff * 100.0
        elif params.application == RecoveryApplication.DISTRICT_HEATING:
            gross_elec_kw = 0.0
            net_thermal_eff = 85.0
        elif params.application == RecoveryApplication.ABSORPTION_CHILLING:
            gross_elec_kw = recoverable_thermal_kw * 0.72  # COP equivalent cooling
            net_thermal_eff = 72.0
        else:  # HRSG Steam
            gross_elec_kw = recoverable_thermal_kw * 0.20
            net_thermal_eff = 20.0

        annual_elec_mwh = (gross_elec_kw * params.annual_operating_hours) / 1000.0
        annual_savings_usd = (gross_elec_kw * params.annual_operating_hours) * params.electricity_export_tariff_usd_kwh

        # In direct heating mode, savings comes from avoided natural gas ($0.04/kWh_th)
        if params.application == RecoveryApplication.DISTRICT_HEATING:
            annual_savings_usd = (recoverable_thermal_kw * 0.85 * params.annual_operating_hours) * 0.045

        annual_co2_tons = ((gross_elec_kw * params.annual_operating_hours) * params.grid_emission_intensity_kg_co2_kwh) / 1000.0
        if params.application == RecoveryApplication.DISTRICT_HEATING:
            # Avoided boiler gas (0.202 kg CO2 / kWh_th)
            annual_co2_tons = (recoverable_thermal_kw * 0.85 * params.annual_operating_hours * 0.202) / 1000.0

        # Exergy efficiency
        exergy_eff_pct = (net_thermal_eff / max(1.0, carnot_limit * 100.0)) * 100.0

        # Capex calculation
        capex_rate = cls.TURNKEY_CAPEX_PER_KW_ELEC.get(params.application, 2000.0)
        reference_kw = gross_elec_kw if params.application == RecoveryApplication.ORC_ELECTRICITY else recoverable_thermal_kw
        total_capex = max(10000.0, reference_kw * capex_rate)
        simple_payback = total_capex / max(1.0, annual_savings_usd)

        # Pinch Stream Data
        pinch_points = [
            HeatPinchPoint(
                stream_name="Industrial Flue Gas (Hot Stream)",
                inlet_temp_c=params.exhaust_gas_temp_c,
                outlet_temp_c=min_stack_temp_c,
                heat_transferred_kw=round(recoverable_thermal_kw, 1),
            ),
            HeatPinchPoint(
                stream_name=f"WHR Working Fluid ({params.working_fluid.value.split(' ')[0]})",
                inlet_temp_c=params.ambient_sink_temp_c + params.pinch_point_delta_t_c,
                outlet_temp_c=params.exhaust_gas_temp_c - params.pinch_point_delta_t_c,
                heat_transferred_kw=round(recoverable_thermal_kw * 0.95, 1),
            ),
        ]

        # 10-Yr Cashflow
        cashflows: List[Dict[str, float]] = []
        cum_cash = -total_capex
        for yr in range(1, 11):
            cum_cash += annual_savings_usd * (1.0 - 0.02 * yr)  # 2% annual O&M
            cashflows.append({"year": yr, "cumulative_usd": round(cum_cash, 2)})

        return WasteHeatRecoveryResult(
            plant_name=params.plant_name,
            recoverable_thermal_heat_kw=round(recoverable_thermal_kw, 1),
            gross_electrical_power_kw=round(gross_elec_kw, 1),
            net_thermal_efficiency_pct=round(net_thermal_eff, 1),
            annual_electricity_generated_mwh=round(annual_elec_mwh, 1),
            annual_cost_savings_usd=round(annual_savings_usd, 2),
            annual_co2_avoided_tons=round(annual_co2_tons, 1),
            exergy_efficiency_pct=round(min(95.0, exergy_eff_pct), 1),
            estimated_turnkey_capex_usd=round(total_capex, 2),
            simple_payback_years=round(simple_payback, 2),
            pinch_points=pinch_points,
            cashflow_10yr=cashflows,
        )
