from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

import pytest

from src.utils.intervention_effectiveness import (
    ENGINE_VERSION,
    EvidenceLevel,
    InterventionStatus,
    OutcomeDirection,
    InterventionStore,
    ValidationError,
    analyze_intervention,
    build_summary,
    calculate_attribution_confidence,
    calculate_effectiveness_score,
    calculate_evidence_score,
    calculate_improvement_pct,
    calculate_measurement_consistency,
    calculate_percentage_change,
    calculate_target_attainment,
    compare_analyses,
    create_intervention,
    create_observation,
    determine_direction,
    export_summary_csv,
    serialize_intervention_bundle,
    validate_bundle,
)


def make_intervention(**overrides):
    values = dict(
        name="Cycle to work",
        category="Transportation",
        adopted_on="2026-01-10",
        baseline_start="2025-11-01",
        baseline_end="2025-12-31",
        observation_start="2026-01-11",
        observation_end="2026-03-31",
        metric="carbon",
        baseline_value=100.0,
        target_value=70.0,
        unit="kg CO2e",
        user_id=7,
        action_id="cycle-work",
    )
    values.update(overrides)
    return create_intervention(**values)


def make_observation(intervention, day, value, **kwargs):
    return create_observation(
        intervention,
        observed_on=day,
        value=value,
        **kwargs,
    )


def test_engine_version_is_present():
    assert ENGINE_VERSION


def test_create_intervention_normalizes_metric_alias():
    item = make_intervention(metric="CO2e")
    assert item.metric == "carbon"


def test_create_intervention_generates_stable_id():
    a = make_intervention()
    b = make_intervention()
    assert a.id == b.id


def test_create_intervention_rejects_missing_name():
    with pytest.raises(ValidationError):
        make_intervention(name="")


def test_create_intervention_rejects_negative_baseline():
    with pytest.raises(ValidationError):
        make_intervention(baseline_value=-1)


def test_create_intervention_rejects_overlapping_periods():
    with pytest.raises(ValidationError):
        make_intervention(
            baseline_start="2025-12-01",
            baseline_end="2026-01-20",
            observation_start="2026-01-11",
        )


def test_create_intervention_rejects_observation_before_adoption():
    with pytest.raises(ValidationError):
        make_intervention(
            adopted_on="2026-02-01",
            observation_start="2026-01-11",
        )


def test_create_intervention_rejects_invalid_status():
    with pytest.raises(ValidationError):
        make_intervention(status="invalid")


def test_create_observation_accepts_quality_range():
    item = make_intervention()
    obs = make_observation(item, "2026-01-15", 90, quality=0.75)
    assert obs.quality == 0.75


def test_create_observation_clamps_quality():
    item = make_intervention()
    assert make_observation(item, "2026-01-15", 90, quality=5).quality == 1
    assert make_observation(item, "2026-01-16", 90, quality=-2).quality == 0


def test_create_observation_rejects_outside_window():
    item = make_intervention()
    with pytest.raises(ValidationError):
        make_observation(item, "2026-04-01", 90)


def test_create_observation_rejects_negative_value():
    item = make_intervention()
    with pytest.raises(ValidationError):
        make_observation(item, "2026-01-15", -1)


def test_percentage_change_handles_zero_baseline():
    assert calculate_percentage_change(0, 0) == 0
    assert calculate_percentage_change(0, 10) is None


def test_reduction_metric_improvement_is_positive_when_value_falls():
    assert calculate_improvement_pct("carbon", 100, 80) == 20


def test_increase_metric_improvement_is_positive_when_value_rises():
    assert calculate_improvement_pct("eco_score", 50, 60) == 20


def test_direction_improved():
    assert determine_direction("carbon", 100, 80) == OutcomeDirection.IMPROVED


def test_direction_worsened():
    assert determine_direction("carbon", 100, 120) == OutcomeDirection.WORSENED


def test_direction_unchanged_within_tolerance():
    assert determine_direction("carbon", 100, 100.5) == OutcomeDirection.UNCHANGED


