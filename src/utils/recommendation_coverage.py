"""Recommendation coverage and sustainability gap analysis.

This module is an analysis layer over EcoBuddy's existing recommendation
pipeline.  It does not generate new src.ai.recommendations.  Instead it answers
whether the recommendations already available to a user adequately cover the
categories that matter most in the user's assessment.

The public API is deliberately dependency-light so it can be reused by the
Streamlit page, tests, and future API endpoints without importing Streamlit.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

DEFAULT_CATEGORIES = (
    "transport",
    "electricity",
    "diet",
    "water",
    "waste",
    "shopping",
    "general",
    "offset",
)

CATEGORY_ALIASES = {
    "transportation": "transport",
    "transport": "transport",
    "travel": "transport",
    "commute": "transport",
    "electricity": "electricity",
    "energy": "electricity",
    "home energy": "electricity",
    "diet": "diet",
    "food": "diet",
    "nutrition": "diet",
    "water": "water",
    "waste": "waste",
    "recycling": "waste",
    "shopping": "shopping",
    "consumption": "shopping",
    "purchasing": "shopping",
    "lifestyle": "general",
    "general lifestyle": "general",
    "general": "general",
    "offset": "offset",
    "carbon offset": "offset",
}

CATEGORY_KEYWORDS = {
    "transport": (
        "transport", "car", "commute", "bike", "cycling", "walk", "walking",
        "bus", "train", "public transit", "public transport", "vehicle", "ev",
        "electric vehicle", "flight", "air travel", "travel",
    ),
    "electricity": (
        "electricity", "energy", "led", "thermostat", "appliance", "solar",
        "heating", "cooling", "power", "standby", "renewable",
    ),
    "diet": (
        "food", "diet", "meal", "meat", "plant-based", "vegetarian", "vegan",
        "food waste", "cooking", "produce",
    ),
    "water": (
        "water", "shower", "laundry", "rainwater", "leak", "low-flow", "garden",
    ),
    "waste": (
        "waste", "recycl", "plastic", "reuse", "reusable", "compost", "landfill",
        "single-use",
    ),
    "shopping": (
        "shop", "shopping", "purchase", "buy", "product", "clothing", "fashion",
        "appliance", "consume", "consumption",
    ),
    "offset": (
        "offset", "tree", "reforestation", "carbon credit",
    ),
}

CATEGORY_LABELS = {
    "transport": "Transportation",
    "electricity": "Electricity & Energy",
    "diet": "Food & Diet",
    "water": "Water",
    "waste": "Waste",
    "shopping": "Shopping & Consumption",
    "general": "General Lifestyle",
    "offset": "Carbon Offsets",
}

class GapSeverity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CoverageStatus(str, Enum):
    COVERED = "covered"
    PARTIAL = "partial"
    GAP = "gap"
    NO_DATA = "no_data"


@dataclass(frozen=True)
class RecommendationRecord:
    """Normalized representation of an existing recommendation."""

    id: str
    title: str
    description: str
    category: str
    impact_score: float | None = None
    co2_savings: float | None = None
    difficulty: str | None = None
    tags: tuple[str, ...] = ()
    completed: bool = False
    rejected: bool = False
    source: str = "existing"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tags"] = list(self.tags)
        return data


@dataclass(frozen=True)
class CategoryCoverage:
    """Coverage metrics for one sustainability category."""

    category: str
    label: str
    impact: float
    impact_share: float
    recommendation_count: int
    relevant_count: int
    completed_count: int
    rejected_count: int
    unique_titles: int
    repetition_rate: float
    coverage_score: float
    status: CoverageStatus
    gap_severity: GapSeverity
    reason: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["gap_severity"] = self.gap_severity.value
        return data


@dataclass(frozen=True)
class CoverageGap:
    """A concrete reason a category is underserved."""

    category: str
    label: str
    severity: GapSeverity
    code: str
    title: str
    reason: str
    recommendation_count: int
    relevant_count: int
    suggested_follow_up: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


@dataclass(frozen=True)
class CoverageReport:
    """Complete, deterministic recommendation coverage src.reporting.report."""

    user_id: int | None
    created_at: str
    overall_score: float
    status: CoverageStatus
    categories: tuple[CategoryCoverage, ...]
    gaps: tuple[CoverageGap, ...]
    repeated_recommendations: tuple[str, ...]
    duplicate_ids: tuple[str, ...]
    recommendation_count: int
    category_count: int
    covered_category_count: int
    high_impact_uncovered_count: int
    recommendation_diversity: float
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "created_at": self.created_at,
            "overall_score": self.overall_score,
            "status": self.status.value,
            "categories": [item.to_dict() for item in self.categories],
            "gaps": [item.to_dict() for item in self.gaps],
            "repeated_recommendations": list(self.repeated_recommendations),
            "duplicate_ids": list(self.duplicate_ids),
            "recommendation_count": self.recommendation_count,
            "category_count": self.category_count,
            "covered_category_count": self.covered_category_count,
            "high_impact_uncovered_count": self.high_impact_uncovered_count,
            "recommendation_diversity": self.recommendation_diversity,
            "metadata": dict(self.metadata),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


@dataclass(frozen=True)
class RecommendationCoverageConfig:
    """Configurable thresholds for deterministic coverage analysis."""

    high_impact_share: float = 0.20
    critical_impact_share: float = 0.40
    full_coverage_recommendations: int = 3
    partial_coverage_recommendations: int = 1
    repetition_warning_rate: float = 0.50
    repeated_title_threshold: int = 2
    minimum_diversity_categories: int = 2

    def __post_init__(self) -> None:
        if not 0 <= self.high_impact_share <= 1:
            raise ValueError("high_impact_share must be between 0 and 1")
        if not 0 <= self.critical_impact_share <= 1:
            raise ValueError("critical_impact_share must be between 0 and 1")
        if self.full_coverage_recommendations < 1:
            raise ValueError("full_coverage_recommendations must be positive")
        if self.partial_coverage_recommendations < 1:
            raise ValueError("partial_coverage_recommendations must be positive")
        if not 0 <= self.repetition_warning_rate <= 1:
            raise ValueError("repetition_warning_rate must be between 0 and 1")
        if self.repeated_title_threshold < 2:
            raise ValueError("repeated_title_threshold must be at least 2")
        if self.minimum_diversity_categories < 1:
            raise ValueError("minimum_diversity_categories must be positive")


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _normalise_text(value: Any) -> str:
    text = _slug(value)
    stop = {"your", "you", "the", "a", "an", "to", "for", "and", "of", "with"}
    return " ".join(token for token in text.split() if token not in stop)


def _stable_id(title: str, category: str) -> str:
    seed = f"{_slug(category)}|{_normalise_text(title)}"
    return "rec-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def normalize_category(category: Any, *, title: str = "", description: str = "") -> str:
    """Map existing category variants to the shared sustainability taxonomy."""
    key = _slug(category)
    if key in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[key]

    text = f"{_slug(title)} {_slug(description)}"
    matches: list[tuple[int, str]] = []
    for candidate, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score:
            matches.append((score, candidate))
    if matches:
        matches.sort(key=lambda pair: (-pair[0], pair[1]))
        return matches[0][1]
    return "general"


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(normalize_category(category), str(category).title())


def _safe_float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    number = _finite(value, math.nan)
    return None if not math.isfinite(number) else number


def _extract_tags(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw = re.split(r"[,;|]", value)
    else:
        try:
            raw = list(value)
        except TypeError:
            raw = [value]
    return tuple(sorted({_slug(item) for item in raw if _slug(item)}))


def _mapping_value(data: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in data:
            return data[name]
    return None


# ---------------------------------------------------------------------------
# Normalisation of existing recommendation output
# ---------------------------------------------------------------------------

def normalize_recommendation(
    recommendation: Any,
    *,
    index: int = 0,
    fallback_category: str | None = None,
) -> RecommendationRecord:
    """Normalize a dict, Recommendation dataclass, or existing recommendation string.

    This function intentionally accepts the output of both ``src.ai.recommendations.py``
    and ``src.ai.recommendation_engine.py`` so the coverage layer does not force a
    migration of the existing recommendation generator.
    """
    if isinstance(recommendation, RecommendationRecord):
        return recommendation

    if isinstance(recommendation, str):
        title = recommendation.strip() or f"Recommendation {index + 1}"
        category = normalize_category(fallback_category or "", title=title)
        return RecommendationRecord(
            id=_stable_id(title, category),
            title=title,
            description=title,
            category=category,
            source="src.ai.recommendations.py",
        )

    if hasattr(recommendation, "to_dict"):
        try:
            recommendation = recommendation.to_dict()
        except Exception:
            recommendation = vars(recommendation)

    if not isinstance(recommendation, Mapping):
        # Some lightweight objects expose fields as class attributes, so vars()
        # can be empty. Materialize the public fields before falling back to vars.
        recommendation = {
            name: getattr(recommendation, name)
            for name in (
                "id", "recommendation_id", "key", "title", "name", "text",
                "recommendation", "description", "details", "category", "domain",
                "area", "impact_score", "impact", "priority_score", "co2_savings",
                "carbon_savings", "estimated_impact", "difficulty", "effort",
                "effort_level", "tags", "keywords", "completed", "is_completed",
                "rejected", "is_rejected", "source", "provider",
            )
            if hasattr(recommendation, name)
        } or vars(recommendation)

    title = str(_mapping_value(recommendation, "title", "name", "text", "recommendation") or "").strip()
    description = str(_mapping_value(recommendation, "description", "details", "text") or title).strip()
    raw_category = _mapping_value(recommendation, "category", "domain", "area") or fallback_category or ""
    category = normalize_category(raw_category, title=title, description=description)
    raw_id = _mapping_value(recommendation, "id", "recommendation_id", "key")
    recommendation_id = str(raw_id).strip() if raw_id is not None else _stable_id(title, category)
    if not recommendation_id:
        recommendation_id = _stable_id(title, category)

    priority = _safe_float_or_none(_mapping_value(recommendation, "impact_score", "impact", "priority_score"))
    savings = _safe_float_or_none(_mapping_value(recommendation, "co2_savings", "carbon_savings", "estimated_impact"))
    difficulty = _mapping_value(recommendation, "difficulty", "effort", "effort_level")
    if difficulty is not None:
        difficulty = str(difficulty).lower()
    tags = _extract_tags(_mapping_value(recommendation, "tags", "keywords"))
    completed = bool(_mapping_value(recommendation, "completed", "is_completed") or False)
    rejected = bool(_mapping_value(recommendation, "rejected", "is_rejected") or False)
    source = str(_mapping_value(recommendation, "source", "provider") or "existing")

    return RecommendationRecord(
        id=recommendation_id,
        title=title or f"Recommendation {index + 1}",
        description=description,
        category=category,
        impact_score=priority,
        co2_savings=savings,
        difficulty=difficulty,
        tags=tags,
        completed=completed,
        rejected=rejected,
        source=source,
    )


def normalize_recommendations(
    recommendations: Iterable[Any],
    *,
    fallback_category: str | None = None,
) -> list[RecommendationRecord]:
    """Normalize and deterministically order existing src.ai.recommendations."""
    result = [
        normalize_recommendation(item, index=index, fallback_category=fallback_category)
        for index, item in enumerate(recommendations)
    ]
    return sorted(result, key=lambda item: (item.category, _normalise_text(item.title), item.id))


def infer_recommendation_categories(recommendations: Iterable[Any]) -> dict[str, int]:
    normalized = normalize_recommendations(recommendations)
    return dict(Counter(item.category for item in normalized))


# ---------------------------------------------------------------------------
# Feedback/history helpers
# ---------------------------------------------------------------------------

def _event_value(event: Any, name: str, default: Any = None) -> Any:
    if isinstance(event, Mapping):
        return event.get(name, default)
    return getattr(event, name, default)


def recommendation_history(
    recommendations: Sequence[RecommendationRecord],
    feedback: Iterable[Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Aggregate existing recommendation feedback without changing it."""
    normalized = normalize_recommendations(recommendations)
    history: dict[str, dict[str, Any]] = {
        item.id: {
            "helpful": 0,
            "completed": 0,
            "rejected": 0,
            "dismissed": 0,
            "events": 0,
            "last_feedback": None,
        }
        for item in normalized
    }
    if not feedback:
        return history

    rejection_types = {"not_helpful", "not_relevant", "already_doing", "too_difficult"}
    for event in feedback:
        rid = str(_event_value(event, "recommendation_id", "")).strip()
        if rid not in history:
            continue
        feedback_type = str(_event_value(event, "feedback_type", "")).strip().lower()
        row = history[rid]
        row["events"] += 1
        row["last_feedback"] = feedback_type
        if feedback_type == "helpful":
            row["helpful"] += 1
        elif feedback_type == "completed":
            row["completed"] += 1
        elif feedback_type in rejection_types:
            row["rejected"] += 1
        elif feedback_type == "dismissed":
            row["dismissed"] += 1
    return history


