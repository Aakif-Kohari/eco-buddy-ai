"""
Streamlit UI Page for Urban Heat Island & Tree Canopy Planner
"""

import streamlit as st
from src.lib.uhi_planner import UrbanHeatIslandPlanner, SURFACE_ALBEDO_PROPERTIES

def render_uhi_page():
    st.set_page_config(page_title="Urban Heat Island Planner", page_icon="🌳", layout="wide")
    st.title("🌳 Urban Heat Island & Tree Canopy Microclimate Planner")
    st.markdown("Quantify urban microclimate cooling, evaluate biospheric canopy expansion benefits, and project district-level HVAC energy savings and stormwater interception.")

    planner = UrbanHeatIslandPlanner()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Neighborhood / Campus Metrics")
        area_sqm = st.number_input("Study District Area (m²)", min_value=1000.0, max_value=10000000.0, value=50000.0, step=5000.0)
        impervious_pct = st.slider("Impervious Paved Surface (%)", min_value=10, max_value=95, value=65)
        current_canopy_pct = st.slider("Baseline Tree Canopy Coverage (%)", min_value=2, max_value=50, value=12)

    with col2:
        st.subheader("Intervention & Environmental Baseline")
        added_canopy_pct = st.slider("Proposed Added Canopy Coverage (%)", min_value=1, max_value=40, value=15)
        baseline_temp = st.number_input("Summer Peak Ambient Temperature (°C)", min_value=20.0, max_value=50.0, value=35.0, step=0.5)

    if st.button("Model Microclimate Cooling & Ecosystem Services", type="primary"):
        res = planner.calculate_microclimate_cooling(
            district_area_sqm=area_sqm,
            impervious_pct=impervious_pct,
            current_canopy_pct=current_canopy_pct,
            proposed_canopy_addition_pct=added_canopy_pct,
            baseline_ambient_temp_c=baseline_temp
        )

        st.subheader("Projected Microclimate Improvements")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Temperature", f"{res['current_district_temp_c']} °C")
        m2.metric("Projected Temperature", f"{res['projected_district_temp_c']} °C", f"-{res['ambient_cooling_delta_c']} °C")
        m3.metric("HVAC Electricity Saved", f"-{res['hvac_energy_savings_pct']}%")
        m4.metric("Trees Added", f"{res['estimated_trees_planted']:,}")

        st.markdown(f"""
        - **Annual Direct Carbon Sequestration:** `{res['annual_co2_sequestered_kg']:,} kg CO₂/year`
        - **Annual Stormwater Interception Capacity:** `{res['stormwater_interception_m3_yr']:,} m³/year`
        """)

if __name__ == "__main__":
    render_uhi_page()
