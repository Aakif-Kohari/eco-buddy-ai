"""Streamlit explorer for sustainability action dependencies and interactions."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from src.utils.action_interactions import (
    analyze_action_set,
    action_statuses,
    estimate_sequential_path,
    explain_action,
    interaction_matrix,
    load_reports,
    save_report,
    serialize_report,
)

st.set_page_config(
    page_title="Action Interaction Analyzer",
    page_icon="🔗",
    layout="wide",
)

DEFAULT_ACTIONS = [
    {
        "id": "insulation",
        "name": "Improve home insulation",
        "category": "Energy",
        "impact_low": 100,
        "impact_high": 250,
        "dependencies": [],
        "description": "Reduce heating and cooling demand before replacing equipment.",
    },
    {
        "id": "heating",
        "name": "Optimize heating demand",
        "category": "Energy",
        "impact_low": 80,
        "impact_high": 180,
        "dependencies": ["insulation"],
        "description": "Tune heating settings after envelope improvements.",
    },
    {
        "id": "energy_monitor",
        "name": "Monitor appliance energy use",
        "category": "Energy",
        "impact_low": 30,
        "impact_high": 90,
        "overlaps": ["heating"],
        "description": "Measure consumption to identify additional reduction opportunities.",
    },
    {
        "id": "public_transport",
        "name": "Use public transport more often",
        "category": "Transportation",
        "impact_low": 150,
        "impact_high": 500,
        "description": "Replace selected private-car journeys with public transport.",
    },
    {
        "id": "drive_less",
        "name": "Reduce private car trips",
        "category": "Transportation",
        "impact_low": 100,
        "impact_high": 350,
        "conflicts": ["flight_reduction"],
        "description": "Reduce unnecessary private vehicle use.",
    },
    {
        "id": "flight_reduction",
        "name": "Reduce non-essential flights",
        "category": "Transportation",
        "impact_low": 200,
        "impact_high": 700,
        "conflicts": ["drive_less"],
        "description": "Use alternatives or combine trips where practical.",
    },
    {
        "id": "plant_meals",
        "name": "Add more plant-based meals",
        "category": "Food",
        "impact_low": 80,
        "impact_high": 250,
        "description": "Replace a portion of higher-impact meals.",
    },
    {
        "id": "compost",
        "name": "Start household composting",
        "category": "Waste",
        "impact_low": 20,
        "impact_high": 80,
        "description": "Divert suitable organic waste from landfill disposal.",
    },
]


def _load_json(text: str) -> list[dict[str, Any]]:
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = payload.get("actions", payload.get("items", []))
    if not isinstance(payload, list):
        raise ValueError("Action document must contain a JSON list or an actions/items list.")
    return [dict(item) for item in payload if isinstance(item, dict)]


def _action_frame(actions: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for action in actions:
        rows.append(
            {
                "ID": action.get("id", ""),
                "Action": action.get("name", action.get("title", "Unnamed")),
                "Category": action.get("category", "General lifestyle"),
                "Impact low": action.get("impact_low", action.get("impact", "Unavailable")),
                "Impact high": action.get("impact_high", action.get("impact", "Unavailable")),
                "Dependencies": ", ".join(action.get("dependencies", []) or []),
                "Conflicts": ", ".join(action.get("conflicts", []) or []),
                "Overlaps": ", ".join(action.get("overlaps", []) or []),
                "Synergies": ", ".join(action.get("synergies", []) or []),
            }
        )
    return pd.DataFrame(rows)


def _render_impact(label: str, impact: Any) -> None:
    if impact.available:
        st.metric(label, f"{impact.low:,.0f}–{impact.high:,.0f} kg CO₂e/yr")
    else:
        st.metric(label, "Unavailable")


def _render_report(report: Any, actions: list[dict[str, Any]]) -> None:
    by_id = {str(a.get("id")): a for a in actions}
    cols = st.columns(4)
    with cols[0]:
        _render_impact("Independent estimate", src.reporting.report.independent_impact)
    with cols[1]:
        _render_impact("Interaction-adjusted", src.reporting.report.combined_impact)
    with cols[2]:
        st.metric("Blocked actions", len(src.reporting.report.blocked_action_ids))
    with cols[3]:
        st.metric("Interactions", len(src.reporting.report.interactions))

    if src.reporting.report.warnings:
        for warning in src.reporting.report.warnings:
            st.warning(warning)

    st.subheader("Recommended execution order")
    order_rows = []
    for position, action_id in enumerate(src.reporting.report.execution_order, 1):
        action = by_id.get(action_id, {})
        order_rows.append({"Step": position, "Action": action.get("name", action_id), "ID": action_id})
    if order_rows:
        st.dataframe(pd.DataFrame(order_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No actions are selected.")

    if src.reporting.report.blocked_action_ids:
        st.subheader("Prerequisites still needed")
        blocked_rows = []
        for finding in src.reporting.report.dependencies:
            if not finding.satisfied:
                blocked_rows.append(
                    {
                        "Action": by_id.get(finding.action_id, {}).get("name", finding.action_id),
                        "Prerequisite": by_id.get(finding.prerequisite_id, {}).get("name", finding.prerequisite_id),
                        "Reason": finding.rationale,
                    }
                )
        if blocked_rows:
            st.dataframe(pd.DataFrame(blocked_rows), use_container_width=True, hide_index=True)

    if src.reporting.report.conflicts:
        st.subheader("Conflicting actions")
        conflict_rows = []
        for conflict in src.reporting.report.conflicts:
            conflict_rows.append(
                {
                    "Action A": by_id.get(conflict.first_id, {}).get("name", conflict.first_id),
                    "Action B": by_id.get(conflict.second_id, {}).get("name", conflict.second_id),
                    "Severity": conflict.severity,
                    "Reason": conflict.rationale,
                }
            )
        st.dataframe(pd.DataFrame(conflict_rows), use_container_width=True, hide_index=True)

    st.subheader("Impact interactions")
    interaction_rows = []
    for item in src.reporting.report.interactions:
        interaction_rows.append(
            {
                "Action A": by_id.get(item.first_id, {}).get("name", item.first_id),
                "Action B": by_id.get(item.second_id, {}).get("name", item.second_id),
                "Relationship": item.relationship,
                "Low adjustment": item.adjustment_low,
                "High adjustment": item.adjustment_high,
                "Reason": item.rationale,
            }
        )
    if interaction_rows:
        st.dataframe(pd.DataFrame(interaction_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No explicit interactions were found among the selected actions.")

    st.subheader("Diminishing-return factors")
    dim_rows = [
        {"Action": by_id.get(action_id, {}).get("name", action_id), "Factor": factor}
        for action_id, factor in src.reporting.report.diminishing_returns.items()
    ]
    if dim_rows:
        st.dataframe(pd.DataFrame(dim_rows), use_container_width=True, hide_index=True)

    st.subheader("Why the result looks this way")
    for explanation in src.reporting.report.explanations:
        st.markdown(f"- {explanation}")


def main() -> None:
    st.title("🔗 Sustainability Action Interaction Analyzer")
    st.caption(
        "Understand prerequisites, conflicts, overlapping benefits, sequential effects, "
        "and diminishing returns before combining sustainability actions."
    )
    st.info(
        "This tool analyzes actions supplied by the existing planning/recommendation layers. "
        "It does not create new recommendations and does not modify historical assessments. "
        "Impact values are treated as estimates, never guarantees."
    )

    with st.sidebar:
        st.header("Action data")
        source = st.radio("Source", ["Demo catalog", "Paste JSON", "Upload JSON"], index=0)
        actions = DEFAULT_ACTIONS
        if source == "Paste JSON":
            raw = st.text_area("Action JSON", value=json.dumps(DEFAULT_ACTIONS, indent=2), height=300)
            try:
                actions = _load_json(raw)
            except (ValueError, json.JSONDecodeError) as exc:
                st.error(f"Invalid JSON: {exc}")
                actions = []
        elif source == "Upload JSON":
            uploaded = st.file_uploader("Upload action JSON", type=["json"])
            if uploaded is not None:
                try:
                    actions = _load_json(uploaded.getvalue().decode("utf-8"))
                except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                    st.error(f"Invalid action file: {exc}")
                    actions = []

        completed = st.multiselect(
            "Already completed",
            options=[str(a.get("id")) for a in actions],
            format_func=lambda item: next((a.get("name", item) for a in actions if str(a.get("id")) == item), item),
        )

    if not actions:
        st.error("No usable actions are available.")
        return

    st.subheader("Available actions")
    st.dataframe(_action_frame(actions), use_container_width=True, hide_index=True)

    options = [str(a.get("id")) for a in actions]
    selected = st.multiselect(
        "Select actions to analyze",
        options=options,
        default=options[:3],
        format_func=lambda item: next((a.get("name", item) for a in actions if str(a.get("id")) == item), item),
    )

    st.caption("Select alternatives together if you want the analyzer to surface conflicts. Select prerequisites with dependents to see the execution sequence.")

    if not selected:
        st.warning("Select at least one action to generate an interaction src.reporting.report.")
        return

    report = analyze_action_set(selected, actions, completed_ids=completed)
    _render_report(report, actions)

    st.subheader("Sequential reduction path")
    path = estimate_sequential_path(selected, actions)
    if path:
        path_df = pd.DataFrame(path)
        path_df["name"] = path_df["action_id"].map({str(a.get("id")): a.get("name") for a in actions})
        st.dataframe(
            path_df[["position", "name", "incremental_low", "incremental_high", "running_low", "running_high", "diminishing_factor"]],
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Action status")
    statuses = action_statuses(selected, actions, completed_ids=completed)
    status_df = pd.DataFrame(
        [
            {
                "Action": next((a.get("name", action_id) for a in actions if str(a.get("id")) == action_id), action_id),
                "Status": status,
            }
            for action_id, status in statuses.items()
        ]
    )
    st.dataframe(status_df, use_container_width=True, hide_index=True)

    st.subheader("Individual action explainers")
    for action_id in selected:
        action_name = next((a.get("name", action_id) for a in actions if str(a.get("id")) == action_id), action_id)
        with st.expander(action_name):
            details = explain_action(action_id, actions)
            st.json(details)

    st.subheader("Export and persistence")
    payload = serialize_report(report)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ Download interaction report",
            data=payload,
            file_name="sustainability_action_interactions.json",
            mime="application/json",
        )
    with col2:
        if st.button("💾 Save analysis snapshot"):
            try:
                record_id = save_report(report, user_id=st.session_state.get("user_id"))
                st.success(f"Saved interaction snapshot #{record_id}.")
            except Exception as exc:
                st.error(f"Could not save snapshot: {exc}")

    with st.expander("Interaction matrix"):
        matrix = interaction_matrix(selected, actions)
        if matrix:
            st.dataframe(pd.DataFrame(matrix), use_container_width=True, hide_index=True)
        else:
            st.info("No pairwise interactions for this selection.")

    with st.expander("Previous saved reports"):
        try:
            reports = load_reports(user_id=st.session_state.get("user_id"), limit=10)
            if reports:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Generated": item.generated_at,
                                "Actions": len(item.selected_action_ids),
                                "Blocked": len(item.blocked_action_ids),
                                "Conflicts": len(item.conflicts),
                            }
                            for item in reports
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No saved interaction snapshots yet.")
        except Exception as exc:
            st.caption(f"Saved-report history is unavailable: {exc}")


if __name__ == "__main__":
    main()
