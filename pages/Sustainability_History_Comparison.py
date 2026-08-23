"""Streamlit UI for Sustainability History Comparison and Change Attribution."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from database import get_assessments_with_factors
from session_state_utils import ensure_session_state
from styles.theme import apply_theme
from sustainability_history_comparison import (
    build_history_timeline,
    compare_assessments,
    compare_selected_ids,
    export_comparison_csv,
    export_comparison_json,
    export_history_json,
    export_markdown_report,
    history_quality_flags,
    normalize_history,
    summarize_history,
    top_category_changes,
    trend_direction,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()
ensure_session_state({"history_compare_period": "monthly"})
st.title("🔎 Sustainability History Comparison")
st.caption("Compare two assessments and separate input/behaviour changes from emission-factor methodology changes.")

raw = get_assessments_with_factors(user_id)
history = normalize_history(raw)
if not history:
    st.info("No assessment history is available yet. Complete at least one carbon footprint assessment first.")
    st.stop()

summary = summarize_history(history)
flags = history_quality_flags(history)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Assessments", summary.count)
c2.metric("Current footprint", f"{history[-1].footprint:.1f} kg")
c3.metric("Footprint change", "—" if summary.footprint_change_kg is None else f"{summary.footprint_change_kg:+.1f} kg")
c4.metric("Trend", trend_direction(history).replace("_", " ").title())

if summary.warnings:
    for warning in summary.warnings:
        st.warning(warning)

if flags:
    st.caption("Data quality flags: " + ", ".join(flags))

st.subheader("Compare assessments")
labels = {
    str(item.id): f"{item.date.strftime('%Y-%m-%d %H:%M')} — {item.footprint:.1f} kg — #{item.id}"
    for item in history
}
options = [str(item.id) for item in history]

col1, col2 = st.columns(2)
with col1:
    before_id = st.selectbox("Earlier assessment", options, index=0, format_func=lambda value: labels[value])
with col2:
    after_index = len(options) - 1
    after_id = st.selectbox("Later assessment", options, index=after_index, format_func=lambda value: labels[value])

if before_id == after_id:
    st.info("Select two different assessments to compare.")
else:
    try:
        comparison = compare_selected_ids(history, before_id, after_id)
    except KeyError as exc:
        st.error(str(exc))
        st.stop()

    if comparison.methodology_warning:
        st.warning(comparison.methodology_warning)

    a, b, c = st.columns(3)
    a.metric("Footprint change", f"{comparison.footprint_change.absolute_change:+.1f} kg", f"{comparison.footprint_change.percent_change:+.1f}%" if comparison.footprint_change.percent_change is not None else None)
    b.metric("Behaviour/input effect", f"{comparison.attribution.behaviour_change_kg:+.1f} kg")
    c.metric("Factor/methodology effect", f"{comparison.attribution.factor_change_kg:+.1f} kg")

    st.subheader("What changed?")
    input_rows = [item.to_dict() for item in comparison.input_changes]
    st.dataframe(pd.DataFrame(input_rows), use_container_width=True, hide_index=True)

    st.subheader("Change attribution")
    attr_rows = [item.to_dict() for item in top_category_changes(comparison, 10)]
    if attr_rows:
        attr_df = pd.DataFrame(attr_rows).set_index("category")
        st.bar_chart(attr_df["change_kg"])
        st.dataframe(pd.DataFrame(attr_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Category attribution is unavailable for these records.")

    st.info("Attribution is a modelled decomposition of stored inputs. It is not a causal experiment or a guarantee of real-world savings.")
    if comparison.attribution.caveats:
        with st.expander("Methodology and caveats"):
            for caveat in comparison.attribution.caveats:
                st.write("• " + caveat)

    st.subheader("Export comparison")
    e1, e2, e3 = st.columns(3)
    e1.download_button("Download JSON", export_comparison_json(comparison), file_name="sustainability-comparison.json", mime="application/json")
    e2.download_button("Download CSV", export_comparison_csv(comparison), file_name="sustainability-comparison.csv", mime="text/csv")
    e3.download_button("Download report", export_markdown_report(comparison), file_name="sustainability-comparison.md", mime="text/markdown")

st.divider()
st.subheader("History timeline")
period = st.selectbox("Grouping", ["monthly", "quarterly", "yearly"], index=0)
timeline = build_history_timeline(history, period)
if timeline:
    timeline_df = pd.DataFrame([point.to_dict() for point in timeline])
    chart_df = timeline_df.set_index("label")[["average_footprint", "average_eco_score"]]
    st.line_chart(chart_df)
    st.dataframe(timeline_df, use_container_width=True, hide_index=True)

st.download_button(
    "Download full history analysis JSON",
    export_history_json(history, period),
    file_name="sustainability-history-analysis.json",
    mime="application/json",
)
