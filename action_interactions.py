"""Sustainability action dependency and impact interaction analysis.

The module is intentionally a planning-analysis layer. It does not generate
new recommendations and it never mutates assessment history. Existing action
records can be supplied as mappings, dataclasses, or JSON-compatible objects.

It models prerequisites, conflicts, sequential effects, overlapping benefits,
diminishing returns, execution order, and transparent impact ranges. Unknown
impact data remains unknown instead of being invented.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

DB_NAME = "eco_buddy.db"
SCHEMA_VERSION = "1.0"
VALID_RELATIONSHIPS = ("dependency", "conflict", "overlap", "sequence", "synergy", "diminishing")
VALID_STATUSES = ("available", "blocked", "selected", "completed", "skipped")


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _optional_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, _number(value)))


def _slug(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_id(category: str, name: str) -> str:
    seed = f"{_slug(category)}|{_slug(name)}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:16]


def _as_ids(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        value = value.split(",")
    return tuple(str(item).strip() for item in value if str(item).strip())


@dataclass(frozen=True)
class SustainabilityAction:
    """Normalized action consumed by the analyzer."""

    id: str
    name: str
    category: str
    impact_low: float | None = None
    impact_high: float | None = None
    dependencies: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    overlaps: tuple[str, ...] = ()
    synergies: tuple[str, ...] = ()
    sequence_after: tuple[str, ...] = ()
    difficulty: str = "moderate"
    cost: float | None = None
    duration_days: float | None = None
    completed: bool = False
    description: str = ""
    evidence: str | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "SustainabilityAction":
        category = str(raw.get("category") or raw.get("area") or "General lifestyle").strip()
        name = str(raw.get("name") or raw.get("title") or raw.get("action") or "Unnamed action").strip()
        action_id = str(raw.get("id") or raw.get("action_id") or "").strip() or _canonical_id(category, name)
        low = raw.get("impact_low", raw.get("estimated_impact_low", raw.get("potential_impact_low")))
        high = raw.get("impact_high", raw.get("estimated_impact_high", raw.get("potential_impact_high")))
        exact = raw.get("impact", raw.get("potential_impact"))
        if low is None and high is None and exact is not None:
            low = high = exact
        low, high = _optional_number(low), _optional_number(high)
        if low is not None:
            low = max(0.0, low)
        if high is not None:
            high = max(0.0, high)
        if low is None and high is not None:
            low = high
        if high is None and low is not None:
            high = low
        if low is not None and high is not None and high < low:
            low, high = high, low
        return cls(
            id=action_id,
            name=name,
            category=category,
            impact_low=low,
            impact_high=high,
            dependencies=_as_ids(raw.get("dependencies")),
            conflicts=_as_ids(raw.get("conflicts")),
            overlaps=_as_ids(raw.get("overlaps")),
            synergies=_as_ids(raw.get("synergies")),
            sequence_after=_as_ids(raw.get("sequence_after", raw.get("prerequisites"))),
            difficulty=str(raw.get("difficulty") or "moderate").strip().lower(),
            cost=None if raw.get("cost", raw.get("estimated_cost")) is None else max(0.0, _number(raw.get("cost", raw.get("estimated_cost")))),
            duration_days=None if raw.get("duration_days", raw.get("time_to_complete")) is None else max(0.0, _number(raw.get("duration_days", raw.get("time_to_complete")))),
            completed=bool(raw.get("completed", False)),
            description=str(raw.get("description") or "").strip(),
            evidence=None if raw.get("evidence") is None else str(raw.get("evidence")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Interaction:
    source_id: str
    target_id: str
    relationship: str
    strength: float = 1.0
    overlap_fraction: float = 0.0
    rationale: str = ""
    source: str = "explicit"

    def __post_init__(self) -> None:
        if self.relationship not in VALID_RELATIONSHIPS:
            raise ValueError(f"Unknown relationship: {self.relationship}")
        object.__setattr__(self, "strength", _clamp(self.strength))
        object.__setattr__(self, "overlap_fraction", _clamp(self.overlap_fraction))


@dataclass(frozen=True)
class ImpactRange:
    low: float | None
    high: float | None
    available: bool
    label: str
    methodology: str = ""

    @property
    def midpoint(self) -> float | None:
        if self.low is None or self.high is None:
            return None
        return (self.low + self.high) / 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DependencyFinding:
    action_id: str
    prerequisite_id: str
    satisfied: bool
    depth: int
    rationale: str


@dataclass(frozen=True)
class ConflictFinding:
    first_id: str
    second_id: str
    severity: float
    rationale: str


@dataclass(frozen=True)
class InteractionFinding:
    first_id: str
    second_id: str
    relationship: str
    adjustment_low: float | None
    adjustment_high: float | None
    rationale: str


@dataclass
class ActionInteractionReport:
    schema_version: str
    generated_at: str
    selected_action_ids: list[str]
    execution_order: list[str]
    blocked_action_ids: list[str]
    dependencies: list[DependencyFinding] = field(default_factory=list)
    conflicts: list[ConflictFinding] = field(default_factory=list)
    interactions: list[InteractionFinding] = field(default_factory=list)
    independent_impact: ImpactRange = field(default_factory=lambda: ImpactRange(None, None, False, "Impact estimate unavailable"))
    combined_impact: ImpactRange = field(default_factory=lambda: ImpactRange(None, None, False, "Impact estimate unavailable"))
    diminishing_returns: dict[str, float] = field(default_factory=dict)
    explanations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "selected_action_ids": self.selected_action_ids,
            "execution_order": self.execution_order,
            "blocked_action_ids": self.blocked_action_ids,
            "dependencies": [asdict(x) for x in self.dependencies],
            "conflicts": [asdict(x) for x in self.conflicts],
            "interactions": [asdict(x) for x in self.interactions],
            "independent_impact": self.independent_impact.to_dict(),
            "combined_impact": self.combined_impact.to_dict(),
            "diminishing_returns": self.diminishing_returns,
            "explanations": self.explanations,
            "warnings": self.warnings,
        }


DIFFICULTY = {"easy": 1.0, "moderate": 0.75, "medium": 0.75, "hard": 0.45, "advanced": 0.3}


def normalize_actions(actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> list[SustainabilityAction]:
    result: list[SustainabilityAction] = []
    seen: set[str] = set()
    for raw in actions:
        action = raw if isinstance(raw, SustainabilityAction) else SustainabilityAction.from_mapping(raw)
        if action.id in seen:
            raise ValueError(f"Duplicate action id: {action.id}")
        seen.add(action.id)
        result.append(action)
    return result


def action_map(actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> dict[str, SustainabilityAction]:
    parsed = normalize_actions(actions)
    return {action.id: action for action in parsed}


def infer_relationships(actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> list[Interaction]:
    """Create explicit relationship records without inventing impact values."""
    parsed = normalize_actions(actions)
    by_id = {a.id: a for a in parsed}
    found: dict[tuple[str, str, str], Interaction] = {}

    def add(a: SustainabilityAction, b_id: str, relationship: str, strength: float = 1.0, overlap: float = 0.0, rationale: str = "", source: str = "explicit") -> None:
        if b_id not in by_id or b_id == a.id:
            return
        key = (a.id, b_id, relationship)
        found[key] = Interaction(a.id, b_id, relationship, strength, overlap, rationale, source)

    for action in parsed:
        for dep in action.dependencies:
            if dep in by_id:
                add(action, dep, "dependency", 1.0, 0.0, f"{action.name} requires {by_id[dep].name} first.")
        for dep in action.sequence_after:
            if dep in by_id:
                add(action, dep, "sequence", 1.0, 0.0, f"{action.name} should follow {by_id[dep].name}.")
        for conflict in action.conflicts:
            if conflict in by_id:
                add(action, conflict, "conflict", 1.0, 0.0, f"{action.name} and {by_id[conflict].name} are alternatives or cannot coexist.")
        for overlap in action.overlaps:
            if overlap in by_id:
                add(action, overlap, "overlap", 0.5, 0.5, f"Benefits of {action.name} overlap with {by_id[overlap].name}.")
        for synergy in action.synergies:
            if synergy in by_id:
                add(action, synergy, "synergy", 0.5, 0.0, f"{action.name} can reinforce {by_id[synergy].name}.")
    return sorted(found.values(), key=lambda x: (x.relationship, x.source_id, x.target_id))


def build_relationship_graph(actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> dict[str, list[Interaction]]:
    parsed = normalize_actions(actions)
    graph = {a.id: [] for a in parsed}
    for relation in infer_relationships(parsed):
        graph[relation.source_id].append(relation)
    return graph


def _dependency_edges(actions: Mapping[str, SustainabilityAction]) -> dict[str, set[str]]:
    edges = {key: set() for key in actions}
    for action in actions.values():
        for dep in (*action.dependencies, *action.sequence_after):
            if dep in actions:
                edges[action.id].add(dep)
    return edges


def detect_dependency_cycles(actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> list[list[str]]:
    by_id = action_map(actions)
    edges = _dependency_edges(by_id)
    cycles: list[list[str]] = []
    visiting: list[str] = []
    active: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in active:
            start = visiting.index(node)
            cycles.append(visiting[start:] + [node])
            return
        if node in visited:
            return
        active.add(node)
        visiting.append(node)
        for dep in sorted(edges[node]):
            visit(dep)
        visiting.pop()
        active.remove(node)
        visited.add(node)

    for node in sorted(by_id):
        visit(node)
    return cycles


def resolve_dependency_chain(action_id: str, actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> list[str]:
    by_id = action_map(actions)
    if action_id not in by_id:
        raise KeyError(action_id)
    result: list[str] = []
    visiting: set[str] = set()

    def visit(current: str) -> None:
        if current in visiting:
            raise ValueError("Dependency cycle detected")
        if current in result:
            return
        visiting.add(current)
        action = by_id[current]
        for dep in (*action.dependencies, *action.sequence_after):
            if dep in by_id:
                visit(dep)
        visiting.remove(current)
        result.append(current)

    visit(action_id)
    return result


def calculate_execution_order(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> list[str]:
    by_id = action_map(actions)
    selected = [item for item in selected_ids if item in by_id]
    selected_set = set(selected)
    edges = {item: set(dep for dep in _dependency_edges(by_id)[item] if dep in selected_set) for item in selected}
    indegree = {item: 0 for item in selected}
    for item, deps in edges.items():
        for dep in deps:
            indegree[item] += 1
    ready = sorted([item for item, degree in indegree.items() if degree == 0])
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for target in sorted(edges):
            if current in edges[target]:
                edges[target].remove(current)
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)
                    ready.sort()
    if len(order) != len(selected):
        raise ValueError("Selected actions contain a dependency cycle")
    return order


def find_dependencies(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]], completed_ids: Iterable[str] = ()) -> list[DependencyFinding]:
    by_id = action_map(actions)
    completed = set(completed_ids)
    findings: list[DependencyFinding] = []
    for action_id in selected_ids:
        if action_id not in by_id:
            continue
        for prerequisite in (*by_id[action_id].dependencies, *by_id[action_id].sequence_after):
            if prerequisite not in by_id:
                findings.append(DependencyFinding(action_id, prerequisite, False, 1, "Prerequisite is not present in the supplied action set."))
                continue
            chain = resolve_dependency_chain(prerequisite, by_id.values())
            satisfied = prerequisite in completed or prerequisite not in selected_ids
            findings.append(DependencyFinding(action_id, prerequisite, satisfied, len(chain), f"{by_id[action_id].name} depends on {by_id[prerequisite].name}."))
    return findings


def find_conflicts(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> list[ConflictFinding]:
    by_id = action_map(actions)
    selected = set(selected_ids)
    results: dict[tuple[str, str], ConflictFinding] = {}
    for action_id in selected:
        if action_id not in by_id:
            continue
        for other in by_id[action_id].conflicts:
            if other not in selected or other not in by_id:
                continue
            key = tuple(sorted((action_id, other)))
            results[key] = ConflictFinding(key[0], key[1], 1.0, f"{by_id[key[0]].name} conflicts with {by_id[key[1]].name}.")
    return sorted(results.values(), key=lambda x: (x.first_id, x.second_id))


def calculate_independent_impact(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> ImpactRange:
    by_id = action_map(actions)
    if not selected_ids:
        return ImpactRange(None, None, False, "Impact estimate unavailable", "No actions were selected.")
    if any(item not in by_id for item in selected_ids):
        return ImpactRange(None, None, False, "Impact estimate unavailable", "At least one selected action is unknown.")
    chosen = [by_id[x] for x in selected_ids]
    if not chosen or any(a.impact_low is None or a.impact_high is None for a in chosen):
        return ImpactRange(None, None, False, "Impact estimate unavailable", "At least one selected action has no supported impact range.")
    return ImpactRange(round(sum(a.impact_low or 0 for a in chosen), 4), round(sum(a.impact_high or 0 for a in chosen), 4), True, "Independent sum", "Sum of supplied action ranges before interactions.")


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def calculate_interaction_adjustment(first: SustainabilityAction, second: SustainabilityAction, relation: Interaction) -> tuple[float | None, float | None]:
    if first.impact_low is None or first.impact_high is None or second.impact_low is None or second.impact_high is None:
        return None, None
    if relation.relationship == "overlap":
        fraction = _clamp(relation.overlap_fraction, 0.0, 0.95)
        return -round(min(first.impact_low, second.impact_low) * fraction, 4), -round(min(first.impact_high, second.impact_high) * fraction, 4)
    if relation.relationship == "synergy":
        bonus = _clamp(relation.strength, 0.0, 1.0) * 0.10
        return round((first.impact_low + second.impact_low) * bonus, 4), round((first.impact_high + second.impact_high) * bonus, 4)
    if relation.relationship == "diminishing":
        reduction = _clamp(relation.strength, 0.0, 1.0) * 0.20
        return -round(second.impact_low * reduction, 4), -round(second.impact_high * reduction, 4)
    return 0.0, 0.0


def analyze_interactions(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> list[InteractionFinding]:
    parsed = normalize_actions(actions)
    by_id = {a.id: a for a in parsed}
    selected = set(selected_ids)
    relations = infer_relationships(parsed)
    findings: list[InteractionFinding] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    for relation in relations:
        if relation.source_id not in selected or relation.target_id not in selected:
            continue
        key = (relation.source_id, relation.target_id, relation.relationship)
        reverse = (relation.target_id, relation.source_id, relation.relationship)
        if key in seen_pairs or reverse in seen_pairs:
            continue
        seen_pairs.add(key)
        first, second = by_id[relation.source_id], by_id[relation.target_id]
        low, high = calculate_interaction_adjustment(first, second, relation)
        findings.append(InteractionFinding(first.id, second.id, relation.relationship, low, high, relation.rationale))
    return findings


def calculate_diminishing_returns(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> dict[str, float]:
    by_id = action_map(actions)
    results: dict[str, float] = {}
    category_position: dict[str, int] = {}
    for action_id in selected_ids:
        if action_id not in by_id:
            continue
        category = _slug(by_id[action_id].category)
        position = category_position.get(category, 0)
        results[action_id] = round(1.0 / (1.0 + position * 0.15), 4)
        category_position[category] = position + 1
    return results


def calculate_combined_impact(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> ImpactRange:
    parsed = normalize_actions(actions)
    by_id = {a.id: a for a in parsed}
    base = calculate_independent_impact(selected_ids, parsed)
    if not base.available:
        return base
    low, high = base.low or 0.0, base.high or 0.0
    for finding in analyze_interactions(selected_ids, parsed):
        if finding.adjustment_low is None or finding.adjustment_high is None:
            return ImpactRange(None, None, False, "Impact estimate unavailable", "An interaction depends on incomplete impact evidence.")
        low += finding.adjustment_low
        high += finding.adjustment_high
    diminishing = calculate_diminishing_returns(selected_ids, parsed)
    # Apply only category-level diminishing factors to the incremental contribution
    # while keeping the first action in each category at full weight.
    category_seen: dict[str, int] = {}
    for action_id in selected_ids:
        if action_id not in by_id:
            continue
        category = _slug(by_id[action_id].category)
        index = category_seen.get(category, 0)
        category_seen[category] = index + 1
        if index == 0:
            continue
        action = by_id[action_id]
        if action.impact_low is not None and action.impact_high is not None:
            factor = diminishing[action_id]
            low -= action.impact_low
            high -= action.impact_high
            low += action.impact_low * factor
            high += action.impact_high * factor
    low, high = max(0.0, low), max(0.0, high)
    return ImpactRange(round(low, 4), round(max(low, high), 4), True, "Interaction-adjusted estimate", "Includes explicit overlap/synergy and conservative diminishing-return adjustments.")


def blocked_actions(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]], completed_ids: Iterable[str] = ()) -> list[str]:
    by_id = action_map(actions)
    selected = set(selected_ids)
    completed = set(completed_ids)
    blocked: list[str] = []
    for action_id in selected:
        if action_id not in by_id:
            blocked.append(action_id)
            continue
        prerequisites = (*by_id[action_id].dependencies, *by_id[action_id].sequence_after)
        if any(dep not in completed and dep not in selected for dep in prerequisites):
            blocked.append(action_id)
    return sorted(set(blocked))


def summarize_action(action: SustainabilityAction) -> dict[str, Any]:
    impact = ImpactRange(action.impact_low, action.impact_high, action.impact_low is not None and action.impact_high is not None,
                         "Estimated range" if action.impact_low is not None and action.impact_high is not None else "Impact estimate unavailable",
                         action.evidence or "")
    return {
        "id": action.id,
        "name": action.name,
        "category": action.category,
        "impact": impact.to_dict(),
        "dependencies": list(action.dependencies),
        "conflicts": list(action.conflicts),
        "overlaps": list(action.overlaps),
        "synergies": list(action.synergies),
        "sequence_after": list(action.sequence_after),
        "difficulty": action.difficulty,
        "cost": action.cost,
        "duration_days": action.duration_days,
        "completed": action.completed,
    }


def build_explanations(report: ActionInteractionReport, actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> list[str]:
    by_id = action_map(actions)
    explanations: list[str] = []
    if report.execution_order:
        names = [by_id[item].name for item in report.execution_order if item in by_id]
        explanations.append("Recommended execution order: " + " → ".join(names) + ".")
    for finding in report.dependencies:
        if not finding.satisfied:
            name = by_id.get(finding.action_id).name if finding.action_id in by_id else finding.action_id
            explanations.append(f"{name} is blocked until its prerequisite is available or completed.")
    for conflict in report.conflicts:
        if conflict.first_id in by_id and conflict.second_id in by_id:
            explanations.append(f"{by_id[conflict.first_id].name} and {by_id[conflict.second_id].name} should not be counted as simultaneous actions.")
    for interaction in report.interactions:
        if interaction.relationship == "overlap":
            explanations.append("Overlapping benefits were discounted so the same reduction is not counted twice.")
        elif interaction.relationship == "synergy":
            explanations.append("A supported synergy was included as an interaction adjustment.")
    if report.independent_impact.available and report.combined_impact.available:
        delta = (report.combined_impact.high or 0) - (report.independent_impact.high or 0)
        if delta < 0:
            explanations.append(f"Combined high-end impact is reduced by {abs(delta):.1f} kg CO2e/year versus an independent sum because of interactions.")
    if not report.combined_impact.available:
        explanations.append("A combined impact estimate is unavailable because at least one selected action lacks sufficient impact evidence.")
    return list(dict.fromkeys(explanations))


def analyze_action_set(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]], completed_ids: Iterable[str] = ()) -> ActionInteractionReport:
    parsed = normalize_actions(actions)
    by_id = {a.id: a for a in parsed}
    selected = [item for item in selected_ids if item in by_id]
    warnings: list[str] = []
    unknown = sorted(set(selected_ids) - set(by_id))
    if unknown:
        warnings.append("Unknown action IDs were ignored: " + ", ".join(unknown))
    conflicts = find_conflicts(selected, parsed)
    if conflicts:
        warnings.append("Conflicting actions are selected; review alternatives before executing the plan.")
    cycles = detect_dependency_cycles(parsed)
    if cycles:
        warnings.append("Dependency cycle detected: " + " | ".join(" → ".join(c) for c in cycles))
    try:
        order = calculate_execution_order(selected, parsed)
    except ValueError:
        order = selected[:]
        warnings.append("Execution order could not be resolved because of a dependency cycle.")
    dependencies = find_dependencies(selected, parsed, completed_ids)
    blocked = blocked_actions(selected, parsed, completed_ids)
    independent = calculate_independent_impact(selected, parsed)
    combined = calculate_combined_impact(selected, parsed)
    report = ActionInteractionReport(
        schema_version=SCHEMA_VERSION,
        generated_at=_now(),
        selected_action_ids=selected,
        execution_order=order,
        blocked_action_ids=blocked,
        dependencies=dependencies,
        conflicts=conflicts,
        interactions=analyze_interactions(selected, parsed),
        independent_impact=independent,
        combined_impact=combined,
        diminishing_returns=calculate_diminishing_returns(selected, parsed),
        warnings=warnings,
    )
    report.explanations = build_explanations(report, parsed)
    return report


def serialize_report(report: ActionInteractionReport, *, pretty: bool = True) -> str:
    return json.dumps(report.to_dict(), indent=2 if pretty else None, sort_keys=True, default=str)


def validate_report_document(document: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if document.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version: {document.get('schema_version')!r}")
    for field_name in ("generated_at", "selected_action_ids", "execution_order", "blocked_action_ids"):
        if field_name not in document:
            errors.append(f"Missing required field: {field_name}")
    for field_name in ("selected_action_ids", "execution_order", "blocked_action_ids", "warnings", "explanations"):
        if field_name in document and not isinstance(document[field_name], list):
            errors.append(f"Field {field_name} must be a list")
    for field_name in ("dependencies", "conflicts", "interactions"):
        if field_name in document and not isinstance(document[field_name], list):
            errors.append(f"Field {field_name} must be a list")
    return errors


def deserialize_report(payload: str | Mapping[str, Any]) -> ActionInteractionReport:
    document = json.loads(payload) if isinstance(payload, str) else dict(payload)
    errors = validate_report_document(document)
    if errors:
        raise ValueError("Invalid interaction report: " + "; ".join(errors))
    dependencies = [DependencyFinding(**item) for item in document.get("dependencies", [])]
    conflicts = [ConflictFinding(**item) for item in document.get("conflicts", [])]
    interactions = [InteractionFinding(**item) for item in document.get("interactions", [])]
    independent = ImpactRange(**document.get("independent_impact", {}))
    combined = ImpactRange(**document.get("combined_impact", {}))
    return ActionInteractionReport(
        schema_version=document["schema_version"],
        generated_at=document["generated_at"],
        selected_action_ids=list(document["selected_action_ids"]),
        execution_order=list(document["execution_order"]),
        blocked_action_ids=list(document["blocked_action_ids"]),
        dependencies=dependencies,
        conflicts=conflicts,
        interactions=interactions,
        independent_impact=independent,
        combined_impact=combined,
        diminishing_returns={str(k): _number(v) for k, v in document.get("diminishing_returns", {}).items()},
        explanations=list(document.get("explanations", [])),
        warnings=list(document.get("warnings", [])),
    )


def report_hash(report: ActionInteractionReport) -> str:
    payload = serialize_report(report, pretty=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compare_reports(previous: ActionInteractionReport | Mapping[str, Any], current: ActionInteractionReport | Mapping[str, Any]) -> dict[str, Any]:
    old = previous if isinstance(previous, ActionInteractionReport) else deserialize_report(previous)
    new = current if isinstance(current, ActionInteractionReport) else deserialize_report(current)
    old_set, new_set = set(old.selected_action_ids), set(new.selected_action_ids)
    old_high = old.combined_impact.high
    new_high = new.combined_impact.high
    return {
        "added_actions": sorted(new_set - old_set),
        "removed_actions": sorted(old_set - new_set),
        "unchanged_actions": sorted(old_set & new_set),
        "blocked_change": len(new.blocked_action_ids) - len(old.blocked_action_ids),
        "conflict_change": len(new.conflicts) - len(old.conflicts),
        "impact_high_change": None if old_high is None or new_high is None else round(new_high - old_high, 4),
        "execution_order_changed": old.execution_order != new.execution_order,
    }


def create_persistence_schema(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS action_interaction_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            report_hash TEXT NOT NULL UNIQUE,
            schema_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            report_json TEXT NOT NULL
        )
    """)
    connection.execute("CREATE INDEX IF NOT EXISTS idx_action_interaction_user ON action_interaction_reports(user_id, created_at)")


