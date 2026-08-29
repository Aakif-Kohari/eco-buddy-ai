"""
Streamlit Page: Eco-Habit Streak Tracker & Daily Habit Engine
Multi-page section enabling users to build sustainable habits, maintain daily streaks, earn XP, and track CO2 savings.
"""

import streamlit as st
import pandas as pd

from src.lifestyle.eco_habit_streak_service import EcoHabitStreakService
from src.lifestyle.eco_habit_streak_types import HabitCategory, HabitFrequency
from src.lifestyle.eco_habit_streak_cards import render_streak_summary_header, render_habit_streak_card
from src.lifestyle.eco_habit_streak_charts import build_habit_streak_bar_chart, build_habit_category_co2_chart

st.set_page_config(
    page_title="Eco-Habit Streak Tracker - EcoBuddy AI",
    page_icon="🔥",
    layout="wide",
)

st.title("🔥 Eco-Habit Streak Tracker & Daily Action Engine")
st.markdown(
    "Build long-term sustainable lifestyle habits, protect your streaks with freeze tokens, "
    "and watch your cumulative environmental impact grow day by day."
)

service = EcoHabitStreakService()
current_user_id = st.session_state.get("user_id", 1)

# Render Summary Header
summary = service.get_user_summary(current_user_id)
render_streak_summary_header(summary)

st.divider()

# Navigation Tabs
tab_my_habits, tab_add_habit, tab_analytics = st.tabs([
    "📌 Daily Habit Dashboard",
    "➕ Create Custom Eco-Habit",
    "📊 Streak Analytics & Insights",
])

# -------------------------------------------------------------------
# Tab 1: Daily Habit Dashboard
# -------------------------------------------------------------------
with tab_my_habits:
    st.subheader("📋 Active Eco-Habits & Daily Streaks")

    category_options = ["All"] + [c.value for c in HabitCategory]
    selected_cat = st.selectbox("Filter by Category", category_options)

    habits = service.get_habits_for_user(current_user_id, category_filter=selected_cat)

    def handle_log_habit(habit_id: int, val_logged: float, notes: str):
        res = service.complete_habit(current_user_id, habit_id, val_logged, notes)
        if res["success"]:
            st.balloons()
            st.success(
                f"🔥 Streak Extended! Current Streak: {res['current_streak']} Days | "
                f"+{res['xp_earned']} XP | {res['co2_avoided_kg']} kg CO₂ Saved!"
            )
            st.rerun()
        else:
            st.warning(res.get("message", "Failed to log habit."))

    if not habits:
        st.info("No active habits found. Create a new habit in the 'Create Custom Eco-Habit' tab!")
    else:
        for habit in habits:
            render_habit_streak_card(habit, on_log_callback=handle_log_habit)

# -------------------------------------------------------------------
# Tab 2: Create Custom Eco-Habit
# -------------------------------------------------------------------
with tab_add_habit:
    st.subheader("➕ Design a New Eco-Habit")
    with st.form("create_habit_form"):
        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input("Habit Title*", placeholder="e.g. Turn Off Standby Electronics")
            description = st.text_area("Description*", placeholder="Unplug unused electronics before sleeping.")
            category = st.selectbox("Category", [c.value for c in HabitCategory])
            frequency = st.selectbox("Frequency", [f.value for f in HabitFrequency])

        with col2:
            target_value = st.number_input("Target Value*", min_value=0.1, value=1.0, step=0.5)
            unit = st.text_input("Unit*", placeholder="e.g. device, km, meal, load")
            co2_saved = st.number_input("CO₂ Saved per Unit (kg)*", min_value=0.01, value=0.50, step=0.1)
            xp_reward = st.number_input("XP Reward per Completion*", min_value=5, value=25, step=5)

        submit_habit = st.form_submit_button("🚀 Add Eco-Habit")
        if submit_habit:
            if not title or not description or not unit:
                st.error("Please fill out all required fields.")
            else:
                new_h = service.add_custom_habit(
                    user_id=current_user_id,
                    title=title,
                    description=description,
                    category=HabitCategory(category),
                    frequency=HabitFrequency(frequency),
                    target_value=target_value,
                    unit=unit,
                    co2_saved_per_unit=co2_saved,
                    xp_per_completion=int(xp_reward),
                )
                if new_h:
                    st.success(f"Successfully added habit '{title}'!")
                    st.rerun()
                else:
                    st.error("Error creating habit.")

# -------------------------------------------------------------------
# Tab 3: Streak Analytics & Insights
# -------------------------------------------------------------------
with tab_analytics:
    st.subheader("📊 Habit Performance & Impact Analytics")

    all_habits = service.get_habits_for_user(current_user_id)
    if all_habits:
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            streak_chart = build_habit_streak_bar_chart(all_habits)
            st.plotly_chart(streak_chart, use_container_width=True)

        with col_c2:
            co2_chart = build_habit_category_co2_chart(all_habits)
            st.plotly_chart(co2_chart, use_container_width=True)
    else:
        st.info("No habit analytics available yet.")