def test_direction_unknown_without_observation():
    assert determine_direction("carbon", 100, None) == OutcomeDirection.UNKNOWN


def test_target_attainment_for_reduction():
    assert calculate_target_attainment("carbon", 100, 70, 85) == pytest.approx(50)


def test_target_attainment_for_increase():
    assert calculate_target_attainment("eco_score", 50, 80, 65) == pytest.approx(50)


def test_target_attainment_is_bounded():
    assert calculate_target_attainment("carbon", 100, 70, 0) == 100
    assert calculate_target_attainment("carbon", 100, 70, 150) == 0


def test_target_attainment_is_none_without_target():
    assert calculate_target_attainment("carbon", 100, None, 80) is None


def test_measurement_consistency_empty():
    assert calculate_measurement_consistency([]) == 0


def test_measurement_consistency_single_observation():
    item = make_intervention()
    obs = make_observation(item, "2026-01-15", 80, quality=0.7)
    assert calculate_measurement_consistency([obs]) == pytest.approx(0.7)


def test_measurement_consistency_rewards_consistent_data():
    item = make_intervention()
    observations = [
        make_observation(item, "2026-01-15", 80),
        make_observation(item, "2026-01-20", 81),
        make_observation(item, "2026-01-25", 79),
    ]
    assert calculate_measurement_consistency(observations) > 0.9


def test_evidence_score_requires_baseline_and_observation():
    item = make_intervention()
    obs = make_observation(item, "2026-01-15", 80)
    assert calculate_evidence_score([obs], has_baseline=True) > 0


def test_evidence_score_increases_with_repeated_measurements():
    item = make_intervention()
    one = [make_observation(item, "2026-01-15", 80)]
    many = [
        make_observation(item, "2026-01-15", 80),
        make_observation(item, "2026-01-20", 81),
        make_observation(item, "2026-01-25", 79),
    ]
    assert calculate_evidence_score(many) > calculate_evidence_score(one)


def test_evidence_score_rewards_control_period():
    item = make_intervention()
    obs = [make_observation(item, "2026-01-15", 80)]
    assert calculate_evidence_score(obs, has_control=True) > calculate_evidence_score(obs)


def test_evidence_level_thresholds():
    from src.utils.intervention_effectiveness import evidence_level
    assert evidence_level(0) == EvidenceLevel.NONE
    assert evidence_level(0.3) == EvidenceLevel.LOW
    assert evidence_level(0.6) == EvidenceLevel.MODERATE
    assert evidence_level(0.9) == EvidenceLevel.HIGH


def test_attribution_confidence_is_bounded():
    assert 0 <= calculate_attribution_confidence(1, has_control=True) <= 1
    assert 0 <= calculate_attribution_confidence(0, confounder_count=20) <= 1


def test_effectiveness_score_is_bounded():
    score = calculate_effectiveness_score(
        OutcomeDirection.IMPROVED, 50, 100, 1, 1
    )
    assert 0 <= score <= 100


def test_effectiveness_score_for_worsening_is_zero():
    score = calculate_effectiveness_score(
        OutcomeDirection.WORSENED, -50, 0, 1, 1
    )
    assert score == 0


def test_analysis_with_no_observations_is_honest():
    item = make_intervention()
    result = analyze_intervention(item)
    assert result.observation_value is None
    assert result.direction == OutcomeDirection.UNKNOWN
    assert result.effectiveness_score == 0
    assert result.warnings


def test_analysis_detects_improvement():
    item = make_intervention()
    observations = [
        make_observation(item, "2026-01-15", 90),
        make_observation(item, "2026-02-15", 80),
        make_observation(item, "2026-03-15", 75),
    ]
    result = analyze_intervention(item, observations)
    assert result.direction == OutcomeDirection.IMPROVED
    assert result.improvement_pct == pytest.approx(18.3333333333)
    assert result.observation_count == 3
    assert result.trend_slope is not None


