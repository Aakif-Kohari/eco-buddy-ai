"""Personalized sustainability action-plan engine.

This module deliberately keeps recommendation generation and plan persistence
separate. It consumes existing recommendation strings and assessment category
contributions instead of creating a second recommendation taxonomy.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")
DEFAULT_WEIGHTS = {
    "impact": 0.34,
    "relevance": 0.25,
    "feasibility": 0.18,
    "preference": 0.10,
    "cost": 0.06,
    "difficulty": 0.04,
    "time": 0.03,
}
VALID_STATUSES = ("planned", "started", "completed", "skipped", "removed")
VALID_HORIZONS = ("top5", "top10", "30d", "90d", "custom")


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return default if not math.isfinite(number) else number


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, _finite(value)))


def _slug(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Action:
    id: str
    name: str
    category: str
    difficulty: str = "moderate"
    estimated_cost: float | None = None
    time_to_complete: float | None = None
    potential_impact_low: float | None = None
    potential_impact_high: float | None = None
    dependencies: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    description: str = ""
    impact_basis: str | None = None
    completed: bool = False

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Action":
        name = str(data.get("name") or data.get("title") or "Untitled action").strip()
        category = str(data.get("category") or "General lifestyle").strip()
        raw_id = str(data.get("id") or "").strip()
        action_id = raw_id or hashlib.sha256(f"{_slug(category)}|{_slug(name)}".encode()).hexdigest()[:16]
        dependencies = tuple(str(x) for x in (data.get("dependencies") or ()) if str(x).strip())
        conflicts = tuple(str(x) for x in (data.get("conflicts") or ()) if str(x).strip())
        low = data.get("potential_impact_low", data.get("impact_low"))
        high = data.get("potential_impact_high", data.get("impact_high"))
        exact = data.get("potential_impact")
        if low is None and high is None and exact is not None:
            low = high = exact
        if low is not None:
            low = max(0.0, _finite(low))
        if high is not None:
            high = max(0.0, _finite(high))
        if low is not None and high is None:
            high = low
        if high is not None and low is None:
            low = high
        if low is not None and high is not None and high < low:
            low, high = high, low
        cost = data.get("estimated_cost", data.get("cost"))
        time = data.get("time_to_complete", data.get("time"))
        return cls(
            id=action_id,
            name=name,
            category=category,
            difficulty=str(data.get("difficulty") or "moderate").lower(),
            estimated_cost=None if cost is None else max(0.0, _finite(cost)),
            time_to_complete=None if time is None else max(0.0, _finite(time)),
            potential_impact_low=low,
            potential_impact_high=high,
            dependencies=dependencies,
            conflicts=conflicts,
            description=str(data.get("description") or "").strip(),
            impact_basis=data.get("impact_basis"),
            completed=bool(data.get("completed", False)),
        )


@dataclass(frozen=True)
class ActionConstraint:
    max_actions: int | None = None
    horizon_days: int | None = None
    max_cost: float | None = None
    max_difficulty: str | None = None
    exclude_completed: bool = True


@dataclass(frozen=True)
class ActionScore:
    action_id: str
    priority: float
    impact_score: float
    relevance_score: float
    feasibility_score: float
    preference_score: float
    cost_score: float
    difficulty_score: float
    time_score: float
    reason: str


@dataclass
class ActionPlan:
    id: str
    user_id: int | None
    horizon: str
    created_at: str
    items: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DIFFICULTY_SCORE = {"easy": 1.0, "moderate": 0.65, "advanced": 0.30}
DIFFICULTY_ORDER = {"easy": 0, "moderate": 1, "advanced": 2}


def _category_key(category: str) -> str:
    text = _slug(category)
    aliases = {
        "transportation": "transport",
        "transport": "transport",
        "energy": "electricity",
        "electricity": "electricity",
        "food": "diet",
        "diet": "diet",
        "water": "water",
        "waste": "waste",
        "shopping": "shopping",
        "general lifestyle": "general",
        "lifestyle": "general",
        "general": "general",
    }
    return aliases.get(text, text)


def _category_relevance(category: str, contributors: Mapping[str, Any]) -> float:
    if not contributors:
        return 0.5
    target = _category_key(category)
    pairs = [(_category_key(str(k)), max(0.0, _finite(v))) for k, v in contributors.items()]
    total = sum(v for _, v in pairs)
    if total <= 0:
        return 0.5
    matching = sum(v for key, v in pairs if key == target)
    return _clamp(matching / total)


def estimate_action_impact(action: Action | Mapping[str, Any], contributors: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return an honest impact range; missing evidence remains unavailable."""
    action = action if isinstance(action, Action) else Action.from_mapping(action)
    low, high = action.potential_impact_low, action.potential_impact_high
    if low is None or high is None:
        return {"available": False, "low": None, "high": None, "label": "Impact estimate unavailable", "basis": None}
    relevance = _category_relevance(action.category, contributors or {})
    # Relevance only gates prioritisation; it never changes the user's stated estimate.
    return {"available": True, "low": round(low, 2), "high": round(high, 2),
            "label": f"Estimated: {low:g}–{high:g} kg CO2e/year", "basis": action.impact_basis}


