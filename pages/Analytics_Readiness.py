"""Streamlit UI for Sustainability Analytics Readiness and Evidence Confidence."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from src.utils.analytics_readiness import (
    DEFAULT_REQUIREMENTS, RELIABLE, LIMITED, INSUFFICIENT,
    build_readiness_report, category_matrix, confidence_label,
    explain_confidence, export_report, persist_report, readiness_matrix,
    recommendations_for_report,
)

st.set_page_config(page_title="Analytics Readiness", page_icon="📊", layout="wide")
st.title("📊 Sustainability Analytics Readiness")
st.caption(
    "Evaluate whether available sustainability history is sufficient for "
    "trends, comparisons, forecasting, recommendations, and benchmarking."
)

st.info(
    "This page is a read-only evidence assessment. It does not modify or "
    "recalculate the underlying sustainability history."
)

with st.expander("How confidence is determined"):
    st.markdown(
        """
        The engine evaluates **record count, distinct dates, historical span,
        completeness, validity, consistency, and recency**. Each analytics
        capability has its own evidence threshold.

        - **Reliable** — evidence meets the configured requirements.
        - **Limited** — analysis may be useful but has material limitations.
        - **Insufficient evidence** — the available history is not adequate
          for a defensible result.
        """
    )

st.subheader("Evidence input")
input_mode = st.radio(
    "Choose evidence source",
    ["Paste JSON", "Use a local JSON file"],
    horizontal=True,
)

payload = []
if input_mode == "Paste JSON":
    raw = st.text_area(
        "Assessment/history JSON",
        value='[\n  {"id": 1, "date": "2026-01-01", "category": "Energy", "value": 1200, "unit": "kg CO2e"}\n]',
        height=220,
    )
    if raw.strip():
        try:
            parsed = json.loads(raw)
            payload = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
else:
    uploaded = st.file_uploader("Upload JSON evidence", type=["json"])
    if uploaded:
        try:
            parsed = json.load(uploaded)
            payload = parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            st.error(f"Unable to read JSON: {exc}")

with st.expander("Advanced thresholds"):
    custom = {}
    for analysis, defaults in DEFAULT_REQUIREMENTS.items():
        st.markdown(f"**{analysis.title()}**")
        c1, c2, c3 = st.columns(3)
        min_records = c1.number_input(
            f"{analysis} minimum records", min_value=0, value=int(defaults["min_records"]), step=1
        )
        min_span = c2.number_input(
            f"{analysis} minimum span (days)", min_value=0, value=int(defaults["min_span_days"]), step=1
        )
        min_quality = c3.slider(
            f"{analysis} minimum quality", 0.0, 1.0, float(defaults["min_quality"]), 0.05
        )
        custom[analysis] = {
            "min_records": min_records,
            "min_span_days": min_span,
            "min_quality": min_quality,
        }

user_id = st.text_input("Optional user/profile ID filter", value="")
if st.button("Analyze evidence", type="primary", use_container_width=True):
    if not payload:
        st.warning("Provide at least one evidence record.")
        st.stop()
    st.session_state["readiness_report"] = build_readiness_report(
        payload, user_id=user_id or None, requirements=custom
    )

report = st.session_state.get("readiness_report")
if report:
    label = confidence_label(src.reporting.report.confidence)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall status", src.reporting.report.status.replace("_", " ").title())
    c2.metric("Confidence", f"{src.reporting.report.confidence:.0%}", label)
    c3.metric("Evidence records", src.reporting.report.summary["record_count"])
    c4.metric("History span", f'{src.reporting.report.summary["history_span_days"]} days')

    if src.reporting.report.status == RELIABLE:
        st.success("The evidence base is broadly ready for analytics.")
    elif src.reporting.report.status == LIMITED:
        st.warning("Analytics are possible, but the evidence has limitations.")
    else:
        st.error("The available evidence is insufficient for reliable analytics.")

    st.subheader("Analytics readiness")
    matrix = pd.DataFrame(readiness_matrix(report))
    if not matrix.empty:
        matrix["status"] = matrix["status"].str.replace("_", " ").str.title()
        matrix["confidence"] = matrix["confidence"].map(lambda x: f"{x:.0%}")
        matrix["quality"] = matrix["quality"].map(lambda x: f"{x:.0%}")
        st.dataframe(matrix, use_container_width=True, hide_index=True)

    st.subheader("Category evidence")
    categories = pd.DataFrame(category_matrix(report))
    if not categories.empty:
        categories["status"] = categories["status"].str.replace("_", " ").str.title()
        categories["confidence"] = categories["confidence"].map(lambda x: f"{x:.0%}")
        categories["quality"] = categories["quality"].map(lambda x: f"{x:.0%}")
        st.dataframe(categories, use_container_width=True, hide_index=True)

    st.subheader("Evidence issues")
    if src.reporting.report.issues:
        issue_df = pd.DataFrame([x.to_dict() for x in src.reporting.report.issues])
        st.dataframe(issue_df, use_container_width=True, hide_index=True)
    else:
        st.success("No evidence-quality issues were detected.")

    st.subheader("What should improve next?")
    recommendations = recommendations_for_report(report)
    if recommendations:
        for recommendation in recommendations:
            st.markdown(f"- {recommendation}")
    else:
        st.success("No additional evidence improvements are currently required.")

    with st.expander("Confidence explanation"):
        explanation = explain_confidence(report)
        st.json(explanation)

    st.download_button(
        "Download readiness report",
        data=export_report(report),
        file_name="sustainability_analytics_readiness.json",
        mime="application/json",
    )

    with st.expander("Optional SQLite snapshot"):
        st.caption("This stores only the generated validation report, not source assessments.")
        db_path = st.text_input("SQLite database path", value="ecobuddy.db")
        if st.button("Persist readiness snapshot"):
            try:
                conn = sqlite3.connect(str(Path(db_path).expanduser()))
                report_id = persist_report(report, conn)
                conn.close()
                st.success(f"Saved readiness snapshot #{report_id}.")
            except sqlite3.Error as exc:
                st.error(f"SQLite error: {exc}")
