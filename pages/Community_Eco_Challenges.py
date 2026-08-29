"""
pages/Community_Eco_Challenges.py
----------------------------------
Streamlit page: Community Eco Challenges.

Join sustainability challenges, compete on leaderboards, track streaks,
form teams, and earn achievement badges for eco-friendly actions.
"""

import math
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Community Eco Challenges",
    page_icon="🏆",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Challenge categories
# ---------------------------------------------------------------------------

CHALLENGE_CATEGORIES = {
    "Energy": {"icon": "⚡", "color": "#ffc107", "points_per_action": 10},
    "Water": {"icon": "💧", "color": "#4a90d9", "points_per_action": 8},
    "Waste": {"icon": "♻️", "color": "#28a745", "points_per_action": 12},
    "Food": {"icon": "🥗", "color": "#fd7e14", "points_per_action": 9},
    "Transport": {"icon": "🚲", "color": "#20c997", "points_per_action": 11},
    "Nature": {"icon": "🌳", "color": "#198754", "points_per_action": 15},
    "Shopping": {"icon": "🛒", "color": "#e83e8c", "points_per_action": 7},
    "Community": {"icon": "👥", "color": "#6f42c1", "points_per_action": 14},
}

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

def _generate_mock_challenges() -> list[dict[str, Any]]:
    """Generate mock active and upcoming challenges."""
    challenges = [
        {"id": "CH-001", "title": "🚶 Walk or Bike to Work Week", "category": "Transport", "description": "Use zero-emission transport for your commute for 5 consecutive days.",
         "points": 150, "duration": "7 days", "difficulty": "Medium", "participants": 342, "target": 5,
         "icon": "🚲", "started": "2026-08-25", "ends": "2026-09-01", "status": "active"},
        {"id": "CH-002", "title": "🧊 Zero Food Waste Challenge", "category": "Food", "description": "Track your food and ensure zero edible food goes to waste for 14 days.",
         "points": 200, "duration": "14 days", "difficulty": "Hard", "participants": 189, "target": 14,
         "icon": "🥗", "started": "2026-08-20", "ends": "2026-09-03", "status": "active"},
        {"id": "CH-003", "title": "💡 Energy Saver Sprint", "category": "Energy", "description": "Reduce your daily electricity usage by 20% for 10 days.",
         "points": 180, "duration": "10 days", "difficulty": "Medium", "participants": 456, "target": 10,
         "icon": "⚡", "started": "2026-08-22", "ends": "2026-09-01", "status": "active"},
        {"id": "CH-004", "title": "💧 Water Conservation Quest", "category": "Water", "description": "Keep daily water usage under 100 liters for 7 days.",
         "points": 120, "duration": "7 days", "difficulty": "Easy", "participants": 523, "target": 7,
         "icon": "💧", "started": "2026-08-27", "ends": "2026-09-03", "status": "active"},
        {"id": "CH-005", "title": "♻️ Plastic-Free July (Extended)", "category": "Waste", "description": "Go 30 days without single-use plastic. Track every avoided item.",
         "points": 500, "duration": "30 days", "difficulty": "Expert", "participants": 98, "target": 30,
         "icon": "♻️", "started": "2026-08-01", "ends": "2026-08-31", "status": "active"},
        {"id": "CH-006", "title": "🌳 Plant a Tree Weekend", "category": "Nature", "description": "Plant at least one tree or help with community tree planting.",
         "points": 200, "duration": "2 days", "difficulty": "Easy", "participants": 678, "target": 1,
         "icon": "🌳", "started": "2026-08-30", "ends": "2026-08-31", "status": "active"},
        {"id": "CH-007", "title": "🛒 Sustainable Shopping Sprint", "category": "Shopping", "description": "Buy only secondhand or certified sustainable products for 2 weeks.",
         "points": 175, "duration": "14 days", "difficulty": "Medium", "participants": 234, "target": 14,
         "icon": "🛒", "started": "2026-09-01", "ends": "2026-09-15", "status": "upcoming"},
        {"id": "CH-008", "title": "👥 Neighborhood Cleanup Rally", "category": "Community", "description": "Organize or join a neighborhood cleanup event this month.",
         "points": 300, "duration": "30 days", "difficulty": "Medium", "participants": 412, "target": 3,
         "icon": "👥", "started": "2026-09-01", "ends": "2026-09-30", "status": "upcoming"},
    ]
    return challenges


