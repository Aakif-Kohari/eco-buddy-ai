"""Streamlit dashboard for Personal Sustainability Benchmark & Trend Analyzer."""
from __future__ import annotations

from datetime import date, timedelta
import json

import pandas as pd
import streamlit as st

from src.core.database import get_assessments
from src.core.session_state_utils import ensure_session_state
from styles.theme import apply_theme
from src.utils.sustainability_trends import (
    DEFAULT_MOVING_AVERAGE_WINDOW,
    available_periods,
    benchmark_label,
    build_trend_summary,
    calculate_consistency_score,
    calculate_period_over_period,
    describe_trend,
    filter_by_period,
    normalize_assessments,
    serialize_summary,
)


user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()
ensure_session_state(
    {
        "sustainability_trends_period": "All time",
        "sustainability_trends_window": DEFAULT_MOVING_AVERAGE_WINDOW,
    }
)

st.title("📈 Personal Sustainability Benchmark & Trends")
st.markdown(
    "Understand how your environmental footprint is changing over time "
    "using your own assessment history."
)

raw_assessments = get_assessments(user_id)
if not raw_assessments:
    st.info(
        "You haven't completed any assessments yet. Complete an assessment "
        "to start building your personal sustainability benchmark."
    )
    st.stop()

try:
    assessments = normalize_assessments(raw_assessments)
except Exception as exc:
    st.error(f"Unable to analyze assessment history: {exc}")
    st.stop()

if not assessments:
    st.info("No valid assessment history is available for analysis.")
    st.stop()

with st.sidebar:
    st.header("Trend Settings")
    period = st.selectbox(
        "Analysis period",
        options=list(available_periods()),
        index=list(available_periods()).index(st.session_state.sustainability_trends_period),
        key="sustainability_trends_period",
    )
    window = st.slider(
        "Moving-average window",
        min_value=2,
        max_value=min(12, max(2, len(assessments))),
        value=min(st.session_state.sustainability_trends_window, max(2, len(assessments))),
        key="sustainability_trends_window",
        help="Number of consecutive assessments used for the moving average.",
    )

try:
    summary = build_trend_summary(
        assessments,
        period=period,
        moving_average_window=window,
    )
except Exception as exc:
    st.error(f"Unable to calculate the trend summary: {exc}")
    st.stop()

benchmark = summary.benchmark
trend = summary.overall

c1, c2, c3, c4 = st.columns(4)
c1.metric("Current footprint", f"{benchmark.current_footprint:,.0f} kg CO₂e" if benchmark.current_footprint is not None else "—")
c2.metric("Historical average", f"{benchmark.historical_average:,.0f} kg CO₂e" if benchmark.historical_average is not None else "—")
c3.metric("Best result", f"{benchmark.best_footprint:,.0f} kg CO₂e" if benchmark.best_footprint is not None else "—")
c4.metric("Assessments", str(benchmark.assessment_count))

if trend.direction == "IMPROVING":
    st.success(describe_trend(trend))
elif trend.direction == "WORSENING":
    st.warning(describe_trend(trend))
elif trend.direction == "STABLE":
    st.info(describe_trend(trend))
else:
    st.info(describe_trend(trend))

st.caption(benchmark_label(benchmark))

st.subheader("Personal benchmark")
b1, b2, b3 = st.columns(3)
b1.metric(
    "Current vs average",
    f"{benchmark.current_vs_average:+.1f}%" if benchmark.current_vs_average is not None else "—",
)
b2.metric(
    "Current vs best",
    f"{benchmark.current_vs_best:+.1f}%" if benchmark.current_vs_best is not None else "—",
)
b3.metric(
    "Current percentile",
    f"{benchmark.current_percentile:.0f}%" if benchmark.current_percentile is not None else "—",
)

st.subheader("Footprint trend")
scoped = filter_by_period(assessments, period)
chart_rows = []
moving_values = list(summary.moving_average)
for index, assessment in enumerate(scoped):
    chart_rows.append(
        {
            "Date": assessment.date,
            "Footprint (kg CO₂e)": assessment.footprint,
            "Moving average": moving_values[index] if index < len(moving_values) else None,
        }
    )
