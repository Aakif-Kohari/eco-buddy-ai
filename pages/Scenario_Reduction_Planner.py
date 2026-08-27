"""
Scenario-Based Reduction Planning & Optimization Engine – Streamlit Page
=========================================================================
Lets a user set a reduction target (percentage or absolute kg CO2),
configure candidate actions, and see ranked combinations of actions
("scenarios") that reach the target with the least modeled effort or cost.

Resolves GitHub issue #1261.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from scenario_reduction_engine import (
    PROJECTION_SOURCE,
    RANK_BY_COST,
    RANK_BY_EFFORT,
    RANK_BY_REDUCTION,
    ReductionAction,
    ReductionTarget,
    ScenarioEngineValidationError,
    generate_scenarios,
    rank_scenarios,
    reconcile_with_emissions_engine,
)

st.set_page_config(page_title="Scenario Reduction Planner", page_icon="🧩", layout="wide")

st.title("🧩 Scenario-Based Reduction Planner")
st.caption(
    "Model combinations of possible actions and find efficient ways to reach "
    "a reduction target. All results below are **modeled projections** "
    "(label: `%s`), not measured reductions." % PROJECTION_SOURCE
)

DEFAULT_ACTIONS = [
    {"id": "bike", "name": "Bike/transit commute", "category": "Transportation",
     "reduction_kg": 600, "effort": "medium", "cost": 50, "max_adoption": 1.0},
    {"id": "ev", "name": "Switch to an EV", "category": "Transportation",
     "reduction_kg": 1200, "effort": "high", "cost": 5000, "max_adoption": 1.0},
    {"id": "led", "name": "Switch to LED bulbs", "category": "Electricity",
     "reduction_kg": 150, "effort": "low", "cost": 30, "max_adoption": 1.0},
    {"id": "solar", "name": "Rooftop solar", "category": "Electricity",
     "reduction_kg": 900, "effort": "high", "cost": 8000, "max_adoption": 1.0},
    {"id": "diet", "name": "Reduce red meat", "category": "Diet",
     "reduction_kg": 400, "effort": "medium", "cost": 0, "max_adoption": 0.5},
]

baseline_kg = st.number_input(
    "Baseline annual footprint (kg CO2)",
    min_value=1.0,
    value=float(st.session_state.get("footprint", 8000.0)),
    step=100.0,
    help="Defaults to your last calculated footprint if available.",
)

target_mode = st.radio("Target type", ["Percentage reduction", "Absolute reduction (kg)"], horizontal=True)
if target_mode == "Percentage reduction":
    target_percent = st.slider("Target reduction (%)", min_value=1, max_value=90, value=10)
    target_kg = None
else:
    target_kg = st.number_input("Target reduction (kg CO2)", min_value=1.0, value=800.0, step=50.0)
    target_percent = None

st.subheader("Candidate actions")
st.caption("Edit, remove, or add rows. `excludes`/`dependencies` are comma-separated action IDs.")

actions_df = st.data_editor(
    pd.DataFrame(DEFAULT_ACTIONS),
    num_rows="dynamic",
    use_container_width=True,
    key="scenario_actions_editor",
)

rank_by_label = st.selectbox(
    "Rank scenarios by",
    ["Effort", "Cost", "Reduction"],
    index=0,
)
rank_by = {"Effort": RANK_BY_EFFORT, "Cost": RANK_BY_COST, "Reduction": RANK_BY_REDUCTION}[rank_by_label]

if st.button("Generate scenarios", type="primary"):
    try:
        actions = [
            ReductionAction(
                id=str(row["id"]),
                name=str(row.get("name", row["id"])),
                category=str(row["category"]),
                reduction_kg=row["reduction_kg"],
                effort=row.get("effort", "medium"),
                cost=row.get("cost", 0.0),
                max_adoption=row.get("max_adoption", 1.0),
            )
            for row in actions_df.to_dict("records")
            if str(row.get("id", "")).strip()
        ]
        target = ReductionTarget(
            baseline_kg=baseline_kg, target_percent=target_percent, target_kg=target_kg
        )
        scenarios = generate_scenarios(actions, target)
        ranked = rank_scenarios(scenarios, by=rank_by, feasible_only=True)
    except ScenarioEngineValidationError as exc:
        st.error(f"Could not generate scenarios: {exc}")
    else:
        st.info(
            f"Target: **{target.resolved_target_kg:.0f} kg CO2** "
            f"({target.resolved_target_percent:.1f}% of baseline)."
        )
        if not ranked:
            st.warning("No combination of the current actions reaches this target.")
        else:
            st.success(f"Found {len(ranked)} feasible scenario(s) — all values are modeled projections.")
            for rank, scenario in enumerate(ranked, start=1):
                with st.expander(
                    f"#{rank}: {', '.join(scenario.action_ids)} — "
                    f"{scenario.total_reduction_kg:.0f} kg reduced "
                    f"({scenario.reduction_percent:.1f}%)"
                ):
                    st.write(f"**Source:** {scenario.source} (modeled, not measured)")
                    st.write(f"**Total effort score:** {scenario.total_effort:.1f}")
                    st.write(f"**Total estimated cost:** {scenario.total_cost:.2f}")
                    st.write("**Category breakdown (kg CO2):**")
                    st.table(pd.DataFrame(
                        scenario.category_breakdown.items(), columns=["Category", "Reduction (kg)"]
                    ))
                    report = reconcile_with_emissions_engine(scenario, baseline_kg)
                    st.write(
                        f"**Reconciled projected total footprint:** "
                        f"{report['projected_total_kg']:.0f} kg CO2"
                    )