def mark_history_status(
    recommendations: Iterable[RecommendationRecord],
    feedback: Iterable[Any] | None = None,
) -> list[RecommendationRecord]:
    """Apply feedback-derived status to normalized records for analysis only."""
    items = list(recommendations)
    history = recommendation_history(items, feedback)
    result: list[RecommendationRecord] = []
    for item in items:
        row = history[item.id]
        result.append(
            RecommendationRecord(
                **{
                    **asdict(item),
                    "completed": item.completed or row["completed"] > 0,
                    "rejected": item.rejected or row["rejected"] > 0,
                }
            )
        )
    return result


# ---------------------------------------------------------------------------
# Repetition and diversity analysis
# ---------------------------------------------------------------------------

def detect_repeated_recommendations(
    recommendations: Iterable[RecommendationRecord],
    *,
    threshold: int = 2,
) -> list[str]:
    """Return normalized titles repeated at least ``threshold`` times."""
    if threshold < 2:
        raise ValueError("threshold must be at least 2")
    counts = Counter(_normalise_text(item.title) for item in recommendations if item.title.strip())
    repeated = [title for title, count in counts.items() if count >= threshold]
    return sorted(repeated)


def duplicate_recommendation_ids(recommendations: Iterable[RecommendationRecord]) -> list[str]:
    counts = Counter(item.id for item in recommendations)
    return sorted(rid for rid, count in counts.items() if count > 1)


