"""Streamlit Page for Agroecological Soil Carbon Sequestration & Crop Rotation Planner.
"""

import streamlit as st
import pandas as pd
from soil_carbon_types import (
    FarmFieldParameters,
    SoilTextureType,
    TillagePractice,
    CoverCropStrategy,
)
from soil_carbon_engine import SoilCarbonEngine
from soil_carbon_cards import render_soil_carbon_kpis
from soil_carbon_charts import create_soc_trajectory_chart, create_cumulative_credits_chart

st.set_page_config(
    page_title="Soil Carbon & Agroecology Planner",
    page_icon="🌾",
    layout="wide",
)

st.title("🌾 Agroecological Soil Carbon Sequestration Planner")
st.markdown(
    """
    Simulate multi-pool Soil Organic Carbon (SOC) accumulation, legume biological nitrogen fixation,
    synthetic fertilizer N₂O abatement, and verified carbon credit yields over a 10-year transition.
    """
)

with st.sidebar:
    st.header("🚜 Farm & Soil Characteristics")
    field_name = st.text_input("Field / Farm Enterprise Name", value="Prairie Meadow Regenerative Farm")
    area_ha = st.number_input("Field Area (Hectares)", min_value=1.0, max_value=50000.0, value=85.0, step=5.0)
    soc_baseline = st.slider("Baseline Topsoil SOC (%)", min_value=0.5, max_value=6.0, value=1.75, step=0.05)
    bulk_density = st.number_input("Bulk Density (g/cm³)", min_value=0.8, max_value=1.8, value=1.32, step=0.02)
    depth_cm = st.slider("Sampling Horizon Depth (cm)", min_value=15, max_value=60, value=30)

    soil_texture = st.selectbox("Soil Texture Classification", list(SoilTextureType), index=0)

    st.subheader("🌱 Regenerative Management Practices")
    tillage = st.selectbox("Tillage Intensity", list(TillagePractice), index=2)
    cover_crop = st.selectbox("Cover Cropping Strategy", list(CoverCropStrategy), index=3)
    compost_tons = st.number_input("Compost / Biochar Addition (Dry t/ha/yr)", min_value=0.0, max_value=25.0, value=3.5, step=0.5)
    fert_n_kg = st.number_input("Baseline Synthetic N Fertilizer (kg N/ha/yr)", min_value=0.0, max_value=300.0, value=120.0, step=10.0)
    credit_price = st.number_input("Carbon Credit Market Price ($/t CO₂e)", min_value=5.0, max_value=150.0, value=32.0, step=1.0)

params = FarmFieldParameters(
    field_name=field_name,
    area_hectares=area_ha,
    baseline_soc_pct=soc_baseline,
    bulk_density_g_cm3=bulk_density,
    sampling_depth_cm=float(depth_cm),
    soil_texture=soil_texture,
    tillage_practice=tillage,
    cover_crop_strategy=cover_crop,
    compost_addition_dry_tons_per_ha_yr=compost_tons,
    synthetic_nitrogen_kg_per_ha_yr=fert_n_kg,
    carbon_credit_price_usd_ton=credit_price,
)

result = SoilCarbonEngine.simulate(params)

# KPIs
render_soil_carbon_kpis(st, result)

# Visualizations
c1, c2 = st.columns([1, 1])

with c1:
    st.plotly_chart(create_soc_trajectory_chart(result.trajectory), use_container_width=True)

with c2:
    st.plotly_chart(create_cumulative_credits_chart(result.trajectory), use_container_width=True)

st.subheader("📋 10-Year Annual Soil GHG & Carbon Accounting Breakdown")
df_traj = pd.DataFrame(
    [
        {
            "Year": f"Year {p.year}",
            "SOC Stock (t C/ha)": p.soc_stock_tons_c_ha,
            "Net Sequestration (t CO₂e/ha)": p.net_annual_sequestration_tons_co2e_ha,
            "N₂O Fertilizer GHG (t CO₂e/ha)": p.n2o_fertilizer_emissions_tons_co2e_ha,
            "Net Annual GHG Balance (t CO₂e/ha)": p.net_ghg_balance_tons_co2e_ha,
            "Cumulative Revenue ($)": f"${p.cumulative_carbon_credits_usd:,.2f}",
        }
        for p in result.trajectory
    ]
)
st.dataframe(df_traj, use_container_width=True)
