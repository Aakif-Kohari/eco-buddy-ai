"""Recommendation lifecycle and feedback learning analytics for EcoBuddy AI.

This module is intentionally additive: it observes recommendation delivery,
user outcomes, and feedback without changing the recommendation engine's
selection algorithm. It produces transparent, deterministic learning signals
that can be used by the UI or future ranking systems.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import math
import os
import sqlite3
import statistics
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

logger = logging.getLogger(__name__)
DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")
ENGINE_VERSION = "1.0"
SCHEMA_VERSION = "1.0"


class LifecycleError(ValueError):
    """Raised for invalid lifecycle data."""


class RecommendationStatus(str, Enum):
    SHOWN = "shown"
    SAVED = "saved"
    STARTED = "started"
    COMPLETED = "completed"
    DISMISSED = "dismissed"
    SNOOZED = "snoozed"
    SKIPPED = "skipped"


class FeedbackType(str, Enum):
    RATING = "rating"
    USEFUL = "useful"
    COMMENT = "comment"
    REASON = "reason"


class FeedbackReason(str, Enum):
    RELEVANT = "relevant"
    NOT_RELEVANT = "not_relevant"
    TOO_EXPENSIVE = "too_expensive"
    TOO_DIFFICULT = "too_difficult"
    ALREADY_DONE = "already_done"
    NOT_FEASIBLE = "not_feasible"
    UNCLEAR = "unclear"
    DUPLICATE = "duplicate"
    GOOD_TIMING = "good_timing"
    OTHER = "other"


@dataclass(frozen=True)
class RecommendationEvent:
    """An immutable event in a recommendation's lifecycle."""

    recommendation_id: str
    user_id: int
    status: RecommendationStatus
    occurred_at: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str | None = None
    source: str = "recommendation_engine"
    context: dict[str, Any] = field(default_factory=dict)
    assessment_id: int | None = None

    def __post_init__(self) -> None:
        if not str(self.recommendation_id).strip():
            raise LifecycleError("recommendation_id is required")
        if int(self.user_id) < 1:
            raise LifecycleError("user_id must be positive")
        _validate_iso_datetime(self.occurred_at)
        if not isinstance(self.context, dict):
            raise LifecycleError("context must be an object")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


@dataclass(frozen=True)
class RecommendationFeedback:
    """Explicit user feedback attached to a recommendation."""

    recommendation_id: str
    user_id: int
    submitted_at: str
    rating: float | None = None
    useful: bool | None = None
    reason: FeedbackReason | None = None
    comment: str | None = None
    feedback_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if not str(self.recommendation_id).strip():
            raise LifecycleError("recommendation_id is required")
        if int(self.user_id) < 1:
            raise LifecycleError("user_id must be positive")
        _validate_iso_datetime(self.submitted_at)
        if self.rating is not None and not 1 <= float(self.rating) <= 5:
            raise LifecycleError("rating must be between 1 and 5")
        if self.comment is not None and len(self.comment) > 1000:
            raise LifecycleError("comment is too long")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reason"] = self.reason.value if self.reason else None
        return value


