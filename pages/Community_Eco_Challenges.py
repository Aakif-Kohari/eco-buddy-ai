"""
Page: Community Eco Challenges
================================
A gamified social hub where users join eco challenges, form teams,
log daily progress, compete on leaderboards, and earn XP rewards.
"""

import streamlit as st
import json
from datetime import datetime

st.set_page_config(page_title="Community Eco Challenges", page_icon="🏆", layout="wide")

# ── Module Imports ────────────────────────────────────────────────────────
from community_challenge_service import (
    list_active_challenges, get_challenge_overview, create_new_challenge,
    participate_in_challenge, submit_progress, get_user_challenge_dashboard,
    get_user_streak, get_category_distribution, get_difficulty_distribution,
    get_weekly_progress_data, get_available_categories, get_difficulty_meta,
)
from community_challenge_cards import (
    inject_card_css, render_challenge_card, render_leaderboard_entry,
    render_feed_item, render_streak_display, render_stats_row,
    render_challenge_create_form,
)
from community_challenge_charts import (
    render_progress_line_chart, render_category_donut, render_difficulty_bar,
    render_team_comparison_chart, render_progress_heatmap,
    render_streak_calendar, render_completion_gauge,
)

# ── Init ──────────────────────────────────────────────────────────────────
inject_card_css()

# Get user_id from session
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("🔐 Please log in or continue as Guest to access Community Challenges.")
    st.stop()

# ── Page Header ───────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding:24px 0 16px; background:linear-gradient(135deg, rgba(34,197,94,0.06), rgba(59,130,246,0.04)); border-radius:16px; margin-bottom:24px;">
    <span style="font-size:42px;">🏆</span>
    <h1 style="margin:8px 0 4px; font-size:32px; font-weight:900; color:#111827;">Community Eco Challenges</h1>
    <p style="color:#6b7280; font-size:15px; max-width:600px; margin:0 auto;">
        Join eco-friendly challenges, form teams, earn XP, and compete to make the biggest environmental impact together!
    </p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar Filters ───────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("🎯 Challenge Filters")
    category_filter = st.selectbox("Category", ["All"] + get_available_categories(), index=0)
    difficulty_filter = st.selectbox("Difficulty", ["All", "easy", "medium", "hard"], index=0)

    cat = category_filter if category_filter != "All" else None
    diff = difficulty_filter if difficulty_filter != "All" else None
    all_challenges = list_active_challenges(category=cat, difficulty=diff)
    st.caption(f"📋 {len(all_challenges)} challenges found")


# ── User Dashboard ────────────────────────────────────────────────────────
st.subheader("📊 Your Dashboard")
dashboard = get_user_challenge_dashboard(user_id)

# Stats Row
render_stats_row({
    "challenges_active": dashboard["challenges_active"],
    "challenges_completed": dashboard["challenges_completed"],
    "total_xp_earned": dashboard["total_xp_earned"],
    "total_actions_logged": int(dashboard["total_actions_logged"]),
})

# Streak + Progress Side by Side
col_streak, col_progress = st.columns([1, 2])

with col_streak:
    streak_data = get_user_streak(user_id)
    render_streak_display(streak_data)

with col_progress:
    if dashboard["completed_challenges"]:
        avg_completion = 100.0
    elif dashboard["active_challenges"]:
        pcts = []
        for ch in dashboard["active_challenges"]:
            my_p = ch.get("my_progress", {})
            target = ch.get("target_value", 1)
            if target > 0:
                pcts.append(min(100, (my_p.get("current_progress", 0) / target) * 100))
        avg_completion = sum(pcts) / len(pcts) if pcts else 0
    else:
        avg_completion = 0

    fig_gauge = render_completion_gauge(avg_completion, "Avg Challenge Progress")
    st.plotly_chart(fig_gauge, use_container_width=True)