def save_report(report: ActionInteractionReport, user_id: int | None = None, database_path: str = DB_NAME) -> int:
    payload = serialize_report(report, pretty=False)
    digest = report_hash(report)
    Path(database_path).parent.mkdir(parents=True, exist_ok=True) if database_path != ":memory:" else None
    connection = sqlite3.connect(database_path)
    try:
        create_persistence_schema(connection)
        cursor = connection.execute(
            "INSERT OR IGNORE INTO action_interaction_reports(user_id, report_hash, schema_version, created_at, report_json) VALUES (?, ?, ?, ?, ?)",
            (user_id, digest, report.schema_version, report.generated_at, payload),
        )
        connection.commit()
        if cursor.lastrowid:
            return int(cursor.lastrowid)
        row = connection.execute("SELECT id FROM action_interaction_reports WHERE report_hash=?", (digest,)).fetchone()
        return int(row[0])
    finally:
        connection.close()


def load_reports(user_id: int | None = None, database_path: str = DB_NAME, limit: int = 20) -> list[ActionInteractionReport]:
    if limit < 1:
        return []
    connection = sqlite3.connect(database_path)
    try:
        create_persistence_schema(connection)
        if user_id is None:
            rows = connection.execute("SELECT report_json FROM action_interaction_reports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = connection.execute("SELECT report_json FROM action_interaction_reports WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
        return [deserialize_report(row[0]) for row in rows]
    finally:
        connection.close()


def delete_report(report_id: int, database_path: str = DB_NAME) -> bool:
    connection = sqlite3.connect(database_path)
    try:
        create_persistence_schema(connection)
        connection.commit()
        cursor = connection.execute("DELETE FROM action_interaction_reports WHERE id=?", (int(report_id),))
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def action_statuses(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]], completed_ids: Iterable[str] = ()) -> dict[str, str]:
    by_id = action_map(actions)
    completed = set(completed_ids)
    blocked = set(blocked_actions(selected_ids, by_id.values(), completed))
    statuses: dict[str, str] = {}
    for action_id in selected_ids:
        if action_id not in by_id:
            statuses[action_id] = "blocked"
        elif action_id in completed:
            statuses[action_id] = "completed"
        elif action_id in blocked:
            statuses[action_id] = "blocked"
        else:
            statuses[action_id] = "selected"
    return statuses


