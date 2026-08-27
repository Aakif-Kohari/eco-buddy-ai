"""Streamlit Page for Passive Cooling & Thermal Comfort Architecture Simulator.
"""

import streamlit as st
import pandas as pd
from src.energy.passive_cooling_types import (
    BuildingParameters,
    ClimateZone,
    InsulationLevel,
    ShadingStrategy,
    VentilationMode,
)
from src.energy.passive_cooling_engine import PassiveCoolingEngine
from src.energy.passive_cooling_cards import render_passive_cooling_kpis, render_envelope_efficiency_badge
from src.energy.passive_cooling_charts import (
    create_diurnal_thermal_chart,
    create_pmv_ppd_comfort_chart,
    create_cooling_strategy_breakdown_chart,
)

st.set_page_config(
    page_title="Passive Cooling & Thermal Comfort Planner",
    page_icon="❄️",
    layout="wide",
)

st.title("❄️ Passive Cooling & Thermal Comfort Optimization Engine")
st.markdown(
    """
    Simulate architectural passive cooling techniques (external solar shading, high thermal mass inertia,
    night-purge cross ventilation, and envelope insulation) to eliminate air-conditioning energy demand
    and enhance building climate resilience.
    """
)

with st.sidebar:
    st.header("⚙️ Building & Envelope Parameters")
    building_name = st.text_input("Building / Project Name", value="Eco-Resilience Tower")
    floor_area = st.number_input("Conditioned Floor Area (m²)", min_value=20.0, max_value=50000.0, value=250.0, step=10.0)
    ceiling_height = st.number_input("Ceiling Height (m)", min_value=2.0, max_value=8.0, value=3.0, step=0.1)
    wwr = st.slider("Window-to-Wall Ratio (WWR %)", min_value=10, max_value=90, value=35) / 100.0

    climate = st.selectbox("Climate Zone", list(ClimateZone), index=0)
    insulation = st.selectbox("Envelope Insulation & Glazing", list(InsulationLevel), index=2)
    shading = st.selectbox("Solar Shading Strategy", list(ShadingStrategy), index=2)
    ventilation = st.selectbox("Natural Ventilation Mechanism", list(VentilationMode), index=1)

    occupants = st.number_input("Number of Occupants", min_value=1, max_value=1000, value=5)
    elec_cost = st.number_input("Electricity Tariff ($/kWh)", min_value=0.01, max_value=1.50, value=0.18, step=0.01)

params = BuildingParameters(
    building_name=building_name,
    floor_area_m2=floor_area,
    ceiling_height_m=ceiling_height,
    window_to_wall_ratio=wwr,
    climate_zone=climate,
    insulation_level=insulation,
    shading_strategy=shading,
    ventilation_mode=ventilation,
    occupant_count=occupants,
    electricity_cost_kwh=elec_cost,
)

result = PassiveCoolingEngine.simulate(params)

# KPIs and Badges
render_passive_cooling_kpis(st, result)
render_envelope_efficiency_badge(st, result)

# Visualizations
tab1, tab2, tab3 = st.tabs(["📈 Diurnal Temperature Profile", "👤 PMV / PPD Comfort Analysis", "📋 Hourly Data Matrix"])

with tab1:
    st.plotly_chart(create_diurnal_thermal_chart(result.hourly_profiles), use_container_width=True)
    c1, c2 = st.columns([1, 1])
    with c1:
        st.plotly_chart(create_cooling_strategy_breakdown_chart(result.strategy_breakdown_pct), use_container_width=True)
    with c2:
        st.info(
            f"""
            **Bioclimatic Engineering Summary for {result.building_name}**:
            - Baseline Cooling Demand: **{result.annual_cooling_energy_baseline_kwh:,.0f} kWh/year**
            - Optimized Passive Cooling: **{result.annual_cooling_energy_passive_kwh:,.0f} kWh/year**
            - Estimated Retrofit CapEx: **${result.estimated_retrofit_capex_usd:,.2f}**
            - Simple Payback Period: **{result.simple_payback_years:.1f} Years**
            """
        )

with tab2:
    st.plotly_chart(create_pmv_ppd_comfort_chart(result.hourly_profiles), use_container_width=True)
    st.caption("ISO 7730 Comfort Index: PMV between -0.5 and +0.5 indicates ideal thermal neutrality (PPD < 10%).")

with tab3:
    df = pd.DataFrame(
        [
            {
                "Hour": f"{p.hour:02d}:00",
                "Outdoor Ambient (°C)": p.outdoor_temp_c,
                "Outdoor Humidity (%)": p.outdoor_humidity_pct,
                "Solar (W/m²)": p.solar_radiation_w_m2,
                "Unconditioned Temp (°C)": p.indoor_temp_unconditioned_c,
                "Passive Temp (°C)": p.indoor_temp_passive_c,
                "PMV": p.predicted_mean_vote_pmv,
                "PPD (%)": p.predicted_percentage_dissatisfied_ppd,
                "Hourly Saved (kWh)": p.cooling_load_saved_kwh,
            }
            for p in result.hourly_profiles
        ]
    )
    st.dataframe(df, use_container_width=True)