def test_analysis_detects_worsening():
    item = make_intervention()
    observations = [make_observation(item, "2026-01-15", 120)]
    result = analyze_intervention(item, observations)
    assert result.direction == OutcomeDirection.WORSENED
    assert result.improvement_pct < 0


def test_analysis_supports_eco_score_increase():
    item = make_intervention(metric="eco_score", baseline_value=50, target_value=80)
    observations = [make_observation(item, "2026-01-15", 70)]
    result = analyze_intervention(item, observations)
    assert result.direction == OutcomeDirection.IMPROVED
    assert result.improvement_pct == pytest.approx(40)


def test_analysis_uses_baseline_measurement_average():
    item = make_intervention(baseline_value=100)
    observations = [make_observation(item, "2026-01-15", 80)]
    result = analyze_intervention(
        item,
        observations,
        baseline_measurements=[100, 110, 90],
    )
    assert result.baseline_value == pytest.approx(100)


def test_analysis_target_attainment():
    item = make_intervention(target_value=60)
    observations = [make_observation(item, "2026-01-15", 80)]
    result = analyze_intervention(item, observations)
    assert result.target_attainment_pct == pytest.approx(50)


def test_analysis_records_confounders_as_limitations():
    item = make_intervention()
    obs = [make_observation(item, "2026-01-15", 80)]
    result = analyze_intervention(item, obs, confounders=["seasonality", "price change"])
    assert any("seasonality" in text for text in result.limitations)


def test_analysis_with_control_has_higher_attribution_confidence():
    item = make_intervention()
    obs = [make_observation(item, "2026-01-15", 80)]
    no_control = analyze_intervention(item, obs, has_control=False)
    control = analyze_intervention(item, obs, has_control=True)
    assert control.attribution_confidence > no_control.attribution_confidence


def test_analysis_fingerprint_changes_when_observation_changes():
    item = make_intervention()
    a = analyze_intervention(item, [make_observation(item, "2026-01-15", 80)])
    b = analyze_intervention(item, [make_observation(item, "2026-01-15", 70)])
    assert a.inputs_fingerprint != b.inputs_fingerprint


def test_analysis_json_is_serializable():
    item = make_intervention()
    result = analyze_intervention(item, [make_observation(item, "2026-01-15", 80)])
    payload = json.loads(result.to_json())
    assert payload["engine_version"] == ENGINE_VERSION
    assert payload["intervention_id"] == item.id


def test_bundle_round_trip_is_json():
    item = make_intervention()
    observations = [make_observation(item, "2026-01-15", 80)]
    analysis = analyze_intervention(item, observations)
    payload = json.loads(serialize_intervention_bundle(item, observations, analysis))
    assert payload["schema_version"] == "1.0"
    assert payload["intervention"]["id"] == item.id
    assert len(payload["observations"]) == 1


def test_bundle_validation_accepts_valid_payload():
    ok, errors = validate_bundle({
        "schema_version": "1.0",
        "intervention": {},
        "observations": [],
        "analysis": None,
    })
    assert ok
    assert errors == []


def test_bundle_validation_rejects_future_schema():
    ok, errors = validate_bundle({
        "schema_version": "9.0",
        "intervention": {},
        "observations": [],
    })
    assert not ok
    assert errors


def test_compare_analyses_requires_same_intervention():
    a = make_intervention(action_id="a", name="A")
    b = make_intervention(action_id="b", name="B")
    aa = analyze_intervention(a, [make_observation(a, "2026-01-15", 80)])
    bb = analyze_intervention(b, [make_observation(b, "2026-01-15", 80)])
    with pytest.raises(ValidationError):
        compare_analyses(aa, bb)


def test_compare_analyses_detects_effectiveness_change():
    item = make_intervention()
    first = analyze_intervention(item, [make_observation(item, "2026-01-15", 95)])
    second = analyze_intervention(item, [
        make_observation(item, "2026-01-15", 80),
        make_observation(item, "2026-02-15", 75),
        make_observation(item, "2026-03-15", 70),
    ])
    comparison = compare_analyses(first, second)
    assert comparison.effectiveness_change is not None
    assert comparison.evidence_change > 0


