"""Recommendation Coverage and Sustainability Gap Analyzer UI."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src.core.database import get_assessments
from src.carbon.emissions import calculate_footprint
from src.ai.recommendations import generate_recommendations
from src.ai.recommendation_feedback import get_feedback_history
from src.utils.recommendation_coverage import (
    CoverageStatus,
    GapSeverity,
    RecommendationCoverageStore,
    build_coverage_from_existing_recommendations,
    coverage_table,
    gap_table,
    summarize_coverage,
)
from styles.theme import apply_theme


st.set_page_config(
    page_title="Recommendation Coverage",
    page_icon="🧭",
    layout="wide",
)
apply_theme()


@st.cache_data(ttl=60, show_spinner=False)
def _latest_assessment(user_id: int):
    rows = get_assessments(user_id)
    if not rows:
        return None
    columns = [
        "id", "user_id", "date", "created_at", "transport", "distance",
        "electricity", "diet", "flights", "footprint", "eco_score",
        "trip_id", "factor_version",
    ]
    frame = pd.DataFrame(rows, columns=columns[: len(rows[0])])
    if "created_at" in frame.columns:
        frame["_created"] = pd.to_datetime(frame["created_at"], errors="coerce")
    else:
        frame["_created"] = pd.NaT
    frame = frame.sort_values("_created", ascending=False, na_position="last")
    return frame.iloc[0].to_dict()


def _safe_float(value, default=0.0):
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _status_badge(status: str) -> str:
    return {
        "covered": "🟢 Covered",
        "partial": "🟡 Partial",
        "gap": "🔴 Gap",
        "no_data": "⚪ No data",
    }.get(status, status.title())


def _severity_badge(severity: str) -> str:
    return {
        "critical": "🔴 Critical",
        "high": "🟠 High",
        "medium": "🟡 Medium",
        "low": "🔵 Low",
        "none": "🟢 None",
    }.get(severity, severity.title())


user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

st.title("🧭 Recommendation Coverage & Sustainability Gaps")
st.caption(
    "This analyzer evaluates the recommendations EcoBuddy already generates. "
    "It does not invent new recommendations or alter your assessment."
)

assessment = _latest_assessment(int(user_id))
if not assessment:
    st.info("Complete a sustainability assessment before analyzing recommendation coverage.")
    st.stop()

transport = str(assessment.get("transport") or "Walking")
distance = _safe_float(assessment.get("distance"))
electricity = _safe_float(assessment.get("electricity"))
diet = str(assessment.get("diet") or "Vegetarian")
flights = int(_safe_float(assessment.get("flights")))

try:
    footprint, contributors = calculate_footprint(
        transport, distance, electricity, diet, flights, "Global"
    )
    _, generated_recommendations = generate_recommendations(
        transport, electricity, diet, flights, contributors
    )
except Exception as exc:
    st.error(f"Could not analyze the latest assessment: {exc}")
    st.stop()

try:
    feedback = get_feedback_history(int(user_id))
except Exception as exc:
    feedback = []
    st.warning(f"Recommendation feedback could not be loaded; coverage will use the current recommendation set only. ({exc})")

report = build_coverage_from_existing_recommendations(
    contributors,
    generated_recommendations,
    feedback=feedback,
    user_id=int(user_id),
    config=None,
)
summary = summarize_coverage(report)

with st.container(border=True):
    st.subheader("Current assessment baseline")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Annual footprint", f"{footprint:,.0f} kg CO₂e")
    c2.metric("Recommendations", src.reporting.report.recommendation_count)
    c3.metric("Coverage score", f"{summary['overall_percent']:.0f}%")
    c4.metric("High-impact gaps", src.reporting.report.high_impact_uncovered_count)

status = src.reporting.report.status.value
if status == CoverageStatus.COVERED.value:
    st.success("Recommendation coverage is strong across the measured impact categories.")
elif status == CoverageStatus.PARTIAL.value:
    st.warning("Recommendation coverage is partial. Review the highest-impact gaps below.")
elif status == CoverageStatus.GAP.value:
    st.error("Important sustainability categories are underserved by the current recommendation set.")
else:
    st.info("There is not enough assessment impact data to evaluate coverage reliably.")

st.divider()

left, right = st.columns([2, 1])
with left:
    st.subheader("Category coverage")
    table = pd.DataFrame(coverage_table(report))
    if table.empty:
        st.info("No category coverage data is available.")
    else:
        display = table.copy()
        display["Impact share"] = (display["Impact share"] * 100).round(1).astype(str) + "%"
        display["Coverage"] = (display["Coverage"] * 100).round(1).astype(str) + "%"
        display["Repetition"] = (display["Repetition"] * 100).round(1).astype(str) + "%"
        display["Status"] = display["Status"].map(_status_badge)
        display["Severity"] = display["Severity"].map(_severity_badge)
        st.dataframe(
            display[
                [
                    "Category", "Impact (kg CO2e)", "Impact share", "Recommendations",
                    "Completed", "Rejected", "Unique", "Coverage", "Status", "Severity",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

with right:
    st.subheader("Recommendation mix")
    distribution = src.reporting.report.metadata.get("category_distribution", {})
    if distribution:
        chart = pd.DataFrame(
            {"Recommendations": distribution}
        ).sort_values("Recommendations", ascending=False)
        st.bar_chart(chart)
    else:
        st.info("No recommendation distribution is available.")

    st.metric("Category diversity", f"{src.reporting.report.recommendation_diversity * 100:.0f}%")
    st.caption(
        "Diversity measures how evenly the existing recommendation set is spread "
        "across sustainability categories. It is not a quality score by itself."
    )

st.divider()

st.subheader("🚩 Sustainability gaps")
if not src.reporting.report.gaps:
    st.success("No material recommendation coverage gaps were detected.")
else:
    for gap in src.reporting.report.gaps:
        severity = gap.severity.value
        with st.expander(f"{_severity_badge(severity)} · {gap.title}", expanded=severity in {"critical", "high"}):
            st.markdown(f"**Category:** {gap.label}")
            st.write(gap.reason)
            st.markdown(f"**Detection code:** `{gap.code}`")
            st.markdown(f"**Existing recommendations:** {gap.recommendation_count}")
            st.markdown(f"**Relevant recommendations:** {gap.relevant_count}")
            st.info(gap.suggested_follow_up)

if src.reporting.report.repeated_recommendations:
    st.warning(
        "Repeated recommendation titles detected: "
        + ", ".join(f"`{title}`" for title in src.reporting.report.repeated_recommendations)
    )

if src.reporting.report.duplicate_ids:
    st.warning(
        "Duplicate recommendation IDs detected. These are flagged for catalog cleanup and are not silently removed."
    )

st.divider()

st.subheader("🔎 Why was this category flagged?")
for row in src.reporting.report.categories:
    if row.status in {CoverageStatus.GAP, CoverageStatus.PARTIAL} and row.impact > 0:
        with st.expander(f"{row.label} · {row.impact_share * 100:.0f}% of impact"):
            st.write(row.reason)
            st.write(
                f"The analyzer found {row.relevant_count} relevant recommendation(s), "
                f"{row.completed_count} completed, and {row.rejected_count} previously rejected."
            )
            st.progress(float(row.coverage_score), text=f"Coverage score: {row.coverage_score * 100:.0f}%")

st.divider()

st.subheader("📈 Coverage history")
store = RecommendationCoverageStore()
try:
    history_rows = store.list_reports(int(user_id), limit=20)
except Exception as exc:
    history_rows = []
    st.warning(f"Coverage history is unavailable: {exc}")

if history_rows:
    history_frame = pd.DataFrame(
        [
            {
                "Date": row["created_at"],
                "Score": row["coverage_score"],
                "Status": row["status"].title(),
            }
            for row in reversed(history_rows)
        ]
    )
    history_frame["Score"] = history_frame["Score"].astype(float)
    st.line_chart(history_frame.set_index("Date")["Score"])
    st.dataframe(history_frame, use_container_width=True, hide_index=True)
else:
    st.info("No saved coverage reports yet. Save the current report below to start a history.")

st.divider()

save_col, download_col = st.columns(2)
with save_col:
    fingerprint = json.dumps(src.reporting.report.to_dict(), sort_keys=True)
    last_saved = st.session_state.get("recommendation_coverage_last_saved")
    if st.button("Save current coverage report", type="primary", use_container_width=True):
        if fingerprint == last_saved:
            st.info("This exact coverage report has already been saved in this session.")
        else:
            try:
                report_id = store.save(report)
                st.session_state["recommendation_coverage_last_saved"] = fingerprint
                st.success(f"Coverage report #{report_id} saved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save coverage report: {exc}")

with download_col:
    st.download_button(
        "Download coverage report (JSON)",
        data=src.reporting.report.to_json(indent=2),
        file_name="recommendation_coverage_report.json",
        mime="application/json",
        use_container_width=True,
    )

st.caption(
    "Coverage analysis is deterministic and uses the existing recommendation output. "
    "A gap means the current catalog does not sufficiently cover the user's measured needs; "
    "it does not mean EcoBuddy has no possible action for that category."
)