def dependency_depth(action_id: str, actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> int:
    chain = resolve_dependency_chain(action_id, actions)
    return max(0, len(chain) - 1)


def interaction_matrix(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> list[dict[str, Any]]:
    parsed = normalize_actions(actions)
    findings = analyze_interactions(selected_ids, parsed)
    matrix: list[dict[str, Any]] = []
    for finding in findings:
        matrix.append({
            "first_id": finding.first_id,
            "second_id": finding.second_id,
            "relationship": finding.relationship,
            "adjustment_low": finding.adjustment_low,
            "adjustment_high": finding.adjustment_high,
            "rationale": finding.rationale,
        })
    return matrix


def rank_execution_candidates(actions: Iterable[SustainabilityAction | Mapping[str, Any]], selected_ids: Sequence[str]) -> list[str]:
    by_id = action_map(actions)
    selected = [by_id[item] for item in selected_ids if item in by_id]
    scored: list[tuple[float, str]] = []
    for action in selected:
        impact = action.impact_high if action.impact_high is not None else 0.0
        feasibility = DIFFICULTY.get(action.difficulty, 0.5)
        depth = dependency_depth(action.id, selected)
        score = impact * 0.70 + feasibility * 100 * 0.30 - depth * 10
        scored.append((-score, action.id))
    return [item for _, item in sorted(scored)]


def select_non_conflicting(actions: Iterable[SustainabilityAction | Mapping[str, Any]], preferred_ids: Sequence[str]) -> list[str]:
    by_id = action_map(actions)
    selected: list[str] = []
    for action_id in preferred_ids:
        if action_id not in by_id:
            continue
        if any(action_id in by_id[x].conflicts or x in by_id[action_id].conflicts for x in selected):
            continue
        selected.append(action_id)
    return selected


def estimate_sequential_path(selected_ids: Sequence[str], actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> list[dict[str, Any]]:
    parsed = normalize_actions(actions)
    by_id = {a.id: a for a in parsed}
    order = calculate_execution_order(selected_ids, parsed)
    result: list[dict[str, Any]] = []
    running_low = 0.0
    running_high = 0.0
    for position, action_id in enumerate(order, 1):
        action = by_id[action_id]
        factor = calculate_diminishing_returns([item for item in order[:position]], parsed)[action_id]
        low = None if action.impact_low is None else round(action.impact_low * factor, 4)
        high = None if action.impact_high is None else round(action.impact_high * factor, 4)
        if low is not None:
            running_low += low
        if high is not None:
            running_high += high
        result.append({
            "position": position,
            "action_id": action_id,
            "name": action.name,
            "incremental_low": low,
            "incremental_high": high,
            "running_low": round(running_low, 4) if low is not None else None,
            "running_high": round(running_high, 4) if high is not None else None,
            "diminishing_factor": factor,
        })
    return result


def explain_action(action_id: str, actions: Iterable[SustainabilityAction | Mapping[str, Any]]) -> dict[str, Any]:
    by_id = action_map(actions)
    if action_id not in by_id:
        raise KeyError(action_id)
    action = by_id[action_id]
    dependencies = list((*action.dependencies, *action.sequence_after))
    related = [r for r in infer_relationships(by_id.values()) if r.source_id == action_id or r.target_id == action_id]
    return {
        "action": summarize_action(action),
        "dependency_depth": dependency_depth(action_id, by_id.values()),
        "prerequisites": dependencies,
        "conflicts": list(action.conflicts),
        "overlaps": list(action.overlaps),
        "synergies": list(action.synergies),
        "relationships": [asdict(item) for item in related],
        "impact_warning": "Impact estimate unavailable" if action.impact_low is None or action.impact_high is None else None,
    }


__all__ = [
    "ActionInteractionReport", "ConflictFinding", "DependencyFinding", "ImpactRange", "Interaction",
    "InteractionFinding", "SustainabilityAction", "SCHEMA_VERSION", "action_map", "action_statuses",
    "analyze_action_set", "analyze_interactions", "build_relationship_graph", "calculate_combined_impact",
    "calculate_diminishing_returns", "calculate_execution_order", "calculate_independent_impact",
    "calculate_interaction_adjustment", "compare_reports", "create_persistence_schema", "delete_report",
    "dependency_depth", "detect_dependency_cycles", "deserialize_report", "estimate_sequential_path",
    "explain_action", "find_conflicts", "find_dependencies", "infer_relationships", "interaction_matrix",
    "load_reports", "normalize_actions", "rank_execution_candidates", "report_hash", "resolve_dependency_chain",
    "save_report", "select_non_conflicting", "serialize_report", "summarize_action", "validate_report_document",
]