def _generate_mock_leaderboard() -> list[dict[str, Any]]:
    """Generate mock leaderboard data."""
    import random
    random.seed(42)

    users = [
        {"name": "EcoWarrior99", "avatar": "🦸", "city": "Portland"},
        {"name": "GreenMachine", "avatar": "🤖", "city": "Seattle"},
        {"name": "TreeHugger42", "avatar": "🌿", "city": "Austin"},
        {"name": "ZeroWasteHero", "avatar": "♻️", "city": "San Francisco"},
        {"name": "SolarPowered", "avatar": "☀️", "city": "Denver"},
        {"name": "BikeRider", "avatar": "🚲", "city": "Amsterdam"},
        {"name": "OceanDefender", "avatar": "🌊", "city": "Miami"},
        {"name": "CompostKing", "avatar": "👑", "city": "Portland"},
        {"name": "WindWalker", "avatar": "💨", "city": "Chicago"},
        {"name": "RainHarvester", "avatar": "🌧️", "city": "Melbourne"},
        {"name": "VeganVibes", "avatar": "🌱", "city": "Brooklyn"},
        {"name": "SmartHomeFan", "avatar": "🏠", "city": "Austin"},
        {"name": "ThriftyFinds", "avatar": "🔍", "city": "Nashville"},
        {"name": "CarbonCutter", "avatar": "✂️", "city": "Portland"},
        {"name": "NatureLover", "avatar": "🦋", "city": "Boulder"},
    ]

    board = []
    for i, user in enumerate(users):
        points = random.randint(800, 5000)
        challenges_done = random.randint(5, 25)
        streak = random.randint(1, 45)
        co2_saved = round(random.uniform(50, 500), 1)
        badges_count = random.randint(3, 15)
        board.append({
            "rank": i + 1,
            **user,
            "points": points,
            "challenges_completed": challenges_done,
            "current_streak": streak,
            "best_streak": streak + random.randint(0, 15),
            "co2_saved_kg": co2_saved,
            "badges": badges_count,
            "level": min(points // 500 + 1, 10),
        })

    board.sort(key=lambda x: x["points"], reverse=True)
    for i, b in enumerate(board):
        b["rank"] = i + 1
    return board


def _generate_mock_badges() -> list[dict[str, Any]]:
    """Generate mock achievement badges."""
    return [
        {"name": "🌱 First Step", "desc": "Complete your first challenge", "icon": "🌱", "rarity": "Common", "unlocked": True, "date": "2026-07-15"},
        {"name": "🔥 Week Warrior", "desc": "7-day streak", "icon": "🔥", "rarity": "Uncommon", "unlocked": True, "date": "2026-07-22"},
        {"name": "⚡ Energy Elite", "desc": "Complete 5 energy challenges", "icon": "⚡", "rarity": "Rare", "unlocked": True, "date": "2026-08-01"},
        {"name": "💧 Water Whisperer", "desc": "Save 10,000 liters total", "icon": "💧", "rarity": "Rare", "unlocked": True, "date": "2026-08-05"},
        {"name": "♻️ Recycling Rockstar", "desc": "Divert 100 kg from landfill", "icon": "♻️", "rarity": "Epic", "unlocked": True, "date": "2026-08-10"},
        {"name": "🚲 Commute Champion", "desc": "30 days of green commuting", "icon": "🚲", "rarity": "Epic", "unlocked": True, "date": "2026-08-15"},
        {"name": "🌳 Nature Guardian", "desc": "Plant 10 trees", "icon": "🌳", "rarity": "Rare", "unlocked": False, "progress": 7},
        {"name": "🔥 Month Master", "desc": "30-day streak", "icon": "🔥", "rarity": "Legendary", "unlocked": False, "progress": 22},
        {"name": "🏆 Grand Champion", "desc": "Reach #1 on leaderboard", "icon": "🏆", "rarity": "Legendary", "unlocked": False, "progress": None},
        {"name": "👥 Team Builder", "desc": "Recruit 5 team members", "icon": "👥", "rarity": "Uncommon", "unlocked": False, "progress": 3},
        {"name": "🌍 Global Citizen", "desc": "Complete challenges from 5 categories", "icon": "🌍", "rarity": "Rare", "unlocked": False, "progress": 4},
        {"name": "♻️ Zero Waste Legend", "desc": "Complete the 30-day plastic-free challenge", "icon": "♻️", "rarity": "Legendary", "unlocked": False, "progress": 18},
    ]


def _generate_mock_teams() -> list[dict[str, Any]]:
    """Generate mock team competition data."""
    return [
        {"name": "Green Hawks", "members": 12, "total_points": 4560, "avg_streak": 18, "avatar": "🦅", "captain": "EcoWarrior99",
         "wins": 5, "category_focus": "Energy"},
        {"name": "Eco Titans", "members": 15, "total_points": 5230, "avg_streak": 22, "avatar": "💪", "captain": "GreenMachine",
         "wins": 7, "category_focus": "Transport"},
        {"name": "Nature's Army", "members": 10, "total_points": 3890, "avg_streak": 15, "avatar": "🌲", "captain": "TreeHugger42",
         "wins": 3, "category_focus": "Nature"},
        {"name": "Zero Waste Warriors", "members": 8, "total_points": 3420, "avg_streak": 20, "avatar": "♻️", "captain": "ZeroWasteHero",
         "wins": 4, "category_focus": "Waste"},
        {"name": "Aqua Savers", "members": 11, "total_points": 4100, "avg_streak": 16, "avatar": "💧", "captain": "RainHarvester",
         "wins": 2, "category_focus": "Water"},
    ]


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_active_challenges(challenges: list[dict]):
    """Render active and upcoming challenges."""
    st.subheader("🎯 Challenges")

    active = [c for c in challenges if c["status"] == "active"]
    upcoming = [c for c in challenges if c["status"] == "upcoming"]

    if active:
        st.markdown(f"**🟢 Active ({len(active)})**")
        for c in active:
            cat = CHALLENGE_CATEGORIES.get(c["category"], {})
            cat_color = cat.get("color", "#666")
            cat_icon = cat.get("icon", "🎯")

            # Progress simulation
            import random
            random.seed(hash(c["id"]))
            progress = random.randint(1, c["target"])
            pct = progress / c["target"] * 100

            with st.expander(f"{c['icon']} **{c['title']}** — {c['points']} pts | {c['participants']} joined", expanded=False):
                st.markdown(f"{c['description']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Category", f"{cat_icon} {c['category']}")
                c2.metric("Duration", c["duration"])
                c3.metric("Difficulty", c["difficulty"])
                c4.metric("Points", f"🏆 {c['points']}")

                # Progress bar
                st.markdown(f"**Your Progress:** {progress}/{c['target']}")
                color = cat_color
                st.markdown(
                    f'<div style="background:#1e1e2e;border-radius:6px;height:20px;margin:6px 0">'
                    f'<div style="width:{pct}%;background:{color};border-radius:6px;height:100%;display:flex;align-items:center;justify-content:center;color:white;font-size:0.75em;font-weight:600">{progress}/{c["target"]}</div></div>',
                    unsafe_allow_html=True,
                )

                # Days remaining
                end_date = datetime.strptime(c["ends"], "%Y-%m-%d")
                days_left = (end_date - datetime.now()).days
                st.caption(f"⏰ {max(days_left, 0)} days remaining | Started {c['started']}")

    if upcoming:
        st.markdown(f"**🔵 Upcoming ({len(upcoming)})**")
        for c in upcoming:
            cat = CHALLENGE_CATEGORIES.get(c["category"], {})
            st.markdown(
                f'<div style="border:1px solid #333;border-radius:8px;padding:10px;margin:6px 0;background:#f8f9fa">'
                f'{c["icon"]} <strong>{c["title"]}</strong> — {c["points"]} pts | {c["duration"]}<br/>'
                f'<span style="font-size:0.85em;color:#666">{c["description"][:80]}...</span></div>',
                unsafe_allow_html=True,
            )


def _render_leaderboard(board: list[dict]):
    """Render community leaderboard."""
    st.subheader("🏆 Leaderboard")

    # Top 3 podium
    if len(board) >= 3:
        podium = [board[1], board[0], board[2]]  # 2nd, 1st, 3rd
        podium_heights = [160, 200, 140]
        medals = ["🥈", "🥇", "🥉"]
        cols = st.columns(3)
        for i, (user, height) in enumerate(zip(podium, podium_heights)):
            with cols[i]:
                medal = medals[i]
                rank = user["rank"]
                st.markdown(
                    f'<div style="text-align:center;padding:16px;background:#f8f9fa;border-radius:12px;margin:8px 0">'
                    f'<div style="font-size:2.5em">{medal}</div>'
                    f'<div style="font-size:1.8em">{user["avatar"]}</div>'
                    f'<div style="font-weight:700;font-size:1.1em">{user["name"]}</div>'
                    f'<div style="color:#666">{user["city"]}</div>'
                    f'<div style="color:#ffc107;font-weight:700;font-size:1.2em">{user["points"]:,} pts</div>'
                    f'<div style="font-size:0.82em;color:#888">Level {user["level"]} | 🔥 {user["current_streak"]} streak</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # Full table
    st.markdown("**Full Rankings:**")
    rows = []
    for b in board:
        medal = "🥇" if b["rank"] == 1 else "🥈" if b["rank"] == 2 else "🥉" if b["rank"] == 3 else f"#{b['rank']}"
        rows.append({
            "Rank": medal,
            "Player": f"{b['avatar']} {b['name']}",
            "City": b["city"],
            "Points": f"{b['points']:,}",
            "Level": b["level"],
            "Challenges": b["challenges_completed"],
            "Streak": f"🔥 {b['current_streak']}",
            "CO₂ Saved": f"{b['co2_saved_kg']} kg",
            "Badges": b["badges"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_streak_tracker():
    """Render streak and progress tracking."""
    st.subheader("🔥 Streak Tracker")

    # Streak calendar simulation
    import random
    random.seed(88)
    streak_days = 22
    today = datetime.now()
    cal_html = '<div style="display:flex;flex-wrap:wrap;gap:4px;padding:10px">'
    for i in range(30):
        day = today - timedelta(days=29 - i)
        if i < streak_days:
            if random.random() < 0.15:
                color = "#ffc107"  # partial day
                icon = "🟡"
            else:
                color = "#28a745"  # full day
                icon = "🟢"
        elif i == streak_days:
            color = "#fd7e14"
            icon = "🔥"
        else:
            color = "#1e1e2e"
            icon = "⬛"

        cal_html += (
            f'<div style="width:28px;height:28px;background:{color};border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:0.6em" title="{day.strftime("%b %d")}">{icon}</div>'
        )
    cal_html += '</div>'
    st.markdown("**Last 30 Days:**")
    st.markdown(cal_html, unsafe_allow_html=True)

    # Streak stats
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Streak", "🔥 22 days")
    c2.metric("Best Streak", "38 days")
    c3.metric("Total Active Days", "156")
    c4.metric("Streak Rank", "Top 15%")

    st.markdown(
        "You're on a **22-day streak** — your second longest! Your best was **38 days**. "
        "Keep going to unlock the **🔥 Month Master** badge at 30 days!"
    )

    # Streak leaderboard
    st.markdown("**Streak Champions:**")
    streak_champs = [
        {"name": "🔥 CompostKing", "streak": 45, "city": "Portland"},
        {"name": "🔥 GreenMachine", "streak": 38, "city": "Seattle"},
        {"name": "🔥 EcoWarrior99", "streak": 35, "city": "Portland"},
        {"name": "🔥 BikeRider", "streak": 32, "city": "Amsterdam"},
        {"name": "🔥 OceanDefender", "streak": 28, "city": "Miami"},
    ]
    for champ in streak_champs:
        st.markdown(
            f'<div style="display:flex;align-items:center;margin:3px 0">'
            f'<span style="width:180px;font-size:0.88em">{champ["name"]}</span>'
            f'<div style="width:40%;background:#1e1e2e;border-radius:3px;height:14px">'
            f'<div style="width:{champ["streak"]/50*100}%;background:#fd7e14;border-radius:3px;height:100%"></div></div>'
            f'<span style="margin-left:8px;font-size:0.82em">{champ["streak"]} days | {champ["city"]}</span></div>',
            unsafe_allow_html=True,
        )


def _render_badges(badges: list[dict]):
    """Render achievement badges."""
    st.subheader("🎖️ Achievement Badges")

    unlocked = [b for b in badges if b["unlocked"]]
    locked = [b for b in badges if not b["unlocked"]]

    rarity_colors = {"Common": "#6c757d", "Uncommon": "#28a745", "Rare": "#4a90d9", "Epic": "#6f42c1", "Legendary": "#ffc107"}

    st.markdown(f"**Unlocked ({len(unlocked)}/{len(badges)})**")
    cols = st.columns(4)
    for i, badge in enumerate(unlocked):
        with cols[i % 4]:
            color = rarity_colors.get(badge["rarity"], "#666")
            st.markdown(
                f'<div style="border:2px solid {color};border-radius:10px;padding:10px;margin:6px 0;text-align:center;background:#f8f9fa">'
                f'<div style="font-size:2em">{badge["icon"]}</div>'
                f'<div style="font-weight:600;font-size:0.85em">{badge["name"]}</div>'
                f'<div style="font-size:0.75em;color:{color}">{badge["rarity"]}</div>'
                f'<div style="font-size:0.72em;color:#888">{badge["date"]}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown(f"**Locked ({len(locked)})**")
    cols = st.columns(4)
    for i, badge in enumerate(locked):
        with cols[i % 4]:
            color = rarity_colors.get(badge["rarity"], "#666")
            progress_html = ""
            if badge.get("progress") is not None:
                progress_html = f'<div style="font-size:0.72em;color:#888">Progress: {badge["progress"]}</div>'
            st.markdown(
                f'<div style="border:1px solid #333;border-radius:10px;padding:10px;margin:6px 0;text-align:center;background:#1e1e2e;opacity:0.7">'
                f'<div style="font-size:2em;filter:grayscale(1)">{badge["icon"]}</div>'
                f'<div style="font-weight:600;font-size:0.85em">{badge["name"]}</div>'
                f'<div style="font-size:0.75em;color:{color}">{badge["rarity"]}</div>'
                f'{progress_html}</div>',
                unsafe_allow_html=True,
            )


def _render_team_competition(teams: list[dict]):
    """Render team vs team competition."""
    st.subheader("👥 Team Competition")

    teams.sort(key=lambda x: x["total_points"], reverse=True)

    for i, team in enumerate(teams):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}"
        color = "#ffc107" if i == 0 else "#c0c0c0" if i == 1 else "#cd7f32" if i == 2 else "#666"
        cat = CHALLENGE_CATEGORIES.get(team["category_focus"], {})
        cat_icon = cat.get("icon", "🎯")

        with st.expander(f"{team['avatar']} **{team['name']}** — {medal} {team['total_points']:,} pts | {team['members']} members", expanded=(i < 3)):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Members", team["members"])
            c2.metric("Total Points", f"{team['total_points']:,}")
            c3.metric("Avg Streak", f"🔥 {team['avg_streak']}")
            c4.metric("Challenge Wins", team["wins"])

            st.markdown(f"**Captain:** {team['captain']} | **Focus:** {cat_icon} {team['category_focus']}")

            # Points bar
            max_pts = teams[0]["total_points"]
            pct = team["total_points"] / max_pts * 100
            st.markdown(
                f'<div style="background:#1e1e2e;border-radius:4px;height:16px;margin:8px 0">'
                f'<div style="width:{pct}%;background:{color};border-radius:4px;height:100%"></div></div>',
                unsafe_allow_html=True,
            )

    # Team join CTA
    st.markdown("---")
    st.info("💡 **Create or join a team** to compete together! Team members earn bonus points when completing challenges as a group.")


def _render_category_progress():
    """Render progress across challenge categories."""
    st.subheader("📊 Category Progress")

    import random
    random.seed(55)
    for cat_name, cat_data in CHALLENGE_CATEGORIES.items():
        completed = random.randint(2, 12)
        total = random.randint(10, 20)
        pct = completed / total * 100
        st.markdown(
            f'<div style="display:flex;align-items:center;margin:5px 0">'
            f'<span style="width:150px;font-size:0.88em">{cat_data["icon"]} {cat_name}</span>'
            f'<div style="width:45%;background:#1e1e2e;border-radius:4px;height:18px">'
            f'<div style="width:{pct}%;background:{cat_data["color"]};border-radius:4px;height:100%;display:flex;align-items:center;justify-content:center;color:white;font-size:0.72em;font-weight:600">{completed}/{total}</div></div>'
            f'<span style="margin-left:8px;font-size:0.82em">{completed} completed | {cat_data["points_per_action"]} pts/action</span></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def render_community_eco_challenges():
    """Render the Community Eco Challenges page."""
    st.title("🏆 Community Eco Challenges")
    st.markdown(
        "Join sustainability challenges, compete on leaderboards, track streaks, and earn badges."
    )

    challenges = _generate_mock_challenges()
    board = _generate_mock_leaderboard()
    badges = _generate_mock_badges()
    teams = _generate_mock_teams()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        show_challenges = st.checkbox("Active Challenges", True)
        show_leaderboard = st.checkbox("Leaderboard", True)
        show_streaks = st.checkbox("Streak Tracker", True)
        show_badges = st.checkbox("Achievement Badges", True)
        show_teams = st.checkbox("Team Competition", True)
        show_categories = st.checkbox("Category Progress", True)

    if show_challenges:
        _render_active_challenges(challenges)

    if show_leaderboard:
        st.markdown("---")
        _render_leaderboard(board)

    if show_streaks:
        st.markdown("---")
        _render_streak_tracker()

    if show_badges:
        st.markdown("---")
        _render_badges(badges)

    if show_teams:
        st.markdown("---")
        _render_team_competition(teams)

    if show_categories:
        st.markdown("---")
        _render_category_progress()

    st.markdown("---")
    st.caption(f"Community Eco Challenges | {len(challenges)} challenges | {len(board)} players | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# Entry point
if __name__ == "__main__" or True:
    render_community_eco_challenges()
