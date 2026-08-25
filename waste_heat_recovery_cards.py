"""UI KPI cards and badges for Industrial Waste Heat Recovery Planner.
"""

from typing import Any
from waste_heat_recovery_types import WasteHeatRecoveryResult


def render_waste_heat_kpi_cards(st: Any, result: WasteHeatRecoveryResult) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Gross Power / Useful Energy",
            value=f"{result.gross_electrical_power_kw:,.1f} kW",
            delta=f"Heat Source: {result.recoverable_thermal_heat_kw:,.0f} kW_th",
            delta_color="normal",
        )

    with col2:
        st.metric(
            label="Annual Utility Savings",
            value=f"${result.annual_cost_savings_usd:,.2f}",
            delta=f"Payback: {result.simple_payback_years:.1f} yrs",
            delta_color="normal" if result.simple_payback_years <= 6.0 else "inverse",
        )

    with col3:
        st.metric(
            label="Annual Scope 1/2 CO₂ Abated",
            value=f"{result.annual_co2_avoided_tons:,.1f} Tons CO₂",
            delta=f"Gen: {result.annual_electricity_generated_mwh:,.0f} MWh/yr",
            delta_color="normal",
        )

    with col4:
        st.metric(
            label="Second Law Exergy Efficiency",
            value=f"{result.exergy_efficiency_pct:.1f}%",
            delta=f"Thermal Eff: {result.net_thermal_efficiency_pct:.1f}%",
            delta_color="normal",
        )
