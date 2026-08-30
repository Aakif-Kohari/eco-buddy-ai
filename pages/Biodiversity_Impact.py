"""
Biodiversity Impact Page.
Streamlit page where users can log garden or community projects, view their BNG score, and track ecological improvements.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from biodiversity_net_gain import BiodiversityNetGainCalculator
from habitat_restoration_db import HabitatRestorationDB
from database import save_biodiversity_project, get_biodiversity_history

st.set_page_config(page_title="Biodiversity Impact", page_icon="🦋", layout="wide")

st.title("🦋 Biodiversity Net Gain & Habitat Restoration Calculator")
st.markdown(
    "Quantify the positive ecological impact of your local habitat restoration activities and track your contribution to nature recovery."
)

db = HabitatRestorationDB()
actions = db.get_all_actions()
baselines = db.get_all_baselines()

# --- Project Setup ---
st.sidebar.header("🏞️ Project Baseline")
baseline_cond = st.sidebar.selectbox(
    "Current Habitat Condition",
    options=baselines,
    format_func=lambda x: x.replace("_", " ").title(),
)
total_area = st.sidebar.number_input(
    "Total Project Area (sqm)", min_value=1.0, step=1.0, value=50.0
)

if "calculator" not in st.session_state or st.session_state.get("reset_calc"):
    st.session_state.calculator = BiodiversityNetGainCalculator(
        baseline_cond, total_area
    )
    st.session_state.reset_calc = False

calc = st.session_state.calculator

# --- Add Action Form ---
st.sidebar.header("➕ Add Restoration Action")
with st.sidebar.form("add_action_form"):
    action = st.selectbox(
        "Action Type",
        options=actions,
        format_func=lambda x: db.get_action_display_name(x),
    )
    area = st.number_input(
        "Area for this Action (sqm)", min_value=0.1, step=0.5, value=5.0
    )
    years = st.slider("Management Duration (Years)", 1, 30, 5)

    if st.form_submit_button("Add to Project"):
        if area <= calc.total_area_sqm:
            calc.add_restoration_action(action, area, years)
            st.sidebar.success("Action added!")
            st.rerun()
        else:
            st.sidebar.error("Action area cannot exceed total project area.")

# --- Results Display ---
st.divider()
result = calc.calculate_net_gain()

st.subheader("📊 Biodiversity Net Gain (BNG) Assessment")

col1, col2, col3 = st.columns(3)
col1.metric(
    "Baseline Score",
    f"{result['baseline_score']:.2f}",
    help="0.0 = Degraded, 1.0 = Pristine",
)
col2.metric("Post-Development Score", f"{result['post_development_score']:.2f}")
col3.metric(
    "Net Gain Percentage",
    f"+{result['bng_percentage']:.1f}%",
    delta_color="normal" if result["is_positive_gain"] else "inverse",
)

# BNG Gauge Chart
fig_gauge = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=result["bng_percentage"],
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Biodiversity Net Gain (%)"},
        gauge={
            "axis": {"range": [-20, 50]},
            "bar": {"color": "#2ca02c" if result["is_positive_gain"] else "#d62728"},
            "steps": [
                {"range": [-20, 0], "color": "#f8d7da"},
                {"range": [0, 10], "color": "#fff3cd"},
                {"range": [10, 50], "color": "#d4edda"},
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": 10.0,  # Common regulatory target is 10% BNG
            },
        },
    )
)
fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
st.plotly_chart(fig_gauge, use_container_width=True)

# Wildlife Supported
st.markdown("### 🐾 Wildlife Supported by Your Project")
if result["wildlife_supported"]:
    tags = " ".join(
        [f"🏷️ `{w.replace('_', ' ').title()}`" for w in result["wildlife_supported"]]
    )
    st.markdown(tags)
else:
    st.info("Add actions to see which wildlife will benefit.")

# Action Breakdown Table
st.markdown("### 📋 Action Breakdown")
if result["action_breakdown"]:
    df_actions = pd.DataFrame(result["action_breakdown"])
    df_actions = df_actions[
        ["action_name", "area_sqm", "management_years", "bu_gained"]
    ]
    df_actions.rename(
        columns={
            "action_name": "Action",
            "area_sqm": "Area (sqm)",
            "management_years": "Years Managed",
            "bu_gained": "Biodiversity Units Gained",
        },
        inplace=True,
    )
    st.dataframe(df_actions, use_container_width=True, hide_index=True)
else:
    st.info("No actions added yet.")

# Recommendations
st.divider()
st.subheader("💡 Recommendations for Improvement")
for rec in calc.get_recommendations():
    st.info(rec)

# Save Button
if st.button("💾 Save Project Assessment"):
    save_biodiversity_project(
        baseline_cond, total_area, result["bng_percentage"], result["total_bu_gained"]
    )
    st.success("Project assessment saved to history!")

# --- History ---
st.divider()
st.subheader("📜 Past Project Assessments")
history = get_biodiversity_history()
if history:
    st.dataframe(pd.DataFrame(history), use_container_width=True)
