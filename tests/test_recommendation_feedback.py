"""Unit tests for recommendation feedback and deterministic personalization."""
from datetime import datetime, timedelta, timezone

import pytest

from src.ai.recommendation_feedback import (
    FEEDBACK_TYPES,
    RecommendationFeedback,
    RecommendationFeedbackStore,
    calculate_effectiveness,
    calculate_preference_score,
    calculate_recommendation_score,
    deserialize_feedback,
    detect_completed_actions,
    detect_repeated_rejection,
    feedback_to_dicts,
    generate_personalized_order,
    get_feedback_history,
    normalize_recommendations,
    rank_recommendations,
    record_feedback,
    recommendation_analytics,
    reset_preferences,
    serialize_feedback,
    validate_feedback_payload,
)


@pytest.fixture
def store(tmp_path):
    return RecommendationFeedbackStore(str(tmp_path / "feedback.db"))


@pytest.fixture
def recommendations():
    return [
        {"id": "transport", "text": "Use public transport", "category": "Transportation", "difficulty": "easy", "impact": 80},
        {"id": "energy", "text": "Reduce standby electricity", "category": "Electricity", "difficulty": "easy", "impact": 45},
        {"id": "flights", "text": "Reduce flights", "category": "Flights", "difficulty": "advanced", "impact": 95},
    ]


def test_feedback_types_are_complete():
    assert set(FEEDBACK_TYPES) == {
        "helpful", "not_helpful", "already_doing", "too_difficult",
        "not_relevant", "completed", "dismissed",
    }


def test_feedback_validation_rejects_unknown_type():
    with pytest.raises(ValueError):
        RecommendationFeedback(1, "r1", "Energy", "unknown")


def test_feedback_validation_rejects_unknown_difficulty():
    with pytest.raises(ValueError):
        RecommendationFeedback(1, "r1", "Energy", "helpful", "impossible")


def test_feedback_validation_rejects_empty_recommendation():
    with pytest.raises(ValueError):
        RecommendationFeedback(1, "", "Energy", "helpful")


def test_validate_payload_requires_fields():
    with pytest.raises(ValueError, match="Missing required fields"):
        validate_feedback_payload({"user_id": 1})


def test_validate_payload_normalizes_category():
    result = validate_feedback_payload({
        "user_id": 1,
        "recommendation_id": "r1",
        "category": "  ",
        "feedback_type": "helpful",
    })
    assert result.category == "General"


def test_store_creates_table_and_indexes(store):
    with store._connect() as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        indexes = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    assert any(row[0] == "recommendation_feedback" for row in tables)
    assert len(indexes) >= 2


def test_record_feedback_persists(store):
    ok, message = record_feedback(7, "r1", "Energy", "helpful", store=store)
    assert ok is True
    assert "recorded" in message.lower()
    history = get_feedback_history(7, store=store)
    assert len(history) == 1
    assert history[0].feedback_type == "helpful"


def test_duplicate_feedback_is_rejected(store):
    timestamp = "2026-08-21T10:00:00+00:00"
    assert record_feedback(1, "r1", "Energy", "helpful", store=store, timestamp=timestamp)[0]
    ok, message = record_feedback(1, "r1", "Energy", "helpful", store=store, timestamp=timestamp)
    assert not ok
    assert "duplicate" in message.lower()


def test_feedback_is_scoped_to_user(store):
    record_feedback(1, "r1", "Energy", "helpful", store=store)
    record_feedback(2, "r1", "Energy", "not_helpful", store=store)
    assert len(get_feedback_history(1, store=store)) == 1
    assert len(get_feedback_history(2, store=store)) == 1
    assert get_feedback_history(1, store=store)[0].feedback_type == "helpful"


def test_recommendation_specific_history(store):
    record_feedback(1, "r1", "Energy", "helpful", store=store)
    record_feedback(1, "r2", "Transport", "completed", store=store)
    assert len(get_feedback_history(1, "r1", store=store)) == 1