# Category & Difficulty Distribution
cat_data = get_category_distribution(user_id)
diff_data = get_difficulty_distribution(user_id)

if cat_data or diff_data:
    col_cat, col_diff = st.columns(2)
    with col_cat:
        if cat_data:
            fig_cat = render_category_donut(cat_data, "Your Challenge Categories")
            st.plotly_chart(fig_cat, use_container_width=True)
    with col_diff:
        if diff_data:
            fig_diff = render_difficulty_bar(diff_data, "Your Difficulty Mix")
            st.plotly_chart(fig_diff, use_container_width=True)


# ── Main Tabs ─────────────────────────────────────────────────────────────
st.markdown("---")
tab_browse, tab_my, tab_create, tab_leaderboard = st.tabs([
    "🌐 Browse Challenges", "🎯 My Challenges", "✨ Create Challenge", "🏆 Leaderboard"
])

# ── Browse Challenges ─────────────────────────────────────────────────────
with tab_browse:
    if not all_challenges:
        st.info("No challenges match your filters. Try broadening your search or create a new one!")
    else:
        for ch in all_challenges:
            overview = get_challenge_overview(ch["id"])
            if not overview:
                continue
            my_progress = None
            if dashboard:
                for m in dashboard.get("active_challenges", []) + dashboard.get("completed_challenges", []):
                    if m.get("id") == ch["id"]:
                        my_progress = m.get("my_progress")
                        break

            render_challenge_card(overview, my_progress=my_progress, show_join=True)

            # Action buttons
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if not my_progress:
                    if st.button("🚀 Join", key=f"join_{ch['id']}", use_container_width=True):
                        result = participate_in_challenge(ch["id"], user_id)
                        if result["success"]:
                            st.success(result["message"])
                            st.rerun()
                        else:
                            st.error(result["error"])
            with c2:
                if my_progress and not my_progress.get("is_completed"):
                    if st.button("📝 Log +1", key=f"log_{ch['id']}", use_container_width=True):
                        result = submit_progress(ch["id"], user_id, 1.0, "Logged via Browse")
                        if result["success"]:
                            st.success(result["message"])
                            st.rerun()
                        else:
                            st.error(result["error"])
            st.markdown("---")


# ── My Challenges ─────────────────────────────────────────────────────────
with tab_my:
    if not dashboard["active_challenges"] and not dashboard["completed_challenges"]:
        st.info("You haven't joined any challenges yet. Browse the list and jump in! 🚀")
    else:
        if dashboard["active_challenges"]:
            st.subheader("🔥 Active Challenges")
            for ch in dashboard["active_challenges"]:
                my_p = ch.get("my_progress", {})
                render_challenge_card(ch, my_progress=my_p)

                # Detailed progress section
                col_log, col_history = st.columns([1, 1])
                with col_log:
                    st.markdown("**📝 Log Progress**")
                    log_val = st.number_input("Value", min_value=0.1, value=1.0, step=0.5,
                                               key=f"logval_{ch['id']}")
                    log_note = st.text_input("Note (optional)", placeholder="e.g., Cycled to work today",
                                              key=f"lognote_{ch['id']}")
                    if st.button("✅ Submit", key=f"submit_{ch['id']}", use_container_width=True):
                        result = submit_progress(ch["id"], user_id, log_val, log_note)
                        if result["success"]:
                            st.success(result["message"])
                            st.rerun()
                        else:
                            st.error(result["error"])

                with col_history:
                    st.markdown("**📈 Progress History**")
                    daily = get_weekly_progress_data(ch["id"])
                    if daily:
                        fig_line = render_progress_line_chart(daily, f"{ch.get('title', '')} — Daily")
                        st.plotly_chart(fig_line, use_container_width=True)
                    else:
                        st.caption("No progress logged yet.")

                # Activity Feed
                from community_challenge_db import get_activity_feed
                feed = get_activity_feed(ch["id"], limit=5)
                if feed:
                    with st.expander("📰 Recent Activity"):
                        for item in feed:
                            render_feed_item(item)

                st.markdown("---")

        if dashboard["completed_challenges"]:
            st.subheader("✅ Completed Challenges")
            for ch in dashboard["completed_challenges"]:
                my_p = ch.get("my_progress", {})
                render_challenge_card(ch, my_progress=my_p)
                st.caption(f"Completed on: {my_p.get('completed_at', 'N/A')}")


