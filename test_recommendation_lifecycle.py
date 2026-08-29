"""Tests for recommendation lifecycle and feedback learning analytics."""
from __future__ import annotations

import json
import sqlite3

import pytest

from recommendation_lifecycle import (
    FeedbackReason,
    LifecycleError,
    RecommendationFeedback,
    RecommendationLifecycleStore,
    RecommendationProfile,
    RecommendationStatus,
    analyze_portfolio,
    analyze_recommendation,
    build_profile,
    build_user_summary,
    calculate_completion_score,
    calculate_engagement_score,
    calculate_feedback_confidence,
    calculate_learning_signal,
    calculate_outcome_change,
    calculate_target_progress,
    create_event,
    create_outcome,
    export_lifecycle_json,
    export_signals_csv,
    feedback_reason_label,
    import_lifecycle_document,
    parse_import_document,
    recommendation_learning_disclaimer,
    status_label,
    utc_now,
    validate_event_payload,
    validate_feedback_payload,
)


def profile(**overrides):
    values = dict(
        recommendation_id="rec_1", impressions=10, saves=2, starts=5,
        completions=3, dismissals=1, snoozes=0, skips=1, ratings=3,
        average_rating=4.0, useful_rate=2 / 3, completion_rate=0.6,
        start_rate=0.5, dismissal_rate=0.1, last_status="completed",
        last_event_at="2026-08-27T10:00:00+00:00", feedback_reasons={"relevant": 2},
    )
    values.update(overrides)
    return RecommendationProfile(**values)


def test_utc_now_is_parseable():
    from datetime import datetime
    datetime.fromisoformat(utc_now())


def test_event_creation_defaults_timestamp():
    event = create_event("rec_1", 1, "shown")
    assert event.status is RecommendationStatus.SHOWN
    assert event.user_id == 1


def test_event_enum_is_preserved():
    event = create_event("rec_1", 1, RecommendationStatus.COMPLETED)
    assert event.status is RecommendationStatus.COMPLETED


def test_event_invalid_status():
    with pytest.raises(LifecycleError):
        create_event("rec_1", 1, "bogus")


def test_event_invalid_user():
    with pytest.raises(LifecycleError):
        create_event("rec_1", 0, "shown")


def test_event_invalid_datetime():
    with pytest.raises(LifecycleError):
        create_event("rec_1", 1, "shown", occurred_at="not-a-date")


def test_event_context_must_be_object():
    with pytest.raises(LifecycleError):
        create_event("rec_1", 1, "shown", context="bad")


def test_event_payload_validation_success():
    assert validate_event_payload({"recommendation_id": "r", "user_id": 1, "status": "shown"}) == []


def test_event_payload_validation_failure():
    errors = validate_event_payload({"user_id": "bad", "status": "bad"})
    assert len(errors) == 3


def test_feedback_creation():
    feedback = RecommendationFeedback("r", 1, utc_now(), rating=5, useful=True, reason=FeedbackReason.RELEVANT)
    assert feedback.to_dict()["reason"] == "relevant"


def test_feedback_invalid_rating():
    with pytest.raises(LifecycleError):
        RecommendationFeedback("r", 1, utc_now(), rating=6)


def test_feedback_invalid_comment():
    with pytest.raises(LifecycleError):
        RecommendationFeedback("r", 1, utc_now(), comment="x" * 1001)


def test_feedback_validation_success():
    assert validate_feedback_payload({"recommendation_id": "r", "user_id": 1, "rating": 4, "reason": "relevant"}) == []


def test_feedback_validation_bad_reason():
    assert validate_feedback_payload({"recommendation_id": "r", "user_id": 1, "reason": "nope"})


def test_engagement_score_is_bounded():
    assert 0 <= calculate_engagement_score(profile()) <= 1


def test_engagement_zero_impressions():
    assert calculate_engagement_score(profile(impressions=0)) == 0.0


def test_completion_score():
    assert calculate_completion_score(profile()) == 0.6


def test_completion_score_without_starts():
    assert calculate_completion_score(profile(starts=0, completions=2)) == 0.0


def test_confidence_zero():
    assert calculate_feedback_confidence(0, 0, 0) == 0


def test_confidence_increases_with_volume():
    assert calculate_feedback_confidence(20, 10, 5) > calculate_feedback_confidence(2, 1, 0)


def test_learning_signal_contains_positive_signals():
    signal = calculate_learning_signal(profile())
    assert signal.learning_score > 0
    assert signal.positive_signals


def test_learning_signal_low_data_is_low_confidence():
    signal = calculate_learning_signal(profile(impressions=1, ratings=0, average_rating=None, feedback_reasons={}))
    assert signal.confidence_label == "low"