@dataclass(frozen=True)
class RecommendationOutcome:
    """Observed outcome of an accepted recommendation."""

    recommendation_id: str
    user_id: int
    measured_at: str
    outcome: str
    value: float | None = None
    unit: str | None = None
    baseline_value: float | None = None
    target_value: float | None = None
    evidence_quality: float = 0.5
    notes: str | None = None
    outcome_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if not str(self.recommendation_id).strip():
            raise LifecycleError("recommendation_id is required")
        if int(self.user_id) < 1:
            raise LifecycleError("user_id must be positive")
        if not str(self.outcome).strip():
            raise LifecycleError("outcome is required")
        _validate_iso_datetime(self.measured_at)
        if not 0 <= float(self.evidence_quality) <= 1:
            raise LifecycleError("evidence_quality must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecommendationProfile:
    """Current lifecycle summary for one recommendation and one user."""

    recommendation_id: str
    impressions: int
    saves: int
    starts: int
    completions: int
    dismissals: int
    snoozes: int
    skips: int
    ratings: int
    average_rating: float | None
    useful_rate: float | None
    completion_rate: float | None
    start_rate: float | None
    dismissal_rate: float | None
    last_status: str | None
    last_event_at: str | None
    feedback_reasons: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecommendationLearningSignal:
    """Transparent aggregate signal suitable for future ranking systems."""

    recommendation_id: str
    sample_size: int
    engagement_score: float
    satisfaction_score: float | None
    completion_score: float
    feedback_confidence: float
    learning_score: float
    confidence_label: str
    positive_signals: tuple[str, ...] = ()
    negative_signals: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["positive_signals"] = list(self.positive_signals)
        value["negative_signals"] = list(self.negative_signals)
        return value


@dataclass(frozen=True)
class LifecycleSummary:
    """Portfolio-level recommendation lifecycle metrics."""

    user_id: int
    recommendation_count: int
    shown_count: int
    started_count: int
    completed_count: int
    dismissed_count: int
    average_rating: float | None
    useful_rate: float | None
    completion_rate: float | None
    engagement_rate: float | None
    top_recommendations: tuple[RecommendationLearningSignal, ...]
    improvement_areas: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["top_recommendations"] = [x.to_dict() for x in self.top_recommendations]
        value["improvement_areas"] = list(self.improvement_areas)
        return value


def _validate_iso_datetime(value: str) -> None:
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise LifecycleError(f"Invalid datetime: {value}") from exc


def utc_now() -> str:
    """Return an explicit UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _normalize_status(value: RecommendationStatus | str) -> RecommendationStatus:
    if isinstance(value, RecommendationStatus):
        return value
    try:
        return RecommendationStatus(str(value).lower())
    except ValueError as exc:
        raise LifecycleError(f"Unsupported recommendation status: {value}") from exc


def _normalize_reason(value: FeedbackReason | str | None) -> FeedbackReason | None:
    if value is None or value == "":
        return None
    if isinstance(value, FeedbackReason):
        return value
    try:
        return FeedbackReason(str(value).lower())
    except ValueError as exc:
        raise LifecycleError(f"Unsupported feedback reason: {value}") from exc


def validate_event_payload(payload: Mapping[str, Any]) -> list[str]:
    """Return validation errors without mutating or persisting anything."""
    errors: list[str] = []
    if not str(payload.get("recommendation_id", "")).strip():
        errors.append("recommendation_id is required")
    try:
        if int(payload.get("user_id", 0)) < 1:
            errors.append("user_id must be positive")
    except (TypeError, ValueError):
        errors.append("user_id must be an integer")
    if "status" not in payload:
        errors.append("status is required")
    else:
        try:
            _normalize_status(payload["status"])
        except LifecycleError as exc:
            errors.append(str(exc))
    if payload.get("occurred_at"):
        try:
            _validate_iso_datetime(str(payload["occurred_at"]))
        except LifecycleError as exc:
            errors.append(str(exc))
    return errors


def validate_feedback_payload(payload: Mapping[str, Any]) -> list[str]:
    """Validate explicit recommendation feedback."""
    errors: list[str] = []
    if not str(payload.get("recommendation_id", "")).strip():
        errors.append("recommendation_id is required")
    try:
        if int(payload.get("user_id", 0)) < 1:
            errors.append("user_id must be positive")
    except (TypeError, ValueError):
        errors.append("user_id must be an integer")
    rating = payload.get("rating")
    if rating is not None:
        numeric = _safe_float(rating)
        if numeric is None or not 1 <= numeric <= 5:
            errors.append("rating must be between 1 and 5")
    comment = payload.get("comment")
    if comment is not None and len(str(comment)) > 1000:
        errors.append("comment is too long")
    if payload.get("reason") is not None:
        try:
            _normalize_reason(payload.get("reason"))
        except LifecycleError as exc:
            errors.append(str(exc))
    return errors


def calculate_engagement_score(profile: RecommendationProfile) -> float:
    """Score engagement from lifecycle transitions, bounded to 0..1."""
    if profile.impressions <= 0:
        return 0.0
    denominator = profile.impressions
    score = (
        profile.saves * 0.15
        + profile.starts * 0.35
        + profile.completions * 0.50
    ) / denominator
    return round(min(max(score, 0.0), 1.0), 4)


def calculate_completion_score(profile: RecommendationProfile) -> float:
    """Score completion relative to starts, with no starts represented as zero."""
    if profile.starts <= 0:
        return 0.0
    return round(min(max(_ratio(profile.completions, profile.starts) or 0.0, 0.0), 1.0), 4)


def calculate_feedback_confidence(sample_size: int, ratings: int, useful_votes: int) -> float:
    """Estimate confidence using a conservative saturating sample curve."""
    if sample_size <= 0:
        return 0.0
    volume = 1 - math.exp(-sample_size / 10)
    coverage = min(1.0, (ratings + useful_votes) / max(sample_size, 1))
    return round(0.7 * volume + 0.3 * coverage, 4)


def calculate_learning_signal(profile: RecommendationProfile) -> RecommendationLearningSignal:
    """Convert lifecycle evidence into an explainable learning signal."""
    engagement = calculate_engagement_score(profile)
    completion = calculate_completion_score(profile)
    satisfaction = profile.average_rating / 5 if profile.average_rating is not None else None
    feedback_samples = profile.ratings + sum(profile.feedback_reasons.values())
    confidence = calculate_feedback_confidence(
        profile.impressions,
        profile.ratings,
        sum(profile.feedback_reasons.values()),
    )
    parts = [engagement * 0.35, completion * 0.35]
    if satisfaction is not None:
        parts.append(satisfaction * 0.30)
    else:
        parts.append(0.0)
    learning = round(sum(parts), 4)
    positives: list[str] = []
    negatives: list[str] = []
    if profile.completion_rate is not None and profile.completion_rate >= 0.5:
        positives.append("high completion rate")
    if profile.useful_rate is not None and profile.useful_rate >= 0.7:
        positives.append("users frequently mark it useful")
    if profile.average_rating is not None and profile.average_rating >= 4:
        positives.append("strong average rating")
    if profile.dismissal_rate is not None and profile.dismissal_rate >= 0.35:
        negatives.append("high dismissal rate")
    if profile.feedback_reasons.get(FeedbackReason.TOO_EXPENSIVE.value, 0):
        negatives.append("cost is a recurring concern")
    if profile.feedback_reasons.get(FeedbackReason.TOO_DIFFICULT.value, 0):
        negatives.append("difficulty is a recurring concern")
    if not feedback_samples:
        negatives.append("insufficient direct feedback")
    label = "high" if confidence >= 0.7 else "medium" if confidence >= 0.4 else "low"
    return RecommendationLearningSignal(
        recommendation_id=profile.recommendation_id,
        sample_size=profile.impressions,
        engagement_score=engagement,
        satisfaction_score=round(satisfaction, 4) if satisfaction is not None else None,
        completion_score=completion,
        feedback_confidence=confidence,
        learning_score=learning,
        confidence_label=label,
        positive_signals=tuple(positives),
        negative_signals=tuple(negatives),
    )


class RecommendationLifecycleStore:
    """SQLite-backed lifecycle event and feedback store."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or DB_NAME
        self._initialized = False

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        """Create additive tables and indexes idempotently."""
        if self._initialized:
            return
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS recommendation_lifecycle_events (
                    event_id TEXT PRIMARY KEY,
                    recommendation_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    category TEXT,
                    source TEXT NOT NULL,
                    context_json TEXT NOT NULL DEFAULT '{}',
                    assessment_id INTEGER
                );
                CREATE INDEX IF NOT EXISTS idx_rec_lifecycle_user
                    ON recommendation_lifecycle_events(user_id, recommendation_id);
                CREATE INDEX IF NOT EXISTS idx_rec_lifecycle_status
                    ON recommendation_lifecycle_events(status, occurred_at);
                CREATE TABLE IF NOT EXISTS recommendation_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    recommendation_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    submitted_at TEXT NOT NULL,
                    rating REAL,
                    useful INTEGER,
                    reason TEXT,
                    comment TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_rec_feedback_user
                    ON recommendation_feedback(user_id, recommendation_id);
                CREATE TABLE IF NOT EXISTS recommendation_outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    recommendation_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    measured_at TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    value REAL,
                    unit TEXT,
                    baseline_value REAL,
                    target_value REAL,
                    evidence_quality REAL NOT NULL,
                    notes TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_rec_outcome_user
                    ON recommendation_outcomes(user_id, recommendation_id);
                CREATE TABLE IF NOT EXISTS recommendation_learning_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    recommendation_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    generated_at TEXT NOT NULL,
                    engine_version TEXT NOT NULL,
                    signal_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_rec_snapshot_user
                    ON recommendation_learning_snapshots(user_id, generated_at);
                """
            )
        self._initialized = True

    def record_event(self, event: RecommendationEvent) -> bool:
        """Persist an event; duplicate event IDs are rejected without overwrite."""
        self.initialize()
        with self._connect() as conn:
            try:
                conn.execute(
                    """INSERT INTO recommendation_lifecycle_events
                    (event_id, recommendation_id, user_id, status, occurred_at,
                     category, source, context_json, assessment_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.event_id,
                        event.recommendation_id,
                        event.user_id,
                        event.status.value,
                        event.occurred_at,
                        event.category,
                        event.source,
                        json.dumps(event.context, sort_keys=True),
                        event.assessment_id,
                    ),
                )
            except sqlite3.IntegrityError:
                return False
        return True

    def record_feedback(self, feedback: RecommendationFeedback) -> bool:
        """Persist feedback without modifying previous feedback rows."""
        self.initialize()
        with self._connect() as conn:
            try:
                conn.execute(
                    """INSERT INTO recommendation_feedback
                    (feedback_id, recommendation_id, user_id, submitted_at,
                     rating, useful, reason, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        feedback.feedback_id,
                        feedback.recommendation_id,
                        feedback.user_id,
                        feedback.submitted_at,
                        feedback.rating,
                        None if feedback.useful is None else int(feedback.useful),
                        feedback.reason.value if feedback.reason else None,
                        feedback.comment,
                    ),
                )
            except sqlite3.IntegrityError:
                return False
        return True

    def record_outcome(self, outcome: RecommendationOutcome) -> bool:
        """Persist an observed outcome."""
        self.initialize()
        with self._connect() as conn:
            try:
                conn.execute(
                    """INSERT INTO recommendation_outcomes
                    (outcome_id, recommendation_id, user_id, measured_at, outcome,
                     value, unit, baseline_value, target_value, evidence_quality, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        outcome.outcome_id,
                        outcome.recommendation_id,
                        outcome.user_id,
                        outcome.measured_at,
                        outcome.outcome,
                        outcome.value,
                        outcome.unit,
                        outcome.baseline_value,
                        outcome.target_value,
                        outcome.evidence_quality,
                        outcome.notes,
                    ),
                )
            except sqlite3.IntegrityError:
                return False
        return True

    def record_feedback_form(
        self,
        *,
        recommendation_id: str,
        user_id: int,
        rating: float | None = None,
        useful: bool | None = None,
        reason: FeedbackReason | str | None = None,
        comment: str | None = None,
    ) -> RecommendationFeedback:
        """Validate and persist a convenient feedback form payload."""
        feedback = RecommendationFeedback(
            recommendation_id=recommendation_id,
            user_id=user_id,
            submitted_at=utc_now(),
            rating=rating,
            useful=useful,
            reason=_normalize_reason(reason),
            comment=comment,
        )
        if not self.record_feedback(feedback):
            raise LifecycleError("feedback_id already exists")
        return feedback

    def fetch_events(
        self,
        user_id: int,
        recommendation_id: str | None = None,
        limit: int = 1000,
    ) -> list[sqlite3.Row]:
        """Fetch lifecycle events in chronological order."""
        self.initialize()
        limit = max(1, min(int(limit), 10_000))
        with self._connect() as conn:
            if recommendation_id:
                return conn.execute(
                    """SELECT * FROM recommendation_lifecycle_events
                    WHERE user_id = ? AND recommendation_id = ?
                    ORDER BY occurred_at, event_id LIMIT ?""",
                    (user_id, recommendation_id, limit),
                ).fetchall()
            return conn.execute(
                """SELECT * FROM recommendation_lifecycle_events
                WHERE user_id = ? ORDER BY occurred_at, event_id LIMIT ?""",
                (user_id, limit),
            ).fetchall()

    def fetch_feedback(
        self,
        user_id: int,
        recommendation_id: str | None = None,
        limit: int = 1000,
    ) -> list[sqlite3.Row]:
        """Fetch feedback rows."""
        self.initialize()
        limit = max(1, min(int(limit), 10_000))
        with self._connect() as conn:
            if recommendation_id:
                return conn.execute(
                    """SELECT * FROM recommendation_feedback
                    WHERE user_id = ? AND recommendation_id = ?
                    ORDER BY submitted_at, feedback_id LIMIT ?""",
                    (user_id, recommendation_id, limit),
                ).fetchall()
            return conn.execute(
                """SELECT * FROM recommendation_feedback
                WHERE user_id = ? ORDER BY submitted_at, feedback_id LIMIT ?""",
                (user_id, limit),
            ).fetchall()

    def fetch_outcomes(
        self,
        user_id: int,
        recommendation_id: str | None = None,
        limit: int = 1000,
    ) -> list[sqlite3.Row]:
        """Fetch observed outcomes."""
        self.initialize()
        limit = max(1, min(int(limit), 10_000))
        with self._connect() as conn:
            if recommendation_id:
                return conn.execute(
                    """SELECT * FROM recommendation_outcomes
                    WHERE user_id = ? AND recommendation_id = ?
                    ORDER BY measured_at, outcome_id LIMIT ?""",
                    (user_id, recommendation_id, limit),
                ).fetchall()
            return conn.execute(
                """SELECT * FROM recommendation_outcomes
                WHERE user_id = ? ORDER BY measured_at, outcome_id LIMIT ?""",
                (user_id, limit),
            ).fetchall()

    def recommendation_ids(self, user_id: int) -> list[str]:
        """Return unique recommendation IDs seen by a user."""
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT recommendation_id FROM recommendation_lifecycle_events
                WHERE user_id = ? UNION SELECT recommendation_id
                FROM recommendation_feedback WHERE user_id = ?
                UNION SELECT recommendation_id FROM recommendation_outcomes WHERE user_id = ?
                ORDER BY recommendation_id""",
                (user_id, user_id, user_id),
            ).fetchall()
        return [str(row[0]) for row in rows]

    def save_snapshot(self, user_id: int, signal: RecommendationLearningSignal) -> str:
        """Save an immutable learning snapshot."""
        self.initialize()
        snapshot_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO recommendation_learning_snapshots
                (snapshot_id, recommendation_id, user_id, generated_at,
                 engine_version, signal_json) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    snapshot_id,
                    signal.recommendation_id,
                    user_id,
                    utc_now(),
                    ENGINE_VERSION,
                    json.dumps(signal.to_dict(), sort_keys=True),
                ),
            )
        return snapshot_id

    def latest_snapshots(self, user_id: int, limit: int = 100) -> list[dict[str, Any]]:
        """Return the newest immutable snapshots."""
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM recommendation_learning_snapshots
                WHERE user_id = ? ORDER BY generated_at DESC LIMIT ?""",
                (user_id, max(1, min(int(limit), 1000))),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["signal"] = json.loads(item.pop("signal_json"))
            result.append(item)
        return result

    def delete_user_data(self, user_id: int) -> int:
        """Delete lifecycle data for a user, useful for privacy/account removal."""
        self.initialize()
        with self._connect() as conn:
            total = 0
            for table in (
                "recommendation_lifecycle_events",
                "recommendation_feedback",
                "recommendation_outcomes",
                "recommendation_learning_snapshots",
            ):
                cursor = conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
                total += cursor.rowcount
        return total


