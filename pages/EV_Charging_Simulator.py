import plotly.graph_objects as go
import streamlit as st

from database import save_ev_charging_session
from ev_charging_optimizer import (
    generate_charging_recommendations,
    optimize_charging_schedule,
)
from grid_intensity_simulator import (
    generate_grid_intensity_profile,
    generate_pricing_profile,
    get_grid_profile_metadata,
)
from units import format_co2, format_currency

st.set_page_config(page_title="EV Charging Simulator", page_icon="🔋", layout="wide")

st.title("🔋 Smart EV Charging Optimizer")
st.markdown(
    "Simulate and optimize your electric vehicle charging schedule to minimize carbon footprint and electricity costs."
)

# --- Sidebar Configuration ---
st.sidebar.header("⚙️ Vehicle & Grid Settings")

battery_capacity = st.sidebar.number_input(
    "Battery Capacity (kWh)", min_value=10.0, max_value=150.0, value=60.0, step=5.0
)
current_soc = st.sidebar.slider("Current State of Charge (%)", 0, 100, 20)
target_soc = st.sidebar.slider("Target State of Charge (%)", current_soc + 10, 100, 80)
charging_rate = st.sidebar.selectbox(
    "Charging Rate",
    [3.7, 7.4, 11.0, 22.0, 50.0],
    index=1,
    format_func=lambda x: f"{x} kW",
)

grid_type = st.sidebar.selectbox(
    "Grid Type",
    ["mixed", "coal_heavy", "renewable_heavy"],
    format_func=lambda x: x.replace("_", " ").title(),
)
pricing_type = st.sidebar.selectbox(
    "Pricing Model",
    ["time_of_use", "flat"],
    format_func=lambda x: x.replace("_", " ").title().replace("Of", "of"),
)

# --- Main Content ---
metadata = get_grid_profile_metadata()
st.info(
    f"**Selected Grid:** {metadata[grid_type]['name']} - {metadata[grid_type]['description']}"
)

if st.button("🚀 Run Optimization", type="primary"):
    with st.spinner("Calculating optimal charging schedule..."):
        grid_profile = generate_grid_intensity_profile(grid_type)
        pricing_profile = generate_pricing_profile(pricing_type)

        try:
            result = optimize_charging_schedule(
                battery_capacity_kwh=battery_capacity,
                current_soc_pct=current_soc,
                target_soc_pct=target_soc,
                charging_rate_kw=charging_rate,
                grid_profile=grid_profile,
                pricing_profile=pricing_profile,
            )

            # Save to database
            save_ev_charging_session(
                battery_capacity,
                current_soc,
                target_soc,
                charging_rate,
                result["optimal_carbon_kg"],
                result["carbon_savings_kg"],
                result["cost_savings_usd"],
            )

            st.success("Optimization complete and session saved!")

            # --- Metrics Display ---
            col1, col2, col3 = st.columns(3)
            col1.metric("Energy Needed", f"{result['energy_needed_kwh']} kWh")
            col2.metric(
                "Carbon Savings",
                format_co2(result["carbon_savings_kg"]),
                delta=f"-{result['carbon_savings_kg']} kg",
            )
            col3.metric(
                "Cost Savings",
                format_currency(result["cost_savings_usd"]),
                delta=f"-${result['cost_savings_usd']}",
            )

            # --- Chart: Carbon Intensity & Schedule ---
            fig = go.Figure()
            hours = list(range(24))

            fig.add_trace(
                go.Bar(
                    x=hours,
                    y=grid_profile,
                    name="Grid Carbon Intensity (kg/kWh)",
                    marker_color="rgba(100, 100, 100, 0.3)",
                    yaxis="y2",
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=hours,
                    y=result["schedule"],
                    name="Charging Schedule (kW)",
                    mode="lines+markers",
                    line={"color": "#2ca02c", "width": 3},
                    marker={"size": 8},
                )
            )

            fig.update_layout(
                title="Optimal Charging Schedule vs Grid Carbon Intensity",
                xaxis_title="Hour of Day",
                yaxis_title="Charging Power (kW)",
                yaxis2={
                    "title": "Carbon Intensity (kg CO2e/kWh)",
                    "overlaying": "y",
                    "side": "right",
                },
                legend={
                    "orientation": "h",
                    "yanchor": "bottom",
                    "y": 1.02,
                    "xanchor": "right",
                    "x": 1,
                },
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- Recommendations ---
            st.subheader("💡 Smart Charging Recommendations")
            for rec in generate_charging_recommendations(result):
                st.markdown(f"- {rec}")

        except ValueError as e:
            st.error(f"Configuration Error: {e}")