def calculate_recommendation_diversity(
    recommendations: Iterable[RecommendationRecord],
) -> float:
    """Return a 0..1 category diversity score using normalized entropy."""
    categories = [item.category for item in recommendations]
    if not categories:
        return 0.0
    counts = Counter(categories)
    if len(counts) == 1:
        return 0.0
    total = len(categories)
    entropy = -sum((count / total) * math.log(count / total) for count in counts.values())
    max_entropy = math.log(len(counts))
    return round(entropy / max_entropy if max_entropy else 0.0, 6)


def category_distribution(
    recommendations: Iterable[RecommendationRecord],
) -> dict[str, int]:
    return dict(sorted(Counter(item.category for item in recommendations).items()))


# ---------------------------------------------------------------------------
# Impact and category calculations
# ---------------------------------------------------------------------------

def normalize_contributors(contributors: Mapping[str, Any] | None) -> dict[str, float]:
    """Normalize assessment contributor keys to the shared category taxonomy."""
    result: defaultdict[str, float] = defaultdict(float)
    for raw_category, raw_value in (contributors or {}).items():
        value = max(0.0, _finite(raw_value))
        category = normalize_category(raw_category)
        result[category] += value
    return dict(sorted(result.items()))


def calculate_impact_shares(contributors: Mapping[str, Any] | None) -> dict[str, float]:
    normalized = normalize_contributors(contributors)
    total = sum(normalized.values())
    if total <= 0:
        return {category: 0.0 for category in normalized}
    return {category: value / total for category, value in normalized.items()}