def test_reset_preferences_deletes_only_selected_user(store):
    record_feedback(1, "r1", "Energy", "helpful", store=store)
    record_feedback(2, "r2", "Transport", "helpful", store=store)
    deleted = reset_preferences(1, store=store)
    assert deleted == 1
    assert get_feedback_history(1, store=store) == []
    assert len(get_feedback_history(2, store=store)) == 1


def test_preference_score_counts_positive_and_negative_feedback():
    events = [
        RecommendationFeedback(1, "r1", "Energy", "helpful"),
        RecommendationFeedback(1, "r2", "Energy", "completed"),
        RecommendationFeedback(1, "r3", "Energy", "not_helpful"),
        RecommendationFeedback(1, "r4", "Energy", "too_difficult", "advanced"),
    ]
    preference = calculate_preference_score(events, category="Energy")
    assert preference.helpful == 1
    assert preference.completion == 1
    assert preference.rejection == 2
    assert preference.difficulty == -1


def test_repeated_rejection_detector(recommendations):
    events = [
        RecommendationFeedback(1, "transport", "Transportation", "not_helpful"),
        RecommendationFeedback(1, "transport", "Transportation", "not_relevant"),
    ]
    ranked = rank_recommendations(recommendations, events)
    history = [score for score in ranked if score.recommendation_id == "transport"][0]
    assert history.suppressed
    assert detect_repeated_rejection(type("H", (), {"rejection_count": 2})())


def test_completed_detector():
    class History:
        completion_count = 1
    assert detect_completed_actions(History())


def test_completed_recommendation_gets_positive_signal(recommendations):
    events = [RecommendationFeedback(1, "transport", "Transportation", "completed")]
    scores = rank_recommendations(recommendations, events)
    transport = next(score for score in scores if score.recommendation_id == "transport")
    assert transport.completion == 0.5
    assert transport.score > 0


def test_helpful_feedback_increases_score(recommendations):
    baseline = rank_recommendations(recommendations, [])
    positive = rank_recommendations(
        recommendations,
        [RecommendationFeedback(1, "energy", "Electricity", "helpful")],
    )
    base_energy = next(x for x in baseline if x.recommendation_id == "energy")
    positive_energy = next(x for x in positive if x.recommendation_id == "energy")
    assert positive_energy.score > base_energy.score


def test_rejection_penalty_decreases_score(recommendations):
    baseline = rank_recommendations(recommendations, [])
    rejected = rank_recommendations(
        recommendations,
        [RecommendationFeedback(1, "energy", "Electricity", "not_helpful")],
    )
    assert next(x for x in rejected if x.recommendation_id == "energy").score < next(x for x in baseline if x.recommendation_id == "energy").score


def test_two_rejections_suppress_recent_item(recommendations):
    events = [
        RecommendationFeedback(1, "energy", "Electricity", "not_helpful"),
        RecommendationFeedback(1, "energy", "Electricity", "not_relevant"),
    ]
    score = next(x for x in rank_recommendations(recommendations, events) if x.recommendation_id == "energy")
    assert score.suppressed
    assert score.score == float("-inf")


def test_old_rejections_are_not_suppressed_forever(recommendations):
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    events = [
        RecommendationFeedback(1, "energy", "Electricity", "not_helpful", timestamp=old),
        RecommendationFeedback(1, "energy", "Electricity", "not_relevant", timestamp=old),
    ]
    score = next(x for x in rank_recommendations(recommendations, events) if x.recommendation_id == "energy")
    assert not score.suppressed


def test_difficulty_preference_favors_completed_level(recommendations):
    events = [
        RecommendationFeedback(1, "a", "General", "completed", "advanced"),
        RecommendationFeedback(1, "b", "General", "completed", "advanced"),
    ]
    advanced = next(x for x in rank_recommendations(recommendations, events) if x.recommendation_id == "flights")
    easy = next(x for x in rank_recommendations(recommendations, events) if x.recommendation_id == "energy")
    assert advanced.difficulty_fit > easy.difficulty_fit


