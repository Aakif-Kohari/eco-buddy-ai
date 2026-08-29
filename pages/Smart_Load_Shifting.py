"""
Smart Load Shifting Page.
Streamlit page featuring an interactive daily load curve chart, a "shift potential" slider, and a projected savings dashboard.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from demand_response_optimizer import DemandResponseOptimizer
from load_shifting_engine import LoadShiftingEngine
from database import save_load_shifting_plan, get_load_shifting_history

st.set_page_config(page_title="Smart Load Shifting", page_icon="⏱️", layout="wide")

st.title("⏱️ Smart Home Energy Demand Response & Load Shifting Optimizer")
st.markdown(
    "Analyze your flexible appliance usage and simulate shifting them to off-peak hours to save money and reduce carbon emissions."
)

optimizer = DemandResponseOptimizer()
engine = LoadShiftingEngine()
appliances = list(optimizer.FLEXIBLE_APPLIANCES.keys())

# --- Input Section ---
st.sidebar.header("⚙️ Household Appliances")
selected_apps = st.sidebar.multiselect(
    "Select Flexible Appliances",
    options=appliances,
    default=["ev_charging", "dishwasher"],
    format_func=lambda x: optimizer.FLEXIBLE_APPLIANCES[x]["name"],
)
optimization_goal = st.sidebar.radio(
    "Optimization Goal", ["Minimize Carbon", "Minimize Cost"]
)

if st.sidebar.button("🔍 Optimize Schedule"):
    optimizer.select_appliances(selected_apps)
    preference = "carbon" if optimization_goal == "Minimize Carbon" else "cost"

    results = optimizer.optimize_all_selected(preference=preference)
    baseline_curve = optimizer.generate_load_curve_data(optimized=False)
    optimized_curve = optimizer.generate_load_curve_data(
        optimized=True, preference=preference
    )

    st.session_state.optimization_results = {
        "results": results,
        "baseline_curve": baseline_curve,
        "optimized_curve": optimized_curve,
        "preference": preference,
    }

    save_load_shifting_plan(
        selected_apps,
        preference,
        results["total_carbon_saved_kg"],
        results["total_money_saved_usd"],
    )
    st.sidebar.success("Optimization complete and saved!")

# --- Results Display ---
if "optimization_results" in st.session_state:
    data = st.session_state.optimization_results
    results = data["results"]

    st.divider()
    st.subheader("📊 Projected Daily Savings")

    col1, col2 = st.columns(2)
    col1.metric(
        "Estimated Annual Cost Savings",
        f"${results['total_money_saved_usd'] * 365:,.2f}",
        help="Based on daily optimization.",
    )
    col2.metric(
        "Estimated Annual Carbon Avoided",
        f"{results['total_carbon_saved_kg'] * 365:,.1f} kg CO₂e",
        help="Based on daily optimization.",
    )

    # Load Curve Comparison Chart
    st.markdown("### 📈 Daily Load Curve Comparison")
    df_baseline = pd.DataFrame(data["baseline_curve"])
    df_optimized = pd.DataFrame(data["optimized_curve"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_baseline["hour"],
            y=df_baseline["load_kw"],
            mode="lines+markers",
            name="Baseline Schedule",
            line=dict(color="#d62728", dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_optimized["hour"],
            y=df_optimized["load_kw"],
            mode="lines+markers",
            name=f"Optimized Schedule ({data['preference'].title()})",
            line=dict(color="#2ca02c", width=3),
        )
    )

    fig.update_layout(
        title="Household Flexible Load Profile (kW)",
        xaxis_title="Hour of Day",
        yaxis_title="Power Demand (kW)",
        template="plotly_white",
        xaxis=dict(tickmode="linear", dtick=2),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Appliance Breakdown Table
    st.markdown("### 📋 Appliance Shift Details")
    breakdown_data = []
    for app in results["appliance_breakdown"]:
        baseline_hrs = ", ".join([f"{h}:00" for h in app["baseline_hours"]])
        optimal_hrs = ", ".join([f"{h}:00" for h in app["optimal_hours"]])

        breakdown_data.append(
            {
                "Appliance": app["appliance"],
                "Energy (kWh)": app["kwh"],
                "Baseline Hours": baseline_hrs,
                "Optimized Hours": optimal_hrs,
                "Carbon Saved (kg)": app["savings"]["carbon_saved_kg"],
                "Money Saved ($)": app["savings"]["money_saved_usd"],
            }
        )

    df_breakdown = pd.DataFrame(breakdown_data)
    st.dataframe(df_breakdown, use_container_width=True, hide_index=True)

    # Grid Context
    st.divider()
    st.subheader("🌍 Grid Context")
    st.markdown(
        "The optimizer uses real-time grid data principles. For example, shifting EV charging from 6 PM (high carbon, high cost) to 2 AM (low carbon, low cost) maximizes both environmental and financial benefits."
    )

# --- History ---
st.divider()
st.subheader("📜 Past Optimization Plans")
history = get_load_shifting_history()
if history:
    st.dataframe(pd.DataFrame(history), use_container_width=True)
else:
    st.info("No optimization plans saved yet.")