def build_profile(
    events: Sequence[Mapping[str, Any]],
    feedback: Sequence[Mapping[str, Any]],
    recommendation_id: str,
) -> RecommendationProfile:
    """Build a recommendation profile from raw records."""
    relevant_events = [
        row for row in events if str(row.get("recommendation_id")) == recommendation_id
    ]
    relevant_feedback = [
        row for row in feedback if str(row.get("recommendation_id")) == recommendation_id
    ]
    counts = {status.value: 0 for status in RecommendationStatus}
    for row in relevant_events:
        status = str(row.get("status", ""))
        if status in counts:
            counts[status] += 1
    ratings = [_safe_float(row.get("rating")) for row in relevant_feedback]
    ratings = [x for x in ratings if x is not None]
    useful_values = [row.get("useful") for row in relevant_feedback if row.get("useful") is not None]
    useful = [bool(int(x)) if isinstance(x, (int, str)) and str(x).isdigit() else bool(x) for x in useful_values]
    reasons: dict[str, int] = {}
    for row in relevant_feedback:
        reason = row.get("reason")
        if reason:
            reasons[str(reason)] = reasons.get(str(reason), 0) + 1
    impressions = counts[RecommendationStatus.SHOWN.value]
    starts = counts[RecommendationStatus.STARTED.value]
    completions = counts[RecommendationStatus.COMPLETED.value]
    last = max(relevant_events, key=lambda x: str(x.get("occurred_at", "")), default=None)
    return RecommendationProfile(
        recommendation_id=recommendation_id,
        impressions=impressions,
        saves=counts[RecommendationStatus.SAVED.value],
        starts=starts,
        completions=completions,
        dismissals=counts[RecommendationStatus.DISMISSED.value],
        snoozes=counts[RecommendationStatus.SNOOZED.value],
        skips=counts[RecommendationStatus.SKIPPED.value],
        ratings=len(ratings),
        average_rating=round(statistics.fmean(ratings), 4) if ratings else None,
        useful_rate=_ratio(sum(useful), len(useful)),
        completion_rate=_ratio(completions, starts),
        start_rate=_ratio(starts, impressions),
        dismissal_rate=_ratio(counts[RecommendationStatus.DISMISSED.value], impressions),
        last_status=str(last.get("status")) if last else None,
        last_event_at=str(last.get("occurred_at")) if last else None,
        feedback_reasons=reasons,
    )