def test_store_creates_three_tables(tmp_path):
    store = InterventionStore(str(tmp_path / "interventions.db"))
    store.initialize()
    with sqlite3.connect(store.db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {
        store.TABLE_INTERVENTIONS,
        store.TABLE_OBSERVATIONS,
        store.TABLE_ANALYSES,
    }.issubset(tables)


def test_store_round_trip_intervention(tmp_path):
    store = InterventionStore(str(tmp_path / "interventions.db"))
    item = make_intervention()
    store.save_intervention(item)
    loaded = store.get_intervention(item.id)
    assert loaded is not None
    assert loaded.name == item.name
    assert loaded.user_id == "7"


def test_store_round_trip_observation(tmp_path):
    store = InterventionStore(str(tmp_path / "interventions.db"))
    item = make_intervention()
    store.save_intervention(item)
    obs = make_observation(item, "2026-01-15", 80)
    store.save_observation(obs)
    loaded = store.list_observations(item.id)
    assert len(loaded) == 1
    assert loaded[0].value == 80


def test_store_round_trip_analysis(tmp_path):
    store = InterventionStore(str(tmp_path / "interventions.db"))
    item = make_intervention()
    obs = make_observation(item, "2026-01-15", 80)
    analysis = analyze_intervention(item, [obs])
    store.save_bundle(item, [obs], analysis)
    loaded = store.latest_analysis(item.id)
    assert loaded is not None
    assert loaded.inputs_fingerprint == analysis.inputs_fingerprint


def test_store_save_bundle_is_transactional(tmp_path):
    store = InterventionStore(str(tmp_path / "interventions.db"))
    item = make_intervention()
    bad = make_observation(item, "2026-01-15", 80)
    # Deliberately create a second observation tied to a different intervention.
    other = make_intervention(action_id="other", name="Other")
    wrong = make_observation(other, "2026-01-15", 70)
    with pytest.raises(ValidationError):
        store.save_bundle(item, [bad, wrong])
    assert store.get_intervention(item.id) is None


def test_store_update_observation_is_idempotent(tmp_path):
    store = InterventionStore(str(tmp_path / "interventions.db"))
    item = make_intervention()
    store.save_intervention(item)
    first = make_observation(item, "2026-01-15", 80, observation_id="same")
    second = make_observation(item, "2026-01-15", 70, observation_id="same")
    store.save_observation(first)
    store.save_observation(second)
    assert len(store.list_observations(item.id)) == 1
    assert store.list_observations(item.id)[0].value == 70


def test_store_latest_analysis_returns_last_snapshot(tmp_path):
    store = InterventionStore(str(tmp_path / "interventions.db"))
    item = make_intervention()
    store.save_intervention(item)
    first = analyze_intervention(item, [make_observation(item, "2026-01-15", 95)])
    second = analyze_intervention(item, [make_observation(item, "2026-01-15", 75)])
    store.save_analysis(first)
    store.save_analysis(second)
    latest = store.latest_analysis(item.id)
    assert latest is not None
    assert latest.inputs_fingerprint == second.inputs_fingerprint


def test_store_delete_respects_user(tmp_path):
    store = InterventionStore(str(tmp_path / "interventions.db"))
    item = make_intervention(user_id=7)
    store.save_intervention(item)
    assert not store.delete_intervention(item.id, user_id=99)
    assert store.get_intervention(item.id) is not None
    assert store.delete_intervention(item.id, user_id=7)


def test_build_summary_counts_status_and_direction():
    a = make_intervention(action_id="a", name="A", status="completed")
    b = make_intervention(action_id="b", name="B", status="active")
    aa = analyze_intervention(a, [make_observation(a, "2026-01-15", 80)])
    bb = analyze_intervention(b, [make_observation(b, "2026-01-15", 120)])
    summary = build_summary([a, b], [aa, bb])
    assert summary.intervention_count == 2
    assert summary.completed_count == 1
    assert summary.improved_count == 1
    assert summary.worsened_count == 1


def test_build_summary_has_category_averages():
    a = make_intervention(action_id="a", name="A", category="Energy")
    b = make_intervention(action_id="b", name="B", category="Energy")
    aa = analyze_intervention(a, [make_observation(a, "2026-01-15", 80)])
    bb = analyze_intervention(b, [make_observation(b, "2026-01-15", 90)])
    summary = build_summary([a, b], [aa, bb])
    assert "Energy" in summary.category_effectiveness


def test_csv_export_has_header():
    item = make_intervention()
    analysis = analyze_intervention(item, [make_observation(item, "2026-01-15", 80)])
    csv_text = export_summary_csv([item], [analysis])
    assert "Intervention,Category,Status" in csv_text


def test_large_observation_history_is_supported():
    item = make_intervention(observation_end="2026-12-31")
    observations = [
        make_observation(
            item,
            date(2026, 1, 11) + timedelta(days=i),
            max(0, 100 - i * 0.1),
        )
        for i in range(100)
    ]
    result = analyze_intervention(item, observations)
    assert result.observation_count == 100
    assert result.trend_slope is not None


def test_large_intervention_portfolio_is_supported(tmp_path):
    store = InterventionStore(str(tmp_path / "portfolio.db"))
    items = [
        make_intervention(action_id=f"a{i}", name=f"Action {i}")
        for i in range(100)
    ]
    for item in items:
        store.save_intervention(item)
        store.save_observation(make_observation(item, "2026-01-15", 90))
    assert len(store.list_interventions(7)) == 100


def test_analysis_preserves_historical_engine_version():
    item = make_intervention()
    result = analyze_intervention(item, [make_observation(item, "2026-01-15", 80)])
    assert result.engine_version == ENGINE_VERSION


def test_analysis_does_not_claim_causality_without_control():
    item = make_intervention()
    result = analyze_intervention(item, [make_observation(item, "2026-01-15", 80)])
    assert any("observational" in text.lower() for text in result.limitations)


def test_analysis_recommends_more_evidence_when_sparse():
    item = make_intervention()
    result = analyze_intervention(item, [make_observation(item, "2026-01-15", 80)])
    assert any("evidence" in text.lower() for text in result.recommendations)


def test_summary_with_empty_inputs():
    summary = build_summary([], [])
    assert summary.intervention_count == 0
    assert summary.average_effectiveness == 0


def test_bundle_contains_analysis_when_supplied():
    item = make_intervention()
    observations = [make_observation(item, "2026-01-15", 80)]
    analysis = analyze_intervention(item, observations)
    payload = json.loads(serialize_intervention_bundle(item, observations, analysis))
    assert payload["analysis"]["effectiveness_score"] == analysis.effectiveness_score


def test_observation_source_is_preserved():
    item = make_intervention()
    obs = make_observation(item, "2026-01-15", 80, source="smart_meter")
    assert obs.source == "smart_meter"


def test_metadata_is_json_safe():
    item = make_intervention(metadata={"source": "goal-plan", "version": 1})
    assert json.loads(json.dumps(item.to_dict()))["metadata"]["version"] == 1


def test_analysis_metadata_contains_control_flag():
    item = make_intervention()
    result = analyze_intervention(item, has_control=True)
    assert result.metadata["has_control"] is True


def test_analysis_limitations_are_tuple_and_serializable():
    item = make_intervention()
    result = analyze_intervention(item)
    assert isinstance(result.limitations, tuple)
    json.dumps(result.to_dict())


def test_intervention_status_round_trip():
    item = make_intervention(status=InterventionStatus.COMPLETED)
    assert item.status == InterventionStatus.COMPLETED
    assert item.to_dict()["status"] == "completed"
