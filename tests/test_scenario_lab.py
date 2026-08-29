"""Tests for the Carbon Footprint Scenario Lab engine."""

import json

import pytest

from src.utils.scenario_lab import (
    SCENARIO_PRESETS,
    ScenarioInput,
    ScenarioResult,
    ScenarioValidationError,
    apply_preset,
    calculate_category_deltas,
    calculate_scenario,
    compare_multiple_scenarios,
    compare_scenario_to_baseline,
    create_scenario,
    deserialize_scenario,
    find_best_single_change,
    rank_scenarios,
    serialize_scenario,
    summarize_scenario,
)


BASELINE = {
    "transport": "Car",
    "distance": 10.0,
    "electricity": 200.0,
    "diet": "Vegetarian",
    "flights": 2,
    "region": "Global",
}


def result(name="Baseline", **overrides):
    scenario = create_scenario(BASELINE, name, **overrides)
    return calculate_scenario(scenario)


def test_create_scenario_preserves_baseline_values():
    scenario = create_scenario(BASELINE, "Copy")
    assert scenario.name == "Copy"
    assert scenario.transport == "Car"
    assert scenario.distance == 10.0
    assert scenario.electricity == 200.0
    assert scenario.diet == "Vegetarian"
    assert scenario.flights == 2
    assert scenario.region == "Global"


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("distance", -1, "distance"),
        ("electricity", -1, "electricity"),
        ("flights", -1, "flights"),
    ],
)
def test_negative_values_are_rejected(field, value, message):
    with pytest.raises(ScenarioValidationError, match=message):
        create_scenario(BASELINE, "Invalid", **{field: value})


def test_empty_name_is_rejected():
    with pytest.raises(ScenarioValidationError, match="name"):
        create_scenario(BASELINE, "   ")


def test_invalid_region_is_rejected():
    with pytest.raises(ScenarioValidationError, match="Invalid region"):
        create_scenario(BASELINE, "Invalid", region="Mars")


def test_distance_boundary_is_enforced():
    valid = create_scenario(BASELINE, "Max", distance=500)
    assert valid.distance == 500

    with pytest.raises(ScenarioValidationError, match="cannot exceed"):
        create_scenario(BASELINE, "Too far", distance=500.1)


def test_electricity_boundary_is_enforced():
    valid = create_scenario(BASELINE, "Max", electricity=10000)
    assert valid.electricity == 10000

    with pytest.raises(ScenarioValidationError, match="cannot exceed"):
        create_scenario(BASELINE, "Too much", electricity=10000.1)


def test_flight_boundary_is_enforced():
    valid = create_scenario(BASELINE, "Max", flights=365)
    assert valid.flights == 365

    with pytest.raises(ScenarioValidationError, match="cannot exceed"):
        create_scenario(BASELINE, "Too many", flights=366)


def test_calculation_reuses_canonical_emissions_engine():
    baseline = result()
    lower_distance = result("Less driving", distance=5)

    assert baseline.footprint > lower_distance.footprint
    assert baseline.contributors["Transport"] > lower_distance.contributors["Transport"]
    assert lower_distance.eco_score >= baseline.eco_score


def test_category_deltas_are_scenario_minus_baseline():
    deltas = calculate_category_deltas(
        {"Transport": 100, "Food": 50},
        {"Transport": 75, "Food": 80, "Flights": 10},
    )
    assert deltas == {"Flights": 10, "Food": 30, "Transport": -25}


def test_comparison_reports_reduction_correctly():
    baseline = result()
    scenario = result("Less driving", distance=5)
    comparison = compare_scenario_to_baseline(baseline, scenario)

    assert comparison.footprint_delta < 0
    assert comparison.reduction > 0
    assert comparison.percentage_change < 0
    assert comparison.eco_score_delta >= 0
    assert comparison.largest_improvement_category == "Transport"
    assert comparison.is_reduction is True


def test_comparison_reports_increased_categories():
    baseline = result()
    scenario = result("More driving", distance=20)
    comparison = compare_scenario_to_baseline(baseline, scenario)

    assert comparison.footprint_delta > 0
    assert comparison.reduction == 0
    assert "Transport" in comparison.increased_categories


def test_zero_baseline_percentage_is_safe():
    zero_result = ScenarioResult(
        scenario=ScenarioInput(
            name="Zero",
            transport="Walking",
            distance=0,
            electricity=0,
            diet="Vegetarian",
            flights=0,
            region="Global",
        ),
        footprint=0.0,
        eco_score=100,
        contributors={},
        audit_log={},
    )
    higher = result("Higher", distance=1)
    comparison = compare_scenario_to_baseline(zero_result, higher)

    assert comparison.percentage_change == 100.0


def test_zero_baseline_to_zero_is_zero_percent():
    zero = ScenarioInput(
        name="Zero",
        transport="Walking",
        distance=0,
        electricity=0,
        diet="Vegetarian",
        flights=0,
        region="Global",
    )
    result_zero = calculate_scenario(zero)
    comparison = compare_scenario_to_baseline(result_zero, result_zero)

    assert comparison.percentage_change == 0.0
    assert comparison.reduction == 0


def test_presets_are_data_driven():
    assert SCENARIO_PRESETS
    scenario = apply_preset(BASELINE, "Reduce car distance by 50%")
    assert scenario.distance == 5.0


