"""
Streamlit Page: Community Eco Challenges Engine
Multi-page section in EcoBuddy AI enabling users to explore, join, track, and complete community sustainability challenges.
"""

import streamlit as st
import pandas as pd

from eco_community_challenges_service import EcoCommunityChallengesService
from eco_community_challenges_types import ChallengeCategory, ChallengeDifficulty
from eco_community_challenges_cards import (
    render_challenge_metrics_header,
    render_challenge_card,
    render_active_enrollment_card,
)
from eco_community_challenges_charts import (
    build_challenge_category_chart,
    build_user_progress_bar_chart,
    build_community_leaderboard_chart,
)
from database import get_leaderboard

st.set_page_config(
    page_title="Community Eco Challenges - EcoBuddy AI",
    page_icon="🌱",
    layout="wide",
)

st.title("🌱 Community Eco-Challenges & Impact Engine")
st.markdown(
    "Join collective sustainability challenges, track your daily eco-actions, earn XP rewards, "
    "and measure your real-world carbon footprint reductions alongside the community."
)

# Initialize Service
service = EcoCommunityChallengesService()
current_user_id = st.session_state.get("user_id", 1)

# Render Overview Header
analytics_summary = service.get_impact_analytics()
render_challenge_metrics_header(analytics_summary)

st.divider()

# Navigation Tabs
tab_explore, tab_my_challenges, tab_leaderboard, tab_analytics = st.tabs([
    "🔍 Explore Challenges",
    "📌 My Active Challenges",
    "🏆 Community Leaderboard",
    "📊 Impact Analytics",
])

# -------------------------------------------------------------------
# Tab 1: Explore Challenges
# -------------------------------------------------------------------
with tab_explore:
    st.subheader("🎯 Available Community Challenges")

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        category_options = ["All"] + [c.value for c in ChallengeCategory]
        selected_category = st.selectbox("Filter by Category", category_options)

    with filter_col2:
        difficulty_options = ["All"] + [d.value for d in ChallengeDifficulty]
        selected_difficulty = st.selectbox("Filter by Difficulty", difficulty_options)

    challenges = service.get_catalog(
        category_filter=selected_category,
        difficulty_filter=selected_difficulty,
    )

    if not challenges:
        st.info("No active challenges found matching your selected criteria.")
    else:
        for ch in challenges:
            render_challenge_card(ch)
            col_btn, _ = st.columns([1, 4])
            with col_btn:
                if st.button(f"Join Challenge #{ch.id}", key=f"enroll_btn_{ch.id}"):
                    result = service.enroll_user(current_user_id, ch.id)
                    if result:
                        st.success(f"Successfully joined '{ch.title}'! Good luck on your eco journey.")
                        st.rerun()
                    else:
                        st.warning("You are already enrolled in this challenge or an error occurred.")

# -------------------------------------------------------------------
# Tab 2: My Active Challenges
# -------------------------------------------------------------------
with tab_my_challenges:
    st.subheader("📌 Your Active Eco Challenges")

    active_enrollments = service.get_active_user_enrollments(current_user_id)

    def handle_log_progress(enrollment_id: int, inc_value: float, notes: str):
        res = service.log_progress(enrollment_id, inc_value, notes)
        if res["success"]:
            if res["completed"]:
                st.balloons()
                st.success(
                    f"🎉 Challenge Completed! You earned +{res['xp_earned']} XP "
                    f"and avoided {res['co2_avoided_kg']} kg CO₂!"
                )
            else:
                st.success(f"Progress updated! +{inc_value} logged. New completion: {res['percentage']}%")
            st.rerun()
        else:
            st.error(res.get("message", "Failed to update progress."))

    if not active_enrollments:
        st.info("You are not enrolled in any active challenges yet. Head to the 'Explore Challenges' tab to get started!")
    else:
        for enrollment in active_enrollments:
            render_active_enrollment_card(enrollment, on_log_callback=handle_log_progress)
            st.divider()

    # User History Section
    st.subheader("📜 Challenge History")
    all_enrollments = service.get_user_history(current_user_id)
    if all_enrollments:
        history_df = pd.DataFrame(all_enrollments)[[
            "title", "category", "joined_date", "status", "current_progress", "target_goal", "co2_impact_kg", "xp_reward"
        ]]
        history_df.columns = ["Challenge", "Category", "Joined", "Status", "Progress", "Target", "CO₂ Impact (kg)", "XP Reward"]
        st.dataframe(history_df, use_container_width=True)

# -------------------------------------------------------------------
# Tab 3: Community Leaderboard
# -------------------------------------------------------------------
with tab_leaderboard:
    st.subheader("🏆 Global Community Leaderboard")
    leaderboard_data = get_leaderboard()
    if leaderboard_data:
        chart = build_community_leaderboard_chart(leaderboard_data)
        st.plotly_chart(chart, use_container_width=True)

        lb_df = pd.DataFrame(leaderboard_data, columns=["Community Member", "Max Eco Score", "Total XP", "Completed Challenges"])
        st.dataframe(lb_df, use_container_width=True)
    else:
        st.info("No community leaderboard entries recorded yet.")

# -------------------------------------------------------------------
# Tab 4: Impact Analytics
# -------------------------------------------------------------------
with tab_analytics:
    st.subheader("📊 Community Eco Impact Breakdown")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        catalog_challenges = service.get_catalog()
        cat_chart = build_challenge_category_chart(catalog_challenges)
        st.plotly_chart(cat_chart, use_container_width=True)

    with col_chart2:
        if active_enrollments:
            prog_chart = build_user_progress_bar_chart(active_enrollments)
            st.plotly_chart(prog_chart, use_container_width=True)
        else:
            st.info("Enroll in challenges to view your active progress analytics.")