def analyze_recommendation(
    recommendation_id: str,
    events: Sequence[Mapping[str, Any]],
    feedback: Sequence[Mapping[str, Any]],
) -> RecommendationLearningSignal:
    """Analyze one recommendation without touching persistent state."""
    profile = build_profile(events, feedback, recommendation_id)
    return calculate_learning_signal(profile)


def analyze_portfolio(
    events: Sequence[Mapping[str, Any]],
    feedback: Sequence[Mapping[str, Any]],
    recommendation_ids: Iterable[str] | None = None,
) -> list[RecommendationLearningSignal]:
    """Analyze many recommendations in deterministic ID order."""
    ids = set(recommendation_ids or ())
    if not ids:
        ids = {str(row.get("recommendation_id")) for row in events if row.get("recommendation_id")}
        ids.update(str(row.get("recommendation_id")) for row in feedback if row.get("recommendation_id"))
    return [analyze_recommendation(rid, events, feedback) for rid in sorted(ids)]


def build_user_summary(
    user_id: int,
    events: Sequence[Mapping[str, Any]],
    feedback: Sequence[Mapping[str, Any]],
) -> LifecycleSummary:
    """Build an explainable portfolio summary."""
    user_events = [row for row in events if int(row.get("user_id", user_id)) == user_id]
    user_feedback = [row for row in feedback if int(row.get("user_id", user_id)) == user_id]
    ids = sorted({str(row.get("recommendation_id")) for row in user_events + user_feedback if row.get("recommendation_id")})
    signals = analyze_portfolio(user_events, user_feedback, ids)
    shown = sum(1 for row in user_events if row.get("status") == RecommendationStatus.SHOWN.value)
    started = sum(1 for row in user_events if row.get("status") == RecommendationStatus.STARTED.value)
    completed = sum(1 for row in user_events if row.get("status") == RecommendationStatus.COMPLETED.value)
    dismissed = sum(1 for row in user_events if row.get("status") == RecommendationStatus.DISMISSED.value)
    ratings = [_safe_float(row.get("rating")) for row in user_feedback]
    ratings = [x for x in ratings if x is not None]
    useful_values = [row.get("useful") for row in user_feedback if row.get("useful") is not None]
    useful = [bool(int(x)) if isinstance(x, (int, str)) and str(x).isdigit() else bool(x) for x in useful_values]
    areas: list[str] = []
    if shown and dismissed / shown >= 0.35:
        areas.append("Review recommendations with high dismissal rates.")
    if user_feedback and useful and sum(useful) / len(useful) < 0.5:
        areas.append("Review relevance and feasibility of low-rated recommendations.")
    if not user_feedback:
        areas.append("Collect explicit feedback before changing recommendation weights.")
    if not started and shown:
        areas.append("Investigate barriers preventing users from starting recommendations.")
    top = tuple(sorted(signals, key=lambda s: (-s.learning_score, s.recommendation_id))[:5])
    return LifecycleSummary(
        user_id=user_id,
        recommendation_count=len(ids),
        shown_count=shown,
        started_count=started,
        completed_count=completed,
        dismissed_count=dismissed,
        average_rating=round(statistics.fmean(ratings), 4) if ratings else None,
        useful_rate=_ratio(sum(useful), len(useful)),
        completion_rate=_ratio(completed, started),
        engagement_rate=_ratio(started, shown),
        top_recommendations=top,
        improvement_areas=tuple(areas),
    )


