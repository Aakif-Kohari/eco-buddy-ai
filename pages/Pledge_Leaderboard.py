"""
Pledge Leaderboard & Accountability Groups – Streamlit Page
============================================================
Browse, create, and join accountability groups. View community
leaderboards, group-level challenges, weekly trends, and share cards.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from src.community.pledge_leaderboard import (
    init_leaderboard_tables,
    create_group,
    join_group,
    leave_group,
    get_group_by_invite,
    get_user_groups,
    get_public_groups,
    get_group_members,
    get_group_members_leaderboard,
    get_leaderboard,
    get_group_leaderboard_position,
    create_group_challenge,
    get_group_challenges,
    update_challenge_progress,
    post_announcement,
    get_group_announcements,
    take_weekly_snapshot,
    get_group_weekly_trend,
    generate_group_share_card,
    generate_member_share_card,
    transfer_ownership,
    promote_member,
    COLLAB_CHALLENGE_PRESETS,
    GROUP_PRIVACY_PUBLIC,
    GROUP_PRIVACY_PRIVATE,
)
from src.utils.green_pledge_tracker import (
    init_pledge_tables,
    current_week_start,
    current_week_end,
    get_user_pledge_stats,
    get_user_weekly_pledges,
)

st.set_page_config(page_title="Pledge Leaderboard", page_icon="🏆", layout="wide")

# Initialise tables
init_pledge_tables()
init_leaderboard_tables()

# ── Auth gate ────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("🔒 Please sign in to access the Pledge Leaderboard.")
    st.stop()

# ── Page header ──────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:10px 0 4px;'>
    <h1 style='margin:0;font-size:2.4rem;'>🏆 Pledge Leaderboard & Groups</h1>
    <p style='color:#6b7280;margin-top:4px;font-size:1.05rem;'>
        Form accountability groups, compete on pledge completions, and see who's making the biggest impact.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────────────
tab_leaderboard, tab_my_groups, tab_browse, tab_create, tab_challenges, tab_announce = st.tabs([
    "🏆 Leaderboard",
    "👥 My Groups",
    "🔍 Browse Groups",
    "➕ Create Group",
    "🎯 Challenges",
    "📢 Announcements",
])

# =====================================================================
# TAB: Leaderboard
# =====================================================================
with tab_leaderboard:
    st.subheader("🏆 Community Group Leaderboard")
    st.caption(f"Week: **{current_week_start()}** → **{current_week_end()}**")

    leaderboard = get_leaderboard(limit=20)

    if not leaderboard:
        st.info("🏆 No groups on the leaderboard yet. Create or join a group to get started!")
    else:
        # Top 3 podium
        if len(leaderboard) >= 3:
            podium_cols = st.columns([1, 1.2, 1])
            podium_emojis = ["🥈", "🥇", "🥉"]
            podium_labels = ["2nd", "1st", "3rd"]
            podium_order = [1, 0, 2]  # display order: 2nd, 1st, 3rd

            for display_idx, podium_idx in enumerate(podium_order):
                with podium_cols[display_idx]:
                    entry = leaderboard[podium_idx]
                    emoji = podium_emojis[podium_idx]
                    size = "2.2rem" if podium_idx == 0 else "1.6rem"
                    border = "2px solid #f59e0b" if podium_idx == 0 else "1px solid #d1d5db"
                    st.markdown(f"""
                    <div style='text-align:center;padding:20px;border-radius:16px;
                                border:{border};background:linear-gradient(135deg,#f0fdf4,#fff);
                                margin-bottom:8px;'>
                        <div style='font-size:{size};'>{emoji}</div>
                        <h3 style='margin:6px 0;'>{entry.group_name}</h3>
                        <p style='color:#6b7280;margin:0;'>{entry.score:.0f} pts · {entry.member_count} members</p>
                        <p style='font-size:0.8rem;margin:4px 0 0;'>🌱 {entry.level} · 🌍 {entry.total_co2_saved_kg:.1f} kg CO₂</p>
                    </div>
                    """, unsafe_allow_html=True)

        st.divider()

        # Full leaderboard table
        st.markdown("#### 📊 Full Rankings")
        leaderboard_data = []
        for entry in leaderboard:
            rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(entry.rank, f"#{entry.rank}")
            leaderboard_data.append({
                "Rank": rank_emoji,
                "Group": entry.group_name,
                "Score": f"{entry.score:.0f}",
                "XP": entry.total_xp,
                "CO₂ Saved (kg)": f"{entry.total_co2_saved_kg:.1f}",
                "Pledges": entry.pledges_completed,
                "Members": entry.member_count,
                "Streak": f"{entry.streak_weeks} wks",
                "Level": entry.level,
            })

        df = pd.DataFrame(leaderboard_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # My group position
        my_groups = get_user_groups(user_id)
        if my_groups:
            st.divider()
            st.markdown("#### 📍 Your Group Positions")
            for g in my_groups:
                pos = get_group_leaderboard_position(g.group_id)
                if pos:
                    delta_icon = "🔺" if pos.weekly_delta > 0 else ("🔻" if pos.weekly_delta < 0 else "➖")
                    st.markdown(
                        f"- **{g.name}** — Rank **#{pos.rank}** "
                        f"| Score: {pos.score:.0f} | Level: {pos.level} "
                        f"{delta_icon}"
                    )

# =====================================================================
# TAB: My Groups
# =====================================================================
with tab_my_groups:
    st.subheader("👥 My Accountability Groups")

    my_groups = get_user_groups(user_id)

    if not my_groups:
        st.info("You're not in any groups yet. Head to **Browse Groups** or **Create Group** to get started!")
    else:
        for group in my_groups:
            role_badge = {"owner": "👑 Owner", "admin": "🛡️ Admin", "member": "👤 Member"}.get(
                group.level if hasattr(group, "role") else "member", "👤"
            )

            # Determine user role from members
            members = get_group_members(group.group_id)
            user_member = next((m for m in members if m.get("user_id") == user_id), {})
            user_role = user_member.get("role", "member")

            st.markdown(f"""
            <div style='border:1px solid #d1fae5;border-radius:16px;padding:20px;
                        background:linear-gradient(135deg,#f0fdf4,#ecfdf5);margin-bottom:16px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <div>
                        <h3 style='margin:0;'>{group.name}</h3>
                        <p style='color:#6b7280;margin:4px 0 0;font-size:0.9rem;'>
                            {group.member_count} members · {group.privacy.title()} ·
                            {'👑 Owner' if user_role == 'owner' else '🛡️ Admin' if user_role == 'admin' else '👤 Member'}
                        </p>
                    </div>
                    <div style='text-align:right;'>
                        <span style='background:#dcfce7;padding:4px 12px;border-radius:20px;
                                     font-weight:600;font-size:0.85rem;'>{group.level}</span>
                    </div>
                </div>
                <div style='display:flex;gap:20px;margin-top:12px;'>
                    <div style='text-align:center;'>
                        <div style='font-size:1.4rem;font-weight:700;color:#16a34a;'>{group.total_xp}</div>
                        <div style='font-size:0.75rem;color:#6b7280;'>Total XP</div>
                    </div>
                    <div style='text-align:center;'>
                        <div style='font-size:1.4rem;font-weight:700;color:#0ea5e9;'>{group.total_co2_saved_kg:.1f}</div>
                        <div style='font-size:0.75rem;color:#6b7280;'>CO₂ Saved (kg)</div>
                    </div>
                    <div style='text-align:center;'>
                        <div style='font-size:1.4rem;font-weight:700;color:#f59e0b;'>{group.total_pledges_completed}</div>
                        <div style='font-size:0.75rem;color:#6b7280;'>Pledges</div>
                    </div>
                    <div style='text-align:center;'>
                        <div style='font-size:1.4rem;font-weight:700;color:#a855f7;'>{group.current_streak_weeks}</div>
                        <div style='font-size:0.75rem;color:#6b7280;'>Streak</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Group badges
            if group.badges:
                badge_html = " ".join(
                    f"<span style='background:#dcfce7;border:1px solid #bbf7d0;border-radius:8px;"
                    f"padding:3px 10px;font-size:0.75rem;font-weight:600;'>{b}</span>"
                    for b in group.badges[:6]
                )
                st.markdown(f"<div style='display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;'>{badge_html}</div>",
                            unsafe_allow_html=True)

            # Expandable group details
            with st.expander(f"📋 Details — {group.name}", expanded=False):
                sub_tab_members, sub_tab_trend, sub_tab_chart, sub_tab_card = st.tabs([
                    "👥 Members", "📈 Trend", "📊 Charts", "📤 Share",
                ])

                with sub_tab_members:
                    members = get_group_members(group.group_id)
                    if members:
                        for m in members:
                            role_icon = {"owner": "👑", "admin": "🛡️"}.get(m.get("role", ""), "👤")
                            st.markdown(
                                f"{role_icon} **{m.get('display_name', 'User')}** "
                                f"— {m.get('role', 'member').title()} "
                                f"| XP: {m.get('personal_xp', 0)} "
                                f"| CO₂: {m.get('personal_co2_kg', 0):.1f} kg "
                                f"| Pledges: {m.get('personal_completed', 0)}"
                            )
                    else:
                        st.info("No members found.")

                    # Transfer ownership (owner only)
                    if user_role == "owner" and len(members) > 1:
                        st.divider()
                        member_ids = [m["user_id"] for m in members if m["user_id"] != user_id]
                        if member_ids:
                            target = st.selectbox(
                                "Transfer ownership to",
                                member_ids,
                                format_func=lambda uid: next(
                                    (m.get("display_name", f"User#{uid}") for m in members if m["user_id"] == uid),
                                    f"User#{uid}",
                                ),
                                key=f"transfer_{group.group_id}",
                            )
                            if st.button("🔄 Transfer Ownership", key=f"transfer_btn_{group.group_id}"):
                                if transfer_ownership(user_id, group.group_id, target):
                                    st.success("Ownership transferred!")
                                    st.rerun()
                                else:
                                    st.error("Transfer failed.")

                with sub_tab_trend:
                    trend = get_group_weekly_trend(group.group_id, weeks=8)
                    if trend:
                        df_trend = pd.DataFrame(trend)
                        st.line_chart(df_trend.set_index("week_start")[["xp_earned", "co2_saved_kg", "pledges_completed"]])
                    else:
                        st.info("No weekly data yet. Check in with your pledges to start tracking!")

                with sub_tab_chart:
                    members = get_group_members(group.group_id)
                    if members:
                        member_leaderboard = get_group_members_leaderboard(group.group_id)
                        if member_leaderboard:
                            df_members = pd.DataFrame(member_leaderboard)
                            fig = go.Figure(data=[
                                go.Bar(
                                    x=df_members["display_name"],
                                    y=df_members["personal_xp"],
                                    marker_color="#4ade80",
                                    name="XP Earned",
                                )
                            ])
                            fig.update_layout(
                                title="Member XP Contribution",
                                height=300,
                                margin=dict(l=0, r=0, t=40, b=0),
                            )
                            st.plotly_chart(fig, use_container_width=True)

                            # CO2 contribution pie
                            fig2 = go.Figure(data=[
                                go.Pie(
                                    labels=df_members["display_name"],
                                    values=df_members["personal_co2_kg"],
                                    hole=0.4,
                                    marker=dict(colors=["#4ade80", "#06b6d4", "#f59e0b", "#a855f7", "#ef4444"]),
                                )
                            ])
                            fig2.update_layout(
                                title="CO₂ Saved by Member",
                                height=300,
                                margin=dict(l=0, r=0, t=40, b=0),
                            )
                            st.plotly_chart(fig2, use_container_width=True)

                with sub_tab_card:
                    share_card = generate_group_share_card(group)
                    st.markdown(f"""
                    <div style='border:2px solid #4ade80;border-radius:20px;padding:28px;
                                background:linear-gradient(135deg,#f0fdf4,#ecfdf5,#dcfce7);
                                text-align:center;'>
                        <h2 style='margin:0;color:#16a34a;'>{share_card['title']}</h2>
                        <p style='color:#6b7280;margin:4px 0 12px;'>{share_card['subtitle']}</p>
                        <p style='font-style:italic;color:#4b5563;margin-bottom:16px;'>{share_card['tagline']}</p>
                        <div style='display:flex;justify-content:center;gap:24px;flex-wrap:wrap;'>
                            <div>
                                <div style='font-size:1.8rem;font-weight:800;color:#16a34a;'>{share_card['stats']['members']}</div>
                                <div style='font-size:0.8rem;color:#6b7280;'>Members</div>
                            </div>
                            <div>
                                <div style='font-size:1.8rem;font-weight:800;color:#0ea5e9;'>{share_card['stats']['co2_saved_kg']}</div>
                                <div style='font-size:0.8rem;color:#6b7280;'>kg CO₂ Saved</div>
                            </div>
                            <div>
                                <div style='font-size:1.8rem;font-weight:800;color:#f59e0b;'>{share_card['stats']['pledges_completed']}</div>
                                <div style='font-size:0.8rem;color:#6b7280;'>Pledges Done</div>
                            </div>
                            <div>
                                <div style='font-size:1.8rem;font-weight:800;color:#a855f7;'>{share_card['stats']['level']}</div>
                                <div style='font-size:0.8rem;color:#6b7280;'>Level</div>
                            </div>
                        </div>
                        <div style='margin-top:14px;font-size:0.8rem;color:#9ca3af;'>
                            Invite code: <code>{share_card['invite_code']}</code>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # Leave button (non-owners)
            if user_role != "owner":
                if st.button(f"🚪 Leave {group.name}", key=f"leave_{group.group_id}", type="secondary"):
                    if leave_group(user_id, group.group_id):
                        st.success(f"You left **{group.name}**.")
                        st.rerun()
                    else:
                        st.error("Could not leave the group.")

            st.divider()

# =====================================================================
# TAB: Browse Groups
# =====================================================================
with tab_browse:
    st.subheader("🔍 Browse Public Groups")

    sort_by = st.selectbox("Sort by", ["Members", "XP", "CO₂ Saved", "Newest"], key="browse_sort")
    sort_key = {"Members": "members", "XP": "xp", "CO₂ Saved": "co2", "Newest": "newest"}[sort_by]

    public_groups = get_public_groups(limit=20, sort_by=sort_key)

    if not public_groups:
        st.info("No public groups found. Be the first to create one!")
    else:
        for group in public_groups:
            st.markdown(f"""
            <div style='border:1px solid #e5e7eb;border-radius:14px;padding:18px;
                        background:#fff;box-shadow:0 2px 8px rgba(0,0,0,0.04);margin-bottom:10px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <div>
                        <h4 style='margin:0;'>{group.name}</h4>
                        <p style='color:#6b7280;margin:4px 0 0;font-size:0.85rem;'>
                            {group.description[:80] if group.description else 'No description'}
                        </p>
                    </div>
                    <span style='background:#dcfce7;padding:4px 12px;border-radius:20px;
                                 font-weight:600;font-size:0.8rem;'>{group.level}</span>
                </div>
                <div style='display:flex;gap:16px;margin-top:10px;font-size:0.82rem;color:#6b7280;'>
                    <span>👥 {group.member_count}/{group.max_members}</span>
                    <span>⭐ {group.total_xp} XP</span>
                    <span>🌍 {group.total_co2_saved_kg:.1f} kg CO₂</span>
                    <span>✅ {group.total_pledges_completed} pledges</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            is_member = any(g.group_id == group.group_id for g in get_user_groups(user_id))
            if is_member:
                st.caption("✅ You're a member")
            elif group.member_count < group.max_members:
                if st.button(f"🤝 Join {group.name}", key=f"join_{group.group_id}"):
                    result = join_group(user_id, group.invite_code)
                    if result:
                        st.success(f"✅ Joined **{group.name}**!")
                        st.rerun()
                    else:
                        st.error("Could not join — maybe the group is full.")

    # Join by invite code
    st.divider()
    st.markdown("#### 🔑 Join by Invite Code")
    invite_code = st.text_input("Enter invite code", placeholder="e.g. A1B2C3D4", key="join_invite")
    if st.button("🔍 Look Up Group", key="lookup_invite"):
        if invite_code:
            group = get_group_by_invite(invite_code.strip().upper())
            if group:
                st.success(f"Found: **{group.name}** ({group.member_count} members)")
                is_member = any(g.group_id == group.group_id for g in get_user_groups(user_id))
                if is_member:
                    st.info("You're already a member!")
                elif group.member_count < group.max_members:
                    if st.button(f"🤝 Join {group.name}", key="join_invite_btn"):
                        result = join_group(user_id, invite_code.strip().upper())
                        if result:
                            st.success("Joined successfully!")
                            st.rerun()
                        else:
                            st.error("Could not join.")
                else:
                    st.warning("Group is full.")
            else:
                st.error("No group found with that code.")

# =====================================================================
# TAB: Create Group
# =====================================================================
with tab_create:
    st.subheader("➕ Create Accountability Group")

    with st.form("create_group_form", clear_on_submit=True):
        name = st.text_input("Group Name", max_chars=60, placeholder="e.g. Green Warriors")
        description = st.text_area("Description", max_chars=500, placeholder="What's your group about?")
        privacy = st.selectbox("Privacy", ["Public", "Private"], help="Public groups appear on the leaderboard.")
        max_members = st.slider("Max Members", min_value=2, max_value=50, value=10)
        tags_input = st.text_input("Tags (comma-separated)", placeholder="e.g. vegan, cycling, solar")

        submitted = st.form_submit_button("🚀 Create Group", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Group name is required.")
            else:
                privacy_val = GROUP_PRIVACY_PUBLIC if privacy == "Public" else GROUP_PRIVACY_PRIVATE
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                result = create_group(
                    name=name.strip(),
                    owner_id=user_id,
                    description=description.strip(),
                    privacy=privacy_val,
                    max_members=max_members,
                    tags=tags,
                )
                if result:
                    st.success(f"🎉 Group **{result.name}** created!")
                    st.info(f"Invite code: **{result.invite_code}**")
                    st.rerun()
                else:
                    st.error("A group with that name already exists.")

    # Quick stats for user's groups
    my_groups = get_user_groups(user_id)
    if my_groups:
        st.divider()
        st.markdown("#### 📊 Your Group Summary")
        total_co2 = sum(g.total_co2_saved_kg for g in my_groups)
        total_xp = sum(g.total_xp for g in my_groups)
        total_pledges = sum(g.total_pledges_completed for g in my_groups)

        c1, c2, c3 = st.columns(3)
        c1.metric("Groups Joined", len(my_groups))
        c2.metric("Combined CO₂ Saved", f"{total_co2:.1f} kg")
        c3.metric("Combined XP", total_xp)

# =====================================================================
# TAB: Challenges
# =====================================================================
with tab_challenges:
    st.subheader("🎯 Group Challenges")

    my_groups = get_user_groups(user_id)
    if not my_groups:
        st.info("Join a group first to access challenges!")
    else:
        selected_group_name = st.selectbox(
            "Select Group",
            [g.name for g in my_groups],
            key="challenge_group_select",
        )
        selected_group = next((g for g in my_groups if g.name == selected_group_name), None)

        if selected_group:
            members = get_group_members(selected_group.group_id)
            user_member = next((m for m in members if m.get("user_id") == user_id), {})
            user_role = user_member.get("role", "member")

            # Active challenges
            active_challenges = get_group_challenges(selected_group.group_id, status="active")
            completed_challenges = get_group_challenges(selected_group.group_id, status="completed")

            if active_challenges:
                st.markdown("#### 🔥 Active Challenges")
                for ch in active_challenges:
                    progress = min(ch.current_value / ch.target_value, 1.0) if ch.target_value > 0 else 0
                    st.markdown(f"""
                    <div style='border:1px solid #fde68a;border-radius:14px;padding:18px;
                                background:linear-gradient(135deg,#fffbeb,#fef3c7);margin-bottom:10px;'>
                        <h4 style='margin:0;'>{ch.title}</h4>
                        <p style='color:#6b7280;margin:4px 0 8px;font-size:0.85rem;'>{ch.description}</p>
                        <p style='font-size:0.82rem;margin:0;'>
                            🎯 {ch.current_value:.1f}/{ch.target_value:.1f} {ch.target_type.replace('_', ' ')}
                            &nbsp;·&nbsp; ⭐ {ch.xp_reward} XP
                            &nbsp;·&nbsp; 📅 Ends: {ch.end_week}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.progress(progress, text=f"{progress*100:.0f}% complete")
            else:
                st.info("No active challenges. Create one to get your group motivated!")

            if completed_challenges:
                with st.expander(f"✅ Completed ({len(completed_challenges)})"):
                    for ch in completed_challenges:
                        st.markdown(f"- ✅ **{ch.title}** — +{ch.xp_reward} XP — Completed {ch.completed_at[:10]}")

            # Create challenge (owner/admin only)
            if user_role in ("owner", "admin"):
                st.divider()
                st.markdown("#### 🆕 Create New Challenge")

                preset_col, custom_col = st.columns(2)

                with preset_col:
                    st.markdown("**Quick Presets**")
                    for i, preset in enumerate(COLLAB_CHALLENGE_PRESETS):
                        if st.button(
                            f"{preset['title']}",
                            key=f"preset_{i}_{selected_group.group_id}",
                            help=preset["description"],
                        ):
                            result = create_group_challenge(
                                creator_id=user_id,
                                group_id=selected_group.group_id,
                                title=preset["title"],
                                description=preset["description"],
                                target_type=preset["target_type"],
                                target_value=preset["target_value"],
                                duration_weeks=preset["duration_weeks"],
                                xp_reward=preset["xp_reward"],
                                eco_points_reward=preset["eco_points_reward"],
                            )
                            if result:
                                st.success(f"Challenge created: {preset['title']}")
                                st.rerun()
                            else:
                                st.error("Failed to create challenge.")

                with custom_col:
                    with st.form("custom_challenge_form"):
                        ch_title = st.text_input("Challenge Title", placeholder="e.g. Zero-Waste Week")
                        ch_desc = st.text_area("Description", placeholder="What's the challenge?")
                        ch_target_type = st.selectbox(
                            "Target Type",
                            ["pledges_completed", "co2_saved", "streak_weeks", "checkins"],
                        )
                        ch_target = st.number_input("Target Value", min_value=1.0, value=10.0)
                        ch_duration = st.slider("Duration (weeks)", 1, 8, 4)
                        ch_xp = st.number_input("XP Reward", min_value=50, value=150)

                        if st.form_submit_button("🚀 Create Custom Challenge"):
                            if ch_title.strip():
                                result = create_group_challenge(
                                    creator_id=user_id,
                                    group_id=selected_group.group_id,
                                    title=ch_title.strip(),
                                    description=ch_desc.strip(),
                                    target_type=ch_target_type,
                                    target_value=ch_target,
                                    duration_weeks=ch_duration,
                                    xp_reward=ch_xp,
                                )
                                if result:
                                    st.success(f"Challenge created: {ch_title}")
                                    st.rerun()
                                else:
                                    st.error("Failed to create challenge.")
                            else:
                                st.error("Title is required.")

# =====================================================================
# TAB: Announcements
# =====================================================================
with tab_announce:
    st.subheader("📢 Group Announcements")

    my_groups = get_user_groups(user_id)
    if not my_groups:
        st.info("Join a group to view and post announcements!")
    else:
        selected_group_name = st.selectbox(
            "Select Group",
            [g.name for g in my_groups],
            key="announce_group_select",
        )
        selected_group = next((g for g in my_groups if g.name == selected_group_name), None)

        if selected_group:
            members = get_group_members(selected_group.group_id)
            user_member = next((m for m in members if m.get("user_id") == user_id), {})
            user_role = user_member.get("role", "member")

            # Post announcement (owner/admin)
            if user_role in ("owner", "admin"):
                with st.form("announcement_form"):
                    ann_title = st.text_input("Title", placeholder="e.g. Weekly Kickoff!")
                    ann_body = st.text_area("Body", placeholder="Share updates, motivation, or tips...")
                    ann_priority = st.selectbox("Priority", ["Normal", "Important", "Urgent"])

                    if st.form_submit_button("📢 Post Announcement"):
                        if ann_title.strip():
                            priority_map = {"Normal": "normal", "Important": "important", "Urgent": "urgent"}
                            result = post_announcement(
                                author_id=user_id,
                                group_id=selected_group.group_id,
                                title=ann_title.strip(),
                                body=ann_body.strip(),
                                priority=priority_map[ann_priority],
                            )
                            if result:
                                st.success("Announcement posted!")
                                st.rerun()
                            else:
                                st.error("Failed to post.")
                        else:
                            st.error("Title is required.")

            # View announcements
            announcements = get_group_announcements(selected_group.group_id)

            if not announcements:
                st.info("No announcements yet.")
            else:
                for ann in announcements:
                    priority_styles = {
                        "normal": "border-left:4px solid #6b7280;",
                        "important": "border-left:4px solid #f59e0b;",
                        "urgent": "border-left:4px solid #ef4444;",
                    }
                    priority_badges = {
                        "normal": "📝",
                        "important": "⚡",
                        "urgent": "🚨",
                    }
                    style = priority_styles.get(ann.priority, priority_styles["normal"])
                    badge = priority_badges.get(ann.priority, "📝")

                    st.markdown(f"""
                    <div style='{style}border-radius:12px;padding:16px;
                                background:rgba(255,255,255,0.03);margin-bottom:10px;'>
                        <div style='display:flex;justify-content:space-between;align-items:center;'>
                            <h4 style='margin:0;'>{badge} {ann.title}</h4>
                            <span style='font-size:0.75rem;color:#9ca3af;'>{ann.created_at[:16] if ann.created_at else ''}</span>
                        </div>
                        <p style='color:#6b7280;margin:6px 0 0;font-size:0.9rem;'>{ann.body}</p>
                        <p style='color:#9ca3af;margin:4px 0 0;font-size:0.75rem;'>By {ann.author_name}</p>
                    </div>
                    """, unsafe_allow_html=True)
