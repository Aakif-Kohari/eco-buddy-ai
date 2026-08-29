"""
Carbon Digital Twin Page.
Streamlit page featuring an interactive forecasting chart, scenario sliders, and trajectory warnings.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.ai.predictive_forecaster import PredictiveForecaster
from src.core.database import save_digital_twin_scenario, get_digital_twin_history

st.set_page_config(page_title="Carbon Digital Twin", page_icon="🔮", layout="wide")

st.title("🔮 Personal Carbon Footprint 'Digital Twin' & Forecasting Engine")
st.markdown(
    "Simulate the long-term impact of planned life events on your carbon trajectory."
)

# --- Input Section ---
st.sidebar.header("⚙️ Twin Configuration")
current_footprint = st.sidebar.number_input(
    "Current Annual Footprint (kg CO₂e)", min_value=0, step=100, value=8000
)
target_goal = st.sidebar.number_input(
    "Target Future Footprint (kg CO₂e)", min_value=0, step=100, value=4000
)

if "forecaster" not in st.session_state:
    st.session_state.forecaster = PredictiveForecaster(current_footprint)

forecaster = st.session_state.forecaster

st.subheader("🎛️ Apply Future Scenarios")
st.markdown("Select the life changes you plan to make in the near future.")

scenarios = forecaster.get_available_scenarios()
cols = st.columns(2)
for i, scenario in enumerate(scenarios):
    with cols[i % 2]:
        if st.checkbox(
            f"{scenario['name']} (-{scenario['reduction_kg']} kg/yr)",
            key=f"scenario_{i}",
        ):
            forecaster.apply_scenario_by_key(
                list(forecaster.SCENARIO_LIBRARY.keys())[i]
            )

if st.button("🔄 Regenerate Forecast", type="primary"):
    # Reset and re-apply based on checkboxes
    forecaster.twin.scenarios_applied = []
    for i, scenario in enumerate(scenarios):
        if st.session_state.get(f"scenario_{i}", False):
            forecaster.apply_scenario_by_key(
                list(forecaster.SCENARIO_LIBRARY.keys())[i]
            )

    report = forecaster.generate_forecast_report(target_goal_kg=target_goal)
    st.session_state.forecast_report = report
    save_digital_twin_scenario(current_footprint, target_goal, report)
    st.success("Forecast updated and saved!")

# --- Results Display ---
if "forecast_report" in st.session_state:
    report = st.session_state.forecast_report

    st.divider()
    st.subheader("📈 5-Year Carbon Trajectory Forecast")

    # Status Metric
    status_color = "normal" if report["goal_status"] == "On Track" else "inverse"
    st.metric(
        "Projection vs. Target Goal",
        report["goal_status"],
        delta=f"Target: {report['target_goal_kg']} kg"
        if report["target_goal_kg"]
        else "No target set",
        delta_color=status_color,
    )

    # Forecast Chart
    baseline_df = pd.DataFrame(report["baseline_trajectory"])
    scenario_df = pd.DataFrame(report["scenario_trajectory"])

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=baseline_df["year"],
            y=baseline_df["projected_footprint_kg"],
            mode="lines+markers",
            name="Baseline (No Change)",
            line=dict(color="#d62728", dash="dash"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=scenario_df["year"],
            y=scenario_df["projected_footprint_kg"],
            mode="lines+markers",
            name=report["scenario_trajectory"][0]["scenario"],
            line=dict(color="#2ca02c", width=3),
        )
    )

    # Add target goal line if set
    if report["target_goal_kg"]:
        fig.add_hline(
            y=report["target_goal_kg"],
            line_dash="dot",
            line_color="blue",
            annotation_text=f"Target Goal: {report['target_goal_kg']} kg",
        )

    fig.update_layout(
        title="Projected Annual Carbon Footprint",
        xaxis_title="Year",
        yaxis_title="kg CO₂e",
        template="plotly_white",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Applied Scenarios Summary
    st.subheader("✅ Active Scenarios")
    if report["scenarios_applied"]:
        for s in report["scenarios_applied"]:
            st.markdown(f"- **{s['name']}**: -{s['annual_reduction_kg']} kg/year")
    else:
        st.info(
            "No future scenarios applied. The forecast shows the baseline trajectory."
        )
