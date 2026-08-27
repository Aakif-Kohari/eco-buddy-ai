"""Sustainability goal progress and reduction pathway analysis.

This module is an additive analytics layer over EcoBuddy's existing ``goals``
and assessment systems.  It deliberately does not replace goal creation,
emission calculations, or historical assessment persistence.  Instead it turns
those existing records into a reusable, explainable pathway model.

The module is dependency-light and keeps Streamlit/database imports out of the
core calculation functions.  That makes the pathway calculations deterministic
and straightforward to test.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

STATUS_ACHIEVED = "ACHIEVED"
STATUS_AHEAD = "AHEAD"
STATUS_ON_TRACK = "ON_TRACK"
STATUS_AT_RISK = "AT_RISK"
STATUS_OFF_TRACK = "OFF_TRACK"
STATUS_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

VALID_STATUSES = (
    STATUS_ACHIEVED,
    STATUS_AHEAD,
    STATUS_ON_TRACK,
    STATUS_AT_RISK,
    STATUS_OFF_TRACK,
    STATUS_INSUFFICIENT_DATA,
)

DEFAULT_THRESHOLDS = {
    "ahead_ratio": -0.05,
    "on_track_ratio": 0.05,
    "at_risk_ratio": 0.20,
    "significant_change_pct": 5.0,
}

MILESTONE_PERCENTS = (10, 25, 50, 75, 90, 100)
DAYS_PER_MONTH = 365.25 / 12

CATEGORY_ALIASES = {
    "transport": "Transportation",
    "transportation": "Transportation",
    "electricity": "Electricity",
    "energy": "Electricity",
    "diet": "Diet",
    "food": "Diet",
    "flights": "Flights",
    "flight": "Flights",
    "water": "Water",
    "waste": "Waste",
    "shopping": "Shopping",
    "general": "General lifestyle",
    "general lifestyle": "General lifestyle",
}


class GoalPathwayValidationError(ValueError):
    """Raised when a pathway input is invalid."""


@dataclass(frozen=True)
class ProgressSnapshot:
    """A point-in-time view of goal progress."""

    date: date
    current_kg: float
    expected_kg: float
    variance_kg: float
    percent_complete: float
    remaining_kg: float
    status: str
    source_assessment_id: int | str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["date"] = self.date.isoformat()
        return data


@dataclass(frozen=True)
class ReductionMilestone:
    """A percentage reduction checkpoint on the pathway."""

    percent: float
    target_kg: float
    target_date: date
    completed: bool
    completed_date: date | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["target_date"] = self.target_date.isoformat()
        if self.completed_date:
            data["completed_date"] = self.completed_date.isoformat()
        return data


@dataclass(frozen=True)
class CategoryProgress:
    """Historical change for one emissions category."""

    category: str
    baseline_kg: float
    current_kg: float
    absolute_change_kg: float
    percentage_change: float | None
    direction: str
    data_available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PathwayProjection:
    """Projection of the current trend at the goal target date."""

    current_kg: float
    projected_final_kg: float
    target_kg: float
    projected_shortfall_kg: float
    projected_surplus_kg: float
    observed_pace_kg_per_month: float
    required_pace_kg_per_month: float
    pace_gap_kg_per_month: float
    projected_target_date: date | None
    months_to_target_at_current_pace: float | None
    feasible_at_current_pace: bool

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.projected_target_date:
            data["projected_target_date"] = self.projected_target_date.isoformat()
        return data


@dataclass(frozen=True)
class GoalStatus:
    """Explainable status classification."""

    code: str
    label: str
    explanation: str
    confidence: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class GoalPathway:
    """Complete analysis returned by :func:`analyze_goal_pathway`."""

    goal_id: int | str | None
    user_id: int | str | None
    baseline_kg: float
    target_kg: float
    start_date: date
    target_date: date
    analyzed_on: date
    progress: dict[str, Any]
    projection: PathwayProjection
    status: GoalStatus
    milestones: list[ReductionMilestone] = field(default_factory=list)
    snapshots: list[ProgressSnapshot] = field(default_factory=list)
    category_progress: list[CategoryProgress] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "user_id": self.user_id,
            "baseline_kg": self.baseline_kg,
            "target_kg": self.target_kg,
            "start_date": self.start_date.isoformat(),
            "target_date": self.target_date.isoformat(),
            "analyzed_on": self.analyzed_on.isoformat(),
            "progress": self.progress,
            "projection": self.projection.to_dict(),
            "status": self.status.to_dict(),
            "milestones": [item.to_dict() for item in self.milestones],
            "snapshots": [item.to_dict() for item in self.snapshots],
            "category_progress": [item.to_dict() for item in self.category_progress],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class PathwayConfig:
    """Configurable analysis rules."""

    ahead_ratio: float = DEFAULT_THRESHOLDS["ahead_ratio"]
    on_track_ratio: float = DEFAULT_THRESHOLDS["on_track_ratio"]
    at_risk_ratio: float = DEFAULT_THRESHOLDS["at_risk_ratio"]
    significant_change_pct: float = DEFAULT_THRESHOLDS["significant_change_pct"]
    milestone_percents: tuple[int, ...] = MILESTONE_PERCENTS


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return default if not math.isfinite(number) else number


def _date(value: Any, field_name: str = "date") -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip().replace(" ", "T")
        if not text:
            raise GoalPathwayValidationError(f"{field_name} must not be empty")
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            try:
                return datetime.strptime(text[:10], "%Y-%m-%d").date()
            except ValueError as exc:
                raise GoalPathwayValidationError(
                    f"{field_name} must be an ISO date"
                ) from exc
    raise GoalPathwayValidationError(f"{field_name} must be a date")


def _category_key(value: Any) -> str:
    text = " ".join(str(value).strip().lower().split())
    return CATEGORY_ALIASES.get(text, str(value).strip() or "Unknown")


def _goal_value(goal: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in goal and goal[key] is not None:
            return goal[key]
    raise GoalPathwayValidationError(f"Missing goal field: {keys[0]}")


def normalize_goal(goal: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize an existing EcoBuddy goal without mutating it."""
    baseline = _finite(_goal_value(goal, "baseline_kg", "baseline"), -1)
    target = _finite(_goal_value(goal, "target_kg", "target"), -1)
    start = _date(_goal_value(goal, "start_date", "start"), "start_date")
    end = _date(_goal_value(goal, "target_date", "end_date", "end"), "target_date")
    if baseline <= 0:
        raise GoalPathwayValidationError("baseline_kg must be greater than zero")
    if target < 0:
        raise GoalPathwayValidationError("target_kg cannot be negative")
    if target >= baseline:
        raise GoalPathwayValidationError("target_kg must be below baseline_kg")
    if end <= start:
        raise GoalPathwayValidationError("target_date must be after start_date")
    return {
        "id": goal.get("id"),
        "user_id": goal.get("user_id"),
        "baseline_kg": baseline,
        "target_kg": target,
        "start_date": start,
        "target_date": end,
        "status": goal.get("status", "active"),
    }