def test_rank_is_deterministic(recommendations):
    events = [RecommendationFeedback(1, "energy", "Electricity", "helpful")]
    first = [x.as_dict() for x in rank_recommendations(recommendations, events)]
    second = [x.as_dict() for x in rank_recommendations(recommendations, events)]
    assert first == second


def test_rank_uses_limit(recommendations):
    assert len(rank_recommendations(recommendations, [], limit=2)) == 2


def test_personalized_order_preserves_item_objects(recommendations):
    events = [RecommendationFeedback(1, "transport", "Transportation", "completed")]
    ordered = generate_personalized_order(recommendations, events)
    assert {item["id"] for item in ordered} == {item["id"] for item in recommendations}


def test_normalize_string_recommendations():
    items = normalize_recommendations(["Reduce electricity", "Walk more"])
    assert len(items) == 2
    assert all(item["id"] for item in items)
    assert items[0]["category"] == "Electricity"
    assert items[1]["category"] == "Transportation"


def test_normalize_mapping_recommendations():
    items = normalize_recommendations([{"text": "Reduce waste"}])
    assert items[0]["category"] == "General"
    assert items[0]["difficulty"] == "moderate"


def test_serialization_round_trip():
    original = RecommendationFeedback(4, "r1", "Diet", "completed", "advanced")
    restored = deserialize_feedback(serialize_feedback(original))
    assert restored == original


def test_feedback_to_dicts():
    events = [RecommendationFeedback(1, "r1", "Energy", "helpful")]
    data = feedback_to_dicts(events)
    assert data[0]["recommendation_id"] == "r1"
    assert data[0]["feedback_type"] == "helpful"


def test_effectiveness_empty():
    result = calculate_effectiveness([])
    assert result["total_events"] == 0
    assert result["completion_rate"] == 0.0


def test_effectiveness_rates():
    events = [
        RecommendationFeedback(1, "r1", "Energy", "helpful"),
        RecommendationFeedback(1, "r2", "Energy", "completed"),
        RecommendationFeedback(1, "r3", "Transport", "not_helpful"),
        RecommendationFeedback(1, "r4", "Diet", "too_difficult"),
    ]
    result = calculate_effectiveness(events)
    assert result["total_events"] == 4
    assert result["helpfulness_rate"] == 0.25
    assert result["completion_rate"] == 0.25
    assert result["rejection_rate"] == 0.5


def test_effectiveness_category_and_difficulty_rollups():
    events = [
        RecommendationFeedback(1, "r1", "Energy", "completed", "easy"),
        RecommendationFeedback(1, "r2", "Energy", "completed", "moderate"),
        RecommendationFeedback(1, "r3", "Diet", "helpful", "advanced"),
    ]
    result = calculate_effectiveness(events)
    assert result["completion_by_category"]["Energy"] == 2
    assert result["completion_by_difficulty"]["easy"] == 1
    assert result["most_effective_categories"][0] == "Energy"


def test_frequently_rejected_is_ranked():
    events = [
        RecommendationFeedback(1, "r1", "Energy", "not_helpful"),
        RecommendationFeedback(1, "r1", "Energy", "not_relevant"),
        RecommendationFeedback(1, "r2", "Diet", "not_helpful"),
    ]
    result = calculate_effectiveness(events)
    assert result["frequently_rejected"][0] == "r1"


def test_repeated_without_completion_is_detected():
    events = [
        RecommendationFeedback(1, "r1", "Energy", "helpful"),
        RecommendationFeedback(1, "r1", "Energy", "not_helpful"),
        RecommendationFeedback(1, "r1", "Energy", "dismissed"),
    ]
    result = calculate_effectiveness(events)
    assert "r1" in result["repeated_without_completion"]


def test_completed_item_not_marked_repeated_without_completion():
    events = [
        RecommendationFeedback(1, "r1", "Energy", "helpful"),
        RecommendationFeedback(1, "r1", "Energy", "dismissed"),
        RecommendationFeedback(1, "r1", "Energy", "completed"),
    ]
    result = calculate_effectiveness(events)
    assert "r1" not in result["repeated_without_completion"]