def test_combined_preset_applies_multiple_changes():
    scenario = apply_preset(BASELINE, "Combined transport + energy reduction")
    assert scenario.distance == 7.5
    assert scenario.electricity == 150.0


def test_preset_flights_rounds_to_integer():
    scenario = apply_preset(BASELINE, "Reduce annual flights by 25%")
    assert scenario.flights == 2


def test_unknown_preset_is_rejected():
    with pytest.raises(ScenarioValidationError, match="Unknown"):
        apply_preset(BASELINE, "does-not-exist")


def test_serialization_round_trip():
    original = create_scenario(BASELINE, "Serializable", distance=4.5, flights=3)
    payload = serialize_scenario(original)
    restored = deserialize_scenario(payload)

    assert restored == original
    assert json.loads(payload)["name"] == "Serializable"


def test_mapping_deserialization_round_trip():
    original = create_scenario(BASELINE, "Mapping")
    restored = deserialize_scenario(json.loads(serialize_scenario(original)))
    assert restored == original


def test_invalid_serialized_payload_is_rejected():
    with pytest.raises(ScenarioValidationError):
        deserialize_scenario('{"name": "bad"}')


def test_rank_scenarios_prefers_largest_reduction():
    baseline = result()
    small = result("Small", distance=9)
    large = result("Large", distance=4)
    ranked = rank_scenarios(baseline, [small, large])

    assert ranked[0][0].scenario.name == "Large"
    assert ranked[0][1].reduction > ranked[1][1].reduction


def test_rank_tie_breaks_deterministically_by_name():
    baseline = result()
    first = result("Alpha", distance=10)
    second = result("Beta", distance=10)
    ranked = rank_scenarios(baseline, [second, first])

    assert [item[0].scenario.name for item in ranked] == ["Alpha", "Beta"]


def test_compare_multiple_scenarios_has_ranked_rows():
    baseline = result()
    scenarios = [
        result("A", distance=9),
        result("B", distance=5),
    ]
    rows = compare_multiple_scenarios(baseline, scenarios)

    assert rows[0]["rank"] == 1
    assert rows[0]["name"] == "B"
    assert rows[1]["rank"] == 2
    assert set(rows[0]) >= {
        "rank",
        "name",
        "footprint_kg_co2e",
        "reduction_kg_co2e",
        "percentage_change",
        "eco_score",
    }


def test_best_single_change_ignores_non_reductions():
    baseline = result()
    increase = result("Increase", distance=20)
    reduction = result("Reduction", distance=5)

    assert find_best_single_change(baseline, [increase, reduction]).scenario.name == "Reduction"


def test_best_single_change_returns_none_when_no_reduction():
    baseline = result()
    same = result("Same", distance=10)

    assert find_best_single_change(baseline, [same]) is None


def test_summary_uses_increase_language_for_higher_footprint():
    baseline = result()
    scenario = result("More driving", distance=20)
    text = summarize_scenario(scenario, compare_scenario_to_baseline(baseline, scenario))

    assert "increases footprint" in text
    assert "saving" not in text.lower()


def test_scenario_calculation_does_not_mutate_baseline_mapping():
    baseline_copy = dict(BASELINE)
    create_scenario(baseline_copy, "Copy", distance=3)
    assert baseline_copy == BASELINE


def test_multiple_category_changes_are_tracked():
    baseline = result()
    scenario = result(
        "Combined",
        distance=5,
        electricity=100,
        flights=0,
        diet="Non-Vegetarian",
    )
    comparison = compare_scenario_to_baseline(baseline, scenario)

    assert comparison.category_deltas["Transport"] < 0
    assert comparison.category_deltas["Electricity"] < 0
    assert comparison.category_deltas["Flights"] < 0
    assert comparison.category_deltas["Diet"] > 0


def test_calculation_result_contains_audit_log():
    calculated = result("Audited")
    assert calculated.audit_log["inputs"]["daily_distance_km"] == 10.0
    assert "emission_factors" in calculated.audit_log
    assert calculated.audit_log["total_emissions_kg_co2"] == calculated.footprint


def test_scenario_result_serialization_contains_all_core_fields():
    calculated = result("Complete")
    payload = calculated.to_dict()

    assert payload["scenario"]["name"] == "Complete"
    assert payload["footprint"] == calculated.footprint
    assert payload["eco_score"] == calculated.eco_score
    assert payload["contributors"] == calculated.contributors


def test_scenario_name_is_trimmed():
    scenario = create_scenario(BASELINE, "  Trimmed  ")
    assert scenario.name == "Trimmed"


def test_non_numeric_input_is_rejected():
    with pytest.raises(ScenarioValidationError, match="distance"):
        create_scenario(BASELINE, "Bad", distance="not-a-number")


def test_invalid_transport_is_rejected():
    with pytest.raises(ScenarioValidationError, match="Invalid transport"):
        create_scenario(BASELINE, "Bad", transport="Rocket")


def test_invalid_diet_is_rejected():
    with pytest.raises(ScenarioValidationError, match="Invalid diet"):
        create_scenario(BASELINE, "Bad", diet="Only Air")


def test_original_assessment_result_is_unchanged_by_comparison():
    baseline = result()
    before = baseline.to_dict()
    scenario = result("Scenario", distance=3)

    compare_scenario_to_baseline(baseline, scenario)

    assert baseline.to_dict() == before
