"""KPI cards and status badges for V2G Energy Orchestrator.
"""

from typing import Any
from src.utils.v2g_orchestrator_types import V2GOrchestrationResult


def render_v2g_kpi_cards(st: Any, result: V2GOrchestrationResult) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Net Annual Arbitrage Profit",
            value=f"${result.net_annual_arbitrage_profit_usd:,.2f}",
            delta=f"Gross Rev: ${result.annual_grid_revenue_usd:,.0f}",
            delta_color="normal",
        )

    with col2:
        st.metric(
            label="Grid Carbon Displaced",
            value=f"{result.annual_co2_avoided_tons:,.1f} Tons CO₂",
            delta=f"Fleet Cap: {result.total_fleet_capacity_kwh:,.0f} kWh",
            delta_color="normal",
        )

    with col3:
        st.metric(
            label="Battery Cycle Lifespan",
            value=f"{result.estimated_battery_cycle_life_years:.1f} Years",
            delta=f"-{result.annual_battery_degradation_pct:.2f}% Fade/yr",
            delta_color="inverse",
        )

    with col4:
        st.metric(
            label="Solar Self-Consumption",
            value=f"{result.solar_self_consumption_pct:.1f}%",
            delta=f"Fleet: {result.fleet_size} EVs",
            delta_color="normal",
        )