def normalize_assessments(assessments: Iterable[Any]) -> list[dict[str, Any]]:
    """Normalize dict or legacy tuple assessment rows."""
    result: list[dict[str, Any]] = []
    for row in assessments or []:
        if isinstance(row, Mapping):
            raw_date = row.get("date", row.get("created_at"))
            raw_footprint = row.get("footprint")
            assessment_id = row.get("id")
            categories = row.get("categories")
            if categories is None:
                categories = row.get("contributors")
        elif isinstance(row, (tuple, list)):
            if len(row) < 8:
                continue
            assessment_id = row[0]
            raw_date = row[1]
            raw_footprint = row[7]
            categories = None
        else:
            continue
        if raw_date is None or raw_footprint is None:
            continue
        try:
            record_date = _date(raw_date)
            footprint = _finite(raw_footprint, math.nan)
        except GoalPathwayValidationError:
            continue
        if not math.isfinite(footprint):
            continue
        result.append({
            "id": assessment_id,
            "date": record_date,
            "footprint": footprint,
            "categories": categories if isinstance(categories, Mapping) else None,
            "raw": row,
        })
    result.sort(key=lambda item: (item["date"], str(item.get("id", ""))))
    return result


def total_required_reduction(goal: Mapping[str, Any]) -> float:
    normalized = normalize_goal(goal)
    return normalized["baseline_kg"] - normalized["target_kg"]