def highest_impact_categories(
    contributors: Mapping[str, Any] | None,
    *,
    minimum_share: float = 0.0,
) -> list[tuple[str, float, float]]:
    normalized = normalize_contributors(contributors)
    shares = calculate_impact_shares(contributors)
    result = [
        (category, normalized[category], shares.get(category, 0.0))
        for category in normalized
        if shares.get(category, 0.0) >= minimum_share
    ]
    return sorted(result, key=lambda row: (-row[2], -row[1], row[0]))


def _impact_bucket(share: float, config: RecommendationCoverageConfig) -> str:
    if share >= src.core.config.critical_impact_share:
        return "critical"
    if share >= src.core.config.high_impact_share:
        return "high"
    return "normal"


def _coverage_status(
    recommendation_count: int,
    relevant_count: int,
    completed_count: int,
    share: float,
    config: RecommendationCoverageConfig,
) -> CoverageStatus:
    effective = max(0, relevant_count - completed_count)
    if share <= 0 and recommendation_count == 0:
        return CoverageStatus.NO_DATA
    if effective >= src.core.config.full_coverage_recommendations:
        return CoverageStatus.COVERED
    if effective >= src.core.config.partial_coverage_recommendations:
        return CoverageStatus.PARTIAL
    return CoverageStatus.GAP


def _gap_severity(
    status: CoverageStatus,
    share: float,
    *,
    completed_count: int,
    rejected_count: int,
    config: RecommendationCoverageConfig,
) -> GapSeverity:
    if status in {CoverageStatus.COVERED, CoverageStatus.NO_DATA}:
        return GapSeverity.NONE
    if share >= src.core.config.critical_impact_share and completed_count > 0:
        return GapSeverity.CRITICAL
    if share >= src.core.config.critical_impact_share:
        return GapSeverity.CRITICAL
    if share >= src.core.config.high_impact_share:
        return GapSeverity.HIGH
    if rejected_count > 0 and share >= src.core.config.high_impact_share / 2:
        return GapSeverity.MEDIUM
    return GapSeverity.LOW


