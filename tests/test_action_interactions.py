"""Tests for the sustainability action interaction analyzer."""
from __future__ import annotations

import json
import sqlite3

import pytest

from src.utils.action_interactions import (
    ActionInteractionReport,
    ImpactRange,
    Interaction,
    SCHEMA_VERSION,
    SustainabilityAction,
    action_statuses,
    analyze_action_set,
    analyze_interactions,
    build_relationship_graph,
    calculate_combined_impact,
    calculate_diminishing_returns,
    calculate_execution_order,
    calculate_independent_impact,
    compare_reports,
    create_persistence_schema,
    delete_report,
    dependency_depth,
    detect_dependency_cycles,
    deserialize_report,
    estimate_sequential_path,
    explain_action,
    find_conflicts,
    find_dependencies,
    infer_relationships,
    interaction_matrix,
    load_reports,
    normalize_actions,
    rank_execution_candidates,
    report_hash,
    resolve_dependency_chain,
    save_report,
    select_non_conflicting,
    serialize_report,
    validate_report_document,
)


BASE = [
    {"id": "insulate", "name": "Improve insulation", "category": "Energy", "impact_low": 100, "impact_high": 200},
    {"id": "heat", "name": "Optimize heating", "category": "Energy", "impact_low": 80, "impact_high": 160, "dependencies": ["insulate"]},
    {"id": "monitor", "name": "Monitor energy", "category": "Energy", "impact_low": 40, "impact_high": 80, "overlaps": ["heat"]},
    {"id": "car", "name": "Drive less", "category": "Transportation", "impact_low": 200, "impact_high": 300},
    {"id": "fly", "name": "Reduce flights", "category": "Transportation", "impact_low": 150, "impact_high": 250, "conflicts": ["car"], "evidence": "survey"},
    {"id": "bike", "name": "Cycle commute", "category": "Transportation", "impact_low": 100, "impact_high": 150, "synergies": ["car"]},
]


def test_action_normalization_and_aliases():
    actions = normalize_actions([{"title": "LED bulbs", "category": "Energy", "impact": 50}])
    assert len(actions) == 1
    assert actions[0].impact_low == 50
    assert actions[0].impact_high == 50
    assert actions[0].id


def test_duplicate_action_ids_are_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        normalize_actions([BASE[0], BASE[0]])


def test_impact_range_reorders_inverted_bounds():
    action = SustainabilityAction.from_mapping({"id": "x", "name": "X", "impact_low": 200, "impact_high": 100})
    assert action.impact_low == 100
    assert action.impact_high == 200


def test_missing_impact_stays_unknown():
    result = calculate_independent_impact(["insulate", "unknown"], BASE)
    assert not result.available
    assert result.low is None


def test_independent_impact_sums_ranges():
    result = calculate_independent_impact(["insulate", "heat"], BASE)
    assert result.available
    assert result.low == 180
    assert result.high == 360


def test_dependency_chain_is_topological():
    chain = resolve_dependency_chain("heat", BASE)
    assert chain == ["insulate", "heat"]
    assert dependency_depth("heat", BASE) == 1


def test_execution_order_places_prerequisite_first():
    assert calculate_execution_order(["heat", "insulate"], BASE) == ["insulate", "heat"]


def test_execution_order_is_deterministic_for_independent_actions():
    first = calculate_execution_order(["car", "fly"], BASE)
    second = calculate_execution_order(["fly", "car"], BASE)
    assert first == second == ["car", "fly"]


def test_dependency_cycle_detection():
    actions = [
        {"id": "a", "name": "A", "dependencies": ["b"]},
        {"id": "b", "name": "B", "dependencies": ["a"]},
    ]
    cycles = detect_dependency_cycles(actions)
    assert cycles


def test_dependency_cycle_blocks_execution_order():
    with pytest.raises(ValueError):
        calculate_execution_order(["a", "b"], [
            {"id": "a", "name": "A", "dependencies": ["b"]},
            {"id": "b", "name": "B", "dependencies": ["a"]},
        ])


def test_find_dependencies_marks_uncompleted_prerequisite():
    findings = find_dependencies(["heat"], BASE, completed_ids=[])
    assert findings[0].prerequisite_id == "insulate"
    assert findings[0].satisfied


def test_completed_dependency_is_satisfied():
    findings = find_dependencies(["heat"], BASE, completed_ids=["insulate"])
    assert findings[0].satisfied


def test_missing_dependency_is_reported():
    findings = find_dependencies(["missingdep"], [{"id": "missingdep", "name": "X", "dependencies": ["nope"]}])
    assert not findings[0].satisfied
    assert "not present" in findings[0].rationale


def test_conflicts_are_deduplicated():
    conflicts = find_conflicts(["car", "fly"], BASE)
    assert len(conflicts) == 1
    assert conflicts[0].severity == 1


def test_conflict_absent_when_only_one_selected():
    assert find_conflicts(["car"], BASE) == []


def test_relationship_inference():
    relations = infer_relationships(BASE)
    kinds = {item.relationship for item in relations}
    assert {"dependency", "conflict", "overlap", "synergy"}.issubset(kinds)


