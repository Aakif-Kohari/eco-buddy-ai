"""
Water-Energy Nexus Dashboard.
Streamlit page featuring an interactive dashboard showing the nexus breakdown and greywater simulation results.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from water_energy_nexus import WaterEnergyNexus
from greywater_simulator import GreywaterSimulator
from database import save_water_energy_profile

st.set_page_config(page_title="Water-Energy Nexus", page_icon="💧", layout="wide")

st.title("💧 Household Water-Energy Nexus & Greywater Simulator")
st.markdown(
    "Quantify the hidden energy costs of your water usage and simulate the dual savings of greywater recycling."
)

# --- Sidebar Configuration ---
st.sidebar.header("⚙️ Household Settings")
household_size = st.sidebar.number_input(
    "Household Size", min_value=1, max_value=10, value=3
)
grid_intensity = st.sidebar.slider(
    "Grid Carbon Intensity (kg CO₂e/kWh)", 0.1, 1.0, 0.4, step=0.05
)

# --- Main Dashboard ---
tab1, tab2 = st.tabs(["🚿 Daily Water-Energy Nexus", "♻️ Greywater Recycling Simulator"])

with tab1:
    st.subheader("Calculate the Hidden Energy Cost of Water")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Baseline Scenario")
        base_volume = st.number_input(
            "Daily Water Volume (Liters)", min_value=10, value=150, key="base_vol"
        )
        base_temp = st.slider(
            "Average Water Temperature (°C)", 15, 60, 40, key="base_temp"
        )
        is_hot = st.checkbox("Is this primarily hot water?", value=True, key="base_hot")

    with col2:
        st.markdown("#### Optimized Scenario")
        opt_volume = st.number_input(
            "Optimized Daily Volume (Liters)", min_value=10, value=100, key="opt_vol"
        )
        opt_temp = st.slider(
            "Optimized Water Temperature (°C)", 15, 60, 35, key="opt_temp"
        )

    if st.button("🔍 Compare Scenarios"):
        nexus = WaterEnergyNexus(grid_carbon_intensity=grid_intensity)
        comparison = nexus.compare_nexus_scenarios(
            base_volume, base_temp, opt_volume, opt_temp
        )

        st.session_state.nexus_comparison = comparison
        save_water_energy_profile(household_size, grid_intensity, comparison)
        st.success("Nexus analysis complete and saved!")

    if "nexus_comparison" in st.session_state:
        comp = st.session_state.nexus_comparison

        st.divider()
        st.subheader("📊 Impact Comparison")
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric(
            "Water Saved",
            f"{comp['water_saved_liters']} L/day",
            delta=f"-{comp['water_saved_liters']} L",
        )
        res_col2.metric(
            "Energy Saved",
            f"{comp['energy_saved_kwh']} kWh/day",
            delta=f"-{comp['energy_saved_kwh']} kWh",
        )
        res_col3.metric(
            "Carbon Saved",
            f"{comp['carbon_saved_kg']} kg CO₂e/day",
            delta=f"-{comp['carbon_saved_kg']} kg",
        )

        # Breakdown Chart
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                name="Baseline",
                x=["Treatment Energy", "Heating Energy"],
                y=[
                    comp["baseline"]["treatment_energy_kwh"],
                    comp["baseline"]["heating_energy_kwh"],
                ],
                marker_color="#1f77b4",
            )
        )
        fig.add_trace(
            go.Bar(
                name="Optimized",
                x=["Treatment Energy", "Heating Energy"],
                y=[
                    comp["optimized"]["treatment_energy_kwh"],
                    comp["optimized"]["heating_energy_kwh"],
                ],
                marker_color="#2ca02c",
            )
        )

        fig.update_layout(
            title="Daily Energy Breakdown (kWh)",
            barmode="group",
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Simulate Greywater Recycling Potential")
    st.markdown(
        "Estimate how much water and energy your household could save by redirecting shower, sink, and laundry water to toilets and gardens."
    )

    efficiency = st.slider(
        "System Capture Efficiency (%)",
        50,
        95,
        80,
        help="Real-world systems lose some water to filtration and evaporation.",
    )

    if st.button("♻️ Run Greywater Simulation"):
        simulator = GreywaterSimulator(
            household_size=household_size, grid_carbon_intensity=grid_intensity
        )
        results = simulator.simulate_recycling_savings(reuse_efficiency_pct=efficiency)
        st.session_state.greywater_results = results

    if "greywater_results" in st.session_state:
        res = st.session_state.greywater_results

        st.divider()
        gw_col1, gw_col2 = st.columns(2)

        with gw_col1:
            st.metric(
                "Daily Water Reused", f"{res['daily_water_reused_liters']} Liters"
            )
            st.metric(
                "Annual Water Saved", f"{res['annual_water_saved_liters']:,.0f} Liters"
            )

        with gw_col2:
            st.metric("Daily Energy Saved", f"{res['daily_energy_saved_kwh']} kWh")
            st.metric(
                "Annual Carbon Saved", f"{res['annual_carbon_saved_kg']:,.2f} kg CO₂e"
            )

        st.info(
            f"💡 **Insight:** For a {household_size}-person household, a greywater system can offset up to **{res['daily_water_reused_liters']} liters** of municipal water demand daily, simultaneously reducing the energy needed for water treatment and heating."
        )
