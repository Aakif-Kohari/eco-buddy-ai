"""Streamlit dashboard for sustainability behavior patterns and correlations."""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import streamlit as st

from behavior_pattern_analyzer import analyze_habit_data, serialize_report, summarize_report
from habit_tracker import load_user_habits_db


st.set_page_config(page_title="Behavior Pattern Analyzer", page_icon="🔎", layout="wide")
st.title("🔎 Sustainability Behavior Pattern & Habit Correlation Analyzer")
st.caption("Explore recurring habit patterns and associations. Associations are not causal claims.")


def _user_id() -> int:
    value = st.session_state.get("user_id", st.session_state.get("user", 1))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 1


def _load_data():
    try:
        return load_user_habits_db(_user_id()) or {"history": {}}
    except Exception as exc:
        st.warning(f"Habit history could not be loaded: {exc}")
        return {"history": {}}


data = _load_data()
with st.sidebar:
    st.header("Analysis settings")
    days = st.slider("History window (days)", 7, 365, 90, 1)
    st.info("The analyzer reads existing habit history. It does not modify assessments or habit records.")

report = analyze_habit_data(data, days=days)
summary = summarize_report(report)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Habits tracked", summary["habits_tracked"])
c2.metric("Observations", summary["observations"])
c3.metric("Avg completion", f"{summary['average_completion_rate']:.1f}%")
c4.metric("Findings", summary["findings"])

if not report.habit_stats:
    st.warning("No usable habit history was found for the selected period.")
    st.stop()

st.subheader("Habit completion")
st.dataframe(pd.DataFrame([s.__dict__ for s in report.habit_stats]), use_container_width=True, hide_index=True)

st.subheader("Habit associations")
if report.correlations:
    corr_df = pd.DataFrame([c.__dict__ for c in report.correlations])
    corr_df["coefficient"] = corr_df["coefficient"].round(3)
    st.dataframe(corr_df, use_container_width=True, hide_index=True)
else:
    st.info("No pair has enough variation to calculate a correlation in this window.")

st.subheader("Pattern findings")
for finding in report.findings:
    with st.expander(f"{finding.title} · {finding.confidence} confidence"):
        st.write(finding.description)
        if finding.evidence:
            st.json(finding.evidence)

st.subheader("Weekday completion")
weekday_rows = []
for habit, rates in report.weekday_rates.items():
    for weekday, rate in rates.items():
        weekday_rows.append({"habit": habit, "weekday": weekday, "completion_rate": rate})
if weekday_rows:
    weekday_df = pd.DataFrame(weekday_rows)
    st.bar_chart(weekday_df.pivot(index="weekday", columns="habit", values="completion_rate"))

st.subheader("Co-occurrence")
co_rows = []
for left, row in report.co_occurrence.items():
    for right, count in row.items():
        if left < right and count:
            co_rows.append({"habit": left, "paired_habit": right, "days_together": count})
if co_rows:
    st.dataframe(pd.DataFrame(co_rows).sort_values("days_together", ascending=False), use_container_width=True, hide_index=True)
else:
    st.info("No same-day co-occurrence pairs were found.")

st.subheader("Limitations")
for limitation in report.limitations:
    st.markdown(f"- {limitation}")

st.download_button(
    "Download analysis JSON",
    data=serialize_report(report, pretty=True),
    file_name=f"sustainability-behavior-analysis-{date.today().isoformat()}.json",
    mime="application/json",
)