def test_relationship_graph_has_all_nodes():
    graph = build_relationship_graph(BASE)
    assert set(graph) == {item["id"] for item in BASE}


def test_overlap_reduces_combined_high_end():
    combined = calculate_combined_impact(["heat", "monitor"], BASE)
    independent = calculate_independent_impact(["heat", "monitor"], BASE)
    assert combined.available
    assert independent.available
    assert combined.high < independent.high


def test_synergy_can_increase_combined_impact():
    combined = calculate_combined_impact(["car", "bike"], BASE)
    independent = calculate_independent_impact(["car", "bike"], BASE)
    assert combined.high > independent.high


def test_diminishing_returns_are_bounded():
    factors = calculate_diminishing_returns(["insulate", "heat", "monitor"], BASE)
    assert factors["insulate"] == 1
    assert 0 < factors["heat"] < 1
    assert 0 < factors["monitor"] < 1


def test_different_categories_do_not_diminish_each_other():
    factors = calculate_diminishing_returns(["insulate", "car"], BASE)
    assert factors["insulate"] == 1
    assert factors["car"] == 1


def test_blocked_action_requires_prerequisite():
    report = analyze_action_set(["heat"], BASE)
    assert src.reporting.report.blocked_action_ids == ["heat"]


def test_completed_prerequisite_unblocks_action():
    report = analyze_action_set(["heat"], BASE, completed_ids=["insulate"])
    assert src.reporting.report.blocked_action_ids == []


def test_report_contains_execution_order():
    report = analyze_action_set(["heat", "insulate"], BASE, completed_ids=["insulate"])
    assert src.reporting.report.execution_order == ["insulate", "heat"]


def test_report_contains_conflict_warning():
    report = analyze_action_set(["car", "fly"], BASE)
    assert src.reporting.report.conflicts
    assert any("Conflicting" in warning for warning in src.reporting.report.warnings)


def test_report_unknown_ids_are_ignored_and_warned():
    report = analyze_action_set(["car", "nope"], BASE)
    assert src.reporting.report.selected_action_ids == ["car"]
    assert any("Unknown" in warning for warning in src.reporting.report.warnings)


def test_report_has_explanations():
    report = analyze_action_set(["heat", "insulate"], BASE)
    assert src.reporting.report.explanations


def test_serialization_round_trip():
    report = analyze_action_set(["insulate", "heat", "monitor"], BASE)
    payload = serialize_report(report)
    restored = deserialize_report(payload)
    assert restored.to_dict() == src.reporting.report.to_dict()


def test_compact_serialization_is_json():
    report = analyze_action_set(["car"], BASE)
    parsed = json.loads(serialize_report(report, pretty=False))
    assert parsed["schema_version"] == SCHEMA_VERSION


def test_invalid_schema_is_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        deserialize_report({"schema_version": "9.0", "generated_at": "x", "selected_action_ids": [], "execution_order": [], "blocked_action_ids": []})


def test_validation_reports_missing_fields():
    errors = validate_report_document({"schema_version": SCHEMA_VERSION})
    assert "Missing required field: generated_at" in errors


def test_report_hash_is_stable():
    report = analyze_action_set(["car"], BASE)
    assert report_hash(report) == report_hash(deserialize_report(serialize_report(report)))


def test_compare_reports_detects_added_removed():
    old = analyze_action_set(["car"], BASE)
    new = analyze_action_set(["car", "bike"], BASE)
    diff = compare_reports(old, new)
    assert diff["added_actions"] == ["bike"]
    assert diff["removed_actions"] == []


def test_compare_reports_detects_order_change():
    old = analyze_action_set(["heat"], BASE)
    new = analyze_action_set(["heat", "insulate"], BASE)
    assert new.execution_order != old.execution_order
    assert compare_reports(old, new)["execution_order_changed"]


def test_action_statuses():
    statuses = action_statuses(["heat", "insulate"], BASE, completed_ids=["insulate"])
    assert statuses == {"heat": "selected", "insulate": "completed"}


def test_interaction_matrix_contains_overlap():
    matrix = interaction_matrix(["heat", "monitor"], BASE)
    assert matrix[0]["relationship"] == "overlap"


def test_analyze_interactions_contains_adjustment():
    findings = analyze_interactions(["heat", "monitor"], BASE)
    assert findings[0].adjustment_low is not None
    assert findings[0].adjustment_low < 0


def test_sequential_path_is_ordered():
    path = estimate_sequential_path(["heat", "insulate"], BASE)
    assert [row["action_id"] for row in path] == ["insulate", "heat"]
    assert path[-1]["position"] == 2


def test_explain_action_contains_relationships():
    explanation = explain_action("heat", BASE)
    assert explanation["action"]["name"] == "Optimize heating"
    assert "insulate" in explanation["prerequisites"]


def test_non_conflicting_selection_skips_conflicting_alternative():
    selected = select_non_conflicting(BASE, ["car", "fly", "bike"])
    assert selected == ["car", "bike"]