def _coverage_score(
    relevant_count: int,
    completed_count: int,
    rejected_count: int,
    repetition_rate: float,
    share: float,
    config: RecommendationCoverageConfig,
) -> float:
    """Calculate category coverage independently from global recommendation ranking."""
    effective = max(0, relevant_count - completed_count)
    count_score = min(1.0, effective / src.core.config.full_coverage_recommendations)
    repetition_penalty = min(0.35, repetition_rate * 0.35)
    rejection_penalty = min(0.25, rejected_count / max(relevant_count, 1) * 0.25)
    impact_bonus = 0.10 if share >= src.core.config.high_impact_share and effective > 0 else 0.0
    score = count_score - repetition_penalty - rejection_penalty + impact_bonus
    return round(max(0.0, min(1.0, score)), 6)


def _category_reason(
    category: str,
    label: str,
    share: float,
    recommendation_count: int,
    relevant_count: int,
    completed_count: int,
    rejected_count: int,
    repetition_rate: float,
    status: CoverageStatus,
) -> str:
    impact = f"{share * 100:.0f}% of measured impact"
    if status == CoverageStatus.COVERED:
        return f"{label} has {relevant_count} relevant recommendations covering {impact}."
    if status == CoverageStatus.NO_DATA:
        return f"No assessment impact data is available for {label}."
    if completed_count and relevant_count <= completed_count:
        return f"{label} is important ({impact}), but its available recommendations are already completed."
    if recommendation_count == 0:
        return f"{label} represents {impact}, but no existing recommendation covers it."
    if rejected_count and relevant_count:
        return f"{label} has recommendations, but {rejected_count} relevant item(s) were previously rejected."
    if repetition_rate >= 0.5:
        return f"{label} has recommendations, but the set is repetitive and may not offer enough distinct choices."
    return f"{label} has only {relevant_count} relevant recommendation(s) for {impact}."


# ---------------------------------------------------------------------------
# Gap generation
# ---------------------------------------------------------------------------

def _gap(
    category: str,
    label: str,
    severity: GapSeverity,
    code: str,
    title: str,
    reason: str,
    count: int,
    relevant: int,
    follow_up: str,
) -> CoverageGap:
    return CoverageGap(
        category=category,
        label=label,
        severity=severity,
        code=code,
        title=title,
        reason=reason,
        recommendation_count=count,
        relevant_count=relevant,
        suggested_follow_up=follow_up,
    )


def find_coverage_gaps(
    category_rows: Sequence[CategoryCoverage],
    *,
    repeated_recommendations: Sequence[str] = (),
) -> list[CoverageGap]:
    """Turn category coverage findings into explicit, user-facing gaps."""
    gaps: list[CoverageGap] = []
    for row in category_rows:
        if row.status == CoverageStatus.NO_DATA:
            continue
        if row.relevant_count == 0 and row.impact_share > 0:
            severity = row.gap_severity
            gaps.append(_gap(
                row.category,
                row.label,
                severity,
                "MISSING_CATEGORY_COVERAGE",
                f"No recommendation covers {row.label}",
                row.reason,
                row.recommendation_count,
                row.relevant_count,
                "Review the existing recommendation catalog for an applicable action before creating new content.",
            ))
            continue
        if row.completed_count >= row.relevant_count and row.relevant_count > 0:
            gaps.append(_gap(
                row.category,
                row.label,
                row.gap_severity,
                "COMPLETED_RECOMMENDATION_GAP",
                f"Completed recommendations leave {row.label} underserved",
                row.reason,
                row.recommendation_count,
                row.relevant_count,
                "Surface a different existing recommendation or collect more category-specific options.",
            ))
        elif row.repetition_rate >= 0.5 and row.recommendation_count >= 2:
            gaps.append(_gap(
                row.category,
                row.label,
                row.gap_severity,
                "REPEATED_RECOMMENDATIONS",
                f"{row.label} recommendations are repetitive",
                row.reason,
                row.recommendation_count,
                row.relevant_count,
                "Prefer distinct existing recommendations with different effort or implementation paths.",
            ))
        elif row.status == CoverageStatus.GAP:
            gaps.append(_gap(
                row.category,
                row.label,
                row.gap_severity,
                "HIGH_IMPACT_LOW_COVERAGE" if row.impact_share >= 0.20 else "LOW_COVERAGE",
                f"{row.label} has insufficient recommendation coverage",
                row.reason,
                row.recommendation_count,
                row.relevant_count,
                "Prioritize an applicable recommendation from the existing catalog before lower-impact categories.",
            ))
        elif row.status == CoverageStatus.PARTIAL and row.impact_share >= 0.20:
            gaps.append(_gap(
                row.category,
                row.label,
                row.gap_severity,
                "HIGH_IMPACT_LOW_COVERAGE",
                f"{row.label} is only partially covered",
                row.reason,
                row.recommendation_count,
                row.relevant_count,
                "Add or surface more distinct existing recommendations for this high-impact category.",
            ))

    if repeated_recommendations:
        existing = {gap.category for gap in gaps}
        if "general" not in existing:
            gaps.append(_gap(
                "general",
                category_label("general"),
                GapSeverity.MEDIUM,
                "REPEATED_RECOMMENDATIONS",
                "Recommendation set contains repeated items",
                "Multiple recommendation entries normalize to the same title, reducing practical choice.",
                0,
                0,
                "Deduplicate or diversify the existing recommendation catalog.",
            ))
    return sorted(gaps, key=lambda gap: (-_severity_rank(gap.severity), gap.category, gap.code))