def calculate_action_priority(
    action: Action | Mapping[str, Any],
    contributors: Mapping[str, Any] | None = None,
    preferences: Mapping[str, Any] | None = None,
    weights: Mapping[str, float] | None = None,
) -> ActionScore:
    action = action if isinstance(action, Action) else Action.from_mapping(action)
    preferences = preferences or {}
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    impact = estimate_action_impact(action, contributors)
    impact_score = 0.5 if not impact["available"] else _clamp(((impact["low"] + impact["high"]) / 2) / 1000)
    relevance = _category_relevance(action.category, contributors or {})
    difficulty = DIFFICULTY_SCORE.get(action.difficulty, 0.5)
    max_cost = max(1.0, _finite(preferences.get("max_cost", 1000), 1000))
    if action.estimated_cost is None:
        cost_score = 0.6
    else:
        cost_score = _clamp(1 - action.estimated_cost / max_cost)
    max_days = max(1.0, _finite(preferences.get("max_days", 30), 30))
    time_score = 0.6 if action.time_to_complete is None else _clamp(1 - action.time_to_complete / max_days)
    pref_categories = {_category_key(str(x)) for x in preferences.get("preferred_categories", [])}
    preference_score = 1.0 if _category_key(action.category) in pref_categories else 0.5
    feasibility = (difficulty * 0.55) + (cost_score * 0.25) + (time_score * 0.20)
    priority = (
        weights.get("impact", 0) * impact_score
        + weights.get("relevance", 0) * relevance
        + weights.get("feasibility", 0) * feasibility
        + weights.get("preference", 0) * preference_score
        + weights.get("cost", 0) * cost_score
        + weights.get("difficulty", 0) * difficulty
        + weights.get("time", 0) * time_score
    )
    if action.completed:
        priority -= 0.75
    reason = f"High {action.category.lower()} relevance" if relevance >= 0.5 else "Balanced for feasibility and impact"
    if not impact["available"]:
        reason += "; impact estimate unavailable"
    return ActionScore(action.id, round(priority, 6), round(impact_score, 6), round(relevance, 6),
                       round(feasibility, 6), round(preference_score, 6), round(cost_score, 6),
                       round(difficulty, 6), round(time_score, 6), reason)


def detect_action_conflicts(actions: Iterable[Action | Mapping[str, Any]]) -> list[tuple[str, str]]:
    parsed = [a if isinstance(a, Action) else Action.from_mapping(a) for a in actions]
    ids = {a.id for a in parsed}
    pairs: set[tuple[str, str]] = set()
    for action in parsed:
        for other in action.conflicts:
            if other in ids and action.id != other:
                pairs.add(tuple(sorted((action.id, other))))
    return sorted(pairs)


def _dependency_order(actions: list[Action]) -> list[Action]:
    by_id = {a.id: a for a in actions}
    result: list[Action] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(a: Action) -> None:
        if a.id in visited:
            return
        if a.id in visiting:
            return  # cyclic dependencies are handled conservatively, not recursively forever
        visiting.add(a.id)
        for dep in a.dependencies:
            if dep in by_id:
                visit(by_id[dep])
        visiting.remove(a.id)
        visited.add(a.id)
        result.append(a)
    for action in actions:
        visit(action)
    return result


