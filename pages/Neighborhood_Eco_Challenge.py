"""
Neighborhood Eco-Challenge Page.
Streamlit page displaying local community progress, anonymous block rankings, and neighborhood-specific tips.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
from src.community.block_leaderboard import BlockLeaderboard
from src.core.database import submit_neighborhood_score, get_neighborhood_leaderboard

st.set_page_config(page_title="Neighborhood Challenge", page_icon="🏘️", layout="wide")

st.title("🏘️ Gamified Neighborhood Eco-Competition")
st.markdown(
    "Join your anonymous community in sustainability challenges. Compete with other zip codes while keeping individual data completely private."
)

# Initialize session state
if "leaderboard_engine" not in st.session_state:
    st.session_state.leaderboard_engine = BlockLeaderboard()

    # Seed some dummy data for demonstration
    engine = st.session_state.leaderboard_engine
    for i in range(50):
        engine.competition.submit_anonymous_score(f"user_{i}", "90210", 75.0, 120.0)
        engine.competition.submit_anonymous_score(
            f"user_{i + 100}", "10001", 82.0, 150.0
        )
        engine.competition.submit_anonymous_score(
            f"user_{i + 200}", "60614", 68.0, 90.0
        )

engine = st.session_state.leaderboard_engine

# --- User Input Section ---
st.sidebar.header("📍 Join Your Neighborhood")
user_zip = st.sidebar.text_input("Enter your Zip Code", value="90210")
user_score = st.sidebar.slider("Your Current Eco-Score", 0, 100, 75)
user_saved = st.sidebar.number_input(
    "Your Carbon Saved (kg)", min_value=0.0, step=10.0, value=50.0
)

if st.sidebar.button("Submit Anonymous Contribution"):
    engine.competition.submit_anonymous_score(
        "current_user", user_zip, user_score, user_saved
    )
    submit_neighborhood_score(user_zip, user_score, user_saved)
    st.sidebar.success("Contribution added anonymously!")
    st.rerun()

# --- Main Dashboard ---
st.subheader(f"📊 Your Neighborhood: {user_zip}")
metrics = engine.competition.get_neighborhood_metrics(user_zip)

col1, col2, col3 = st.columns(3)
col1.metric("Anonymous Participants", metrics["total_participants"])
col2.metric("Average Eco-Score", f"{metrics['average_eco_score']}/100")
col3.metric("Total Carbon Saved", f"{metrics['total_carbon_saved_kg']:,.0f} kg")

# --- Challenge Progress ---
st.divider()
st.subheader("🏆 Active Community Challenges")
challenge_data = engine.evaluate_community_challenge_progress(user_zip, "challenge_1")

st.markdown(f"### {challenge_data['challenge_name']}")
st.markdown(challenge_data["description"])

# Progress bar
st.progress(challenge_data["progress_pct"] / 100.0)
st.caption(
    f"{challenge_data['current_saved_kg']:,.0f} / {challenge_data['goal_kg']:,.0f} kg CO₂e saved by {challenge_data['participants']} neighbors"
)

if challenge_data["is_completed"]:
    st.balloons()
    st.success(
        "🎉 Challenge Completed! Your neighborhood has earned the 'Green Block' badge."
    )

# --- Leaderboard ---
st.divider()
st.subheader("🌍 Regional Leaderboard")
st.markdown("Ranked by Average Eco-Score (Individual data is never exposed)")

leaderboard_data = engine.generate_leaderboard(metric="average_eco_score")
if leaderboard_data:
    df = pd.DataFrame(leaderboard_data)
    df = df[
        [
            "rank",
            "zip_code",
            "total_participants",
            "average_eco_score",
            "total_carbon_saved_kg",
        ]
    ]
    df.rename(
        columns={
            "zip_code": "Zip Code",
            "total_participants": "Participants",
            "average_eco_score": "Avg Eco-Score",
            "total_carbon_saved_kg": "Total Saved (kg)",
        },
        inplace=True,
    )

    # Highlight the user's zip code
    def highlight_user(row):
        return [
            "background-color: #d4edda" if str(row["Zip Code"]) == str(user_zip) else ""
            for _ in row
        ]

    styled_df = df.style.apply(highlight_user, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
else:
    st.info("No neighborhood data available yet. Be the first to submit!")

# --- Localized Tips ---
st.divider()
st.subheader("💡 Neighborhood Action Tips")
tips = engine.get_localized_sustainability_tips(user_zip)
for tip in tips:
    st.info(tip)
