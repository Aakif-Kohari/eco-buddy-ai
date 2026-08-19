"""
Streamlit UI Page for Microgrid & Battery Storage Simulator
"""

import streamlit as st
from src.lib.microgrid_simulator import MicrogridStorageSimulator, BATTERY_CHEMISTRIES

def render_microgrid_page():
    st.set_page_config(page_title="Microgrid & BESS Simulator", page_icon="🔋", layout="wide")
    st.title("🔋 Microgrid & Battery Energy Storage (BESS) Simulator")
    st.markdown("Simulate solar photovoltaic + battery storage dispatch dynamics, calculate peak tariff arbitrage savings, and quantify localized carbon avoidance.")

    simulator = MicrogridStorageSimulator()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("System Sizing")
        solar_kw = st.number_input("Solar PV Array Capacity (kWp)", min_value=1.0, max_value=500.0, value=6.5, step=0.5)
        battery_kwh = st.number_input("Battery Storage Capacity (kWh)", min_value=0.0, max_value=1000.0, value=13.5, step=1.0)
        daily_load_kwh = st.number_input("Average Daily Household / Facility Load (kWh)", min_value=1.0, max_value=2000.0, value=22.0, step=1.0)

    with col2:
        st.subheader("Tariff & Grid Parameters")
        chem_options = list(BATTERY_CHEMISTRIES.keys())
        chem_choice = st.selectbox("Battery Chemistry", chem_options, format_func=lambda k: BATTERY_CHEMISTRIES[k]["name"])
        peak_rate = st.number_input("Peak Tariff Rate ($/kWh)", min_value=0.05, max_value=2.0, value=0.38, step=0.01)
        offpeak_rate = st.number_input("Off-Peak Tariff Rate ($/kWh)", min_value=0.01, max_value=1.0, value=0.14, step=0.01)
        grid_co2 = st.number_input("Regional Grid Carbon Intensity (gCO2/kWh)", min_value=10.0, max_value=1200.0, value=480.0, step=10.0)

    if st.button("Simulate 24-Hour Dispatch & Financials", type="primary"):
        res = simulator.simulate_daily_dispatch(
            solar_capacity_kw=solar_kw,
            battery_capacity_kwh=battery_kwh,
            daily_consumption_kwh=daily_load_kwh,
            battery_chemistry=chem_choice,
            grid_peak_rate_usd=peak_rate,
            grid_offpeak_rate_usd=offpeak_rate,
            grid_carbon_intensity_gco2=grid_co2
        )

        st.subheader("Simulation Results & Energy Balance")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Self-Sufficiency", f"{res['self_sufficiency_pct']}%")
        m2.metric("Annual Utility Savings", f"${res['annual_financial_savings_usd']:,}")
        m3.metric("Annual Carbon Abatement", f"{res['annual_carbon_abatement_kg']} kg CO₂")
        m4.metric("Estimated Lifespan", f"{res['expected_battery_lifespan_years']} Years")

        st.markdown(f"""
        - **Daily Solar Generation:** `{res['daily_solar_gen_kwh']} kWh`
        - **Direct Solar Self-Consumed:** `{res['direct_solar_consumed_kwh']} kWh`
        - **Energy Stored & Discharged through BESS:** `{res['battery_discharged_kwh']} kWh`
        - **Remaining Grid Import Requirement:** `{res['remaining_grid_demand_kwh']} kWh / day`
        """)

if __name__ == "__main__":
    render_microgrid_page()
