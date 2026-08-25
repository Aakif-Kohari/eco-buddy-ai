"""
Page: Carbon Budget Planner
=============================
Set monthly carbon budgets, log daily spending, track category limits,
receive smart alerts, and visualize your carbon reduction journey.
"""

import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Carbon Budget Planner", page_icon="🎯", layout="wide")

from carbon_budget_service import (
    setup_budget, get_budget_summary, add_spending, quick_log,
    get_projection, get_category_suggestions, get_savings_tips,
)
from carbon_budget_cards import (
    inject_css, render_budget_overview_card, render_stat_grid,
    render_category_card, render_alert, render_suggestion_card,
    render_spending_log_form, render_budget_setup_form,
)
from carbon_budget_charts import (
    render_gauge_chart, render_category_bar_chart, render_daily_trend,
    render_projection_chart, render_history_line, render_pie_chart,
    render_co2_equivalence,
)
from carbon_budget_db import (
    seed_default_categories, ACTIVITY_CO2_DATABASE, get_unread_alerts,
    mark_alert_read, get_budget_history, get_spending_logs,
)

inject_css()

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("🔐 Please log in to use Carbon Budget Planner.")
    st.stop()

st.markdown("""
<div style="text-align:center;padding:20px 0 12px;background:linear-gradient(135deg,rgba(34,197,94,0.06),rgba(59,130,246,0.04));border-radius:16px;margin-bottom:20px;">
    <span style="font-size:36px;">🎯</span>
    <h1 style="margin:6px 0 2px;font-size:28px;font-weight:900;">Carbon Budget Planner</h1>
    <p style="color:#6b7280;font-size:14px;">Set limits, track spending, and stay on track with your carbon goals.</p>
</div>""", unsafe_allow_html=True)

categories = seed_default_categories()

# ── Setup or Summary ───────────────────────────────────────────────────
summary = get_budget_summary(user_id)

if not summary.get("has_budget"):
    st.info("No carbon budget set yet. Let's create one!")
    form = render_budget_setup_form()
    if form["submitted"]:
        setup_budget(user_id, form["monthly_limit_kg"])
        st.success("🎯 Carbon budget created!")
        st.rerun()
    st.stop()

# ── Alerts ─────────────────────────────────────────────────────────────
alerts = get_unread_alerts(user_id)
if alerts:
    with st.expander(f"🔔 {len(alerts)} New Alert(s)", expanded=True):
        for a in alerts:
            render_alert(a)
            if st.button("Dismiss", key=f"dismiss_{a['id']}"):
                mark_alert_read(a["id"])
                st.rerun()

# ── Overview ───────────────────────────────────────────────────────────
render_budget_overview_card(summary)
render_stat_grid({
    "daily_avg": f"{summary['daily_avg']} kg",
    "projected_month": f"{summary['projected_month']} kg",
    "daily_budget": f"{summary['daily_budget']} kg",
    "on_track": summary["on_track"],
})

# ── Equivalence ────────────────────────────────────────────────────────
if summary["monthly_spent"] > 0:
    saved = max(0, summary["monthly_limit"] - summary["monthly_spent"])
    if saved > 0:
        fig_eq = render_co2_equivalence(saved)
        st.plotly_chart(fig_eq, use_container_width=True)

# ── Main Tabs ──────────────────────────────────────────────────────────
st.markdown("---")
tab_log, tab_cats, tab_proj, tab_history, tab_tips = st.tabs([
    "📝 Log Spending", "📊 Categories", "📈 Projections", "📅 History", "💡 Tips"
])

# ── Log Spending ───────────────────────────────────────────────────────
with tab_log:
    form_data = render_spending_log_form(categories, ACTIVITY_CO2_DATABASE)
    if form_data["submitted"]:
        result = add_spending(user_id, form_data["category"], form_data["activity"],
                              form_data["co2_kg"], form_data["log_date"])
        if result["success"]:
            st.success(f"✅ Logged {form_data['co2_kg']:.1f} kg CO₂ for {form_data['activity']}")
            st.rerun()

    # Recent logs
    st.subheader("📋 Recent Spending")
    logs = get_spending_logs(user_id, limit=15)
    if logs:
        for log in logs:
            cat_label = categories.get(log["category"], {}).get("label", log["category"])
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-radius:10px;border:1px solid rgba(0,0,0,0.06);margin-bottom:6px;background:rgba(255,255,255,0.5);">
                <div>
                    <span style="font-weight:700;">{cat_label}</span>
                    <span style="color:#6b7280;font-size:13px;margin-left:8px;">{log['activity']}</span>
                </div>
                <div style="text-align:right;">
                    <span style="font-weight:800;color:#ef4444;">{log['co2_kg']:.1f} kg</span>
                    <span style="font-size:11px;color:#9ca3af;margin-left:6px;">{log['log_date']}</span>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.caption("No spending logged yet this month.")

