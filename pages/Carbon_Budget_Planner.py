"""
Carbon Budget Planner Page
==========================
Set per-category carbon budgets, track usage, and get alerts
when limits are approached or exceeded.
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

from src.utils.carbon_budget_planner import (
    generate_budget_report, get_budget_template, calculate_category_budgets,
    DEFAULT_BUDGET_TEMPLATES,
)


def render_budget_gauge(score: dict) -> None:
    """Gauge showing overall budget score."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score["score"],
        number={"suffix": "", "font": {"size": 36}},
        title={"text": f"Budget Score — Grade: {score['grade']}", "font": {"size": 16}},
        gauge={"axis": {"range": [0, 100]},
               "bar": {"color": "#22c55e" if score["score"] >= 75 else ("#f59e0b" if score["score"] >= 50 else "#ef4444")},
               "steps": [{"range": [0, 40], "color": "#fecaca"},
                         {"range": [40, 75], "color": "#fef3c7"},
                         {"range": [75, 100], "color": "#dcfce7"}]},
    ))
    fig.update_layout(height=280, margin=dict(t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)


def render_usage_bar_chart(evaluations: list[dict]) -> None:
    """Horizontal bar chart showing budget vs actual per category."""
    cats = [e["category"] for e in evaluations]
    budgets = [e["budget_kg"] for e in evaluations]
    actuals = [e["actual_kg"] for e in evaluations]
    colors = ["#ef4444" if a > b else "#22c55e" for a, b in zip(actuals, budgets)]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Budget", y=cats, x=budgets, orientation="h",
                         marker_color="#e5e7eb", text=[f"{b:.0f}" for b in budgets]))
    fig.add_trace(go.Bar(name="Actual", y=cats, x=actuals, orientation="h",
                         marker_color=colors, text=[f"{a:.0f}" for a in actuals]))
    fig.update_layout(barmode="overlay", height=280, margin=dict(t=20, b=20),
                      xaxis_title="kg CO₂/month", legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, use_container_width=True)


def render_projection_chart(projections: dict, budgets: dict) -> None:
    """Bar chart comparing current vs projected month-end usage."""
    cats = list(projections.keys())
    current = [projections[c]["current_kg"] for c in cats]
    projected = [projections[c]["projected_month_end_kg"] for c in cats]
    budget_vals = [budgets.get(c, 0) for c in cats]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Current", x=cats, y=current, marker_color="#3b82f6"))
    fig.add_trace(go.Bar(name="Projected (Month-End)", x=cats, y=projected,
                         marker_color="#f59e0b", marker_pattern_shape="//"))
    fig.add_trace(go.Scatter(name="Budget Limit", x=cats, y=budget_vals,
                             mode="lines+markers", line=dict(color="#ef4444", dash="dash", width=2)))
    fig.update_layout(barmode="group", height=300, margin=dict(t=30, b=30),
                      yaxis_title="kg CO₂", legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, use_container_width=True)


def render_donut_breakdown(actuals: dict) -> None:
    """Donut chart of current actual usage by category."""
    cats = list(actuals.keys())
    vals = list(actuals.values())
    colors = ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6"]

    fig = go.Figure(go.Pie(
        labels=cats, values=vals, hole=0.45,
        marker_colors=colors[:len(cats)],
        textinfo="label+percent",
    ))
    total = sum(vals)
    fig.update_layout(height=280, margin=dict(t=20, b=20),
                      annotations=[dict(text=f"{total:,.0f}<br>kg", x=0.5, y=0.5,
                                        font_size=16, showarrow=False)])
    st.plotly_chart(fig, use_container_width=True)


def render_alert_cards(alerts: list[dict]) -> None:
    """Render alert cards."""
    severity_styles = {
        "critical": ("#dc2626", "#fef2f2"),
        "high": ("#ea580c", "#fff7ed"),
        "medium": ("#ca8a04", "#fefce8"),
        "low": ("#2563eb", "#eff6ff"),
    }
    for alert in alerts:
        border_color, bg_color = severity_styles.get(alert["severity"], ("#6b7280", "#f9fafb"))
        st.markdown(
            f"<div style='padding:14px 18px; margin:10px 0; border-radius:12px; "
            f"border-left:5px solid {border_color}; background:{bg_color};'>"
            f"<strong>{alert['icon']} {alert['title']}</strong><br>"
            f"{alert['message']}<br>"
            f"<em style='color:#6b7280;'>💡 {alert['action']}</em>"
            f"</div>",
            unsafe_allow_html=True,
        )


