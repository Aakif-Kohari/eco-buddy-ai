"""Streamlit UI for Sustainability Data Quality and Assessment Completeness."""
from datetime import datetime, timezone
import csv
import io
import streamlit as st

from src.data.sustainability_data_quality import (
    build_dashboard_payload,
    build_quality_report,
    critical_issues,
    filter_issues,
    IssueSeverity,
    report_markdown,
    serialize_report,
    sorted_issues,
    status_label,
    top_quality_actions,
    warning_issues,
)

st.set_page_config(
    page_title="Data Quality Center",
    page_icon="✅",
    layout="wide",
)

st.title("✅ Sustainability Data Quality Center")
st.caption(
    "Review assessment completeness, validation errors, missing inputs, "
    "duplicate records, stale data, and analysis readiness."
)

user_id = st.session_state.get("user_id", 1)

try:
    from src.core.database import get_assessments
except Exception as exc:
    st.error(f"Unable to import the database layer: {exc}")
    st.stop()

records = []
load_error = None

for call in (
    lambda: get_assessments(user_id),
    lambda: get_assessments(),
):
    try:
        records = call()
        break
    except TypeError:
        continue
    except Exception as exc:
        load_error = exc
        break

if load_error:
    st.error(f"Unable to load assessments: {load_error}")
    records = []

with st.sidebar:
    st.header("Quality settings")
    stale_days = st.number_input(
        "Stale after (days)",
        min_value=7,
        max_value=3650,
        value=90,
        step=7,
    )
    issue_filter = st.selectbox(
        "Show issues",
        ["All", "Errors", "Warnings", "Information"],
    )
    show_details = st.checkbox("Show assessment-level details", value=True)

report = build_quality_report(
    records,
    stale_days=int(stale_days),
    now=datetime.now(timezone.utc),
)

payload = build_dashboard_payload(report)

if src.reporting.report.assessments_checked == 0:
    st.warning(
        "No assessment records are available for quality analysis. "
        "Complete an assessment to establish a baseline."
    )

badges = payload["overview"]
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Quality score", f'{badges["score"]:.1f}/100')
c2.metric("Completeness", f'{badges["completeness_pct"]:.1f}%')
c3.metric("Assessments", src.reporting.report.assessments_checked)
c4.metric("Errors", src.reporting.report.assessments_with_errors)
c5.metric("Needs review", src.reporting.report.assessments_needing_review)

st.subheader(f"Overall status: {status_label(src.reporting.report.status)}")
st.write(
    "The center checks the values already stored by EcoBuddy. "
    "It does not rewrite assessments or recalculate historical footprints."
)

readiness = payload["readiness"]
if readiness["ready_for_trends"]:
    st.success("Trend analysis readiness: available.")
else:
    st.warning("Trend analysis readiness: resolve the listed quality issues first.")

if readiness["ready_for_benchmarking"]:
    st.success("Benchmarking readiness: available.")
else:
    st.info("Benchmarking readiness: requires a higher-quality dataset.")

st.subheader("Priority actions")
actions = top_quality_actions(report, limit=5)
if actions:
    for action in actions:
        st.write(f"- {action}")
else:
    st.success("No corrective actions are currently required.")

st.subheader("Field coverage")
coverage_rows = payload["field_coverage"]
if coverage_rows:
    st.dataframe(coverage_rows, use_container_width=True, hide_index=True)
else:
    st.info("No fields to display.")

st.subheader("Issue summary")
issue_rows = payload["issue_summary"]
if issue_rows:
    st.dataframe(issue_rows, use_container_width=True, hide_index=True)
else:
    st.success("No quality issues were detected.")

all_issues = sorted_issues(
    critical_issues(report) + warning_issues(report)
)
if issue_filter == "Errors":
    all_issues = sorted_issues(
        filter_issues(src.reporting.report.assessments[0].issues if src.reporting.report.assessments else (), severity=IssueSeverity.ERROR)
        if src.reporting.report.assessments else ()
    )
elif issue_filter == "Warnings":
    all_issues = sorted_issues(
        filter_issues(src.reporting.report.assessments[0].issues if src.reporting.report.assessments else (), severity=IssueSeverity.WARNING)
        if src.reporting.report.assessments else ()
    )
elif issue_filter == "Information":
    all_issues = sorted_issues(
        filter_issues(
            [issue for assessment in src.reporting.report.assessments for issue in assessment.issues],
            severity=IssueSeverity.INFO,
        )
    )

if all_issues:
    st.subheader("Quality issues")
    for issue in all_issues[:50]:
        title = f"{issue.severity.value.upper()} · {issue.field or 'record'} · {issue.message}"
        with st.expander(title):
            st.write(issue.recommendation)
            if issue.assessment_id:
                st.caption(f"Assessment: {issue.assessment_id}")
            if issue.evidence:
                st.json(issue.evidence)

if show_details:
    st.subheader("Assessment completeness")
    for assessment in src.reporting.report.assessments:
        with st.expander(
            f"{assessment.assessment_id} · "
            f"{assessment.status.value} · "
            f"{assessment.completeness_pct:.1f}%"
        ):
            left, right = st.columns(2)
            with left:
                st.metric("Completeness", f"{assessment.completeness_pct:.1f}%")
                st.metric("Quality score", f"{assessment.score:.1f}/100")
                st.write(
                    f"Valid fields: {assessment.valid_field_count}/"
                    f"{assessment.expected_field_count}"
                )
            with right:
                st.write("**Missing required:**")
                st.write(", ".join(assessment.missing_required) or "None")
                st.write("**Missing optional:**")
                st.write(", ".join(assessment.missing_optional) or "None")
                st.write("**Invalid fields:**")
                st.write(", ".join(assessment.invalid_fields) or "None")

            for issue in sorted_issues(assessment.issues):
                st.write(
                    f"**{issue.severity.value.upper()}** — {issue.message} "
                    f"_{issue.recommendation}_"
                )

st.subheader("Exports")

report_json = serialize_report(report)
report_md = report_markdown(report)

csv_buffer = io.StringIO()
writer = csv.DictWriter(
    csv_buffer,
    fieldnames=[
        "assessment_id",
        "status",
        "score",
        "completeness_pct",
        "missing_required",
        "missing_optional",
        "invalid_fields",
        "warnings",
        "errors",
    ],
)
writer.writeheader()
for assessment in src.reporting.report.assessments:
    writer.writerow({
        "assessment_id": assessment.assessment_id,
        "status": assessment.status.value,
        "score": assessment.score,
        "completeness_pct": assessment.completeness_pct,
        "missing_required": ", ".join(assessment.missing_required),
        "missing_optional": ", ".join(assessment.missing_optional),
        "invalid_fields": ", ".join(assessment.invalid_fields),
        "warnings": assessment.warnings,
        "errors": assessment.errors,
    })

d1, d2, d3 = st.columns(3)
d1.download_button(
    "Download JSON",
    report_json,
    "sustainability-data-quality.json",
    "application/json",
)
d2.download_button(
    "Download Markdown",
    report_md,
    "sustainability-data-quality.md",
    "text/markdown",
)
d3.download_button(
    "Download CSV",
    csv_buffer.getvalue(),
    "sustainability-assessment-quality.csv",
    "text/csv",
)