def test_learning_signal_flags_cost_reason():
    signal = calculate_learning_signal(profile(feedback_reasons={"too_expensive": 2}))
    assert "cost is a recurring concern" in signal.negative_signals


def test_build_profile_counts_events():
    events = [
        {"recommendation_id": "r", "status": "shown", "occurred_at": "2026-08-01T00:00:00+00:00"},
        {"recommendation_id": "r", "status": "started", "occurred_at": "2026-08-02T00:00:00+00:00"},
        {"recommendation_id": "r", "status": "completed", "occurred_at": "2026-08-03T00:00:00+00:00"},
    ]
    p = build_profile(events, [], "r")
    assert p.impressions == 1
    assert p.starts == 1
    assert p.completions == 1


def test_build_profile_counts_feedback():
    feedback = [
        {"recommendation_id": "r", "rating": 4, "useful": 1, "reason": "relevant"},
        {"recommendation_id": "r", "rating": 2, "useful": 0, "reason": "too_expensive"},
    ]
    p = build_profile([], feedback, "r")
    assert p.ratings == 2
    assert p.average_rating == 3
    assert p.useful_rate == 0.5
    assert p.feedback_reasons["relevant"] == 1


def test_analyze_recommendation_filters_id():
    signal = analyze_recommendation("r", [{"recommendation_id": "other", "status": "shown"}], [])
    assert signal.recommendation_id == "r"
    assert signal.sample_size == 0


def test_analyze_portfolio_deterministic_ids():
    events = [{"recommendation_id": "b", "status": "shown"}, {"recommendation_id": "a", "status": "shown"}]
    assert [x.recommendation_id for x in analyze_portfolio(events, [])] == ["a", "b"]


def test_user_summary_metrics():
    events = [
        {"user_id": 1, "recommendation_id": "r", "status": "shown"},
        {"user_id": 1, "recommendation_id": "r", "status": "started"},
        {"user_id": 1, "recommendation_id": "r", "status": "completed"},
    ]
    summary = build_user_summary(1, events, [])
    assert summary.shown_count == 1
    assert summary.completed_count == 1
    assert summary.engagement_rate == 1.0


def test_user_summary_recommends_feedback_collection():
    summary = build_user_summary(1, [{"user_id": 1, "recommendation_id": "r", "status": "shown"}], [])
    assert any("feedback" in x.lower() for x in summary.improvement_areas)


def test_outcome_change():
    outcome = create_outcome("r", 1, "energy", value=80, baseline_value=100)
    assert calculate_outcome_change(outcome) == -20


def test_outcome_change_zero_baseline_is_unknown():
    outcome = create_outcome("r", 1, "energy", value=80, baseline_value=0)
    assert calculate_outcome_change(outcome) is None


def test_target_progress():
    outcome = create_outcome("r", 1, "energy", value=75, baseline_value=100, target_value=50)
    assert calculate_target_progress(outcome) == 0.5


def test_target_progress_clamped():
    outcome = create_outcome("r", 1, "energy", value=0, baseline_value=100, target_value=50)
    assert calculate_target_progress(outcome) == 1.0


def test_target_progress_without_data():
    outcome = create_outcome("r", 1, "energy")
    assert calculate_target_progress(outcome) is None


