"""Streamlit UI for Sustainability Scenario Simulation (#1296)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from sustainability_scenarios import (
    ScenarioChange,
    ScenarioDefinition,
    ScenarioValidationError,
    category_contribution_table,
    combine_scenarios,
    compare_scenarios,
    default_scenarios,
    export_comparison,
    export_result,
    explain_change,
    make_percentage_scenario,
    make_set_scenario,
    run_default_scenarios,
    sensitivity_analysis,
    simulate_scenario,
)


st.set_page_config(
    page_title="Sustainability Scenario Simulator",
    page_icon="🔬",
    layout="wide",
)


def _find_database() -> Path | None:
    candidates = [
        Path("eco_buddy.db"),
        Path("data/eco_buddy.db"),
        Path(__file__).resolve().parents[1] / "eco_buddy.db",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _assessment_columns(connection: sqlite3.Connection) -> list[str]:
    try:
        rows = connection.execute("PRAGMA table_info(assessments)").fetchall()
        return [str(row[1]) for row in rows]
    except sqlite3.Error:
        return []


def _load_latest_assessment(user_id: int = 1) -> dict[str, Any] | None:
    """Load the latest compatible assessment without assuming one exact schema."""

    db = _find_database()
    if db is None:
        return None

    try:
        with sqlite3.connect(db) as connection:
            connection.row_factory = sqlite3.Row
            columns = _assessment_columns(connection)
            if not columns:
                return None

            where = "user_id = ?" if "user_id" in columns else "1 = 1"
            order_column = (
                "date"
                if "date" in columns
                else "created_at"
                if "created_at" in columns
                else "id"
                if "id" in columns
                else columns[0]
            )
            row = connection.execute(
                f"SELECT * FROM assessments WHERE {where} "
                f"ORDER BY {order_column} DESC LIMIT 1",
                (user_id,) if "user_id" in columns else (),
            ).fetchone()

            if row is None:
                return None

            raw = dict(row)

        return _normalize_assessment_row(raw)
    except sqlite3.Error:
        return None


def _first(row: dict[str, Any], names: tuple[str, ...], default: Any) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return default


def _normalize_assessment_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map common historical assessment column names to simulator inputs."""

    return {
        "transport": str(
            _first(row, ("transport", "transport_mode", "travel_mode"), "Car")
        ),
        "distance": float(
            _first(
                row,
                ("distance", "daily_distance", "distance_km", "daily_distance_km"),
                0,
            )
        ),
        "electricity": float(
            _first(
                row,
                (
                    "electricity",
                    "electricity_kwh",
                    "monthly_electricity",
                    "monthly_electricity_kwh",
                ),
                0,
            )
        ),
        "diet": str(_first(row, ("diet", "diet_type"), "Vegetarian")),
        "flights": int(
            float(
                _first(
                    row,
                    ("flights", "annual_flights", "flight_count"),
                    0,
                )
            )
        ),
        "region": str(_first(row, ("region", "country_region"), "Global")),
    }


def _render_metric_summary(baseline: dict[str, Any], result: Any) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Baseline", f"{result.baseline_total_kg:,.0f} kg")
    c2.metric(
        "Scenario",
        f"{result.scenario_total_kg:,.0f} kg",
        delta=f"{result.absolute_change_kg:,.0f} kg",
    )
    c3.metric("Estimated reduction", f"{result.reduction_kg:,.0f} kg")
    c4.metric("Change", f"{result.reduction_percent:.1f}%")


def _scenario_selector() -> ScenarioDefinition:
    scenarios = list(default_scenarios())
    labels = {scenario.name: scenario for scenario in scenarios}
    choice = st.selectbox(
        "Scenario",
        list(labels),
        help="These are modeled what-if scenarios. They never overwrite the assessment.",
    )
    return labels[choice]


