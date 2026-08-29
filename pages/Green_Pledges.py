"""
Community Green Pledges – Streamlit Page
=========================================
Streamlit multi-page entry point for browsing, enrolling in,
tracking, and viewing community impact of weekly green pledges.
"""

import streamlit as st
from datetime import datetime

from src.utils.green_pledge_tracker import (
    init_pledge_tables,
    get_all_templates,
    get_categories,
    get_template_by_id,
    create_pledge,
    checkin_pledge,
    abandon_pledge,
    get_user_weekly_pledges,
    get_user_all_pledges,
    get_user_pledge_stats,
    get_pledge_checkin_dates,
    get_community_impact,
    estimate_co2_equivalents,
    suggest_pledges_for_user,
    project_annual_co2_saved,
    weekly_streak_calendar,
    pledge_to_dict,
    export_user_pledges_json,
    current_week_start,
    current_week_end,
    PLEDGE_CATEGORIES,
)

st.set_page_config(page_title="Green Pledges", page_icon="🤝", layout="wide")

# Initialise tables on first load
init_pledge_tables()

# ── Auth gate ────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("🔒 Please sign in to use Green Pledges.")
    st.stop()

# ── Page header ──────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:10px 0 4px;'>
    <h1 style='margin:0;font-size:2.4rem;'>🤝 Community Green Pledges</h1>
    <p style='color:#6b7280;margin-top:4px;font-size:1.05rem;'>
        Make weekly sustainability commitments, track your streak, and see your collective impact.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────────────
tab_browse, tab_my, tab_stats, tab_community, tab_export = st.tabs([
    "🔍 Browse Pledges",
    "✅ My Pledges",
    "📊 My Stats",
    "🌍 Community Impact",
    "📦 Export",
])

