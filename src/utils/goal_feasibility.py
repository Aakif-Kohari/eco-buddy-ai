
"""Sustainability Goal Conflict & Feasibility Analyzer.

An additive analytics layer for EcoBuddy's existing reduction src.utils.goals.  The
module never mutates goal or assessment records.  It normalizes the records
that existing pages/database helpers already produce, detects conflicts and
overlap, evaluates timeline/data/action-plan feasibility, and produces an
explainable report that can be persisted independently.

The core module intentionally avoids Streamlit imports so it can be used by
tests, dashboards, exports, and future APIs.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

DAYS_PER_MONTH = 365.25 / 12

FEASIBLE = "FEASIBLE"
AT_RISK = "AT_RISK"
UNLIKELY = "UNLIKELY"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
ACHIEVED = "ACHIEVED"

CONFLICT_OVERLAPPING_TARGET = "OVERLAPPING_TARGET"
CONFLICT_IMPOSSIBLE_TIMELINE = "IMPOSSIBLE_TIMELINE"
CONFLICT_CONFLICTING_ACTIONS = "CONFLICTING_ACTIONS"
CONFLICT_INSUFFICIENT_BASELINE = "INSUFFICIENT_BASELINE"
CONFLICT_UNSUPPORTED_CATEGORY = "UNSUPPORTED_CATEGORY"
CONFLICT_DUPLICATE_GOAL = "DUPLICATE_GOAL"
CONFLICT_DEPENDENCY = "DEPENDENCY_CONFLICT"
CONFLICT_INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"

CATEGORY_ALIASES = {
    "transport": "Transportation",
    "transportation": "Transportation",
    "mobility": "Transportation",
    "electricity": "Electricity",
    "energy": "Electricity",
    "power": "Electricity",
    "diet": "Diet",
    "food": "Diet",
    "flights": "Flights",
    "flight": "Flights",
    "water": "Water",
    "waste": "Waste",
    "shopping": "Shopping",
    "lifestyle": "General lifestyle",
    "general": "General lifestyle",
    "general lifestyle": "General lifestyle",
}
SUPPORTED_CATEGORIES = frozenset(CATEGORY_ALIASES.values())
REDUCTION_CEILINGS = {
    "Transportation": 0.80,
    "Electricity": 0.60,
    "Diet": 0.45,
    "Flights": 1.00,
    "Water": 0.60,
    "Waste": 0.70,
    "Shopping": 0.60,
    "General lifestyle": 0.50,
}
DEFAULT_CEILING = 0.50


class GoalFeasibilityValidationError(ValueError):
    """Raised when a goal cannot be safely normalized."""


@dataclass(frozen=True)
class GoalConstraint:
    """A normalized constraint used during feasibility evaluation."""

    name: str
    value: Any
    source: str
    severity: str = "INFO"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GoalConflict:
    """An explainable relationship between one or two src.utils.goals."""

    conflict_type: str
    severity: str
    goal_ids: tuple[str, ...]
    title: str
    explanation: str
    recommendation: str
    overlap_kg: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["goal_ids"] = list(self.goal_ids)
        return data


@dataclass(frozen=True)
class GoalDependency:
    """A prerequisite relationship between src.utils.goals."""

    goal_id: str
    depends_on: str
    satisfied: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GoalFeasibility:
    """Per-goal feasibility result with transparent evidence."""

    goal_id: str
    title: str
    category: str
    status: str
    risk_score: float
    baseline_kg: float
    target_kg: float
    required_reduction_kg: float
    required_reduction_pct: float
    current_kg: float | None
    observed_reduction_kg_per_month: float
    required_reduction_kg_per_month: float
    projected_reduction_kg: float | None
    projected_shortfall_kg: float | None
    time_remaining_days: int
    supporting_actions: int
    completed_supporting_actions: int
    constraints: tuple[GoalConstraint, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["constraints"] = [item.to_dict() for item in self.constraints]
        data["warnings"] = list(self.warnings)
        return data


@dataclass
class FeasibilityReport:
    """Complete multi-goal feasibility src.reporting.report."""

    user_id: int | str | None
    analyzed_on: date
    overall_status: str
    overall_score: float
    goals: list[GoalFeasibility]
    conflicts: list[GoalConflict]
    dependencies: list[GoalDependency]
    recommendations: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "analyzed_on": self.analyzed_on.isoformat(),
            "overall_status": self.overall_status,
            "overall_score": self.overall_score,
            "goals": [goal.to_dict() for goal in self.goals],
            "conflicts": [item.to_dict() for item in self.conflicts],
            "dependencies": [item.to_dict() for item in self.dependencies],
            "recommendations": list(self.recommendations),
            "metadata": _json_safe(self.metadata),
        }


def _finite(value: Any, default: float = math.nan) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _date(value: Any, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip().replace(" ", "T")
        if not text:
            raise GoalFeasibilityValidationError(f"{field} must not be empty")
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            try:
                return datetime.strptime(text[:10], "%Y-%m-%d").date()
            except ValueError as exc:
                raise GoalFeasibilityValidationError(
                    f"{field} must be an ISO-8601 date"
                ) from exc
    raise GoalFeasibilityValidationError(f"{field} must be a date")


def _category(value: Any) -> str:
    text = " ".join(str(value or "").strip().lower().split())
    return CATEGORY_ALIASES.get(text, str(value or "Unknown").strip() or "Unknown")


def _goal_id(goal: Mapping[str, Any], fallback: int) -> str:
    value = goal.get("id", fallback)
    return str(value)


def _first(goal: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in goal and goal[key] is not None:
            return goal[key]
    return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "done", "completed"}


def normalize_goal(goal: Mapping[str, Any], fallback_id: int = 0) -> dict[str, Any]:
    """Normalize an existing EcoBuddy goal without mutating it."""
    baseline = _finite(_first(goal, "baseline_kg", "baseline"))
    target = _finite(_first(goal, "target_kg", "target"))
    start_raw = _first(goal, "start_date", "start")
    end_raw = _first(goal, "target_date", "end_date", "end")
    if not math.isfinite(baseline) or baseline <= 0:
        raise GoalFeasibilityValidationError("baseline_kg must be a positive finite number")
    if not math.isfinite(target) or target < 0:
        raise GoalFeasibilityValidationError("target_kg must be a non-negative finite number")
    if target >= baseline:
        raise GoalFeasibilityValidationError("target_kg must be below baseline_kg")
    if start_raw is None or end_raw is None:
        raise GoalFeasibilityValidationError("start_date and target_date are required")
    start = _date(start_raw, "start_date")
    end = _date(end_raw, "target_date")
    if end <= start:
        raise GoalFeasibilityValidationError("target_date must be after start_date")
    category = _category(_first(goal, "category", "area", "domain") or "General lifestyle")
    title = str(_first(goal, "title", "name", "goal_name") or f"{category} goal").strip()
    actions = _first(goal, "actions", "action_ids", "supporting_actions") or []
    if isinstance(actions, str):
        actions = [item.strip() for item in actions.split(",") if item.strip()]
    if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes)):
        actions = []
    dependencies = _first(goal, "depends_on", "dependency_ids", "dependencies") or []
    if isinstance(dependencies, str):
        dependencies = [item.strip() for item in dependencies.split(",") if item.strip()]
    if not isinstance(dependencies, Sequence) or isinstance(dependencies, (str, bytes)):
        dependencies = []
    exclusive_with = _first(goal, "exclusive_with", "conflicts_with") or []
    if isinstance(exclusive_with, str):
        exclusive_with = [item.strip() for item in exclusive_with.split(",") if item.strip()]
    strategy = str(_first(goal, "strategy", "method") or "").strip()
    max_reduction_pct = _finite(_first(goal, "max_reduction_pct", "maximum_reduction_pct"), math.nan)
    return {
        "id": _goal_id(goal, fallback_id),
        "user_id": goal.get("user_id"),
        "title": title,
        "category": category,
        "baseline_kg": baseline,
        "target_kg": target,
        "start_date": start,
        "target_date": end,
        "status": str(goal.get("status", "active")),
        "actions": [str(item) for item in actions],
        "dependencies": [str(item) for item in dependencies],
        "exclusive_with": [str(item) for item in exclusive_with],
        "strategy": strategy,
        "max_reduction_pct": max_reduction_pct,
        "metadata": dict(goal.get("metadata") or {}),
    }


def normalize_goals(goals: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Normalize all goals and return usable records plus validation warnings."""
    normalized: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, goal in enumerate(goals or []):
        try:
            normalized.append(normalize_goal(goal, index))
        except GoalFeasibilityValidationError as exc:
            warnings.append(f"Goal {index + 1} was skipped: {exc}")
    return normalized, warnings