def test_analytics_contains_category_details():
    events = [RecommendationFeedback(1, "r1", "Energy", "completed")]
    result = recommendation_analytics(events)
    assert result["by_category"]["Energy"]["completed"] == 1
    assert result["by_category"]["Energy"]["completion_rate"] == 1.0


def test_reset_does_not_touch_other_tables(store):
    with store._connect() as conn:
        conn.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO unrelated(value) VALUES ('keep')")
    record_feedback(1, "r1", "Energy", "helpful", store=store)
    reset_preferences(1, store=store)
    with store._connect() as conn:
        assert conn.execute("SELECT value FROM unrelated").fetchone()[0] == "keep"


def test_feedback_count(store):
    assert store.count(1) == 0
    record_feedback(1, "r1", "Energy", "helpful", store=store)
    assert store.count(1) == 1


def test_dismissed_feedback_counts_as_repetition(store):
    for _ in range(3):
        record_feedback(1, "r1", "Energy", "dismissed", store=store, timestamp=f"2026-08-2{_ + 1}T10:00:00+00:00")
    history = get_feedback_history(1, "r1", store=store)
    assert len(history) == 3


def test_negative_feedback_types_are_supported(store):
    for index, kind in enumerate(("not_helpful", "not_relevant", "already_doing", "too_difficult")):
        ok, _ = record_feedback(1, f"r{index}", "Energy", kind, "advanced", store=store)
        assert ok


def test_completion_is_not_carbon_savings_claim():
    events = [RecommendationFeedback(1, "r1", "Energy", "completed")]
    result = calculate_effectiveness(events)
    assert "carbon_savings" not in result


def test_custom_weights_are_respected(recommendations):
    normal = next(x for x in rank_recommendations(recommendations, []) if x.recommendation_id == "flights")
    custom = next(x for x in rank_recommendations(recommendations, [], weights={"impact": 0.0}) if x.recommendation_id == "flights")
    assert custom.score < normal.score


def test_missing_impact_is_safe():
    items = [{"id": "r1", "category": "Energy", "difficulty": "easy"}]
    score = rank_recommendations(items, [])[0]
    assert score.impact == 0.0


def test_invalid_impact_is_safe():
    items = [{"id": "r1", "category": "Energy", "difficulty": "easy", "impact": "not-a-number"}]
    score = rank_recommendations(items, [])[0]
    assert score.impact == 0.0


def test_impression_tracking_and_counts(store):
    store.record_impression(1, "r1", "Energy", "easy")
    store.record_impression(1, "r1", "Energy", "easy")
    store.record_impression(1, "r2", "Diet", "moderate")
    counts = store.get_impression_counts(1)
    assert counts == {"r1": 2, "r2": 1}
    assert store.get_last_impression(1, "r1") is not None


def test_impressions_feed_repetition_analytics(store):
    for _ in range(3):
        store.record_impression(1, "r1", "Energy", "easy")
    result = calculate_effectiveness([], impression_counts=store.get_impression_counts(1))
    assert "r1" in result["repeated_without_completion"]


def test_impressions_feed_ranking_history(recommendations, store):
    for _ in range(3):
        store.record_impression(1, "energy", "Electricity", "easy")
    scores = rank_recommendations(
        recommendations, [],
        impression_counts=store.get_impression_counts(1),
        last_impressions={"energy": store.get_last_impression(1, "energy")},
    )
    energy = next(score for score in scores if score.recommendation_id == "energy")
    assert energy.repetition > 0


def test_reset_preferences_clears_impressions(store):
    store.record_impression(1, "r1", "Energy", "easy")
    record_feedback(1, "r1", "Energy", "helpful", store=store)
    reset_preferences(1, store=store)
    assert store.get_impression_counts(1) == {}
    assert store.count(1) == 0