# =====================================================================
# TAB: Browse Pledges
# =====================================================================
with tab_browse:
    st.subheader("Available Pledges")
    st.caption(f"Week: **{current_week_start()}** → **{current_week_end()}**")

    # Category filter
    cats = get_categories()
    cat_labels = ["All"] + [v["label"] for v in cats.values()]
    cat_keys = ["all"] + list(cats.keys())
    selected = st.radio(
        "Filter by category",
        cat_labels,
        horizontal=True,
        key="pledge_cat_filter",
    )
    cat_filter = cat_keys[cat_labels.index(selected)]

    templates = get_all_templates()
    if cat_filter != "all":
        templates = [t for t in templates if t.category == cat_filter]

    # Already enrolled this week
    my_pledges = get_user_weekly_pledges(user_id)
    enrolled_ids = {p.template_id for p in my_pledges}

    # Suggest top picks
    user_footprint = st.session_state.get("footprint", 5000.0)
    suggestions = suggest_pledges_for_user(user_footprint, my_pledges, n=4)
    sugg_ids = {s["template_id"] for s in suggestions}

    if suggestions:
        st.markdown("#### ⭐ Recommended for You")
        cols = st.columns(min(len(suggestions), 4))
        for idx, sug in enumerate(suggestions):
            with cols[idx]:
                tpl = get_template_by_id(sug["template_id"])
                cat_info = PLEDGE_CATEGORIES.get(tpl.category, {})
                st.markdown(f"""
                <div style='border:1px solid #e5e7eb;border-radius:12px;padding:14px;
                            background:linear-gradient(135deg,#f0fdf4,#ffffff);margin-bottom:8px;'>
                    <span style='font-size:1.3rem;'>{cat_info.get('label', '')}</span>
                    <h4 style='margin:6px 0 2px;'>{tpl.title}</h4>
                    <p style='font-size:0.85rem;color:#6b7280;margin:0;'>{tpl.description}</p>
                    <p style='font-size:0.8rem;margin:6px 0 0;'>
                        <b>🌱 {tpl.weekly_co2_saved_kg} kg CO₂/wk</b>
                        &nbsp;·&nbsp; ⭐ {tpl.xp_reward} XP
                        &nbsp;·&nbsp; 📊 Fit: {sug['fit_score']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                if tpl.id not in enrolled_ids:
                    if st.button(f"Enrol", key=f"enrol_sug_{tpl.id}"):
                        result = create_pledge(user_id, tpl.id)
                        if result:
                            st.success(f"✅ Enrolled in **{tpl.title}**!")
                            st.rerun()
                        else:
                            st.error("Could not enrol — maybe already active.")
                else:
                    st.info("Already enrolled ✅")

        st.divider()

    # All pledges grid
    st.markdown("#### 📋 All Pledges")
    diff_filter = st.selectbox(
        "Difficulty",
        ["All", "Easy", "Medium", "Hard"],
        key="pledge_diff_filter",
    )
    if diff_filter != "All":
        templates = [t for t in templates if t.difficulty == diff_filter.lower()]

    cols_per_row = 3
    for row_start in range(0, len(templates), cols_per_row):
        cols = st.columns(cols_per_row)
        for ci, tpl in enumerate(templates[row_start:row_start + cols_per_row]):
            with cols[ci]:
                cat_info = PLEDGE_CATEGORIES.get(tpl.category, {})
                enrolled = tpl.id in enrolled_ids
                status_badge = "✅ Enrolled" if enrolled else ""
                diff_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(tpl.difficulty, "⚪")

                st.markdown(f"""
                <div style='border:1px solid #e5e7eb;border-radius:12px;padding:16px;
                            min-height:180px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,0.04);'>
                    <span style='font-size:0.8rem;color:{cat_info.get('color', '#888')};font-weight:600;'>
                        {cat_info.get('label', tpl.category)}
                    </span>
                    <span style='float:right;font-size:0.8rem;'>{diff_emoji} {tpl.difficulty.title()}</span>
                    <h4 style='margin:8px 0 4px;'>{tpl.title}</h4>
                    <p style='font-size:0.85rem;color:#6b7280;margin:0;'>{tpl.description}</p>
                    <p style='font-size:0.82rem;margin:8px 0 0;'>
                        🌱 {tpl.weekly_co2_saved_kg} kg CO₂
                        &nbsp;·&nbsp; ⭐ {tpl.xp_reward} XP
                        &nbsp;·&nbsp; 💎 {tpl.eco_points} pts
                    </p>
                </div>
                """, unsafe_allow_html=True)

                if enrolled:
                    st.caption(status_badge)
                else:
                    if st.button(f"🤝 Enrol", key=f"enrol_{tpl.id}", use_container_width=True):
                        result = create_pledge(user_id, tpl.id)
                        if result:
                            st.success(f"✅ Enrolled!")
                            st.rerun()
                        else:
                            st.error("Already enrolled this week.")

# =====================================================================
# TAB: My Pledges
# =====================================================================
with tab_my:
    st.subheader("My Active Pledges")
    week = current_week_start()
    my_active = get_user_weekly_pledges(user_id, week)
    my_all = get_user_all_pledges(user_id, limit=30)

    if not my_active:
        st.info("You haven't enrolled in any pledges this week. Head to **Browse Pledges** to get started!")
    else:
        for p in my_active:
            tpl = get_template_by_id(p.template_id)
            cat_info = PLEDGE_CATEGORIES.get(tpl.category, {}) if tpl else {}
            title = tpl.title if tpl else p.template_id
            desc = tpl.description if tpl else ""

            st.markdown(f"""
            <div style='border:1px solid #d1fae5;border-radius:12px;padding:18px;
                        background:linear-gradient(135deg,#f0fdf4,#ecfdf5);margin-bottom:12px;'>
                <span style='font-size:1.1rem;'>{cat_info.get('label', '')}</span>
                <h3 style='margin:4px 0;'>{title}</h3>
                <p style='color:#6b7280;font-size:0.9rem;margin:0;'>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

            # Progress bar
            progress = min(p.day_checkins / 7.0, 1.0)
            st.progress(progress, text=f"Day {p.day_checkins}/7 — {p.completion_pct:.0f}% complete")

            # Check-in dates
            dates = get_pledge_checkin_dates(p.pledge_id)
            if dates:
                st.caption("📅 Checked in: " + ", ".join(dates))

            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                if st.button("✅ Check In Today", key=f"checkin_{p.pledge_id}", use_container_width=True):
                    result = checkin_pledge(user_id, p.pledge_id)
                    if result:
                        if result.status == "completed":
                            st.balloons()
                            st.success(f"🎉 Pledge completed! Earned {result.earned_xp} XP and {result.earned_eco_points} eco points!")
                        else:
                            st.success(f"✅ Checked in! {result.day_checkins}/7 days")
                        st.rerun()
                    else:
                        st.warning("Already checked in today or pledge inactive.")
            with col2:
                note = st.text_input("Note", key=f"note_{p.pledge_id}", placeholder="How was it?", label_visibility="collapsed")
            with col3:
                if st.button("🚫 Abandon", key=f"abandon_{p.pledge_id}", type="secondary", use_container_width=True):
                    abandon_pledge(user_id, p.pledge_id)
                    st.warning("Pledge abandoned.")
                    st.rerun()

    # ── History ───────────────────────────────────────────────────────
    if my_all:
        st.divider()
        st.subheader("📜 Pledge History")
        for p in my_all:
            tpl = get_template_by_id(p.template_id)
            title = tpl.title if tpl else p.template_id
            status_emoji = {
                "completed": "✅",
                "active": "🔄",
                "missed": "❌",
                "abandoned": "🚫",
            }.get(p.status, "❓")
            st.markdown(
                f"{status_emoji} **{title}** — Week of {p.week_start} "
                f"| {p.day_checkins}/7 days | {p.completion_pct:.0f}% "
                f"| {'+' + str(p.earned_xp) + ' XP' if p.earned_xp else '—'}"
            )

# =====================================================================
# TAB: My Stats
# =====================================================================
with tab_stats:
    st.subheader("📊 My Pledge Stats")
    stats = get_user_pledge_stats(user_id)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Level", stats.level)
    c2.metric("Total Completed", stats.total_pledges_completed)
    c3.metric("Current Streak", f"{stats.current_streak} wks")
    c4.metric("CO₂ Saved", f"{stats.total_co2_saved_kg:.1f} kg")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Total XP", stats.total_xp_earned)
    c6.metric("Eco Points", stats.total_eco_points)
    c7.metric("Completion Rate", f"{stats.completion_rate_pct:.1f}%")
    c8.metric("Best Streak", f"{stats.best_streak} wks")

    # Streak calendar
    st.markdown("#### 📅 Streak Calendar (Last 12 Weeks)")
    cal = weekly_streak_calendar(user_id, weeks=12)
    cal_html = "<div style='display:flex;gap:6px;flex-wrap:wrap;margin:8px 0;'>"
    for week in cal:
        if week["status"] == "completed":
            bg = "#22c55e"
            title = f"✅ {week['week_start']}"
        elif week["status"] == "active":
            bg = "#f59e0b"
            title = f"🔄 {week['week_start']}"
        else:
            bg = "#e5e7eb"
            title = f"⬜ {week['week_start']}"
        cal_html += (
            f"<div title='{title}' style='width:36px;height:36px;border-radius:6px;"
            f"background:{bg};display:flex;align-items:center;justify-content:center;"
            f"font-size:0.6rem;color:#fff;font-weight:700;'>"
            f"{week['week_start'][-2:]}</div>"
        )
    cal_html += "</div>"
    st.markdown(cal_html, unsafe_allow_html=True)

    # Projection
    if stats.total_pledges_completed > 0:
        st.markdown("#### 🔮 Annual Projection")
        proj = project_annual_co2_saved(user_id)
        eq = proj["equivalents"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Projected Annual CO₂", f"{proj['annual_estimate_kg']:.1f} kg")
        c2.metric("Equivalent Car km", f"{eq['car_km']:.0f} km")
        c3.metric("Trees Equivalent", f"{eq['trees_needed']:.1f} 🌳")

    # Badges
    if stats.badges:
        st.markdown("#### 🏅 Badges Earned")
        badge_html = "<div style='display:flex;gap:10px;flex-wrap:wrap;'>"
        for b in stats.badges:
            badge_html += (
                f"<div style='background:linear-gradient(135deg,#f0fdf4,#dcfce7);"
                f"border:1px solid #bbf7d0;border-radius:10px;padding:8px 14px;"
                f"font-size:0.85rem;font-weight:600;'>{b}</div>"
            )
        badge_html += "</div>"
        st.markdown(badge_html, unsafe_allow_html=True)

# =====================================================================
# TAB: Community Impact
# =====================================================================
with tab_community:
    st.subheader("🌍 Community Impact")
    impact = get_community_impact()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Participants", impact.total_participants)
    c2.metric("Total Pledges", impact.total_pledges)
    c3.metric("Completed", impact.total_completed)
    c4.metric("Community CO₂ Saved", f"{impact.community_co2_saved_kg:.1f} kg")

    st.metric("Active This Week", impact.active_this_week)

    if impact.community_co2_saved_kg > 0:
        eq = estimate_co2_equivalents(impact.community_co2_saved_kg)
        st.markdown(f"""
        **Community equivalents:**
        - 🚗 {eq['car_km']:.0f} km of driving avoided
        - 🌳 {eq['trees_needed']:.0f} trees' annual absorption
        - 📱 {eq['smartphone_charges']:.0f} smartphone charges saved
        """, unsafe_allow_html=True)

    if impact.weekly_trend:
        st.markdown("#### 📈 Weekly Trend")
        import pandas as pd
        df = pd.DataFrame(impact.weekly_trend)
        if not df.empty:
            st.line_chart(df.set_index("week")[["completed", "users"]])

    if impact.top_categories:
        st.markdown("#### 🏆 Most Popular Pledges")
        for item in impact.top_categories[:5]:
            tpl = get_template_by_id(item["template_id"])
            if tpl:
                st.markdown(f"- **{tpl.title}** — {item['count']} enrolments")

# =====================================================================
# TAB: Export
# =====================================================================
with tab_export:
    st.subheader("📦 Export Pledge Data")
    st.write("Download your complete pledge history as JSON.")

    json_data = export_user_pledges_json(user_id)
    st.download_button(
        label="📥 Download JSON",
        data=json_data,
        file_name="my_green_pledges.json",
        mime="application/json",
        use_container_width=True,
    )

    st.markdown("#### Preview")
    st.json(json_data)