def normalize_assessments(assessments: Iterable[Any]) -> list[dict[str, Any]]:
    """Normalize dict and legacy tuple assessment rows."""
    result: list[dict[str, Any]] = []
    for row in assessments or []:
        if isinstance(row, Mapping):
            raw_date = row.get("date", row.get("created_at"))
            footprint = row.get("footprint")
            categories = row.get("categories", row.get("contributors"))
            record_id = row.get("id")
        elif isinstance(row, (tuple, list)):
            if len(row) < 8:
                continue
            record_id, raw_date, footprint = row[0], row[1], row[7]
            categories = None
        else:
            continue
        try:
            record_date = _date(raw_date, "assessment date")
            number = _finite(footprint)
        except (GoalFeasibilityValidationError, TypeError, ValueError):
            continue
        if not math.isfinite(number):
            continue
        result.append({
            "id": record_id,
            "date": record_date,
            "footprint": number,
            "categories": categories if isinstance(categories, Mapping) else {},
        })
    result.sort(key=lambda item: (item["date"], str(item.get("id", ""))))
    return result


def normalize_actions(actions: Iterable[Any]) -> list[dict[str, Any]]:
    """Normalize action-plan records for goal support analysis."""
    result: list[dict[str, Any]] = []
    for index, row in enumerate(actions or []):
        if isinstance(row, Mapping):
            action_id = str(row.get("id", row.get("action_id", index)))
            category = _category(row.get("category", "General lifestyle"))
            status = str(row.get("status", "planned")).lower()
            goal_ids = row.get("goal_ids", row.get("goals", [])) or []
            if isinstance(goal_ids, str):
                goal_ids = [item.strip() for item in goal_ids.split(",") if item.strip()]
            result.append({
                "id": action_id,
                "category": category,
                "status": status,
                "goal_ids": [str(item) for item in goal_ids],
                "conflicts": [str(item) for item in (row.get("conflicts", []) or [])],
            })
    return result