def _custom_builder() -> ScenarioDefinition:
    st.subheader("Build a custom scenario")
    st.caption(
        "Create a hypothetical combination. Values are applied to a copy of the "
        "assessment and are never saved as a real assessment."
    )

    selected_fields = st.multiselect(
        "Inputs to change",
        ["distance", "electricity", "flights", "transport", "diet"],
        default=["distance"],
    )

    changes: list[ScenarioChange] = []
    labels = {
        "distance": ("Distance", "km/day"),
        "electricity": ("Electricity", "kWh/month"),
        "flights": ("Annual flights", "flights/year"),
        "transport": ("Transport", "mode"),
        "diet": ("Diet", "category"),
    }

    for field in selected_fields:
        title, unit = labels[field]
        if field in {"distance", "electricity", "flights"}:
            operation = st.selectbox(
                f"{title} operation",
                ["percent", "absolute"],
                key=f"operation_{field}",
            )
            if operation == "percent":
                value = st.number_input(
                    f"{title} change (%)",
                    min_value=-100.0,
                    max_value=100.0,
                    value=-20.0,
                    step=5.0,
                    key=f"value_{field}_percent",
                )
            else:
                value = st.number_input(
                    f"New {title}",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key=f"value_{field}_absolute",
                )
        else:
            options = (
                ["Car", "Bike", "Public Transport", "Walking"]
                if field == "transport"
                else ["Vegetarian", "Non-Vegetarian"]
            )
            operation = "set"
            value = st.selectbox(
                f"New {title}",
                options,
                key=f"value_{field}_set",
            )

        changes.append(
            ScenarioChange(
                field=field,
                operation=operation,
                value=value,
                label=f"{title}: {operation} {value}",
                unit=unit,
            )
        )

    if not changes:
        raise ScenarioValidationError("Select at least one input to change.")

    return ScenarioDefinition(
        id="custom-scenario",
        name="Custom scenario",
        description="User-defined what-if scenario.",
        changes=tuple(changes),
        tags=("custom",),
    )


