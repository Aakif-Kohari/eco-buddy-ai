"""
Simulator UI Components.

Streamlit widgets for the Decision Simulator.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from src.decision_engine.models import (
    ScenarioInputs, TransportMode, EnergySource, DietType, SimulationResult
)

def render_inputs_form(key_prefix: str, defaults: ScenarioInputs) -> ScenarioInputs:
    """Renders the comprehensive form to edit scenario inputs."""
    st.markdown("### 🚗 Transport")
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        primary_mode = st.selectbox(
            "Primary Transport Mode", 
            [m.value for m in TransportMode], 
            index=[m.value for m in TransportMode].index(defaults.transport.primary_mode),
            key=f"{key_prefix}_t_mode"
        )
        weekly_commute = st.number_input("Weekly Commute (km)", value=float(defaults.transport.weekly_commute_km), key=f"{key_prefix}_t_commute")
        weekend_travel = st.number_input("Weekend Travel (km/week)", value=float(defaults.transport.weekend_travel_km), key=f"{key_prefix}_t_weekend")
        flights = st.number_input("Flights per year", value=int(defaults.transport.flights_per_year), key=f"{key_prefix}_t_flights")
    with t_col2:
        car_eff = st.number_input("Car Efficiency (MPG)", value=float(defaults.transport.car_efficiency_mpg), key=f"{key_prefix}_t_mpg")
        ev_eff = st.number_input("EV Efficiency (kWh/100km)", value=float(defaults.transport.ev_efficiency_kwh_per_100km), key=f"{key_prefix}_t_ev")
        telecommute = st.number_input("Telecommute Days/Week", value=int(defaults.transport.telecommute_days_per_week), max_value=7, key=f"{key_prefix}_t_tele")
        maint_cost = st.number_input("Annual Maintenance ($)", value=float(defaults.transport.annual_maintenance_cost), key=f"{key_prefix}_t_maint")
        
    st.markdown("### ⚡ Energy")
    e_col1, e_col2 = st.columns(2)
    with e_col1:
        energy_source = st.selectbox(
            "Primary Energy Source", 
            [e.value for e in EnergySource], 
            index=[e.value for e in EnergySource].index(defaults.energy.primary_source),
            key=f"{key_prefix}_e_source"
        )
        elec_kwh = st.number_input("Monthly Electricity (kWh)", value=float(defaults.energy.monthly_electricity_kwh), key=f"{key_prefix}_e_elec")
        gas_therms = st.number_input("Monthly Gas (therms)", value=float(defaults.energy.monthly_gas_therms), key=f"{key_prefix}_e_gas")
    with e_col2:
        smart_thermostat = st.checkbox("Has Smart Thermostat", value=defaults.energy.has_smart_thermostat, key=f"{key_prefix}_e_smart")
        led_pct = st.slider("LED Lighting %", 0.0, 100.0, value=float(defaults.energy.led_lighting_percentage), key=f"{key_prefix}_e_led")
        solar_kw = st.number_input("Solar Capacity (kW)", value=float(defaults.energy.solar_capacity_kw), key=f"{key_prefix}_e_solar")

    st.markdown("### 🥗 Food")
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        diet = st.selectbox(
            "Diet Type", 
            [d.value for d in DietType], 
            index=[d.value for d in DietType].index(defaults.food.diet_type),
            key=f"{key_prefix}_f_diet"
        )
        food_waste = st.slider("Food Waste %", 0.0, 100.0, value=float(defaults.food.food_waste_percentage), key=f"{key_prefix}_f_waste")
    with f_col2:
        compost = st.checkbox("Composting Enabled", value=defaults.food.composting_enabled, key=f"{key_prefix}_f_compost")
        dining_out = st.number_input("Dining Out (times/week)", value=int(defaults.food.dining_out_frequency_per_week), key=f"{key_prefix}_f_dining")
        grocery_budget = st.number_input("Monthly Grocery Budget ($)", value=float(defaults.food.grocery_budget_monthly), key=f"{key_prefix}_f_grocery")
        
    st.markdown("### 🗑️ Waste & 💧 Water")
    w_col1, w_col2 = st.columns(2)
    with w_col1:
        trash_bags = st.number_input("Weekly Trash Bags", value=float(defaults.waste.weekly_trash_bags), key=f"{key_prefix}_w_trash")
        recycling = st.slider("Recycling Rate %", 0.0, 100.0, value=float(defaults.waste.recycling_rate_percentage), key=f"{key_prefix}_w_recyc")
    with w_col2:
        showers = st.number_input("Average Shower (minutes)", value=float(defaults.water.shower_duration_minutes), key=f"{key_prefix}_w_shower")
        low_flow = st.checkbox("Low-Flow Fixtures", value=defaults.water.low_flow_fixtures_installed, key=f"{key_prefix}_w_lowflow")

    # Reconstruct modified inputs
    defaults.transport.primary_mode = TransportMode(primary_mode)
    defaults.transport.weekly_commute_km = weekly_commute
    defaults.transport.weekend_travel_km = weekend_travel
    defaults.transport.flights_per_year = flights
    defaults.transport.car_efficiency_mpg = car_eff
    defaults.transport.ev_efficiency_kwh_per_100km = ev_eff
    defaults.transport.telecommute_days_per_week = telecommute
    defaults.transport.annual_maintenance_cost = maint_cost
    
    defaults.energy.primary_source = EnergySource(energy_source)
    defaults.energy.monthly_electricity_kwh = elec_kwh
    defaults.energy.monthly_gas_therms = gas_therms
    defaults.energy.has_smart_thermostat = smart_thermostat
    defaults.energy.led_lighting_percentage = led_pct
    defaults.energy.solar_capacity_kw = solar_kw
    
    defaults.food.diet_type = DietType(diet)
    defaults.food.food_waste_percentage = food_waste
    defaults.food.composting_enabled = compost
    defaults.food.dining_out_frequency_per_week = dining_out
    defaults.food.grocery_budget_monthly = grocery_budget
    
    defaults.waste.weekly_trash_bags = trash_bags
    defaults.waste.recycling_rate_percentage = recycling
    
    defaults.water.shower_duration_minutes = showers
    defaults.water.low_flow_fixtures_installed = low_flow
    
    return defaults

def render_simulation_dashboard(result: SimulationResult):
    """Renders the charts and comparisons for the simulation result."""
    
    # 1. Environmental Comparison Chart
    st.subheader("🌍 Environmental Impact Comparison (kg CO2e/yr)")
    
    co2_data = []
    scenarios = [result.baseline] + result.alternatives
    for s in scenarios:
        env = s.environmental_impact
        co2_data.append({
            "Scenario": s.name,
            "Transport": env.transport_co2e,
            "Energy": env.energy_co2e,
            "Food": env.food_co2e,
            "Waste": env.waste_co2e
        })
    df_co2 = pd.DataFrame(co2_data).set_index("Scenario")
    st.bar_chart(df_co2)
    
    # 2. Financial Comparison
    st.subheader("💰 Financial Analysis")
    fin_col1, fin_col2 = st.columns(2)
    
    with fin_col1:
        cost_data = [{"Scenario": s.name, "Yearly Cost ($)": s.financial_impact.yearly_recurring_cost} for s in scenarios]
        st.dataframe(pd.DataFrame(cost_data), use_container_width=True)
        
    with fin_col2:
        upfront_data = [{"Scenario": s.name, "Implementation Cost ($)": s.financial_impact.implementation_cost_upfront} for s in scenarios]
        st.dataframe(pd.DataFrame(upfront_data), use_container_width=True)
        
    # 3. Time Horizon Projections (Cumulative Cost vs Savings)
    st.subheader("📈 10-Year Trajectory (Cumulative Cost)")
    proj_data = {"Months": [1, 6, 12, 60, 120]}
    for s in scenarios:
        proj_data[s.name] = [s.projections[m].cumulative_cost for m in proj_data["Months"]]
        
    df_proj = pd.DataFrame(proj_data).set_index("Months")
    st.line_chart(df_proj)
    
    # 4. Trade-Offs
    st.subheader("⚖️ Trade-Offs Detected")
    has_tradeoffs = False
    for alt_id, tradeoffs in result.trade_offs.items():
        if tradeoffs:
            has_tradeoffs = True
            st.markdown(f"**For {alt_id}:**")
            for t in tradeoffs:
                color = "red" if t.severity == "high" else "orange" if t.severity == "medium" else "blue"
                st.markdown(f"- :{color}[{t.category}]: {t.description}")
                
    if not has_tradeoffs:
        st.success("No negative trade-offs detected! These alternatives are strict upgrades.")
        
    # 5. Rankings & Recommendations
    st.subheader("🏆 Scenario Rankings")
    
    rank_col1, rank_col2, rank_col3 = st.columns(3)
    with rank_col1:
        st.metric("Lowest Carbon", result.rankings["lowest_carbon"][0])
    with rank_col2:
        st.metric("Lowest Recurring Cost", result.rankings["lowest_cost"][0])
    with rank_col3:
        st.metric("Highest Sustainability Score", result.rankings["highest_sustainability_score"][0])
        
    st.subheader("💡 Recommendations")
    for rec in result.recommendations:
        st.info(rec)