def reduction_percent(goal: Mapping[str, Any]) -> float:
    normalized = normalize_goal(goal)
    return total_required_reduction(normalized) / normalized["baseline_kg"] * 100


def expected_footprint_at(goal: Mapping[str, Any], on_date: Any) -> float:
    """Return the ideal linear pathway value at ``on_date``."""
    normalized = normalize_goal(goal)
    when = _date(on_date, "on_date")
    start = normalized["start_date"]
    end = normalized["target_date"]
    if when <= start:
        return normalized["baseline_kg"]
    if when >= end:
        return normalized["target_kg"]
    fraction = (when - start).days / (end - start).days
    return normalized["baseline_kg"] - total_required_reduction(normalized) * fraction


def required_monthly_reduction(goal: Mapping[str, Any]) -> float:
    normalized = normalize_goal(goal)
    months = max((normalized["target_date"] - normalized["start_date"]).days / DAYS_PER_MONTH, 0.0)
    return total_required_reduction(normalized) / months if months else 0.0


def observed_reduction_pace(assessments: Iterable[Any]) -> float:
    """Estimate reduction pace using a least-squares footprint trend."""
    records = normalize_assessments(assessments)
    if len(records) < 2:
        return 0.0
    origin = records[0]["date"]
    xs = [(item["date"] - origin).days / DAYS_PER_MONTH for item in records]
    ys = [item["footprint"] for item in records]
    avg_x = mean(xs)
    avg_y = mean(ys)
    denominator = sum((x - avg_x) ** 2 for x in xs)
    if denominator <= 0:
        return 0.0
    slope = sum((x - avg_x) * (y - avg_y) for x, y in zip(xs, ys)) / denominator
    return -slope


def latest_assessment(assessments: Iterable[Any]) -> dict[str, Any] | None:
    records = normalize_assessments(assessments)
    return records[-1] if records else None


def current_footprint(goal: Mapping[str, Any], assessments: Iterable[Any]) -> tuple[float, bool]:
    latest = latest_assessment(assessments)
    if latest is None:
        return normalize_goal(goal)["baseline_kg"], False
    return latest["footprint"], True


def calculate_progress(goal: Mapping[str, Any], assessments: Iterable[Any], as_of: Any | None = None) -> dict[str, Any]:
    """Calculate progress metrics without changing the underlying goal."""
    normalized = normalize_goal(goal)
    records = normalize_assessments(assessments)
    when = _date(as_of or date.today(), "as_of")
    current, has_data = current_footprint(normalized, records)
    required = total_required_reduction(normalized)
    achieved = normalized["baseline_kg"] - current
    complete = max(0.0, min(100.0, achieved / required * 100.0)) if required else 100.0
    expected = expected_footprint_at(normalized, when)
    remaining = max(0.0, current - normalized["target_kg"])
    days_remaining = max(0, (normalized["target_date"] - when).days)
    months_remaining = max(0.0, days_remaining / DAYS_PER_MONTH)
    pace_needed = remaining / months_remaining if months_remaining else 0.0
    return {
        "as_of": when,
        "current_kg": round(current, 2),
        "baseline_kg": round(normalized["baseline_kg"], 2),
        "target_kg": round(normalized["target_kg"], 2),
        "required_kg": round(required, 2),
        "achieved_kg": round(achieved, 2),
        "remaining_kg": round(remaining, 2),
        "percent_complete": round(complete, 2),
        "expected_kg": round(expected, 2),
        "variance_kg": round(current - expected, 2),
        "days_remaining": days_remaining,
        "months_remaining": round(months_remaining, 2),
        "observed_pace_kg_per_month": round(observed_reduction_pace(records), 2),
        "required_pace_kg_per_month": round(required_monthly_reduction(normalized), 2),
        "pace_needed_from_now_kg_per_month": round(pace_needed, 2),
        "record_count": len(records),
        "has_data": has_data,
    }


