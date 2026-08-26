"""Community Sustainability Challenges – Join eco-challenges, form teams, compete on the leaderboard, and track your community's collective environmental impact."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random
import math

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Community Challenges", page_icon="🏆", layout="wide")

# ─── Theme ──────────────────────────────────────────────────────────────────
try:
    from styles.theme import apply_theme
    apply_theme()
except Exception:
    pass

# ─── Constants ──────────────────────────────────────────────────────────────
CHALLENGE_CATEGORIES = {
    "energy": {"label": "⚡ Energy", "color": "#f59e0b", "icon": "⚡"},
    "waste": {"label": "♻️ Waste Reduction", "color": "#22c55e", "icon": "♻️"},
    "transport": {"label": "🚲 Transportation", "color": "#3b82f6", "icon": "🚲"},
    "food": {"label": "🥗 Sustainable Food", "color": "#8b5cf6", "icon": "🥗"},
    "water": {"label": "💧 Water Conservation", "color": "#06b6d4", "icon": "💧"},
    "biodiversity": {"label": "🌿 Biodiversity", "color": "#10b981", "icon": "🌿"},
    "community": {"label": "🤝 Community Action", "color": "#f97316", "icon": "🤝"},
    "education": {"label": "📚 Eco Education", "color": "#ec4899", "icon": "📚"},
}

CHALLENGE_DURATIONS = {
    "1_week": {"label": "1 Week", "days": 7},
    "2_weeks": {"label": "2 Weeks", "days": 14},
    "1_month": {"label": "1 Month", "days": 30},
    "3_months": {"label": "3 Months", "days": 90},
}

DIFFICULTY_LEVELS = {
    "beginner": {"label": "🌱 Beginner", "color": "#22c55e", "points_multiplier": 1.0},
    "intermediate": {"label": "🌿 Intermediate", "color": "#f59e0b", "points_multiplier": 1.5},
    "advanced": {"label": "🌳 Advanced", "color": "#ef4444", "points_multiplier": 2.0},
    "expert": {"label": "🏔️ Expert", "color": "#8b5cf6", "points_multiplier": 3.0},
}

ACHIEVEMENT_TYPES = {
    "first_challenge": {"label": "🎯 First Steps", "description": "Join your first challenge", "points": 50},
    "week_streak": {"label": "🔥 Week Warrior", "description": "7-day participation streak", "points": 100},
    "month_streak": {"label": "💎 Monthly Master", "description": "30-day participation streak", "points": 500},
    "challenge_complete": {"label": "🏆 Challenge Champion", "description": "Complete a challenge", "points": 200},
    "top_10": {"label": "🌟 Top 10 Finisher", "description": "Finish in the top 10", "points": 300},
    "team_leader": {"label": "👑 Team Leader", "description": "Lead a team to completion", "points": 400},
    "community_hero": {"label": "🦸 Community Hero", "description": "Help 5 others complete challenges", "points": 600},
    "eco_streak": {"label": "♻️ Eco Streak", "description": "60-day sustainability streak", "points": 1000},
    "carbon_neutral": {"label": "🌍 Carbon Neutral", "description": "Offset 1 tonne of CO₂", "points": 750},
    "zero_waste": {"label": "🗑️ Zero Waste Warrior", "description": "30 days of zero waste", "points": 500},
}

# ─── Session State ──────────────────────────────────────────────────────────
if "challenges" not in st.session_state:
    st.session_state.challenges = _generate_sample_challenges()
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "name": "Eco Champion",
        "avatar": "🌱",
        "level": 12,
        "xp": 2450,
        "xp_next": 3000,
        "total_co2_saved": 1250,
        "challenges_joined": 8,
        "challenges_completed": 5,
        "current_streak": 14,
        "longest_streak": 21,
        "team_id": "TEAM-001",
        "achievements": ["first_challenge", "week_streak", "challenge_complete", "top_10"],
        "join_date": "2025-01-15",
    }
if "leaderboard" not in st.session_state:
    st.session_state.leaderboard = _generate_leaderboard()
if "community_teams" not in st.session_state:
    st.session_state.community_teams = _generate_teams()
if "activity_feed" not in st.session_state:
    st.session_state.activity_feed = _generate_activity_feed()


def _generate_sample_challenges():
    """Generate sample sustainability challenges."""
    challenges = []
    names = [
        ("Zero Waste Week", "waste", "Spend 7 days producing zero landfill waste"),
        ("Bike to Work Month", "transport", "Cycle or walk to work for 30 days"),
        ("Meatless Monday Marathon", "food", "Go meat-free every Monday for 4 weeks"),
        ("Energy Reduction Challenge", "energy", "Reduce home energy use by 20%"),
        ("Water Wise Warrior", "water", "Cut household water use by 25%"),
        ("Plant a Garden", "biodiversity", "Plant 10 native species in your garden"),
        ("Community Clean-Up", "community", "Organize or join a neighborhood cleanup"),
        ("Eco Education Sprint", "education", "Complete 5 eco-learning modules"),
        ("Plastic-Free February", "waste", "Eliminate single-use plastics for a month"),
        ("Solar Ambassador", "energy", "Help 3 neighbors understand solar benefits"),
        ("Composting Champion", "waste", "Start and maintain a compost bin for 30 days"),
        ("Public Transit Hero", "transport", "Use only public transit for 2 weeks"),
        ("Farmers Market Regular", "food", "Buy local produce weekly for a month"),
        ("Rain Harvest Helper", "water", "Install and use a rainwater collection system"),
        ("Bird Sanctuary Builder", "biodiversity", "Create a bird-friendly habitat"),
        ("Green Team Builder", "community", "Recruit 5 friends for sustainability"),
    ]

    for i, (name, cat, desc) in enumerate(names):
        meta = CHALLENGE_CATEGORIES[cat]
        diff = random.choice(list(DIFFICULTY_LEVELS.keys()))
        duration = random.choice(list(CHALLENGE_DURATIONS.keys()))
        dur_info = CHALLENGE_DURATIONS[duration]
        start = datetime.now() - timedelta(days=random.randint(0, 14))
        end = start + timedelta(days=dur_info["days"])

        participants = random.randint(15, 500)
        total_points = participants * random.randint(50, 200)

        challenges.append({
            "id": f"CHAL-{1000 + i}",
            "name": name,
            "description": desc,
            "category": cat,
            "category_label": meta["label"],
            "category_color": meta["color"],
            "difficulty": diff,
            "difficulty_label": DIFFICULTY_LEVELS[diff]["label"],
            "points_multiplier": DIFFICULTY_LEVELS[diff]["points_multiplier"],
            "duration": duration,
            "duration_label": dur_info["label"],
            "days": dur_info["days"],
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "participants": participants,
            "total_points": total_points,
            "status": "active" if end > datetime.now() else "completed",
            "progress": random.randint(10, 95),
            "daily_tasks": random.randint(3, 8),
            "tasks_completed": random.randint(1, 7),
            "joined": random.random() > 0.6,
            "tags": random.sample(["eco", "green", "community", "impact", "fun", "learning"], k=random.randint(2, 4)),
            "rules": [
                "Log your daily actions honestly",
                "Support fellow participants",
                "Share tips and encouragement",
                "Report progress at least once per day",
            ],
            "rewards": [
                f"{int(200 * DIFFICULTY_LEVELS[diff]['points_multiplier'])} XP",
                "🏆 Completion Badge",
                "📜 Digital Certificate",
            ],
        })
    return challenges


def _generate_leaderboard():
    """Generate sample leaderboard data."""
    names = [
        "Luna Greenleaf", "Solar Mike", "Eco Emma", "River Jackson", "Terra Chen",
        "Forest Williams", "Ocean Patel", "Sage Thompson", "Coral Martinez", "Breeze Kumar",
        "Willow Davis", "Sky Anderson", "Meadow Brown", "Storm Wilson", "Rain Taylor",
        "Sun Lee", "Cloud Garcia", "Wind Thomas", "Earth Moore", "Leaf Clark",
        "Petal Young", "Root Hall", "Seed Allen", "Moss Wright", "Fern King",
    ]

    leaderboard = []
    for i, name in enumerate(names):
        level = max(1, 20 - i + random.randint(-3, 3))
        xp = random.randint(1000, 5000)
        challenges_completed = random.randint(2, 15)
        co2_saved = random.randint(100, 3000)
        streak = random.randint(0, 45)

        leaderboard.append({
            "rank": i + 1,
            "name": name,
            "avatar": random.choice(["🌱", "🌿", "🌳", "🍃", "🌻", "🌸", "🍀", "🌺", "🌾", "🌵"]),
            "level": level,
            "xp": xp,
            "challenges_completed": challenges_completed,
            "co2_saved_kg": co2_saved,
            "current_streak": streak,
            "badges": random.randint(3, 12),
        })

    return sorted(leaderboard, key=lambda x: x["xp"], reverse=True)


def _generate_teams():
    """Generate sample teams."""
    teams = [
        {"id": "TEAM-001", "name": "Green Warriors", "members": 12, "xp": 8500, "co2_saved": 4200, "rank": 1, "avatar": "⚔️"},
        {"id": "TEAM-002", "name": "Eco Avengers", "members": 10, "xp": 7200, "co2_saved": 3600, "rank": 2, "avatar": "🦸"},
        {"id": "TEAM-003", "name": "Nature's Guardians", "members": 15, "xp": 6800, "co2_saved": 3100, "rank": 3, "avatar": "🛡️"},
        {"id": "TEAM-004", "name": "Solar Squad", "members": 8, "xp": 5900, "co2_saved": 2800, "rank": 4, "avatar": "☀️"},
        {"id": "TEAM-005", "name": "Carbon Crushers", "members": 11, "xp": 5400, "co2_saved": 2500, "rank": 5, "avatar": "💪"},
        {"id": "TEAM-006", "name": "Ocean Defenders", "members": 9, "xp": 4800, "co2_saved": 2200, "rank": 6, "avatar": "🌊"},
        {"id": "TEAM-007", "name": "Rainforest Rangers", "members": 13, "xp": 4300, "co2_saved": 1900, "rank": 7, "avatar": "🌴"},
        {"id": "TEAM-008", "name": "Zero Waste Zealots", "members": 7, "xp": 3800, "co2_saved": 1600, "rank": 8, "avatar": "♻️"},
    ]
    return teams


def _generate_activity_feed():
    """Generate recent activity feed."""
    activities = []
    actions = [
        ("completed a challenge", "🏆", 200),
        ("earned a badge", "🎖️", 50),
        ("joined a team", "👥", 25),
        ("logged daily action", "📝", 10),
        ("reached a streak", "🔥", 100),
        ("saved 10kg CO₂", "🌍", 75),
        ("helped a teammate", "🤝", 30),
        ("shared a tip", "💡", 15),
    ]

    names = ["Luna", "Solar Mike", "Eco Emma", "River", "Terra", "Forest", "Ocean", "Sage"]
    for i in range(20):
        action_text, icon, xp = random.choice(actions)
        activities.append({
            "time": (datetime.now() - timedelta(minutes=random.randint(1, 1440))).strftime("%H:%M"),
            "user": random.choice(names),
            "action": action_text,
            "icon": icon,
            "xp": xp,
        })
    return sorted(activities, key=lambda x: x["time"], reverse=True)


# ─── Helpers ────────────────────────────────────────────────────────────────

def render_xp_bar(current, maximum, height=12):
    """Render an XP progress bar."""
    pct = min(100, (current / maximum) * 100) if maximum > 0 else 0
    color = "#22c55e" if pct >= 80 else "#f59e0b" if pct >= 50 else "#3b82f6"
    st.markdown(f"""
    <div style="background:#1e293b;border-radius:6px;height:{height}px;overflow:hidden">
        <div style="background:{color};width:{pct}%;height:100%;border-radius:6px;transition:width 0.5s"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:#94a3b8;margin-top:2px">
        <span>{current:,} XP</span><span>{maximum:,} XP</span>
    </div>
    """, unsafe_allow_html=True)


# ─── Main Rendering ─────────────────────────────────────────────────────────

def render_community_challenges_hub():
    st.title("🏆 Community Sustainability Challenges")
    st.markdown("Join eco-challenges, compete with your community, climb the leaderboard, and make a real environmental impact together!")

    profile = st.session_state.user_profile

    # User header
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    with c1:
        st.markdown(f"### {profile['avatar']} {profile['name']}")
        st.caption(f"Level {profile['level']} • Joined {profile['join_date']}")
    with c2:
        st.metric("🔥 Streak", f"{profile['current_streak']} days")
    with c3:
        st.metric("🌍 CO₂ Saved", f"{profile['total_co2_saved']:,} kg")
    with c4:
        st.metric("🏆 Challenges", f"{profile['challenges_completed']}/{profile['challenges_joined']}")

    render_xp_bar(profile["xp"], profile["xp_next"])
    st.divider()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🎯 Active Challenges",
        "🏆 Leaderboard",
        "👥 Teams",
        "🎖️ Achievements",
        "📊 My Progress",
        "📰 Activity Feed",
        "🆕 Create Challenge",
    ])

    # ═══════════════════════════════════════════
    # TAB 1: Active Challenges
    # ═══════════════════════════════════════════
    with tab1:
        st.subheader("🎯 Available Challenges")

        # Filters
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            filter_cat = st.selectbox("Category", ["All"] + [v["label"] for v in CHALLENGE_CATEGORIES.values()])
        with fc2:
            filter_diff = st.selectbox("Difficulty", ["All"] + [v["label"] for v in DIFFICULTY_LEVELS.values()])
        with fc3:
            filter_dur = st.selectbox("Duration", ["All"] + [v["label"] for v in CHALLENGE_DURATIONS.values()])
        with fc4:
            filter_status = st.selectbox("Status", ["All", "Active", "Completed", "Joined"])

        # Apply filters
        challenges = st.session_state.challenges
        filtered = challenges

        if filter_cat != "All":
            cat_key = [k for k, v in CHALLENGE_CATEGORIES.items() if v["label"] == filter_cat][0]
            filtered = [c for c in filtered if c["category"] == cat_key]
        if filter_diff != "All":
            diff_key = [k for k, v in DIFFICULTY_LEVELS.items() if v["label"] == filter_diff][0]
            filtered = [c for c in filtered if c["difficulty"] == diff_key]
        if filter_dur != "All":
            dur_key = [k for k, v in CHALLENGE_DURATIONS.items() if v["label"] == filter_dur][0]
            filtered = [c for c in filtered if c["duration"] == dur_key]
        if filter_status == "Active":
            filtered = [c for c in filtered if c["status"] == "active"]
        elif filter_status == "Completed":
            filtered = [c for c in filtered if c["status"] == "completed"]
        elif filter_status == "Joined":
            filtered = [c for c in filtered if c["joined"]]

        st.caption(f"Showing {len(filtered)} challenges")

        for ch in filtered:
            with st.container():
                cols = st.columns([4, 2, 2, 2])
                with cols[0]:
                    st.markdown(f"**{CHALLENGE_CATEGORIES.get(ch['category'], {}).get('icon', '🎯')} {ch['name']}**")
                    st.caption(f"{ch['description']}")
                    st.caption(f"{ch['difficulty_label']} • {ch['duration_label']} • {ch['category_label']}")
                    # Tags
                    tag_html = " ".join([f'<span style="background:#1e293b;padding:2px 6px;border-radius:4px;font-size:10px;margin-right:4px">#{t}</span>' for t in ch["tags"]])
                    st.markdown(tag_html, unsafe_allow_html=True)

                with cols[1]:
                    st.metric("👥 Participants", f"{ch['participants']:,}")
                    st.metric("⭐ Points", f"{ch['total_points']:,}")
                    days_left = max(0, (datetime.strptime(ch["end_date"], "%Y-%m-%d") - datetime.now()).days)
                    st.metric("📅 Days Left", days_left)

                with cols[2]:
                    if ch["joined"]:
                        st.progress(ch["progress"] / 100)
                        st.caption(f"Progress: {ch['progress']}%")
                        st.caption(f"Tasks: {ch['tasks_completed']}/{ch['daily_tasks']} today")
                    else:
                        st.markdown(f"**Rules:**")
                        for rule in ch["rules"][:2]:
                            st.caption(f"• {rule}")

                with cols[3]:
                    if ch["joined"]:
                        if st.button("📊 View", key=f"view_{ch['id']}"):
                            st.session_state[f"show_detail_{ch['id']}"] = True
                    else:
                        if st.button("🚀 Join", key=f"join_{ch['id']}", type="primary"):
                            ch["joined"] = True
                            ch["participants"] += 1
                            profile["challenges_joined"] += 1
                            st.success(f"🎉 Joined '{ch['name']}'!")
                            st.rerun()
                st.divider()

    # ═══════════════════════════════════════════
    # TAB 2: Leaderboard
    # ═══════════════════════════════════════════
    with tab2:
        st.subheader("🏆 Community Leaderboard")

        lb_view = st.radio("View", ["Individual", "Teams"], horizontal=True, key="lb_view")

        if lb_view == "Individual":
            # Top 3 podium
            top3 = st.session_state.leaderboard[:3]
            podium_cols = st.columns(3)
            medals = ["🥇", "🥈", "🥉"]
            for i, (col, user) in enumerate(zip(podium_cols, top3)):
                with col:
                    st.markdown(f"""
                    <div style="text-align:center;padding:20px;background:linear-gradient(135deg,{'#fefce8' if i==0 else '#f1f5f9' if i==1 else '#fef2f2'});border-radius:16px;border:2px solid {'#f59e0b' if i==0 else '#94a3b8' if i==1 else '#cd7c2f'}">
                        <div style="font-size:40px">{medals[i]}</div>
                        <div style="font-size:24px;margin:8px 0">{user['avatar']}</div>
                        <div style="font-weight:bold;font-size:16px">{user['name']}</div>
                        <div style="color:#6b7280;font-size:13px">Level {user['level']}</div>
                        <div style="font-size:20px;font-weight:bold;color:#22c55e;margin-top:8px">{user['xp']:,} XP</div>
                        <div style="font-size:12px;color:#94a3b8">{user['challenges_completed']} challenges • {user['badges']} badges</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()

            # Full leaderboard
            lb_data = st.session_state.leaderboard
            lb_df = pd.DataFrame(lb_data)
            lb_df.index = lb_df.index + 1
            display_df = lb_df[["rank", "name", "avatar", "level", "xp", "challenges_completed", "co2_saved_kg", "current_streak", "badges"]].copy()
            display_df.columns = ["Rank", "Name", "", "Level", "XP", "Completed", "CO₂ Saved (kg)", "Streak", "Badges"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # XP distribution chart
            fig = px.bar(lb_df.head(15), x="name", y="xp", title="Top 15 XP Distribution",
                         color="level", color_continuous_scale="Viridis")
            fig.update_layout(height=350, xaxis_title="", yaxis_title="XP")
            st.plotly_chart(fig, use_container_width=True)

        else:
            # Team leaderboard
            teams = st.session_state.community_teams
            team_df = pd.DataFrame(teams)

            # Top 3 teams podium
            podium_cols = st.columns(3)
            medals = ["🥇", "🥈", "🥉"]
            for i in range(3):
                team = teams[i]
                with podium_cols[i]:
                    st.markdown(f"""
                    <div style="text-align:center;padding:20px;background:linear-gradient(135deg,{'#fefce8' if i==0 else '#f1f5f9' if i==1 else '#fef2f2'});border-radius:16px">
                        <div style="font-size:36px">{medals[i]} {team['avatar']}</div>
                        <div style="font-weight:bold;font-size:16px;margin:8px 0">{team['name']}</div>
                        <div style="font-size:20px;font-weight:bold;color:#22c55e">{team['xp']:,} XP</div>
                        <div style="font-size:12px;color:#94a3b8">{team['members']} members • {team['co2_saved']:,}kg CO₂</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()

            # Team table
            team_display = team_df[["rank", "avatar", "name", "members", "xp", "co2_saved"]].copy()
            team_display.columns = ["Rank", "", "Team", "Members", "XP", "CO₂ Saved (kg)"]
            st.dataframe(team_display, use_container_width=True, hide_index=True)

            # Team comparison
            fig = px.bar(team_df, x="name", y=["xp", "co2_saved"], title="Team Performance",
                         barmode="group", color_discrete_map={"xp": "#3b82f6", "co2_saved": "#22c55e"})
            fig.update_layout(height=350, xaxis_title="", legend_title="Metric")
            st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════
    # TAB 3: Teams
    # ═══════════════════════════════════════════
    with tab3:
        st.subheader("👥 Community Teams")

        tc1, tc2 = st.columns([3, 1])
        with tc2:
            if st.button("🆕 Create Team", type="primary"):
                st.session_state.show_create_team = True

        teams = st.session_state.community_teams
        for team in teams:
            is_member = team["id"] == profile.get("team_id")
            with st.container():
                cols = st.columns([4, 2, 2, 2])
                with cols[0]:
                    st.markdown(f"**{team['avatar']} {team['name']}**")
                    st.caption(f"#{team['rank']} ranked • {team['members']} members")
                with cols[1]:
                    st.metric("⭐ XP", f"{team['xp']:,}")
                with cols[2]:
                    st.metric("🌍 CO₂", f"{team['co2_saved']:,} kg")
                with cols[3]:
                    if is_member:
                        st.success("✅ Your Team")
                    else:
                        if st.button("Join", key=f"join_team_{team['id']}"):
                            profile["team_id"] = team["id"]
                            team["members"] += 1
                            st.success(f"Joined {team['name']}!")
                            st.rerun()
                st.divider()

        # Create Team Modal
        if st.session_state.get("show_create_team"):
            with st.form("create_team"):
                st.subheader("🆕 Create New Team")
                team_name = st.text_input("Team Name")
                team_avatar = st.selectbox("Avatar", ["⚔️", "🦸", "🛡️", "☀️", "💪", "🌊", "🌴", "♻️", "🌍", "🌱", "⚡", "🔥"])
                team_desc = st.text_area("Description")
                if st.form_submit_button("Create Team"):
                    new_team = {
                        "id": f"TEAM-{random.randint(100, 999)}",
                        "name": team_name or "New Team",
                        "members": 1,
                        "xp": 0,
                        "co2_saved": 0,
                        "rank": len(teams) + 1,
                        "avatar": team_avatar,
                    }
                    st.session_state.community_teams.append(new_team)
                    profile["team_id"] = new_team["id"]
                    st.success(f"Created '{team_name}'!")
                    st.session_state.show_create_team = False
                    st.rerun()

    # ═══════════════════════════════════════════
    # TAB 4: Achievements
    # ═══════════════════════════════════════════
    with tab4:
        st.subheader("🎖️ Achievements & Badges")

        earned = profile.get("achievements", [])
        total_earned_points = sum(ACHIEVEMENT_TYPES[a]["points"] for a in earned)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("🏅 Earned", f"{len(earned)}/{len(ACHIEVEMENT_TYPES)}")
        with c2:
            st.metric("⭐ Badge Points", f"{total_earned_points}")
        with c3:
            st.metric("📊 Completion", f"{len(earned) / len(ACHIEVEMENT_TYPES) * 100:.0f}%")

        st.divider()

        # Achievement grid
        achievement_cols = st.columns(3)
        for i, (key, ach) in enumerate(ACHIEVEMENT_TYPES.items()):
            is_earned = key in earned
            with achievement_cols[i % 3]:
                bg = "linear-gradient(135deg, #f0fdf4, #dcfce7)" if is_earned else "linear-gradient(135deg, #f8fafc, #f1f5f9)"
                border = "#22c55e" if is_earned else "#e2e8f0"
                opacity = "1" if is_earned else "0.5"
                st.markdown(f"""
                <div style="padding:16px;background:{bg};border:2px solid {border};border-radius:12px;opacity:{opacity};margin-bottom:12px">
                    <div style="font-size:24px;text-align:center;margin-bottom:8px">{ach['label']}</div>
                    <div style="font-size:12px;color:#6b7280;text-align:center">{ach['description']}</div>
                    <div style="font-size:14px;font-weight:bold;color:#22c55e;text-align:center;margin-top:8px">+{ach['points']} XP</div>
                    <div style="font-size:10px;color:{'#22c55e' if is_earned else '#94a3b8'};text-align:center;margin-top:4px">
                        {'✅ Earned' if is_earned else '🔒 Locked'}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Progress to next achievements
        st.subheader("📈 Closest to Earning")
        locked = [k for k in ACHIEVEMENT_TYPES if k not in earned]
        if locked:
            for key in locked[:3]:
                ach = ACHIEVEMENT_TYPES[key]
                progress = random.randint(30, 85)
                st.markdown(f"**{ach['label']}** — {ach['description']}")
                st.progress(progress / 100)
                st.caption(f"{progress}% complete • +{ach['points']} XP when earned")

    # ═══════════════════════════════════════════
    # TAB 5: My Progress
    # ═══════════════════════════════════════════
    with tab5:
        st.subheader("📊 My Sustainability Progress")

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("🎯 Level", profile["level"])
        with c2:
            st.metric("⭐ Total XP", f"{profile['xp']:,}")
        with c3:
            st.metric("🌍 CO₂ Saved", f"{profile['total_co2_saved']:,} kg")
        with c4:
            st.metric("🔥 Current Streak", f"{profile['current_streak']}d")
        with c5:
            st.metric("🏅 Badges", len(profile["achievements"]))

        st.divider()

        # XP progression
        st.subheader("📈 Level Progression")
        levels_data = []
        for lvl in range(1, profile["level"] + 2):
            xp_needed = lvl * 250
            xp_earned = min(xp_needed, profile["xp"] - sum(range(1, lvl) * [250]) if lvl <= profile["level"] else 0)
            levels_data.append({"Level": lvl, "XP Needed": xp_needed, "Status": "Completed" if lvl < profile["level"] else "Current" if lvl == profile["level"] else "Locked"})

        levels_df = pd.DataFrame(levels_data)
        fig = px.bar(levels_df, x="Level", y="XP Needed", color="Status",
                     color_discrete_map={"Completed": "#22c55e", "Current": "#3b82f6", "Locked": "#e2e8f0"},
                     title="XP Required per Level")
        fig.update_layout(height=300, xaxis_title="Level", yaxis_title="XP")
        st.plotly_chart(fig, use_container_width=True)

        # CO2 impact over time
        st.subheader("🌍 CO₂ Impact Timeline")
        months = [(datetime.now() - timedelta(days=30 * i)).strftime("%b %Y") for i in range(11, -1, -1)]
        co2_data = [random.randint(50, 200) for _ in range(12)]
        co2_cumulative = []
        total = 0
        for v in co2_data:
            total += v
            co2_cumulative.append(total)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=months, y=co2_data, name="Monthly CO₂ Saved", marker_color="#22c55e"))
        fig.add_trace(go.Scatter(x=months, y=co2_cumulative, name="Cumulative", line=dict(color="#f59e0b", width=2)))
        fig.update_layout(height=350, title="CO₂ Savings Over Time", xaxis_title="", yaxis_title="kg CO₂")
        st.plotly_chart(fig, use_container_width=True)

        # Challenge history
        st.subheader("🎯 Challenge History")
        completed = [
            {"Challenge": "Zero Waste Week", "Category": "♻️ Waste", "Duration": "1 Week", "Result": "✅ Completed", "Points": 200},
            {"Challenge": "Bike to Work", "Category": "🚲 Transport", "Duration": "1 Month", "Result": "✅ Completed", "Points": 450},
            {"Challenge": "Meatless Monday", "Category": "🥗 Food", "Duration": "4 Weeks", "Result": "✅ Completed", "Points": 300},
            {"Challenge": "Energy Saver", "Category": "⚡ Energy", "Duration": "2 Weeks", "Result": "⚡ In Progress", "Points": 150},
            {"Challenge": "Water Wise", "Category": "💧 Water", "Duration": "1 Month", "Result": "⏰ Upcoming", "Points": 0},
        ]
        st.dataframe(pd.DataFrame(completed), use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════
    # TAB 6: Activity Feed
    # ═══════════════════════════════════════════
    with tab6:
        st.subheader("📰 Community Activity Feed")

        feed = st.session_state.activity_feed
        for item in feed[:15]:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;padding:10px;margin:4px 0;background:#f8fafc;border-radius:8px;border-left:3px solid #22c55e">
                <span style="font-size:20px">{item['icon']}</span>
                <div style="flex:1">
                    <span style="font-weight:600">{item['user']}</span>
                    <span style="color:#6b7280"> {item['action']}</span>
                    <span style="color:#22c55e;font-weight:600"> +{item['xp']} XP</span>
                </div>
                <span style="color:#94a3b8;font-size:12px">{item['time']}</span>
            </div>
            """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════
    # TAB 7: Create Challenge
    # ═══════════════════════════════════════════
    with tab7:
        st.subheader("🆕 Create a Community Challenge")

        with st.form("create_challenge"):
            c1, c2 = st.columns(2)
            with c1:
                ch_name = st.text_input("Challenge Name")
                ch_desc = st.text_area("Description")
                ch_category = st.selectbox("Category", list(CHALLENGE_CATEGORIES.keys()),
                                            format_func=lambda x: CHALLENGE_CATEGORIES[x]["label"])
                ch_difficulty = st.selectbox("Difficulty", list(DIFFICULTY_LEVELS.keys()),
                                              format_func=lambda x: DIFFICULTY_LEVELS[x]["label"])
            with c2:
                ch_duration = st.selectbox("Duration", list(CHALLENGE_DURATIONS.keys()),
                                            format_func=lambda x: CHALLENGE_DURATIONS[x]["label"])
                ch_tasks = st.number_input("Daily Tasks Required", 1, 20, 5)
                ch_rewards = st.text_area("Rewards (one per line)", "🏆 Completion Badge\n📜 Certificate\n⭐ Bonus XP")
                ch_rules = st.text_area("Rules (one per line)", "Log daily actions\nBe honest\nSupport others")

            if st.form_submit_button("🚀 Create Challenge", type="primary"):
                if ch_name:
                    new_challenge = {
                        "id": f"CHAL-{random.randint(1000, 9999)}",
                        "name": ch_name,
                        "description": ch_desc or "A community sustainability challenge",
                        "category": ch_category,
                        "category_label": CHALLENGE_CATEGORIES[ch_category]["label"],
                        "category_color": CHALLENGE_CATEGORIES[ch_category]["color"],
                        "difficulty": ch_difficulty,
                        "difficulty_label": DIFFICULTY_LEVELS[ch_difficulty]["label"],
                        "points_multiplier": DIFFICULTY_LEVELS[ch_difficulty]["points_multiplier"],
                        "duration": ch_duration,
                        "duration_label": CHALLENGE_DURATIONS[ch_duration]["label"],
                        "days": CHALLENGE_DURATIONS[ch_duration]["days"],
                        "start_date": datetime.now().strftime("%Y-%m-%d"),
                        "end_date": (datetime.now() + timedelta(days=CHALLENGE_DURATIONS[ch_duration]["days"])).strftime("%Y-%m-%d"),
                        "participants": 1,
                        "total_points": 100,
                        "status": "active",
                        "progress": 0,
                        "daily_tasks": ch_tasks,
                        "tasks_completed": 0,
                        "joined": True,
                        "tags": ["community", "new"],
                        "rules": [r.strip() for r in ch_rules.split("\n") if r.strip()],
                        "rewards": [r.strip() for r in ch_rewards.split("\n") if r.strip()],
                    }
                    st.session_state.challenges.append(new_challenge)
                    profile["challenges_joined"] += 1
                    st.success(f"🎉 Challenge '{ch_name}' created! Share it with your community.")
                else:
                    st.error("Please enter a challenge name.")


# ─── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__" or True:
    render_community_challenges_hub()
