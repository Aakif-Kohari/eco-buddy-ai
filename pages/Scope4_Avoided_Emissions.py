"""
Scope 4 Avoided Emissions Page.
Streamlit page featuring a "Net-Positive Impact" dashboard, showcasing total emissions prevented over time.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.utils.remote_work_calculator import RemoteWorkCalculator
from src.carbon.avoided_emissions_tracker import AvoidedEmissionsTracker
from src.core.database import save_avoided_emissions_log, get_avoided_emissions_history

st.set_page_config(
    page_title="Scope 4 Avoided Emissions", page_icon="🌱", layout="wide"
)

st.title("🌱 Scope 4 Avoided Emissions & Net-Positive Impact Tracker")
st.markdown(
    "Quantify the emissions *prevented* by your sustainable choices, such as remote work, virtual meetings, and digital workflows."
)

# Initialize session state
if "tracker" not in st.session_state:
    st.session_state.tracker = AvoidedEmissionsTracker()

tracker = st.session_state.tracker

# --- Input Section: Remote Work ---
st.subheader("💻 Remote Work Impact Calculator")
col1, col2, col3 = st.columns(3)

with col1:
    days_per_week = st.slider("WFH Days per Week", 1, 5, 3)
with col2:
    commute_km = st.number_input(
        "One-Way Commute Distance (km)", min_value=0.0, step=1.0, value=15.0
    )
with col3:
    vehicle_type = st.selectbox(
        "Primary Commute Vehicle",
        ["ice_car", "ev", "public_transit"],
        format_func=lambda x: x.replace("_", " ").title(),
    )

if st.button("➕ Add Remote Work Savings"):
    calculator = RemoteWorkCalculator()
    # We use a fresh calculator to get the calculation, but we log it to the session tracker
    # For simplicity in this UI, we'll just calculate and add to session tracker manually
    vehicle_factors = {"ice_car": 0.192, "ev": 0.053, "public_transit": 0.105}
    baseline_per_day = ((commute_km * 2) * vehicle_factors[vehicle_type]) + 15.0
    alternative_per_day = 4.0
    total_days = days_per_week * 48.0

    record = tracker.log_avoided_activity(
        activity_type=f"Remote Work ({vehicle_type.replace('_', ' ').title()})",
        quantity=total_days,
        baseline_factor=baseline_per_day,
        alternative_factor=alternative_per_day,
    )

    save_avoided_emissions_log(
        record["activity_type"], record["quantity"], record["avoided_kg"]
    )
    st.success(f"Logged {record['avoided_kg']} kg CO₂e avoided for the year!")
    st.rerun()

# --- Other Avoided Activities (Mock for demonstration) ---
st.subheader("📹 Other Sustainable Choices")
if st.button("➕ Add 10 Virtual Meetings (vs. Travel)"):
    tracker.log_avoided_activity(
        "virtual_meeting", 10, baseline_factor=50.0, alternative_factor=2.0
    )
    st.rerun()

if st.button("➕ Add 50 Digital Documents (vs. Printed/Shipped)"):
    tracker.log_avoided_activity(
        "digital_document", 50, baseline_factor=1.5, alternative_factor=0.1
    )
    st.rerun()

# --- Dashboard Display ---
st.divider()
st.subheader("📊 Your Net-Positive Impact Dashboard")

summary = tracker.get_summary()

col1, col2 = st.columns(2)
col1.metric("Total Avoided Emissions", f"{summary['total_avoided_kg']:,.1f} kg CO₂e")
col2.metric(
    "Equivalent to", f"{int(summary['total_avoided_kg'] / 20)} Trees grown for 10 years"
)

if summary["activity_count"] > 0:
    # Breakdown Chart
    st.markdown("### Avoided Emissions by Activity")
    categories = list(summary["breakdown_by_type"].keys())
    values = list(summary["breakdown_by_type"].values())

    fig = go.Figure(
        data=[
            go.Bar(
                x=categories,
                y=values,
                marker_color="#2ca02c",
                text=[f"{v} kg" for v in values],
                textposition="auto",
            )
        ]
    )
    fig.update_layout(
        title="Annual Avoided Emissions Breakdown",
        xaxis_title="Activity Type",
        yaxis_title="kg CO₂e Avoided",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detailed Table
    st.markdown("### 📜 Activity Log")
    df = pd.DataFrame(tracker.avoided_activities)
    st.dataframe(df, use_container_width=True, hide_index=True)

    if st.button("🗑️ Clear All Logged Data"):
        tracker.reset_tracker()
        st.rerun()
else:
    st.info(
        "No avoided emissions logged yet. Use the calculators above to start building your Net-Positive impact!"
    )

# --- History ---
st.divider()
st.subheader("📜 Historical Saved Logs")
history = get_avoided_emissions_history()
if history:
    st.dataframe(pd.DataFrame(history), use_container_width=True)
