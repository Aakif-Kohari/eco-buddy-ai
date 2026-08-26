"""
EJ Impact Mapper Page.
Streamlit page featuring an interactive impact dashboard, community vulnerability metrics, and localized advocacy tips.
"""

import streamlit as st
import plotly.graph_objects as go
from environmental_justice_mapper import EnvironmentalJusticeMapper
from local_air_quality_tracker import LocalAirQualityTracker
from database import save_ej_impact_log, get_ej_history

st.set_page_config(page_title="EJ Impact Mapper", page_icon="⚖️", layout="wide")

st.title("⚖️ Hyper-Local Environmental Justice & Air Quality Impact Mapper")
st.markdown(
    "Understand how your lifestyle choices impact local air quality and correlate with community vulnerability metrics."
)

mapper = EnvironmentalJusticeMapper()
tracker = LocalAirQualityTracker(mapper)
regions = mapper.get_all_regions()

# --- Input Section ---
st.subheader("📍 Select Your Community & Activity")
col1, col2 = st.columns(2)

with col1:
    zip_code = st.selectbox(
        "Select Region (Zip Code)",
        options=regions,
        format_func=lambda x: f"{mapper.get_region_display_name(x)} ({x})",
    )

with col2:
    activity = st.selectbox(
        "Daily Activity",
        options=[
            "ice_car_mile",
            "ev_car_mile",
            "gas_generator_hour",
            "wood_burning_hour",
        ],
        format_func=lambda x: x.replace("_", " ").title(),
    )
    quantity = st.number_input(
        "Quantity (miles or hours)", min_value=0.1, step=0.5, value=10.0
    )

if st.button("🔍 Calculate Local Impact"):
    with st.spinner("Analyzing local air quality and EJ metrics..."):
        try:
            impact = tracker.calculate_activity_impact(zip_code, activity, quantity)
            tips = tracker.generate_mitigation_tips(impact)

            st.session_state.ej_impact = impact
            st.session_state.ej_tips = tips

            save_ej_impact_log(zip_code, activity, quantity, impact)
            st.success("Impact analysis complete and saved!")
        except ValueError as e:
            st.error(str(e))

# --- Results Display ---
if "ej_impact" in st.session_state:
    impact = st.session_state.ej_impact
    tips = st.session_state.ej_tips

    st.divider()
    st.subheader(f"📊 Community Profile: {impact['region_name']}")

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Environmental Justice Index",
        f"{impact['baseline_ej_index']}/100",
        help="Higher score indicates higher vulnerability and disadvantage.",
    )
    col2.metric(
        "Baseline PM2.5",
        f"{impact['estimated_new_pm25'] - (impact['added_pm25_g'] / 1000):.1f} µg/m³",
    )
    col3.metric("Vulnerability Level", impact["vulnerability_level"])

    # Impact Bar Chart
    st.markdown("### 🏭 Marginal Pollutant Contribution")
    st.info(
        f"Your logged activity (**{impact['quantity']} {activity.replace('_', ' ').title()}**) adds an estimated **{impact['added_pm25_g']}g of PM2.5** and **{impact['added_nox_g']}g of NOx** to the local airshed."
    )

    fig = go.Figure(
        data=[
            go.Bar(
                name="Added PM2.5 (g)",
                x=["Your Activity"],
                y=[impact["added_pm25_g"]],
                marker_color="#d62728",
            ),
            go.Bar(
                name="Added NOx (g)",
                x=["Your Activity"],
                y=[impact["added_nox_g"]],
                marker_color="#ff7f0e",
            ),
        ]
    )
    fig.update_layout(
        title="Estimated Local Pollutant Load from Activity",
        yaxis_title="Grams",
        template="plotly_white",
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Mitigation Tips
    st.divider()
    st.subheader("💡 Localized Mitigation & Advocacy Tips")
    for tip in tips:
        st.markdown(f"- {tip}")
