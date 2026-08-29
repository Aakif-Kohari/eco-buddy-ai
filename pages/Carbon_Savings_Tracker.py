"""
Carbon Savings Tracker Page
===========================
Track your cumulative carbon savings, streaks, milestones, and
real-world equivalents over time.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from src.utils.carbon_savings_tracker import (
    generate_savings_report, compute_savings_history, compute_streak,
    check_milestones, compute_savings_equivalents, compute_monthly_savings_rate,
    MILESTONES, STREAK_THRESHOLDS,
)


def render_streak_gauge(streak: dict) -> None:
    """Render a gauge showing current streak."""
    current = streak.get("current_streak_months", 0)
    longest = streak.get("longest_streak_months", 0)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current,
        delta={"reference": longest, "increasing": {"color": "#22c55e"}},
        title={"text": "Current Streak (months)", "font": {"size": 16}},
        number={"suffix": " mo"},
        gauge={"axis": {"range": [0, max(longest + 1, 12)]},
               "bar": {"color": "#22c55e"},
               "steps": [
                   {"range": [0, STREAK_THRESHOLDS["bronze"] // 30], "color": "#fbbf24"},
                   {"range": [STREAK_THRESHOLDS["bronze"] // 30, STREAK_THRESHOLDS["silver"] // 30], "color": "#a3a3a3"},
                   {"range": [STREAK_THRESHOLDS["silver"] // 30, STREAK_THRESHOLDS["gold"] // 30], "color": "#facc15"},
               ]},
    ))
    fig.update_layout(height=250, margin=dict(t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)


def render_savings_line(records: list[dict]) -> None:
    """Line chart of cumulative savings over time."""
    dates = [r["date"] for r in records]
    cumulative = [r["cumulative_savings_kg"] for r in records]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=cumulative, mode="lines+markers",
        line=dict(color="#22c55e", width=3), fill="tozeroy",
        fillcolor="rgba(34,197,94,0.1)", name="Cumulative Savings",
    ))
    fig.update_layout(
        height=300, margin=dict(t=30, b=30),
        xaxis_title="Date", yaxis_title="Cumulative Savings (kg CO₂)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_monthly_bar(records: list[dict]) -> None:
    """Bar chart of per-month savings."""
    dates = [r["date"] for r in records]
    savings = [r["savings_kg"] for r in records]
    colors = ["#22c55e" if s > 0 else "#ef4444" for s in savings]

    fig = go.Figure(go.Bar(
        x=dates, y=savings, marker_color=colors,
        text=[f"{s:+.0f}" for s in savings], textposition="outside",
    ))
    fig.update_layout(
        height=280, margin=dict(t=20, b=30),
        xaxis_title="Date", yaxis_title="Savings (kg CO₂)",
        shapes=[dict(type="line", x0=dates[0], x1=dates[-1], y0=0, y1=0,
                     line=dict(color="white", width=1, dash="dash"))],
    )
    st.plotly_chart(fig, use_container_width=True)


def render_milestone_progress(cumulative: float) -> None:
    """Show milestone progress cards."""
    next_ms = None
    achieved = []
    for m in MILESTONES:
        if cumulative >= m["kg_threshold"]:
            achieved.append(m)
        elif next_ms is None:
            next_ms = m

    if achieved:
        st.markdown("**🏅 Achieved Milestones**")
        cols = st.columns(min(len(achieved), 3))
        for i, m in enumerate(achieved):
            with cols[i % len(cols)]:
                st.success(f"{m['badge']}\n\n{m['message']}")

    if next_ms:
        remaining = next_ms["kg_threshold"] - cumulative
        progress = min(cumulative / next_ms["kg_threshold"], 1.0)
        st.markdown(f"**Next:** {next_ms['badge']} ({remaining:.0f} kg to go)")
        st.progress(progress)
    else:
        st.success("🎉 You've achieved all milestones!")


def render_equivalents(equivalents: list[dict]) -> None:
    """Render real-world equivalents."""
    cols = st.columns(len(equivalents))
    for i, eq in enumerate(equivalents):
        with cols[i]:
            st.metric(f"{eq['icon']} {eq['label']}", f"{eq['value']:,.1f} {eq['unit']}")


def render_benchmarking_chart(report: dict) -> None:
    """Compare total savings against common benchmarks."""
    total = report.get("total_savings_kg", 0)
    benchmarks = [
        ("Your Savings", total, "#22c55e"),
        ("Avg. Annual US Footprint", 14900.0, "#6b7280"),
        ("2030 Target", 2500.0, "#3b82f6"),
        ("2050 Target", 1500.0, "#15803d"),
    ]

    fig = go.Figure(go.Bar(
        x=[b[0] for b in benchmarks],
        y=[b[1] for b in benchmarks],
        marker_color=[b[2] for b in benchmarks],
        text=[f"{b[1]:,.0f} kg" for b in benchmarks],
        textposition="auto",
    ))
    fig.update_layout(height=250, margin=dict(t=20, b=20), yaxis_title="kg CO₂")
    st.plotly_chart(fig, use_container_width=True)


def render_carbon_savings_tracker():
    """Main page render function."""
    st.markdown(
        "<div class='section-header'>📈 Carbon Savings Tracker</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Track your cumulative carbon savings, celebrate streaks, "
        "and see your real-world environmental impact."
    )

    # ── Input Section ───────────────────────────────────────────────────
    st.subheader("🔧 Assessment History")
    st.markdown(
        "Enter your past monthly assessments to compute savings. "
        "Each entry should include your monthly footprint (kg CO₂)."
    )

    num_entries = st.number_input(
        "Number of monthly assessments to enter",
        min_value=2, max_value=36, value=6, step=1,
    )

    baseline_kg = st.number_input(
        "Baseline Footprint (kg CO₂/year) — leave 0 for auto-detect",
        min_value=0.0, max_value=100000.0, value=0.0, step=100.0,
        help="The baseline is the footprint you're comparing savings against. "
             "If set to 0, the first assessment's footprint is used."
    )

    assessments = []
    cols = st.columns(2)
    for i in range(int(num_entries)):
        col = cols[i % 2]
        with col:
            month_dt = datetime.now() - timedelta(days=30 * (int(num_entries) - 1 - i))
            default_date = month_dt.strftime("%Y-%m-%d")
            default_fp = max(1000, 4500 - i * 150 + (hash(str(i)) % 300 - 150))

            c1, c2 = st.columns(2)
            with c1:
                date = st.text_input(f"Date {i+1}", value=default_date, key=f"date_{i}")
            with c2:
                fp = st.number_input(
                    f"Footprint {i+1} (kg)", min_value=0.0,
                    value=float(default_fp), step=50.0, key=f"fp_{i}",
                )
            assessments.append({"date": date, "footprint": fp})

    analyze = st.button("📊 Generate Savings Report", use_container_width=True)

    if analyze:
        bl = baseline_kg if baseline_kg > 0 else None
        report = generate_savings_report(assessments, baseline_kg=bl)

        if "summary" in report:
            st.warning(report["summary"])
            return

        # ── Key Metrics ──────────────────────────────────────────────
        st.divider()
        st.subheader("📊 Key Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Savings", f"{report['total_savings_kg']:,.0f} kg",
                  delta=f"{report['savings_pct']:.1f}% vs baseline")
        m2.metric("Current Footprint", f"{report['current_footprint_kg']:,.0f} kg")
        m3.metric("Baseline", f"{report['baseline_kg']:,.0f} kg")
        m4.metric("Months Tracked", str(report['monthly_rate']['total_months']))

        # ── Cumulative Savings Chart ─────────────────────────────────
        st.divider()
        st.subheader("📈 Cumulative Savings Over Time")
        render_savings_line(report["records"])

        # ── Monthly Savings Chart ────────────────────────────────────
        st.subheader("📊 Monthly Savings Breakdown")
        render_monthly_bar(report["records"])

        # ── Streak ───────────────────────────────────────────────────
        st.divider()
        st.subheader("🔥 Savings Streak")
        streak = report["streak"]
        sc1, sc2 = st.columns([1, 1])
        with sc1:
            render_streak_gauge(streak)
        with sc2:
            tier_emoji = {
                "none": "⚪", "bronze": "🥉", "silver": "🥈",
                "gold": "🥇", "platinum": "💎", "diamond": "👑",
            }
            st.markdown(
                f"### {tier_emoji.get(streak['streak_tier'], '⚪')} "
                f"{streak['streak_tier'].title()} Streak"
            )
            st.markdown(
                f"**Current:** {streak['current_streak_months']} months "
                f"({streak['current_streak_days']} days)"
            )
            st.markdown(
                f"**Longest:** {streak['longest_streak_months']} months "
                f"({streak['longest_streak_days']} days)"
            )
            st.caption(
                "Streak tiers: Bronze (7d) → Silver (30d) → Gold (90d) → Platinum (180d) → Diamond (365d)"
            )

        # ── Milestones ───────────────────────────────────────────────
        st.divider()
        st.subheader("🏅 Milestones")
        render_milestone_progress(report["total_savings_kg"])

        # ── Real-World Equivalents ───────────────────────────────────
        st.divider()
        st.subheader("🌍 Your Impact in Real-World Terms")
        render_equivalents(report["equivalents"])

        # ── Savings Rate ─────────────────────────────────────────────
        st.divider()
        st.subheader("📉 Savings Rate Analysis")
        rate = report["monthly_rate"]
        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Avg Monthly Savings", f"{rate['avg_monthly_savings_kg']:,.1f} kg")
        rc2.metric("Projected (12mo)", f"{rate['projection_12m_kg']:,.0f} kg")
        trend_icon = {"improving": "📈", "declining": "📉", "stable": "➡️"}.get(rate["trend"], "❓")
        rc3.metric("Trend", f"{trend_icon} {rate['trend'].title()}")
        st.caption(
            f"Positive months: {rate['positive_months']}/{rate['total_months']} — "
            f"Keep pushing to improve your streak!"
        )

        # ── Benchmark Comparison ─────────────────────────────────────
        st.divider()
        st.subheader("📋 Benchmark Comparison")
        render_benchmarking_chart(report)

        # ── Recommendations ──────────────────────────────────────────
        st.divider()
        st.subheader("💡 What's Next?")
        tips = []
        if rate["trend"] == "declining":
            tips.append("📉 Your savings rate is declining — review recent changes to reverse the trend.")
        if streak["current_streak_months"] < 3:
            tips.append("🔥 Build momentum — aim for a 3-month streak to reach Bronze tier!")
        if report["total_savings_kg"] < 500:
            tips.append("🌱 Focus on one high-impact area (transport or electricity) for faster gains.")
        nm = report.get("next_milestone")
        if nm:
            tips.append(f"🎯 Next milestone: {nm['badge']} — just {nm['remaining_kg']:.0f} kg away!")
        tips.extend([
            "📊 Use the **Regional Benchmarking** page to compare against peers.",
            "🎯 Set a **Reduction Goal** to formalize your savings target.",
            "🔄 Enter new assessments monthly to maintain your streak.",
        ])
        for tip in tips:
            st.markdown(f"• {tip}")
    else:
        st.info("👆 Enter your monthly assessments and click **Generate Savings Report** to begin tracking.")


if __name__ == "__main__":
    st.set_page_config(page_title="Carbon Savings Tracker — EcoBuddy AI", page_icon="📈", layout="wide")
    render_carbon_savings_tracker()
else:
    render_carbon_savings_tracker()