def classify_goal_status(
    goal: Mapping[str, Any],
    progress: Mapping[str, Any],
    config: PathwayConfig | None = None,
) -> GoalStatus:
    """Classify status from pathway variance with transparent thresholds."""
    config = config or PathwayConfig()
    if not progress.get("has_data"):
        return GoalStatus(
            STATUS_INSUFFICIENT_DATA,
            "Insufficient data",
            "No assessment has been logged since this goal was created.",
            "low",
        )
    if progress["current_kg"] <= progress["target_kg"]:
        return GoalStatus(STATUS_ACHIEVED, "Goal achieved", "Current footprint is at or below the target.", "high")
    required = max(total_required_reduction(goal), 1e-9)
    ratio = progress["variance_kg"] / required
    if ratio <= src.core.config.ahead_ratio:
        return GoalStatus(STATUS_AHEAD, "Ahead of schedule", "Current footprint is below the ideal pathway.", "high")
    if ratio <= src.core.config.on_track_ratio:
        return GoalStatus(STATUS_ON_TRACK, "On track", "Current footprint is close to the ideal pathway.", "high")
    if ratio <= src.core.config.at_risk_ratio:
        return GoalStatus(STATUS_AT_RISK, "At risk", "Current footprint is above the ideal pathway and needs a faster reduction pace.", "high")
    return GoalStatus(STATUS_OFF_TRACK, "Off track", "Current footprint is substantially above the ideal pathway.", "high")


def project_final_footprint(goal: Mapping[str, Any], assessments: Iterable[Any], as_of: Any | None = None) -> float:
    normalized = normalize_goal(goal)
    when = _date(as_of or date.today(), "as_of")
    current, _ = current_footprint(normalized, assessments)
    remaining_months = max(0.0, (normalized["target_date"] - when).days / DAYS_PER_MONTH)
    if remaining_months <= 0:
        return current
    pace = observed_reduction_pace(assessments)
    return max(0.0, current - pace * remaining_months)


def project_target_date(goal: Mapping[str, Any], assessments: Iterable[Any], as_of: Any | None = None) -> date | None:
    """Estimate when the target is reached at the observed reduction pace."""
    normalized = normalize_goal(goal)
    when = _date(as_of or date.today(), "as_of")
    current, _ = current_footprint(normalized, assessments)
    pace = observed_reduction_pace(assessments)
    if current <= normalized["target_kg"]:
        return when
    if pace <= 0:
        return None
    months = (current - normalized["target_kg"]) / pace
    return when + timedelta(days=round(months * DAYS_PER_MONTH))


def build_projection(goal: Mapping[str, Any], assessments: Iterable[Any], as_of: Any | None = None) -> PathwayProjection:
    normalized = normalize_goal(goal)
    progress = calculate_progress(normalized, assessments, as_of)
    current = progress["current_kg"]
    target = normalized["target_kg"]
    projected = project_final_footprint(normalized, assessments, progress["as_of"])
    pace = progress["observed_pace_kg_per_month"]
    required = progress["pace_needed_from_now_kg_per_month"]
    target_date = project_target_date(normalized, assessments, progress["as_of"])
    months_to_target = None
    if pace > 0 and current > target:
        months_to_target = (current - target) / pace
    return PathwayProjection(
        current_kg=round(current, 2),
        projected_final_kg=round(projected, 2),
        target_kg=round(target, 2),
        projected_shortfall_kg=round(max(0.0, projected - target), 2),
        projected_surplus_kg=round(max(0.0, target - projected), 2),
        observed_pace_kg_per_month=round(pace, 2),
        required_pace_kg_per_month=round(required, 2),
        pace_gap_kg_per_month=round(pace - required, 2),
        projected_target_date=target_date,
        months_to_target_at_current_pace=round(months_to_target, 2) if months_to_target is not None else None,
        feasible_at_current_pace=projected <= target,
    )