def rank_actions(actions: Iterable[Action | Mapping[str, Any]], contributors: Mapping[str, Any] | None = None,
                 preferences: Mapping[str, Any] | None = None, weights: Mapping[str, float] | None = None,
                 constraint: ActionConstraint | None = None) -> list[tuple[Action, ActionScore]]:
    constraint = constraint or ActionConstraint()
    parsed = [a if isinstance(a, Action) else Action.from_mapping(a) for a in actions]
    scored = [(a, calculate_action_priority(a, contributors, preferences, weights)) for a in parsed
              if not (constraint.exclude_completed and a.completed)]
    scored.sort(key=lambda pair: (-pair[1].priority, pair[0].id, _slug(pair[0].name)))
    selected: list[tuple[Action, ActionScore]] = []
    selected_ids: set[str] = set()
    cost = 0.0
    max_diff = DIFFICULTY_ORDER.get(str(constraint.max_difficulty).lower(), 99) if constraint.max_difficulty else 99
    conflict_map = {a.id: set(a.conflicts) for a, _ in scored}
    for action, score in scored:
        if DIFFICULTY_ORDER.get(action.difficulty, 1) > max_diff:
            continue
        if constraint.max_cost is not None and action.estimated_cost is not None and cost + action.estimated_cost > constraint.max_cost:
            continue
        if any(x in selected_ids for x in action.conflicts):
            continue
        if any(action.id in conflict_map.get(selected, set()) for selected in selected_ids):
            continue
        # prerequisites must be selected first when they are part of the candidate set
        if any(dep in {a.id for a, _ in scored} and dep not in selected_ids for dep in action.dependencies):
            continue
        selected.append((action, score)); selected_ids.add(action.id)
        if action.estimated_cost is not None:
            cost += action.estimated_cost
        if constraint.max_actions and len(selected) >= constraint.max_actions:
            break
    # If dependencies prevented selection, add their prerequisites ahead of dependents.
    ordered_actions = _dependency_order([a for a, _ in selected])
    score_map = {a.id: s for a, s in selected}
    return [(a, score_map[a.id]) for a in ordered_actions]


def build_action_plan(actions: Iterable[Action | Mapping[str, Any]], contributors: Mapping[str, Any] | None = None,
                      preferences: Mapping[str, Any] | None = None, horizon: str = "top5",
                      weights: Mapping[str, float] | None = None, user_id: int | None = None,
                      plan_id: str | None = None) -> ActionPlan:
    if horizon not in VALID_HORIZONS:
        raise ValueError(f"Unsupported horizon: {horizon}")
    limits = {"top5": 5, "top10": 10, "30d": 5, "90d": 10, "custom": None}
    horizon_days = {"30d": 30, "90d": 90}.get(horizon)
    ranked = rank_actions(actions, contributors, preferences, weights,
                          ActionConstraint(max_actions=limits[horizon], horizon_days=horizon_days))
    if plan_id is None:
        seed = f"{user_id}|{horizon}|" + "|".join(a.id for a, _ in ranked)
        plan_id = hashlib.sha256(seed.encode()).hexdigest()[:20]
    items = []
    for position, (action, score) in enumerate(ranked, 1):
        impact = estimate_action_impact(action, contributors)
        items.append({
            "action_id": action.id, "name": action.name, "category": action.category,
            "description": action.description, "difficulty": action.difficulty,
            "estimated_cost": action.estimated_cost, "time_to_complete": action.time_to_complete,
            "estimated_impact_low": impact["low"], "estimated_impact_high": impact["high"],
            "impact_available": impact["available"], "impact_label": impact["label"],
            "dependencies": list(action.dependencies), "conflicts": list(action.conflicts),
            "priority": score.priority, "priority_reason": score.reason, "status": "planned",
            "position": position,
        })
    return ActionPlan(plan_id, user_id, horizon, _now(), items)


def calculate_plan_impact(plan: ActionPlan | Mapping[str, Any]) -> dict[str, Any]:
    items = plan.items if isinstance(plan, ActionPlan) else list(plan.get("items", []))
    available = [(_finite(i.get("estimated_impact_low")), _finite(i.get("estimated_impact_high")))
                 for i in items if i.get("impact_available") and i.get("status") not in ("skipped", "removed")]
    if not available:
        return {"available": False, "low": None, "high": None, "label": "Impact estimate unavailable"}
    return {"available": True, "low": round(sum(x[0] for x in available), 2),
            "high": round(sum(x[1] for x in available), 2),
            "label": f"Estimated: {sum(x[0] for x in available):g}–{sum(x[1] for x in available):g} kg CO2e/year"}


