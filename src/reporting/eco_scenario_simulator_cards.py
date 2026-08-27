"""
Streamlit Component Renderers for Eco-Footprint Scenario Simulator
"""

import streamlit as st
from typing import List, Dict, Any
from src.utils.eco_scenario_simulator_types import FootprintScenario, ScenarioLever


def render_scenario_summary_header(scenario: FootprintScenario) -> None:
    """Renders top metrics comparing baseline vs simulated emissions for a scenario."""
    base_co2 = scenario.calculate_total_baseline_co2_kg()
    sim_co2 = scenario.calculate_total_simulated_co2_kg()
    diff_co2 = base_co2 - sim_co2
    pct = scenario.calculate_annual_reduction_pct()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🌍 Baseline Footprint",
            value=f"{base_co2:,.1f} kg",
            delta="Current Annual",
        )

    with col2:
        st.metric(
            label="🌱 Simulated Footprint",
            value=f"{sim_co2:,.1f} kg",
            delta=f"-{pct}% Target",
        )

    with col3:
        st.metric(
            label="📉 Annual CO₂ Avoided",
            value=f"{diff_co2:,.1f} kg",
            delta="Net Reduction",
        )

    with col4:
        st.metric(
            label="🎯 Target Completion Year",
            value=f"{scenario.target_year}",
            delta="Simulation Horizon",
        )


def render_lever_slider_card(lever: ScenarioLever, index: int) -> float:
    """Renders an interactive slider card for adjusting a scenario lever."""
    delta_co2 = lever.calculate_co2_delta_kg()

    with st.container():
        st.markdown(f"#### ⚙️ {lever.name} ({lever.category.value})")
        st.caption(lever.description)

        col_slider, col_info = st.columns([3, 1])

        with col_slider:
            new_val = st.slider(
                f"Simulated Value ({lever.unit})",
                min_value=0.0,
                max_value=float(lever.baseline_value * 2.0) if lever.baseline_value > 0 else 100.0,
                value=float(lever.simulated_value),
                key=f"lever_slider_{index}",
            )

        with col_info:
            color = "#2E7D32" if delta_co2 <= 0 else "#D32F2F"
            st.markdown(
                f"""
                <div style="text-align: center; padding: 8px; border-radius: 8px; background-color: #F5F5F5;">
                    <span style="font-size: 0.8rem; color: #666;">CO₂ Impact</span><br>
                    <b style="color: {color}; font-size: 1.1rem;">{delta_co2:+.1f} kg</b>
                </div>
                """,
                unsafe_allow_html=True,
            )

        return new_val
