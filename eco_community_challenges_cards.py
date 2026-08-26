"""
Streamlit UI Component Cards for Eco-Community Challenges
Contains HTML/CSS metric cards, badge components, and challenge card renderer functions.
"""

import streamlit as st
from typing import Dict, Any
from eco_community_challenges_types import CommunityChallenge, ChallengeAnalyticsSummary


def render_challenge_metrics_header(summary: ChallengeAnalyticsSummary) -> None:
    """Renders high-impact overview metrics at the top of the challenges page."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🌍 Active Challenges",
            value=f"{summary.total_challenges}",
            delta="Available Catalog",
        )

    with col2:
        st.metric(
            label="👥 Community Participants",
            value=f"{summary.active_participants}",
            delta="Active Users",
        )

    with col3:
        st.metric(
            label="🌱 CO₂ Avoided",
            value=f"{summary.total_co2_avoided_kg:,.1f} kg",
            delta="Cumulative Impact",
        )

    with col4:
        st.metric(
            label="⭐ XP Awarded",
            value=f"{summary.total_xp_awarded:,} XP",
            delta=f"{summary.completion_rate_pct}% Completion Rate",
        )


def render_challenge_card(challenge: CommunityChallenge, on_enroll_callback=None) -> None:
    """Renders an individual challenge card with details, criteria, and enrollment button."""
    with st.container():
        st.markdown(
            f"""
            <div style="
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 16px;
                background-color: #ffffff;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #2E7D32;">{challenge.title}</h3>
                    <span style="
                        background-color: #E8F5E9;
                        color: #1B5E20;
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-size: 0.85rem;
                        font-weight: 600;
                    ">{challenge.category.value}</span>
                </div>
                <p style="color: #555555; margin-top: 8px; font-size: 0.95rem;">{challenge.description}</p>
                <div style="display: flex; gap: 16px; font-size: 0.88rem; color: #666666; margin-top: 10px;">
                    <span>⏱️ <b>{challenge.duration_days} Days</b></span>
                    <span>⚡ <b>{challenge.xp_reward} XP</b></span>
                    <span>🌿 <b>{challenge.co2_impact_kg} kg CO₂ Impact</b></span>
                    <span>🎯 <b>{challenge.difficulty.value}</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_active_enrollment_card(enrollment: Dict[str, Any], on_log_callback=None) -> None:
    """Renders a user's active challenge enrollment progress card."""
    with st.container():
        st.subheader(f"📌 {enrollment['title']}")
        st.caption(f"Category: {enrollment['category']} | Target Completion: {enrollment['target_completion_date']}")

        # Progress bar
        st.progress(enrollment["percentage"] / 100.0)
        st.write(
            f"**Progress:** {enrollment['current_progress']} / {enrollment['target_goal']} {enrollment['unit']} "
            f"({enrollment['percentage']}%)"
        )

        with st.expander("➕ Log Progress"):
            with st.form(key=f"log_progress_form_{enrollment['enrollment_id']}"):
                inc = st.number_input(
                    f"Increment ({enrollment['unit']})",
                    min_value=0.1,
                    value=1.0,
                    step=0.5,
                    key=f"inc_{enrollment['enrollment_id']}",
                )
                notes = st.text_input("Notes (Optional)", key=f"notes_{enrollment['enrollment_id']}")
                submitted = st.form_submit_button("Submit Progress")
                if submitted and on_log_callback:
                    on_log_callback(enrollment['enrollment_id'], inc, notes)
