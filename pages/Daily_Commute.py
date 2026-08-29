"""
Daily Commute Page.
Streamlit page featuring side-by-side mode comparison, live carbon saved counter, and weekly commute habit heatmap.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
from daily_commute_optimizer import DailyCommuteOptimizer
from transit_carbon_tracker import TransitCarbonTracker
from database import save_commute_log, get_commute_history

st.set_page_config(page_title="Daily Commute", page_icon="🚲", layout="wide")

st.title("🚲 Dynamic Daily Commute Optimizer & Savings Tracker")
st.markdown(
    "Compare real-time adjusted commute options and track your cumulative carbon savings from sustainable choices."
)

# Initialize tracker
if "commute_tracker" not in st.session_state:
    st.session_state.commute_tracker = TransitCarbonTracker()

tracker = st.session_state.commute_tracker

# --- Input Section ---
st.sidebar.header("⚙️ Commute Configuration")
distance = st.sidebar.number_input(
    "One-Way Distance (km)", min_value=0.1, step=0.5, value=10.0
)
weather = st.sidebar.selectbox(
    "Current Weather", ["sunny", "rainy", "snowy", "extreme_heat"]
)
traffic = st.sidebar.selectbox("Traffic Conditions", ["light", "moderate", "heavy"])
baseline_mode = st.sidebar.selectbox(
    "Your Usual Commute Mode", ["driving_gas", "driving_ev", "public_transit"]
)

if st.sidebar.button("🔍 Evaluate Options"):
    st.session_state.optimizer = DailyCommuteOptimizer(distance, weather, traffic)
    st.session_state.baseline_mode = baseline_mode
    st.rerun()

# --- Evaluation Results ---
if "optimizer" in st.session_state:
    optimizer = st.session_state.optimizer
    baseline_mode = st.session_state.baseline_mode
    results = optimizer.evaluate_modes()

    st.subheader("📊 Ranked Commute Options")
    st.markdown(f"*Adjusted for **{weather}** weather and **{traffic}** traffic.*")

    # Display top 3 options prominently
    cols = st.columns(3)
    for i, res in enumerate(results[:3]):
        with cols[i]:
            is_baseline = res["mode_key"] == baseline_mode
            border_color = (
                "#2ca02c" if i == 0 else ("#007bff" if is_baseline else "#6c757d")
            )

            st.markdown(
                f"""
            <div style="border: 2px solid {border_color}; border-radius: 10px; padding: 15px; background-color: #f8f9fa;">
                <h4 style="color: {border_color}; margin-top: 0;">{i + 1}. {res["mode"]}</h4>
                <p><strong>🌱 Carbon:</strong> {res["carbon_kg"]} kg CO₂e</p>
                <p><strong>⏱️ Time:</strong> {res["time_minutes"]} mins</p>
                <p><strong>💰 Cost:</strong> ${res["cost_usd"]}</p>
                {"<p><em>🌟 Most Sustainable</em></p>" if i == 0 else ""}
                {"<p><em>📍 Your Baseline</em></p>" if is_baseline else ""}
            </div>
            """,
                unsafe_allow_html=True,
            )

            if st.button(f"Log {res['mode']} Trip", key=f"log_{res['mode_key']}"):
                from datetime import datetime

                today = datetime.now().strftime("%Y-%m-%d")

                entry = tracker.log_commute(
                    today, distance, res["mode_key"], baseline_mode
                )
                save_commute_log(
                    "demo_user",
                    today,
                    distance,
                    res["mode_key"],
                    baseline_mode,
                    entry["carbon_saved_kg"],
                )

                st.success(
                    f"Logged! You saved **{entry['carbon_saved_kg']} kg** of CO₂e compared to {baseline_mode.replace('_', ' ')}."
                )
                st.rerun()

# --- Savings Dashboard ---
st.divider()
st.subheader("💰 Your Carbon Savings Dashboard")

summary = tracker.get_savings_summary()

col1, col2, col3 = st.columns(3)
col1.metric("Saved Today", f"{summary['today_kg']:.2f} kg CO₂e")
col2.metric("Saved This Month", f"{summary['month_kg']:.2f} kg CO₂e")
col3.metric(
    "All-Time Savings",
    f"{summary['total_kg']:.2f} kg CO₂e",
    help="Equivalent to planting ~" + str(int(summary["total_kg"] / 20)) + " trees.",
)

# Weekly Heatmap
st.markdown("### 🗓️ Weekly Commute Habit Heatmap")
heatmap_data = tracker.get_weekly_heatmap_data()
df_heatmap = pd.DataFrame(heatmap_data)

fig = px.bar(
    df_heatmap,
    x="date",
    y="carbon_saved_kg",
    color="modes_used",
    title="Daily Carbon Saved (Last 7 Days)",
    labels={
        "carbon_saved_kg": "Carbon Saved (kg CO₂e)",
        "date": "Date",
        "modes_used": "Modes Used",
    },
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.update_layout(template="plotly_white")
st.plotly_chart(fig, use_container_width=True)
