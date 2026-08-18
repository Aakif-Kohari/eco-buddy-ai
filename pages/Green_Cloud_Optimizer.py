"""
Streamlit UI Page for Green Cloud & AI Workload Carbon Optimizer
"""

import streamlit as st
from src.lib.green_cloud import GreenCloudOptimizer, CLOUD_REGION_CARBON_INTENSITY, HARDWARE_POWER_SPECS

def render_green_cloud_page():
    st.set_page_config(page_title="Green Cloud Optimizer", page_icon="☁️", layout="wide")
    st.title("☁️ Green Cloud & AI Workload Carbon Optimizer")
    st.markdown("Measure carbon emissions from cloud compute, model training, and database instances. Optimize region placement and time-shift batch workloads to minimize Scope 2/3 IT footprints.")

    optimizer = GreenCloudOptimizer()

    tab1, tab2 = st.tabs(["🖥️ Workload Carbon Calculator", "🕒 Intelligent Batch Time-Shifting"])

    with tab1:
        st.subheader("Compute Workload Footprint")
        col1, col2 = st.columns(2)

        with col1:
            region_names = {k: f"{v['name']} ({v['gco2_per_kwh']} gCO2/kWh)" for k, v in CLOUD_REGION_CARBON_INTENSITY.items()}
            selected_region_key = st.selectbox("Current Cloud Region", list(region_names.keys()), format_func=lambda k: region_names[k])
            runtime = st.number_input("Workload Duration (Hours)", min_value=0.5, max_value=8760.0, value=24.0, step=1.0)
            cpu_cores = st.number_input("vCPU Cores", min_value=1, max_value=256, value=16)
            mem_gb = st.number_input("Memory (GB RAM)", min_value=2.0, max_value=1024.0, value=64.0, step=4.0)

        with col2:
            gpu_choice = st.selectbox("Accelerator / GPU Type", ["None", "gpu_nvidia_t4", "gpu_nvidia_a100", "gpu_nvidia_h100"])
            gpu_count = st.number_input("Number of GPUs", min_value=0, max_value=64, value=0 if gpu_choice == "None" else 2)
            utilization = st.slider("Average Utilization Rate (%)", min_value=10, max_value=100, value=80)
            storage = st.number_input("SSD Storage Volume (TB)", min_value=0.1, max_value=100.0, value=1.0, step=0.5)

        if st.button("Analyze Footprint & Find Cleanest Region", type="primary"):
            res = optimizer.estimate_workload_emissions(
                region=selected_region_key,
                runtime_hours=runtime,
                cpu_cores=cpu_cores,
                gpu_type=None if gpu_choice == "None" else gpu_choice,
                gpu_count=gpu_count,
                avg_utilization_pct=utilization,
                memory_gb=mem_gb,
                storage_tb=storage
            )

            m1, m2, m3 = st.columns(3)
            m1.metric("Energy Consumed", f"{res['energy_consumed_kwh']} kWh")
            m2.metric("Emissions Generated", f"{res['emissions_kg_co2e']} kg CO₂e")
            m3.metric("Facility Power Draw", f"{res['total_power_watts']} Watts")

            st.success(f"🌱 **Recommended Clean Region:** {res['cleanest_alternative_region']}")
            st.info(f"Relocating this workload can reduce carbon emissions by **{res['potential_savings_kg_co2e']} kg CO₂e** ({res['savings_percentage']}% reduction).")

    with tab2:
        st.subheader("Renewable Grid Time-Shifting Strategy")
        w_type = st.selectbox("Select Scheduled Job Type", ["ai_model_training", "batch_analytics", "ci_cd_pipelines", "database_backups"])
        flexibility = st.slider("Allowable Execution Delay Window (Hours)", min_value=1, max_value=48, value=12)

        if st.button("Generate Green Dispatch Schedule"):
            plan = optimizer.batch_schedule_recommendation(w_type, flexibility)
            st.write(f"**Recommended Time Window:** {plan['recommended_dispatch_window']}")
            st.metric("Expected Carbon Abatement", f"-{plan['projected_carbon_reduction_pct']}%")

if __name__ == "__main__":
    render_green_cloud_page()
