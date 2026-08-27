"""Streamlit page for the Sustainability Goal Progress Analyzer."""
from __future__ import annotations

import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.core.database import get_active_goal, get_assessments
from src.utils.goal_pathway import (
    STATUS_ACHIEVED,
    STATUS_INSUFFICIENT_DATA,
    analyze_goal_pathway,
    best_improvement,
    build_chart_rows,
    human_status_message,
    largest_regression,
    serialize_pathway,
    target_date_at_current_pace,
)


def _user_id() -> int | None:
    value = st.session_state.get("user_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _load_goal(user_id: int):
    return get_active_goal(user_id)


def _goal_from_row(row, user_id: int) -> dict:
    if isinstance(row, dict):
        return {
            "id": row.get("id"),
            "user_id": row.get("user_id", user_id),
            "baseline_kg": row.get("baseline_kg"),
            "target_kg": row.get("target_kg"),
            "start_date": row.get("start_date"),
            "target_date": row.get("target_date"),
            "status": row.get("status", "active"),
        }
    return {
        "id": row["id"],
        "user_id": user_id,
        "baseline_kg": row["baseline_kg"],
        "target_kg": row["target_kg"],
        "start_date": row["start_date"],
        "target_date": row["target_date"],
        "status": row["status"],
    }


def _render_status(analysis):
    status = analysis.status
    st.markdown(
        f"<div style='padding:1rem;border-radius:10px;border-left:6px solid "
        f"#4caf50;background:rgba(128,128,128,.08);margin-bottom:1rem;'>"
        f"<strong>{status.label}</strong><br>{human_status_message(analysis)}</div>",
        unsafe_allow_html=True,
    )


def _render_metrics(analysis):
    p = analysis.progress
    a, b, c, d = st.columns(4)
    a.metric("Current", f"{p['current_kg']:,.0f} kg")
    b.metric("Target", f"{p['target_kg']:,.0f} kg")
    c.metric("Progress", f"{p['percent_complete']:.0f}%")
    d.metric("Days left", f"{p['days_remaining']:,}")
    st.progress(min(1.0, max(0.0, p["percent_complete"] / 100)))


def _render_pathway_chart(analysis):
    st.subheader("Pathway vs. actual footprint")
    rows = build_chart_rows(analysis)
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=[row["date"] for row in rows],
        y=[row["ideal_kg"] for row in rows],
        mode="lines",
        name="Ideal pathway",
        line=dict(width=3, dash="dash"),
    ))
    actual = [row for row in rows if row["actual_kg"] is not None]
    if actual:
        figure.add_trace(go.Scatter(
            x=[row["date"] for row in actual],
            y=[row["actual_kg"] for row in actual],
            mode="lines+markers",
            name="Your footprint",
            line=dict(width=3),
        ))
    figure.add_hline(y=analysis.target_kg, line_dash="dot", annotation_text="Target")
    figure.update_layout(
        height=430,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Date",
        yaxis_title="kg CO2e / year",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    st.plotly_chart(figure, use_container_width=True)


def _render_pace(analysis):
    st.subheader("Reduction pace")
    p = analysis.progress
    left, right = st.columns(2)
    left.metric("Observed pace", f"{p['observed_pace_kg_per_month']:,.1f} kg/month")
    right.metric("Needed from now", f"{p['pace_needed_from_now_kg_per_month']:,.1f} kg/month")
    st.caption(
        "Observed pace is calculated from the trend across usable assessment history; "
        "a single assessment cannot establish a pace."
    )

    projection = analysis.projection
    if projection.projected_target_date:
        if projection.projected_target_date <= analysis.target_date:
            st.success(
                f"At the observed pace, the target is projected for "
                f"{projection.projected_target_date.isoformat()}."
            )
        else:
            st.warning(
                f"At the observed pace, the target is projected for "
                f"{projection.projected_target_date.isoformat()}, after the committed target date."
            )
    else:
        st.info("A target date cannot be projected until a positive reduction pace is established.")


def _render_milestones(analysis):
    st.subheader("Reduction milestones")
    rows = []
    for milestone in analysis.milestones:
        rows.append({
            "Milestone": f"{milestone.percent}% reduction",
            "Target (kg)": milestone.target_kg,
            "Target date": milestone.target_date,
            "Status": "Completed" if milestone.completed else "Upcoming",
            "Completed date": milestone.completed_date or "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_categories(analysis):
    st.subheader("Category progress")
    if not analysis.category_progress:
        st.info(
            "Category-level contributions are not available in the assessment records "
            "provided to the analyzer. No category savings are invented."
        )
        return
    rows = [
        {
            "Category": item.category,
            "Baseline (kg)": item.baseline_kg,
            "Current (kg)": item.current_kg,
            "Change (kg)": item.absolute_change_kg,
            "Change (%)": item.percentage_change,
            "Direction": item.direction,
        }
        for item in analysis.category_progress
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    improved = best_improvement(analysis.category_progress)
    regression = largest_regression(analysis.category_progress)
    if improved:
        st.success(f"Largest measurable improvement: {improved.category} ({improved.absolute_change_kg:,.0f} kg).")
    if regression:
        st.warning(f"Largest measurable regression: {regression.category} (+{regression.absolute_change_kg:,.0f} kg).")


def _render_projection(analysis):
    st.subheader("Target-date what-if")
    projection = analysis.projection
    if projection.projected_target_date:
        delta_days = (projection.projected_target_date - analysis.target_date).days
        if delta_days <= 0:
            st.success(f"Current pace reaches the target about {abs(delta_days):,} days early.")
        else:
            st.warning(f"Current pace reaches the target about {delta_days:,} days late.")
    else:
        st.info("There is not enough positive trend data to project a target date.")

    result = target_date_at_current_pace(
        {
            "id": analysis.goal_id,
            "user_id": analysis.user_id,
            "baseline_kg": analysis.baseline_kg,
            "target_kg": analysis.target_kg,
            "start_date": analysis.start_date,
            "target_date": analysis.target_date,
        },
        [snapshot.to_dict() for snapshot in analysis.snapshots],
        analysis.analyzed_on,
    )
    # The projection above is already based on the complete assessment history.
    # Keep this section deliberately informational and never write the result back.
    if result["available"]:
        st.caption(f"Projected target date: {result['projected_date'].isoformat()}")


def main():
    user_id = _user_id()
    if user_id is None:
        st.warning("Please log in from the main application page.")
        return

    st.title("🎯 Sustainability Goal Pathway")
    st.write(
        "Understand how quickly you are reducing your footprint, where you should be "
        "on the pathway today, and whether your current trend is sufficient to reach the target."
    )

    goal_row = _load_goal(user_id)
    if not goal_row:
        st.info("No active reduction goal is available. Set a goal from the Reduction Goals page first.")
        return

    assessments = get_assessments(user_id)
    goal = _goal_from_row(goal_row, user_id)
    analysis = analyze_goal_pathway(goal, assessments)

    _render_status(analysis)
    _render_metrics(analysis)

    if analysis.status.code == STATUS_INSUFFICIENT_DATA:
        st.info("Your goal is valid, but at least two dated assessments are needed to establish a reduction pace.")

    _render_pathway_chart(analysis)
    _render_pace(analysis)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Projected final footprint", f"{analysis.projection.projected_final_kg:,.0f} kg")
    with col2:
        st.metric("Projected shortfall", f"{analysis.projection.projected_shortfall_kg:,.0f} kg")

    _render_milestones(analysis)
    _render_categories(analysis)
    _render_projection(analysis)

    if analysis.warnings:
        with st.expander("⚠️ Pathway notes"):
            for warning in analysis.warnings:
                st.write(f"- {warning}")

    with st.expander("Assessment snapshots"):
        if analysis.snapshots:
            st.dataframe(
                pd.DataFrame([snapshot.to_dict() for snapshot in analysis.snapshots]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No assessment snapshots are available for this goal.")

    st.download_button(
        "Export pathway JSON",
        data=serialize_pathway(analysis),
        file_name=f"goal-pathway-{analysis.goal_id or 'current'}.json",
        mime="application/json",
        use_container_width=True,
    )


main()
