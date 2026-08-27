"""
Community Eco Challenge Hub — Card Components
==============================================
Reusable Streamlit card components for challenge display, progress
indicators, leaderboard entries, and activity feed items.
"""

import streamlit as st
from typing import Dict, Any, Optional, List


# ── Card Styles ───────────────────────────────────────────────────────────

CARD_CSS = """
<style>
    .challenge-card {
        background: linear-gradient(145deg, rgba(255,255,255,0.92), rgba(240,255,240,0.75));
        border: 1px solid rgba(34,197,94,0.2);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 8px 32px rgba(34,197,94,0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .challenge-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 16px 48px rgba(34,197,94,0.14);
    }
    .challenge-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        background: linear-gradient(90deg, #22c55e, #86efac, #16a34a);
    }
    .challenge-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-easy { background: rgba(34,197,94,0.15); color: #16a34a; }
    .badge-medium { background: rgba(234,179,8,0.15); color: #ca8a04; }
    .badge-hard { background: rgba(239,68,68,0.15); color: #dc2626; }
    .progress-track {
        width: 100%;
        height: 10px;
        border-radius: 999px;
        background: rgba(0,0,0,0.06);
        overflow: hidden;
        margin: 8px 0;
    }
    .progress-fill {
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, #16a34a, #22c55e, #86efac);
        transition: width 0.6s ease;
    }
    .stat-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 8px;
        background: rgba(0,0,0,0.04);
        font-size: 13px;
        font-weight: 600;
        margin-right: 6px;
    }
    .leaderboard-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 6px;
        background: rgba(255,255,255,0.7);
        border: 1px solid rgba(0,0,0,0.06);
        transition: background 0.15s ease;
    }
    .leaderboard-row:hover { background: rgba(34,197,94,0.06); }
    .leaderboard-row.gold { background: linear-gradient(135deg, rgba(255,215,0,0.12), rgba(255,215,0,0.04)); border-color: rgba(255,215,0,0.25); }
    .leaderboard-row.silver { background: linear-gradient(135deg, rgba(192,192,192,0.12), rgba(192,192,192,0.04)); border-color: rgba(192,192,192,0.25); }
    .leaderboard-row.bronze { background: linear-gradient(135deg, rgba(205,127,50,0.12), rgba(205,127,50,0.04)); border-color: rgba(205,127,50,0.25); }
    .feed-item {
        padding: 10px 14px;
        border-left: 3px solid #22c55e;
        margin-bottom: 8px;
        border-radius: 0 8px 8px 0;
        background: rgba(255,255,255,0.5);
        font-size: 13px;
    }
    .feed-item .feed-time { color: #9ca3af; font-size: 11px; }
    .feed-item .feed-user { font-weight: 700; color: #16a34a; }
    .streak-flame {
        font-size: 32px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.15); }
    }
    .category-tag {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        background: rgba(34,197,94,0.1);
        color: #15803d;
    }
    @media (prefers-color-scheme: dark) {
        .challenge-card {
            background: linear-gradient(145deg, rgba(15,23,42,0.92), rgba(10,30,15,0.75));
            border-color: rgba(74,222,128,0.2);
        }
        .leaderboard-row {
            background: rgba(30,41,59,0.7);
            border-color: rgba(148,163,184,0.12);
            color: #f1f5f9;
        }
        .leaderboard-row.gold { background: linear-gradient(135deg, rgba(255,215,0,0.08), rgba(255,215,0,0.02)); }
        .leaderboard-row.silver { background: linear-gradient(135deg, rgba(192,192,192,0.08), rgba(192,192,192,0.02)); }
        .leaderboard-row.bronze { background: linear-gradient(135deg, rgba(205,127,50,0.08), rgba(205,127,50,0.02)); }
        .feed-item { background: rgba(30,41,59,0.5); color: #e2e8f0; }
        .stat-pill { background: rgba(148,163,184,0.12); color: #e2e8f0; }
        .category-tag { background: rgba(74,222,128,0.12); color: #86efac; }
    }
</style>
"""