def total_reduction(goal: Mapping[str, Any]) -> float:
    return float(goal["baseline_kg"]) - float(goal["target_kg"])


def reduction_percent(goal: Mapping[str, Any]) -> float:
    baseline = float(goal["baseline_kg"])
    return total_reduction(goal) / baseline * 100.0 if baseline else 0.0


def months_between(start: Any, end: Any) -> float:
    return max(0.0, (_date(end, "end") - _date(start, "start")).days / DAYS_PER_MONTH)


def required_monthly_reduction(goal: Mapping[str, Any]) -> float:
    months = months_between(goal["start_date"], goal["target_date"])
    return total_reduction(goal) / months if months else math.inf


def current_footprint(assessments: Iterable[Any]) -> float | None:
    records = normalize_assessments(assessments)
    return records[-1]["footprint"] if records else None


def observed_reduction_pace(assessments: Iterable[Any]) -> float:
    """Return positive kg/month when historical footprint is falling."""
    records = normalize_assessments(assessments)
    if len(records) < 2:
        return 0.0
    origin = records[0]["date"]
    xs = [(row["date"] - origin).days / DAYS_PER_MONTH for row in records]
    ys = [row["footprint"] for row in records]
    mean_x = mean(xs)
    mean_y = mean(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator <= 0:
        return 0.0
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    return -slope


def project_reduction(
    goal: Mapping[str, Any],
    assessments: Iterable[Any],
    as_of: date | None = None,
) -> tuple[float | None, float | None]:
    """Return projected reduction and projected final footprint."""
    current = current_footprint(assessments)
    if current is None:
        return None, None
    when = as_of or date.today()
    months = months_between(when, goal["target_date"])
    if months <= 0:
        return max(0.0, goal["baseline_kg"] - current), current
    pace = observed_reduction_pace(assessments)
    projected = max(0.0, current - pace * months)
    return max(0.0, goal["baseline_kg"] - projected), projected


def _interval_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> int:
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    return max(0, (end - start).days)


def _same_strategy(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    sa, sb = a.get("strategy", "").strip().lower(), b.get("strategy", "").strip().lower()
    return bool(sa and sb and sa == sb)


def _action_conflicts(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    a_conflicts = set(a.get("exclusive_with", []))
    b_conflicts = set(b.get("exclusive_with", []))
    return str(b["id"]) in a_conflicts or str(a["id"]) in b_conflicts


def detect_duplicates(goals: Sequence[Mapping[str, Any]]) -> list[GoalConflict]:
    """Detect exact or near-exact duplicate src.utils.goals."""
    conflicts: list[GoalConflict] = []
    for index, first in enumerate(goals):
        for second in goals[index + 1:]:
            same_category = first["category"] == second["category"]
            same_target = abs(first["target_kg"] - second["target_kg"]) < 0.01
            same_dates = first["start_date"] == second["start_date"] and first["target_date"] == second["target_date"]
            if same_category and same_target and same_dates:
                conflicts.append(GoalConflict(
                    CONFLICT_DUPLICATE_GOAL,
                    "CRITICAL",
                    (str(first["id"]), str(second["id"])),
                    "Duplicate goals",
                    f"Goals {first['id']} and {second['id']} describe the same category, target, and time window.",
                    "Keep one goal and archive or revise the duplicate.",
                ))
    return conflicts


def detect_overlapping_goals(goals: Sequence[Mapping[str, Any]]) -> list[GoalConflict]:
    """Detect reductions that overlap and may be double-counted."""
    conflicts: list[GoalConflict] = []
    for index, first in enumerate(goals):
        for second in goals[index + 1:]:
            if first["category"] != second["category"]:
                continue
            overlap_days = _interval_overlap(
                first["start_date"], first["target_date"],
                second["start_date"], second["target_date"],
            )
            if overlap_days <= 0:
                continue
            # If the two goals are materially different, their requested
            # reductions can still be compatible, but the shared category is
            # explicitly flagged so a combined dashboard does not add them twice.
            reduction = min(total_reduction(first), total_reduction(second))
            conflicts.append(GoalConflict(
                CONFLICT_OVERLAPPING_TARGET,
                "WARNING",
                (str(first["id"]), str(second["id"])),
                "Overlapping category targets",
                (
                    f"Both goals target {first['category']} during an overlapping "
                    f"{overlap_days}-day window. Their reductions may refer to the same "
                    "baseline emissions and should not be added automatically."
                ),
                "Treat the goals as linked targets or define separate baselines.",
                round(reduction, 2),
            ))
    return conflicts


def detect_action_conflicts(
    goals: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]] | None = None,
) -> list[GoalConflict]:
    """Detect explicit mutually exclusive strategies and action metadata conflicts."""
    conflicts: list[GoalConflict] = []
    action_map = {str(action["id"]): action for action in actions or []}
    for index, first in enumerate(goals):
        for second in goals[index + 1:]:
            if _action_conflicts(first, second):
                conflicts.append(GoalConflict(
                    CONFLICT_CONFLICTING_ACTIONS,
                    "CRITICAL",
                    (str(first["id"]), str(second["id"])),
                    "Explicitly conflicting goal strategies",
                    f"Goal {first['id']} and goal {second['id']} declare mutually exclusive strategies.",
                    "Choose one strategy or split the goals into alternatives.",
                ))
            first_actions = set(first.get("actions", []))
            second_actions = set(second.get("actions", []))
            for first_action_id in first_actions:
                first_action = action_map.get(str(first_action_id), {})
                first_conflicts = {str(item) for item in first_action.get("conflicts", [])}
                for second_action_id in second_actions:
                    second_action = action_map.get(str(second_action_id), {})
                    second_conflicts = {str(item) for item in second_action.get("conflicts", [])}
                    if str(second_action_id) in first_conflicts or str(first_action_id) in second_conflicts:
                        conflicts.append(GoalConflict(
                            CONFLICT_CONFLICTING_ACTIONS,
                            "CRITICAL",
                            (str(first["id"]), str(second["id"])),
                            "Conflicting supporting actions",
                            (
                                f"Supporting actions {first_action_id} and {second_action_id} "
                                "are explicitly marked as mutually conflicting."
                            ),
                            "Remove one conflicting action from the combined plan.",
                        ))
    return conflicts


def detect_unsupported_categories(goals: Sequence[Mapping[str, Any]]) -> list[GoalConflict]:
    """Flag categories that EcoBuddy's shared sustainability taxonomy cannot analyze."""
    conflicts: list[GoalConflict] = []
    for goal in goals:
        if goal["category"] not in SUPPORTED_CATEGORIES:
            conflicts.append(GoalConflict(
                CONFLICT_UNSUPPORTED_CATEGORY,
                "WARNING",
                (str(goal["id"]),),
                "Unsupported goal category",
                f"Category '{goal['category']}' is not in the shared sustainability taxonomy.",
                "Map the goal to an existing category before using feasibility calculations.",
            ))
    return conflicts


def detect_timeline_conflicts(
    goals: Sequence[Mapping[str, Any]],
    as_of: date | None = None,
) -> list[GoalConflict]:
    """Detect expired, zero-window, or implausibly aggressive timelines."""
    when = as_of or date.today()
    conflicts: list[GoalConflict] = []
    for goal in goals:
        months = months_between(goal["start_date"], goal["target_date"])
        requested_pct = reduction_percent(goal)
        ceiling = _finite(goal.get("max_reduction_pct"), math.nan)
        if not math.isfinite(ceiling):
            ceiling = REDUCTION_CEILINGS.get(goal["category"], DEFAULT_CEILING) * 100
        if goal["target_date"] <= when and goal["target_kg"] > 0:
            conflicts.append(GoalConflict(
                CONFLICT_IMPOSSIBLE_TIMELINE,
                "CRITICAL",
                (str(goal["id"]),),
                "Goal deadline has passed",
                f"The target date {goal['target_date'].isoformat()} is not in the future.",
                "Extend the deadline or close the goal as achieved/not achieved.",
            ))
        if months < 1:
            conflicts.append(GoalConflict(
                CONFLICT_IMPOSSIBLE_TIMELINE,
                "CRITICAL",
                (str(goal["id"]),),
                "Goal window is too short",
                "The configured goal window is shorter than one month.",
                "Use a longer measurement window so progress can be observed reliably.",
            ))
        if requested_pct > ceiling + 1e-9:
            conflicts.append(GoalConflict(
                CONFLICT_IMPOSSIBLE_TIMELINE,
                "CRITICAL",
                (str(goal["id"]),),
                "Requested reduction exceeds feasibility ceiling",
                (
                    f"The goal requests a {requested_pct:.1f}% reduction, while the "
                    f"configured ceiling for {goal['category']} is {ceiling:.1f}%."
                ),
                "Reduce the target, change the category/strategy, or document a custom ceiling.",
            ))
    return conflicts


def detect_history_constraints(
    goals: Sequence[Mapping[str, Any]],
    assessments: Sequence[Mapping[str, Any]],
) -> list[GoalConflict]:
    """Flag goals that cannot be evaluated from available assessment history."""
    conflicts: list[GoalConflict] = []
    if len(assessments) < 2:
        for goal in goals:
            conflicts.append(GoalConflict(
                CONFLICT_INSUFFICIENT_HISTORY,
                "WARNING",
                (str(goal["id"]),),
                "Insufficient assessment history",
                "Fewer than two usable assessments are available, so an observed reduction rate cannot be established.",
                "Complete another dated assessment before treating pace-based feasibility as reliable.",
            ))
    return conflicts


def detect_dependencies(goals: Sequence[Mapping[str, Any]]) -> list[GoalDependency]:
    """Resolve explicit goal prerequisites without mutating the goal records."""
    ids = {str(goal["id"]) for goal in goals}
    completed = {str(goal["id"]) for goal in goals if str(goal.get("status", "")).lower() in {"completed", "achieved"}}
    dependencies: list[GoalDependency] = []
    for goal in goals:
        for dependency in goal.get("dependencies", []):
            dep = str(dependency)
            dependencies.append(GoalDependency(
                str(goal["id"]),
                dep,
                dep in completed,
                "Prerequisite is marked completed." if dep in completed else (
                    "Prerequisite goal is missing." if dep not in ids else "Prerequisite goal is not completed."
                ),
            ))
    return dependencies


def detect_dependency_cycles(goals: Sequence[Mapping[str, Any]]) -> list[GoalConflict]:
    """Detect cycles in explicit dependency relationships."""
    graph = {str(goal["id"]): [str(item) for item in goal.get("dependencies", [])] for goal in goals}
    conflicts: list[GoalConflict] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def walk(node: str, path: list[str]) -> None:
        if node in visiting:
            cycle = path[path.index(node):] if node in path else path
            conflicts.append(GoalConflict(
                CONFLICT_DEPENDENCY,
                "CRITICAL",
                tuple(cycle),
                "Circular goal dependency",
                "Goals form a dependency cycle and therefore have no valid execution order.",
                "Remove at least one dependency from the cycle.",
            ))
            return
        if node in visited:
            return
        visiting.add(node)
        for child in graph.get(node, []):
            if child in graph:
                walk(child, path + [child])
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        walk(node, [node])
    unique: dict[tuple[str, ...], GoalConflict] = {}
    for conflict in conflicts:
        unique[conflict.goal_ids] = conflict
    return list(unique.values())


def _supporting_actions(goal: Mapping[str, Any], actions: Sequence[Mapping[str, Any]]) -> tuple[int, int]:
    ids = set(str(item) for item in goal.get("actions", []))
    selected = [
        action
        for action in actions
        if str(action["id"]) in ids
        or str(goal["id"]) in set(str(item) for item in action.get("goal_ids", []))
    ]
    completed = sum(1 for action in selected if action["status"] in {"completed", "done", "achieved"})
    return len(selected), completed


def _goal_constraints(
    goal: Mapping[str, Any],
    current: float | None,
    assessments: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]],
    conflicts: Sequence[GoalConflict],
) -> tuple[GoalConstraint, ...]:
    constraints: list[GoalConstraint] = []
    constraints.append(GoalConstraint("baseline", goal["baseline_kg"], "goal"))
    constraints.append(GoalConstraint("target", goal["target_kg"], "goal"))
    constraints.append(GoalConstraint("category", goal["category"], "goal"))
    constraints.append(GoalConstraint("time_window_months", round(months_between(goal["start_date"], goal["target_date"]), 2), "goal"))
    constraints.append(GoalConstraint("required_reduction_pct", round(reduction_percent(goal), 2), "goal"))
    constraints.append(GoalConstraint("assessment_count", len(assessments), "assessment_history"))
    if current is not None:
        constraints.append(GoalConstraint("current_footprint", round(current, 2), "assessment_history"))
    support, completed = _supporting_actions(goal, actions)
    constraints.append(GoalConstraint("supporting_actions", support, "action_plan"))
    constraints.append(GoalConstraint("completed_supporting_actions", completed, "action_plan"))
    for conflict in conflicts:
        if str(goal["id"]) in conflict.goal_ids:
            constraints.append(GoalConstraint(
                f"conflict:{conflict.conflict_type}",
                conflict.severity,
                "feasibility_engine",
                conflict.severity,
            ))
    return tuple(constraints)