def calculate_plan_cost(plan: ActionPlan | Mapping[str, Any]) -> float | None:
    items = plan.items if isinstance(plan, ActionPlan) else list(plan.get("items", []))
    costs = [i.get("estimated_cost") for i in items if i.get("estimated_cost") is not None and i.get("status") not in ("skipped", "removed")]
    return None if not costs else round(sum(_finite(x) for x in costs), 2)


def estimate_time_to_complete(plan: ActionPlan | Mapping[str, Any]) -> float | None:
    items = plan.items if isinstance(plan, ActionPlan) else list(plan.get("items", []))
    times = [i.get("time_to_complete") for i in items if i.get("time_to_complete") is not None and i.get("status") not in ("skipped", "removed")]
    return None if not times else round(sum(_finite(x) for x in times), 2)


def detect_action_conflict_ids(plan: ActionPlan | Mapping[str, Any]) -> list[tuple[str, str]]:
    items = plan.items if isinstance(plan, ActionPlan) else list(plan.get("items", []))
    ids = {str(i.get("action_id")) for i in items}
    pairs = set()
    for item in items:
        for conflict in item.get("conflicts", []):
            if conflict in ids:
                pairs.add(tuple(sorted((str(item.get("action_id")), str(conflict)))))
    return sorted(pairs)


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_action_plan_storage(db_path: str | None = None) -> None:
    conn = _connect(db_path)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS action_plan_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, plan_id TEXT NOT NULL,
            action_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'planned', priority REAL NOT NULL,
            estimated_impact_low REAL, estimated_impact_high REAL, created_at TEXT NOT NULL,
            completed_at TEXT, position INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, plan_id, action_id))""")
        conn.commit()
    finally:
        conn.close()


def save_action_plan(plan: ActionPlan, db_path: str | None = None) -> int:
    init_action_plan_storage(db_path)
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN")
        conn.execute("DELETE FROM action_plan_items WHERE user_id IS ? AND plan_id = ?", (plan.user_id, plan.id))
        for item in plan.items:
            conn.execute("""INSERT INTO action_plan_items
                (user_id,plan_id,action_id,status,priority,estimated_impact_low,estimated_impact_high,created_at,position)
                VALUES (?,?,?,?,?,?,?,?,?)""", (plan.user_id, plan.id, item["action_id"], item.get("status", "planned"),
                item.get("priority", 0), item.get("estimated_impact_low"), item.get("estimated_impact_high"), plan.created_at, item.get("position", 0)))
        conn.commit()
        return len(plan.items)
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def mark_action_complete(user_id: int, plan_id: str, action_id: str, status: str = "completed", db_path: str | None = None) -> bool:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid action status: {status}")
    init_action_plan_storage(db_path)
    conn = _connect(db_path)
    try:
        stamp = _now() if status == "completed" else None
        cur = conn.execute("UPDATE action_plan_items SET status=?, completed_at=? WHERE user_id=? AND plan_id=? AND action_id=?",
                           (status, stamp, user_id, plan_id, action_id))
        conn.commit(); return cur.rowcount == 1
    finally: conn.close()


def load_plan_progress(user_id: int, plan_id: str, db_path: str | None = None) -> dict[str, str]:
    init_action_plan_storage(db_path)
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT action_id,status FROM action_plan_items WHERE user_id=? AND plan_id=?", (user_id, plan_id)).fetchall()
        return {str(r["action_id"]): str(r["status"]) for r in rows}
    finally: conn.close()


def recalculate_plan(plan: ActionPlan, actions: Iterable[Action | Mapping[str, Any]], contributors: Mapping[str, Any] | None = None,
                     preferences: Mapping[str, Any] | None = None, weights: Mapping[str, float] | None = None) -> ActionPlan:
    progress = {i["action_id"]: i.get("status", "planned") for i in plan.items}
    rebuilt = build_action_plan(actions, contributors, preferences, plan.horizon, weights, plan.user_id, plan.id)
    for item in rebuilt.items:
        if item["action_id"] in progress:
            item["status"] = progress[item["action_id"]]
    return rebuilt


def serialize_plan(plan: ActionPlan) -> str:
    return json.dumps(plan.to_dict(), indent=2, sort_keys=True)


def deserialize_plan(payload: str | Mapping[str, Any]) -> ActionPlan:
    data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    return ActionPlan(str(data["id"]), data.get("user_id"), str(data["horizon"]), str(data["created_at"]), list(data.get("items", [])))
