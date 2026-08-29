"""Tests for the Sustainability Scenario Simulation engine (#1296)."""

from __future__ import annotations

import json
import math

import pytest

from sustainability_scenarios import (
    ScenarioChange,
    ScenarioDefinition,
    ScenarioValidationError,
    apply_change,
    apply_changes,
    build_custom_scenario,
    category_contribution_table,
    combine_scenarios,
    compare_scenarios,
    copy_assessment_inputs,
    default_scenarios,
    export_comparison,
    export_result,
    explain_change,
    make_percentage_scenario,
    make_set_scenario,
    rank_scenarios,
    safe_scenario,
    sensitivity_analysis,
    simulate_scenario,
    validate_result,
)


BASELINE = {
    "transport": "Car",
    "distance": 20,
    "electricity": 250,
    "diet": "Non-Vegetarian",
    "flights": 2,
    "region": "Global",
}


def test_copy_isolated_from_original():
    original = dict(BASELINE)
    copied = copy_assessment_inputs(original)
    copied["distance"] = 99
    assert original["distance"] == 20


def test_percentage_change_reduces_numeric_value():
    changed, warnings = apply_change(
        BASELINE,
        ScenarioChange("distance", "percent", -30),
    )
    assert changed["distance"] == pytest.approx(14)
    assert warnings is None


def test_percentage_change_increases_numeric_value():
    changed, _ = apply_change(
        BASELINE,
        ScenarioChange("electricity", "percent", 20),
    )
    assert changed["electricity"] == pytest.approx(300)


def test_flight_percentage_is_rounded_to_whole_number():
    changed, _ = apply_change(
        BASELINE,
        ScenarioChange("flights", "percent", -50),
    )
    assert changed["flights"] == 1
    assert isinstance(changed["flights"], int)


def test_negative_absolute_value_is_rejected():
    with pytest.raises(ScenarioValidationError):
        apply_change(BASELINE, ScenarioChange("distance", "absolute", -1))


def test_categorical_percent_change_is_rejected():
    with pytest.raises(ScenarioValidationError):
        ScenarioChange("transport", "percent", -20)


def test_transport_switch():
    changed, warning = apply_change(
        BASELINE,
        ScenarioChange("transport", "set", "Public Transport"),
    )
    assert changed["transport"] == "Public Transport"
    assert warning is None


def test_diet_switch():
    changed, _ = apply_change(
        BASELINE,
        ScenarioChange("diet", "set", "Vegetarian"),
    )
    assert changed["diet"] == "Vegetarian"


def test_multiple_changes_apply_to_one_copy():
    result, warnings = apply_changes(
        BASELINE,
        (
            ScenarioChange("distance", "percent", -30),
            ScenarioChange("electricity", "percent", -20),
        ),
    )
    assert result["distance"] == pytest.approx(14)
    assert result["electricity"] == pytest.approx(200)
    assert warnings == []


def test_duplicate_field_change_is_rejected():
    with pytest.raises(ScenarioValidationError):
        apply_changes(
            BASELINE,
            (
                ScenarioChange("distance", "percent", -10),
                ScenarioChange("distance", "percent", -20),
            ),
        )


def test_scenario_definition_requires_changes():
    with pytest.raises(ScenarioValidationError):
        ScenarioDefinition("x", "Empty", "bad", ())


def test_default_scenarios_cover_required_use_cases():
    ids = {scenario.id for scenario in default_scenarios()}
    assert "car-minus-30" in ids
    assert "public-transport" in ids
    assert "electricity-minus-20" in ids
    assert "vegetarian-diet" in ids
    assert "flights-minus-50" in ids


def test_baseline_is_calculated_by_canonical_engine():
    scenario = make_percentage_scenario(
        "car-test",
        "Car reduction",
        "distance",
        -30,
    )
    result = simulate_scenario(BASELINE, scenario)
    assert result.baseline_total_kg > 0
    assert result.scenario_total_kg >= 0
    assert math.isfinite(result.reduction_kg)