def calculate_goal_feasibility(
    goal: Mapping[str, Any],
    assessments: Iterable[Any],
    actions: Iterable[Any] | None = None,
    conflicts: Sequence[GoalConflict] | None = None,
    as_of: date | None = None,
) -> GoalFeasibility:
    """Calculate a deterministic feasibility score for one normalized goal."""
    normalized = normalize_goal(goal)
    records = normalize_assessments(assessments)
    action_records = normalize_actions(actions or [])
    all_conflicts = list(conflicts or [])
    when = as_of or date.today()
    current = records[-1]["footprint"] if records else None
    required = total_reduction(normalized)
    required_pct = reduction_percent(normalized)
    months = months_between(normalized["start_date"], normalized["target_date"])
    required_pace = required / months if months else math.inf
    observed_pace = observed_reduction_pace(records)
    projected_reduction, projected_final = project_reduction(normalized, records, when)
    remaining_days = max(0, (normalized["target_date"] - when).days)
    support, completed = _supporting_actions(normalized, action_records)

    relevant = [item for item in all_conflicts if str(normalized["id"]) in item.goal_ids]
    critical = sum(1 for item in relevant if item.severity == "CRITICAL")
    warning = sum(1 for item in relevant if item.severity == "WARNING")
    risk = min(100.0, critical * 32.0 + warning * 12.0)
    warnings: list[str] = []

    if current is None:
        warnings.append("No assessment history is available for a current-footprint check.")
        risk += 15.0
    elif current > normalized["baseline_kg"] * 1.05:
        warnings.append("The latest footprint is above the goal baseline.")
        risk += 15.0

    if support == 0:
        warnings.append("No supporting action is explicitly linked to this goal.")
        risk += 10.0
    elif completed == 0:
        warnings.append("Supporting actions exist, but none are marked completed.")
        risk += 5.0

    if math.isfinite(required_pace) and required_pace > 0 and observed_pace > 0:
        pace_ratio = observed_pace / required_pace
        if pace_ratio >= 1.0:
            risk -= 12.0
        elif pace_ratio < 0.5:
            risk += 12.0
    elif len(records) < 2:
        risk += 8.0
    else:
        risk += 10.0

    for conflict in relevant:
        if conflict.conflict_type in {CONFLICT_DUPLICATE_GOAL, CONFLICT_DEPENDENCY}:
            risk += 10.0

    risk = max(0.0, min(100.0, risk))
    hard_conflict = any(item.severity == "CRITICAL" for item in relevant)
    unsupported = normalized["category"] not in SUPPORTED_CATEGORIES
    if unsupported:
        status = INSUFFICIENT_DATA
    elif hard_conflict:
        status = UNLIKELY
    elif current is not None and current <= normalized["target_kg"]:
        status = ACHIEVED
    elif len(records) < 2:
        status = INSUFFICIENT_DATA
    elif risk >= 65:
        status = UNLIKELY
    elif risk >= 35:
        status = AT_RISK
    else:
        status = FEASIBLE

    return GoalFeasibility(
        goal_id=str(normalized["id"]),
        title=normalized["title"],
        category=normalized["category"],
        status=status,
        risk_score=round(risk, 2),
        baseline_kg=round(normalized["baseline_kg"], 2),
        target_kg=round(normalized["target_kg"], 2),
        required_reduction_kg=round(required, 2),
        required_reduction_pct=round(required_pct, 2),
        current_kg=round(current, 2) if current is not None else None,
        observed_reduction_kg_per_month=round(observed_pace, 2),
        required_reduction_kg_per_month=round(required_pace, 2) if math.isfinite(required_pace) else 0.0,
        projected_reduction_kg=round(projected_reduction, 2) if projected_reduction is not None else None,
        projected_shortfall_kg=round(max(0.0, required - projected_reduction), 2) if projected_reduction is not None else None,
        time_remaining_days=remaining_days,
        supporting_actions=support,
        completed_supporting_actions=completed,
        constraints=_goal_constraints(normalized, current, records, action_records, relevant),
        warnings=tuple(warnings),
    )


