
"""Streamlit page for Sustainability Goal Conflict & Feasibility Analyzer."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

from src.utils.goal_feasibility import (
    ACHIEVED,
    AT_RISK,
    FEASIBLE,
    INSUFFICIENT_DATA,
    UNLIKELY,
    analyze_goal_feasibility,
    load_feasibility_reports,
    persist_feasibility_report,
    serialize_feasibility_report,
)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


def _user_id() -> int | None:
    value = st.session_state.get("user_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _database_connection():
    try:
        from database_connection import database_connection
        return database_connection(DB_NAME)
    except ImportError:
        return sqlite3.connect(DB_NAME)


def _row_to_dict(row, columns):
    return {column: row[index] for index, column in enumerate(columns)}


def _load_goal_rows(user_id: int) -> list[dict]:
    """Read existing goal rows without altering the application's goal schema."""
    try:
        from database import get_active_goal
    except Exception:
        get_active_goal = None

    rows: list[dict] = []
    # Prefer the repository's existing helper because it already knows the
    # application's canonical goal representation.
    if get_active_goal is not None:
        try:
            active = get_active_goal(user_id)
            if active:
                if isinstance(active, dict):
                    rows.append(dict(active))
                elif hasattr(active, "keys"):
                    rows.append(dict(active))
        except Exception:
            pass

    # If the database contains a multi-goal table, discover its columns and
    # adapt only the fields the analyzer understands. No schema changes occur.
    try:
        with _database_connection() as connection:
            table_rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('reduction_goals', 'goals') ORDER BY CASE "
                "WHEN name='reduction_goals' THEN 0 ELSE 1 END"
            ).fetchall()
            for (table,) in table_rows:
                columns = [
                    row[1] for row in connection.execute(
                        f'PRAGMA table_info("{table}")'
                    ).fetchall()
                ]
                if "user_id" not in columns:
                    continue
                select_columns = ", ".join(f'"{column}"' for column in columns)
                query = (
                    f'SELECT {select_columns} FROM "{table}" '
                    'WHERE user_id = ? ORDER BY target_date ASC'
                )
                try:
                    raw_rows = connection.execute(query, (user_id,)).fetchall()
                except sqlite3.Error:
                    continue
                for raw in raw_rows:
                    candidate = _row_to_dict(raw, columns)
                    candidate["user_id"] = user_id
                    if not any(str(item.get("id")) == str(candidate.get("id")) for item in rows):
                        rows.append(candidate)
                if rows:
                    break
    except Exception:
        pass

    return rows


def _load_assessments(user_id: int):
    try:
        from database import get_assessments
        return get_assessments(user_id)
    except Exception:
        return []


def _load_action_items(user_id: int) -> list[dict]:
    """Load optional action-plan items when the existing table is present."""
    try:
        with _database_connection() as connection:
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='action_plan_items'"
            ).fetchall()
            if not tables:
                return []
            columns = [
                row[1] for row in connection.execute(
                    'PRAGMA table_info("action_plan_items")'
                ).fetchall()
            ]
            if "user_id" not in columns:
                return []
            raw = connection.execute(
                'SELECT * FROM "action_plan_items" WHERE user_id = ?',
                (user_id,),
            ).fetchall()
            return [_row_to_dict(row, columns) for row in raw]
    except Exception:
        return []


def _status_label(status: str) -> str:
    return {
        FEASIBLE: "Feasible",
        AT_RISK: "At risk",
        UNLIKELY: "Unlikely",
        INSUFFICIENT_DATA: "Insufficient data",
        ACHIEVED: "Achieved",
    }.get(status, status.replace("_", " ").title())


def _render_status(report):
    colors = {
        FEASIBLE: "success",
        AT_RISK: "warning",
        UNLIKELY: "error",
        INSUFFICIENT_DATA: "info",
        ACHIEVED: "success",
    }
    message = (
        f"**{_status_label(src.reporting.report.overall_status)}** — "
        f"overall feasibility score **{src.reporting.report.overall_score:.0f}/100**."
    )
    getattr(st, colors.get(src.reporting.report.overall_status, "info"))(message)


def _render_metrics(report):
    feasible = sum(item.status in {FEASIBLE, ACHIEVED} for item in src.reporting.report.goals)
    risky = sum(item.status == AT_RISK for item in src.reporting.report.goals)
    blocked = sum(item.status == UNLIKELY for item in src.reporting.report.goals)
    a, b, c, d = st.columns(4)
    a.metric("Goals analyzed", len(src.reporting.report.goals))
    b.metric("Feasible / achieved", feasible)
    c.metric("At risk", risky)
    d.metric("Unlikely", blocked)


def _render_goal_table(report):
    rows = [
        {
            "Goal": item.title,
            "Category": item.category,
            "Status": _status_label(item.status),
            "Risk": f"{item.risk_score:.0f}/100",
            "Required reduction": f"{item.required_reduction_kg:,.0f} kg",
            "Required reduction %": f"{item.required_reduction_pct:.1f}%",
            "Current": "—" if item.current_kg is None else f"{item.current_kg:,.0f} kg",
            "Actions": f"{item.completed_supporting_actions}/{item.supporting_actions}",
            "Days remaining": item.time_remaining_days,
        }
        for item in src.reporting.report.goals
    ]
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No valid goals are available for analysis.")