# ── Create Challenge ──────────────────────────────────────────────────────
with tab_create:
    categories = get_available_categories()
    diff_meta = get_difficulty_meta()
    form_data = render_challenge_create_form(categories, diff_meta)

    if form_data["submitted"]:
        result = create_new_challenge(
            title=form_data["title"],
            description=form_data["description"],
            category=form_data["category"],
            difficulty=form_data["difficulty"],
            target_value=form_data["target_value"],
            target_unit=form_data["target_unit"],
            xp_reward=form_data["xp_reward"],
            duration_days=form_data["duration_days"],
            created_by=user_id,
        )
        if result["success"]:
            st.success(f"🎉 Challenge created! (ID: {result['challenge_id']})")
            st.balloons()
            st.rerun()
        else:
            st.error(result["error"])


# ── Leaderboard ───────────────────────────────────────────────────────────
with tab_leaderboard:
    active_ids = [ch["id"] for ch in all_challenges]

    if not active_ids:
        st.info("No active challenges to show leaderboards for.")
    else:
        selected_id = st.selectbox(
            "Select Challenge",
            active_ids,
            format_func=lambda cid: next((c["title"] for c in all_challenges if c["id"] == cid), str(cid)),
        )

        challenge = get_challenge_overview(selected_id)
        if not challenge:
            st.error("Challenge not found")
        else:
            st.markdown(f"### {challenge.get('badge_icon', '🏆')} {challenge['title']}")

            # Team Leaderboard
            from community_challenge_db import get_team_leaderboard, get_user_leaderboard
            teams = get_team_leaderboard(selected_id)
            users = get_user_leaderboard(selected_id)

            col_teams, col_users = st.columns(2)

            with col_teams:
                st.markdown("#### 👥 Teams")
                if teams:
                    fig_teams = render_team_comparison_chart(teams)
                    st.plotly_chart(fig_teams, use_container_width=True)

                    for rank, team in enumerate(teams, 1):
                        render_leaderboard_entry(
                            rank, team["team_name"], team["total_score"],
                            challenge.get("target_value", 1), team.get("team_icon", "🌿"),
                        )
                else:
                    st.caption("No teams yet. Start a team when joining!")

            with col_users:
                st.markdown("#### 🧑‍🤝‍🧑 Individuals")
                if users:
                    for rank, user in enumerate(users, 1):
                        is_me = user.get("user_id") == user_id
                        render_leaderboard_entry(
                            rank, user.get("username", f"User-{user['user_id']}"),
                            user.get("current_progress", 0),
                            challenge.get("target_value", 1),
                            is_user=is_me,
                        )
                else:
                    st.caption("No participants yet.")

            # Heatmap
            st.markdown("---")
            daily = get_weekly_progress_data(selected_id, days=28)
            if daily:
                fig_heat = render_progress_heatmap(daily, "Community Activity Heatmap")
                st.plotly_chart(fig_heat, use_container_width=True)

            # Full Activity Feed
            from community_challenge_db import get_activity_feed
            feed = get_activity_feed(selected_id, limit=20)
            if feed:
                with st.expander("📰 Full Activity Feed", expanded=False):
                    for item in feed:
                        render_feed_item(item)


# ── Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center; padding:16px; color:#9ca3af; font-size:13px;">
    🌱 Community Eco Challenges — Powered by EcoBuddy AI &nbsp;|&nbsp; Every action counts!
</div>
""", unsafe_allow_html=True)
