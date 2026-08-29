"""
Page: Eco Impact Time Capsule
================================
Capture your eco state at a point in time, seal it as a capsule,
and compare your growth over days, weeks, and months.
"""

import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Eco Time Capsule", page_icon="📸", layout="wide")

from src.utils.eco_time_capsule_service import (
    create_snapshot_capsule, get_user_dashboard, open_capsule,
    compare_capsules, auto_detect_milestones, get_timeline_data,
    get_growth_summary,
)
from src.reporting.eco_time_capsule_cards import (
    inject_css, render_capsule_card, render_comparison, render_milestone,
    render_timeline_item, render_growth_card, render_create_form,
)
from src.reporting.eco_time_capsule_charts import (
    render_timeline_chart, render_mood_distribution, render_comparison_radar,
    render_score_gauge, render_capsule_type_bar,
)
from src.utils.eco_time_capsule_db import get_milestones, get_reflections, add_reflection, MOOD_EMOJI

inject_css()

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("🔐 Please log in to use Eco Time Capsule.")
    st.stop()

st.markdown("""
<div style="text-align:center;padding:20px 0 12px;background:linear-gradient(135deg,rgba(99,102,241,0.06),rgba(168,85,247,0.04));border-radius:16px;margin-bottom:20px;">
    <span style="font-size:36px;">📸</span>
    <h1 style="margin:6px 0 2px;font-size:28px;font-weight:900;">Eco Time Capsule</h1>
    <p style="color:#6b7280;font-size:14px;">Seal your eco moments, compare your growth, and reflect on your journey.</p>
</div>""", unsafe_allow_html=True)

dashboard = get_user_dashboard(user_id)
stats = dashboard.get("stats", {})

# ── Stats Row ───────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("📦 Total Capsules", stats.get("total_capsules", 0))
with c2: st.metric("📂 Opened", stats.get("opened", 0))
with c3: st.metric("🔒 Sealed", stats.get("pending", 0))
with c4: st.metric("⭐ Avg Score", stats.get("avg_eco_score", 0))

# ── Growth Summary ──────────────────────────────────────────────────────
growth = get_growth_summary(user_id)
render_growth_card(growth)

# ── Tabs ────────────────────────────────────────────────────────────────
st.markdown("---")
tab_create, tab_capsules, tab_compare, tab_timeline, tab_insights = st.tabs([
    "📸 Create", "📦 My Capsules", "🔍 Compare", "📅 Timeline", "📊 Insights"
])

with tab_create:
    form = render_create_form()
    if form["submitted"]:
        if not form["title"]:
            st.error("Please enter a title.")
        else:
            result = create_snapshot_capsule(
                user_id=user_id, title=form["title"], capsule_type=form["capsule_type"],
                eco_score=form["eco_score"], carbon_kg=form["carbon_kg"],
                streak_days=form["streak_days"], badges_earned=form["badges_earned"],
                challenges_done=form["challenges_done"], mood=form["mood"],
                notes=form["notes"], open_date=form["open_date"])
            if result["success"]:
                cid = result["capsule_id"]
                milestones = auto_detect_milestones(cid)
                st.success(f"📸 Time capsule sealed! (ID: {cid})")
                if milestones:
                    st.markdown("**🏆 Milestones Detected:**")
                    for m in milestones:
                        render_milestone({"title": m})
                st.balloons()
                st.rerun()

with tab_capsules:
    if not dashboard.get("capsules"):
        st.info("No capsules yet. Create your first one above! 📸")
    else:
        # Ready to open
        if dashboard.get("ready_to_open"):
            st.subheader("🎁 Ready to Open!")
            for c in dashboard["ready_to_open"]:
                render_capsule_card(c)
                if st.button("🔓 Open Capsule", key=f"open_{c['id']}"):
                    result = open_capsule(c["id"], user_id)
                    if result["success"]:
                        st.success("🎉 Capsule opened!")
                        for m in result.get("milestones", []):
                            render_milestone(m)
                        st.rerun()

        # Sealed
        if dashboard.get("sealed"):
            st.subheader("🔒 Sealed Capsules")
            for c in dashboard["sealed"]:
                render_capsule_card(c, show_actions=False)

        # Opened
        if dashboard.get("opened"):
            st.subheader("📂 Opened Capsules")
            for c in dashboard["opened"]:
                render_capsule_card(c)
                milestones = get_milestones(c["id"])
                if milestones:
                    with st.expander(f"🏆 Milestones ({len(milestones)})"):
                        for m in milestones:
                            render_milestone(m)
                # Reflections
                reflections = get_reflections(c["id"])
                with st.expander(f"💭 Reflections ({len(reflections)})"):
                    for r in reflections:
                        st.markdown(f"*{r['reflection_text']}* — {'⭐' * r.get('rating',5)} ({r['created_at'][:10]})")
                    ref_text = st.text_input("Add reflection", key=f"ref_{c['id']}")
                    ref_rating = st.slider("Rating", 1, 5, 5, key=f"rating_{c['id']}")
                    if st.button("Save", key=f"saveref_{c['id']}"):
                        if ref_text:
                            add_reflection(c["id"], ref_text, ref_rating)
                            st.success("Reflection saved!")
                            st.rerun()

with tab_compare:
    capsules = dashboard.get("capsules", [])
    if len(capsules) < 2:
        st.info("You need at least 2 capsules to compare.")
    else:
        st.subheader("🔍 Compare Two Capsules")
        opts = [(c["id"], f"{c['title']} ({c['created_at'][:10]})") for c in capsules]
        c1, c2 = st.columns(2)
        with c1:
            a_id = st.selectbox("Capsule A", opts, format_func=lambda x: x[1])
        with c2:
            b_id = st.selectbox("Capsule B", opts, index=min(1, len(opts)-1), format_func=lambda x: x[1])
        if st.button("🔍 Compare", use_container_width=True):
            result = compare_capsules(a_id[0], b_id[0])
            if "error" in result:
                st.error(result["error"])
            else:
                render_comparison(result)
                fig_radar = render_comparison_radar(result)
                st.plotly_chart(fig_radar, use_container_width=True)

with tab_timeline:
    timeline = get_timeline_data(user_id)
    if not timeline:
        st.info("No capsules to show on timeline.")
    else:
        fig_timeline = render_timeline_chart(timeline)
        st.plotly_chart(fig_timeline, use_container_width=True)
        st.subheader("📅 Chronological View")
        for item in timeline:
            render_timeline_item(item)

with tab_insights:
    if not capsules:
        st.info("Create capsules to unlock insights.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            fig_mood = render_mood_distribution(capsules)
            st.plotly_chart(fig_mood, use_container_width=True)
        with col2:
            fig_types = render_capsule_type_bar(capsules)
            st.plotly_chart(fig_types, use_container_width=True)

        # Latest score gauge
        latest = capsules[0]
        fig_gauge = render_score_gauge(latest.get("eco_score", 0), "Latest Eco Score")
        st.plotly_chart(fig_gauge, use_container_width=True)

st.markdown("---")
st.markdown("""
<div style="text-align:center;padding:14px;color:#9ca3af;font-size:13px;">
    📸 Eco Time Capsule — Capture, seal, and compare your eco journey · Powered by EcoBuddy AI
</div>""", unsafe_allow_html=True)
