"""
Pledge Impact Insights – Streamlit Page
========================================
Rich analytics dashboard for pledge impact: trends, predictions,
milestones, personalised insights, community comparisons, and
downloadable impact reports.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from src.community.pledge_impact_engine import (
    init_impact_tables,
    get_weekly_impacts,
    analyse_trend,
    predict_future_impact,
    check_milestones,
    get_user_milestones,
    generate_insights,
    get_category_breakdown,
    generate_comparison_report,
    generate_full_report,
    export_report_json,
    get_report_history,
    MILESTONE_DEFINITIONS,
    INSIGHT_CATEGORIES,
)
from src.utils.green_pledge_tracker import (
    init_pledge_tables,
    current_week_start,
    current_week_end,
    get_user_pledge_stats,
    estimate_co2_equivalents,
    PLEDGE_CATEGORIES,
)

st.set_page_config(page_title="Pledge Insights", page_icon="📊", layout="wide")

# Initialise tables
init_pledge_tables()
init_impact_tables()

# ── Auth gate ────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("🔒 Please sign in to view Pledge Insights.")
    st.stop()

# ── Page header ──────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:10px 0 4px;'>
    <h1 style='margin:0;font-size:2.4rem;'>📊 Pledge Impact Insights</h1>
    <p style='color:#6b7280;margin-top:4px;font-size:1.05rem;'>
        Deep analytics, trends, predictions, and personalised insights for your pledge journey.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────────────
tab_overview, tab_trends, tab_predict, tab_milestones, tab_insights, tab_compare, tab_report = st.tabs([
    "📊 Overview",
    "📈 Trends",
    "🔮 Predictions",
    "🏆 Milestones",
    "💡 Insights",
    "⚖️ Compare",
    "📄 Report",
])

# =====================================================================
# TAB: Overview
# =====================================================================
with tab_overview:
    st.subheader("📊 Impact Overview")

    stats = get_user_pledge_stats(user_id)
    weekly = get_weekly_impacts(user_id, weeks=12)
    cat_breakdown = get_category_breakdown(user_id)

    # Key metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌍 Total CO₂ Saved", f"{stats.total_co2_saved_kg:.1f} kg")
    c2.metric("⭐ Total XP", f"{stats.total_xp_earned}")
    c3.metric("✅ Pledges Completed", f"{stats.total_pledges_completed}")
    c4.metric("🔥 Current Streak", f"{stats.current_streak} wks")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("📈 Completion Rate", f"{stats.completion_rate_pct:.1f}%")
    c6.metric("🏆 Best Streak", f"{stats.best_streak} wks")
    c7.metric("💎 Eco Points", f"{stats.total_eco_points}")
    c8.metric("🌱 Level", stats.level)

    st.divider()

    # Category breakdown
    st.markdown("#### 📂 Category Breakdown")

    if any(cb.total_enrolled > 0 for cb in cat_breakdown):
        active_cats = [cb for cb in cat_breakdown if cb.total_enrolled > 0]

        # Bar chart
        fig_bar = go.Figure(data=[
            go.Bar(
                x=[cb.label for cb in active_cats],
                y=[cb.co2_saved_kg for cb in active_cats],
                marker_color=[cb.color for cb in active_cats],
                name="CO₂ Saved (kg)",
            )
        ])
        fig_bar.update_layout(
            title="CO₂ Saved by Category",
            height=300,
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis_title="Category",
            yaxis_title="kg CO₂",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Detailed cards
        cols = st.columns(min(len(active_cats), 3))
        for idx, cb in enumerate(active_cats):
            with cols[idx % len(cols)]:
                st.markdown(f"""
                <div style='border:1px solid {cb.color}30;border-radius:14px;padding:16px;
                            background:linear-gradient(135deg,{cb.color}08,#fff);margin-bottom:8px;'>
                    <h4 style='margin:0;color:{cb.color};'>{cb.label}</h4>
                    <p style='margin:4px 0;font-size:0.85rem;color:#6b7280;'>
                        {cb.total_completed}/{cb.total_enrolled} completed · {cb.co2_saved_kg:.1f} kg CO₂
                    </p>
                    <p style='margin:0;font-size:0.8rem;color:#9ca3af;'>
                        ⭐ {cb.avg_xp_per_pledge:.0f} avg XP · 📊 {cb.completion_rate:.0f}% rate
                    </p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No category data yet. Complete some pledges to see your breakdown!")

    # Weekly activity
    if weekly:
        st.divider()
        st.markdown("#### 📅 Weekly Activity (Last 12 Weeks)")

        active_weeks = [w for w in weekly if w.pledges_enrolled > 0]
        if active_weeks:
            df = pd.DataFrame([{
                "Week": w.week_start,
                "CO₂ Saved (kg)": w.co2_saved_kg,
                "XP Earned": w.xp_earned,
                "Checkins": w.checkins,
                "Completed": w.pledges_completed,
            } for w in active_weeks])

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["Week"], y=df["CO₂ Saved (kg)"],
                name="CO₂ Saved", marker_color="#4ade80",
            ))
            fig.add_trace(go.Scatter(
                x=df["Week"], y=df["XP Earned"],
                name="XP Earned", mode="lines+markers",
                line=dict(color="#f59e0b", width=2),
                yaxis="y2",
            ))
            fig.update_layout(
                title="Weekly CO₂ Saved & XP Earned",
                height=350,
                margin=dict(l=0, r=0, t=40, b=0),
                yaxis=dict(title="CO₂ (kg)"),
                yaxis2=dict(title="XP", overlaying="y", side="right"),
                legend=dict(x=0, y=1.12, orientation="h"),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No weekly data yet. Start completing pledges to see your impact over time!")

    # Equivalents
    if stats.total_co2_saved_kg > 0:
        st.divider()
        st.markdown("#### 🌍 Your Impact in Real Terms")
        eq = estimate_co2_equivalents(stats.total_co2_saved_kg)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🚗 Driving Avoided", f"{eq['car_km']:.0f} km")
        c2.metric("🌳 Trees Equivalent", f"{eq['trees_needed']:.1f}")
        c3.metric("📱 Phone Charges", f"{eq['smartphone_charges']:.0f}")
        c4.metric("🍔 Beef Burgers", f"{eq['beef_burgers']:.0f}")


# =====================================================================
# TAB: Trends
# =====================================================================
with tab_trends:
    st.subheader("📈 Trend Analysis")

    trend = analyse_trend(user_id)

    # Direction card
    direction_styles = {
        "improving": ("📈", "#22c55e", "Your activity is trending upward!"),
        "stable": ("➡️", "#f59e0b", "Your activity is steady."),
        "declining": ("📉", "#ef4444", "Your activity has been declining."),
        "insufficient_data": ("❓", "#6b7280", "Not enough data for trend analysis."),
    }
    emoji, color, _ = direction_styles.get(trend.direction, ("❓", "#6b7280", ""))

    st.markdown(f"""
    <div style='border:2px solid {color}40;border-radius:16px;padding:24px;
                background:linear-gradient(135deg,{color}08,#fff);'>
        <div style='display:flex;align-items:center;gap:12px;'>
            <span style='font-size:2.5rem;'>{emoji}</span>
            <div>
                <h3 style='margin:0;color:{color};'>Trend: {trend.direction.replace('_', ' ').title()}</h3>
                <p style='color:#6b7280;margin:4px 0 0;'>{trend.summary}</p>
            </div>
        </div>
        <div style='display:flex;gap:24px;margin-top:12px;'>
            <div>
                <span style='font-size:0.8rem;color:#9ca3af;'>Slope</span>
                <div style='font-size:1.2rem;font-weight:700;'>{trend.slope:+.2f} kg/wk</div>
            </div>
            <div>
                <span style='font-size:0.8rem;color:#9ca3af;'>Confidence</span>
                <div style='font-size:1.2rem;font-weight:700;'>{trend.confidence:.0%}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Moving average chart
    if trend.moving_average:
        st.divider()
        st.markdown("#### 📊 Moving Average (4-Week)")
        df_ma = pd.DataFrame({
            "Week": list(range(len(trend.moving_average))),
            "Moving Average CO₂ (kg)": trend.moving_average,
        })
        fig_ma = px.line(df_ma, x="Week", y="Moving Average CO₂ (kg)", markers=True)
        fig_ma.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_ma, use_container_width=True)

    # Trend forecast
    if trend.forecast:
        st.divider()
        st.markdown("#### 📉 Trend Forecast (Next 12 Weeks)")
        df_fc = pd.DataFrame(trend.forecast)
        fig_fc = px.line(df_fc, x="week_offset", y="predicted_co2_kg", markers=True,
                         labels={"week_offset": "Weeks Ahead", "predicted_co2_kg": "Predicted CO₂ (kg)"})
        fig_fc.update_traces(line_color="#4ade80")
        fig_fc.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_fc, use_container_width=True)


# =====================================================================
# TAB: Predictions
# =====================================================================
with tab_predict:
    st.subheader("🔮 Impact Predictions")

    prediction = predict_future_impact(user_id)

    st.markdown(f"""
    <div style='border:1px solid #e0e7ff;border-radius:16px;padding:24px;
                background:linear-gradient(135deg,#eef2ff,#fff);'>
        <h3 style='margin:0 0 8px;'>🔮 Next 12 Weeks Forecast</h3>
        <p style='color:#6b7280;margin:0 0 16px;'>Based on your recent pledge activity</p>
        <div style='display:flex;gap:32px;flex-wrap:wrap;'>
            <div>
                <div style='font-size:2.2rem;font-weight:800;color:#4ade80;'>{prediction.predicted_co2_12w:.1f} kg</div>
                <div style='font-size:0.85rem;color:#6b7280;'>Predicted CO₂ Saved</div>
            </div>
            <div>
                <div style='font-size:2.2rem;font-weight:800;color:#f59e0b;'>{prediction.predicted_xp_12w}</div>
                <div style='font-size:0.85rem;color:#6b7280;'>Predicted XP</div>
            </div>
            <div>
                <div style='font-size:2.2rem;font-weight:800;color:#06b6d4;'>{prediction.predicted_pledges_12w}</div>
                <div style='font-size:0.85rem;color:#6b7280;'>Predicted Pledges</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Confidence interval
    if prediction.confidence_interval:
        ci = prediction.confidence_interval
        st.markdown(f"**Confidence interval:** {ci.get('lower', 0):.1f} – {ci.get('upper', 0):.1f} kg CO₂")

    # Scenario comparison
    st.divider()
    st.markdown("#### 🎯 Scenario Comparison")

    scenarios = pd.DataFrame([
        {"Scenario": "😟 Pessimistic (-30%)", "CO₂ Saved (kg)": prediction.scenario_worse.get("co2_kg", 0), "XP": prediction.scenario_worse.get("xp", 0)},
        {"Scenario": "➡️ Current Pace", "CO₂ Saved (kg)": prediction.predicted_co2_12w, "XP": prediction.predicted_xp_12w},
        {"Scenario": "💪 Optimistic (+20%)", "CO₂ Saved (kg)": prediction.scenario_better.get("co2_kg", 0), "XP": prediction.scenario_better.get("xp", 0)},
    ])

    fig_sc = go.Figure(data=[
        go.Bar(x=scenarios["Scenario"], y=scenarios["CO₂ Saved (kg)"],
               marker_color=["#ef4444", "#4ade80", "#22c55e"], name="CO₂ Saved"),
    ])
    fig_sc.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0), yaxis_title="kg CO₂")
    st.plotly_chart(fig_sc, use_container_width=True)

    # Equivalents
    if prediction.equivalents_12w:
        eq = prediction.equivalents_12w
        st.markdown("#### 🌍 What Your Predicted Savings Mean")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🚗 Driving Avoided", f"{eq.get('car_km', 0):.0f} km")
        c2.metric("🌳 Trees Needed", f"{eq.get('trees_needed', 0):.1f}")
        c3.metric("📱 Phone Charges", f"{eq.get('smartphone_charges', 0):.0f}")
        c4.metric("🍔 Burgers", f"{eq.get('beef_burgers', 0):.0f}")


# =====================================================================
# TAB: Milestones
# =====================================================================
with tab_milestones:
    st.subheader("🏆 Milestones & Achievements")

    milestones = check_milestones(user_id)
    achieved = [m for m in milestones if m.achieved]
    remaining = [m for m in milestones if not m.achieved]

    st.metric("Milestones Achieved", f"{len(achieved)} / {len(milestones)}")

    # Progress bar
    if milestones:
        progress = len(achieved) / len(milestones)
        st.progress(progress, text=f"{progress*100:.0f}% of milestones unlocked")

    # Achieved milestones
    if achieved:
        st.divider()
        st.markdown("#### ✅ Achieved")
        achieved_html = "<div style='display:flex;gap:10px;flex-wrap:wrap;'>"
        for m in achieved:
            defn = MILESTONE_DEFINITIONS.get(
                __import__("pledge_impact_engine", fromlist=["MilestoneType"]).MilestoneType(m.milestone_type),
                {}
            )
            xp_bonus = defn.get("xp_bonus", m.xp_bonus)
            achieved_html += (
                f"<div style='background:linear-gradient(135deg,#f0fdf4,#dcfce7);"
                f"border:1px solid #bbf7d0;border-radius:12px;padding:12px 18px;"
                f"min-width:200px;'>"
                f"<div style='font-size:1.2rem;'>{m.title}</div>"
                f"<p style='color:#6b7280;font-size:0.8rem;margin:2px 0 0;'>{m.description}</p>"
                f"<p style='color:#16a34a;font-size:0.75rem;margin:4px 0 0;'>+{xp_bonus} XP bonus</p>"
                f"</div>"
            )
        achieved_html += "</div>"
        st.markdown(achieved_html, unsafe_allow_html=True)

    # Remaining milestones
    if remaining:
        st.divider()
        st.markdown("#### 🔒 Remaining")
        for m in remaining:
            defn = MILESTONE_DEFINITIONS.get(
                __import__("pledge_impact_engine", fromlist=["MilestoneType"]).MilestoneType(m.milestone_type),
                {}
            )
            xp_bonus = defn.get("xp_bonus", m.xp_bonus)
            st.markdown(
                f"- 🔒 **{m.title}** — {m.description} (+{xp_bonus} XP)"
            )

    # User's achieved milestones from DB
    user_milestones = get_user_milestones(user_id)
    if user_milestones:
        st.divider()
        st.markdown("#### 📅 Achievement Timeline")
        for um in user_milestones:
            st.markdown(f"**{um['title']}** — {um['achieved_at'][:10]} · +{um['xp_bonus']} XP")


# =====================================================================
# TAB: Insights
# =====================================================================
with tab_insights:
    st.subheader("💡 Personalised Insights")

    insights = generate_insights(user_id)

    if not insights:
        st.info("Keep completing pledges to unlock personalised insights!")
    else:
        # Group by priority
        priority_order = ["celebration", "high", "medium", "low"]
        priority_styles = {
            "celebration": ("🎉", "#22c55e", "#f0fdf4"),
            "high": ("⚡", "#f59e0b", "#fffbeb"),
            "medium": ("💡", "#3b82f6", "#eff6ff"),
            "low": ("📝", "#6b7280", "#f9fafb"),
        }

        for priority in priority_order:
            p_insights = [i for i in insights if i.priority == priority]
            if not p_insights:
                continue

            for insight in p_insights:
                emoji, color, bg = priority_styles.get(priority, ("💡", "#6b7280", "#f9fafb"))
                cat_label = INSIGHT_CATEGORIES.get(insight.category, insight.category)

                st.markdown(f"""
                <div style='border:1px solid {color}30;border-radius:14px;padding:18px;
                            background:linear-gradient(135deg,{bg},#fff);margin-bottom:10px;'>
                    <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                        <div>
                            <span style='font-size:0.75rem;color:{color};font-weight:600;'>{cat_label}</span>
                            <h4 style='margin:2px 0 4px;'>{emoji} {insight.title}</h4>
                            <p style='color:#6b7280;margin:0;font-size:0.9rem;'>{insight.body}</p>
                            {f"<p style='color:{color};margin:4px 0 0;font-size:0.85rem;font-weight:600;'>→ {insight.action_suggestion}</p>" if insight.action_suggestion else ""}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


# =====================================================================
# TAB: Compare
# =====================================================================
with tab_compare:
    st.subheader("⚖️ Community Comparison")

    comparison = generate_comparison_report(user_id)

    # Percentile
    st.markdown(f"""
    <div style='border:1px solid #e0e7ff;border-radius:16px;padding:24px;
                background:linear-gradient(135deg,#eef2ff,#fff);text-align:center;'>
        <h3 style='margin:0 0 4px;'>🏆 You're in the Top {100 - comparison.percentile_rank:.0f}%</h3>
        <p style='color:#6b7280;margin:0;'>Based on XP earned across {comparison.vs_community.get('community_size', 0)} groups</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Head-to-head comparison
    st.markdown("#### 📊 You vs Community Average")
    vc = comparison.vs_community
    comp_df = pd.DataFrame([
        {"Metric": "XP Earned", "You": vc.get("user_xp", 0), "Community Avg": vc.get("avg_xp", 0)},
        {"Metric": "CO₂ Saved (kg)", "You": vc.get("user_co2_kg", 0), "Community Avg": vc.get("avg_co2_kg", 0)},
        {"Metric": "Pledges Completed", "You": vc.get("user_pledges", 0), "Community Avg": vc.get("avg_pledges", 0)},
    ])

    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(name="You", x=comp_df["Metric"], y=comp_df["You"], marker_color="#4ade80"))
    fig_comp.add_trace(go.Bar(name="Community Avg", x=comp_df["Metric"], y=comp_df["Community Avg"], marker_color="#94a3b8"))
    fig_comp.update_layout(barmode="group", height=350, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_comp, use_container_width=True)

    # Strengths & areas for improvement
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 💪 Strengths")
        if comparison.strengths:
            for s in comparison.strengths:
                st.markdown(f"- ✅ {s}")
        else:
            st.info("No specific strengths identified yet.")

    with c2:
        st.markdown("#### 📈 Areas for Improvement")
        if comparison.improvement_areas:
            for a in comparison.improvement_areas:
                st.markdown(f"- 🔄 {a}")
        else:
            st.info("You're doing great across the board!")

    # Category comparison
    if comparison.category_comparison:
        st.divider()
        st.markdown("#### 📂 Category Performance")
        cat_df = pd.DataFrame(comparison.category_comparison)
        fig_cat = px.bar(cat_df, x="category", y="completion_rate", color="above_average",
                         color_discrete_map={True: "#4ade80", False: "#f87171"},
                         labels={"category": "Category", "completion_rate": "Completion Rate (%)"},
                         title="Completion Rate by Category")
        fig_cat.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_cat, use_container_width=True)


# =====================================================================
# TAB: Report
# =====================================================================
with tab_report:
    st.subheader("📄 Impact Report")

    col1, col2 = st.columns([2, 1])
    with col1:
        period = st.selectbox("Report Period", [4, 8, 12, 26], index=2, format_func=lambda x: f"{x} weeks")
    with col2:
        if st.button("🚀 Generate Report", use_container_width=True):
            with st.spinner("Generating comprehensive impact src.reporting.report..."):
                report = generate_full_report(user_id, period_weeks=period)
                st.session_state["generated_report"] = report

    if "generated_report" in st.session_state:
        report = st.session_state["generated_report"]

        st.divider()
        st.markdown(f"#### 📊 Report Summary — {src.reporting.report.period_weeks}-Week Period")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌍 CO₂ Saved", f"{src.reporting.report.total_co2_saved_kg:.1f} kg")
        c2.metric("⭐ XP Earned", f"{src.reporting.report.total_xp}")
        c3.metric("✅ Pledges", f"{src.reporting.report.total_pledges_completed}")
        c4.metric("📅 Checkins", f"{src.reporting.report.total_checkins}")

        st.metric("📊 Avg Weekly CO₂", f"{src.reporting.report.avg_weekly_co2_kg:.2f} kg")

        # Best/worst week
        if src.reporting.report.best_week:
            st.markdown(f"**Best week:** {src.reporting.report.best_week.week_start} — {src.reporting.report.best_week.co2_saved_kg:.1f} kg CO₂")
        if src.reporting.report.worst_week:
            st.markdown(f"**Worst week:** {src.reporting.report.worst_week.week_start} — {src.reporting.report.worst_week.co2_saved_kg:.1f} kg CO₂")

        # Weekly data table
        if src.reporting.report.weekly_data:
            with st.expander("📅 Weekly Breakdown"):
                active = [w for w in src.reporting.report.weekly_data if w.pledges_enrolled > 0]
                if active:
                    df = pd.DataFrame([{
                        "Week": w.week_start,
                        "Enrolled": w.pledges_enrolled,
                        "Completed": w.pledges_completed,
                        "Checkins": w.checkins,
                        "CO₂ (kg)": w.co2_saved_kg,
                        "XP": w.xp_earned,
                        "Categories": ", ".join(w.categories_touched) if w.categories_touched else "—",
                    } for w in active])
                    st.dataframe(df, use_container_width=True, hide_index=True)

        # Milestones from report
        if src.reporting.report.milestones:
            achieved = [m for m in src.reporting.report.milestones if m.achieved]
            st.markdown(f"#### 🏆 Milestones ({len(achieved)}/{len(src.reporting.report.milestones)})")

        # Download
        st.divider()
        json_data = export_report_json(user_id, period_weeks=period)
        st.download_button(
            label="📥 Download Report as JSON",
            data=json_data,
            file_name=f"pledge_impact_report_{period}w.json",
            mime="application/json",
            use_container_width=True,
        )

    # Report history
    history = get_report_history(user_id, limit=5)
    if history:
        st.divider()
        st.markdown("#### 📚 Report History")
        for h in history:
            st.markdown(
                f"- **{h.get('generated_at', '')[:10]}** — "
                f"{h.get('period_weeks', 0)} weeks · "
                f"{h.get('total_co2_saved_kg', 0):.1f} kg CO₂ · "
                f"{h.get('total_xp', 0)} XP"
            )