def _severity_rank(severity: GapSeverity) -> int:
    return {
        GapSeverity.NONE: 0,
        GapSeverity.LOW: 1,
        GapSeverity.MEDIUM: 2,
        GapSeverity.HIGH: 3,
        GapSeverity.CRITICAL: 4,
    }[severity]


# ---------------------------------------------------------------------------
# Main analysis API
# ---------------------------------------------------------------------------

def analyze_category_coverage(
    contributors: Mapping[str, Any] | None,
    recommendations: Iterable[Any],
    *,
    feedback: Iterable[Any] | None = None,
    config: RecommendationCoverageConfig | None = None,
) -> tuple[CategoryCoverage, ...]:
    """Analyze coverage for all assessment categories represented by the data."""
    config = config or RecommendationCoverageConfig()
    normalized_contributors = normalize_contributors(contributors)
    shares = calculate_impact_shares(contributors)
    normalized = mark_history_status(normalize_recommendations(recommendations), feedback)
    history = recommendation_history(normalized, feedback)

    categories = set(normalized_contributors) | {item.category for item in normalized}
    if not categories:
        categories = set(DEFAULT_CATEGORIES)

    rows: list[CategoryCoverage] = []
    for category in sorted(categories):
        category_items = [item for item in normalized if item.category == category]
        impact = normalized_contributors.get(category, 0.0)
        share = shares.get(category, 0.0)
        relevant = len(category_items)
        completed = sum(1 for item in category_items if item.completed or history[item.id]["completed"] > 0)
        rejected = sum(1 for item in category_items if item.rejected or history[item.id]["rejected"] > 0)
        titles = [_normalise_text(item.title) for item in category_items if item.title.strip()]
        title_counts = Counter(titles)
        repeated = sum(count - 1 for count in title_counts.values() if count > 1)
        repetition_rate = repeated / relevant if relevant else 0.0
        unique_titles = len(title_counts)
        status = _coverage_status(relevant, relevant, completed, share, config)
        # A category with no measured impact is not a user-specific gap even if
        # the catalog has no recommendation for it.
        if impact <= 0 and category not in normalized_contributors:
            status = CoverageStatus.NO_DATA
        severity = _gap_severity(
            status,
            share,
            completed_count=completed,
            rejected_count=rejected,
            config=config,
        )
        score = _coverage_score(relevant, completed, rejected, repetition_rate, share, config)
        reason = _category_reason(
            category,
            category_label(category),
            share,
            relevant,
            relevant,
            completed,
            rejected,
            repetition_rate,
            status,
        )
        rows.append(CategoryCoverage(
            category=category,
            label=category_label(category),
            impact=round(impact, 2),
            impact_share=round(share, 6),
            recommendation_count=relevant,
            relevant_count=relevant,
            completed_count=completed,
            rejected_count=rejected,
            unique_titles=unique_titles,
            repetition_rate=round(repetition_rate, 6),
            coverage_score=score,
            status=status,
            gap_severity=severity,
            reason=reason,
        ))
    return tuple(rows)


def calculate_coverage_score(rows: Sequence[CategoryCoverage]) -> float:
    """Compute an impact-weighted overall coverage score."""
    measured = [row for row in rows if row.impact > 0]
    if not measured:
        return 0.0
    total_weight = sum(row.impact for row in measured)
    if total_weight <= 0:
        return 0.0
    score = sum(row.coverage_score * row.impact for row in measured) / total_weight
    return round(max(0.0, min(1.0, score)), 6)


def _overall_status(score: float, gaps: Sequence[CoverageGap], rows: Sequence[CategoryCoverage]) -> CoverageStatus:
    if not rows or not any(row.impact > 0 for row in rows):
        return CoverageStatus.NO_DATA
    if any(gap.severity == GapSeverity.CRITICAL for gap in gaps):
        return CoverageStatus.GAP
    if score >= 0.75 and not any(gap.severity in {GapSeverity.HIGH, GapSeverity.CRITICAL} for gap in gaps):
        return CoverageStatus.COVERED
    if score >= 0.45:
        return CoverageStatus.PARTIAL
    return CoverageStatus.GAP


