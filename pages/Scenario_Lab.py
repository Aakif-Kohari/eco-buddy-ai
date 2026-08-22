"""Interactive carbon-footprint what-if Scenario Lab."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dataclasses import replace

from database import get_assessments_with_factors, save_assessment
from emissions import get_factor_version
from scenario_lab import (
    SCENARIO_PRESETS,
    ScenarioResult,
    ScenarioValidationError,
    apply_preset,
    calculate_scenario,
    compare_multiple_scenarios,
    compare_scenario_to_baseline,
    create_scenario,
    summarize_scenario,
)
from session_state_utils import ensure_session_state
from styles.theme import apply_theme


user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()
st.title("🔮 Carbon Footprint Scenario Lab")
st.markdown(
    "Experiment with lifestyle changes before committing them to your assessment "
    "history. Scenarios are temporary until you explicitly save one as a new assessment."
)

ensure_session_state(
    {
        "scenario_lab_baseline_id": None,
        "scenario_lab_region": "Global",
        "scenario_lab_name": "My Scenario",
        "scenario_lab_transport": "Car",
        "scenario_lab_distance": 10.0,
        "scenario_lab_electricity": 200.0,
        "scenario_lab_diet": "Vegetarian",
        "scenario_lab_flights": 0,
        "scenario_lab_scenarios": [],
    }
)

assessments = get_assessments_with_factors(user_id)
if not assessments:
    st.info(
        "You need at least one completed assessment before creating a scenario. "
        "Run an assessment from the Carbon Footprint page first."
    )
    st.stop()

# get_assessments_with_factors:
# id, date, transport, created_at, distance, electricity, diet, flights,
# footprint, eco_score, factor_version
assessment_rows = []
for row in assessments:
    assessment_rows.append(
        {
            "id": row[0],
            "date": row[1],
            "transport": row[2],
            "created_at": row[3],
            "distance": float(row[4]),
            "electricity": float(row[5]),
            "diet": row[6],
            "flights": int(row[7]),
            "footprint": float(row[8]),
            "eco_score": int(row[9]),
            "factor_version": row[10] or "static-v1",
        }
    )

labels = [
    f"#{row['id']} • {row['date']} • {row['footprint']:.0f} kg CO₂e • "
    f"Score {row['eco_score']}"
    for row in assessment_rows
]
selected_index = st.selectbox(
    "Baseline assessment",
    range(len(assessment_rows)),
    format_func=lambda i: labels[i],
    key="scenario_lab_baseline_selector",
)
baseline_record = assessment_rows[selected_index]

# Reset temporary scenarios/editor whenever the baseline changes.
if st.session_state.scenario_lab_baseline_id != baseline_record["id"]:
    st.session_state.scenario_lab_baseline_id = baseline_record["id"]
    st.session_state.scenario_lab_scenarios = []
    st.session_state.scenario_lab_region = st.session_state.get(
        "region", "Global"
    )
    st.session_state.scenario_lab_name = "My Scenario"
    st.session_state.scenario_lab_transport = baseline_record["transport"]
    st.session_state.scenario_lab_distance = baseline_record["distance"]
    st.session_state.scenario_lab_electricity = baseline_record["electricity"]
    st.session_state.scenario_lab_diet = baseline_record["diet"]
    st.session_state.scenario_lab_flights = baseline_record["flights"]

baseline_region = st.selectbox(
    "Scenario emission-factor region",
    ["Global", "US", "UK", "EU"],
    key="scenario_lab_region",
    help=(
        "Historical assessments do not currently persist their region. "
        "Global is used unless you select the region that matches the original assessment."
    ),
)

baseline_inputs = {
    "transport": baseline_record["transport"],
    "distance": baseline_record["distance"],
    "electricity": baseline_record["electricity"],
    "diet": baseline_record["diet"],
    "flights": baseline_record["flights"],
    "region": baseline_region,
}

try:
    # Rebuild the category contribution breakdown using the selected current
    # factor region, while preserving the stored assessment total/score as the
    # baseline displayed to the user.
    calculated_baseline = calculate_scenario(
        create_scenario(baseline_inputs, "Baseline")
    )
    baseline = replace(
        calculated_baseline,
        footprint=baseline_record["footprint"],
        eco_score=baseline_record["eco_score"],
    )
except ScenarioValidationError as exc:
    st.error(f"Unable to prepare this assessment as a baseline: {exc}")
    st.stop()

current_factor_version = get_factor_version(baseline_region)
if baseline_record["factor_version"] != current_factor_version:
    st.warning(
        "This assessment was created with a different emission-factor version "
        f"({baseline_record['factor_version']}) than the current "
        f"{current_factor_version}. Category details use the selected current "
        "region/factors; the stored assessment total and score remain unchanged."
    )

st.subheader("📌 Baseline")
baseline_cols = st.columns(4)
baseline_cols[0].metric("Annual footprint", f"{baseline.footprint:,.0f} kg CO₂e")
baseline_cols[1].metric("Eco Score", baseline.eco_score)
baseline_cols[2].metric("Transport", f"{baseline.contributors.get('Transport', 0):,.0f} kg")
baseline_cols[3].metric("Electricity", f"{baseline.contributors.get('Electricity', 0):,.0f} kg")

st.divider()
st.subheader("🧪 Build a Scenario")

preset_names = ["Custom scenario"] + list(SCENARIO_PRESETS)
preset = st.selectbox("Scenario preset", preset_names, key="scenario_lab_preset")

if st.button("Load preset", use_container_width=False):
    try:
        if preset == "Custom scenario":
            scenario = create_scenario(
                baseline_inputs,
                st.session_state.scenario_lab_name,
                transport=st.session_state.scenario_lab_transport,
                distance=st.session_state.scenario_lab_distance,
                electricity=st.session_state.scenario_lab_electricity,
                diet=st.session_state.scenario_lab_diet,
                flights=st.session_state.scenario_lab_flights,
            )
        else:
            scenario = apply_preset(baseline_inputs, preset)
        st.session_state.scenario_lab_name = scenario.name
        st.session_state.scenario_lab_transport = scenario.transport
        st.session_state.scenario_lab_distance = scenario.distance
        st.session_state.scenario_lab_electricity = scenario.electricity
        st.session_state.scenario_lab_diet = scenario.diet
        st.session_state.scenario_lab_flights = scenario.flights
        st.success(f"Loaded: {scenario.name}")
    except ScenarioValidationError as exc:
        st.error(str(exc))

editor_cols = st.columns(2)
with editor_cols[0]:
    st.text_input("Scenario name", key="scenario_lab_name")
    st.selectbox(
        "Primary transport",
        ["Car", "Public Transport", "Bike", "Walking"],
        key="scenario_lab_transport",
    )
    st.number_input(
        "Daily distance (km)",
        min_value=0.0,
        max_value=500.0,
        step=1.0,
        key="scenario_lab_distance",
    )
with editor_cols[1]:
    st.number_input(
        "Monthly electricity (kWh)",
        min_value=0.0,
        max_value=10000.0,
        step=10.0,
        key="scenario_lab_electricity",
    )
    st.selectbox(
        "Diet",
        ["Vegetarian", "Non-Vegetarian"],
        key="scenario_lab_diet",
    )
    st.number_input(
        "Annual flights",
        min_value=0,
        max_value=365,
        step=1,
        key="scenario_lab_flights",
    )

try:
    editor_scenario = create_scenario(
        baseline_inputs,
        st.session_state.scenario_lab_name,
        transport=st.session_state.scenario_lab_transport,
        distance=st.session_state.scenario_lab_distance,
        electricity=st.session_state.scenario_lab_electricity,
        diet=st.session_state.scenario_lab_diet,
        flights=st.session_state.scenario_lab_flights,
    )
    editor_result = calculate_scenario(editor_scenario)
    editor_comparison = compare_scenario_to_baseline(baseline, editor_result)

    metric_cols = st.columns(4)
    metric_cols[0].metric(
        "Scenario footprint",
        f"{editor_result.footprint:,.0f} kg",
        delta=f"{editor_comparison.footprint_delta:+,.0f} kg",
    )
    metric_cols[1].metric(
        "Change",
        f"{editor_comparison.percentage_change:+.1f}%",
    )
    metric_cols[2].metric(
        "Eco Score",
        editor_result.eco_score,
        delta=f"{editor_comparison.eco_score_delta:+d}",
    )
    metric_cols[3].metric(
        "Reduction",
        f"{editor_comparison.reduction:,.0f} kg",
    )

    if editor_comparison.footprint_delta < 0:
        st.success(summarize_scenario(editor_result, editor_comparison))
    elif editor_comparison.footprint_delta > 0:
        st.error(summarize_scenario(editor_result, editor_comparison))
    else:
        st.info(summarize_scenario(editor_result, editor_comparison))

    if editor_comparison.increased_categories:
        st.warning(
            "Increased categories: "
            + ", ".join(editor_comparison.increased_categories)
        )

    if st.button("➕ Add scenario for comparison", type="primary"):
        existing = {
            item["scenario"]["name"]
            for item in st.session_state.scenario_lab_scenarios
        }
        if editor_result.scenario.name in existing:
            st.warning("A scenario with this name is already in the comparison list.")
        else:
            st.session_state.scenario_lab_scenarios.append(editor_result.to_dict())
            st.success("Scenario added. Create another scenario to compare it.")
            st.rerun()

except ScenarioValidationError as exc:
    editor_result = None
    editor_comparison = None
    st.error(f"Scenario validation failed: {exc}")

scenarios = []
for payload in st.session_state.scenario_lab_scenarios:
    try:
        # Recalculate from stored inputs so the comparison remains a real
        # calculation, not a stale serialized result.
        scenario_data = payload["scenario"]
        scenario = create_scenario(
            scenario_data,
            scenario_data["name"],
        )
        scenarios.append(calculate_scenario(scenario))
    except (KeyError, ScenarioValidationError):
        continue

if scenarios:
    st.divider()
    st.subheader("📊 Scenario Comparison")

    comparison_rows = compare_multiple_scenarios(baseline, scenarios)
    st.dataframe(
        pd.DataFrame(comparison_rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "rank": st.column_config.NumberColumn("Rank", width="small"),
            "footprint_kg_co2e": st.column_config.NumberColumn(
                "Scenario kg CO₂e", format="%.0f"
            ),
            "reduction_kg_co2e": st.column_config.NumberColumn(
                "Reduction kg CO₂e", format="%.0f"
            ),
            "percentage_change": st.column_config.NumberColumn(
                "Change %", format="%.1f%%"
            ),
            "eco_score": st.column_config.NumberColumn("Eco Score"),
            "eco_score_change": st.column_config.NumberColumn("Score Δ"),
        },
    )

    scenario_names = [result.scenario.name for result in scenarios]
    selected_scenario_name = st.selectbox(
        "Inspect scenario",
        scenario_names,
        key="scenario_lab_inspect",
    )
    selected_result = next(
        result for result in scenarios if result.scenario.name == selected_scenario_name
    )
    selected_comparison = compare_scenario_to_baseline(
        baseline, selected_result
    )

    detail_cols = st.columns(3)
    detail_cols[0].metric(
        "Absolute change",
        f"{selected_comparison.footprint_delta:+,.2f} kg CO₂e",
    )
    detail_cols[1].metric(
        "Percentage change",
        f"{selected_comparison.percentage_change:+.2f}%",
    )
    detail_cols[2].metric(
        "Largest improvement",
        selected_comparison.largest_improvement_category or "None",
    )

    chart_categories = sorted(
        set(baseline.contributors) | set(selected_result.contributors)
    )
    fig = go.Figure()
    fig.add_bar(
        name="Baseline",
        x=chart_categories,
        y=[baseline.contributors.get(category, 0) for category in chart_categories],
    )
    fig.add_bar(
        name=selected_result.scenario.name,
        x=chart_categories,
        y=[
            selected_result.contributors.get(category, 0)
            for category in chart_categories
        ],
    )
    fig.update_layout(
        barmode="group",
        title="Category-by-category footprint",
        yaxis_title="kg CO₂e/year",
        margin=dict(t=60, b=20, l=20, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    category_df = pd.DataFrame(
        [
            {
                "Category": category,
                "Baseline (kg CO₂e)": baseline.contributors.get(category, 0),
                "Scenario (kg CO₂e)": selected_result.contributors.get(category, 0),
                "Change (kg CO₂e)": selected_comparison.category_deltas.get(category, 0),
            }
            for category in chart_categories
        ]
    )
    st.dataframe(category_df, use_container_width=True, hide_index=True)

    if selected_comparison.increased_categories:
        st.warning(
            "This scenario increases: "
            + ", ".join(selected_comparison.increased_categories)
        )

    st.subheader("💾 Save as a New Assessment")
    st.caption(
        "Saving creates a separate assessment. Your selected baseline assessment "
        "is never updated or deleted."
    )
    save_confirmed = st.checkbox(
        "I understand this will create a new assessment record.",
        key="scenario_lab_save_confirmed",
    )
    if st.button(
        "Save selected scenario as new assessment",
        disabled=not save_confirmed,
        type="primary",
    ):
        scenario = selected_result.scenario
        success = save_assessment(
            user_id,
            scenario.transport,
            scenario.distance,
            scenario.electricity,
            scenario.diet,
            scenario.flights,
            selected_result.footprint,
            selected_result.eco_score,
            factor_version=selected_result.audit_log.get("factor_version"),
        )
        if success:
            st.success(
                f"Saved '{scenario.name}' as a new assessment. "
                "Your original baseline remains unchanged."
            )
            st.session_state.scenario_lab_save_confirmed = False
            st.session_state.scenario_lab_scenarios = []
            st.rerun()
        else:
            st.error("The new assessment could not be saved. No existing assessment was changed.")

    if st.button("🗑️ Clear temporary scenarios"):
        st.session_state.scenario_lab_scenarios = []
        st.rerun()
else:
    st.info("Add at least one scenario above to compare multiple possibilities.")
