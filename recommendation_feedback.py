"""Feedback, effectiveness, and deterministic personalization for EcoBuddy recommendations.

The module intentionally keeps ranking logic independent from Streamlit and the
existing recommendation generator.  Feedback is persisted in a small SQLite
table and can therefore be reused by any UI/API layer without changing the
assessment schema.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence

FEEDBACK_TYPES = (
    "helpful", "not_helpful", "already_doing", "too_difficult",
    "not_relevant", "completed", "dismissed",
)
DIFFICULTIES = ("easy", "moderate", "advanced")
DEFAULT_SUPPRESSION_DAYS = 7
DEFAULT_WEIGHTS = {
    "impact": 1.0,
    "relevance": 10.0,
    "helpful": 8.0,
    "completion": 12.0,
    "difficulty_fit": 5.0,
    "recency": 3.0,
    "repetition": 4.0,
    "rejection": 10.0,
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | str | None) -> str:
    if value is None:
        return utcnow().isoformat()
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _parse_time(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class RecommendationFeedback:
    user_id: int
    recommendation_id: str
    category: str
    feedback_type: str
    difficulty: str = "moderate"
    timestamp: str = field(default_factory=lambda: utcnow().isoformat())
    id: int | None = None

    def __post_init__(self) -> None:
        if int(self.user_id) < 0:
            raise ValueError("user_id must be non-negative")
        if not str(self.recommendation_id).strip():
            raise ValueError("recommendation_id is required")
        if self.feedback_type not in FEEDBACK_TYPES:
            raise ValueError(f"Unknown feedback type: {self.feedback_type}")
        if self.difficulty not in DIFFICULTIES:
            raise ValueError(f"Unknown difficulty: {self.difficulty}")
        _parse_time(self.timestamp)


@dataclass(frozen=True)
class RecommendationPreference:
    helpful: float = 0.0
    completion: float = 0.0
    rejection: float = 0.0
    difficulty: float = 0.0
    recency: float = 0.0
    repetition: float = 0.0


@dataclass(frozen=True)
class RecommendationHistory:
    recommendation_id: str
    category: str
    difficulty: str
    shown_count: int = 0
    helpful_count: int = 0
    completion_count: int = 0
    rejection_count: int = 0
    dismissed_count: int = 0
    last_feedback: str | None = None
    last_seen: str | None = None
    last_completed: str | None = None

    @property
    def total_feedback(self) -> int:
        return self.helpful_count + self.completion_count + self.rejection_count + self.dismissed_count


@dataclass(frozen=True)
class RecommendationScore:
    recommendation_id: str
    score: float
    impact: float
    relevance: float
    helpful: float
    completion: float
    difficulty_fit: float
    recency: float
    repetition: float
    rejection: float
    suppressed: bool = False
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class RecommendationFeedbackStore:
    """SQLite persistence for recommendation feedback.

    The store creates only its own table and indexes. It does not modify
    assessments, users, or any existing schema.
    """

    TABLE = "recommendation_feedback"

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv("ECO_BUDDY_DB", "eco_buddy.db")
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    recommendation_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    difficulty TEXT NOT NULL DEFAULT 'moderate',
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, recommendation_id, feedback_type, created_at)
                )"""
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_rec_feedback_user ON {self.TABLE}(user_id, created_at)"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_rec_feedback_rec ON {self.TABLE}(user_id, recommendation_id, created_at)"
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS recommendation_impressions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    recommendation_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    difficulty TEXT NOT NULL DEFAULT 'moderate',
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rec_impressions_user ON recommendation_impressions(user_id, recommendation_id, created_at)"
            )

    def record_impression(
        self, user_id: int, recommendation_id: str, category: str,
        difficulty: str = "moderate", timestamp: str | datetime | None = None,
    ) -> None:
        if not str(recommendation_id).strip():
            raise ValueError("recommendation_id is required")
        if difficulty not in DIFFICULTIES:
            raise ValueError(f"Unknown difficulty: {difficulty}")
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO recommendation_impressions
                (user_id, recommendation_id, category, difficulty, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (user_id, recommendation_id, category, difficulty, _iso(timestamp)),
            )

    def get_impression_counts(self, user_id: int) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT recommendation_id, COUNT(*) AS n
                FROM recommendation_impressions
                WHERE user_id = ?
                GROUP BY recommendation_id""",
                (user_id,),
            ).fetchall()
        return {str(row["recommendation_id"]): int(row["n"]) for row in rows}

    def get_last_impression(self, user_id: int, recommendation_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT created_at FROM recommendation_impressions
                WHERE user_id = ? AND recommendation_id = ?
                ORDER BY created_at DESC, id DESC LIMIT 1""",
                (user_id, recommendation_id),
            ).fetchone()
        return str(row["created_at"]) if row else None

    def record(self, feedback: RecommendationFeedback) -> RecommendationFeedback:
        with self._connect() as conn:
            cur = conn.execute(
                f"""INSERT INTO {self.TABLE}
                (user_id, recommendation_id, category, feedback_type, difficulty, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (feedback.user_id, feedback.recommendation_id, feedback.category,
                 feedback.feedback_type, feedback.difficulty, feedback.timestamp),
            )
            return RecommendationFeedback(**{**asdict(feedback), "id": cur.lastrowid})

    def record_safe(self, feedback: RecommendationFeedback) -> tuple[bool, str]:
        try:
            self.record(feedback)
            return True, "Feedback recorded."
        except sqlite3.IntegrityError:
            return False, "Duplicate feedback event was ignored."
        except sqlite3.Error as exc:
            return False, f"Could not save feedback: {exc}"

    def get_history(self, user_id: int, recommendation_id: str | None = None) -> list[RecommendationFeedback]:
        query = f"SELECT * FROM {self.TABLE} WHERE user_id = ?"
        args: list[Any] = [user_id]
        if recommendation_id:
            query += " AND recommendation_id = ?"
            args.append(recommendation_id)
        query += " ORDER BY created_at ASC, id ASC"
        with self._connect() as conn:
            rows = conn.execute(query, args).fetchall()
        return [
            RecommendationFeedback(
                user_id=row["user_id"], recommendation_id=row["recommendation_id"],
                category=row["category"], feedback_type=row["feedback_type"],
                difficulty=row["difficulty"], timestamp=row["created_at"], id=row["id"]
            ) for row in rows
        ]

    def clear_user(self, user_id: int) -> int:
        with self._connect() as conn:
            cur = conn.execute(f"DELETE FROM {self.TABLE} WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM recommendation_impressions WHERE user_id = ?", (user_id,))
            return int(cur.rowcount)

    def count(self, user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(f"SELECT COUNT(*) AS n FROM {self.TABLE} WHERE user_id = ?", (user_id,)).fetchone()
        return int(row["n"])


def validate_feedback_payload(payload: Mapping[str, Any]) -> RecommendationFeedback:
    required = ("user_id", "recommendation_id", "category", "feedback_type")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    return RecommendationFeedback(
        user_id=int(payload["user_id"]),
        recommendation_id=str(payload["recommendation_id"]),
        category=str(payload["category"]).strip() or "General",
        feedback_type=str(payload["feedback_type"]),
        difficulty=str(payload.get("difficulty", "moderate")),
        timestamp=_iso(payload.get("timestamp")),
    )


def record_feedback(
    user_id: int,
    recommendation_id: str,
    category: str,
    feedback_type: str,
    difficulty: str = "moderate",
    *,
    store: RecommendationFeedbackStore | None = None,
    timestamp: str | datetime | None = None,
) -> tuple[bool, str]:
    feedback = RecommendationFeedback(
        user_id=user_id, recommendation_id=recommendation_id, category=category,
        feedback_type=feedback_type, difficulty=difficulty, timestamp=_iso(timestamp),
    )
    return (store or RecommendationFeedbackStore()).record_safe(feedback)


def get_feedback_history(
    user_id: int,
    recommendation_id: str | None = None,
    *,
    store: RecommendationFeedbackStore | None = None,
) -> list[RecommendationFeedback]:
    return (store or RecommendationFeedbackStore()).get_history(user_id, recommendation_id)


def _history_for(
    feedback: Iterable[RecommendationFeedback],
    recommendation_id: str,
    category: str,
    difficulty: str,
    *,
    shown_count: int = 0,
    last_seen: str | None = None,
) -> RecommendationHistory:
    events = [event for event in feedback if event.recommendation_id == recommendation_id]
    shown = shown_count or sum(1 for event in events if event.feedback_type == "dismissed")
    helpful = sum(1 for event in events if event.feedback_type == "helpful")
    completed = sum(1 for event in events if event.feedback_type == "completed")
    rejected = sum(1 for event in events if event.feedback_type in {"not_helpful", "not_relevant", "already_doing", "too_difficult"})
    dismissed = sum(1 for event in events if event.feedback_type == "dismissed")
    last = events[-1] if events else None
    completed_events = [event for event in events if event.feedback_type == "completed"]
    return RecommendationHistory(
        recommendation_id=recommendation_id,
        category=category,
        difficulty=difficulty,
        shown_count=shown,
        helpful_count=helpful,
        completion_count=completed,
        rejection_count=rejected,
        dismissed_count=dismissed,
        last_feedback=last.feedback_type if last else None,
        last_seen=last_seen or (last.timestamp if last else None),
        last_completed=completed_events[-1].timestamp if completed_events else None,
    )


def build_history(
    feedback: Iterable[RecommendationFeedback],
    recommendations: Iterable[Mapping[str, Any]],
    *,
    impression_counts: Mapping[str, int] | None = None,
    last_impressions: Mapping[str, str | None] | None = None,
) -> dict[str, RecommendationHistory]:
    events = list(feedback)
    impression_counts = impression_counts or {}
    last_impressions = last_impressions or {}
    result: dict[str, RecommendationHistory] = {}
    for item in recommendations:
        rid = str(item["id"])
        result[rid] = _history_for(
            events, rid, str(item.get("category", "General")), str(item.get("difficulty", "moderate")),
            shown_count=int(impression_counts.get(rid, 0)),
            last_seen=last_impressions.get(rid),
        )
    return result


def detect_repeated_rejection(history: RecommendationHistory, threshold: int = 2) -> bool:
    return history.rejection_count >= threshold


def detect_completed_actions(history: RecommendationHistory) -> bool:
    return history.completion_count > 0


def _difficulty_fit(user_difficulties: Sequence[str], recommendation_difficulty: str) -> float:
    if not user_difficulties:
        return 0.5
    counts = {difficulty: user_difficulties.count(difficulty) for difficulty in DIFFICULTIES}
    total = sum(counts.values()) or 1
    preferred = max(counts, key=counts.get)
    if preferred == recommendation_difficulty:
        return 1.0
    if {preferred, recommendation_difficulty} <= {"easy", "moderate"}:
        return 0.75
    return 0.35


def calculate_preference_score(
    feedback: Iterable[RecommendationFeedback],
    *,
    category: str | None = None,
) -> RecommendationPreference:
    events = list(feedback)
    if category:
        events = [event for event in events if event.category == category]
    helpful = sum(1 for e in events if e.feedback_type == "helpful")
    completion = sum(1 for e in events if e.feedback_type == "completed")
    rejection = sum(1 for e in events if e.feedback_type in {"not_helpful", "not_relevant", "already_doing", "too_difficult"})
    now = utcnow()
    recency = sum(max(0.0, 1.0 - (_parse_time(e.timestamp) - now).days / 30.0) for e in events)
    advanced_completed = sum(1 for e in events if e.feedback_type == "completed" and e.difficulty == "advanced")
    advanced_too_difficult = sum(1 for e in events if e.feedback_type == "too_difficult" and e.difficulty == "advanced")
    difficulty = advanced_completed - advanced_too_difficult
    repetition = max(0.0, len(events) - len({e.recommendation_id for e in events}))
    return RecommendationPreference(
        helpful=float(helpful), completion=float(completion), rejection=float(rejection),
        difficulty=float(difficulty), recency=float(recency), repetition=float(repetition),
    )


def _impact_value(item: Mapping[str, Any]) -> float:
    try:
        return max(0.0, min(float(item.get("impact", item.get("potential_impact", 0.0))), 100.0))
    except (TypeError, ValueError):
        return 0.0


def calculate_recommendation_score(
    recommendation: Mapping[str, Any],
    history: RecommendationHistory,
    user_feedback: Iterable[RecommendationFeedback],
    *,
    weights: Mapping[str, float] | None = None,
    suppression_days: int = DEFAULT_SUPPRESSION_DAYS,
) -> RecommendationScore:
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    events = list(user_feedback)
    category = str(recommendation.get("category", "General"))
    difficulty = str(recommendation.get("difficulty", "moderate"))
    pref = calculate_preference_score(events, category=category)
    difficulty_events = [e.difficulty for e in events if e.feedback_type in {"completed", "too_difficult", "helpful"}]
    difficulty_fit = _difficulty_fit(difficulty_events, difficulty)
    now = utcnow()
    last_feedback = _parse_time(history.last_seen) if history.last_seen else None
    if last_feedback is None and history.last_seen:
        last_feedback = _parse_time(history.last_seen)
    recency = 0.0 if not last_feedback else max(0.0, 1.0 - (now - last_feedback).days / 30.0)
    suppressed = False
    if history.rejection_count >= 2 and last_feedback:
        suppressed = now - last_feedback < timedelta(days=suppression_days)
    impact = _impact_value(recommendation)
    category_events = [e for e in events if e.category == category]
    category_helpful = sum(1 for e in category_events if e.feedback_type == "helpful")
    category_completed = sum(1 for e in category_events if e.feedback_type == "completed")
    category_rejected = sum(1 for e in category_events if e.feedback_type in {"not_helpful", "not_relevant", "already_doing", "too_difficult"})
    relevance = min(1.0, (category_helpful + category_completed + 1) / (category_rejected + category_helpful + category_completed + 2))
    helpful = min(1.0, history.helpful_count / 3.0)
    completion = min(1.0, history.completion_count / 2.0)
    repetition = min(1.0, history.shown_count / 5.0)
    rejection = min(1.0, history.rejection_count / 3.0)
    raw = (
        weights["impact"] * impact
        + weights["relevance"] * relevance
        + weights["helpful"] * helpful
        + weights["completion"] * completion
        + weights["difficulty_fit"] * difficulty_fit
        + weights["recency"] * recency
        - weights["repetition"] * repetition
        - weights["rejection"] * rejection
    )
    if suppressed:
        raw = float("-inf")
    reason_parts = []
    if category_helpful or category_completed:
        reason_parts.append("similar actions received positive feedback")
    if history.rejection_count:
        reason_parts.append(f"{history.rejection_count} prior rejection(s)")
    if history.completion_count:
        reason_parts.append("previously completed")
    if difficulty_fit >= 0.9:
        reason_parts.append("matches preferred difficulty")
    if suppressed:
        reason_parts.append("temporarily suppressed after repeated rejection")
    reason = "; ".join(reason_parts) or "baseline impact and relevance"
    return RecommendationScore(
        recommendation_id=str(recommendation["id"]), score=raw, impact=impact,
        relevance=relevance, helpful=helpful, completion=completion,
        difficulty_fit=difficulty_fit, recency=recency, repetition=repetition,
        rejection=rejection, suppressed=suppressed, reason=reason,
    )


def rank_recommendations(
    recommendations: Iterable[Mapping[str, Any]],
    feedback: Iterable[RecommendationFeedback],
    *,
    weights: Mapping[str, float] | None = None,
    suppression_days: int = DEFAULT_SUPPRESSION_DAYS,
    limit: int | None = None,
    impression_counts: Mapping[str, int] | None = None,
    last_impressions: Mapping[str, str | None] | None = None,
) -> list[RecommendationScore]:
    items = list(recommendations)
    events = list(feedback)
    histories = build_history(events, items, impression_counts=impression_counts, last_impressions=last_impressions)
    scored = [
        calculate_recommendation_score(
            item, histories[str(item["id"])], events,
            weights=weights, suppression_days=suppression_days,
        ) for item in items
    ]
    scored.sort(key=lambda score: (score.suppressed, -score.score, score.recommendation_id))
    return scored[:limit] if limit else scored


def generate_personalized_order(
    recommendations: Iterable[Mapping[str, Any]],
    feedback: Iterable[RecommendationFeedback],
    **kwargs: Any,
) -> list[Mapping[str, Any]]:
    items = list(recommendations)
    ranked = rank_recommendations(items, feedback, **kwargs)
    by_id = {str(item["id"]): item for item in items}
    return [by_id[score.recommendation_id] for score in ranked]


def calculate_effectiveness(
    feedback: Iterable[RecommendationFeedback],
    *,
    impression_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    events = list(feedback)
    impression_counts = impression_counts or {}
    total = len(events)
    if not total:
        repeated = sorted(rid for rid, count in impression_counts.items() if int(count) >= 3)
        return {
            "total_events": 0, "acceptance_rate": 0.0, "completion_rate": 0.0,
            "rejection_rate": 0.0, "helpfulness_rate": 0.0,
            "completion_by_category": {}, "completion_by_difficulty": {},
            "most_effective_categories": [], "frequently_rejected": [],
            "repeated_without_completion": repeated,
        }
    completed = [e for e in events if e.feedback_type == "completed"]
    helpful = [e for e in events if e.feedback_type == "helpful"]
    rejected = [e for e in events if e.feedback_type in {"not_helpful", "not_relevant", "already_doing", "too_difficult"}]
    acceptance = len(helpful) + len(completed)
    category_completion: dict[str, int] = {}
    difficulty_completion: dict[str, int] = {}
    rejection_by_rec: dict[str, int] = {}
    event_by_rec: dict[str, list[RecommendationFeedback]] = {}
    for event in events:
        event_by_rec.setdefault(event.recommendation_id, []).append(event)
        if event.feedback_type == "completed":
            category_completion[event.category] = category_completion.get(event.category, 0) + 1
            difficulty_completion[event.difficulty] = difficulty_completion.get(event.difficulty, 0) + 1
        if event in rejected:
            rejection_by_rec[event.recommendation_id] = rejection_by_rec.get(event.recommendation_id, 0) + 1
    repeated = []
    candidate_ids = set(event_by_rec) | set(impression_counts)
    for rid in candidate_ids:
        rec_events = event_by_rec.get(rid, [])
        shown = int(impression_counts.get(rid, len(rec_events)))
        if shown >= 3 and not any(e.feedback_type == "completed" for e in rec_events):
            repeated.append(rid)
    effective_categories = sorted(category_completion, key=category_completion.get, reverse=True)
    frequent_rejected = sorted(rejection_by_rec, key=rejection_by_rec.get, reverse=True)
    return {
        "total_events": total,
        "acceptance_rate": round(acceptance / total, 4),
        "completion_rate": round(len(completed) / total, 4),
        "rejection_rate": round(len(rejected) / total, 4),
        "helpfulness_rate": round(len(helpful) / total, 4),
        "completion_by_category": dict(sorted(category_completion.items())),
        "completion_by_difficulty": dict(sorted(difficulty_completion.items())),
        "most_effective_categories": effective_categories,
        "frequently_rejected": frequent_rejected,
        "repeated_without_completion": sorted(repeated),
    }


def recommendation_analytics(
    feedback: Iterable[RecommendationFeedback],
    *,
    impression_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Return dashboard-friendly analytics with category/difficulty rollups."""
    events = list(feedback)
    base = calculate_effectiveness(events, impression_counts=impression_counts)
    by_category: dict[str, dict[str, int]] = {}
    for event in events:
        stats = by_category.setdefault(event.category, {"events": 0, "helpful": 0, "completed": 0, "rejected": 0})
        stats["events"] += 1
        if event.feedback_type == "helpful":
            stats["helpful"] += 1
        if event.feedback_type == "completed":
            stats["completed"] += 1
        if event.feedback_type in {"not_helpful", "not_relevant", "already_doing", "too_difficult"}:
            stats["rejected"] += 1
    for stats in by_category.values():
        stats["completion_rate"] = round(stats["completed"] / stats["events"], 4) if stats["events"] else 0.0
    return {**base, "by_category": by_category}


def reset_preferences(user_id: int, *, store: RecommendationFeedbackStore | None = None) -> int:
    return (store or RecommendationFeedbackStore()).clear_user(user_id)


def serialize_feedback(feedback: RecommendationFeedback) -> str:
    return json.dumps(asdict(feedback), sort_keys=True)


def deserialize_feedback(payload: str | bytes) -> RecommendationFeedback:
    data = json.loads(payload)
    return validate_feedback_payload(data)


def feedback_to_dicts(feedback: Iterable[RecommendationFeedback]) -> list[dict[str, Any]]:
    return [asdict(item) for item in feedback]


def normalize_recommendations(recommendations: Iterable[Any]) -> list[dict[str, Any]]:
    """Adapt the repository's existing string recommendation list to stable IDs."""
    normalized: list[dict[str, Any]] = []
    for index, value in enumerate(recommendations):
        if isinstance(value, Mapping):
            item = dict(value)
            item.setdefault("id", f"recommendation-{index}")
            item.setdefault("category", "General")
            item.setdefault("difficulty", "moderate")
            item.setdefault("impact", 0.0)
        else:
            text = str(value)
            category = "General"
            lowered = text.lower()
            if "transport" in lowered or "car" in lowered or "cycle" in lowered or "walk" in lowered:
                category = "Transportation"
            elif "electric" in lowered or "appliance" in lowered or "led" in lowered:
                category = "Electricity"
            elif "meat" in lowered or "plant" in lowered or "diet" in lowered:
                category = "Diet"
            elif "flight" in lowered or "air travel" in lowered:
                category = "Flights"
            stable_id = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]
            item = {"id": f"recommendation-{stable_id}", "text": text, "category": category, "difficulty": "moderate", "impact": 0.0}
        normalized.append(item)
    return normalized
