import json

import pytest

from src.utils.assessment_explainability import (
    SOURCE_UNAVAILABLE,
    AssessmentAudit,
    CalculationStep,
    CalculationTrace,
    CategoryContribution,
    aggregate_category_contributions,
    audit_from_json,
    build_assessment_audit,
    build_calculation_trace,
    calculate_contribution,
    compare_audit_traces,
    normalize_assessment,
    serialize_audit,
    trace_category,
    trace_conversion,
    trace_factor,
    trace_input,
)
from src.carbon.emission_factors import DEFAULT_VERSION, get_factor_set


def assessment(**overrides):
    data = {
        "id": 101,
        "user_id": 7,
        "date": "2026-08-20T10:00:00+00:00",
        "created_at": "2026-08-20T10:00:00+00:00",
        "transport": "Car",
        "distance": 20.0,
        "electricity": 100.0,
        "diet": "Vegetarian",
        "flights": 2,
        "footprint": 4971.0,
        "eco_score": 55,
        "factor_version": "static-v1",
    }
    data.update(overrides)
    return data


def test_normalize_assessment_accepts_aliases_and_validates():
    result = normalize_assessment({
        "assessment_id": 1, "assessment_date": "today", "transport": "Car",
        "distance": "5", "electricity": 20, "diet": "Vegetarian", "flights": 0,
        "footprint": 100, "eco_score": 50,
    })
    assert result["id"] == 1
    assert result["distance"] == 5.0
    assert result["factor_version"] == DEFAULT_VERSION


@pytest.mark.parametrize("field", ["distance", "electricity", "flights"])
def test_invalid_numeric_inputs_are_rejected(field):
    data = assessment(**{field: -1})
    with pytest.raises(ValueError):
        normalize_assessment(data)


def test_missing_transport_is_rejected():
    with pytest.raises(ValueError):
        normalize_assessment(assessment(transport=""))


def test_trace_input_returns_units():
    assert trace_input(assessment(), "distance") == {"name": "distance", "value": 20.0, "unit": "km/day"}
    assert trace_input(assessment(), "electricity")["unit"] == "kWh/month"


def test_trace_input_rejects_unknown_name():
    with pytest.raises(ValueError):
        trace_input(assessment(), "unknown")


def test_trace_conversion_is_explicit_and_reproducible():
    step = trace_conversion("daily to annual", 20, "km/day", 7300, "km/year", 365)
    assert step.normalized_value == 7300
    assert "365" in step.calculation


def test_trace_factor_preserves_missing_source_honestly():
    factor = trace_factor(0.2, "kg CO2e/km")
    assert factor.source == SOURCE_UNAVAILABLE
    assert factor.value == 0.2


def test_calculate_contribution_is_deterministic():
    assert calculate_contribution(100, 0.2, 365) == 7300.0


def test_build_trace_uses_recorded_factor_set():
    trace = build_calculation_trace(assessment())
    assert trace.methodology_available is True
    assert trace.factor_version == "static-v1"
    assert len(trace.steps) == 4
    assert len(trace.conversions) == 2
    assert trace_category(trace, "Transportation")[0].factor == get_factor_set("static-v1")["factors"]["transport"]["Car"]


def test_trace_contains_inputs_factors_formulas_and_results():
    trace = build_calculation_trace(assessment())
    transport = trace_category(trace, "Transportation")[0]
    assert transport.input_value == 20.0
    assert transport.input_unit == "km/day"
    assert transport.normalized_value == 7300.0
    assert transport.factor_unit == "kg CO2e/km"
    assert transport.result == pytest.approx(7300 * get_factor_set("static-v1")["factors"]["transport"]["Car"])
    assert "×" in transport.calculation
    assert transport.source != SOURCE_UNAVAILABLE


def test_known_factor_set_reproduces_total():
    data = assessment()
    factors = get_factor_set("static-v1")["factors"]
    expected = (
        data["distance"] * 365 * factors["transport"][data["transport"]]
        + data["electricity"] * 12 * factors["electricity"]
        + factors["diet"][data["diet"]]
        + data["flights"] * factors["flight"]
    )
    assert build_calculation_trace(data).total_result == pytest.approx(expected)


def test_category_contributions_are_ranked_and_percentages_sum_to_100():
    audit = build_assessment_audit(assessment())
    assert [c.rank for c in audit.contributions] == [1, 2, 3, 4]
    assert sum(c.percentage for c in audit.contributions) == pytest.approx(100.0, abs=0.05)
    assert audit.contributions[0].result >= audit.contributions[-1].result


def test_zero_total_percentages_are_safe():
    trace = CalculationTrace(
        assessment_id=1, assessment_date=None, factor_version="x", methodology_available=True,
        steps=(CalculationStep("A", "x", 0, "u", 0, "u", 0, "f", "0", 0, "kg", "s", "x"),
               CalculationStep("B", "y", 0, "u", 0, "u", 0, "f", "0", 0, "kg", "s", "x")),
    )
    contributions = aggregate_category_contributions(trace)
    assert all(c.percentage == 0 for c in contributions)


def test_negative_contribution_does_not_crash():
    trace = CalculationTrace(
        assessment_id=1, assessment_date=None, factor_version="x", methodology_available=True,
        steps=(CalculationStep("A", "x", 1, "u", 1, "u", -1, "f", "-1", -1, "kg", "s", "x"),
               CalculationStep("B", "y", 2, "u", 2, "u", 2, "f", "4", 4, "kg", "s", "x")),
    )
    contributions = aggregate_category_contributions(trace)
    assert len(contributions) == 2
    assert any(c.result < 0 for c in contributions)