def generate_pathway(goal: Mapping[str, Any], points: int | None = None) -> list[dict[str, Any]]:
    """Generate ideal pathway points with exact start/end anchors."""
    normalized = normalize_goal(goal)
    total_days = (normalized["target_date"] - normalized["start_date"]).days
    if points is None:
        points = max(2, round(total_days / 30) + 1)
    points = max(2, int(points))
    reduction = total_required_reduction(normalized)
    result = []
    for index in range(points):
        fraction = index / (points - 1)
        point_date = normalized["start_date"] + timedelta(days=round(total_days * fraction))
        result.append({
            "date": point_date,
            "target_kg": round(normalized["baseline_kg"] - reduction * fraction, 2),
            "fraction": round(fraction, 4),
        })
    result[0] = {"date": normalized["start_date"], "target_kg": normalized["baseline_kg"], "fraction": 0.0}
    result[-1] = {"date": normalized["target_date"], "target_kg": normalized["target_kg"], "fraction": 1.0}
    return result


def generate_milestones(
    goal: Mapping[str, Any],
    assessments: Iterable[Any] = (),
    as_of: Any | None = None,
    percentages: Sequence[int] | None = None,
) -> list[ReductionMilestone]:
    normalized = normalize_goal(goal)
    records = normalize_assessments(assessments)
    when = _date(as_of or date.today(), "as_of")
    percentages = percentages or MILESTONE_PERCENTS
    result: list[ReductionMilestone] = []
    total = total_required_reduction(normalized)
    for raw_percent in percentages:
        percent = int(raw_percent)
        if percent < 0 or percent > 100:
            raise GoalPathwayValidationError("milestone percentages must be between 0 and 100")
        target_value = normalized["baseline_kg"] - total * percent / 100
        target_day = normalized["start_date"] + timedelta(
            days=round((normalized["target_date"] - normalized["start_date"]).days * percent / 100)
        )
        completed_date = None
        for record in records:
            if record["footprint"] <= target_value and record["date"] >= normalized["start_date"]:
                completed_date = record["date"]
                break
        if completed_date is None and when >= target_day and not records:
            completed = False
        else:
            completed = completed_date is not None
        result.append(ReductionMilestone(percent, round(target_value, 2), target_day, completed, completed_date))
    return result


def _category_values(record: Mapping[str, Any]) -> dict[str, float]:
    categories = record.get("categories")
    if isinstance(categories, Mapping):
        result: dict[str, float] = {}
        for key, value in categories.items():
            numeric = _finite(value, math.nan)
            if math.isfinite(numeric):
                result[_category_key(key)] = max(0.0, numeric)
        return result
    raw = record.get("raw")
    # Legacy assessment tuples do not contain calculated category contributions;
    # returning an empty mapping is intentional rather than inventing a split.
    if isinstance(raw, Mapping) and isinstance(raw.get("category_contributions"), Mapping):
        return _category_values({"categories": raw["category_contributions"]})
    return {}


def calculate_category_progress(
    goal: Mapping[str, Any], assessments: Iterable[Any]
) -> list[CategoryProgress]:
    """Compare first and latest category contributions when available."""
    records = normalize_assessments(assessments)
    if not records:
        return []
    baseline_record = records[0]
    latest_record = records[-1]
    baseline_categories = _category_values(baseline_record)
    current_categories = _category_values(latest_record)
    categories = sorted(set(baseline_categories) | set(current_categories))
    result: list[CategoryProgress] = []
    for category in categories:
        before = baseline_categories.get(category)
        after = current_categories.get(category)
        if before is None or after is None:
            result.append(CategoryProgress(category, before or 0.0, after or 0.0, (after or 0.0) - (before or 0.0), None, "UNKNOWN", False))
            continue
        change = after - before
        percentage = (change / before * 100) if before else None
        direction = "IMPROVING" if change < 0 else "WORSENING" if change > 0 else "STABLE"
        result.append(CategoryProgress(category, round(before, 2), round(after, 2), round(change, 2), round(percentage, 2) if percentage is not None else None, direction))
    result.sort(key=lambda item: (abs(item.absolute_change_kg), item.category), reverse=True)
    return result


