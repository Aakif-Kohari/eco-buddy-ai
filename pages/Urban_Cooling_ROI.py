"""
Urban Cooling ROI Page.
Streamlit page where users can input property details, compare green infrastructure options, and view long-term ROI charts.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from urban_heat_mitigation import UrbanHeatMitigationCalculator
from green_infrastructure_db import GreenInfrastructureDB
from database import save_urban_cooling_plan, get_urban_cooling_history

st.set_page_config(page_title="Urban Cooling ROI", page_icon="🌳", layout="wide")

st.title("🌳 Hyper-Local Urban Heat Island Mitigation & Green Infrastructure ROI")
st.markdown(
    "Model the temperature reduction and financial returns of adding green infrastructure to your residential or commercial property."
)

db = GreenInfrastructureDB()
options = db.get_all_options()

# --- Input Section ---
st.sidebar.header("🏠 Property Baseline")
baseline_temp = st.sidebar.number_input(
    "Current Summer Avg Temp (°C)", min_value=20.0, max_value=50.0, step=0.5, value=32.0
)
hvac_cost = st.sidebar.number_input(
    "Annual HVAC Cost ($)", min_value=0, step=100, value=1200
)
area = st.sidebar.number_input("Property Area (sqm)", min_value=10, step=10, value=200)

if "calculator" not in st.session_state or st.session_state.get("reset_calc"):
    st.session_state.calculator = UrbanHeatMitigationCalculator(
        baseline_temp, hvac_cost, area
    )
    st.session_state.reset_calc = False

calc = st.session_state.calculator

# --- Add Measure Form ---
st.sidebar.header("➕ Add Green Infrastructure")
with st.sidebar.form("add_measure_form"):
    option = st.selectbox(
        "Measure Type",
        options=options,
        format_func=lambda x: db.get_option_display_name(x),
    )
    quantity = st.number_input(
        "Quantity",
        min_value=1.0,
        step=1.0,
        value=10.0 if "sqm" in db.get_option_details(option)["unit"] else 1.0,
    )

    if st.form_submit_button("Add to Property"):
        calc.add_measure(option, quantity)
        st.sidebar.success("Measure added!")
        st.rerun()

# --- Results Display ---
st.divider()
result = calc.calculate_roi()

st.subheader("📊 Mitigation Impact & Financial ROI")

col1, col2, col3 = st.columns(3)
col1.metric(
    "Projected Temp Reduction",
    f"-{result['total_cooling_effect_c']:.1f} °C",
    delta=f"New Avg: {result['projected_temp_c']:.1f} °C",
)
col2.metric("Annual HVAC Savings", f"${result['annual_hvac_savings_usd']:,.2f}")
col3.metric(
    "20-Year Net Savings",
    f"${result['twenty_year_net_savings_usd']:,.2f}",
    delta_color="normal" if result["twenty_year_net_savings_usd"] > 0 else "inverse",
)

# ROI Bar Chart
st.markdown("### 💰 Long-Term Financial Breakdown")
fig = go.Figure()
fig.add_trace(
    go.Bar(
        name="Upfront Installation Cost",
        x=["20-Year Projection"],
        y=[-result["total_installation_cost_usd"]],
        marker_color="#d62728",
    )
)
fig.add_trace(
    go.Bar(
        name="Cumulative HVAC Savings (20 yrs)",
        x=["20-Year Projection"],
        y=[result["annual_hvac_savings_usd"] * 20],
        marker_color="#2ca02c",
    )
)
fig.add_trace(
    go.Bar(
        name="Cumulative Maintenance (20 yrs)",
        x=["20-Year Projection"],
        y=[-result["total_annual_maintenance_usd"] * 20],
        marker_color="#ff7f0e",
    )
)

fig.update_layout(
    title="20-Year Cash Flow Projection",
    yaxis_title="USD ($)",
    template="plotly_white",
    barmode="relative",  # Stacks positive and negative values
)
st.plotly_chart(fig, use_container_width=True)

# Measure Breakdown Table
st.markdown("### 📋 Installed Measures Breakdown")
if result["measure_breakdown"]:
    df_measures = pd.DataFrame(result["measure_breakdown"])
    df_measures = df_measures[
        [
            "option_name",
            "quantity",
            "unit",
            "cooling_effect_c",
            "installation_cost_usd",
            "annual_maintenance_usd",
        ]
    ]
    df_measures.rename(
        columns={
            "option_name": "Measure",
            "quantity": "Amount",
            "cooling_effect_c": "Cooling (°C)",
            "installation_cost_usd": "Install Cost ($)",
            "annual_maintenance_usd": "Annual Maint. ($)",
        },
        inplace=True,
    )
    st.dataframe(df_measures, use_container_width=True, hide_index=True)
else:
    st.info("No measures added yet. Use the sidebar to model different scenarios.")

# Payback Info
st.divider()
col_a, col_b = st.columns(2)
with col_a:
    st.metric("Simple Payback Period", f"{result['payback_years']} years")
with col_b:
    if result["twenty_year_net_savings_usd"] > 0:
        st.success(
            "✅ **Positive ROI:** This combination of measures pays for itself and generates net savings over its lifespan."
        )
    else:
        st.warning(
            "⚠️ **Negative ROI:** The upfront costs outweigh the energy savings. Consider focusing on high-impact, low-cost measures like tree planting."
        )

# Save Button
if st.button("💾 Save Mitigation Plan"):
    save_urban_cooling_plan(
        baseline_temp,
        hvac_cost,
        result["total_cooling_effect_c"],
        result["twenty_year_net_savings_usd"],
    )
    st.success("Plan saved to history!")

# --- History ---
st.divider()
st.subheader("📜 Past Mitigation Plans")
history = get_urban_cooling_history()
if history:
    st.dataframe(pd.DataFrame(history), use_container_width=True)