def test_car_reduction_has_positive_reduction_for_car_baseline():
    scenario = make_percentage_scenario(
        "car-test",
        "Car reduction",
        "distance",
        -30,
    )
    result = simulate_scenario(BASELINE, scenario)
    assert result.reduction_kg > 0


def test_electricity_reduction_changes_electricity_category():
    scenario = make_percentage_scenario(
        "energy-test",
        "Energy reduction",
        "electricity",
        -20,
    )
    result = simulate_scenario(BASELINE, scenario)
    assert result.category_changes["Electricity"] > 0


def test_transport_switch_changes_transport_category():
    scenario = make_set_scenario(
        "pt",
        "Public transport",
        "transport",
        "Public Transport",
    )
    result = simulate_scenario(BASELINE, scenario)
    assert result.scenario_inputs["transport"] == "Public Transport"
    assert "Transport" in result.category_changes


def test_diet_switch_changes_diet_category():
    scenario = make_set_scenario(
        "veg",
        "Vegetarian",
        "diet",
        "Vegetarian",
    )
    result = simulate_scenario(BASELINE, scenario)
    assert result.scenario_inputs["diet"] == "Vegetarian"
    assert "Diet" in result.category_changes


def test_combined_scenario_supports_multiple_changes():
    first = make_percentage_scenario("a", "Distance", "distance", -30)
    second = make_percentage_scenario("b", "Energy", "electricity", -20)
    combined = combine_scenarios("combined", "Both", [first, second])
    result = simulate_scenario(BASELINE, combined)
    assert result.scenario_inputs["distance"] == pytest.approx(14)
    assert result.scenario_inputs["electricity"] == pytest.approx(200)
    assert result.reduction_kg > 0


def test_combined_scenario_rejects_duplicate_fields():
    first = make_percentage_scenario("a", "Distance", "distance", -30)
    second = make_percentage_scenario("b", "Distance", "distance", -10)
    with pytest.raises(ScenarioValidationError):
        combine_scenarios("combined", "Both", [first, second])


def test_rank_scenarios_orders_by_reduction():
    results = [
        simulate_scenario(
            BASELINE,
            make_percentage_scenario("a", "Small", "distance", -10),
        ),
        simulate_scenario(
            BASELINE,
            make_percentage_scenario("b", "Large", "distance", -50),
        ),
    ]
    ranked = rank_scenarios(results)
    assert ranked[0].reduction_kg >= ranked[1].reduction_kg


def test_rank_can_be_ascending():
    results = [
        simulate_scenario(
            BASELINE,
            make_percentage_scenario("a", "Small", "distance", -10),
        ),
        simulate_scenario(
            BASELINE,
            make_percentage_scenario("b", "Large", "distance", -50),
        ),
    ]
    ranked = rank_scenarios(results, descending=False)
    assert ranked[0].reduction_kg <= ranked[1].reduction_kg


def test_compare_scenarios_identifies_best():
    results = [
        simulate_scenario(
            BASELINE,
            make_percentage_scenario("a", "Small", "distance", -10),
        ),
        simulate_scenario(
            BASELINE,
            make_percentage_scenario("b", "Large", "distance", -50),
        ),
    ]
    comparison = compare_scenarios(results)
    assert comparison.best_reduction_id == "b"
    assert comparison.lowest_total_id == "b"


def test_compare_empty_is_safe():
    comparison = compare_scenarios([])
    assert comparison.results == ()
    assert comparison.best_reduction_id is None


def test_sensitivity_returns_stable_curve():
    points = sensitivity_analysis(BASELINE, "distance", [0, 5, 10, 15, 20])
    assert len(points) == 5
    assert all(point.valid for point in points)
    assert points[0].value == 0
    assert points[-1].value == 20


def test_sensitivity_rejects_categorical_fields():
    with pytest.raises(ScenarioValidationError):
        sensitivity_analysis(BASELINE, "transport", [1, 2, 3])


