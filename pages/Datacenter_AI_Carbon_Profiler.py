"""Streamlit Page for Green Data Center & AI Workload Carbon Profiler.
"""

import streamlit as st
import pandas as pd
from datacenter_carbon_types import (
    AIWorkloadParameters,
    GPUModel,
    CloudRegion,
    CoolingTechnology,
)
from datacenter_carbon_engine import DataCenterCarbonEngine
from datacenter_carbon_cards import render_datacenter_carbon_kpis, render_pue_efficiency_badge
from datacenter_carbon_charts import create_scope_breakdown_waterfall, create_regional_comparison_bar

st.set_page_config(
    page_title="AI & Cloud Carbon Profiler",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Green Data Center & AI Workload Carbon Profiler")
st.markdown(
    """
    Quantify full life-cycle carbon footprint (Scope 2 electricity & Scope 3 embodied silicon LCA)
    and water consumption for LLM training and distributed cloud compute clusters.
    """
)

with st.sidebar:
    st.header("🖥️ Cluster & Workload Specs")
    job_name = st.text_input("Workload / Run Name", value="Llama-3-FineTune-Cluster")
    gpu_model = st.selectbox("GPU / Accelerator Hardware", list(GPUModel), index=0)
    gpu_count = st.number_input("Number of Accelerators (GPUs)", min_value=1, max_value=65536, value=64, step=8)
    duration_hours = st.number_input("Run Duration (Hours)", min_value=0.5, max_value=5000.0, value=72.0, step=1.0)
    utilization = st.slider("Average GPU Utilization (%)", min_value=10, max_value=100, value=85)

    st.subheader("🌐 Infrastructure & Region")
    cloud_region = st.selectbox("Primary Cloud Region", list(CloudRegion), index=0)
    cooling_tech = st.selectbox("Cooling Architecture", list(CoolingTechnology), index=1)

    st.subheader("📚 Model & Dataset Context")
    param_billions = st.number_input("Model Size (Billion Parameters)", min_value=0.1, max_value=2000.0, value=70.0)
    tokens_billions = st.number_input("Dataset Volume (Billion Tokens)", min_value=0.1, max_value=50000.0, value=500.0)

params = AIWorkloadParameters(
    job_name=job_name,
    gpu_model=gpu_model,
    gpu_count=gpu_count,
    training_duration_hours=duration_hours,
    average_gpu_utilization_pct=utilization,
    cloud_region=cloud_region,
    cooling_tech=cooling_tech,
    model_parameter_count_billions=param_billions,
    dataset_tokens_billions=tokens_billions,
)

result = DataCenterCarbonEngine.calculate_workload_emissions(params)

# KPIs and Badges
render_datacenter_carbon_kpis(st, result)
render_pue_efficiency_badge(st, result.effective_pue)

# Visualizations
col_left, col_right = st.columns([1, 1])

with col_left:
    st.plotly_chart(create_scope_breakdown_waterfall(result), use_container_width=True)

with col_right:
    if result.green_region_alternatives:
        st.plotly_chart(create_regional_comparison_bar(result.green_region_alternatives), use_container_width=True)
    else:
        st.success("Currently operating in the lowest carbon intensity region available!")

st.subheader("📊 Spatial Rescheduling & Low-Carbon Region Opportunities")
if result.green_region_alternatives:
    df_opt = pd.DataFrame(
        [
            {
                "Target Region": opt.target_region.value,
                "Carbon Reduction (%)": f"-{opt.carbon_reduction_pct:.1f}%",
                "Emissions Avoided (kg CO₂e)": f"{opt.avoided_emissions_kg:,.1f}",
                "Water Conserved (Liters)": f"{opt.water_saved_liters:,.1f}",
                "Cost Impact ($)": f"{'+' if opt.net_cost_differential_usd > 0 else ''}${opt.net_cost_differential_usd:,.2f}",
            }
            for opt in result.green_region_alternatives
        ]
    )
    st.dataframe(df_opt, use_container_width=True)
