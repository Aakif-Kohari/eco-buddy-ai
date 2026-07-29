import streamlit as st
import pandas as pd
from database import get_leaderboard

# Login check
if "user_id" not in st.session_state:
    st.session_state["user_id"] = 1

st.title("🏆 Community Leaderboard")

st.markdown(
    "Compare your Eco Score, XP, and completed sustainability challenges with other users."
)

# Ranking period selector
ranking_type = st.radio(
    "Ranking Period",
    ["All Time", "Weekly", "Monthly"],
    horizontal=True
)

if ranking_type == "Weekly":
    leaderboard = get_leaderboard("weekly")
elif ranking_type == "Monthly":
    leaderboard = get_leaderboard("monthly")
else:
    leaderboard = get_leaderboard("all")

if leaderboard:

    rows = []

    for rank, row in enumerate(leaderboard, start=1):
        rows.append({
            "Rank": rank,
            "User": row[0],
            "Eco Score": row[1],
            "XP": row[2],
            "Challenges Completed": row[3]
        })

    df = pd.DataFrame(rows)

    # Summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("👥 Participants", len(df))

    with col2:
        st.metric("🌱 Top Eco Score", int(df["Eco Score"].max()))

    with col3:
        st.metric("⭐ Top XP", int(df["XP"].max()))

    st.markdown("---")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No leaderboard data available yet.")