def build_coverage_report(
    contributors: Mapping[str, Any] | None,
    recommendations: Iterable[Any],
    *,
    feedback: Iterable[Any] | None = None,
    user_id: int | None = None,
    config: RecommendationCoverageConfig | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CoverageReport:
    """Build the complete recommendation coverage src.reporting.report."""
    config = config or RecommendationCoverageConfig()
    normalized = mark_history_status(normalize_recommendations(recommendations), feedback)
    rows = analyze_category_coverage(contributors, normalized, feedback=feedback, config=config)
    repeated = detect_repeated_recommendations(normalized, threshold=src.core.config.repeated_title_threshold)
    duplicates = duplicate_recommendation_ids(normalized)
    gaps = find_coverage_gaps(rows, repeated_recommendations=repeated)
    score = calculate_coverage_score(rows)
    status = _overall_status(score, gaps, rows)
    covered = sum(1 for row in rows if row.status == CoverageStatus.COVERED)
    high_uncovered = sum(
        1 for row in rows
        if row.impact_share >= src.core.config.high_impact_share and row.status in {CoverageStatus.GAP, CoverageStatus.PARTIAL}
    )
    diversity = calculate_recommendation_diversity(normalized)
    report_metadata = {
        "category_distribution": category_distribution(normalized),
        "normalized_category_count": len({item.category for item in normalized}),
        "high_impact_threshold": src.core.config.high_impact_share,
        "critical_impact_threshold": src.core.config.critical_impact_share,
        "engine": "recommendation_coverage_v1",
    }
    if metadata:
        report_metadata.update(dict(metadata))
    return CoverageReport(
        user_id=user_id,
        created_at=utcnow().isoformat(),
        overall_score=score,
        status=status,
        categories=rows,
        gaps=tuple(gaps),
        repeated_recommendations=tuple(repeated),
        duplicate_ids=tuple(duplicates),
        recommendation_count=len(normalized),
        category_count=len(rows),
        covered_category_count=covered,
        high_impact_uncovered_count=high_uncovered,
        recommendation_diversity=diversity,
        metadata=report_metadata,
    )


def summarize_coverage(report: CoverageReport) -> dict[str, Any]:
    """Return concise metrics suitable for cards and API responses."""
    severity_counts = Counter(gap.severity.value for gap in src.reporting.report.gaps)
    return {
        "overall_score": src.reporting.report.overall_score,
        "overall_percent": round(src.reporting.report.overall_score * 100, 1),
        "status": src.reporting.report.status.value,
        "recommendations": src.reporting.report.recommendation_count,
        "categories": src.reporting.report.category_count,
        "covered_categories": src.reporting.report.covered_category_count,
        "high_impact_uncovered": src.reporting.report.high_impact_uncovered_count,
        "diversity": src.reporting.report.recommendation_diversity,
        "gap_count": len(src.reporting.report.gaps),
        "severity_counts": dict(severity_counts),
        "top_gap": src.reporting.report.gaps[0].title if src.reporting.report.gaps else None,
    }


def serialize_coverage_report(report: CoverageReport, *, indent: int = 2) -> str:
    return src.reporting.report.to_json(indent=indent)


def coverage_table(report: CoverageReport) -> list[dict[str, Any]]:
    """Return flat rows for pandas/DataFrame consumers."""
    return [
        {
            "Category": row.label,
            "Impact (kg CO2e)": row.impact,
            "Impact share": row.impact_share,
            "Recommendations": row.recommendation_count,
            "Relevant": row.relevant_count,
            "Completed": row.completed_count,
            "Rejected": row.rejected_count,
            "Unique": row.unique_titles,
            "Repetition": row.repetition_rate,
            "Coverage": row.coverage_score,
            "Status": row.status.value,
            "Severity": row.gap_severity.value,
            "Reason": row.reason,
        }
        for row in src.reporting.report.categories
    ]


def gap_table(report: CoverageReport) -> list[dict[str, Any]]:
    return [
        {
            "Category": gap.label,
            "Severity": gap.severity.value,
            "Code": gap.code,
            "Gap": gap.title,
            "Reason": gap.reason,
            "Follow-up": gap.suggested_follow_up,
        }
        for gap in src.reporting.report.gaps
    ]


# ---------------------------------------------------------------------------
# SQLite persistence
# ---------------------------------------------------------------------------

class RecommendationCoverageStore:
    """SQLite store for immutable coverage report snapshots."""

    TABLE = "recommendation_coverage_reports"

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or DB_NAME
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                f"""CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    coverage_score REAL NOT NULL,
                    status TEXT NOT NULL,
                    report_payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                f"""CREATE INDEX IF NOT EXISTS idx_rec_coverage_user_time
                ON {self.TABLE}(user_id, created_at DESC)"""
            )

    def save(self, report: CoverageReport) -> int:
        payload = serialize_coverage_report(report)
        with self._connect() as connection:
            cursor = connection.execute(
                f"""INSERT INTO {self.TABLE}
                (user_id, coverage_score, status, report_payload, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (src.reporting.report.user_id, src.reporting.report.overall_score, src.reporting.report.status.value, payload, src.reporting.report.created_at),
            )
            return int(cursor.lastrowid)

    def list_reports(self, user_id: int, *, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT id, user_id, coverage_score, status, report_payload, created_at
                FROM {self.TABLE}
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest(self, user_id: int) -> dict[str, Any] | None:
        rows = self.list_reports(user_id, limit=1)
        return rows[0] if rows else None

    def delete_user_reports(self, user_id: int) -> int:
        with self._connect() as connection:
            cursor = connection.execute(f"DELETE FROM {self.TABLE} WHERE user_id = ?", (user_id,))
            return int(cursor.rowcount)


def persist_coverage_report(
    report: CoverageReport,
    *,
    store: RecommendationCoverageStore | None = None,
) -> int:
    return (store or RecommendationCoverageStore()).save(report)


def load_latest_coverage_report(
    user_id: int,
    *,
    store: RecommendationCoverageStore | None = None,
) -> dict[str, Any] | None:
    return (store or RecommendationCoverageStore()).latest(user_id)


# ---------------------------------------------------------------------------
# Convenience API for existing EcoBuddy recommendation output
# ---------------------------------------------------------------------------

def build_coverage_from_existing_recommendations(
    contributors: Mapping[str, Any] | None,
    recommendations: Iterable[Any],
    *,
    feedback: Iterable[Any] | None = None,
    user_id: int | None = None,
    config: RecommendationCoverageConfig | None = None,
) -> CoverageReport:
    """Named adapter used by application code and future API endpoints."""
    return build_coverage_report(
        contributors,
        recommendations,
        feedback=feedback,
        user_id=user_id,
        config=config,
        metadata={"source": "existing_recommendation_pipeline"},
    )


def category_coverage_index(report: CoverageReport) -> dict[str, CategoryCoverage]:
    return {row.category: row for row in src.reporting.report.categories}


def gap_codes(report: CoverageReport) -> set[str]:
    return {gap.code for gap in src.reporting.report.gaps}


def is_high_impact_gap(row: CategoryCoverage, *, threshold: float = 0.20) -> bool:
    return row.impact_share >= threshold and row.status in {CoverageStatus.GAP, CoverageStatus.PARTIAL}


def recommendation_matches_category(recommendation: Any, category: str) -> bool:
    normalized = normalize_recommendation(recommendation)
    return normalized.category == normalize_category(category)


def filter_recommendations_by_category(
    recommendations: Iterable[Any],
    category: str,
) -> list[RecommendationRecord]:
    target = normalize_category(category)
    return [item for item in normalize_recommendations(recommendations) if item.category == target]


def report_fingerprint(report: CoverageReport) -> str:
    """Stable fingerprint excluding the creation timestamp."""
    payload = src.reporting.report.to_dict()
    payload["created_at"] = ""
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


__all__ = [
    "CATEGORY_ALIASES",
    "CATEGORY_LABELS",
    "CoverageGap",
    "CoverageReport",
    "CoverageStatus",
    "CategoryCoverage",
    "GapSeverity",
    "RecommendationCoverageConfig",
    "RecommendationCoverageStore",
    "RecommendationRecord",
    "analyze_category_coverage",
    "build_coverage_from_existing_recommendations",
    "build_coverage_report",
    "calculate_coverage_score",
    "calculate_impact_shares",
    "calculate_recommendation_diversity",
    "category_coverage_index",
    "category_distribution",
    "coverage_table",
    "detect_repeated_recommendations",
    "duplicate_recommendation_ids",
    "filter_recommendations_by_category",
    "find_coverage_gaps",
    "gap_codes",
    "gap_table",
    "highest_impact_categories",
    "infer_recommendation_categories",
    "is_high_impact_gap",
    "load_latest_coverage_report",
    "mark_history_status",
    "normalize_category",
    "normalize_contributors",
    "normalize_recommendation",
    "normalize_recommendations",
    "persist_coverage_report",
    "recommendation_history",
    "recommendation_matches_category",
    "report_fingerprint",
    "serialize_coverage_report",
    "summarize_coverage",
]