def _render_goal_details(report):
    st.subheader("Goal-by-goal feasibility")
    for item in src.reporting.report.goals:
        with st.expander(f"{item.title} · {_status_label(item.status)} · risk {item.risk_score:.0f}/100"):
            left, right = st.columns(2)
            left.metric("Baseline", f"{item.baseline_kg:,.0f} kg")
            left.metric("Target", f"{item.target_kg:,.0f} kg")
            right.metric("Required reduction", f"{item.required_reduction_kg:,.0f} kg")
            right.metric("Required pace", f"{item.required_reduction_kg_per_month:,.1f} kg/month")
            if item.current_kg is not None:
                st.metric("Latest footprint", f"{item.current_kg:,.0f} kg")
            if item.projected_shortfall_kg is not None:
                if item.projected_shortfall_kg > 0:
                    st.warning(
                        f"Projected shortfall at the observed pace: "
                        f"{item.projected_shortfall_kg:,.0f} kg."
                    )
                else:
                    st.success("Current observed pace is sufficient for the modeled target.")
            if item.warnings:
                st.markdown("**Evidence notes**")
                for warning in item.warnings:
                    st.write(f"- {warning}")
            if item.constraints:
                st.markdown("**Constraints and evidence**")
                st.dataframe(
                    pd.DataFrame([constraint.to_dict() for constraint in item.constraints]),
                    use_container_width=True,
                    hide_index=True,
                )


def _render_conflicts(report):
    st.subheader("Goal conflicts and interactions")
    if not src.reporting.report.conflicts:
        st.success("No goal conflicts were detected.")
        return
    rows = [
        {
            "Severity": conflict.severity,
            "Type": conflict.conflict_type.replace("_", " ").title(),
            "Goals": ", ".join(conflict.goal_ids),
            "Finding": conflict.title,
            "Explanation": conflict.explanation,
            "Suggested action": conflict.recommendation,
        }
        for conflict in src.reporting.report.conflicts
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_dependency_table(report):
    st.subheader("Goal dependencies")
    if not src.reporting.report.dependencies:
        st.info("No explicit goal dependencies are configured.")
        return
    rows = [
        {
            "Goal": item.goal_id,
            "Prerequisite": item.depends_on,
            "Satisfied": "Yes" if item.satisfied else "No",
            "Reason": item.reason,
        }
        for item in src.reporting.report.dependencies
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_combined_reduction(report):
    st.subheader("Combined reduction — double-counting check")
    combined = src.reporting.report.metadata.get("combined_reduction", {})
    rows = combined.get("categories", [])
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    a, b, c = st.columns(3)
    a.metric("Gross requested reduction", f"{combined.get('gross_reduction_kg', 0):,.0f} kg")
    b.metric("Conservative combined reduction", f"{combined.get('conservative_reduction_kg', 0):,.0f} kg")
    c.metric("Potential overlap", f"{combined.get('potential_double_counted_kg', 0):,.0f} kg")
    st.caption(
        "The conservative figure counts the largest reduction once per category. "
        "It is a safety check, not a promise of actual emissions savings."
    )


def _render_recommendations(report):
    st.subheader("Recommended corrections")
    for recommendation in src.reporting.report.recommendations:
        st.write(f"• {recommendation}")


def _render_history(user_id: int):
    try:
        with _database_connection() as connection:
            reports = load_feasibility_reports(connection, user_id=user_id, limit=10)
    except Exception:
        reports = []
    if not reports:
        st.info("No saved feasibility snapshots yet.")
        return
    rows = [
        {
            "Analyzed": row["analyzed_on"],
            "Status": _status_label(row["overall_status"]),
            "Score": round(float(row["overall_score"])),
            "Report ID": row["report_id"],
        }
        for row in reports
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def main():
    user_id = _user_id()
    if user_id is None:
        st.warning("Please log in from the main application page.")
        return

    st.title("🎯 Sustainability Goal Feasibility")
    st.write(
        "Analyze your sustainability goals together to find conflicts, overlapping "
        "reductions, unrealistic timelines, missing evidence, and unsupported dependencies."
    )

    goals = _load_goal_rows(user_id)
    assessments = _load_assessments(user_id)
    actions = _load_action_items(user_id)

    if not goals:
        st.info(
            "No existing reduction goals were found. Create a goal first, then return "
            "here to evaluate its feasibility."
        )
        return

    with st.sidebar:
        st.header("Analysis")
        as_of = st.date_input("Analyze as of", value=date.today())
        if st.button("Refresh analysis", use_container_width=True):
            st.rerun()

    report = analyze_goal_feasibility(
        goals,
        assessments,
        actions=actions,
        user_id=user_id,
        as_of=as_of,
    )

    _render_status(report)
    _render_metrics(report)

    tabs = st.tabs([
        "Overview",
        "Goal details",
        "Conflicts",
        "Dependencies",
        "Reduction overlap",
        "Recommendations",
        "History",
    ])

    with tabs[0]:
        _render_goal_table(report)
        st.caption(
            "Feasibility is an evidence-based estimate. It does not guarantee that a "
            "target can be achieved and never changes the underlying goal."
        )

    with tabs[1]:
        _render_goal_details(report)

    with tabs[2]:
        _render_conflicts(report)

    with tabs[3]:
        _render_dependency_table(report)

    with tabs[4]:
        _render_combined_reduction(report)

    with tabs[5]:
        _render_recommendations(report)

    with tabs[6]:
        _render_history(user_id)

    st.divider()
    payload = serialize_feasibility_report(report)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download feasibility report",
            data=payload,
            file_name=f"goal-feasibility-{user_id}-{as_of.isoformat()}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col2:
        if st.button("Save analysis snapshot", use_container_width=True):
            try:
                with _database_connection() as connection:
                    row_id = persist_feasibility_report(connection, report)
                st.success(f"Saved feasibility snapshot #{row_id}.")
            except Exception as exc:
                st.error(f"Could not save the snapshot: {exc}")

    if src.reporting.report.metadata.get("validation_warnings"):
        with st.expander("Validation notes"):
            for warning in src.reporting.report.metadata["validation_warnings"]:
                st.write(f"- {warning}")


main()
