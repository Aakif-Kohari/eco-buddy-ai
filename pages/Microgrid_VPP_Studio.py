"""
Streamlit Interface for Enterprise Microgrid & Virtual Power Plant (VPP) Dispatch Suite
"""

import streamlit as st
from src.energy.microgrid_vpp_engine import MicrogridVppEngine, DistributedEnergyResource

st.set_page_config(
    page_title="Microgrid & VPP Dispatch Studio",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Enterprise Microgrid & Virtual Power Plant (VPP) Dispatch Studio")
st.caption("Real-time distributed energy resource (DER) telemetry, battery storage dispatch, and peak shaving optimization.")

if "vpp_engine" not in st.session_state:
    st.session_state.vpp_engine = MicrogridVppEngine()

engine: MicrogridVppEngine = st.session_state.vpp_engine

facilities = list(engine.facilities.values())

col1, col2, col3, col4 = st.columns(4)

total_cap = sum(f.total_capacity_kw for f in facilities)
total_load = sum(f.current_load_kw for f in facilities)
avg_ren = sum(f.renewable_fraction_pct for f in facilities) / len(facilities) if facilities else 0.0
total_savings = sum(f.peak_shaving_savings_usd for f in facilities)

col1.metric("Total VPP Capacity", f"{total_cap:.0f} kW", "Grid Stabilized")
col2.metric("Current Campus Load", f"{total_load:.0f} kW", "Peak Shaved")
col3.metric("Renewable Energy Fraction", f"{avg_ren:.1f}%", "+12.4% vs Grid")
col4.metric("Demand Charge Savings", f"${total_savings:,.2f}", "Monthly Offset")

st.markdown("---")

st.subheader("🌐 Active Distributed Microgrid Facilities")

for fac in facilities:
    with st.expander(f"⚡ {fac.facility_name} ({fac.microgrid_id}) - {fac.location}"):
        st.write(f"**Grid Status:** `{fac.grid_connection_status}` | **Capacity:** {fac.total_capacity_kw} kW | **Load:** {fac.current_load_kw} kW")
        st.write(f"**Renewable Mix:** {fac.renewable_fraction_pct}% | **Peak Shaving Savings:** ${fac.peak_shaving_savings_usd:,.2f}")
        
        st.markdown("#### Distributed Energy Resources (DERs)")
        for asset in fac.assets:
            st.success(
                f"🔌 **{asset.asset_name}** [{asset.asset_type}] - Status: `{asset.operating_status}` | "
                f"Output: {asset.current_output_kw}/{asset.capacity_kw} kW | SoC: {asset.state_of_charge_pct}% | "
                f"Carbon Offset: {asset.carbon_offset_kg_per_hr} kg/hr"
            )

st.markdown("---")
st.subheader("➕ Register New Microgrid Facility")

with st.form("register_microgrid_form"):
    m_id = st.text_input("Microgrid Facility ID", value="GRID-VPP-702")
    m_name = st.text_input("Facility Name", value="Silicon Valley AI Data Center Microgrid")
    location = st.text_input("Location", value="Santa Clara, California")
    load_kw = st.number_input("Peak Load (kW)", value=3200.0, min_value=100.0)

    st.markdown("##### Battery Asset (BESS)")
    bess_cap = st.number_input("BESS Capacity (kW)", value=2000.0)
    bess_out = st.number_input("BESS Active Output (kW)", value=1500.0)

    submitted = st.form_submit_button("Register & Connect Microgrid to VPP Network")

    if submitted:
        der = DistributedEnergyResource(
            asset_id="DER-BESS-NEW",
            asset_name="Enterprise Megapack",
            asset_type="BESS",
            capacity_kw=bess_cap,
            current_output_kw=bess_out,
            state_of_charge_pct=90.0,
            operating_status="DISPATCHING",
            carbon_offset_kg_per_hr=500.0
        )
        engine.register_facility_profile(m_id, m_name, location, load_kw, [der])
        st.success(f"Facility {m_name} registered and connected to VPP dispatch grid!")
        st.rerun()