def build_combined_reduction_summary(goals: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Show gross and de-duplicated reduction requests by category."""
    by_category: dict[str, list[dict[str, Any]]] = {}
    for goal in goals:
        by_category.setdefault(goal["category"], []).append(dict(goal))
    rows: list[dict[str, Any]] = []
    gross_total = 0.0
    conservative_total = 0.0
    for category, items in sorted(by_category.items()):
        gross = sum(total_reduction(item) for item in items)
        # A conservative combined estimate counts the largest reduction once
        # when multiple goals share the same category/baseline domain.
        conservative = max(total_reduction(item) for item in items)
        gross_total += gross
        conservative_total += conservative
        rows.append({
            "category": category,
            "goal_count": len(items),
            "gross_reduction_kg": round(gross, 2),
            "conservative_reduction_kg": round(conservative, 2),
            "overlap_kg": round(max(0.0, gross - conservative), 2),
        })
    return {
        "categories": rows,
        "gross_reduction_kg": round(gross_total, 2),
        "conservative_reduction_kg": round(conservative_total, 2),
        "potential_double_counted_kg": round(max(0.0, gross_total - conservative_total), 2),
    }


def rank_goal_risks(results: Iterable[GoalFeasibility]) -> list[GoalFeasibility]:
    """Return goals from highest to lowest risk with stable ID tie-breaking."""
    return sorted(results, key=lambda item: (-item.risk_score, item.goal_id))


def _overall_status(results: Sequence[GoalFeasibility], conflicts: Sequence[GoalConflict]) -> tuple[str, float]:
    if not results:
        return INSUFFICIENT_DATA, 0.0
    critical = sum(1 for item in conflicts if item.severity == "CRITICAL")
    score = sum(max(0.0, 100.0 - item.risk_score) for item in results) / len(results)
    score -= min(25.0, critical * 5.0)
    score = round(max(0.0, min(100.0, score)), 2)
    if any(item.status == UNLIKELY for item in results):
        status = UNLIKELY
    elif any(item.status == AT_RISK for item in results):
        status = AT_RISK
    elif any(item.status == INSUFFICIENT_DATA for item in results):
        status = INSUFFICIENT_DATA
    else:
        status = FEASIBLE
    return status, score


def build_recommendations(
    results: Sequence[GoalFeasibility],
    conflicts: Sequence[GoalConflict],
    dependencies: Sequence[GoalDependency],
) -> list[str]:
    """Generate explainable corrective guidance; never creates new goal data."""
    recommendations: list[str] = []
    if any(item.conflict_type == CONFLICT_DUPLICATE_GOAL for item in conflicts):
        src.ai.recommendations.append("Review duplicate goals and keep a single source of truth for each target.")
    if any(item.conflict_type == CONFLICT_OVERLAPPING_TARGET for item in conflicts):
        src.ai.recommendations.append("Do not add reductions from overlapping goals as if they were independent savings.")
    if any(item.conflict_type == CONFLICT_IMPOSSIBLE_TIMELINE for item in conflicts):
        src.ai.recommendations.append("Extend aggressive deadlines or reduce the requested target before committing to the pathway.")
    if any(not item.satisfied for item in dependencies):
        src.ai.recommendations.append("Complete prerequisite goals before treating dependent goals as fully supported.")
    for result in rank_goal_risks(results):
        if result.status in {AT_RISK, UNLIKELY}:
            src.ai.recommendations.append(
                f"Review '{result.title}': its feasibility risk is {result.risk_score:.0f}/100."
            )
    if any(result.status == INSUFFICIENT_DATA for result in results):
        src.ai.recommendations.append("Collect additional dated assessments before relying on pace-based feasibility.")
    if not recommendations:
        src.ai.recommendations.append("The current goal set has no detected critical feasibility blockers.")
    return recommendations


def build_feasibility_report(
    goals: Iterable[Mapping[str, Any]],
    assessments: Iterable[Any],
    actions: Iterable[Any] | None = None,
    user_id: int | str | None = None,
    as_of: date | None = None,
) -> FeasibilityReport:
    """Build the complete multi-goal analysis."""
    when = as_of or date.today()
    normalized, validation_warnings = normalize_goals(goals)
    records = normalize_assessments(assessments)
    action_records = normalize_actions(actions or [])

    conflicts: list[GoalConflict] = []
    conflicts.extend(detect_duplicates(normalized))
    conflicts.extend(detect_overlapping_goals(normalized))
    conflicts.extend(detect_action_conflicts(normalized, action_records))
    conflicts.extend(detect_unsupported_categories(normalized))
    conflicts.extend(detect_timeline_conflicts(normalized, when))
    conflicts.extend(detect_history_constraints(normalized, records))
    dependencies = detect_dependencies(normalized)
    conflicts.extend(detect_dependency_cycles(normalized))
    for dependency in dependencies:
        if not dependency.satisfied:
            conflicts.append(GoalConflict(
                CONFLICT_DEPENDENCY,
                "WARNING",
                (dependency.goal_id, dependency.depends_on),
                "Unsatisfied goal dependency",
                dependency.reason,
                "Complete or remove the prerequisite before relying on this goal.",
            ))

    # Canonicalize and de-duplicate conflict records deterministically so
    # reversing the input goal order cannot change the src.reporting.report.
    unique: dict[tuple[Any, ...], GoalConflict] = {}
    for conflict in conflicts:
        goal_ids = tuple(sorted(str(item) for item in conflict.goal_ids))
        canonical = GoalConflict(
            conflict.conflict_type,
            conflict.severity,
            goal_ids,
            conflict.title,
            conflict.explanation,
            conflict.recommendation,
            conflict.overlap_kg,
        )
        key = (
            canonical.conflict_type,
            canonical.severity,
            canonical.goal_ids,
            canonical.title,
        )
        unique[key] = canonical
    conflicts = sorted(
        unique.values(),
        key=lambda item: (item.severity != "CRITICAL", item.conflict_type, item.goal_ids),
    )

    results = [
        calculate_goal_feasibility(
            goal,
            records,
            action_records,
            conflicts,
            when,
        )
        for goal in normalized
    ]
    status, score = _overall_status(results, conflicts)
    recommendations = build_recommendations(results, conflicts, dependencies)
    metadata = {
        "goal_count": len(normalized),
        "assessment_count": len(records),
        "action_count": len(action_records),
        "validation_warnings": validation_warnings,
        "combined_reduction": build_combined_reduction_summary(normalized),
        "engine_version": "1.0",
    }
    return FeasibilityReport(
        user_id=user_id,
        analyzed_on=when,
        overall_status=status,
        overall_score=score,
        goals=results,
        conflicts=conflicts,
        dependencies=dependencies,
        recommendations=recommendations,
        metadata=metadata,
    )


def analyze_goal_feasibility(
    goals: Iterable[Mapping[str, Any]],
    assessments: Iterable[Any],
    actions: Iterable[Any] | None = None,
    user_id: int | str | None = None,
    as_of: date | None = None,
) -> FeasibilityReport:
    """Public entry point used by the Streamlit page and tests."""
    return build_feasibility_report(goals, assessments, actions, user_id, as_of)


def serialize_feasibility_report(report: FeasibilityReport) -> str:
    """Serialize a report to stable JSON."""
    return json.dumps(src.reporting.report.to_dict(), sort_keys=True, indent=2, default=str)


def deserialize_feasibility_report(payload: str | Mapping[str, Any]) -> dict[str, Any]:
    """Load JSON without executing or modifying any database state."""
    data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    if not isinstance(data, Mapping):
        raise GoalFeasibilityValidationError("Report payload must be an object")
    return dict(data)


def report_id(report: FeasibilityReport) -> str:
    """Stable content-derived identifier for a src.reporting.report."""
    payload = serialize_feasibility_report(report).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def ensure_report_table(connection: sqlite3.Connection) -> None:
    """Create only the analyzer's report table; never alter existing tables."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS goal_feasibility_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT NOT NULL UNIQUE,
            user_id TEXT,
            analyzed_on TEXT NOT NULL,
            overall_status TEXT NOT NULL,
            overall_score REAL NOT NULL,
            report_payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_goal_feasibility_user_date "
        "ON goal_feasibility_reports(user_id, analyzed_on)"
    )
    connection.commit()


