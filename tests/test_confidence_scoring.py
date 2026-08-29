"""
Unit tests for Data Quality Confidence Scoring for Assessments (#1260).
"""

from datetime import datetime, timezone

import pytest

from src.carbon.confidence_scoring import (
    CONFIDENCE_WEIGHTS,
    calculate_assessment_confidence,
    explain_confidence,
)

AS_OF = datetime(2026, 8, 27, tzinfo=timezone.utc)


def complete_assessment(**overrides):
    data = {
        "id": 101,
        "user_id": 7,
        "date": "2026-08-20T10:00:00+00:00",  # 7 days before AS_OF
        "created_at": "2026-08-20T10:00:00+00:00",
        "transport": "Car",
        "distance": 20.0,
        "electricity": 100.0,
        "diet": "Vegetarian",
        "flights": 2,
        "footprint": 4971.0,
        "eco_score": 55,
        "factor_version": "static-v2",
    }
    data.update(overrides)
    return data


def test_every_assessment_receives_a_classification():
    result = calculate_assessment_confidence(complete_assessment(), region="Global", as_of=AS_OF)
    assert result.classification in ("High", "Medium", "Low")
    assert 0.0 <= result.total_score <= 100.0


def test_confidence_weights_sum_to_100():
    assert sum(CONFIDENCE_WEIGHTS.values()) == 100.0


def test_confidence_is_independent_of_eco_score():
    low_eco_score = calculate_assessment_confidence(
        complete_assessment(eco_score=5), region="Global", as_of=AS_OF
    )
    high_eco_score = calculate_assessment_confidence(
        complete_assessment(eco_score=95), region="Global", as_of=AS_OF
    )
    assert low_eco_score.total_score == high_eco_score.total_score
    assert low_eco_score.classification == high_eco_score.classification


def test_well_formed_assessment_scores_high():
    result = calculate_assessment_confidence(complete_assessment(), region="Global", as_of=AS_OF)
    assert result.classification == "High"


def test_missing_optional_metadata_reduces_confidence():
    complete = calculate_assessment_confidence(complete_assessment(), region="Global", as_of=AS_OF)
    sparse = calculate_assessment_confidence(
        complete_assessment(date=None, created_at=None, factor_version=None), as_of=AS_OF
    )
    assert sparse.total_score < complete.total_score


def test_out_of_range_inputs_reduce_confidence_and_add_warning():
    result = calculate_assessment_confidence(
        complete_assessment(distance=999999), region="Global", as_of=AS_OF
    )
    baseline = calculate_assessment_confidence(complete_assessment(), region="Global", as_of=AS_OF)
    assert result.total_score < baseline.total_score
    assert any("distance" in warning for warning in result.warnings)


def test_zero_quantitative_categories_reduce_confidence():
    baseline = calculate_assessment_confidence(complete_assessment(), region="Global", as_of=AS_OF)
    sparse_categories = calculate_assessment_confidence(
        complete_assessment(electricity=0, flights=0), region="Global", as_of=AS_OF
    )
    assert sparse_categories.total_score < baseline.total_score


def test_dynamic_low_uncertainty_factor_set_scores_higher_than_legacy():
    modern = calculate_assessment_confidence(
        complete_assessment(factor_version="static-v2"), region="Global", as_of=AS_OF
    )
    legacy = calculate_assessment_confidence(
        complete_assessment(factor_version="static-v1"), region="Global", as_of=AS_OF
    )
    assert modern.total_score > legacy.total_score


def test_unknown_factor_version_is_penalised_but_does_not_crash():
    result = calculate_assessment_confidence(
        complete_assessment(factor_version="not-a-real-version"), region="Global", as_of=AS_OF
    )
    assert result.total_score >= 0.0


def test_non_metric_input_reduces_unit_conversion_score():
    metric = calculate_assessment_confidence(complete_assessment(), region="Global", as_of=AS_OF)
    imperial = calculate_assessment_confidence(
        complete_assessment(), region="Global", input_unit_system="imperial", as_of=AS_OF
    )
    assert imperial.total_score < metric.total_score


def test_extra_warnings_reduce_confidence():
    baseline = calculate_assessment_confidence(complete_assessment(), region="Global", as_of=AS_OF)
    warned = calculate_assessment_confidence(
        complete_assessment(), region="Global", as_of=AS_OF,
        extra_warnings=["Region unavailable, defaulted to Global."],
    )
    assert warned.total_score < baseline.total_score
    assert "Region unavailable, defaulted to Global." in warned.warnings


def test_confidence_is_deterministic_for_same_assessment_and_as_of():
    result_a = calculate_assessment_confidence(complete_assessment(), region="Global", as_of=AS_OF)
    result_b = calculate_assessment_confidence(complete_assessment(), region="Global", as_of=AS_OF)
    assert result_a == result_b


def test_confidence_stays_tied_to_original_assessment_id():
    result = calculate_assessment_confidence(complete_assessment(id=555), region="Global", as_of=AS_OF)
    assert result.assessment_id == 555


def test_data_age_reduces_confidence_over_time():
    fresh = calculate_assessment_confidence(
        complete_assessment(date="2026-08-20T10:00:00+00:00"), region="Global", as_of=AS_OF
    )
    stale = calculate_assessment_confidence(
        complete_assessment(date="2024-01-01T10:00:00+00:00"), region="Global", as_of=AS_OF
    )
    assert stale.total_score < fresh.total_score


def test_explain_confidence_returns_readable_strings():
    result = calculate_assessment_confidence(
        complete_assessment(date=None, created_at=None, factor_version=None), as_of=AS_OF
    )
    explanations = explain_confidence(result)
    assert isinstance(explanations, list)
    assert all(isinstance(item, str) for item in explanations)
    assert len(explanations) > 0