def build_snapshots(goal: Mapping[str, Any], assessments: Iterable[Any], config: PathwayConfig | None = None) -> list[ProgressSnapshot]:
    """Evaluate every usable assessment against the ideal pathway."""
    normalized = normalize_goal(goal)
    records = normalize_assessments(assessments)
    result = []
    for record in records:
        if record["date"] < normalized["start_date"]:
            continue
        progress = calculate_progress(normalized, [record], record["date"])
        status = classify_goal_status(normalized, progress, config).code
        result.append(ProgressSnapshot(
            record["date"], record["footprint"], expected_footprint_at(normalized, record["date"]),
            round(record["footprint"] - expected_footprint_at(normalized, record["date"]), 2),
            progress["percent_complete"], progress["remaining_kg"], status, record.get("id")
        ))
    return result


def detect_significant_progress_change(previous_kg: float, current_kg: float, threshold_pct: float = 5.0) -> dict[str, Any]:
    """Classify a footprint change using a transparent percentage threshold."""
    previous = _finite(previous_kg)
    current = _finite(current_kg)
    if previous <= 0:
        return {"significant": False, "direction": "UNKNOWN", "change_kg": round(current - previous, 2), "change_pct": None}
    change_pct = (current - previous) / previous * 100
    direction = "IMPROVEMENT" if change_pct < 0 else "REGRESSION" if change_pct > 0 else "STABLE"
    return {
        "significant": abs(change_pct) >= abs(threshold_pct),
        "direction": direction,
        "change_kg": round(current - previous, 2),
        "change_pct": round(change_pct, 2),
    }


def compare_periods(
    assessments: Iterable[Any],
    first_start: Any,
    first_end: Any,
    second_start: Any,
    second_end: Any,
) -> dict[str, Any]:
    """Compare average footprints in two explicit periods."""
    records = normalize_assessments(assessments)
    a_start, a_end = _date(first_start), _date(first_end)
    b_start, b_end = _date(second_start), _date(second_end)
    first = [r["footprint"] for r in records if a_start <= r["date"] <= a_end]
    second = [r["footprint"] for r in records if b_start <= r["date"] <= b_end]
    first_avg = mean(first) if first else None
    second_avg = mean(second) if second else None
    if first_avg is None or second_avg is None:
        return {"available": False, "first_count": len(first), "second_count": len(second), "first_average": first_avg, "second_average": second_avg}
    change = second_avg - first_avg
    return {
        "available": True,
        "first_count": len(first),
        "second_count": len(second),
        "first_average": round(first_avg, 2),
        "second_average": round(second_avg, 2),
        "change_kg": round(change, 2),
        "change_pct": round(change / first_avg * 100, 2) if first_avg else None,
        "direction": "IMPROVEMENT" if change < 0 else "REGRESSION" if change > 0 else "STABLE",
    }


def analyze_goal_pathway(
    goal: Mapping[str, Any],
    assessments: Iterable[Any],
    as_of: Any | None = None,
    config: PathwayConfig | None = None,
) -> GoalPathway:
    """Build the complete goal pathway analysis."""
    normalized = normalize_goal(goal)
    when = _date(as_of or date.today(), "as_of")
    config = config or PathwayConfig()
    records = normalize_assessments(assessments)
    progress = calculate_progress(normalized, records, when)
    status = classify_goal_status(normalized, progress, config)
    projection = build_projection(normalized, records, when)
    milestones = generate_milestones(normalized, records, when, src.core.config.milestone_percents)
    snapshots = build_snapshots(normalized, records, config)
    categories = calculate_category_progress(normalized, records)
    warnings: list[str] = []
    if not records:
        warnings.append("No usable assessment history is available for this goal.")
    if projection.projected_target_date is None and progress["current_kg"] > normalized["target_kg"]:
        warnings.append("Current reduction pace is not positive, so a target date cannot be projected.")
    if projection.projected_shortfall_kg > 0:
        warnings.append(
            f"At the observed pace, the projected footprint is {projection.projected_shortfall_kg:,.0f} kg above target."
        )
    if progress["target_kg"] < 0:
        warnings.append("Target footprint is below zero and should be reviewed.")
    return GoalPathway(
        normalized["id"], normalized["user_id"], normalized["baseline_kg"], normalized["target_kg"],
        normalized["start_date"], normalized["target_date"], when, progress, projection, status,
        milestones, snapshots, categories, warnings,
    )


