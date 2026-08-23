"""
Urban Health Impact Analyzer Page.
Streamlit page featuring interactive sliders to visualize the trade-off between noise exposure and green space benefits.
"""

import streamlit as st
import plotly.graph_objects as go
from noise_pollution_tracker import NoisePollutionTracker
from green_space_health_impact import GreenSpaceHealthImpact
from database import save_urban_health_profile

st.set_page_config(page_title="Urban Health Impact", page_icon="🌳", layout="wide")

st.title("🌳 Dynamic Noise Pollution & Green Space Health Impact Analyzer")
st.markdown(
    "Estimate your daily noise exposure and see how green space habits can mitigate health impacts."
)

tracker = NoisePollutionTracker()
green_space = GreenSpaceHealthImpact()

# --- Input Section ---
st.subheader("🏙️ Daily Environment Profile")
st.markdown(
    "Estimate how many hours you spend in each environment per day (Total should be ~24h)."
)

col1, col2 = st.columns(2)
with col1:
    hours_dense_urban = st.number_input(
        "Dense Urban (Busy streets)", min_value=0, max_value=24, value=4
    )
    hours_suburban = st.number_input(
        "Suburban (Residential)", min_value=0, max_value=24, value=8
    )
    hours_highway = st.number_input("Near Highway", min_value=0, max_value=24, value=1)
    hours_indoor = st.number_input("Indoor Home", min_value=0, max_value=24, value=8)

with col2:
    hours_park = st.number_input(
        "Park / Green Space", min_value=0, max_value=24, value=1
    )
    hours_office = st.number_input("Office / Work", min_value=0, max_value=24, value=8)

    st.divider()
    st.markdown("🌿 Green Space Habits")
    weekly_park_visits = st.slider("Park/Green Space visits per week", 0, 14, 2)
    tree_canopy_pct = st.slider(
        "Estimated tree canopy coverage near your home (%)", 0, 100, 30
    )

time_allocation = {
    "dense_urban": hours_dense_urban,
    "suburban": hours_suburban,
    "near_highway": hours_highway,
    "indoor_home": hours_indoor,
    "park_green": hours_park,
    "office": hours_office,
}

if st.button("🔍 Analyze Health Impact", type="primary"):
    exposure = tracker.calculate_daily_exposure(time_allocation)
    mitigation = green_space.calculate_mitigation(
        exposure["health_impact_score"], weekly_park_visits, tree_canopy_pct
    )

    st.session_state.exposure = exposure
    st.session_state.mitigation = mitigation

    # Save to DB
    save_urban_health_profile(
        time_allocation, weekly_park_visits, tree_canopy_pct, exposure, mitigation
    )
    st.success("Analysis complete and saved!")

# --- Results Section ---
if "exposure" in st.session_state and "mitigation" in st.session_state:
    exposure = st.session_state.exposure
    mitigation = st.session_state.mitigation

    st.divider()
    st.subheader("📊 Health Impact Analysis")

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Average Daily Noise",
        f"{exposure['average_daily_db']} dB",
        delta=exposure["risk_level"],
    )
    col2.metric(
        "Baseline Impact Score",
        f"{mitigation['baseline_noise_impact']}/100",
        delta_color="inverse",
    )
    col3.metric(
        "Adjusted Impact Score",
        f"{mitigation['adjusted_health_impact_score']}/100",
        delta=f"-{mitigation['total_mitigation_points']}"
        if mitigation["total_mitigation_points"] > 0
        else "0",
        delta_color="normal"
        if mitigation["adjusted_health_impact_score"] < 50
        else "inverse",
    )

    # Waterfall Chart showing mitigation
    fig = go.Figure(
        go.Waterfall(
            name="Impact Mitigation",
            orientation="v",
            measure=["relative", "relative", "relative", "total"],
            x=[
                "Baseline Noise Impact",
                "Park Visits Mitigation",
                "Tree Canopy Mitigation",
                "Final Adjusted Impact",
            ],
            y=[
                mitigation["baseline_noise_impact"],
                -mitigation["park_mitigation_points"],
                -mitigation["canopy_mitigation_points"],
                mitigation["adjusted_health_impact_score"],
            ],
            decreasing={"marker": {"color": "#2ca02c"}},
            increasing={"marker": {"color": "#d62728"}},
            totals={"marker": {"color": "#1f77b4"}},
        )
    )

    fig.update_layout(
        title="How Green Space Mitigates Noise-Related Health Impacts",
        yaxis_title="Health Impact Score (Lower is Better)",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Insights
    st.subheader("💡 Actionable Insights")
    st.info(
        f"**Stress Reduction Potential:** {mitigation['estimated_stress_reduction_pct']}%"
    )
    st.info(f"**Sleep Quality Improvement:** {mitigation['sleep_quality_improvement']}")

    for rec in mitigation["recommendations"]:
        st.markdown(f"- {rec}")
