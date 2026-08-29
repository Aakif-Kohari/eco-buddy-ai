"""UI KPI cards and badges for Soil Carbon and Agroecology Planner.
"""

from typing import Any
from src.carbon.soil_carbon_types import AgroecologySimulationResult


def render_soil_carbon_kpis(st: Any, result: AgroecologySimulationResult) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="10-Yr Total Net Carbon Sequestered",
            value=f"{result.net_10yr_carbon_sequestered_tons_co2e:,.1f} t CO₂e",
            delta=f"{result.annual_sequestration_rate_tons_co2e_per_ha:+.2f} t/ha/yr",
            delta_color="normal",
        )

    with col2:
        st.metric(
            label="Carbon Credit Revenue (10-Yr)",
            value=f"${result.total_carbon_credit_revenue_10yr_usd:,.2f}",
            delta=f"Area: {result.area_hectares:.0f} ha",
            delta_color="normal",
        )

    with col3:
        st.metric(
            label="Synthetic N Fertilizer Offset",
            value=f"{result.synthetic_n_fertilizer_offset_kg_yr:,.0f} kg N/yr",
            delta="Biological N Fixation",
            delta_color="normal",
        )

    with col4:
        st.metric(
            label="Water Retention Uplift",
            value=f"+{result.soil_water_holding_capacity_uplift_pct:.1f}%",
            delta=f"SOC: {result.initial_soc_stock_tons_c_ha:.1f} → {result.final_soc_stock_tons_c_ha_yr10:.1f} t C/ha",
            delta_color="normal",
        )