def calculate_outcome_change(outcome: RecommendationOutcome) -> float | None:
    """Return percentage change from baseline when both values exist."""
    if outcome.value is None or outcome.baseline_value is None:
        return None
    baseline = float(outcome.baseline_value)
    if baseline == 0:
        return None
    return round((float(outcome.value) - baseline) / abs(baseline) * 100, 4)


def calculate_target_progress(outcome: RecommendationOutcome) -> float | None:
    """Return 0..1 progress toward a target when all values are available."""
    if outcome.value is None or outcome.baseline_value is None or outcome.target_value is None:
        return None
    denominator = outcome.target_value - outcome.baseline_value
    if denominator == 0:
        return 1.0 if outcome.value == outcome.target_value else 0.0
    progress = (outcome.value - outcome.baseline_value) / denominator
    return round(min(max(progress, 0.0), 1.0), 4)


def summarize_outcomes(outcomes: Sequence[RecommendationOutcome]) -> dict[str, Any]:
    """Summarize outcome evidence without asserting causality."""
    changes = [calculate_outcome_change(item) for item in outcomes]
    changes = [x for x in changes if x is not None]
    progresses = [calculate_target_progress(item) for item in outcomes]
    progresses = [x for x in progresses if x is not None]
    evidence = [float(item.evidence_quality) for item in outcomes]
    return {
        "observations": len(outcomes),
        "measured_changes": len(changes),
        "average_change_pct": round(statistics.fmean(changes), 4) if changes else None,
        "average_target_progress": round(statistics.fmean(progresses), 4) if progresses else None,
        "average_evidence_quality": round(statistics.fmean(evidence), 4) if evidence else None,
        "causal_claim_supported": False,
        "caveat": "Observed outcomes do not by themselves establish causation.",
    }