def test_execution_candidate_ranking_returns_all():
    ranked = rank_execution_candidates(BASE, ["heat", "insulate", "car"])
    assert set(ranked) == {"heat", "insulate", "car"}


def test_persistence_schema_can_be_created():
    conn = sqlite3.connect(":memory:")
    create_persistence_schema(conn)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert ("action_interaction_reports",) in tables
    conn.close()


def test_save_and_load_report(tmp_path):
    db = tmp_path / "interaction.db"
    report = analyze_action_set(["car", "bike"], BASE)
    record_id = save_report(report, user_id=7, database_path=str(db))
    assert record_id > 0
    loaded = load_reports(user_id=7, database_path=str(db))
    assert len(loaded) == 1
    assert loaded[0].selected_action_ids == ["car", "bike"]


def test_save_is_idempotent_for_same_report(tmp_path):
    db = tmp_path / "interaction.db"
    report = analyze_action_set(["car"], BASE)
    first = save_report(report, database_path=str(db))
    second = save_report(report, database_path=str(db))
    assert first == second
    assert len(load_reports(database_path=str(db))) == 1


def test_delete_report(tmp_path):
    db = tmp_path / "interaction.db"
    report = analyze_action_set(["car"], BASE)
    record_id = save_report(report, database_path=str(db))
    assert delete_report(record_id, database_path=str(db))
    assert load_reports(database_path=str(db)) == []


def test_delete_unknown_report_is_false(tmp_path):
    db = tmp_path / "interaction.db"
    assert not delete_report(999, database_path=str(db))


def test_load_limit():
    assert load_reports(database_path=":memory:", limit=0) == []


def test_action_to_dict():
    action = SustainabilityAction.from_mapping(BASE[0])
    assert action.to_dict()["id"] == "insulate"


def test_interaction_validates_relationship():
    with pytest.raises(ValueError):
        Interaction("a", "b", "not-a-real-relation")


def test_impact_range_midpoint():
    assert ImpactRange(10, 20, True, "x").midpoint == 15
    assert ImpactRange(None, None, False, "x").midpoint is None


def test_no_impact_in_combined_report_is_honest():
    actions = [{"id": "a", "name": "A", "impact_low": 10, "impact_high": 20}, {"id": "b", "name": "B"}]
    report = analyze_action_set(["a", "b"], actions)
    assert not src.reporting.report.combined_impact.available
    assert "unavailable" in src.reporting.report.combined_impact.label.lower()


def test_completed_action_can_still_be_analyzed():
    completed = [dict(BASE[0], completed=True)] + BASE[1:]
    report = analyze_action_set(["insulate", "heat"], completed_ids=["insulate"], actions=completed)
    assert src.reporting.report.selected_action_ids == ["insulate", "heat"]


# Additional edge-case coverage keeps the analyzer deterministic and safe.
@pytest.mark.parametrize("value", [None, "", "not-a-number", float("nan"), float("inf")])
def test_invalid_numeric_values_become_unknown(value):
    action = SustainabilityAction.from_mapping({"id": "x", "name": "X", "impact_low": value, "impact_high": value})
    assert action.impact_low is None
    assert action.impact_high is None


@pytest.mark.parametrize("difficulty", ["easy", "moderate", "medium", "hard", "advanced", "unknown"])
def test_difficulty_is_normalized(difficulty):
    action = SustainabilityAction.from_mapping({"id": "x", "name": "X", "difficulty": difficulty})
    assert action.difficulty == difficulty


def test_unknown_dependency_does_not_crash_graph():
    graph = build_relationship_graph([{"id": "a", "name": "A", "dependencies": ["missing"]}])
    assert graph["a"] == []


def test_empty_action_set():
    report = analyze_action_set([], [])
    assert src.reporting.report.selected_action_ids == []
    assert src.reporting.report.execution_order == []
    assert not src.reporting.report.combined_impact.available


def test_empty_selection_with_catalog():
    report = analyze_action_set([], BASE)
    assert src.reporting.report.selected_action_ids == []


def test_report_schema_version():
    assert analyze_action_set(["car"], BASE).schema_version == "1.0"


def test_sequence_after_is_dependency_like():
    actions = [
        {"id": "a", "name": "A"},
        {"id": "b", "name": "B", "sequence_after": ["a"]},
    ]
    assert calculate_execution_order(["b", "a"], actions) == ["a", "b"]


def test_conflict_is_symmetric_for_selection():
    assert len(find_conflicts(["fly", "car"], BASE)) == 1


def test_report_serializes_nested_findings():
    report = analyze_action_set(["car", "fly", "bike"], BASE)
    payload = json.loads(serialize_report(report))
    assert payload["conflicts"]
    assert payload["interactions"]


def test_report_compare_impact_none_is_safe():
    old = analyze_action_set(["car"], BASE)
    new = analyze_action_set(["car", "monitor"], [{"id": "car", "name": "Car", "impact_low": 1, "impact_high": 2}, {"id": "monitor", "name": "Monitor"}])
    diff = compare_reports(old, new)
    assert diff["impact_high_change"] is None


def test_relationship_source_is_explicit():
    assert all(item.source == "explicit" for item in infer_relationships(BASE))
