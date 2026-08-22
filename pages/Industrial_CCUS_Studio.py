"""
Streamlit Page for Enterprise Industrial CCUS & Carbon Sequestration Studio
"""

import streamlit as st
from industrial_ccus_engine import IndustrialCcusEngine, CcusCaptureUnit

st.set_page_config(
    page_title="Industrial CCUS Studio",
    page_icon="🏭",
    layout="wide"
)

st.title("🏭 Enterprise Industrial Carbon Capture, Utilization & Storage (CCUS) Studio")
st.caption("Flue gas CO2 absorption telemetry, Direct Air Capture (DAC) monitoring, and Section 45Q carbon credit tracking.")

if "ccus_engine" not in st.session_state:
    st.session_state.ccus_engine = IndustrialCcusEngine()

engine: IndustrialCcusEngine = st.session_state.ccus_engine

facilities = list(engine.facilities.values())

c1, c2, c3, c4 = st.columns(4)

total_gross = sum(f.annual_gross_emissions_tons for f in facilities)
total_captured = sum(f.annual_net_captured_tons for f in facilities)
total_offset = sum(f.net_carbon_tax_offset_usd for f in facilities)
avg_abatement = (total_captured / total_gross * 100.0) if total_gross > 0 else 0.0

c1.metric("Gross Industrial Emissions", f"{total_gross:,.0f} Tons/yr", "Monitored")
c2.metric("Net CO2 Captured & Stored", f"{total_captured:,.0f} Tons/yr", f"{avg_abatement:.1f}% Abated")
c3.metric("Section 45Q Carbon Offset", f"${total_offset:,.2f}", "Tax Credit Eligible")
c4.metric("Audited CCUS Plants", f"{len(facilities)} Facilities", "EPA Class VI Verified")

st.markdown("---")

st.subheader("📊 Industrial Plant Capture & Sequestration Telemetry")

for plant in facilities:
    with st.expander(f"🏭 {plant.facility_name} ({plant.facility_id}) - {plant.industry_sector}"):
        st.write(f"**Location:** {plant.location} | **Sequestration Method:** `{plant.sequestration_method}`")
        st.write(f"**Annual Gross:** {plant.annual_gross_emissions_tons:,.0f} Tons | **Captured:** {plant.annual_net_captured_tons:,.0f} Tons")
        st.write(f"**Net Tax Credit Offset:** ${plant.net_carbon_tax_offset_usd:,.2f}")
        
        st.markdown("#### Operational Capture Units")
        for unit in plant.units:
            st.info(
                f"• **{unit.unit_name}** [{unit.technology_type}] - Status: `{unit.operating_status}` | "
                f"Flue Gas Flow: {unit.flue_gas_flow_rate_m3_hr:,.0f} m³/hr | CO2 Conc: {unit.co2_concentration_pct}% | "
                f"Daily Capture: {unit.daily_co2_captured_metric_tons} Metric Tons | Efficiency: {unit.capture_efficiency_pct}%"
            )

st.markdown("---")
st.subheader("➕ Register Industrial Plant CCUS Unit")

with st.form("new_ccus_facility_form"):
    f_id = st.text_input("Facility ID", value="PLANT-CCUS-902")
    f_name = st.text_input("Facility Name", value="Gulf Coast Steel Decarbonization Hub")
    sector = st.selectbox("Industry Sector", ["STEEL_PRODUCTION", "CEMENT_MANUFACTURING", "CHEMICAL_REFINERY", "POWER_GENERATION"])
    loc = st.text_input("Location", value="Baton Rouge, Louisiana")
    gross_emissions = st.number_input("Gross Annual Emissions (Tons)", value=650000.0)

    submitted = st.form_submit_button("Register Facility to Industrial CCUS Grid")

    if submitted:
        unit = CcusCaptureUnit(
            unit_id="CCUS-UNIT-NEW",
            unit_name="Direct Air Capture (DAC) Module B",
            technology_type="DIRECT_AIR_CAPTURE_DAC",
            flue_gas_flow_rate_m3_hr=500000.0,
            co2_concentration_pct=0.04,
            capture_efficiency_pct=90.0,
            daily_co2_captured_metric_tons=300.0,
            parasitic_energy_penalty_mwh_per_ton=2.0,
            solvent_degradation_rate_ppm=0.2,
            operating_status="OPTIMAL_ABSORPTION"
        )
        engine.register_facility_profile(f_id, f_name, sector, loc, gross_emissions, [unit])
        st.success(f"Facility {f_name} registered and synced to CCUS carbon tracking network!")
        st.rerun()