chart_df = pd.DataFrame(chart_rows).set_index("Date")
st.line_chart(chart_df, use_container_width=True)

st.subheader("Assessment history")
history_df = pd.DataFrame(
    [
        {
            "Date": record.date.strftime("%Y-%m-%d %H:%M"),
            "Footprint (kg CO₂e)": round(record.footprint, 2),
            "Eco Score": record.eco_score,
            "Factor Version": record.factor_version or "Unavailable",
            "Assessment ID": record.id,
        }
        for record in scoped
    ]
)
st.dataframe(history_df, use_container_width=True, hide_index=True)

st.subheader("Best and worst performance")
best, worst = summary.best_period, summary.worst_period
left, right = st.columns(2)
with left:
    if best:
        st.success(
            f"Best: **{best.footprint:,.0f} kg CO₂e** on "
            f"{best.date.strftime('%Y-%m-%d')} (assessment #{best.id})."
        )
    else:
        st.info("Best result unavailable.")
with right:
    if worst:
        st.warning(
            f"Highest: **{worst.footprint:,.0f} kg CO₂e** on "
            f"{worst.date.strftime('%Y-%m-%d')} (assessment #{worst.id})."
        )
    else:
        st.info("Highest result unavailable.")

st.subheader("Change events")
if summary.significant_changes:
    event_df = pd.DataFrame(
        [
            {
                "Assessment": item.assessment_id,
                "Previous": item.previous_assessment_id,
                "Change (kg CO₂e)": round(item.absolute_change, 2),
                "Change (%)": round(item.percentage_change, 2) if item.percentage_change is not None else None,
                "Direction": item.direction,
                "Magnitude": item.magnitude,
            }
            for item in summary.significant_changes
        ]
    )
    st.dataframe(event_df, use_container_width=True, hide_index=True)
else:
    st.info("No changes exceeded the configured significant-change threshold.")

st.subheader("Period-over-period comparison")
comparison = calculate_period_over_period(assessments, days=30)
p1, p2, p3 = st.columns(3)
p1.metric("Previous 30-day average", f"{comparison.first_average:,.0f} kg" if comparison.first_average is not None else "—")
p2.metric("Current 30-day average", f"{comparison.second_average:,.0f} kg" if comparison.second_average is not None else "—")
p3.metric("Change", f"{comparison.percentage_change:+.1f}%" if comparison.percentage_change is not None else "—")

st.subheader("Category trends")
if summary.category_trends:
    category_df = pd.DataFrame(
        [
            {
                "Category": item.category,
                "Start": item.starting_value,
                "Current": item.ending_value,
                "Change": item.absolute_change,
                "Change (%)": item.percentage_change,
                "Direction": item.direction,
            }
            for item in summary.category_trends
        ]
    )
    st.dataframe(category_df, use_container_width=True, hide_index=True)
    if summary.most_improved_category:
        st.success(f"Most improved category: {summary.most_improved_category.category}")
    if summary.most_worsened_category:
        st.warning(f"Largest increase: {summary.most_worsened_category.category}")
else:
    st.info(
        "Category-level contribution data is not stored in the current assessment-history schema, "
        "so category trends are not fabricated."
    )

st.subheader("Consistency")
consistency = calculate_consistency_score(scoped)
if consistency is not None:
    st.progress(int(round(consistency)), text=f"Consistency score: {consistency:.0f}/100")
    st.caption(
        "This score describes how tightly your historical footprint values cluster around your own average; "
        "it is not a sustainability rating."
    )
else:
    st.info("Not enough data to calculate consistency.")

st.subheader("Export trend report")
report = {
    "analysis_period": period,
    "moving_average_window": window,
    "summary": json.loads(serialize_summary(summary)),
}
st.download_button(
    "Download JSON trend report",
    data=json.dumps(report, indent=2, sort_keys=True),
    file_name="sustainability_trend_report.json",
    mime="application/json",
)
