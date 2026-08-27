"""
Streamlit Page for Enterprise Smart Grid EV V2G Optimization Studio
"""

import streamlit as st
from src.energy.smart_grid_ev_v2g_engine import SmartGridEvV2gEngine, EvChargerAsset

st.set_page_config(
    page_title="Smart Grid EV V2G Studio",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Enterprise Smart Grid EV V2G Optimization Studio")
st.caption("Bidirectional Vehicle-to-Grid (V2G) fleet dispatch, ISO 15118 smart charging, and frequency response monetization.")

if "v2g_engine" not in st.session_state:
    st.session_state.v2g_engine = SmartGridEvV2gEngine()

engine: SmartGridEvV2gEngine = st.session_state.v2g_engine

depots = list(engine.depots.values())

c1, c2, c3, c4 = st.columns(4)

total_chargers = sum(len(d.chargers) for d in depots)
total_v2g_discharging = sum(sum(c.grid_feedin_rate_kw for c in d.chargers if c.v2g_mode_active) for d in depots)
total_revenue = sum(sum(c.revenue_earned_usd for c in d.chargers) for d in depots)
total_emissions_avoided = sum(d.carbon_emissions_avoided_kg for d in depots)

c1.metric("Active V2G Chargers", f"{total_chargers} Stations", "ISO 15118 Active")
c2.metric("V2G Feed-in Output", f"{total_v2g_discharging:.1f} kW", "Grid Stabilizing")
c3.metric("Grid Arbitrage Revenue", f"${total_revenue:,.2f}", "Peak Pricing Offset")
c4.metric("CO2 Emissions Avoided", f"{total_emissions_avoided:,.0f} kg", "-34% Fleet Carbon")

st.markdown("---")

st.subheader("⚡ Fleet Depot Grid Hub Telemetry")

for d in depots:
    with st.expander(f"🏢 {d.hub_name} ({d.hub_id}) - {d.location}"):
        st.write(f"**Grid Operator:** `{d.grid_operator}` | **Transformer Rating:** {d.transformer_capacity_kva} kVA")
        st.write(f"**Total V2G Discharge:** {d.total_v2g_discharge_kwh} kWh | **Carbon Avoided:** {d.carbon_emissions_avoided_kg} kg")
        
        st.markdown("#### Connected Fleet Chargers")
        for chg in d.chargers:
            v2g_badge = "🟢 V2G DISCHARGING" if chg.v2g_mode_active else "⚡ CHARGING ONLY"
            st.info(
                f"• **{chg.station_name}** [{chg.charger_type}] - Mode: `{v2g_badge}` | "
                f"EV VIN: `{chg.connected_ev_vin}` | Battery SoC: {chg.ev_state_of_charge_pct}% (Target: {chg.target_soc_pct}%) | "
                f"Grid Feed-in: {chg.grid_feedin_rate_kw} kW | Revenue: ${chg.revenue_earned_usd:.2f}"
            )

st.markdown("---")
st.subheader("➕ Register New V2G Fleet Depot Hub")

with st.form("new_v2g_depot_form"):
    h_id = st.text_input("Depot Hub ID", value="HUB-V2G-802")
    h_name = st.text_input("Hub Name", value="Seattle EV Bus & Truck Logistics Hub")
    h_loc = st.text_input("Location", value="Seattle, Washington")
    grid_op = st.text_input("Grid Operator", value="Seattle City Light")
    trans_rating = st.number_input("Transformer Capacity (kVA)", value=3500.0)

    submitted = st.form_submit_button("Register Fleet Hub to V2G Smart Grid")

    if submitted:
        chg = EvChargerAsset(
            charger_id="V2G-CHG-NEW",
            station_name="Seattle Bay 1 (DC Fast V2G)",
            charger_type="DC_FAST_V2G",
            connector_standard="CCS2_ISO15118",
            power_rating_kw=200.0,
            current_power_kw=150.0,
            connected_ev_vin="1FTVW1EL9PW091234",
            ev_battery_capacity_kwh=140.0,
            ev_state_of_charge_pct=90.0,
            target_soc_pct=85.0,
            v2g_mode_active=True,
            grid_feedin_rate_kw=100.0,
            revenue_earned_usd=65.0
        )
        engine.register_depot_hub(h_id, h_name, h_loc, grid_op, trans_rating, [chg])
        st.success(f"Hub {h_name} registered and synced to V2G smart grid network!")
        st.rerun()
