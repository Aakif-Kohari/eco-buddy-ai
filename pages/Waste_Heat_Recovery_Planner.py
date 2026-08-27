"""Streamlit Page for Industrial Waste Heat Recovery (WHR) & ORC Simulation.
"""

import streamlit as st
import pandas as pd
from src.environment.waste_heat_recovery_types import (
    IndustrialPlantParameters,
    HeatSourceIndustry,
    WorkingFluid,
    RecoveryApplication,
)
from src.environment.waste_heat_recovery_engine import WasteHeatRecoveryEngine
from src.environment.waste_heat_recovery_cards import render_waste_heat_kpi_cards
from src.environment.waste_heat_recovery_charts import create_pinch_point_chart, create_cashflow_waterfall

st.set_page_config(
    page_title="Industrial Waste Heat Recovery Planner",
    page_icon="🏭",
    layout="wide",
)

st.title("🏭 Industrial Waste Heat Recovery & Exergy Optimization Engine")
st.markdown(
    """
    Model thermodynamic First & Second Law exergy efficiency, Organic Rankine Cycle (ORC) power generation,
    heat exchanger pinch-point constraints, and avoided Scope 1 & 2 carbon src.carbon.emissions.
    """
)

with st.sidebar:
    st.header("⚙️ Plant & Heat Source")
    plant_name = st.text_input("Facility Name", value="Vulcan Advanced Steelworks")
    industry = st.selectbox("Industry / Flue Gas Source", list(HeatSourceIndustry), index=1)
    exhaust_temp = st.number_input("Exhaust Gas Temperature (°C)", min_value=150.0, max_value=1000.0, value=480.0, step=10.0)
    mass_flow = st.number_input("Exhaust Gas Mass Flow (kg/s)", min_value=1.0, max_value=150.0, value=25.0, step=1.0)

    st.subheader("🔄 Recovery Thermodynamics")
    application = st.selectbox("Heat Recovery Technology", list(RecoveryApplication), index=0)
    fluid = st.selectbox("ORC / Thermodynamic Working Fluid", list(WorkingFluid), index=1)
    pinch_dt = st.slider("Minimum Pinch Point ΔT (°C)", min_value=5.0, max_value=30.0, value=12.0, step=1.0)
    operating_hours = st.number_input("Annual Operating Hours (hrs/yr)", min_value=1000.0, max_value=8760.0, value=7500.0, step=250.0)

    st.subheader("💰 Energy Tariffs")
    tariff = st.number_input("Power Export Tariff ($/kWh)", min_value=0.04, max_value=0.60, value=0.12, step=0.01)

params = IndustrialPlantParameters(
    plant_name=plant_name,
    industry_type=industry,
    exhaust_gas_temp_c=exhaust_temp,
    exhaust_mass_flow_kg_s=mass_flow,
    working_fluid=fluid,
    application=application,
    annual_operating_hours=operating_hours,
    pinch_point_delta_t_c=pinch_dt,
    electricity_export_tariff_usd_kwh=tariff,
)

result = WasteHeatRecoveryEngine.calculate_recovery(params)

# KPIs
render_waste_heat_kpi_cards(st, result)

# Visualizations
tab_pinch, tab_cash, tab_table = st.tabs(["🔥 T-Q Pinch Curve", "📈 10-Yr Cashflow & NPV", "📋 Engineering Summary"])

with tab_pinch:
    st.plotly_chart(create_pinch_point_chart(result.pinch_points), use_container_width=True)

with tab_cash:
    st.plotly_chart(create_cashflow_waterfall(result.cashflow_10yr), use_container_width=True)

with tab_table:
    st.info(
        f"""
        **Thermodynamic & Financial Feasibility for {result.plant_name}**:
        - Recoverable Thermal Enthalpy: **{result.recoverable_thermal_heat_kw:,.1f} kW_th**
        - Gross Electrical Output: **{result.gross_electrical_power_kw:,.1f} kW_e**
        - Net Thermal Efficiency: **{result.net_thermal_efficiency_pct:.1f}%**
        - Second Law Exergy Efficiency: **{result.exergy_efficiency_pct:.1f}%**
        - Estimated Total Turnkey CapEx: **${result.estimated_turnkey_capex_usd:,.2f}**
        - Simple Payback Horizon: **{result.simple_payback_years:.1f} Years**
        """
    )
