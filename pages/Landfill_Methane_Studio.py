"""
Streamlit Page for Enterprise Landfill Methane Recovery & Telemetry Studio
"""

import streamlit as st
from src.environment.landfill_methane_engine import LandfillMethaneEngine, GasWellheadSensor

st.set_page_config(
    page_title="Landfill Methane Recovery Studio",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Enterprise Landfill Methane Emissions & Energy Recovery Studio")
st.caption("Fugitive CH4 emissions tracking, gas wellhead vacuum tuning, and Renewable Natural Gas (RNG) pipeline injection telemetry.")

if "methane_engine" not in st.session_state:
    st.session_state.methane_engine = LandfillMethaneEngine()

engine: LandfillMethaneEngine = st.session_state.methane_engine

facilities = list(engine.facilities.values())

c1, c2, c3, c4 = st.columns(4)

total_waste = sum(f.waste_in_place_metric_tons for f in facilities)
total_rng = sum(f.rng_production_mcf_day for f in facilities)
total_mmbtu = sum(engine.calculate_rng_energy_equivalent_mmbtu(f.rng_production_mcf_day) for f in facilities)
total_credits = sum(f.carbon_credits_generated_usd for f in facilities)

c1.metric("Waste in Place", f"{total_waste / 1000000:.2f}M Metric Tons", "EPA Subpart HH")
c2.metric("Pipeline RNG Output", f"{total_rng:,.0f} MCF/day", f"{total_mmbtu:,.0f} MMBtu/day")
c3.metric("RNG & Carbon Credit Value", f"${total_credits:,.2f}", "RINs & Offset Credits")
c4.metric("Active Wellhead Sensors", f"{sum(len(f.wellheads) for f in facilities)} Wells", "Real-Time Telemetry")

st.markdown("---")

st.subheader("🌐 Audited Landfill Gas Recovery Facilities")

for fac in facilities:
    with st.expander(f"🔥 {fac.facility_name} ({fac.facility_id}) - {fac.location}"):
        st.write(f"**Landfill Area:** {fac.total_landfill_area_acres} Acres | **Waste in Place:** {fac.waste_in_place_metric_tons:,.0f} Metric Tons")
        st.write(f"**Fugitive Emissions:** {fac.ch4_fugitive_emissions_kg_hr} kg CH4/hr | **Flared Volume:** {fac.flared_ch4_volume_cfm} CFM")
        st.write(f"**Carbon Credit Revenue:** ${fac.carbon_credits_generated_usd:,.2f}")

        st.markdown("#### Wellhead Sensor Telemetry Matrix")
        for well in fac.wellheads:
            status_color = "🟢 OPTIMAL" if well.well_status == "OPTIMAL_EXTRACTION" else "⚠️ ALERT"
            st.info(
                f"• **{well.well_name}** ({well.well_id}) - Status: `{status_color}` | "
                f"CH4: {well.methane_concentration_pct}% | CO2: {well.carbon_dioxide_pct}% | O2: {well.oxygen_pct}% | "
                f"Flow: {well.flow_rate_cfm} CFM | Vacuum: {well.vacuum_pressure_inches_wcat} in. W.C."
            )

st.markdown("---")
st.subheader("➕ Register Landfill Wellhead Cluster")

with st.form("new_landfill_form"):
    l_id = st.text_input("Facility ID", value="LF-CH4-402")
    l_name = st.text_input("Facility Name", value="Cascade Mountain EcoLandfill RNG Center")
    l_loc = st.text_input("Location", value="Portland, Oregon")
    l_acres = st.number_input("Area (Acres)", value=310.0)
    l_waste = st.number_input("Waste in Place (Metric Tons)", value=8500000.0)

    submitted = st.form_submit_button("Register Facility to RNG Telemetry Network")

    if submitted:
        w = GasWellheadSensor(
            well_id="WELL-NEW-01",
            well_name="Cluster 1 Extraction Wellhead",
            methane_concentration_pct=57.0,
            carbon_dioxide_pct=40.0,
            oxygen_pct=0.3,
            flow_rate_cfm=180.0,
            vacuum_pressure_inches_wcat=-14.0,
            temperature_celsius=37.0,
            well_status="OPTIMAL_EXTRACTION"
        )
        engine.register_landfill_facility(l_id, l_name, l_loc, l_acres, l_waste, [w])
        st.success(f"Landfill {l_name} registered and connected to RNG grid telemetry!")
        st.rerun()
