"""Streamlit Page for Smart EV Charging & Vehicle-to-Grid (V2G) Orchestration.
"""

import streamlit as st
import pandas as pd
from src.utils.v2g_orchestrator_types import (
    FleetVehicleConfig,
    BatteryChemistry,
    ChargingTariffScheme,
    GridServiceMode,
)
from src.utils.v2g_orchestrator_engine import V2GOrchestratorEngine
from src.reporting.v2g_orchestrator_cards import render_v2g_kpi_cards
from src.reporting.v2g_orchestrator_charts import create_v2g_dispatch_chart, create_fleet_soc_curve

st.set_page_config(
    page_title="V2G Energy Orchestrator",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Smart EV Charging & Vehicle-to-Grid (V2G) Orchestrator")
st.markdown(
    """
    Model bi-directional fleet power exchange, dynamic TOU revenue arbitrage,
    solar co-location self-consumption, and battery cycle degradation management.
    """
)

with st.sidebar:
    st.header("⚡ Fleet Configuration")
    fleet_size = st.slider("EV Fleet Size", min_value=1, max_value=250, value=25, step=1)
    battery_kwh = st.number_input("Battery Pack Capacity (kWh)", min_value=30.0, max_value=200.0, value=75.0, step=5.0)
    chemistry = st.selectbox("Battery Chemistry", list(BatteryChemistry), index=0)
    charge_power = st.number_input("Max Charge Power (kW/vehicle)", min_value=3.3, max_value=50.0, value=11.0, step=1.0)
    discharge_power = st.number_input("Max V2G Discharge (kW/vehicle)", min_value=3.3, max_value=50.0, value=11.0, step=1.0)
    eff_pct = st.slider("Round-Trip Efficiency (%)", min_value=75, max_value=98, value=90)

    st.subheader("💡 Grid & Tariff Parameters")
    tariff_scheme = st.selectbox("Electricity Tariff Structure", list(ChargingTariffScheme), index=0)
    service_mode = st.selectbox("Grid Dispatch Priority", list(GridServiceMode), index=0)
    solar_peak = st.number_input("Co-located Solar Peak (kW)", min_value=0.0, max_value=1000.0, value=120.0, step=10.0)

vehicle_cfg = FleetVehicleConfig(
    vehicle_id="fleet_default",
    battery_capacity_kwh=battery_kwh,
    chemistry=chemistry,
    max_charge_power_kw=charge_power,
    max_discharge_power_kw=discharge_power,
    round_trip_efficiency_pct=float(eff_pct),
)

result = V2GOrchestratorEngine.simulate_fleet(
    fleet_size=fleet_size,
    vehicle_cfg=vehicle_cfg,
    tariff_scheme=tariff_scheme,
    service_mode=service_mode,
    rooftop_solar_peak_kw=solar_peak,
)

# KPIs
render_v2g_kpi_cards(st, result)

# Visualizations
tab_dispatch, tab_soc, tab_table = st.tabs(["⚡ 24-Hr Power Dispatch", "🔋 Battery SoC Trajectory", "📊 Hourly Dispatch Matrix"])

with tab_dispatch:
    st.plotly_chart(create_v2g_dispatch_chart(result.hourly_schedule), use_container_width=True)

with tab_soc:
    st.plotly_chart(create_fleet_soc_curve(result.hourly_schedule), use_container_width=True)

with tab_table:
    df = pd.DataFrame(
        [
            {
                "Hour": f"{d.hour:02d}:00",
                "Tariff ($/kWh)": f"${d.tariff_price_usd_kwh:.2f}",
                "Grid Carbon (g/kWh)": d.grid_carbon_intensity_g_kwh,
                "Solar Gen (kW)": d.solar_generation_kw,
                "Fleet Charge (kW)": d.fleet_charging_kw,
                "V2G Discharge (kW)": d.fleet_discharging_kw,
                "Net Grid Exchange (kW)": d.net_grid_exchange_kw,
                "Average Fleet SoC (%)": f"{d.average_fleet_soc_pct:.1f}%",
                "Cumulative Margin ($)": f"${d.cumulative_cashflow_usd:.2f}",
            }
            for d in result.hourly_schedule
        ]
    )
    st.dataframe(df, use_container_width=True)
