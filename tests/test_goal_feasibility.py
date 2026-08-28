
"""Tests for the Sustainability Goal Conflict & Feasibility Analyzer."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

import pytest

from src.utils.goal_feasibility import (
    ACHIEVED,
    AT_RISK,
    CONFLICT_CONFLICTING_ACTIONS,
    CONFLICT_DEPENDENCY,
    CONFLICT_DUPLICATE_GOAL,
    CONFLICT_IMPOSSIBLE_TIMELINE,
    CONFLICT_INSUFFICIENT_HISTORY,
    CONFLICT_OVERLAPPING_TARGET,
    FEASIBLE,
    INSUFFICIENT_DATA,
    UNLIKELY,
    GoalFeasibilityValidationError,
    analyze_goal_feasibility,
    build_combined_reduction_summary,
    build_feasibility_report,
    calculate_goal_feasibility,
    detect_action_conflicts,
    detect_dependencies,
    detect_dependency_cycles,
    detect_duplicates,
    detect_history_constraints,
    detect_overlapping_goals,
    detect_timeline_conflicts,
    normalize_actions,
    normalize_assessments,
    normalize_goal,
    normalize_goals,
    observed_reduction_pace,
    persist_feasibility_report,
    report_id,
    required_monthly_reduction,
    reduction_percent,
    serialize_feasibility_report,
    total_reduction,
)


BASE = date(2026, 1, 1)


def goal(
    goal_id="g1",
    category="Transportation",
    baseline=5000,
    target=3000,
    start=BASE,
    end=date(2027, 1, 1),
    **extra,
):
    return {
        "id": goal_id,
        "user_id": 7,
        "title": f"{category} reduction",
        "category": category,
        "baseline_kg": baseline,
        "target_kg": target,
        "start_date": start,
        "target_date": end,
        "status": "active",
        **extra,
    }


def assessment(when, footprint, assessment_id=None, categories=None):
    return {
        "id": assessment_id or when.isoformat(),
        "date": when,
        "footprint": footprint,
        "categories": categories or {},
    }


def actions_for(goal_id, count=2, completed=1):
    rows = []
    for index in range(count):
        rows.append(
            {
                "id": f"a{index + 1}",
                "goal_ids": [goal_id],
                "category": "Transportation",
                "status": "completed" if index < completed else "planned",
            }
        )
    return rows


def test_normalize_goal_accepts_existing_shape():
    result = normalize_goal(goal("42"))
    assert result["id"] == "42"
    assert result["category"] == "Transportation"
    assert result["baseline_kg"] == 5000
    assert result["target_kg"] == 3000
    assert result["start_date"] == BASE


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"baseline_kg": 0}, "baseline"),
        ({"baseline_kg": -1}, "baseline"),
        ({"target_kg": 6000}, "target"),
        ({"target_kg": -1}, "target"),
        ({"start_date": None}, "start_date"),
        ({"target_date": BASE}, "target_date"),
    ],
)
def test_normalize_goal_rejects_invalid_inputs(changes, message):
    data = goal()
    data.update(changes)
    with pytest.raises(GoalFeasibilityValidationError) as exc:
        normalize_goal(data)
    assert message in str(exc.value)


def test_normalize_goal_supports_aliases_and_action_strings():
    data = goal(category="transport", actions="a1,a2", dependencies="g0", exclusive_with="g9")
    result = normalize_goal(data)
    assert result["category"] == "Transportation"
    assert result["actions"] == ["a1", "a2"]
    assert result["dependencies"] == ["g0"]
    assert result["exclusive_with"] == ["g9"]


def test_normalize_goals_skips_invalid_records_and_reports_reason():
    records, warnings = normalize_goals([goal(), {"id": "bad", "baseline_kg": -2}])
    assert len(records) == 1
    assert len(warnings) == 1
    assert "skipped" in warnings[0]


def test_normalize_assessments_supports_dicts_and_legacy_tuples():
    rows = [
        assessment(BASE, 5000),
        (2, (BASE + timedelta(days=30)).isoformat(), "car", 100, 200, "mixed", 1, 4800, 90),
    ]
    result = normalize_assessments(rows)
    assert len(result) == 2
    assert result[-1]["footprint"] == 4800


def test_normalize_assessments_discards_invalid_rows():
    result = normalize_assessments(
        [
            {"date": "not-a-date", "footprint": 100},
            {"date": BASE, "footprint": "nan"},
            ("too",),
            object(),
        ]
    )
    assert result == []


def test_normalize_actions_supports_strings():
    result = normalize_actions(
        [
            {"id": 1, "category": "energy", "status": "done", "goal_ids": "g1,g2"}
        ]
    )
    assert result[0]["category"] == "Electricity"
    assert result[0]["goal_ids"] == ["g1", "g2"]


def test_reduction_math():
    data = goal()
    assert total_reduction(data) == 2000
    assert reduction_percent(data) == pytest.approx(40)
    assert required_monthly_reduction(data) == pytest.approx(2000 / 12.0, rel=0.02)


def test_observed_reduction_pace_is_positive_when_footprint_falls():
    rows = [
        assessment(BASE, 5000),
        assessment(BASE + timedelta(days=30), 4900),
        assessment(BASE + timedelta(days=60), 4800),
    ]
    assert observed_reduction_pace(rows) > 0


def test_observed_reduction_pace_is_negative_when_footprint_rises():
    rows = [
        assessment(BASE, 5000),
        assessment(BASE + timedelta(days=30), 5100),
    ]
    assert observed_reduction_pace(rows) < 0


def test_observed_reduction_pace_needs_two_assessments():
    assert observed_reduction_pace([assessment(BASE, 5000)]) == 0


def test_duplicate_goals_are_critical():
    conflicts = detect_duplicates([goal("g1"), goal("g2")])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == CONFLICT_DUPLICATE_GOAL
    assert conflicts[0].severity == "CRITICAL"


def test_different_targets_are_not_duplicates():
    conflicts = detect_duplicates([goal("g1"), goal("g2", target=2500)])
    assert conflicts == []


def test_overlapping_same_category_goals_are_flagged():
    first = goal("g1", start=BASE, end=date(2027, 1, 1))
    second = goal("g2", start=date(2026, 6, 1), end=date(2027, 6, 1))
    conflicts = detect_overlapping_goals([first, second])
    assert conflicts[0].conflict_type == CONFLICT_OVERLAPPING_TARGET
    assert conflicts[0].overlap_kg == pytest.approx(2000)


def test_different_categories_can_overlap():
    conflicts = detect_overlapping_goals(
        [goal("g1", category="Transportation"), goal("g2", category="Energy")]
    )
    assert conflicts == []


def test_explicit_exclusive_goal_conflict():
    first = goal("g1", exclusive_with=["g2"])
    second = goal("g2")
    conflicts = detect_action_conflicts([first, second])
    assert any(item.conflict_type == CONFLICT_CONFLICTING_ACTIONS for item in conflicts)


def test_shared_conflicting_action_is_detected():
    first = goal("g1", actions=["a1"])
    second = goal("g2", actions=["a2"])
    actions = [
        {"id": "a1", "goal_ids": ["g1"], "conflicts": ["a2"]},
        {"id": "a2", "goal_ids": ["g2"], "conflicts": ["a1"]},
    ]
    conflicts = detect_action_conflicts([first, second], normalize_actions(actions))
    assert any(item.conflict_type == CONFLICT_CONFLICTING_ACTIONS for item in conflicts)


def test_timeline_detects_expired_goal():
    expired = goal("g1", end=BASE)
    conflicts = detect_timeline_conflicts([expired], BASE + timedelta(days=1))
    assert any(item.conflict_type == CONFLICT_IMPOSSIBLE_TIMELINE for item in conflicts)


def test_timeline_detects_excessive_reduction_ceiling():
    impossible = goal("g1", baseline=1000, target=0, category="Diet")
    conflicts = detect_timeline_conflicts([impossible], BASE)
    assert any(item.conflict_type == CONFLICT_IMPOSSIBLE_TIMELINE for item in conflicts)


def test_custom_reduction_ceiling_is_respected():
    custom = goal("g1", baseline=1000, target=600, max_reduction_pct=30)
    conflicts = detect_timeline_conflicts([custom], BASE)
    assert any(item.conflict_type == CONFLICT_IMPOSSIBLE_TIMELINE for item in conflicts)


def test_history_constraint_for_short_history():
    conflicts = detect_history_constraints([goal()], [assessment(BASE, 5000)])
    assert conflicts[0].conflict_type == CONFLICT_INSUFFICIENT_HISTORY


def test_no_history_constraint_for_two_assessments():
    rows = [assessment(BASE, 5000), assessment(BASE + timedelta(days=30), 4900)]
    assert detect_history_constraints([goal()], rows) == []


def test_dependencies_are_satisfied_by_completed_goal():
    first = goal("g1", target=4500, status="completed")
    second = goal("g2", dependencies=["g1"])
    result = detect_dependencies([first, second])
    dep = next(item for item in result if item.goal_id == "g2")
    assert dep.satisfied is True


def test_missing_dependency_is_unsatisfied():
    result = detect_dependencies([goal("g2", dependencies=["missing"])])
    assert result[0].satisfied is False
    assert "missing" in result[0].reason


def test_dependency_cycle_is_detected():
    first = goal("g1", dependencies=["g2"])
    second = goal("g2", dependencies=["g1"])
    conflicts = detect_dependency_cycles([first, second])
    assert any(item.conflict_type == CONFLICT_DEPENDENCY for item in conflicts)


def test_dependency_without_cycle_is_clean():
    first = goal("g1")
    second = goal("g2", dependencies=["g1"])
    assert detect_dependency_cycles([first, second]) == []


def test_combined_reduction_does_not_double_count_same_category():
    result = build_combined_reduction_summary([goal("g1"), goal("g2", target=2500)])
    assert result["gross_reduction_kg"] == 4500
    assert result["conservative_reduction_kg"] == 2500
    assert result["potential_double_counted_kg"] == 2000


def test_supporting_action_counts():
    result = calculate_goal_feasibility(
        goal("g1", actions=["a1", "a2"]),
        [assessment(BASE, 5000), assessment(BASE + timedelta(days=30), 4800)],
        actions_for("g1", 2, 1),
    )
    assert result.supporting_actions == 2
    assert result.completed_supporting_actions == 1


def test_feasibility_with_good_history():
    rows = [
        assessment(BASE, 5000),
        assessment(BASE + timedelta(days=90), 4500),
        assessment(BASE + timedelta(days=180), 4000),
    ]
    result = calculate_goal_feasibility(goal(), rows, actions_for("g1", 3, 2))
    assert result.status in {FEASIBLE, AT_RISK}
    assert result.observed_reduction_kg_per_month > 0


def test_feasibility_without_history_is_insufficient():
    result = calculate_goal_feasibility(goal(), [])
    assert result.status == INSUFFICIENT_DATA
    assert result.current_kg is None
    assert result.projected_reduction_kg is None


def test_achieved_goal_is_detected():
    rows = [
        assessment(BASE, 5000),
        assessment(BASE + timedelta(days=30), 2900),
    ]
    result = calculate_goal_feasibility(goal(), rows)
    assert result.status == ACHIEVED


def test_conflict_changes_goal_risk():
    clean = calculate_goal_feasibility(goal(), [assessment(BASE, 5000), assessment(BASE + timedelta(days=30), 4900)])
    conflict = detect_duplicates([goal("g1"), goal("g2")])
    risky = calculate_goal_feasibility(goal("g1"), [assessment(BASE, 5000), assessment(BASE + timedelta(days=30), 4900)], conflicts=conflict)
    assert risky.risk_score > clean.risk_score


def test_build_report_contains_all_sections():
    goals = [goal("g1"), goal("g2", category="Energy", baseline=4000, target=3000)]
    rows = [
        assessment(BASE, 9000),
        assessment(BASE + timedelta(days=60), 8600),
    ]
    report = build_feasibility_report(goals, rows, actions_for("g1", 2, 1), user_id=7, as_of=BASE)
    assert src.reporting.report.user_id == 7
    assert len(src.reporting.report.goals) == 2
    assert "combined_reduction" in src.reporting.report.metadata
    assert src.reporting.report.overall_score >= 0


def test_report_public_alias_matches_builder():
    report = analyze_goal_feasibility([goal()], [assessment(BASE, 5000)], user_id=3, as_of=BASE)
    assert src.reporting.report.user_id == 3
    assert len(src.reporting.report.goals) == 1


def test_report_deduplicates_duplicate_conflicts():
    duplicate = [goal("g1"), goal("g2")]
    report = build_feasibility_report(duplicate, [], as_of=BASE)
    keys = [(item.conflict_type, item.goal_ids, item.title) for item in src.reporting.report.conflicts]
    assert len(keys) == len(set(keys))


def test_report_serialization_is_valid_json():
    report = build_feasibility_report([goal()], [assessment(BASE, 5000)], as_of=BASE)
    payload = serialize_feasibility_report(report)
    data = json.loads(payload)
    assert data["overall_status"]
    assert data["goals"][0]["goal_id"] == "g1"


def test_report_serialization_is_deterministic():
    report = build_feasibility_report([goal()], [assessment(BASE, 5000)], as_of=BASE)
    assert serialize_feasibility_report(report) == serialize_feasibility_report(report)


def test_report_id_is_stable():
    report = build_feasibility_report([goal()], [assessment(BASE, 5000)], as_of=BASE)
    assert report_id(report) == report_id(report)
    assert len(report_id(report)) == 24


def test_report_metadata_records_validation_warnings():
    report = build_feasibility_report([goal(), {"id": "bad"}], [], as_of=BASE)
    assert src.reporting.report.metadata["validation_warnings"]


def test_empty_goal_set_is_insufficient():
    report = build_feasibility_report([], [], as_of=BASE)
    assert src.reporting.report.overall_status == INSUFFICIENT_DATA
    assert src.reporting.report.overall_score == 0


def test_multiple_categories_are_independent():
    report = build_feasibility_report(
        [
            goal("transport", "Transportation"),
            goal("energy", "Energy", baseline=4000, target=3200),
            goal("food", "Food", baseline=3000, target=2400),
        ],
        [assessment(BASE, 12000), assessment(BASE + timedelta(days=60), 11500)],
        as_of=BASE,
    )
    categories = {item.category for item in src.reporting.report.goals}
    assert categories == {"Transportation", "Electricity", "Diet"}


def test_status_is_deterministic_for_same_input():
    rows = [assessment(BASE, 5000), assessment(BASE + timedelta(days=30), 4900)]
    first = build_feasibility_report([goal()], rows, as_of=BASE + timedelta(days=30))
    second = build_feasibility_report([goal()], rows, as_of=BASE + timedelta(days=30))
    assert first.to_dict() == second.to_dict()


def test_goal_constraint_evidence_contains_baseline_and_target():
    result = calculate_goal_feasibility(goal(), [])
    names = {item.name for item in result.constraints}
    assert {"baseline", "target", "category"} <= names


def test_warning_for_missing_supporting_actions():
    result = calculate_goal_feasibility(
        goal("g1"),
        [assessment(BASE, 5000), assessment(BASE + timedelta(days=30), 4900)],
        [],
    )
    assert any("supporting action" in warning for warning in result.warnings)


def test_completed_actions_reduce_support_risk():
    planned = calculate_goal_feasibility(
        goal("g1", actions=["a1", "a2"]),
        [assessment(BASE, 5000), assessment(BASE + timedelta(days=30), 4900)],
        actions_for("g1", 2, 0),
    )
    completed = calculate_goal_feasibility(
        goal("g1", actions=["a1", "a2"]),
        [assessment(BASE, 5000), assessment(BASE + timedelta(days=30), 4900)],
        actions_for("g1", 2, 2),
    )
    assert completed.risk_score < planned.risk_score


def test_future_target_has_positive_remaining_days():
    result = calculate_goal_feasibility(goal(), [assessment(BASE, 5000)], as_of=BASE)
    assert result.time_remaining_days > 0


def test_projected_shortfall_never_negative():
    rows = [
        assessment(BASE, 5000),
        assessment(BASE + timedelta(days=30), 4500),
    ]
    result = calculate_goal_feasibility(goal(), rows, as_of=BASE + timedelta(days=30))
    assert result.projected_shortfall_kg is None or result.projected_shortfall_kg >= 0


def test_overlapping_conflict_contains_conservative_overlap():
    report = build_feasibility_report(
        [goal("g1"), goal("g2", target=2500)],
        [assessment(BASE, 5000), assessment(BASE + timedelta(days=30), 4900)],
        as_of=BASE,
    )
    overlap = next(item for item in src.reporting.report.conflicts if item.conflict_type == CONFLICT_OVERLAPPING_TARGET)
    assert overlap.overlap_kg is not None


def test_unknown_category_is_reported():
    unknown = goal("g1", category="Unknown niche category")
    report = build_feasibility_report([unknown], [assessment(BASE, 5000)], as_of=BASE)
    assert any(item.conflict_type == "UNSUPPORTED_CATEGORY" for item in src.reporting.report.conflicts)


def test_unsatisfied_dependency_generates_conflict():
    report = build_feasibility_report(
        [goal("g2", dependencies=["missing"])],
        [assessment(BASE, 5000)],
        as_of=BASE,
    )
    assert any(item.conflict_type == CONFLICT_DEPENDENCY for item in src.reporting.report.conflicts)


def test_report_persistence_round_trip():
    connection = sqlite3.connect(":memory:")
    report = build_feasibility_report([goal()], [assessment(BASE, 5000)], user_id=7, as_of=BASE)
    row_id = persist_feasibility_report(connection, report)
    assert row_id > 0
    rows = connection.execute("SELECT report_payload FROM goal_feasibility_reports").fetchall()
    assert len(rows) == 1
    assert json.loads(rows[0][0])["user_id"] == 7


def test_report_persistence_is_idempotent_for_same_snapshot():
    connection = sqlite3.connect(":memory:")
    report = build_feasibility_report([goal()], [assessment(BASE, 5000)], user_id=7, as_of=BASE)
    first = persist_feasibility_report(connection, report)
    second = persist_feasibility_report(connection, report)
    assert first == second
    assert connection.execute("SELECT COUNT(*) FROM goal_feasibility_reports").fetchone()[0] == 1


def test_report_persistence_separates_users():
    connection = sqlite3.connect(":memory:")
    first = build_feasibility_report([goal()], [assessment(BASE, 5000)], user_id=1, as_of=BASE)
    second = build_feasibility_report([goal()], [assessment(BASE, 5000)], user_id=2, as_of=BASE)
    persist_feasibility_report(connection, first)
    persist_feasibility_report(connection, second)
    assert connection.execute("SELECT COUNT(*) FROM goal_feasibility_reports").fetchone()[0] == 2


def test_goal_with_zero_target_can_be_valid_for_flights():
    data = goal(category="Flights", baseline=1000, target=0)
    normalized = normalize_goal(data)
    assert normalized["target_kg"] == 0


def test_empty_actions_are_safe():
    assert normalize_actions([]) == []


def test_legacy_assessment_order_is_sorted():
    rows = [
        assessment(BASE + timedelta(days=60), 4800),
        assessment(BASE, 5000),
    ]
    normalized = normalize_assessments(rows)
    assert normalized[0]["date"] == BASE


def test_same_day_assessments_do_not_create_fake_pace():
    rows = [assessment(BASE, 5000), assessment(BASE, 4000)]
    assert observed_reduction_pace(rows) == 0


def test_goal_id_fallback_is_stable():
    result = normalize_goal(goal(goal_id=None), 14)
    assert result["id"] == "None"


def test_action_goal_links_can_select_actions_even_without_explicit_goal_actions():
    result = calculate_goal_feasibility(
        goal("g1"),
        [assessment(BASE, 5000), assessment(BASE + timedelta(days=30), 4900)],
        [{"id": "a1", "goal_ids": ["g1"], "status": "completed"}],
    )
    assert result.supporting_actions == 1
    assert result.completed_supporting_actions == 1


def test_multiple_critical_conflicts_raise_risk():
    first = goal("g1", exclusive_with=["g2"])
    second = goal("g2", exclusive_with=["g1"])
    report = build_feasibility_report([first, second], [], as_of=BASE)
    assert any(item.status == UNLIKELY for item in src.reporting.report.goals)


def test_recommendations_are_explainable():
    report = build_feasibility_report(
        [goal("g1"), goal("g2")],
        [assessment(BASE, 5000)],
        as_of=BASE,
    )
    assert src.reporting.report.recommendations
    assert all(isinstance(item, str) for item in src.reporting.report.recommendations)


def test_report_has_engine_version():
    report = build_feasibility_report([goal()], [], as_of=BASE)
    assert src.reporting.report.metadata["engine_version"] == "1.0"


def test_json_report_contains_no_python_date_objects():
    report = build_feasibility_report([goal()], [], as_of=BASE)
    payload = serialize_feasibility_report(report)
    assert "datetime.date" not in payload
    assert "2026-01-01" in payload


def test_goal_status_string_does_not_change_feasibility_math():
    first = goal("g1", status="active")
    second = goal("g1", status="archived")
    a = normalize_goal(first)
    b = normalize_goal(second)
    assert a["baseline_kg"] == b["baseline_kg"]
    assert a["target_kg"] == b["target_kg"]


def test_explicit_dependency_completion_uses_status():
    first = goal("g1", status="achieved")
    second = goal("g2", dependencies=["g1"])
    dependency = detect_dependencies([first, second])[-1]
    assert dependency.satisfied


def test_conflict_order_is_stable():
    goals = [goal("g2"), goal("g1")]
    first = build_feasibility_report(goals, [], as_of=BASE)
    second = build_feasibility_report(list(reversed(goals)), [], as_of=BASE)
    assert [(c.conflict_type, c.goal_ids) for c in first.conflicts] == [
        (c.conflict_type, c.goal_ids) for c in second.conflicts
    ]


def test_category_aliases_cover_common_taxonomy():
    for value in ["transport", "energy", "food", "water", "waste", "shopping"]:
        result = normalize_goal(goal(category=value))
        assert result["category"] in {
            "Transportation",
            "Electricity",
            "Diet",
            "Water",
            "Waste",
            "Shopping",
        }


def test_goal_with_far_future_target_is_not_marked_expired():
    conflicts = detect_timeline_conflicts([goal()], BASE)
    assert not any(item.title == "Goal deadline has passed" for item in conflicts)


def test_goal_with_high_but_allowed_reduction_is_not_ceiling_conflict():
    data = goal(category="Flights", baseline=1000, target=100)
    conflicts = detect_timeline_conflicts([data], BASE)
    assert not any(item.title == "Requested reduction exceeds feasibility ceiling" for item in conflicts)


def test_build_combined_summary_empty():
    result = build_combined_reduction_summary([])
    assert result["gross_reduction_kg"] == 0
    assert result["categories"] == []


def test_goal_feasibility_exposes_projection():
    rows = [
        assessment(BASE, 5000),
        assessment(BASE + timedelta(days=90), 4500),
    ]
    result = calculate_goal_feasibility(goal(), rows, as_of=BASE + timedelta(days=90))
    assert result.projected_reduction_kg is not None
    assert result.projected_shortfall_kg is not None


def test_feasibility_score_is_bounded():
    report = build_feasibility_report(
        [goal("g1"), goal("g2"), goal("g3")],
        [],
        as_of=BASE,
    )
    assert 0 <= src.reporting.report.overall_score <= 100


def test_per_goal_risk_is_bounded():
    report = build_feasibility_report([goal()], [], as_of=BASE)
    assert 0 <= src.reporting.report.goals[0].risk_score <= 100


def test_report_dict_is_plain_json_compatible():
    report = build_feasibility_report([goal()], [assessment(BASE, 5000)], as_of=BASE)
    payload = src.reporting.report.to_dict()
    json.dumps(payload)


def test_persistence_schema_has_user_date_index():
    connection = sqlite3.connect(":memory:")
    report = build_feasibility_report([goal()], [], as_of=BASE)
    persist_feasibility_report(connection, report)
    indexes = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_goal_feasibility_user_date'"
    ).fetchall()
    assert indexes


def test_invalid_json_payload_is_rejected_by_json_parser():
    from goal_feasibility import deserialize_feasibility_report
    with pytest.raises(json.JSONDecodeError):
        deserialize_feasibility_report("{invalid")


def test_deserialize_report_mapping_is_supported():
    from goal_feasibility import deserialize_feasibility_report
    result = deserialize_feasibility_report({"overall_status": "FEASIBLE"})
    assert result["overall_status"] == "FEASIBLE"
