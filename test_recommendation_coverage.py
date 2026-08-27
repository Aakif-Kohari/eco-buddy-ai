"""Tests for recommendation coverage and sustainability gap analysis."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from recommendation_coverage import (
    CoverageStatus,
    GapSeverity,
    RecommendationCoverageConfig,
    RecommendationCoverageStore,
    RecommendationRecord,
    analyze_category_coverage,
    build_coverage_report,
    calculate_coverage_score,
    calculate_impact_shares,
    calculate_recommendation_diversity,
    category_coverage_index,
    category_distribution,
    coverage_table,
    detect_repeated_recommendations,
    duplicate_recommendation_ids,
    filter_recommendations_by_category,
    find_coverage_gaps,
    gap_codes,
    gap_table,
    highest_impact_categories,
    infer_recommendation_categories,
    is_high_impact_gap,
    load_latest_coverage_report,
    mark_history_status,
    normalize_category,
    normalize_contributors,
    normalize_recommendation,
    normalize_recommendations,
    persist_coverage_report,
    recommendation_history,
    recommendation_matches_category,
    report_fingerprint,
    serialize_coverage_report,
    summarize_coverage,
)


def rec(
    rid: str,
    title: str,
    category: str,
    *,
    impact: float | None = None,
    completed: bool = False,
    rejected: bool = False,
):
    return {
        "id": rid,
        "title": title,
        "description": title,
        "category": category,
        "impact_score": impact,
        "completed": completed,
        "rejected": rejected,
    }


def event(rid: str, kind: str, category: str = "energy"):
    return {
        "recommendation_id": rid,
        "feedback_type": kind,
        "category": category,
    }


def test_category_aliases_are_normalized():
    assert normalize_category("Transportation") == "transport"
    assert normalize_category("energy") == "electricity"
    assert normalize_category("Food") == "diet"
    assert normalize_category("recycling") == "waste"
    assert normalize_category("shopping") == "shopping"
    assert normalize_category("unknown") == "general"


def test_category_can_be_inferred_from_title():
    assert normalize_category("", title="Switch to public transport") == "transport"
    assert normalize_category("", title="Install LED lighting") == "electricity"
    assert normalize_category("", title="Eat more plant-based meals") == "diet"
    assert normalize_category("", title="Fix leaking shower") == "water"
    assert normalize_category("", title="Use reusable bags") == "waste"


def test_normalize_string_recommendation():
    item = normalize_recommendation("Use public transport twice a week")
    assert item.id.startswith("rec-")
    assert item.category == "transport"
    assert item.source == "recommendations.py"


def test_normalize_mapping_recommendation():
    item = normalize_recommendation({
        "id": "abc",
        "title": "Switch to LEDs",
        "description": "Replace old bulbs",
        "category": "Energy",
        "impact_score": 80,
        "co2_savings": 100,
        "tags": ["LED", "energy"],
        "difficulty": "easy",
    })
    assert item.id == "abc"
    assert item.category == "electricity"
    assert item.impact_score == 80
    assert item.co2_savings == 100
    assert item.tags == ("energy", "led")


def test_normalize_dataclass_recommendation():
    original = RecommendationRecord("a", "LED", "LED", "electricity")
    result = normalize_recommendation(original)
    assert result is original


def test_normalize_recommendations_is_deterministic():
    items = [
        rec("2", "Public Transport", "transport"),
        rec("1", "LED", "energy"),
        rec("3", "Meal Planning", "food"),
    ]
    first = [item.id for item in normalize_recommendations(items)]
    second = [item.id for item in normalize_recommendations(items)]
    assert first == second
    assert first == ["3", "1", "2"]


def test_contributor_normalization_merges_aliases():
    result = normalize_contributors({"Energy": 200, "electricity": 100, "Transport": 50})
    assert result == {"electricity": 300, "transport": 50}


def test_negative_contributors_are_clamped():
    result = normalize_contributors({"energy": -20, "transport": 10})
    assert result["electricity"] == 0
    assert result["transport"] == 10


def test_impact_shares_sum_to_one():
    shares = calculate_impact_shares({"energy": 200, "transport": 100, "food": 100})
    assert round(sum(shares.values()), 8) == 1.0
    assert shares["electricity"] == 0.5


def test_impact_shares_empty_input():
    assert calculate_impact_shares({}) == {}


def test_highest_impact_categories_are_sorted():
    result = highest_impact_categories({"energy": 500, "transport": 300, "food": 200})
    assert result[0][0] == "electricity"
    assert result[0][2] == 0.5


def test_category_distribution():
    items = normalize_recommendations([
        rec("1", "LED", "energy"),
        rec("2", "Solar", "energy"),
        rec("3", "Bus", "transport"),
    ])
    assert category_distribution(items) == {"electricity": 2, "transport": 1}


def test_recommendation_diversity_single_category_is_zero():
    items = normalize_recommendations([
        rec("1", "LED", "energy"),
        rec("2", "Solar", "energy"),
    ])
    assert calculate_recommendation_diversity(items) == 0.0


def test_recommendation_diversity_multiple_categories_is_positive():
    items = normalize_recommendations([
        rec("1", "LED", "energy"),
        rec("2", "Bus", "transport"),
        rec("3", "Meal", "food"),
    ])
    assert calculate_recommendation_diversity(items) == 1.0


def test_repeated_recommendations_are_detected():
    items = normalize_recommendations([
        rec("1", "Switch to LEDs", "energy"),
        rec("2", "Switch to LEDs", "energy"),
        rec("3", "Use bus", "transport"),
    ])
    assert detect_repeated_recommendations(items) == ["switch leds"]


def test_repeated_detection_threshold_is_respected():
    items = normalize_recommendations([
        rec("1", "Switch to LEDs", "energy"),
        rec("2", "Switch to LEDs", "energy"),
    ])
    assert detect_repeated_recommendations(items, threshold=3) == []


def test_duplicate_ids_are_reported_without_deletion():
    items = normalize_recommendations([
        rec("same", "LED", "energy"),
        rec("same", "Solar", "energy"),
    ])
    assert duplicate_recommendation_ids(items) == ["same"]
    assert len(items) == 2


def test_feedback_history_counts_events():
    items = normalize_recommendations([
        rec("1", "LED", "energy"),
        rec("2", "Bus", "transport"),
    ])
    history = recommendation_history(items, [
        event("1", "helpful"),
        event("1", "completed"),
        event("1", "not_helpful"),
        event("2", "dismissed", "transport"),
    ])
    assert history["1"]["helpful"] == 1
    assert history["1"]["completed"] == 1
    assert history["1"]["rejected"] == 1
    assert history["2"]["dismissed"] == 1


def test_feedback_for_unknown_recommendation_is_ignored():
    items = normalize_recommendations([rec("1", "LED", "energy")])
    history = recommendation_history(items, [event("unknown", "completed")])
    assert history["1"]["events"] == 0


def test_mark_history_status_marks_completed():
    items = normalize_recommendations([rec("1", "LED", "energy")])
    marked = mark_history_status(items, [event("1", "completed")])
    assert marked[0].completed is True


def test_mark_history_status_marks_rejected():
    items = normalize_recommendations([rec("1", "LED", "energy")])
    marked = mark_history_status(items, [event("1", "not_relevant")])
    assert marked[0].rejected is True


def test_coverage_marks_high_impact_missing_category_as_gap():
    rows = analyze_category_coverage(
        {"energy": 800, "transport": 200},
        [rec("1", "Bus", "transport")],
    )
    index = {row.category: row for row in rows}
    assert index["electricity"].status == CoverageStatus.GAP
    assert index["electricity"].gap_severity == GapSeverity.CRITICAL


def test_coverage_marks_three_recommendations_as_covered():
    rows = analyze_category_coverage(
        {"energy": 500},
        [
            rec("1", "LED", "energy"),
            rec("2", "Solar", "energy"),
            rec("3", "Thermostat", "energy"),
        ],
    )
    row = {item.category: item for item in rows}["electricity"]
    assert row.status == CoverageStatus.COVERED
    assert row.coverage_score == 1.0


def test_coverage_marks_one_recommendation_as_partial():
    rows = analyze_category_coverage(
        {"energy": 500},
        [rec("1", "LED", "energy")],
    )
    row = {item.category: item for item in rows}["electricity"]
    assert row.status == CoverageStatus.PARTIAL


def test_completed_only_category_becomes_gap():
    rows = analyze_category_coverage(
        {"energy": 500},
        [rec("1", "LED", "energy")],
        feedback=[event("1", "completed")],
    )
    row = {item.category: item for item in rows}["electricity"]
    assert row.status == CoverageStatus.GAP
    assert row.completed_count == 1


def test_rejected_category_receives_reason():
    rows = analyze_category_coverage(
        {"energy": 500},
        [rec("1", "LED", "energy")],
        feedback=[event("1", "not_helpful")],
    )
    row = {item.category: item for item in rows}["electricity"]
    assert row.rejected_count == 1
    assert "rejected" in row.reason.lower()


def test_no_assessment_data_is_not_a_gap():
    rows = analyze_category_coverage({}, [rec("1", "LED", "energy")])
    row = {item.category: item for item in rows}["electricity"]
    assert row.status == CoverageStatus.NO_DATA
    assert row.gap_severity == GapSeverity.NONE


def test_empty_inputs_return_default_no_data_categories():
    rows = analyze_category_coverage({}, [])
    assert rows
    assert all(row.status == CoverageStatus.NO_DATA for row in rows)


def test_zero_total_impact_is_safe():
    rows = analyze_category_coverage({"energy": 0, "transport": 0}, [])
    assert all(row.impact_share == 0 for row in rows)


def test_coverage_score_is_impact_weighted():
    rows = analyze_category_coverage(
        {"energy": 900, "transport": 100},
        [
            rec("1", "LED", "energy"),
            rec("2", "Solar", "energy"),
            rec("3", "Thermostat", "energy"),
            rec("4", "Bus", "transport"),
        ],
    )
    score = calculate_coverage_score(rows)
    assert 0.75 <= score <= 1.0


def test_gap_codes_include_missing_category():
    report = build_coverage_report(
        {"energy": 900},
        [rec("1", "Bus", "transport")],
    )
    assert "MISSING_CATEGORY_COVERAGE" in gap_codes(report)


def test_find_gaps_returns_sorted_by_severity():
    rows = analyze_category_coverage(
        {"energy": 800, "transport": 100, "food": 100},
        [rec("1", "Bus", "transport")],
    )
    gaps = find_coverage_gaps(rows)
    ranks = {
        GapSeverity.NONE: 0,
        GapSeverity.LOW: 1,
        GapSeverity.MEDIUM: 2,
        GapSeverity.HIGH: 3,
        GapSeverity.CRITICAL: 4,
    }
    assert [ranks[g.severity] for g in gaps] == sorted(
        [ranks[g.severity] for g in gaps], reverse=True
    )


def test_build_report_contains_all_sections():
    report = build_coverage_report(
        {"energy": 500, "transport": 500},
        [rec("1", "LED", "energy"), rec("2", "Bus", "transport")],
        user_id=7,
    )
    assert report.user_id == 7
    assert report.recommendation_count == 2
    assert report.category_count >= 2
    assert report.created_at
    assert isinstance(report.metadata, dict)


def test_report_serializes_to_json():
    report = build_coverage_report({"energy": 100}, [rec("1", "LED", "energy")])
    text = serialize_coverage_report(report)
    payload = json.loads(text)
    assert payload["recommendation_count"] == 1
    assert payload["categories"]


def test_report_fingerprint_ignores_created_at():
    report = build_coverage_report({"energy": 100}, [rec("1", "LED", "energy")])
    second = build_coverage_report({"energy": 100}, [rec("1", "LED", "energy")])
    assert report_fingerprint(report) == report_fingerprint(second)


def test_summary_contains_expected_metrics():
    report = build_coverage_report({"energy": 100}, [rec("1", "LED", "energy")])
    summary = summarize_coverage(report)
    assert "overall_percent" in summary
    assert "gap_count" in summary
    assert "severity_counts" in summary


def test_coverage_table_is_flat():
    report = build_coverage_report({"energy": 100}, [rec("1", "LED", "energy")])
    rows = coverage_table(report)
    assert rows
    assert "Category" in rows[0]
    assert "Status" in rows[0]


def test_gap_table_is_flat():
    report = build_coverage_report({"energy": 100}, [])
    rows = gap_table(report)
    assert rows
    assert "Severity" in rows[0]
    assert "Follow-up" in rows[0]


def test_category_index_returns_lookup():
    report = build_coverage_report({"energy": 100}, [rec("1", "LED", "energy")])
    index = category_coverage_index(report)
    assert index["electricity"].label == "Electricity & Energy"


def test_high_impact_gap_helper():
    report = build_coverage_report({"energy": 900, "transport": 100}, [])
    row = category_coverage_index(report)["electricity"]
    assert is_high_impact_gap(row)


def test_recommendation_matches_category():
    assert recommendation_matches_category(rec("1", "Bus", "transport"), "Transportation")
    assert not recommendation_matches_category(rec("1", "Bus", "transport"), "Energy")


def test_filter_recommendations_by_category():
    items = filter_recommendations_by_category(
        [rec("1", "Bus", "transport"), rec("2", "LED", "energy")],
        "Transportation",
    )
    assert [item.id for item in items] == ["1"]


def test_infer_recommendation_categories():
    categories = infer_recommendation_categories([
        "Use public transport",
        "Install LED bulbs",
        "Plan plant-based meals",
    ])
    assert categories == {"diet": 1, "electricity": 1, "transport": 1}


def test_existing_string_recommendations_can_be_analyzed():
    report = build_coverage_report(
        {"transport": 700, "energy": 300},
        [
            "Use public transportation",
            "Walk or cycle for nearby trips",
            "Switch to LED lighting",
        ],
    )
    assert report.recommendation_count == 3
    index = category_coverage_index(report)
    assert index["transport"].recommendation_count == 2
    assert index["electricity"].recommendation_count == 1


def test_missing_recommendation_metadata_does_not_crash():
    report = build_coverage_report(
        {"energy": 500},
        [{"title": "Turn off unused devices"}],
    )
    assert report.recommendation_count == 1
    assert report.categories


def test_nan_recommendation_values_are_safe():
    item = normalize_recommendation({
        "id": "nan",
        "title": "LED",
        "category": "energy",
        "impact_score": float("nan"),
    })
    assert item.impact_score is None


def test_invalid_config_is_rejected():
    with pytest.raises(ValueError):
        RecommendationCoverageConfig(high_impact_share=2)
    with pytest.raises(ValueError):
        RecommendationCoverageConfig(repeated_title_threshold=1)


def test_custom_config_changes_coverage_threshold():
    config = RecommendationCoverageConfig(full_coverage_recommendations=1)
    rows = analyze_category_coverage(
        {"energy": 500},
        [rec("1", "LED", "energy")],
        config=config,
    )
    row = {item.category: item for item in rows}["electricity"]
    assert row.status == CoverageStatus.COVERED


def test_repetition_rate_is_computed():
    rows = analyze_category_coverage(
        {"energy": 500},
        [
            rec("1", "LED", "energy"),
            rec("2", "LED", "energy"),
            rec("3", "Solar", "energy"),
        ],
    )
    row = {item.category: item for item in rows}["electricity"]
    assert round(row.repetition_rate, 4) == round(1 / 3, 4)


def test_completed_items_are_not_treated_as_new_coverage():
    rows = analyze_category_coverage(
        {"energy": 500},
        [rec("1", "LED", "energy"), rec("2", "Solar", "energy")],
        feedback=[event("1", "completed")],
    )
    row = {item.category: item for item in rows}["electricity"]
    assert row.completed_count == 1
    assert row.coverage_score < 1


def test_multiple_rejected_items_reduce_coverage():
    rows = analyze_category_coverage(
        {"energy": 500},
        [rec("1", "LED", "energy"), rec("2", "Solar", "energy")],
        feedback=[event("1", "not_relevant"), event("2", "not_helpful")],
    )
    row = {item.category: item for item in rows}["electricity"]
    assert row.rejected_count == 2
    assert row.coverage_score < 1


def test_completed_and_rejected_statuses_are_preserved_in_report():
    report = build_coverage_report(
        {"energy": 500},
        [rec("1", "LED", "energy")],
        feedback=[event("1", "completed"), event("1", "not_helpful")],
    )
    row = category_coverage_index(report)["electricity"]
    assert row.completed_count == 1
    assert row.rejected_count == 1


def test_persistence_round_trip(tmp_path: Path):
    db = tmp_path / "coverage.db"
    store = RecommendationCoverageStore(str(db))
    report = build_coverage_report(
        {"energy": 100}, [rec("1", "LED", "energy")], user_id=42
    )
    report_id = store.save(report)
    assert report_id > 0
    rows = store.list_reports(42)
    assert len(rows) == 1
    assert rows[0]["coverage_score"] == report.overall_score
    assert json.loads(rows[0]["report_payload"])["user_id"] == 42


def test_persistence_latest_returns_latest(tmp_path: Path):
    db = tmp_path / "coverage.db"
    store = RecommendationCoverageStore(str(db))
    first = build_coverage_report({"energy": 100}, [rec("1", "LED", "energy")], user_id=1)
    second = build_coverage_report({"energy": 900}, [], user_id=1)
    store.save(first)
    store.save(second)
    latest = store.latest(1)
    assert latest is not None
    assert latest["coverage_score"] == second.overall_score


def test_persistence_delete_user_reports(tmp_path: Path):
    db = tmp_path / "coverage.db"
    store = RecommendationCoverageStore(str(db))
    report = build_coverage_report({"energy": 100}, [rec("1", "LED", "energy")], user_id=1)
    store.save(report)
    assert store.delete_user_reports(1) == 1
    assert store.list_reports(1) == []


def test_persistence_helper_functions(tmp_path: Path):
    db = tmp_path / "coverage.db"
    store = RecommendationCoverageStore(str(db))
    report = build_coverage_report({"energy": 100}, [rec("1", "LED", "energy")], user_id=1)
    report_id = persist_coverage_report(report, store=store)
    assert report_id > 0
    latest = load_latest_coverage_report(1, store=store)
    assert latest is not None


def test_store_creates_only_its_own_table(tmp_path: Path):
    db = tmp_path / "coverage.db"
    store = RecommendationCoverageStore(str(db))
    with sqlite3.connect(db) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert store.TABLE in tables
    assert tables == {store.TABLE, "sqlite_sequence"}


def test_report_fingerprint_is_stable_for_equivalent_coverage():
    first = build_coverage_report({"energy": 100}, [rec("1", "LED", "energy")])
    second = build_coverage_report({"energy": 100}, [rec("1", "Solar", "energy")])
    # The fingerprint describes the coverage result, not the raw catalog text.
    assert report_fingerprint(first) == report_fingerprint(second)


def test_high_impact_uncovered_count():
    report = build_coverage_report({"energy": 600, "transport": 400}, [])
    assert report.high_impact_uncovered_count == 2


def test_overall_gap_status_for_empty_recommendation_set():
    report = build_coverage_report({"energy": 600, "transport": 400}, [])
    assert report.status == CoverageStatus.GAP


def test_overall_no_data_status_for_empty_assessment():
    report = build_coverage_report({}, [])
    assert report.status == CoverageStatus.NO_DATA


def test_overall_covered_status_for_strong_coverage():
    recommendations = [
        rec("e1", "LED", "energy"),
        rec("e2", "Solar", "energy"),
        rec("e3", "Thermostat", "energy"),
        rec("t1", "Bus", "transport"),
        rec("t2", "Bike", "transport"),
        rec("t3", "Walk", "transport"),
    ]
    report = build_coverage_report({"energy": 500, "transport": 500}, recommendations)
    assert report.status == CoverageStatus.COVERED


def test_gap_severity_critical_for_large_share():
    report = build_coverage_report({"energy": 900, "transport": 100}, [])
    energy = category_coverage_index(report)["electricity"]
    assert energy.gap_severity == GapSeverity.CRITICAL


def test_gap_reason_mentions_category_label():
    report = build_coverage_report({"energy": 500}, [])
    energy = category_coverage_index(report)["electricity"]
    assert "Electricity" in energy.reason


def test_metadata_can_be_supplied():
    report = build_coverage_report(
        {"energy": 100}, [rec("1", "LED", "energy")], metadata={"assessment_id": 123}
    )
    assert report.metadata["assessment_id"] == 123


def test_report_to_dict_is_json_safe():
    report = build_coverage_report({"energy": 100}, [rec("1", "LED", "energy")])
    payload = report.to_dict()
    json.dumps(payload)


def test_category_rows_are_sorted():
    rows = analyze_category_coverage(
        {"water": 100, "energy": 100, "transport": 100},
        [],
    )
    assert [row.category for row in rows] == sorted(row.category for row in rows)


def test_gaps_are_deterministic():
    recommendations = [rec("1", "LED", "energy"), rec("2", "Bus", "transport")]
    first = build_coverage_report({"energy": 500, "transport": 500}, recommendations)
    second = build_coverage_report({"energy": 500, "transport": 500}, recommendations)
    assert [(g.code, g.category) for g in first.gaps] == [(g.code, g.category) for g in second.gaps]


def test_same_recommendation_text_gets_same_generated_id():
    a = normalize_recommendation("Use public transport")
    b = normalize_recommendation("Use public transport")
    assert a.id == b.id


def test_different_recommendation_text_gets_different_generated_id():
    a = normalize_recommendation("Use public transport")
    b = normalize_recommendation("Walk to nearby destinations")
    assert a.id != b.id


def test_category_keyword_tie_is_deterministic():
    a = normalize_category("", title="Energy efficient electric vehicle")
    b = normalize_category("", title="Energy efficient electric vehicle")
    assert a == b


def test_empty_title_mapping_receives_stable_fallback():
    first = normalize_recommendation({"category": "energy"})
    second = normalize_recommendation({"category": "energy"})
    assert first.id == second.id


def test_non_mapping_object_is_supported():
    class RecommendationObject:
        id = "object-1"
        title = "LED lighting"
        description = "Use LED bulbs"
        category = "energy"

    item = normalize_recommendation(RecommendationObject())
    assert item.id == "object-1"
    assert item.category == "electricity"


def test_recommendation_matching_uses_aliases():
    assert recommendation_matches_category({"title": "LED", "category": "energy"}, "electricity")


def test_filtering_is_stable():
    items = [
        rec("2", "Solar", "energy"),
        rec("1", "LED", "energy"),
        rec("3", "Bus", "transport"),
    ]
    filtered = filter_recommendations_by_category(items, "energy")
    assert [item.id for item in filtered] == ["1", "2"]


def test_feedback_category_does_not_override_recommendation_category():
    items = [rec("1", "LED", "energy")]
    history = recommendation_history(items, [event("1", "completed", "transport")])
    assert history["1"]["completed"] == 1


def test_store_limit_is_capped(tmp_path: Path):
    db = tmp_path / "coverage.db"
    store = RecommendationCoverageStore(str(db))
    for _ in range(3):
        store.save(build_coverage_report({"energy": 100}, [], user_id=1))
    assert len(store.list_reports(1, limit=1000)) == 3


def test_report_payload_contains_engine_version():
    report = build_coverage_report({}, [])
    assert report.metadata["engine"] == "recommendation_coverage_v1"


def test_gap_follow_up_is_actionable():
    report = build_coverage_report({"energy": 500}, [])
    assert report.gaps
    assert all(gap.suggested_follow_up for gap in report.gaps)


def test_status_bad_data_does_not_raise():
    report = build_coverage_report(
        {"energy": "not-a-number", "transport": None},
        [{"title": None, "category": None}],
    )
    assert report.recommendation_count == 1


def test_large_recommendation_list_is_supported():
    recommendations = [
        rec(str(i), f"Action {i}", "energy" if i % 2 == 0 else "transport")
        for i in range(500)
    ]
    report = build_coverage_report({"energy": 500, "transport": 500}, recommendations)
    assert report.recommendation_count == 500
    assert report.recommendation_diversity > 0


def test_duplicate_ids_do_not_change_category_count():
    report = build_coverage_report(
        {"energy": 100},
        [rec("same", "LED", "energy"), rec("same", "Solar", "energy")],
    )
    assert report.category_count >= 1
    assert report.duplicate_ids == ("same",)


def test_completed_recommendation_gap_has_expected_code():
    report = build_coverage_report(
        {"energy": 500},
        [rec("1", "LED", "energy")],
        feedback=[event("1", "completed")],
    )
    assert "COMPLETED_RECOMMENDATION_GAP" in gap_codes(report)


def test_repetition_gap_has_expected_code():
    report = build_coverage_report(
        {"energy": 500},
        [rec("1", "LED", "energy"), rec("2", "LED", "energy")],
    )
    assert "REPEATED_RECOMMENDATIONS" in gap_codes(report)


def test_summary_top_gap_is_none_when_no_gaps():
    recommendations = [
        rec("1", "LED", "energy"),
        rec("2", "Solar", "energy"),
        rec("3", "Thermostat", "energy"),
    ]
    report = build_coverage_report({"energy": 100}, recommendations)
    assert summarize_coverage(report)["top_gap"] is None