def main() -> None:
    st.title("🔬 Sustainability Scenario Simulator")
    st.write(
        "Explore hypothetical behavior changes before making them in real life. "
        "Every result is a **modeled projection** and your assessment history is "
        "**never modified**."
    )

    latest = _load_latest_assessment(
        int(st.session_state.get("user_id", 1) or 1)
    )

    if latest is None:
        st.info(
            "No saved assessment was found. Enter a baseline below to explore scenarios."
        )
        latest = {
            "transport": "Car",
            "distance": 20.0,
            "electricity": 250.0,
            "diet": "Non-Vegetarian",
            "flights": 2,
            "region": "Global",
        }

    with st.expander("Baseline assessment inputs", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            transport = st.selectbox(
                "Transport",
                ["Car", "Bike", "Public Transport", "Walking"],
                index=(
                    ["Car", "Bike", "Public Transport", "Walking"].index(
                        latest["transport"]
                    )
                    if latest["transport"]
                    in ["Car", "Bike", "Public Transport", "Walking"]
                    else 0
                ),
            )
            distance = st.number_input(
                "Daily distance (km)",
                min_value=0.0,
                value=float(latest["distance"]),
                step=1.0,
            )
        with col2:
            electricity = st.number_input(
                "Monthly electricity (kWh)",
                min_value=0.0,
                value=float(latest["electricity"]),
                step=10.0,
            )
            flights = st.number_input(
                "Annual flights",
                min_value=0,
                value=int(latest["flights"]),
                step=1,
            )
        with col3:
            diets = ["Vegetarian", "Non-Vegetarian"]
            diet = st.selectbox(
                "Diet",
                diets,
                index=diets.index(latest["diet"]) if latest["diet"] in diets else 0,
            )
            region = st.text_input("Region", value=str(latest["region"] or "Global"))

    baseline = {
        "transport": transport,
        "distance": distance,
        "electricity": electricity,
        "diet": diet,
        "flights": flights,
        "region": region or "Global",
    }

    try:
        if st.button("Calculate baseline", type="secondary"):
            st.session_state["scenario_baseline"] = baseline

        baseline_result = simulate_scenario(
            baseline,
            make_percentage_scenario(
                "baseline-noop",
                "Baseline",
                "distance",
                0,
            ),
        )
    except Exception as exc:
        st.error(f"Unable to calculate the baseline: {exc}")
        return

    st.divider()
    st.subheader("Quick what-if scenarios")

    try:
        results = run_default_scenarios(baseline)
    except Exception as exc:
        st.error(f"Scenario engine error: {exc}")
        return

    cards = st.columns(min(3, len(results)))
    for index, result in enumerate(results):
        with cards[index % len(cards)]:
            direction = "↓" if result.reduction_kg >= 0 else "↑"
            st.metric(
                result.scenario_name,
                f"{result.scenario_total_kg:,.0f} kg",
                delta=f"{direction} {abs(result.reduction_kg):,.0f} kg",
            )
            st.caption(f"{result.reduction_percent:+.1f}% vs baseline")

    st.divider()
    st.subheader("Detailed scenario analysis")

    mode = st.radio(
        "Scenario mode",
        ["Preset", "Custom", "Combined"],
        horizontal=True,
    )

    try:
        if mode == "Preset":
            scenario = _scenario_selector()
        elif mode == "Custom":
            scenario = _custom_builder()
        else:
            preset_map = {scenario.name: scenario for scenario in default_scenarios()}
            chosen = st.multiselect(
                "Combine presets",
                list(preset_map),
                default=list(preset_map)[:2],
            )
            if not chosen:
                st.warning("Choose at least one preset.")
                return
            scenario = combine_scenarios(
                "combined",
                "Combined scenario",
                [preset_map[name] for name in chosen],
                description="Combined hypothetical changes.",
            )

        result = simulate_scenario(baseline, scenario)
    except ScenarioValidationError as exc:
        st.warning(str(exc))
        return
    except Exception as exc:
        st.error(f"Could not evaluate scenario: {exc}")
        return

    _render_metric_summary(baseline_result.to_dict(), result)

    if result.reduction_kg > 0:
        st.success(
            f"Modeled reduction: {result.reduction_kg:,.2f} kg CO2/year "
            f"({result.reduction_percent:.2f}%)."
        )
    elif result.reduction_kg < 0:
        st.warning(
            f"This scenario models an increase of "
            f"{abs(result.reduction_kg):,.2f} kg CO2/year."
        )
    else:
        st.info("This scenario produces no modeled change.")

    for message in explain_change(result):
        st.caption(message)

    st.subheader("Category impact")
    table = pd.DataFrame(category_contribution_table(result))
    if not table.empty:
        st.dataframe(table, use_container_width=True, hide_index=True)

        chart = table.set_index("category")[["baseline_kg", "scenario_kg"]]
        st.bar_chart(chart)

    st.subheader("Input changes")
    st.dataframe(
        pd.DataFrame(result.changes),
        use_container_width=True,
        hide_index=True,
    )

    if result.warnings:
        with st.expander("Validation warnings"):
            for warning in result.warnings:
                st.warning(warning)

    st.download_button(
        "Download scenario JSON",
        data=export_result(result),
        file_name=f"scenario-{result.result_id}.json",
        mime="application/json",
    )

    st.divider()
    st.subheader("Compare all presets")

    comparison = compare_scenarios(results)
    ranked = sorted(
        results,
        key=lambda item: (item.reduction_kg, -item.scenario_total_kg),
        reverse=True,
    )
    ranking_table = pd.DataFrame(
        [
            {
                "Scenario": item.scenario_name,
                "Scenario footprint (kg)": item.scenario_total_kg,
                "Reduction (kg)": item.reduction_kg,
                "Reduction (%)": item.reduction_percent,
                "Direction": item.direction,
            }
            for item in ranked
        ]
    )
    st.dataframe(ranking_table, use_container_width=True, hide_index=True)

    if comparison.best_reduction_id:
        st.info(
            f"Highest modeled reduction among presets: "
            f"**{next(r.scenario_name for r in results if r.scenario_id == comparison.best_reduction_id)}**."
        )

    st.download_button(
        "Download preset comparison",
        data=export_comparison(comparison),
        file_name="scenario-comparison.json",
        mime="application/json",
    )

    st.divider()
    st.subheader("Sensitivity analysis")

    sensitivity_field = st.selectbox(
        "Input",
        ["distance", "electricity", "flights"],
    )
    baseline_value = float(baseline[sensitivity_field])

    if sensitivity_field == "distance":
        values = [round(max(0, baseline_value * factor), 2) for factor in (0, .25, .5, .75, 1)]
        unit = "km/day"
    elif sensitivity_field == "electricity":
        values = [round(max(0, baseline_value * factor), 2) for factor in (0, .25, .5, .75, 1)]
        unit = "kWh/month"
    else:
        values = sorted(
            set(
                max(0, int(round(baseline_value + delta)))
                for delta in (-3, -2, -1, 0, 1, 2, 3)
            )
        )
        unit = "flights/year"

    points = sensitivity_analysis(baseline, sensitivity_field, values)
    sensitivity_table = pd.DataFrame(
        [
            {
                "Value": point.value,
                f"Total (kg)": point.total_kg,
                "Reduction (kg)": point.reduction_kg,
                "Reduction (%)": point.reduction_percent,
                "Valid": point.valid,
            }
            for point in points
        ]
    )
    st.caption(f"Sensitivity values shown in {unit}.")
    st.dataframe(sensitivity_table, use_container_width=True, hide_index=True)

    valid_points = [point for point in points if point.valid]
    if valid_points:
        chart = pd.DataFrame(
            {
                "value": [point.value for point in valid_points],
                "total_kg": [point.total_kg for point in valid_points],
            }
        ).set_index("value")
        st.line_chart(chart)

    st.caption(
        "Scenario results are estimates. They are not guarantees of future savings, "
        "and they do not create a new assessment or alter historical records."
    )


if __name__ == "__main__":
    main()
