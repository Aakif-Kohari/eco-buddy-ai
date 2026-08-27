"""
Appliance Lifecycle Page.
Streamlit page where users can register appliances, view circularity scores, and receive repair vs. replace recommendations.
"""

import streamlit as st
import plotly.graph_objects as go
from appliance_circularity_engine import ApplianceCircularityEngine
from embodied_carbon_tracker import EmbodiedCarbonTracker
from database import save_appliance_registration, get_appliance_history

st.set_page_config(page_title="Appliance Lifecycle", page_icon="🔌", layout="wide")

st.title("🔌 Household Appliance Circularity & Lifecycle Tracker")
st.markdown(
    "Make data-driven decisions on whether to maintain, repair, or replace your household devices based on embodied and operational carbon metrics."
)

engine = ApplianceCircularityEngine()
tracker = EmbodiedCarbonTracker()
appliance_types = tracker.get_all_appliance_types()

# --- Input Section ---
st.sidebar.header("➕ Register an Appliance")
with st.sidebar.form("register_appliance"):
    app_type = st.selectbox(
        "Appliance Type",
        options=appliance_types,
        format_func=lambda x: tracker.get_appliance_display_name(x),
    )
    age = st.number_input(
        "Current Age (Years)", min_value=0, max_value=30, step=1, value=5
    )
    usage = st.number_input(
        "Estimated Annual Usage (kWh)", min_value=10, step=50, value=500
    )

    if st.form_submit_button("Register & Analyze"):
        try:
            result = engine.evaluate_appliance(app_type, age, usage)
            st.session_state.latest_analysis = result
            save_appliance_registration("demo_user", app_type, age, usage, result)
            st.sidebar.success("Analysis complete!")
            st.rerun()
        except ValueError as e:
            st.sidebar.error(str(e))

# --- Results Display ---
if "latest_analysis" in st.session_state:
    res = st.session_state.latest_analysis

    st.divider()
    st.subheader(
        f"📊 Lifecycle Analysis: {tracker.get_appliance_display_name(res['appliance_type'])}"
    )

    col1, col2, col3 = st.columns(3)

    # Circularity Score Gauge
    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=res["circularity_score"],
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Circularity Score (Higher = Keep)"},
            gauge={
                "axis": {"range": [None, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 40], "color": "#dc3545"},  # Red: Replace
                    {"range": [40, 70], "color": "#ffc107"},  # Yellow: Consider
                    {"range": [70, 100], "color": "#2ca02c"},  # Green: Keep
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": res["circularity_score"],
                },
            },
        )
    )
    fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    col1.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        st.metric("Current Annual Carbon", f"{res['current_annual_carbon_kg']} kg")
        st.metric("New Model Annual Carbon", f"{res['new_annual_carbon_kg']} kg")
        st.metric(
            "Potential Annual Savings",
            f"{res['annual_operational_savings_kg']} kg",
            delta_color="normal",
        )

    with col3:
        st.metric("Embodied Carbon Cost", f"{res['embodied_carbon_cost_kg']} kg")
        st.metric("Tipping Point", f"{res['tipping_point_years']} yrs")
        st.metric(
            "Recycling Value", f"{res['end_of_life_recycling_value_kg']} kg avoided"
        )

    st.markdown("### 💡 Recommendation")
    st.info(res["recommendation"])

    # Trade-off Chart
    st.markdown("### ⚖️ Embodied vs. Operational Carbon Trade-off")
    fig_bar = go.Figure()
    fig_bar.add_trace(
        go.Bar(
            name="Embodied Carbon (One-time cost of new)",
            x=["Carbon Impact"],
            y=[res["embodied_carbon_cost_kg"]],
            marker_color="#1f77b4",
        )
    )
    fig_bar.add_trace(
        go.Bar(
            name=f"Operational Savings over {res['tipping_point_years'] if isinstance(res['tipping_point_years'], float) else 5} Years",
            x=["Carbon Impact"],
            y=[
                res["annual_operational_savings_kg"]
                * (
                    res["tipping_point_years"]
                    if isinstance(res["tipping_point_years"], float)
                    else 5
                )
            ],
            marker_color="#2ca02c",
        )
    )
    fig_bar.update_layout(barmode="group", template="plotly_white")
    st.plotly_chart(fig_bar, use_container_width=True)
