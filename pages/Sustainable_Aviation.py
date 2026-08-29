"""
Sustainable Aviation Page.
Streamlit page featuring an interactive flight builder, layover vs. direct comparison charts, and SAF impact sliders.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from aviation_carbon_optimizer import AviationCarbonOptimizer
from saf_impact_calculator import SAFImpactCalculator
from database import save_aviation_plan, get_aviation_history

st.set_page_config(page_title="Sustainable Aviation", page_icon="✈️", layout="wide")

st.title("✈️ Aviation & Long-Distance Travel Carbon Optimizer")
st.markdown(
    "Evaluate the carbon footprint of your flights, compare routing options, and explore the impact of Sustainable Aviation Fuel (SAF)."
)

# --- Input Section ---
st.sidebar.header("⚙️ Flight Details")
distance = st.sidebar.number_input(
    "Flight Distance (km)", min_value=100, step=50, value=1500
)
cabin = st.sidebar.selectbox(
    "Cabin Class", ["Economy", "Premium Economy", "Business", "First"]
)
layover = st.sidebar.checkbox("Includes Layover(s)", value=False)
base_price = st.sidebar.number_input(
    "Estimated Base Ticket Price ($)", min_value=50, step=25, value=300
)

if st.sidebar.button("🔍 Analyze Flight"):
    optimizer = AviationCarbonOptimizer(
        distance_km=distance, cabin_class=cabin, has_layover=layover
    )
    result = optimizer.calculate_emissions()
    rail_comp = optimizer.compare_with_rail()
    recs = optimizer.get_recommendations()

    saf_calc = SAFImpactCalculator(result["total_emissions_kg"], base_price)
    saf_scenarios = saf_calc.calculate_saf_scenarios()

    st.session_state.aviation_result = {
        "flight": result,
        "rail": rail_comp,
        "recs": recs,
        "saf": saf_scenarios,
        "saf_edu": saf_calc.get_saf_education_snippet(),
    }
    save_aviation_plan(distance, cabin, layover, result["total_emissions_kg"])
    st.success("Flight analysis complete and saved!")

# --- Results Display ---
if "aviation_result" in st.session_state:
    res = st.session_state.aviation_result

    st.divider()
    st.subheader("📊 Flight Carbon Footprint")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Total Emissions", f"{res['flight']['total_emissions_kg']:,.1f} kg CO₂e"
        )
        st.metric("Distance", f"{res['flight']['distance_km']} km")
        st.info(
            f"Routing: **{res['flight']['routing_type']}** | Class: **{res['flight']['cabin_class']}**"
        )

    with col2:
        # Bar chart comparing base vs adjusted
        fig = go.Figure(
            data=[
                go.Bar(
                    name="Base Emissions",
                    x=["Flight"],
                    y=[res["flight"]["base_emissions_kg"]],
                    marker_color="#1f77b4",
                ),
                go.Bar(
                    name="Adjusted Emissions",
                    x=["Flight"],
                    y=[res["flight"]["total_emissions_kg"]],
                    marker_color="#d62728",
                ),
            ]
        )
        fig.update_layout(title="Emissions Multiplier Impact", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 💡 Optimization Recommendations")
    for rec in res["recs"]:
        st.markdown(f"- {rec}")

    if res["rail"]["viable"]:
        st.divider()
        st.subheader("🚆 Rail Alternative Comparison")
        st.success(
            f"Taking high-speed rail for this distance would save **{res['rail']['savings_kg']} kg CO₂e** ({res['rail']['savings_pct']}% reduction)!"
        )

    st.divider()
    st.subheader("🌱 Sustainable Aviation Fuel (SAF) Impact")
    st.markdown(res["saf_edu"])

    # SAF Scenarios Table
    df_saf = pd.DataFrame(res["saf"])
    df_saf.rename(
        columns={
            "blend_pct": "SAF Blend (%)",
            "carbon_saved_kg": "Carbon Saved (kg)",
            "remaining_emissions_kg": "Remaining Emissions (kg)",
            "cost_premium_usd": "Est. Cost Premium ($)",
            "total_price_usd": "Total Est. Price ($)",
        },
        inplace=True,
    )

    st.dataframe(df_saf, use_container_width=True, hide_index=True)

    # SAF Chart
    fig_saf = go.Figure()
    fig_saf.add_trace(
        go.Bar(
            x=df_saf["SAF Blend (%)"],
            y=df_saf["Carbon Saved (kg)"],
            name="Carbon Saved (kg)",
            marker_color="#2ca02c",
        )
    )
    fig_saf.update_layout(
        title="Carbon Savings by SAF Blend Percentage", template="plotly_white"
    )
    st.plotly_chart(fig_saf, use_container_width=True)
