"""Interactive audit trail and calculation explainability page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.utils.assessment_explainability import (
    METHODOLOGY_CHANGED,
    SOURCE_UNAVAILABLE,
    build_assessment_audit,
    compare_audit_traces,
    serialize_audit,
)
from src.core.database import get_assessments_with_factors
from src.carbon.emissions import get_factor_version
from styles.theme import apply_theme


st.set_page_config(page_title="Assessment Audit", page_icon="🔎", layout="wide")
apply_theme()

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

st.title("🔎 Assessment Audit & Explainability")
st.caption("Inspect the inputs, emission factors, units, formulas, and historical methodology behind an assessment.")
st.info("Historical results are never silently recalculated with today's factors. If the recorded factor set is unavailable, the page reports that limitation instead of inventing metadata.")

rows = get_assessments_with_factors(int(user_id))
if not rows:
    st.info("No assessments are available for auditing yet. Complete an assessment first.")
    st.stop()

columns = ["id", "date", "transport", "created_at", "distance", "electricity", "diet", "flights", "footprint", "eco_score", "factor_version"]
assessments = [dict(zip(columns, row)) for row in rows]
labels = {
    item["id"]: f"#{item['id']} · {item['date']} · {item['footprint']:.2f} kg CO2e · {item.get('factor_version') or 'static-v1'}"
    for item in assessments
}

selected_id = st.selectbox("Assessment", options=[item["id"] for item in assessments], format_func=lambda value: labels[value])
selected = next(item for item in assessments if item["id"] == selected_id)

try:
    current_factor_version = get_factor_version("Global")
except Exception:
    current_factor_version = None

audit = build_assessment_audit(selected, current_factor_version=current_factor_version)

if audit.methodology_changed:
    st.warning(f"⚠️ {METHODOLOGY_CHANGED} Recorded: `{audit.factor_version}` · Current: `{current_factor_version}`")
if not audit.methodology_available:
    st.error(f"⚠️ Historical factor set `{audit.factor_version}` is unavailable. The original stored footprint is preserved and no replacement calculation is presented as historical truth.")
for note in audit.notes:
    if note not in (METHODOLOGY_CHANGED,):
        st.caption(f"ℹ️ {note}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Stored footprint", f"{audit.stored_footprint:.2f} kg" if audit.stored_footprint is not None else "Unavailable")
m2.metric("Reconstructed trace", f"{audit.trace.total_result:.2f} kg" if audit.methodology_available else "Unavailable")
m3.metric("Eco score", str(audit.stored_eco_score) if audit.stored_eco_score is not None else "Unavailable")
m4.metric("Factor version", audit.factor_version or "Unavailable")

st.subheader("📊 Category Contributions")
if audit.contributions:
    contribution_df = pd.DataFrame([
        {"Category": c.category, "kg CO2e": c.result, "% of trace": c.percentage, "Rank": c.rank}
        for c in audit.contributions
    ])
    st.bar_chart(contribution_df.set_index("Category")["kg CO2e"])
    st.dataframe(contribution_df, use_container_width=True, hide_index=True)
else:
    st.warning("Category contributions cannot be reconstructed because the historical methodology is unavailable.")

st.subheader("🧾 Inputs Used")
input_df = pd.DataFrame([
    {"Input": "Transport", "Value": audit.inputs.get("transport"), "Unit": "mode"},
    {"Input": "Distance", "Value": audit.inputs.get("distance"), "Unit": "km/day"},
    {"Input": "Electricity", "Value": audit.inputs.get("electricity"), "Unit": "kWh/month"},
    {"Input": "Diet", "Value": audit.inputs.get("diet"), "Unit": "profile"},
    {"Input": "Flights", "Value": audit.inputs.get("flights"), "Unit": "flights/year"},
])
st.dataframe(input_df, use_container_width=True, hide_index=True)

st.subheader("🧮 Calculation Trace")
if audit.trace.conversions:
    with st.expander("Unit conversions", expanded=False):
        conversion_df = pd.DataFrame([{
            "Step": c.name, "Input": c.input_value, "Input unit": c.input_unit,
            "Normalized": c.normalized_value, "Normalized unit": c.normalized_unit,
            "Multiplier": c.multiplier, "Calculation": c.calculation,
        } for c in audit.trace.conversions])
        st.dataframe(conversion_df, use_container_width=True, hide_index=True)

if audit.trace.steps:
    for index, step in enumerate(audit.trace.steps, 1):
        with st.expander(f"{index}. {step.category} — {step.result:.2f} kg CO2e", expanded=index == 1):
            st.write(f"**Input:** {step.input_value} {step.input_unit}")
            st.write(f"**Normalized:** {step.normalized_value} {step.normalized_unit}")
            st.write(f"**Factor:** {step.factor if step.factor is not None else SOURCE_UNAVAILABLE} {step.factor_unit}")
            st.write(f"**Calculation:** `{step.calculation}`")
            st.write(f"**Result:** {step.result:.2f} {step.result_unit}")
            st.write(f"**Source:** {step.source or SOURCE_UNAVAILABLE}")
            st.write(f"**Factor version:** `{step.factor_version or SOURCE_UNAVAILABLE}`")
else:
    st.warning("No reproducible calculation steps are available for this historical assessment.")

st.subheader("🔬 Factor Metadata")
metadata = audit.factor_metadata
st.json(metadata)

st.subheader("↔️ Previous vs Current")
previous_candidates = [item for item in assessments if item["id"] != selected_id]
if previous_candidates:
    previous_id = st.selectbox("Compare with", options=[item["id"] for item in previous_candidates], format_func=lambda value: labels[value])
    previous = next(item for item in previous_candidates if item["id"] == previous_id)
    previous_audit = build_assessment_audit(previous, current_factor_version=current_factor_version)
    comparison = compare_audit_traces(previous_audit, audit)
    c1, c2, c3 = st.columns(3)
    c1.metric("Footprint change", f"{comparison['total_change']:+.2f} kg")
    c2.metric("Input changes", comparison["input_changes"])
    c3.metric("Factor changes", comparison["factor_changes"])
    if comparison["methodology_changed"]:
        st.warning(METHODOLOGY_CHANGED)
    comparison_df = pd.DataFrame(comparison["categories"])
    if not comparison_df.empty:
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
else:
    st.caption("A second assessment is required for historical comparison.")

st.subheader("📥 Export Audit Report")
report_json = serialize_audit(audit)
st.download_button(
    "Download audit report (JSON)", data=report_json,
    file_name=f"assessment-audit-{audit.assessment_id}.json",
    mime="application/json", use_container_width=True,
)
st.caption("The report is generated locally from the selected assessment and recorded factor metadata. No external upload is performed.")