def test_store_creates_tables(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    store.initialize()
    with sqlite3.connect(store.db_path) as conn:
        names = {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}
    assert "recommendation_feedback" in names
    assert "recommendation_lifecycle_events" in names


def test_store_event_round_trip(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    event = create_event("r", 1, "shown")
    assert store.record_event(event)
    rows = store.fetch_events(1)
    assert rows[0]["recommendation_id"] == "r"


def test_store_duplicate_event_is_ignored(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    event = create_event("r", 1, "shown")
    assert store.record_event(event)
    assert not store.record_event(event)


def test_store_feedback_form(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    item = store.record_feedback_form(recommendation_id="r", user_id=1, rating=5, useful=True, reason="relevant")
    assert item.rating == 5
    assert len(store.fetch_feedback(1)) == 1


def test_store_outcome(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    outcome = create_outcome("r", 1, "energy", value=80, baseline_value=100)
    assert store.record_outcome(outcome)
    assert len(store.fetch_outcomes(1)) == 1


def test_recommendation_ids_union(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    store.record_event(create_event("r1", 1, "shown"))
    store.record_feedback_form(recommendation_id="r2", user_id=1, rating=4)
    assert store.recommendation_ids(1) == ["r1", "r2"]


def test_snapshot_persistence(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    signal = calculate_learning_signal(profile())
    sid = store.save_snapshot(1, signal)
    snapshots = store.latest_snapshots(1)
    assert snapshots[0]["snapshot_id"] == sid
    assert snapshots[0]["signal"]["recommendation_id"] == "rec_1"


def test_export_json_schema(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    store.record_event(create_event("r", 1, "shown"))
    data = json.loads(export_lifecycle_json(1, store))
    assert data["schema_version"] == "1.0"
    assert len(data["events"]) == 1


def test_export_csv_header():
    signal = calculate_learning_signal(profile())
    csv_text = export_signals_csv([signal])
    assert "recommendation_id" in csv_text
    assert "rec_1" in csv_text


def test_parse_invalid_json():
    with pytest.raises(LifecycleError):
        parse_import_document("{")


def test_parse_wrong_schema():
    with pytest.raises(LifecycleError):
        parse_import_document(json.dumps({"schema_version": "9.0", "events": [], "feedback": [], "outcomes": []}))


def test_parse_valid_document():
    doc = parse_import_document(json.dumps({"schema_version": "1.0", "events": [], "feedback": [], "outcomes": []}))
    assert doc["events"] == []


def test_import_is_transactional(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    document = {
        "schema_version": "1.0", "events": [
            {"event_id": "e1", "recommendation_id": "r", "user_id": 1, "status": "shown", "occurred_at": "2026-08-01T00:00:00+00:00"},
            {"event_id": "e2", "recommendation_id": "r", "user_id": 2, "status": "shown", "occurred_at": "2026-08-01T00:00:00+00:00"},
        ], "feedback": [], "outcomes": []
    }
    with pytest.raises(LifecycleError):
        import_lifecycle_document(json.dumps(document), store, 1)
    assert store.fetch_events(1) == []


def test_import_valid_document(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    document = {"schema_version": "1.0", "events": [{"event_id": "e1", "recommendation_id": "r", "user_id": 1, "status": "shown", "occurred_at": "2026-08-01T00:00:00+00:00", "context": {}}], "feedback": [], "outcomes": []}
    result = import_lifecycle_document(json.dumps(document), store, 1)
    assert result["events"] == 1


def test_import_duplicate_is_skipped(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    document = {"schema_version": "1.0", "events": [{"event_id": "e1", "recommendation_id": "r", "user_id": 1, "status": "shown", "occurred_at": "2026-08-01T00:00:00+00:00", "context": {}}], "feedback": [], "outcomes": []}
    import_lifecycle_document(json.dumps(document), store, 1)
    result = import_lifecycle_document(json.dumps(document), store, 1)
    assert result["skipped"] == 1


def test_delete_user_data(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    store.record_event(create_event("r", 1, "shown"))
    store.record_feedback_form(recommendation_id="r", user_id=1, rating=4)
    assert store.delete_user_data(1) == 2
    assert store.fetch_events(1) == []


def test_user_isolation(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    store.record_event(create_event("r", 1, "shown"))
    store.record_event(create_event("r", 2, "shown"))
    assert len(store.fetch_events(1)) == 1
    assert len(store.fetch_events(2)) == 1


def test_reason_label():
    assert feedback_reason_label("too_expensive") == "Too Expensive"


def test_status_label():
    assert status_label("in_progress") == "In Progress"


def test_disclaimer_is_explicit():
    text = recommendation_learning_disclaimer()
    assert "not proof" in text


def test_profile_serialization():
    data = profile().to_dict()
    assert data["recommendation_id"] == "rec_1"


def test_signal_serialization():
    data = calculate_learning_signal(profile()).to_dict()
    assert isinstance(data["positive_signals"], list)


def test_outcome_validation_quality():
    with pytest.raises(LifecycleError):
        create_outcome("r", 1, "x", evidence_quality=2)


def test_feedback_enum_reason_roundtrip():
    item = RecommendationFeedback("r", 1, utc_now(), reason=FeedbackReason.DUPLICATE)
    assert item.to_dict()["reason"] == "duplicate"


def test_store_reinitialization_is_idempotent(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    store.initialize()
    store.initialize()
    assert store.recommendation_ids(1) == []


def test_event_context_is_serializable(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    store.record_event(create_event("r", 1, "shown", context={"score": 0.5}))
    exported = json.loads(export_lifecycle_json(1, store))
    assert exported["events"][0]["context"]["score"] == 0.5


def test_feedback_comment_export(tmp_path):
    store = RecommendationLifecycleStore(str(tmp_path / "db.sqlite"))
    store.record_feedback_form(recommendation_id="r", user_id=1, rating=4, comment="Helpful")
    exported = json.loads(export_lifecycle_json(1, store))
    assert exported["feedback"][0]["comment"] == "Helpful"


def test_learning_score_is_deterministic():
    assert calculate_learning_signal(profile()).to_dict() == calculate_learning_signal(profile()).to_dict()