def persist_feasibility_report(
    connection: sqlite3.Connection,
    report: FeasibilityReport,
) -> int:
    """Persist an immutable snapshot, replacing only an identical src.reporting.report."""
    ensure_report_table(connection)
    rid = report_id(report)
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO goal_feasibility_reports
        (report_id, user_id, analyzed_on, overall_status, overall_score, report_payload)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            rid,
            None if src.reporting.report.user_id is None else str(src.reporting.report.user_id),
            src.reporting.report.analyzed_on.isoformat(),
            src.reporting.report.overall_status,
            src.reporting.report.overall_score,
            serialize_feasibility_report(report),
        ),
    )
    connection.commit()
    if cursor.rowcount:
        return int(cursor.lastrowid)
    row = connection.execute(
        "SELECT id FROM goal_feasibility_reports WHERE report_id = ?",
        (rid,),
    ).fetchone()
    return int(row[0]) if row else 0


def load_feasibility_reports(
    connection: sqlite3.Connection,
    user_id: int | str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Load saved snapshots for the UI without exposing raw SQL to pages."""
    ensure_report_table(connection)
    safe_limit = max(1, min(int(limit), 100))
    if user_id is None:
        rows = connection.execute(
            "SELECT * FROM goal_feasibility_reports ORDER BY analyzed_on DESC, id DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM goal_feasibility_reports WHERE user_id = ? "
            "ORDER BY analyzed_on DESC, id DESC LIMIT ?",
            (str(user_id), safe_limit),
        ).fetchall()
    columns = [item[0] for item in connection.description]
    return [dict(zip(columns, row)) for row in rows]


def _json_safe(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value