# ── Categories ─────────────────────────────────────────────────────────
with tab_cats:
    st.subheader("📊 Category Breakdown")
    cat_status = summary.get("category_status", {})
    cat_labels = {k: v["label"] for k, v in categories.items()}
    for cat, status in cat_status.items():
        label = cat_labels.get(cat, cat)
        color = categories.get(cat, {}).get("color", "#22c55e")
        render_category_card(cat, label, status["spent"], status["limit"], color)

    # Charts
    col_pie, col_bar = st.columns(2)
    with col_pie:
        cat_data = summary.get("category_breakdown", {})
        if cat_data:
            fig_pie = render_pie_chart(cat_data, cat_labels)
            st.plotly_chart(fig_pie, use_container_width=True)
    with col_bar:
        cat_limits = summary.get("budget", {}).get("category_limits", {})
        cat_data = summary.get("category_breakdown", {})
        if cat_data:
            fig_bar = render_category_bar_chart(cat_data, cat_limits, cat_labels)
            st.plotly_chart(fig_bar, use_container_width=True)

# ── Projections ────────────────────────────────────────────────────────
with tab_proj:
    proj = get_projection(user_id)
    col_gauge, col_proj = st.columns(2)
    with col_gauge:
        fig_gauge = render_gauge_chart(summary["monthly_spent"], summary["monthly_limit"])
        st.plotly_chart(fig_gauge, use_container_width=True)
    with col_proj:
        fig_proj = render_projection_chart(
            proj["projected_total"], proj["limit"], proj["daily_avg"], proj["days_remaining"])
        st.plotly_chart(fig_proj, use_container_width=True)

    if proj["will_exceed"]:
        st.warning(f"⚠️ At current rate, you'll exceed your budget by **{proj['projected_total'] - proj['limit']:.1f} kg**. "
                   f"Reduce daily spending by **{proj['daily_saving_needed']:.1f} kg/day** to stay on track.")
    else:
        st.success(f"✅ You're on track! Projected spend: **{proj['projected_total']:.1f} kg** "
                   f"(under your **{proj['limit']:.0f} kg** budget).")

    # Daily trend
    daily = summary.get("daily_history", [])
    if daily:
        fig_trend = render_daily_trend(daily, summary.get("daily_budget", 16.7))
        st.plotly_chart(fig_trend, use_container_width=True)

# ── History ────────────────────────────────────────────────────────────
with tab_history:
    st.subheader("📅 Monthly Budget History")
    history = get_budget_history(user_id)
    if history:
        fig_hist = render_history_line(history)
        st.plotly_chart(fig_hist, use_container_width=True)

        st.dataframe([
            {"Month": h["month"], "Spent (kg)": h["total_spent_kg"],
             "Limit (kg)": h["monthly_limit_kg"], "Saved (kg)": h["savings_kg"]}
            for h in history
        ], use_container_width=True)
    else:
        st.info("No history yet. Complete a month to see your budget history.")

# ── Tips ───────────────────────────────────────────────────────────────
with tab_tips:
    st.subheader("💡 Smart Suggestions")
    suggestions = get_category_suggestions(user_id)
    if suggestions:
        for s in suggestions:
            render_suggestion_card(s)
    else:
        st.success("🌟 Great job! You're within budget across all categories.")

    st.markdown("---")
    st.subheader("🌱 Savings Tips by Category")
    for cat, info in categories.items():
        with st.expander(f"{info['label']} Tips"):
            for tip in get_savings_tips(cat):
                st.markdown(f"- {tip}")

st.markdown("---")
st.markdown("""
<div style="text-align:center;padding:14px;color:#9ca3af;font-size:13px;">
    🎯 Carbon Budget Planner — Track, limit, and reduce your carbon spending · Powered by EcoBuddy AI
</div>""", unsafe_allow_html=True)