def test_sensitivity_marks_negative_values_invalid():
    points = sensitivity_analysis(BASELINE, "distance", [-1, 0, 1])
    assert points[0].valid is False
    assert points[1].valid is True


def test_result_reconciles():
    result = simulate_scenario(
        BASELINE,
        make_percentage_scenario("a", "Distance", "distance", -20),
    )
    assert validate_result(result) == []


def test_result_source_is_explicitly_modeled():
    result = simulate_scenario(
        BASELINE,
        make_percentage_scenario("a", "Distance", "distance", -20),
    )
    assert result.source == "MODELED_WHAT_IF"
    assert result.engine_version == "1.0"


def test_result_has_deterministic_result_id():
    scenario = make_percentage_scenario("a", "Distance", "distance", -20)
    first = simulate_scenario(BASELINE, scenario)
    second = simulate_scenario(BASELINE, scenario)
    assert first.result_id == second.result_id


def test_category_table_contains_before_after_and_change():
    result = simulate_scenario(
        BASELINE,
        make_percentage_scenario("a", "Distance", "distance", -20),
    )
    rows = category_contribution_table(result)
    assert rows
    assert {"category", "baseline_kg", "scenario_kg", "change_kg"} <= set(rows[0])


def test_explanation_is_transparent_about_projection():
    result = simulate_scenario(
        BASELINE,
        make_percentage_scenario("a", "Distance", "distance", -20),
    )
    messages = explain_change(result)
    assert any("projection" in message.lower() for message in messages)


def test_export_result_is_valid_json():
    result = simulate_scenario(
        BASELINE,
        make_percentage_scenario("a", "Distance", "distance", -20),
    )
    payload = json.loads(export_result(result))
    assert payload["scenario_id"] == "a"
    assert payload["source"] == "MODELED_WHAT_IF"


def test_export_comparison_is_valid_json():
    result = simulate_scenario(
        BASELINE,
        make_percentage_scenario("a", "Distance", "distance", -20),
    )
    comparison = compare_scenarios([result])
    payload = json.loads(export_comparison(comparison))
    assert payload["results"][0]["scenario_id"] == "a"


def test_custom_scenario_builder():
    scenario = build_custom_scenario(
        scenario_id="custom",
        name="Custom",
        changes=[
            {"field": "distance", "operation": "percent", "value": -25},
            {"field": "electricity", "operation": "percent", "value": -10},
        ],
    )
    assert len(scenario.changes) == 2


def test_safe_scenario_returns_valid_result_for_normal_input():
    result = safe_scenario(
        BASELINE,
        make_percentage_scenario("safe", "Safe", "distance", -10),
    )
    assert result.valid is True


@pytest.mark.parametrize(
    "field",
    ["transport", "distance", "electricity", "diet", "flights", "region"],
)
def test_supported_fields_are_accepted(field):
    value = BASELINE[field]
    if field in {"distance", "electricity"}:
        change = ScenarioChange(field, "absolute", value)
    elif field == "flights":
        change = ScenarioChange(field, "absolute", value)
    else:
        change = ScenarioChange(field, "set", value)
    changed, _ = apply_change(BASELINE, change)
    assert changed[field] == value


def test_original_input_is_not_mutated_by_simulation():
    original = dict(BASELINE)
    simulate_scenario(
        original,
        make_percentage_scenario("a", "Distance", "distance", -20),
    )
    assert original == BASELINE


def test_zero_baseline_percent_is_safe():
    zero = dict(BASELINE)
    zero["distance"] = 0
    zero["electricity"] = 0
    zero["flights"] = 0
    zero["diet"] = "Vegetarian"
    # Diet still contributes, so the denominator remains non-zero.
    result = simulate_scenario(
        zero,
        make_percentage_scenario("a", "Distance", "distance", -20),
    )
    assert math.isfinite(result.reduction_percent)