def render_budget_planner():
    """Main page render function."""
    st.markdown(
        "<div class='section-header'>💰 Carbon Budget Planner</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Set monthly carbon budgets per category, track your usage in real time, "
        "and get alerts before you overshoot."
    )

    # ── Budget Template Selection ───────────────────────────────────────
    st.subheader("🎯 Choose Budget Template")
    template_name = st.selectbox(
        "Budget Level",
        list(DEFAULT_BUDGET_TEMPLATES.keys()),
        format_func=lambda k: DEFAULT_BUDGET_TEMPLATES[k]["label"],
        index=1,
    )
    template = get_budget_template(template_name)
    st.caption(template["description"])

    # ── Custom Budget Override ──────────────────────────────────────────
    use_custom = st.checkbox("✏️ Customize budget amounts", value=False)

    if use_custom:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            b_t = st.number_input("Transport (kg/mo)", value=template["Transport"], step=10.0, key="b_t")
        with c2:
            b_e = st.number_input("Electricity (kg/mo)", value=template["Electricity"], step=10.0, key="b_e")
        with c3:
            b_d = st.number_input("Diet (kg/mo)", value=template["Diet"], step=10.0, key="b_d")
        with c4:
            b_f = st.number_input("Flights (kg/mo)", value=template["Flights"], step=10.0, key="b_f")
        budgets = {"Transport": b_t, "Electricity": b_e, "Diet": b_d, "Flights": b_f}
    else:
        budgets = {
            "Transport": template["Transport"],
            "Electricity": template["Electricity"],
            "Diet": template["Diet"],
            "Flights": template["Flights"],
        }

    st.markdown(f"**Total Monthly Budget:** {sum(budgets.values()):,.0f} kg CO₂")

    # ── Current Usage Inputs ────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Current Month Usage")

    day_of_month = st.slider("Day of month", 1, 31, datetime.now().day)

    a1, a2, a3, a4 = st.columns(4)
    with a1:
        a_t = st.number_input("Transport Used (kg)", min_value=0.0, value=140.0, step=5.0, key="a_t")
    with a2:
        a_e = st.number_input("Electricity Used (kg)", min_value=0.0, value=110.0, step=5.0, key="a_e")
    with a3:
        a_d = st.number_input("Diet Used (kg)", min_value=0.0, value=65.0, step=5.0, key="a_d")
    with a4:
        a_f = st.number_input("Flights Used (kg)", min_value=0.0, value=0.0, step=5.0, key="a_f")
    actuals = {"Transport": a_t, "Electricity": a_e, "Diet": a_d, "Flights": a_f}

    if st.button("📊 Generate Budget Report", use_container_width=True):
        report = generate_budget_report(budgets, actuals, day_of_month, template_name=template_name)

        # ── Score Overview ────────────────────────────────────────────
        st.divider()
        st.subheader("🎯 Budget Score")
        sc1, sc2 = st.columns([1, 2])
        with sc1:
            render_budget_gauge(report["score"])
        with sc2:
            score = report["score"]
            st.markdown(f"### Grade: {score['grade']} ({score['score']:.0f}/100)")
            st.markdown(score["description"])
            totals = report["totals"]
            st.metric("Total Used", f"{totals['actual_kg']:,.0f} kg",
                      delta=f"{totals['remaining_kg']:+,.0f} kg remaining",
                      delta_color="inverse" if totals["remaining_kg"] < 0 else "normal")

        # ── Budget vs Actual ──────────────────────────────────────────
        st.divider()
        st.subheader("📊 Budget vs Actual")
        render_usage_bar_chart(report["evaluations"])

        # Category detail table
        st.markdown("| Category | Budget | Actual | Remaining | Usage | Status |")
        st.markdown("|----------|--------|--------|-----------|-------|--------|")
        for ev in report["evaluations"]:
            st.markdown(
                f"| {ev['category']} | {ev['budget_kg']:,.0f} kg | "
                f"{ev['actual_kg']:,.0f} kg | {ev['remaining_kg']:+,.0f} kg | "
                f"{ev['usage_percent']:.0f}% | {ev['alert_icon']} |"
            )

        # ── Projections ───────────────────────────────────────────────
        st.divider()
        st.subheader("🔮 Month-End Projection")
        render_projection_chart(report["projections"], budgets)
        st.caption(
            f"Based on day {day_of_month} usage rate, projected month-end totals are shown "
            f"against budget limits (red dashed line)."
        )

        # ── Usage Breakdown ───────────────────────────────────────────
        sc1, sc2 = st.columns(2)
        with sc1:
            st.subheader("🥧 Usage Breakdown")
            render_donut_breakdown(actuals)
        with sc2:
            st.subheader("📋 Template Comparison")
            for t_name, t_data in DEFAULT_BUDGET_TEMPLATES.items():
                total = sum(t_data[c] for c in ["Transport", "Electricity", "Diet", "Flights"])
                active = " ← active" if t_name == template_name else ""
                st.markdown(f"**{t_data['label']}**{active}")
                st.caption(f"  {total:,.0f} kg/month total")

        # ── Alerts ────────────────────────────────────────────────────
        if report["alerts"]:
            st.divider()
            st.subheader("⚠️ Alerts")
            render_alert_cards(report["alerts"])
        else:
            st.divider()
            st.success("✅ No alerts — all categories are within budget!")

        # ── Recommendations ───────────────────────────────────────────
        st.divider()
        st.subheader("💡 Recommendations")
        for rec in report["recommendations"]:
            st.markdown(f"• {rec}")

    else:
        st.info("👆 Configure your budget and usage, then click **Generate Budget Report**.")


if __name__ == "__main__":
    st.set_page_config(page_title="Carbon Budget Planner — EcoBuddy AI", page_icon="💰", layout="wide")
    render_budget_planner()
else:
    render_budget_planner()