def inject_card_css():
    """Inject challenge card styles."""
    st.markdown(CARD_CSS, unsafe_allow_html=True)


# ── Challenge Card ────────────────────────────────────────────────────────

def render_challenge_card(challenge: Dict[str, Any], my_progress: Optional[Dict[str, Any]] = None,
                           show_join: bool = True):
    """Render a single challenge card with stats and optional progress."""
    difficulty = challenge.get("difficulty", "medium")
    diff_cls = f"badge-{difficulty}"
    days_left = challenge.get("days_remaining", 0)
    stats = challenge.get("stats", {})

    progress_pct = 0
    if my_progress and challenge.get("target_value", 0) > 0:
        progress_pct = min(100, (my_progress.get("current_progress", 0) / challenge["target_value"]) * 100)

    st.markdown(f"""
    <div class="challenge-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <span style="font-size:28px;">{challenge.get('badge_icon', '🏆')}</span>
                <span style="font-size:20px; font-weight:800; margin-left:8px;">{challenge.get('title', 'Challenge')}</span>
            </div>
            <span class="challenge-badge {diff_cls}">{difficulty.upper()}</span>
        </div>
        <p style="color:#6b7280; margin:8px 0; font-size:14px;">{challenge.get('description', '')}</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin:10px 0;">
            <span class="stat-pill">🎯 Target: {challenge.get('target_value', 0)} {challenge.get('target_unit', 'actions')}</span>
            <span class="stat-pill">⭐ XP: {challenge.get('xp_reward', 0)}</span>
            <span class="stat-pill">👥 {stats.get('total_participants', 0)} joined</span>
            <span class="stat-pill">📅 {days_left} days left</span>
            <span class="category-tag">📁 {challenge.get('category', 'general')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if my_progress:
        completed = my_progress.get("is_completed", False)
        if completed:
            st.success(f"✅ Completed! Earned **{challenge.get('xp_reward', 0)} XP**")
        else:
            st.markdown(f"""
            <div class="progress-track">
                <div class="progress-fill" style="width: {progress_pct:.1f}%;"></div>
            </div>
            """, unsafe_allow_html=True)
            st.caption(f"{my_progress.get('current_progress', 0):.1f} / {challenge.get('target_value', 1)} ({progress_pct:.0f}%)")


# ── Leaderboard Row ──────────────────────────────────────────────────────

def render_leaderboard_entry(rank: int, name: str, score: float, target: float = 1.0,
                              team_icon: str = "", is_user: bool = False):
    """Render a single leaderboard row with rank styling."""
    medal = ""
    row_cls = ""
    if rank == 1:
        medal, row_cls = "🥇", "gold"
    elif rank == 2:
        medal, row_cls = "🥈", "silver"
    elif rank == 3:
        medal, row_cls = "🥉", "bronze"
    else:
        medal = f"#{rank}"

    pct = min(100, (score / target * 100)) if target > 0 else 0
    highlight = "border: 2px solid #22c55e;" if is_user else ""

    st.markdown(f"""
    <div class="leaderboard-row {row_cls}" style="{highlight}">
        <div style="display:flex; align-items:center; gap:10px;">
            <span style="font-size:20px; min-width:30px; text-align:center;">{medal}</span>
            <span style="font-size:18px;">{team_icon}</span>
            <span style="font-weight:700; font-size:15px;">{name}</span>
        </div>
        <div style="text-align:right;">
            <span style="font-weight:800; font-size:16px; color:#16a34a;">{score:.1f}</span>
            <span style="color:#9ca3af; font-size:12px; margin-left:4px;">/ {target:.0f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Activity Feed Item ───────────────────────────────────────────────────

def render_feed_item(item: Dict[str, Any]):
    """Render a single activity feed entry."""
    username = item.get("username", "Anonymous")
    atype = item.get("activity_type", "unknown")
    payload = item.get("payload", "{}")
    created = item.get("created_at", "")

    try:
        import json
        data = json.loads(payload) if isinstance(payload, str) else payload
    except Exception:
        data = {}

    icons = {"joined": "👋", "progress": "📊", "completed": "🎉", "team_created": "👥"}
    icon = icons.get(atype, "📌")
    action_text = {
        "joined": "joined the challenge",
        "progress": f"logged progress ({data.get('value', '')})",
        "completed": "completed the challenge! 🎊",
        "team_created": f"created team {data.get('team', '')}",
    }.get(atype, atype)

    st.markdown(f"""
    <div class="feed-item">
        <span class="feed-user">{icon} {username}</span> {action_text}
        <span class="feed-time" style="float:right;">{created[:16] if created else ''}</span>
    </div>
    """, unsafe_allow_html=True)


# ── Streak Display ───────────────────────────────────────────────────────

def render_streak_display(streak_data: Dict[str, Any]):
    """Render user streak with animated flame."""
    current = streak_data.get("current_streak", 0)
    longest = streak_data.get("longest_streak", 0)
    total = streak_data.get("total_days_active", 0)

    flame_emoji = "🔥" if current >= 3 else "🕯️" if current >= 1 else "💤"

    st.markdown(f"""
    <div style="text-align:center; padding:20px; background:linear-gradient(135deg, rgba(255,107,53,0.08), rgba(255,69,0,0.04)); border-radius:16px; border:1px solid rgba(255,107,53,0.15);">
        <div class="streak-flame">{flame_emoji}</div>
        <div style="font-size:36px; font-weight:900; color:#ea580c; margin:8px 0;">{current}</div>
        <div style="font-size:14px; color:#9a3412; font-weight:600;">Day Streak</div>
        <div style="display:flex; justify-content:center; gap:24px; margin-top:16px;">
            <div>
                <div style="font-size:18px; font-weight:800;">{longest}</div>
                <div style="font-size:11px; color:#9a3412;">Longest</div>
            </div>
            <div>
                <div style="font-size:18px; font-weight:800;">{total}</div>
                <div style="font-size:11px; color:#9a3412;">Total Days</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Stats Summary Row ────────────────────────────────────────────────────

def render_stats_row(stats: Dict[str, int], icons: Optional[Dict[str, str]] = None):
    """Render a row of metric pills."""
    if icons is None:
        icons = {"challenges_completed": "🏆", "total_xp_earned": "⭐",
                 "total_actions_logged": "📊", "challenges_active": "🔥"}
    cols = st.columns(len(stats))
    for col, (key, val) in zip(cols, stats.items()):
        with col:
            icon = icons.get(key, "📌")
            label = key.replace("_", " ").title()
            st.metric(label=f"{icon} {label}", value=val)


# ── Challenge Create Form ────────────────────────────────────────────────

def render_challenge_create_form(categories: List[str], difficulty_meta: Dict[str, Any]):
    """Render a challenge creation form with validation."""
    with st.form("create_challenge_form", clear_on_submit=True):
        st.subheader("🌱 Create New Challenge")
        title = st.text_input("Challenge Title", max_chars=80, placeholder="e.g., 🌳 Plant 5 Trees This Month")
        description = st.text_area("Description", max_chars=300, placeholder="What does this challenge involve?")
        c1, c2 = st.columns(2)
        with c1:
            category = st.selectbox("Category", categories)
            difficulty = st.selectbox("Difficulty", list(difficulty_meta.keys()),
                                       format_func=lambda x: f"{difficulty_meta[x]['icon']} {difficulty_meta[x]['label']}")
        with c2:
            target_value = st.number_input("Target Value", min_value=1.0, value=7.0, step=1.0)
            target_unit = st.text_input("Target Unit", value="days", max_chars=20)
        xp_reward = st.slider("XP Reward", min_value=10, max_value=500, value=100, step=10)
        duration_days = st.slider("Duration (days)", min_value=1, max_value=90, value=30)
        submitted = st.form_submit_button("🚀 Create Challenge", use_container_width=True)
    return {
        "submitted": submitted,
        "title": title, "description": description, "category": category,
        "difficulty": difficulty, "target_value": target_value, "target_unit": target_unit,
        "xp_reward": xp_reward, "duration_days": duration_days,
    }
