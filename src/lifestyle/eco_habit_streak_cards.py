"""
Streamlit Component Cards & Renderers for Eco-Habit Streak Tracker
"""

import streamlit as st
from typing import Dict, Any, Callable


def render_streak_summary_header(summary: Dict[str, Any]) -> None:
    """Renders top summary metric cards for active habit streak dashboard."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🔥 Active Max Streak",
            value=f"{summary['active_max_streak']} Days",
            delta="Current Best Streak",
        )

    with col2:
        st.metric(
            label="🏆 All-Time Record",
            value=f"{summary['all_time_max_streak']} Days",
            delta="Personal Best",
        )

    with col3:
        st.metric(
            label="🌿 Total CO₂ Saved",
            value=f"{summary['total_co2_avoided_kg']} kg",
            delta="Avoided Emissions",
        )

    with col4:
        st.metric(
            label="⭐ Habit XP Earned",
            value=f"{summary['total_xp_earned']} XP",
            delta=f"{summary['total_completions']} Total Logs",
        )


def render_habit_streak_card(habit: Dict[str, Any], on_log_callback: Callable = None) -> None:
    """Renders an interactive habit card showing streak status, badge, and quick log button."""
    streak = habit["current_streak"]
    completed_today = habit["completed_today"]
    fire_emoji = "🔥" if streak > 0 else "⚪"

    with st.container():
        st.markdown(
            f"""
            <div style="
                border: 1px solid {'#4CAF50' if completed_today else '#E0E0E0'};
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 14px;
                background-color: {'#F1F8E9' if completed_today else '#FFFFFF'};
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #2E7D32;">{habit['title']}</h3>
                    <span style="
                        font-size: 1.1rem;
                        font-weight: 700;
                        color: #E65100;
                        background: #FFF3E0;
                        padding: 4px 12px;
                        border-radius: 14px;
                    ">{fire_emoji} {streak} Day Streak</span>
                </div>
                <p style="color: #666; margin-top: 6px;">{habit['description']}</p>
                <div style="display: flex; gap: 16px; font-size: 0.88rem; color: #555;">
                    <span><b>Category:</b> {habit['category']}</span>
                    <span><b>Frequency:</b> {habit['frequency']}</span>
                    <span><b>Target:</b> {habit['target_value']} {habit['unit']}</span>
                    <span><b>XP:</b> +{habit['xp_per_completion']} XP</span>
                    <span><b>Freeze Tokens:</b> 🛡️ {habit['freeze_tokens']}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not completed_today:
            with st.expander("✅ Log Habit Today"):
                with st.form(key=f"log_habit_form_{habit['habit_id']}"):
                    val = st.number_input(
                        f"Amount ({habit['unit']})",
                        min_value=0.1,
                        value=float(habit['target_value']),
                        step=0.5,
                        key=f"val_{habit['habit_id']}",
                    )
                    notes = st.text_input("Notes (Optional)", key=f"notes_{habit['habit_id']}")
                    submit = st.form_submit_button("Complete Habit & Extend Streak 🔥")
                    if submit and on_log_callback:
                        on_log_callback(habit['habit_id'], val, notes)
        else:
            st.success("🎉 Completed for today! Streak extended.")
