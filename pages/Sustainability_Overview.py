"""Personal Sustainability Overview dashboard for EcoBuddy AI."""

import pandas as pd
import streamlit as st

from database import get_active_goal, get_assessments, get_waste_assessments, get_water_assessments, migrate
from goals import summarize_goal
from styles.theme import apply_theme
from sustainability_overview import build_overview


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Sustainability Overview · EcoBuddy AI",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------

success, message = migrate()

if not success:
    st.error(f"Database migration failed: {message}")
    st.stop()


apply_theme()


# ---------------------------------------------------------
# SESSION INFORMATION
# ---------------------------------------------------------

user_id = st.session_state.get("user_id")
username = st.session_state.get("username")

if not user_id:
    st.warning(
        "Sign in or continue as Guest from the main EcoBuddy page "
        "before opening your sustainability overview."
    )
    st.page_link("app.py", label="Return to EcoBuddy", icon="🌱")
    st.stop()


# ---------------------------------------------------------
# BREADCRUMB NAVIGATION
# ---------------------------------------------------------

st.markdown(
    """
    <nav class="breadcrumb" aria-label="Breadcrumb">
        <span class="breadcrumb-item">🏠 Home</span>
        <span class="breadcrumb-separator">›</span>
        <span class="breadcrumb-item">🌱 Sustainability</span>
        <span class="breadcrumb-separator">›</span>
        <span class="breadcrumb-item active">Overview</span>
    </nav>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------------

st.markdown(
    "<div class='section-header'>📊 Personal Sustainability Overview</div>",
    unsafe_allow_html=True,
)
st.caption(
    f"A single summary of your environmental impact and progress, "
    f"{username or 'EcoBuddy user'}."
)


# ---------------------------------------------------------
# LOAD DATA & BUILD OVERVIEW
# ---------------------------------------------------------

raw_assessments = get_assessments(user_id)
active_goal = get_active_goal(user_id)

water_rows = get_water_assessments(user_id)
latest_water = water_rows[0] if water_rows else None

waste_rows = get_waste_assessments(user_id)
latest_waste = waste_rows[0] if waste_rows else None

overview = build_overview(
    raw_assessments,
    active_goal=active_goal,
    water_row=latest_water,
    waste_row=latest_waste,
)


# ---------------------------------------------------------
# EMPTY STATE
# ---------------------------------------------------------

if not overview["has_data"]:
    st.info(
        "📊 Your Personal Sustainability Overview will appear here "
        "after you complete your first carbon assessment."
    )
    st.page_link("app.py", label="🌍 Start a Carbon Assessment", icon="🌱")
    st.stop()


# ---------------------------------------------------------
# TOP SUMMARY
# ---------------------------------------------------------

st.markdown("### 🧾 Summary")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "🏆 Sustainability Score",
    f"{overview['eco_score']}/100" if overview["eco_score"] is not None else "N/A",
)

col2.metric(
    "🌍 Current Footprint",
    f"{overview['comparison']['current_kg']:,.0f} kg CO₂",
)

comparison = overview["comparison"]
if comparison["percent_change"] is not None:
    delta_label = f"{comparison['percent_change']:+.1f}% vs previous"
    col3.metric(
        "📈 Change vs Previous",
        f"{comparison['delta_kg']:+,.0f} kg CO₂",
        delta=delta_label,
        delta_color="inverse",
    )
else:
    col3.metric("📈 Change vs Previous", "N/A")
    col3.caption("Complete another assessment to see a trend.")

opportunity = overview["opportunity"]
col4.metric(
    "🎯 Highest-Impact Area",
    opportunity["category"] if opportunity else "N/A",
)


# ---------------------------------------------------------
# CATEGORY-WISE BREAKDOWN
# ---------------------------------------------------------

st.markdown("### 🧮 Category-Wise Impact Breakdown")

categories = dict(overview["lifestyle_categories"])
water = overview["water"]

if categories:
    chart_frame = pd.DataFrame(
        {"Category": list(categories.keys()), "kg CO₂ / year": list(categories.values())}
    ).set_index("Category")
    st.bar_chart(chart_frame, use_container_width=True)

    breakdown_col1, breakdown_col2 = st.columns(2)
    with breakdown_col1:
        st.write("**🍽️ Food:**", f"{categories.get('Food', 0):,.0f} kg CO₂/year" if "Food" in categories else "N/A")
        st.write("**🚗 Transportation:**", f"{categories.get('Transportation', 0):,.0f} kg CO₂/year" if "Transportation" in categories else "N/A")
    with breakdown_col2:
        st.write("**⚡ Energy:**", f"{categories.get('Energy', 0):,.0f} kg CO₂/year" if "Energy" in categories else "N/A")
        st.write("**🗑️ Waste:**", f"{categories.get('Waste', 0):,.0f} kg CO₂/year" if "Waste" in categories else "Not assessed yet")
else:
    st.info("A category breakdown will appear once your latest assessment can be recalculated.")

st.write(
    "**💧 Water:**",
    f"{water['liters_per_day']:,.0f} L/day" if water else "Not assessed yet",
)

if overview["waste"]:
    st.caption(f"♻️ {overview['waste']['recyclable_pct']:.0f}% of your recent waste is recyclable.")

nav_col1, nav_col2 = st.columns(2)
with nav_col1:
    st.page_link("pages/Water_Footprint.py", label="💧 Update Water Footprint", icon="💧")
with nav_col2:
    st.page_link("pages/Waste_Footprint.py", label="🗑️ Update Waste Footprint", icon="🗑️")


# ---------------------------------------------------------
# BIGGEST OPPORTUNITY
# ---------------------------------------------------------

st.markdown("### 🚀 Biggest Opportunity")

if opportunity:
    st.warning(
        f"**{opportunity['category']}** is your highest-impact category, responsible for "
        f"about {opportunity['share_pct']:.0f}% of your tracked CO₂ footprint "
        f"({opportunity['kg_co2']:,.0f} kg CO₂/year). Focusing here offers the greatest "
        "potential improvement."
    )
else:
    st.info("Complete a carbon assessment to see where your biggest opportunity lies.")


# ---------------------------------------------------------
# PROGRESS TOWARD REDUCTION GOAL
# ---------------------------------------------------------

st.markdown("### 🎯 Progress Toward Your Goal")

goal_data = overview["goal"]

if goal_data:
    st.progress(min(1.0, goal_data["percent_complete"] / 100.0))
    st.write(summarize_goal(active_goal, goal_data))

    goal_col1, goal_col2, goal_col3 = st.columns(3)
    goal_col1.metric("Current", f"{goal_data['current_kg']:,.0f} kg")
    goal_col2.metric("Target", f"{goal_data['target_kg']:,.0f} kg")
    goal_col3.metric("Progress", f"{goal_data['percent_complete']:.0f}%")
else:
    st.info("You don't have an active reduction goal yet.")
    st.page_link("pages/Reduction_Goals.py", label="🎯 Set a Reduction Goal", icon="🎯")


# ---------------------------------------------------------
# PERSONALIZED INSIGHTS
# ---------------------------------------------------------

st.markdown("### 💡 Key Personalized Insights")

insights = overview["insights"]
if insights:
    for tip in insights[:5]:
        st.markdown(f"- {tip}")
else:
    st.info("Personalized insights will appear once a full category breakdown is available.")


# ---------------------------------------------------------
# NAVIGATION
# ---------------------------------------------------------

st.markdown("### 🧭 Explore EcoBuddy")

explore_col1, explore_col2, explore_col3 = st.columns(3)
with explore_col1:
    st.page_link("pages/Carbon_Footprint.py", label="🌍 New Assessment", icon="🌱")
with explore_col2:
    st.page_link("pages/Sustainability_Journey.py", label="📈 Sustainability Journey", icon="📈")
with explore_col3:
    st.page_link("pages/Assessment_History.py", label="📋 Assessment History", icon="📊")