def export_lifecycle_json(
    user_id: int,
    store: RecommendationLifecycleStore,
) -> str:
    """Export lifecycle data for the current user as inspectable JSON."""
    events = [dict(row) for row in store.fetch_events(user_id, limit=10_000)]
    feedback = [dict(row) for row in store.fetch_feedback(user_id, limit=10_000)]
    outcomes = [dict(row) for row in store.fetch_outcomes(user_id, limit=10_000)]
    for row in events:
        row["context"] = json.loads(row.pop("context_json", "{}"))
    return json.dumps(
        {
            "schema_version": SCHEMA_VERSION,
            "engine_version": ENGINE_VERSION,
            "exported_at": utc_now(),
            "user_id": user_id,
            "events": events,
            "feedback": feedback,
            "outcomes": outcomes,
        },
        indent=2,
        sort_keys=True,
    )


def export_signals_csv(signals: Sequence[RecommendationLearningSignal]) -> str:
    """Export learning signals as CSV for local analysis."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "recommendation_id",
            "sample_size",
            "engagement_score",
            "satisfaction_score",
            "completion_score",
            "feedback_confidence",
            "learning_score",
            "confidence_label",
            "positive_signals",
            "negative_signals",
        ],
    )
    writer.writeheader()
    for signal in signals:
        row = signal.to_dict()
        row["positive_signals"] = "; ".join(signal.positive_signals)
        row["negative_signals"] = "; ".join(signal.negative_signals)
        writer.writerow(row)
    return output.getvalue()


def feedback_reason_label(reason: str | None) -> str:
    """Human-readable feedback reason."""
    if not reason:
        return "Unspecified"
    return str(reason).replace("_", " ").title()


def status_label(status: str | None) -> str:
    """Human-readable lifecycle status."""
    if not status:
        return "Unknown"
    return str(status).replace("_", " ").title()


def recommendation_learning_disclaimer() -> str:
    """Return the UI disclosure required for responsible learning analytics."""
    return (
        "Feedback signals describe observed user behavior. They are not proof that a "
        "recommendation caused an environmental outcome, and low-volume signals should "
        "not be treated as reliable ranking evidence."
    )


def create_event(
    recommendation_id: str,
    user_id: int,
    status: RecommendationStatus | str,
    *,
    category: str | None = None,
    source: str = "recommendation_engine",
    context: Mapping[str, Any] | None = None,
    assessment_id: int | None = None,
    occurred_at: str | None = None,
) -> RecommendationEvent:
    """Create a validated lifecycle event."""
    if context is not None and not isinstance(context, Mapping):
        raise LifecycleError("context must be an object")
    return RecommendationEvent(
        recommendation_id=recommendation_id,
        user_id=user_id,
        status=_normalize_status(status),
        occurred_at=occurred_at or utc_now(),
        category=category,
        source=source,
        context=dict(context or {}),
        assessment_id=assessment_id,
    )


def create_outcome(
    recommendation_id: str,
    user_id: int,
    outcome: str,
    *,
    value: float | None = None,
    unit: str | None = None,
    baseline_value: float | None = None,
    target_value: float | None = None,
    evidence_quality: float = 0.5,
    notes: str | None = None,
    measured_at: str | None = None,
) -> RecommendationOutcome:
    """Create a validated outcome observation."""
    return RecommendationOutcome(
        recommendation_id=recommendation_id,
        user_id=user_id,
        measured_at=measured_at or utc_now(),
        outcome=outcome,
        value=value,
        unit=unit,
        baseline_value=baseline_value,
        target_value=target_value,
        evidence_quality=evidence_quality,
        notes=notes,
    )


def parse_import_document(raw: str) -> dict[str, Any]:
    """Parse and validate a lifecycle export without persisting it."""
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LifecycleError("Invalid JSON export") from exc
    if not isinstance(document, dict):
        raise LifecycleError("Export root must be an object")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise LifecycleError("Unsupported lifecycle export schema version")
    for key in ("events", "feedback", "outcomes"):
        if not isinstance(document.get(key), list):
            raise LifecycleError(f"{key} must be an array")
    return document


def import_lifecycle_document(
    raw: str,
    store: RecommendationLifecycleStore,
    user_id: int,
) -> dict[str, int]:
    """Import a validated export transactionally for one user."""
    document = parse_import_document(raw)
    imported = {"events": 0, "feedback": 0, "outcomes": 0, "skipped": 0}
    store.initialize()
    conn = store._connect()
    try:
        conn.execute("BEGIN")
        for raw_event in document["events"]:
            if int(raw_event.get("user_id", user_id)) != user_id:
                raise LifecycleError("Export contains another user's event")
            event = create_event(
                raw_event["recommendation_id"], user_id, raw_event["status"],
                category=raw_event.get("category"), source=raw_event.get("source", "import"),
                context=raw_event.get("context", {}), assessment_id=raw_event.get("assessment_id"),
                occurred_at=raw_event["occurred_at"],
            )
            event = RecommendationEvent(
                recommendation_id=event.recommendation_id,
                user_id=event.user_id,
                status=_normalize_status(event.status),
                occurred_at=event.occurred_at,
                event_id=raw_event["event_id"],
                category=event.category,
                source=event.source,
                context=event.context,
                assessment_id=event.assessment_id,
            )
            cursor = conn.execute(
                """INSERT OR IGNORE INTO recommendation_lifecycle_events
                (event_id, recommendation_id, user_id, status, occurred_at, category,
                 source, context_json, assessment_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event.event_id, event.recommendation_id, user_id, event.status.value,
                 event.occurred_at, event.category, event.source, json.dumps(event.context), event.assessment_id),
            )
            imported["events"] += int(cursor.rowcount > 0)
            imported["skipped"] += int(cursor.rowcount == 0)
        for raw_feedback in document["feedback"]:
            if int(raw_feedback.get("user_id", user_id)) != user_id:
                raise LifecycleError("Export contains another user's feedback")
            feedback = RecommendationFeedback(
                recommendation_id=raw_feedback["recommendation_id"], user_id=user_id,
                submitted_at=raw_feedback["submitted_at"], rating=raw_feedback.get("rating"),
                useful=raw_feedback.get("useful"), reason=_normalize_reason(raw_feedback.get("reason")),
                comment=raw_feedback.get("comment"), feedback_id=raw_feedback["feedback_id"],
            )
            cursor = conn.execute(
                """INSERT OR IGNORE INTO recommendation_feedback
                (feedback_id, recommendation_id, user_id, submitted_at, rating, useful, reason, comment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (feedback.feedback_id, feedback.recommendation_id, user_id, feedback.submitted_at,
                 feedback.rating, None if feedback.useful is None else int(feedback.useful),
                 feedback.reason.value if feedback.reason else None, feedback.comment),
            )
            imported["feedback"] += int(cursor.rowcount > 0)
            imported["skipped"] += int(cursor.rowcount == 0)
        for raw_outcome in document["outcomes"]:
            if int(raw_outcome.get("user_id", user_id)) != user_id:
                raise LifecycleError("Export contains another user's outcome")
            outcome = RecommendationOutcome(
                recommendation_id=raw_outcome["recommendation_id"], user_id=user_id,
                measured_at=raw_outcome["measured_at"], outcome=raw_outcome["outcome"],
                value=raw_outcome.get("value"), unit=raw_outcome.get("unit"),
                baseline_value=raw_outcome.get("baseline_value"), target_value=raw_outcome.get("target_value"),
                evidence_quality=raw_outcome.get("evidence_quality", 0.5), notes=raw_outcome.get("notes"),
                outcome_id=raw_outcome["outcome_id"],
            )
            cursor = conn.execute(
                """INSERT OR IGNORE INTO recommendation_outcomes
                (outcome_id, recommendation_id, user_id, measured_at, outcome, value, unit,
                 baseline_value, target_value, evidence_quality, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (outcome.outcome_id, outcome.recommendation_id, user_id, outcome.measured_at,
                 outcome.outcome, outcome.value, outcome.unit, outcome.baseline_value,
                 outcome.target_value, outcome.evidence_quality, outcome.notes),
            )
            imported["outcomes"] += int(cursor.rowcount > 0)
            imported["skipped"] += int(cursor.rowcount == 0)
        conn.commit()
        return imported
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


__all__ = [
    "DB_NAME", "ENGINE_VERSION", "SCHEMA_VERSION", "LifecycleError",
    "RecommendationStatus", "FeedbackType", "FeedbackReason",
    "RecommendationEvent", "RecommendationFeedback", "RecommendationOutcome",
    "RecommendationProfile", "RecommendationLearningSignal", "LifecycleSummary",
    "RecommendationLifecycleStore", "validate_event_payload", "validate_feedback_payload",
    "calculate_engagement_score", "calculate_completion_score", "calculate_feedback_confidence",
    "calculate_learning_signal", "build_profile", "analyze_recommendation", "analyze_portfolio",
    "build_user_summary", "calculate_outcome_change", "calculate_target_progress", "summarize_outcomes",
    "export_lifecycle_json", "export_signals_csv", "feedback_reason_label", "status_label",
    "recommendation_learning_disclaimer", "create_event", "create_outcome", "parse_import_document",
    "import_lifecycle_document", "utc_now",
]
