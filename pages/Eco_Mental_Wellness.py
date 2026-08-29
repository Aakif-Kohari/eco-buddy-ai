"""
Eco Mental Wellness Page.
Streamlit page featuring a mood/efficacy check-in interface, daily micro-action checklist, and long-term agency trend chart.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from eco_efficacy_tracker import EcoEfficacyTracker
from micro_action_therapy import MicroActionTherapy
from database import save_efficacy_checkin, get_efficacy_history

st.set_page_config(page_title="Eco Mental Wellness", page_icon="🧠", layout="wide")

st.title("🧠 Eco-Efficacy & Climate Action Micro-Step Therapy")
st.markdown(
    "Address climate anxiety by focusing on manageable, daily actions that restore your sense of personal agency and well-being."
)

# Initialize components
if "efficacy_tracker" not in st.session_state:
    st.session_state.efficacy_tracker = EcoEfficacyTracker()
    st.session_state.therapy = MicroActionTherapy()
    st.session_state.current_action = None

tracker = st.session_state.efficacy_tracker
therapy = st.session_state.therapy

# --- Main Layout ---
tab1, tab2 = st.tabs(["📝 Daily Check-In & Action", "📈 Your Agency Trend"])

with tab1:
    st.subheader("1. How are you feeling today?")
    col1, col2 = st.columns(2)

    with col1:
        anxiety = st.slider(
            "Climate Anxiety Level", 1, 10, 5, help="1 = Very Calm, 10 = Highly Anxious"
        )
    with col2:
        agency = st.slider(
            "Sense of Personal Agency",
            1,
            10,
            5,
            help="1 = Powerless, 10 = Empowered to act",
        )

    if st.button("Calculate Eco-Efficacy Score"):
        # Check if action was taken (mocked as True for the check-in flow if they had one)
        action_taken = st.session_state.get("action_completed_today", False)

        result = tracker.administer_check_in(anxiety, agency, action_taken)
        st.session_state.latest_checkin = result

        # Generate new action if none exists or if score changed significantly
        if not st.session_state.current_action or st.session_state.get(
            "new_action_requested"
        ):
            st.session_state.current_action = therapy.generate_daily_action(
                result["efficacy_score"]
            )
            st.session_state.action_completed_today = False  # Reset for new action
            st.session_state.new_action_requested = False

        save_efficacy_checkin(
            "demo_user", anxiety, agency, action_taken, result["efficacy_score"]
        )
        st.success("Check-in recorded!")
        st.rerun()

    if "latest_checkin" in st.session_state:
        res = st.session_state.latest_checkin
        st.markdown(f"### Your Eco-Efficacy Score: **{res['efficacy_score']}/100**")
        st.info(res["interpretation"])

        st.divider()
        st.subheader("2. Your Micro-Action for Today")

        action = st.session_state.current_action
        if action:
            st.markdown(f"#### 🎯 **{action['action_text']}**")
            st.markdown(f"*Effort Level: {action['effort_level']}*")
            st.success(f"💬 *{action['encouragement']}*")

            if not st.session_state.get("action_completed_today"):
                if st.button("✅ Mark Action as Completed", type="primary"):
                    st.session_state.action_completed_today = True
                    therapy.log_completion(action["action_text"])

                    # Recalculate score with action bonus
                    updated_result = tracker.administer_check_in(
                        res["anxiety_level"], res["agency_level"], action_taken=True
                    )
                    st.session_state.latest_checkin = updated_result
                    st.balloons()
                    st.success(
                        "Fantastic! Completing small actions builds real momentum. Your efficacy score has been updated."
                    )
                    st.rerun()
            else:
                st.markdown(
                    "✅ **Action Completed!** Great job taking a positive step today."
                )

with tab2:
    st.subheader("Your Eco-Efficacy Journey")
    history = tracker.get_trend_data(days=14)

    if len(history) > 1:
        df = pd.DataFrame(history)
        # Create a mock date index for visualization if real dates aren't stored yet
        df["day"] = list(range(1, len(df) + 1))

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["day"],
                y=df["efficacy_score"],
                mode="lines+markers",
                name="Efficacy Score",
                line=dict(color="#2ca02c", width=3),
                fill="tozeroy",
            )
        )

        fig.update_layout(
            title="Eco-Efficacy Score Trend (Last 14 Check-ins)",
            xaxis_title="Check-in Sequence",
            yaxis_title="Efficacy Score (0-100)",
            yaxis=dict(range=[0, 110]),
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📋 Recent Completed Actions")
        for act in therapy.completed_actions[-5:]:
            st.markdown(f"- ✅ {act}")
    else:
        st.info("Complete a few daily check-ins to see your agency trend over time.")