def build_weekly_summary(analysis: GoalPathway) -> dict[str, Any]:
    """Build a concise summary suitable for dashboard cards."""
    p = analysis.progress
    return {
        "status": analysis.status.code,
        "status_label": analysis.status.label,
        "current_kg": p["current_kg"],
        "target_kg": p["target_kg"],
        "progress_percent": p["percent_complete"],
        "remaining_kg": p["remaining_kg"],
        "days_remaining": p["days_remaining"],
        "observed_pace_kg_per_month": p["observed_pace_kg_per_month"],
        "required_pace_kg_per_month": p["pace_needed_from_now_kg_per_month"],
        "projected_final_kg": analysis.projection.projected_final_kg,
        "next_milestone": next((m.to_dict() for m in analysis.milestones if not m.completed), None),
    }


def _json_safe(value: Any) -> Any:
    """Recursively convert dates and dataclass-adjacent values to JSON types."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def serialize_pathway(analysis: GoalPathway) -> str:
    """Serialize a pathway using only JSON-compatible values."""
    return json.dumps(_json_safe(analysis.to_dict()), sort_keys=True, separators=(",", ":"))


def deserialize_pathway(payload: str | Mapping[str, Any]) -> dict[str, Any]:
    """Deserialize a pathway payload for exports and persistence consumers."""
    data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    for key in ("start_date", "target_date", "analyzed_on"):
        if key in data:
            data[key] = _date(data[key], key).isoformat()
    return data


def pathway_id(goal: Mapping[str, Any], analysis: GoalPathway) -> str:
    """Return a stable identifier for the same goal/day analysis."""
    normalized = normalize_goal(goal)
    seed = "|".join([
        str(normalized.get("user_id")), str(normalized.get("id")),
        normalized["start_date"].isoformat(), normalized["target_date"].isoformat(),
        analysis.analyzed_on.isoformat(), f"{analysis.progress['current_kg']:.2f}",
    ])
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def rank_categories(category_progress: Iterable[CategoryProgress]) -> list[CategoryProgress]:
    """Rank categories by absolute footprint improvement/regression."""
    return sorted(category_progress, key=lambda item: (abs(item.absolute_change_kg), item.category), reverse=True)


def best_improvement(category_progress: Iterable[CategoryProgress]) -> CategoryProgress | None:
    improvements = [item for item in category_progress if item.absolute_change_kg < 0]
    return min(improvements, key=lambda item: item.absolute_change_kg) if improvements else None


def largest_regression(category_progress: Iterable[CategoryProgress]) -> CategoryProgress | None:
    regressions = [item for item in category_progress if item.absolute_change_kg > 0]
    return max(regressions, key=lambda item: item.absolute_change_kg) if regressions else None


def target_date_at_current_pace(goal: Mapping[str, Any], assessments: Iterable[Any], as_of: Any | None = None) -> dict[str, Any]:
    """Return a human-readable target-date projection."""
    normalized = normalize_goal(goal)
    when = _date(as_of or date.today(), "as_of")
    target = project_target_date(normalized, assessments, when)
    if target is None:
        return {"available": False, "projected_date": None, "days_delta": None, "months_delta": None}
    return {
        "available": True,
        "projected_date": target,
        "days_delta": (target - normalized["target_date"]).days,
        "months_delta": round((target - normalized["target_date"]).days / DAYS_PER_MONTH, 2),
    }


def validate_pathway_config(config: PathwayConfig) -> None:
    if not (src.core.config.ahead_ratio <= src.core.config.on_track_ratio <= src.core.config.at_risk_ratio):
        raise GoalPathwayValidationError("status thresholds must be ordered ahead <= on-track <= at-risk")
    if src.core.config.significant_change_pct < 0:
        raise GoalPathwayValidationError("significant_change_pct cannot be negative")
    if not src.core.config.milestone_percents:
        raise GoalPathwayValidationError("at least one milestone is required")
    if any(percent < 0 or percent > 100 for percent in src.core.config.milestone_percents):
        raise GoalPathwayValidationError("milestones must be between 0 and 100")


def build_chart_rows(analysis: GoalPathway) -> list[dict[str, Any]]:
    """Return chart-friendly pathway and observed values."""
    rows = []
    for point in generate_pathway({
        "id": analysis.goal_id,
        "user_id": analysis.user_id,
        "baseline_kg": analysis.baseline_kg,
        "target_kg": analysis.target_kg,
        "start_date": analysis.start_date,
        "target_date": analysis.target_date,
    }):
        rows.append({"date": point["date"], "ideal_kg": point["target_kg"], "actual_kg": None})
    by_date = {snapshot.date: snapshot.current_kg for snapshot in analysis.snapshots}
    for row in rows:
        if row["date"] in by_date:
            row["actual_kg"] = by_date[row["date"]]
    for snapshot in analysis.snapshots:
        if snapshot.date not in {row["date"] for row in rows}:
            rows.append({"date": snapshot.date, "ideal_kg": snapshot.expected_kg, "actual_kg": snapshot.current_kg})
    rows.sort(key=lambda item: item["date"])
    return rows


def human_status_message(analysis: GoalPathway) -> str:
    """Generate a concise status message without inventing causal claims."""
    p = analysis.progress
    if analysis.status.code == STATUS_ACHIEVED:
        return f"Goal achieved at {p['current_kg']:,.0f} kg CO2e/year."
    if analysis.status.code == STATUS_INSUFFICIENT_DATA:
        return f"Goal set at {p['target_kg']:,.0f} kg CO2e/year. Log an assessment to begin tracking."
    if analysis.status.code == STATUS_AHEAD:
        return f"Ahead of schedule by {abs(p['variance_kg']):,.0f} kg versus the ideal pathway."
    if analysis.status.code == STATUS_ON_TRACK:
        return f"On track; {p['remaining_kg']:,.0f} kg remains to reach the target."
    if analysis.status.code == STATUS_AT_RISK:
        return f"At risk; {p['pace_needed_from_now_kg_per_month']:,.0f} kg/month is needed from now."
    return f"Off track; current pace projects {analysis.projection.projected_shortfall_kg:,.0f} kg above target."


__all__ = [
    "CategoryProgress", "GoalPathway", "GoalPathwayValidationError", "GoalStatus",
    "PathwayConfig", "PathwayProjection", "ProgressSnapshot", "ReductionMilestone",
    "STATUS_ACHIEVED", "STATUS_AHEAD", "STATUS_ON_TRACK", "STATUS_AT_RISK",
    "STATUS_OFF_TRACK", "STATUS_INSUFFICIENT_DATA", "analyze_goal_pathway",
    "build_chart_rows", "build_projection", "build_snapshots", "build_weekly_summary",
    "calculate_category_progress", "calculate_progress", "classify_goal_status",
    "compare_periods", "current_footprint", "deserialize_pathway", "detect_significant_progress_change",
    "expected_footprint_at", "generate_milestones", "generate_pathway", "human_status_message",
    "largest_regression", "latest_assessment", "normalize_assessments", "normalize_goal",
    "observed_reduction_pace", "pathway_id", "project_final_footprint", "project_target_date",
    "rank_categories", "reduction_percent", "required_monthly_reduction", "serialize_pathway",
    "target_date_at_current_pace", "total_required_reduction", "validate_pathway_config",
]
