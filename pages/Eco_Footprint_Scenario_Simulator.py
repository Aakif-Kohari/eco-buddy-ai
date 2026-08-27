"""
Streamlit Page: Eco-Footprint Scenario Simulator & Decarbonization Planner
Multi-page section in EcoBuddy AI allowing users to simulate interactive lifestyle levers and project multi-year decarbonization targets.
"""

import streamlit as st
import pandas as pd

from src.utils.eco_scenario_simulator_service import FootprintScenarioSimulatorService
from src.utils.eco_scenario_simulator_types import FootprintScenario, ScenarioLever, ScenarioLeverCategory
from src.reporting.eco_scenario_simulator_cards import render_scenario_summary_header, render_lever_slider_card
from src.reporting.eco_scenario_simulator_charts import build_trajectory_forecast_chart, build_lever_waterfall_chart

st.set_page_config(
    page_title="Scenario Simulator - EcoBuddy AI",
    page_icon="🔮",
    layout="wide",
)

st.title("🔮 Interactive Eco-Footprint Scenario Simulator")
st.markdown(
    "Model future lifestyle changes, simulate carbon reduction levers in real-time, "
    "and project your multi-year net-zero trajectory."
)

service = FootprintScenarioSimulatorService()
current_user_id = st.session_state.get("user_id", 1)

# Session state initialization for working scenario
if "active_scenario" not in st.session_state:
    default_levers = service.get_default_levers()
    st.session_state.active_scenario = FootprintScenario(
        id=None,
        user_id=current_user_id,
        scenario_name="2030 Net-Zero Target",
        description="Default decarbonization scenario with mixed transport and energy levers.",
        target_year=2030,
        levers=default_levers,
    )

active_scenario = st.session_state.active_scenario

# Render Header Metrics
render_scenario_summary_header(active_scenario)

st.divider()

# Navigation Tabs
tab_simulator, tab_forecast, tab_saved = st.tabs([
    "⚙️ Interactive Lever Simulator",
    "📈 Multi-Year Trajectory Forecast",
    "💾 Saved Scenarios",
])

# -------------------------------------------------------------------
# Tab 1: Interactive Lever Simulator
# -------------------------------------------------------------------
with tab_simulator:
    st.subheader("⚙️ Adjust Lifestyle Decarbonization Levers")

    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        active_scenario.scenario_name = st.text_input("Scenario Name", active_scenario.scenario_name)
    with col_meta2:
        active_scenario.target_year = st.number_input("Target Year", min_value=2026, max_value=2050, value=active_scenario.target_year)

    st.write("---")

    updated_levers = []
    for idx, lever in enumerate(active_scenario.levers):
        new_val = render_lever_slider_card(lever, idx)
        lever.simulated_value = new_val
        updated_levers.append(lever)

    active_scenario.levers = updated_levers

    col_save, _ = st.columns([1, 4])
    with col_save:
        if st.button("💾 Save Scenario"):
            saved = service.save_scenario(active_scenario)
            if saved:
                st.success(f"Scenario '{saved.scenario_name}' saved successfully!")
            else:
                st.error("Error saving scenario.")

# -------------------------------------------------------------------
# Tab 2: Multi-Year Trajectory Forecast
# -------------------------------------------------------------------
with tab_forecast:
    st.subheader("📈 Projected Multi-Year Footprint Trajectory")

    projections = service.build_projection_timeline(active_scenario)
    line_chart = build_trajectory_forecast_chart(projections)
    st.plotly_chart(line_chart, use_container_width=True)

    st.subheader("📊 Carbon Reduction Waterfall Breakdown")
    waterfall_chart = build_lever_waterfall_chart(active_scenario.levers)
    st.plotly_chart(waterfall_chart, use_container_width=True)

# -------------------------------------------------------------------
# Tab 3: Saved Scenarios
# -------------------------------------------------------------------
with tab_saved:
    st.subheader("💾 Your Saved Scenarios")
    saved_scenarios = service.get_scenarios(current_user_id)

    if not saved_scenarios:
        st.info("No saved scenarios found yet. Save your scenario in the simulator tab!")
    else:
        for sc in saved_scenarios:
            with st.expander(f"🔮 {sc.scenario_name} (Target Year: {sc.target_year})"):
                st.write(f"**Description:** {sc.description}")
                st.write(f"**Baseline CO₂:** {sc.calculate_total_baseline_co2_kg()} kg | **Simulated CO₂:** {sc.calculate_total_simulated_co2_kg()} kg")
                st.write(f"**Reduction Target:** -{sc.calculate_annual_reduction_pct()}%")