def test_unknown_factor_version_never_uses_current_factors():
    trace = build_calculation_trace(assessment(factor_version="future-v999"))
    assert trace.methodology_available is False
    assert trace.steps == ()
    assert SOURCE_UNAVAILABLE in trace.notes


def test_build_audit_flags_methodology_change():
    audit = build_assessment_audit(assessment(), current_factor_version="static-v2")
    assert audit.methodology_changed is True
    assert any("methodology changed" in note.lower() for note in audit.notes)


def test_build_audit_does_not_flag_same_methodology():
    audit = build_assessment_audit(assessment(), current_factor_version="static-v1")
    assert audit.methodology_changed is False


def test_factor_metadata_contains_provenance():
    audit = build_assessment_audit(assessment())
    assert audit.factor_metadata["available"] is True
    assert audit.factor_metadata["version"] == "static-v1"
    assert audit.factor_metadata["source"] != SOURCE_UNAVAILABLE
    assert audit.factor_metadata["fingerprint"]


def test_compare_detects_input_change():
    previous = build_assessment_audit(assessment(id=1, distance=10))
    current = build_assessment_audit(assessment(id=2, distance=20))
    result = compare_audit_traces(previous, current)
    assert result["input_changes"] >= 1
    transport = next(row for row in result["categories"] if row["category"] == "Transportation")
    assert transport["input_changed"] is True
    assert transport["factor_changed"] is False


def test_compare_detects_factor_change():
    previous = build_assessment_audit(assessment(id=1, factor_version="static-v1"))
    current = build_assessment_audit(assessment(id=2, factor_version="static-v2"))
    result = compare_audit_traces(previous, current)
    assert result["methodology_changed"] is True
    assert result["factor_changes"] >= 1


def test_compare_detects_unit_change():
    old_trace = CalculationTrace(
        assessment_id=1, assessment_date=None, factor_version="v1", methodology_available=True,
        steps=(CalculationStep("A", "x", 10, "km/day", 3650, "km/year", 0.1, "kg/km", "3650×0.1", 365, "kg", "s", "v1"),),
    )
    new_trace = CalculationTrace(
        assessment_id=2, assessment_date=None, factor_version="v1", methodology_available=True,
        steps=(CalculationStep("A", "x", 10, "mi/day", 3650, "mi/year", 0.1, "kg/km", "3650×0.1", 365, "kg", "s", "v1"),),
    )
    result = compare_audit_traces(old_trace, new_trace)
    assert result["unit_changes"] == 1


def test_compare_reports_total_change():
    previous = build_assessment_audit(assessment(id=1, distance=10))
    current = build_assessment_audit(assessment(id=2, distance=20))
    result = compare_audit_traces(previous, current)
    assert result["total_change"] > 0


def test_serialization_round_trip_preserves_audit():
    original = build_assessment_audit(assessment())
    payload = serialize_audit(original)
    restored = audit_from_json(payload)
    assert restored.assessment_id == original.assessment_id
    assert restored.factor_version == original.factor_version
    assert restored.trace.total_result == original.trace.total_result
    assert len(restored.contributions) == len(original.contributions)


def test_serialized_audit_is_valid_json():
    audit = build_assessment_audit(assessment())
    raw = json.loads(serialize_audit(audit))
    assert raw["factor_version"] == "static-v1"
    assert "trace" in raw
    assert "contributions" in raw


def test_audit_is_reproducible_for_same_snapshot():
    first = build_assessment_audit(assessment())
    second = build_assessment_audit(assessment())
    assert serialize_audit(first).replace(first.generated_at, "") == serialize_audit(second).replace(second.generated_at, "")


def test_audit_preserves_stored_result_when_reconstruction_differs():
    audit = build_assessment_audit(assessment(footprint=1234.5))
    assert audit.stored_footprint == 1234.5
    assert audit.trace.total_result != audit.stored_footprint
    assert any("differs from stored result" in note for note in audit.notes)


def test_source_unavailable_is_used_for_unknown_factor_metadata():
    audit = build_assessment_audit(assessment(factor_version="not-registered"))
    assert audit.factor_metadata["source"] == SOURCE_UNAVAILABLE
    assert audit.methodology_available is False


def test_category_trace_filters_case_insensitively():
    trace = build_calculation_trace(assessment())
    assert len(trace_category(trace, "energy")) == 1


def test_factor_metadata_is_serializable():
    audit = build_assessment_audit(assessment())
    raw = json.loads(serialize_audit(audit))
    json.dumps(raw)


def test_trace_result_handles_zero_flights():
    trace = build_calculation_trace(assessment(flights=0))
    flight = trace_category(trace, "Flights")[0]
    assert flight.result == 0


def test_trace_result_handles_zero_electricity():
    trace = build_calculation_trace(assessment(electricity=0))
    energy = trace_category(trace, "Energy")[0]
    assert energy.result == 0


def test_assessment_audit_is_dataclass():
    audit = build_assessment_audit(assessment())
    assert isinstance(audit, AssessmentAudit)
    assert all(isinstance(c, CategoryContribution) for c in audit.contributions)
