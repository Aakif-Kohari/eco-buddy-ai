"""Sustainability intervention outcome tracking and effectiveness analysis.

This module is intentionally additive: it records intervention outcomes without
changing historical assessments and provides deterministic, explainable metrics
for evaluating whether an adopted sustainability action is associated with a
measurable change.

The engine does not claim causal certainty.  It distinguishes:
* measured change: arithmetic difference between baseline and observation data
* normalized change: change relative to the baseline
* target attainment: progress toward an optional target
* effectiveness: a bounded score based on target attainment and evidence quality
* attribution confidence: how strongly the available evidence supports the
  intervention as an explanation for the observed change

All persisted snapshots contain the inputs used for the calculation so an old
analysis can be inspected without silently recalculating it with new rules.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import statistics
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ENGINE_VERSION = "1.0.0"
DEFAULT_DB_PATH = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")
SUPPORTED_METRICS = frozenset(
    {
        "carbon",
        "electricity",
        "transport",
        "distance",
        "water",
        "waste",
        "food",
        "flights",
        "eco_score",
        "custom",
    }
)
REDUCTION_IS_BETTER = frozenset(
    {"carbon", "electricity", "transport", "distance", "water", "waste", "food", "flights"}
)
INCREASE_IS_BETTER = frozenset({"eco_score"})


class InterventionStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"


class OutcomeDirection(str, Enum):
    IMPROVED = "improved"
    WORSENED = "worsened"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"


class EvidenceLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ValidationError(ValueError):
    """Raised when intervention or outcome data is unsafe to analyze."""


def _finite(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _date(value: Any, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValidationError(f"{field_name} is required")
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(raw[:10])
            except ValueError as exc:
                raise ValidationError(
                    f"{field_name} must be an ISO-8601 date"
                ) from exc
    raise ValidationError(f"{field_name} must be an ISO-8601 date")


def _iso(value: date | datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _date(value, "date").isoformat()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(_text(item) for item in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def normalize_metric(metric: Any) -> str:
    value = _text(metric).lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "co2": "carbon",
        "co2e": "carbon",
        "carbon_footprint": "carbon",
        "energy": "electricity",
        "power": "electricity",
        "travel": "transport",
        "mileage": "distance",
        "water_use": "water",
        "waste_generation": "waste",
        "diet": "food",
        "flight": "flights",
        "score": "eco_score",
    }
    normalized = aliases.get(value, value)
    return normalized if normalized in SUPPORTED_METRICS else "custom"


def normalize_status(value: Any) -> InterventionStatus:
    if isinstance(value, InterventionStatus):
        return value
    raw = _text(value, InterventionStatus.PLANNED.value).lower()
    try:
        return InterventionStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            f"Unsupported intervention status: {raw}"
        ) from exc


@dataclass(frozen=True)
class Intervention:
    """A sustainability action adopted by a user."""

    id: str
    user_id: int | str | None
    action_id: str
    name: str
    category: str
    adopted_on: date
    baseline_start: date
    baseline_end: date
    observation_start: date
    observation_end: date
    metric: str
    baseline_value: float
    target_value: float | None = None
    unit: str = "units"
    status: InterventionStatus = InterventionStatus.ACTIVE
    description: str = ""
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        for key in (
            "adopted_on",
            "baseline_start",
            "baseline_end",
            "observation_start",
            "observation_end",
        ):
            data[key] = data[key].isoformat()
        return _json_safe(data)


@dataclass(frozen=True)
class OutcomeObservation:
    """A measured observation within an intervention period."""

    id: str
    intervention_id: str
    observed_on: date
    value: float
    unit: str
    source: str = "manual"
    quality: float = 1.0
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["observed_on"] = self.observed_on.isoformat()
        return _json_safe(data)


@dataclass(frozen=True)
class EffectivenessAnalysis:
    """Immutable calculation snapshot for an intervention."""

    intervention_id: str
    analyzed_at: datetime
    engine_version: str
    baseline_value: float
    observation_value: float | None
    target_value: float | None
    absolute_change: float | None
    percentage_change: float | None
    improvement_pct: float | None
    target_attainment_pct: float | None
    direction: OutcomeDirection
    evidence_level: EvidenceLevel
    evidence_score: float
    attribution_confidence: float
    effectiveness_score: float
    observation_count: int
    baseline_observation_count: int
    measurement_consistency: float
    trend_slope: float | None
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    inputs_fingerprint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["analyzed_at"] = self.analyzed_at.isoformat()
        data["direction"] = self.direction.value
        data["evidence_level"] = self.evidence_level.value
        data["warnings"] = list(self.warnings)
        data["limitations"] = list(self.limitations)
        data["recommendations"] = list(self.recommendations)
        return _json_safe(data)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


@dataclass(frozen=True)
class InterventionComparison:
    """Comparison between two intervention analyses."""

    intervention_id: str
    previous_effectiveness: float | None
    current_effectiveness: float | None
    effectiveness_change: float | None
    previous_improvement_pct: float | None
    current_improvement_pct: float | None
    improvement_change: float | None
    evidence_change: float | None
    direction_changed: bool
    summary: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["warnings"] = list(self.warnings)
        return _json_safe(data)


@dataclass(frozen=True)
class InterventionSummary:
    """Aggregate user-level intervention effectiveness summary."""

    intervention_count: int
    analyzed_count: int
    completed_count: int
    active_count: int
    improved_count: int
    worsened_count: int
    unchanged_count: int
    average_effectiveness: float
    average_attribution_confidence: float
    high_confidence_count: int
    total_observations: int
    category_effectiveness: dict[str, float]
    recommendations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def validate_intervention(intervention: Intervention) -> None:
    if not intervention.id.strip():
        raise ValidationError("intervention id is required")
    if not intervention.name.strip():
        raise ValidationError("intervention name is required")
    if not intervention.action_id.strip():
        raise ValidationError("action_id is required")
    if not intervention.category.strip():
        raise ValidationError("category is required")
    if intervention.metric not in SUPPORTED_METRICS:
        raise ValidationError(f"unsupported metric: {intervention.metric}")
    if not math.isfinite(intervention.baseline_value):
        raise ValidationError("baseline_value must be finite")
    if intervention.baseline_value < 0:
        raise ValidationError("baseline_value cannot be negative")
    if intervention.target_value is not None and not math.isfinite(intervention.target_value):
        raise ValidationError("target_value must be finite")
    if intervention.baseline_end < intervention.baseline_start:
        raise ValidationError("baseline_end must not precede baseline_start")
    if intervention.observation_end < intervention.observation_start:
        raise ValidationError("observation_end must not precede observation_start")
    if intervention.observation_start < intervention.adopted_on:
        raise ValidationError("observation_start cannot precede adoption")
    if intervention.baseline_end >= intervention.observation_start:
        raise ValidationError("baseline and observation periods must not overlap")


def create_intervention(
    *,
    name: str,
    category: str,
    adopted_on: Any,
    baseline_start: Any,
    baseline_end: Any,
    observation_start: Any,
    observation_end: Any,
    metric: Any,
    baseline_value: Any,
    action_id: str | None = None,
    user_id: int | str | None = None,
    target_value: Any = None,
    unit: str = "units",
    status: Any = InterventionStatus.ACTIVE,
    description: str = "",
    notes: str = "",
    intervention_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Intervention:
    adopted = _date(adopted_on, "adopted_on")
    base_start = _date(baseline_start, "baseline_start")
    base_end = _date(baseline_end, "baseline_end")
    obs_start = _date(observation_start, "observation_start")
    obs_end = _date(observation_end, "observation_end")
    base = _finite(baseline_value)
    if base is None:
        raise ValidationError("baseline_value must be numeric")
    target = _finite(target_value) if target_value is not None else None
    aid = _text(action_id) or _stable_id("action", name, category)
    iid = _text(intervention_id) or _stable_id(
        "int", aid, user_id, adopted, base_start, base_end
    )
    item = Intervention(
        id=iid,
        user_id=user_id,
        action_id=aid,
        name=_text(name),
        category=_text(category, "General lifestyle"),
        adopted_on=adopted,
        baseline_start=base_start,
        baseline_end=base_end,
        observation_start=obs_start,
        observation_end=obs_end,
        metric=normalize_metric(metric),
        baseline_value=base,
        target_value=target,
        unit=_text(unit, "units"),
        status=normalize_status(status),
        description=_text(description),
        notes=_text(notes),
        metadata=dict(metadata or {}),
    )
    validate_intervention(item)
    return item


def create_observation(
    intervention: Intervention,
    *,
    observed_on: Any,
    value: Any,
    unit: str | None = None,
    source: str = "manual",
    quality: Any = 1.0,
    notes: str = "",
    observation_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> OutcomeObservation:
    observed = _date(observed_on, "observed_on")
    numeric = _finite(value)
    if numeric is None:
        raise ValidationError("observation value must be numeric")
    if numeric < 0:
        raise ValidationError("observation value cannot be negative")
    quality_value = _finite(quality, 1.0)
    assert quality_value is not None
    quality_value = _clamp(quality_value)
    if observed < intervention.observation_start or observed > intervention.observation_end:
        raise ValidationError("observation date is outside the observation period")
    oid = _text(observation_id) or _stable_id(
        "obs", intervention.id, observed.isoformat(), numeric, source
    )
    return OutcomeObservation(
        id=oid,
        intervention_id=intervention.id,
        observed_on=observed,
        value=numeric,
        unit=_text(unit, intervention.unit),
        source=_text(source, "manual"),
        quality=quality_value,
        notes=_text(notes),
        metadata=dict(metadata or {}),
    )


def _mean(values: Sequence[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _median(values: Sequence[float]) -> float | None:
    return statistics.median(values) if values else None


def _linear_slope(observations: Sequence[OutcomeObservation]) -> float | None:
    if len(observations) < 2:
        return None
    origin = observations[0].observed_on
    xs = [(item.observed_on - origin).days for item in observations]
    ys = [item.value for item in observations]
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator <= 0:
        return None
    return sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator


def calculate_absolute_change(baseline: float, observed: float | None) -> float | None:
    if observed is None:
        return None
    return observed - baseline


def calculate_percentage_change(baseline: float, observed: float | None) -> float | None:
    if observed is None:
        return None
    if baseline == 0:
        return 0.0 if observed == 0 else None
    return (observed - baseline) / abs(baseline) * 100.0


def calculate_improvement_pct(
    metric: str,
    baseline: float,
    observed: float | None,
) -> float | None:
    if observed is None:
        return None
    if baseline == 0:
        return 100.0 if observed == 0 else 0.0
    if metric in INCREASE_IS_BETTER:
        return (observed - baseline) / abs(baseline) * 100.0
    return (baseline - observed) / abs(baseline) * 100.0


def determine_direction(
    metric: str,
    baseline: float,
    observed: float | None,
    tolerance_pct: float = 1.0,
) -> OutcomeDirection:
    improvement = calculate_improvement_pct(metric, baseline, observed)
    if improvement is None:
        return OutcomeDirection.UNKNOWN
    if improvement > tolerance_pct:
        return OutcomeDirection.IMPROVED
    if improvement < -tolerance_pct:
        return OutcomeDirection.WORSENED
    return OutcomeDirection.UNCHANGED


def calculate_target_attainment(
    metric: str,
    baseline: float,
    target: float | None,
    observed: float | None,
) -> float | None:
    if target is None or observed is None:
        return None
    if baseline == target:
        return 100.0 if observed == target else 0.0
    if metric in INCREASE_IS_BETTER:
        denominator = target - baseline
        progress = (observed - baseline) / denominator
    else:
        denominator = baseline - target
        progress = (baseline - observed) / denominator
    return _clamp(progress, 0.0, 1.0) * 100.0


def calculate_measurement_consistency(observations: Sequence[OutcomeObservation]) -> float:
    if not observations:
        return 0.0
    if len(observations) == 1:
        return observations[0].quality
    qualities = [item.quality for item in observations]
    mean_quality = statistics.fmean(qualities)
    values = [item.value for item in observations]
    mean_value = statistics.fmean(values)
    if mean_value == 0:
        variability = 0.0
    else:
        variability = min(1.0, statistics.pstdev(values) / abs(mean_value))
    return _clamp(mean_quality * (1.0 - 0.5 * variability))


def calculate_evidence_score(
    observations: Sequence[OutcomeObservation],
    *,
    has_baseline: bool = True,
    has_control: bool = False,
    has_repeated_measurements: bool | None = None,
) -> float:
    count = len(observations)
    repeated = count >= 3 if has_repeated_measurements is None else has_repeated_measurements
    score = 0.0
    if has_baseline:
        score += 0.25
    if count >= 1:
        score += 0.20
    if repeated:
        score += 0.20
    if has_control:
        score += 0.20
    if count >= 5:
        score += 0.05
    quality = statistics.fmean([o.quality for o in observations]) if observations else 0.0
    score += 0.10 * quality
    return _clamp(score)


def evidence_level(score: float) -> EvidenceLevel:
    if score >= 0.80:
        return EvidenceLevel.HIGH
    if score >= 0.55:
        return EvidenceLevel.MODERATE
    if score >= 0.25:
        return EvidenceLevel.LOW
    return EvidenceLevel.NONE


def calculate_attribution_confidence(
    evidence_score: float,
    *,
    has_control: bool = False,
    confounder_count: int = 0,
    observation_months: float = 0.0,
) -> float:
    confidence = _clamp(evidence_score)
    if has_control:
        confidence += 0.15
    if observation_months >= 3:
        confidence += 0.05
    confidence -= min(0.30, max(0, confounder_count) * 0.05)
    return _clamp(confidence)


def calculate_effectiveness_score(
    direction: OutcomeDirection,
    improvement_pct: float | None,
    target_attainment_pct: float | None,
    evidence_score: float,
    attribution_confidence: float,
) -> float:
    if improvement_pct is None:
        outcome_score = 0.0
    else:
        outcome_score = _clamp(improvement_pct / 100.0)
    if target_attainment_pct is not None:
        outcome_score = 0.6 * outcome_score + 0.4 * (target_attainment_pct / 100.0)
    evidence_multiplier = 0.45 + 0.55 * _clamp(evidence_score)
    attribution_multiplier = 0.50 + 0.50 * _clamp(attribution_confidence)
    if direction == OutcomeDirection.WORSENED:
        outcome_score = min(0.0, outcome_score)
    return round(_clamp(outcome_score) * evidence_multiplier * attribution_multiplier * 100.0, 2)


def summarize_observations(
    observations: Iterable[OutcomeObservation],
) -> dict[str, Any]:
    items = sorted(observations, key=lambda item: (item.observed_on, item.id))
    values = [item.value for item in items]
    return {
        "count": len(items),
        "mean": _mean(values),
        "median": _median(values),
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
        "first": values[0] if values else None,
        "last": values[-1] if values else None,
        "slope": _linear_slope(items),
        "quality_mean": statistics.fmean([item.quality for item in items]) if items else 0.0,
    }


def _period_months(start: date, end: date) -> float:
    return max(0.0, (end - start).days / 30.4375)


def analyze_intervention(
    intervention: Intervention,
    observations: Iterable[OutcomeObservation] = (),
    *,
    baseline_measurements: Sequence[float] | None = None,
    has_control: bool = False,
    confounders: Sequence[str] | None = None,
    analyzed_at: datetime | None = None,
) -> EffectivenessAnalysis:
    validate_intervention(intervention)
    items = sorted(
        [item for item in observations if item.intervention_id == intervention.id],
        key=lambda item: (item.observed_on, item.id),
    )
    baseline_values = [
        value for value in (baseline_measurements or []) if math.isfinite(float(value))
    ]
    baseline = _mean(baseline_values) if baseline_values else intervention.baseline_value
    observed = _mean([item.value for item in items])
    absolute = calculate_absolute_change(baseline, observed)
    percentage = calculate_percentage_change(baseline, observed)
    improvement = calculate_improvement_pct(intervention.metric, baseline, observed)
    target_attainment = calculate_target_attainment(
        intervention.metric, baseline, intervention.target_value, observed
    )
    direction = determine_direction(intervention.metric, baseline, observed)
    evidence = calculate_evidence_score(
        items,
        has_baseline=baseline is not None,
        has_control=has_control,
    )
    confounder_list = [str(x).strip() for x in (confounders or []) if str(x).strip()]
    months = _period_months(intervention.observation_start, intervention.observation_end)
    attribution = calculate_attribution_confidence(
        evidence,
        has_control=has_control,
        confounder_count=len(confounder_list),
        observation_months=months,
    )
    effectiveness = calculate_effectiveness_score(
        direction, improvement, target_attainment, evidence, attribution
    )
    consistency = calculate_measurement_consistency(items)
    warnings: list[str] = []
    limitations: list[str] = []
    recommendations: list[str] = []
    if not items:
        warnings.append("No outcome observations were recorded.")
    if len(items) < 3:
        limitations.append("Fewer than three observations limit trend reliability.")
    if not has_control:
        limitations.append("No control or comparison period was supplied; attribution is observational.")
    if confounder_list:
        limitations.append(
            "Potential confounders were reported: " + ", ".join(confounder_list)
        )
    if observed is None:
        recommendations.append("Record at least one observation during the observation period.")
    elif direction == OutcomeDirection.IMPROVED:
        recommendations.append("Continue the intervention and collect repeated measurements.")
    elif direction == OutcomeDirection.WORSENED:
        recommendations.append("Review implementation quality and possible confounding changes.")
    else:
        recommendations.append("Collect more observations before deciding whether the intervention is effective.")
    if target_attainment is not None and target_attainment < 100:
        recommendations.append("Compare the observed pace with the remaining target gap.")
    if evidence < 0.55 or len(items) < 3:
        recommendations.append(
            "Improve evidence quality with repeated measurements or a comparison period."
        )
    fingerprint_payload = {
        "intervention": intervention.to_dict(),
        "observations": [item.to_dict() for item in items],
        "baseline_measurements": baseline_values,
        "has_control": has_control,
        "confounders": confounder_list,
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return EffectivenessAnalysis(
        intervention_id=intervention.id,
        analyzed_at=analyzed_at or datetime.now(timezone.utc),
        engine_version=ENGINE_VERSION,
        baseline_value=float(baseline),
        observation_value=observed,
        target_value=intervention.target_value,
        absolute_change=absolute,
        percentage_change=percentage,
        improvement_pct=improvement,
        target_attainment_pct=target_attainment,
        direction=direction,
        evidence_level=evidence_level(evidence),
        evidence_score=round(evidence, 4),
        attribution_confidence=round(attribution, 4),
        effectiveness_score=effectiveness,
        observation_count=len(items),
        baseline_observation_count=len(baseline_values),
        measurement_consistency=round(consistency, 4),
        trend_slope=_linear_slope(items),
        warnings=tuple(warnings),
        limitations=tuple(limitations),
        recommendations=tuple(recommendations),
        inputs_fingerprint=fingerprint,
        metadata={
            "has_control": has_control,
            "confounders": confounder_list,
            "observation_summary": summarize_observations(items),
        },
    )


def compare_analyses(
    previous: EffectivenessAnalysis,
    current: EffectivenessAnalysis,
) -> InterventionComparison:
    if previous.intervention_id != current.intervention_id:
        raise ValidationError("analyses must belong to the same intervention")
    eff_change = current.effectiveness_score - previous.effectiveness_score
    imp_change = None
    if previous.improvement_pct is not None and current.improvement_pct is not None:
        imp_change = current.improvement_pct - previous.improvement_pct
    evidence_change = current.evidence_score - previous.evidence_score
    direction_changed = previous.direction != current.direction
    if direction_changed:
        summary = (
            f"Outcome direction changed from {previous.direction.value} "
            f"to {current.direction.value}."
        )
    elif eff_change > 2:
        summary = "Effectiveness evidence improved."
    elif eff_change < -2:
        summary = "Effectiveness evidence declined."
    else:
        summary = "Effectiveness is broadly stable."
    warnings: list[str] = []
    if current.evidence_score < previous.evidence_score:
        warnings.append("The newer analysis has weaker evidence quality.")
    if current.attribution_confidence < previous.attribution_confidence:
        warnings.append("The newer analysis has lower attribution confidence.")
    return InterventionComparison(
        intervention_id=current.intervention_id,
        previous_effectiveness=previous.effectiveness_score,
        current_effectiveness=current.effectiveness_score,
        effectiveness_change=round(eff_change, 2),
        previous_improvement_pct=previous.improvement_pct,
        current_improvement_pct=current.improvement_pct,
        improvement_change=None if imp_change is None else round(imp_change, 2),
        evidence_change=round(evidence_change, 4),
        direction_changed=direction_changed,
        summary=summary,
        warnings=tuple(warnings),
    )


def build_summary(
    interventions: Iterable[Intervention],
    analyses: Iterable[EffectivenessAnalysis],
) -> InterventionSummary:
    items = list(interventions)
    analysis_list = list(analyses)
    by_id = {item.intervention_id: item for item in analysis_list}
    improved = sum(a.direction == OutcomeDirection.IMPROVED for a in analysis_list)
    worsened = sum(a.direction == OutcomeDirection.WORSENED for a in analysis_list)
    unchanged = sum(a.direction == OutcomeDirection.UNCHANGED for a in analysis_list)
    category_values: dict[str, list[float]] = {}
    for intervention in items:
        analysis = by_id.get(intervention.id)
        if analysis:
            category_values.setdefault(intervention.category, []).append(
                analysis.effectiveness_score
            )
    category_effectiveness = {
        key: round(statistics.fmean(values), 2)
        for key, values in sorted(category_values.items())
    }
    avg_eff = statistics.fmean([a.effectiveness_score for a in analysis_list]) if analysis_list else 0.0
    avg_conf = (
        statistics.fmean([a.attribution_confidence for a in analysis_list])
        if analysis_list
        else 0.0
    )
    recommendations: list[str] = []
    if not analysis_list:
        recommendations.append("Analyze at least one intervention outcome.")
    if worsened:
        recommendations.append("Review interventions with worsening outcomes.")
    if improved and not worsened:
        recommendations.append("Continue collecting evidence for interventions showing improvement.")
    if any(a.evidence_score < 0.55 for a in analysis_list):
        recommendations.append("Strengthen evidence with repeated measurements or comparison periods.")
    return InterventionSummary(
        intervention_count=len(items),
        analyzed_count=len(analysis_list),
        completed_count=sum(
            item.status == InterventionStatus.COMPLETED for item in items
        ),
        active_count=sum(item.status == InterventionStatus.ACTIVE for item in items),
        improved_count=improved,
        worsened_count=worsened,
        unchanged_count=unchanged,
        average_effectiveness=round(avg_eff, 2),
        average_attribution_confidence=round(avg_conf, 4),
        high_confidence_count=sum(
            a.evidence_level == EvidenceLevel.HIGH for a in analysis_list
        ),
        total_observations=sum(a.observation_count for a in analysis_list),
        category_effectiveness=category_effectiveness,
        recommendations=tuple(recommendations),
    )


def serialize_intervention_bundle(
    intervention: Intervention,
    observations: Iterable[OutcomeObservation],
    analysis: EffectivenessAnalysis | None = None,
) -> str:
    payload = {
        "schema_version": "1.0",
        "engine_version": ENGINE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "intervention": intervention.to_dict(),
        "observations": [item.to_dict() for item in observations],
        "analysis": analysis.to_dict() if analysis else None,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def validate_bundle(payload: Mapping[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if payload.get("schema_version") != "1.0":
        errors.append("Unsupported or missing schema_version.")
    if not isinstance(payload.get("intervention"), Mapping):
        errors.append("intervention object is required.")
    observations = payload.get("observations", [])
    if not isinstance(observations, list):
        errors.append("observations must be a list.")
    if payload.get("analysis") is not None and not isinstance(payload.get("analysis"), Mapping):
        errors.append("analysis must be an object or null.")
    return not errors, errors


class InterventionStore:
    """SQLite persistence for interventions, observations, and analysis snapshots."""

    TABLE_INTERVENTIONS = "sustainability_interventions"
    TABLE_OBSERVATIONS = "sustainability_intervention_observations"
    TABLE_ANALYSES = "sustainability_intervention_analyses"

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self._initialized = False

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        if self._initialized:
            return
        with self._connect() as conn:
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {self.TABLE_INTERVENTIONS} (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    action_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    adopted_on TEXT NOT NULL,
                    baseline_start TEXT NOT NULL,
                    baseline_end TEXT NOT NULL,
                    observation_start TEXT NOT NULL,
                    observation_end TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    baseline_value REAL NOT NULL,
                    target_value REAL,
                    unit TEXT NOT NULL,
                    status TEXT NOT NULL,
                    description TEXT,
                    notes TEXT,
                    metadata_json TEXT NOT NULL
                )"""
            )
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {self.TABLE_OBSERVATIONS} (
                    id TEXT PRIMARY KEY,
                    intervention_id TEXT NOT NULL,
                    observed_on TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    source TEXT NOT NULL,
                    quality REAL NOT NULL,
                    notes TEXT,
                    metadata_json TEXT NOT NULL,
                    FOREIGN KEY(intervention_id)
                        REFERENCES {self.TABLE_INTERVENTIONS}(id)
                        ON DELETE CASCADE
                )"""
            )
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {self.TABLE_ANALYSES} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intervention_id TEXT NOT NULL,
                    analyzed_at TEXT NOT NULL,
                    engine_version TEXT NOT NULL,
                    effectiveness_score REAL NOT NULL,
                    evidence_score REAL NOT NULL,
                    attribution_confidence REAL NOT NULL,
                    direction TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    inputs_fingerprint TEXT NOT NULL,
                    FOREIGN KEY(intervention_id)
                        REFERENCES {self.TABLE_INTERVENTIONS}(id)
                        ON DELETE CASCADE
                )"""
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE_INTERVENTIONS}_user "
                f"ON {self.TABLE_INTERVENTIONS}(user_id)"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE_OBSERVATIONS}_intervention "
                f"ON {self.TABLE_OBSERVATIONS}(intervention_id)"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE_ANALYSES}_intervention "
                f"ON {self.TABLE_ANALYSES}(intervention_id)"
            )
        self._initialized = True

    def save_intervention(self, intervention: Intervention) -> None:
        validate_intervention(intervention)
        self.initialize()
        with self._connect() as conn:
            conn.execute(
                f"""INSERT INTO {self.TABLE_INTERVENTIONS} (
                    id,user_id,action_id,name,category,adopted_on,baseline_start,
                    baseline_end,observation_start,observation_end,metric,
                    baseline_value,target_value,unit,status,description,notes,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    user_id=excluded.user_id,
                    action_id=excluded.action_id,
                    name=excluded.name,
                    category=excluded.category,
                    adopted_on=excluded.adopted_on,
                    baseline_start=excluded.baseline_start,
                    baseline_end=excluded.baseline_end,
                    observation_start=excluded.observation_start,
                    observation_end=excluded.observation_end,
                    metric=excluded.metric,
                    baseline_value=excluded.baseline_value,
                    target_value=excluded.target_value,
                    unit=excluded.unit,
                    status=excluded.status,
                    description=excluded.description,
                    notes=excluded.notes,
                    metadata_json=excluded.metadata_json""",
                (
                    intervention.id,
                    None if intervention.user_id is None else str(intervention.user_id),
                    intervention.action_id,
                    intervention.name,
                    intervention.category,
                    intervention.adopted_on.isoformat(),
                    intervention.baseline_start.isoformat(),
                    intervention.baseline_end.isoformat(),
                    intervention.observation_start.isoformat(),
                    intervention.observation_end.isoformat(),
                    intervention.metric,
                    intervention.baseline_value,
                    intervention.target_value,
                    intervention.unit,
                    intervention.status.value,
                    intervention.description,
                    intervention.notes,
                    json.dumps(_json_safe(intervention.metadata), sort_keys=True),
                ),
            )

    def save_observation(self, observation: OutcomeObservation) -> None:
        self.initialize()
        with self._connect() as conn:
            exists = conn.execute(
                f"SELECT 1 FROM {self.TABLE_INTERVENTIONS} WHERE id=?",
                (observation.intervention_id,),
            ).fetchone()
            if exists is None:
                raise ValidationError("intervention does not exist")
            conn.execute(
                f"""INSERT INTO {self.TABLE_OBSERVATIONS} (
                    id,intervention_id,observed_on,value,unit,source,quality,notes,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    observed_on=excluded.observed_on,
                    value=excluded.value,
                    unit=excluded.unit,
                    source=excluded.source,
                    quality=excluded.quality,
                    notes=excluded.notes,
                    metadata_json=excluded.metadata_json""",
                (
                    observation.id,
                    observation.intervention_id,
                    observation.observed_on.isoformat(),
                    observation.value,
                    observation.unit,
                    observation.source,
                    observation.quality,
                    observation.notes,
                    json.dumps(_json_safe(observation.metadata), sort_keys=True),
                ),
            )

    def save_analysis(self, analysis: EffectivenessAnalysis) -> int:
        self.initialize()
        with self._connect() as conn:
            cursor = conn.execute(
                f"""INSERT INTO {self.TABLE_ANALYSES} (
                    intervention_id,analyzed_at,engine_version,effectiveness_score,
                    evidence_score,attribution_confidence,direction,payload_json,
                    inputs_fingerprint
                ) VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    analysis.intervention_id,
                    analysis.analyzed_at.isoformat(),
                    analysis.engine_version,
                    analysis.effectiveness_score,
                    analysis.evidence_score,
                    analysis.attribution_confidence,
                    analysis.direction.value,
                    analysis.to_json(),
                    analysis.inputs_fingerprint,
                ),
            )
            return int(cursor.lastrowid)

    @staticmethod
    def _intervention_from_row(row: sqlite3.Row) -> Intervention:
        return create_intervention(
            intervention_id=row["id"],
            user_id=row["user_id"],
            action_id=row["action_id"],
            name=row["name"],
            category=row["category"],
            adopted_on=row["adopted_on"],
            baseline_start=row["baseline_start"],
            baseline_end=row["baseline_end"],
            observation_start=row["observation_start"],
            observation_end=row["observation_end"],
            metric=row["metric"],
            baseline_value=row["baseline_value"],
            target_value=row["target_value"],
            unit=row["unit"],
            status=row["status"],
            description=row["description"],
            notes=row["notes"],
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    @staticmethod
    def _observation_from_row(row: sqlite3.Row) -> OutcomeObservation:
        return OutcomeObservation(
            id=row["id"],
            intervention_id=row["intervention_id"],
            observed_on=_date(row["observed_on"], "observed_on"),
            value=float(row["value"]),
            unit=row["unit"],
            source=row["source"],
            quality=float(row["quality"]),
            notes=row["notes"] or "",
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    def get_intervention(self, intervention_id: str) -> Intervention | None:
        self.initialize()
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {self.TABLE_INTERVENTIONS} WHERE id=?",
                (intervention_id,),
            ).fetchone()
        return self._intervention_from_row(row) if row else None

    def list_interventions(self, user_id: int | str | None = None) -> list[Intervention]:
        self.initialize()
        with self._connect() as conn:
            if user_id is None:
                rows = conn.execute(
                    f"SELECT * FROM {self.TABLE_INTERVENTIONS} ORDER BY adopted_on DESC, id"
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT * FROM {self.TABLE_INTERVENTIONS} WHERE user_id=? "
                    f"ORDER BY adopted_on DESC, id",
                    (str(user_id),),
                ).fetchall()
        return [self._intervention_from_row(row) for row in rows]

    def list_observations(self, intervention_id: str) -> list[OutcomeObservation]:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {self.TABLE_OBSERVATIONS} "
                f"WHERE intervention_id=? ORDER BY observed_on, id",
                (intervention_id,),
            ).fetchall()
        return [self._observation_from_row(row) for row in rows]

    def list_analyses(self, intervention_id: str) -> list[EffectivenessAnalysis]:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT payload_json FROM {self.TABLE_ANALYSES} "
                f"WHERE intervention_id=? ORDER BY analyzed_at, id",
                (intervention_id,),
            ).fetchall()
        return [analysis_from_dict(json.loads(row["payload_json"])) for row in rows]

    def latest_analysis(self, intervention_id: str) -> EffectivenessAnalysis | None:
        items = self.list_analyses(intervention_id)
        return items[-1] if items else None

    def delete_intervention(self, intervention_id: str, user_id: int | str | None = None) -> bool:
        self.initialize()
        with self._connect() as conn:
            if user_id is None:
                cursor = conn.execute(
                    f"DELETE FROM {self.TABLE_INTERVENTIONS} WHERE id=?",
                    (intervention_id,),
                )
            else:
                cursor = conn.execute(
                    f"DELETE FROM {self.TABLE_INTERVENTIONS} WHERE id=? AND user_id=?",
                    (intervention_id, str(user_id)),
                )
            return cursor.rowcount > 0

    def save_bundle(
        self,
        intervention: Intervention,
        observations: Sequence[OutcomeObservation],
        analysis: EffectivenessAnalysis | None = None,
    ) -> None:
        """Persist a complete intervention in one transaction."""
        validate_intervention(intervention)
        for item in observations:
            if item.intervention_id != intervention.id:
                raise ValidationError("observation belongs to a different intervention")
            if item.observed_on < intervention.observation_start or item.observed_on > intervention.observation_end:
                raise ValidationError("observation is outside intervention period")
        self.initialize()
        with self._connect() as conn:
            try:
                conn.execute("BEGIN")
                conn.execute(
                    f"""INSERT INTO {self.TABLE_INTERVENTIONS} (
                        id,user_id,action_id,name,category,adopted_on,baseline_start,
                        baseline_end,observation_start,observation_end,metric,
                        baseline_value,target_value,unit,status,description,notes,metadata_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        user_id=excluded.user_id,name=excluded.name,category=excluded.category,
                        adopted_on=excluded.adopted_on,baseline_start=excluded.baseline_start,
                        baseline_end=excluded.baseline_end,observation_start=excluded.observation_start,
                        observation_end=excluded.observation_end,metric=excluded.metric,
                        baseline_value=excluded.baseline_value,target_value=excluded.target_value,
                        unit=excluded.unit,status=excluded.status,description=excluded.description,
                        notes=excluded.notes,metadata_json=excluded.metadata_json""",
                    (
                        intervention.id,
                        None if intervention.user_id is None else str(intervention.user_id),
                        intervention.action_id,
                        intervention.name,
                        intervention.category,
                        intervention.adopted_on.isoformat(),
                        intervention.baseline_start.isoformat(),
                        intervention.baseline_end.isoformat(),
                        intervention.observation_start.isoformat(),
                        intervention.observation_end.isoformat(),
                        intervention.metric,
                        intervention.baseline_value,
                        intervention.target_value,
                        intervention.unit,
                        intervention.status.value,
                        intervention.description,
                        intervention.notes,
                        json.dumps(_json_safe(intervention.metadata), sort_keys=True),
                    ),
                )
                for item in observations:
                    conn.execute(
                        f"""INSERT INTO {self.TABLE_OBSERVATIONS} (
                            id,intervention_id,observed_on,value,unit,source,quality,notes,metadata_json
                        ) VALUES (?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(id) DO UPDATE SET
                            observed_on=excluded.observed_on,value=excluded.value,
                            unit=excluded.unit,source=excluded.source,quality=excluded.quality,
                            notes=excluded.notes,metadata_json=excluded.metadata_json""",
                        (
                            item.id, item.intervention_id, item.observed_on.isoformat(),
                            item.value, item.unit, item.source, item.quality, item.notes,
                            json.dumps(_json_safe(item.metadata), sort_keys=True),
                        ),
                    )
                if analysis is not None:
                    conn.execute(
                        f"""INSERT INTO {self.TABLE_ANALYSES} (
                            intervention_id,analyzed_at,engine_version,effectiveness_score,
                            evidence_score,attribution_confidence,direction,payload_json,
                            inputs_fingerprint
                        ) VALUES (?,?,?,?,?,?,?,?,?)""",
                        (
                            analysis.intervention_id,
                            analysis.analyzed_at.isoformat(),
                            analysis.engine_version,
                            analysis.effectiveness_score,
                            analysis.evidence_score,
                            analysis.attribution_confidence,
                            analysis.direction.value,
                            analysis.to_json(),
                            analysis.inputs_fingerprint,
                        ),
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise


def analysis_from_dict(payload: Mapping[str, Any]) -> EffectivenessAnalysis:
    def tup(name: str) -> tuple[str, ...]:
        value = payload.get(name, ())
        return tuple(str(item) for item in value) if isinstance(value, (list, tuple)) else ()

    return EffectivenessAnalysis(
        intervention_id=_text(payload.get("intervention_id")),
        analyzed_at=datetime.fromisoformat(_text(payload.get("analyzed_at")).replace("Z", "+00:00")),
        engine_version=_text(payload.get("engine_version"), ENGINE_VERSION),
        baseline_value=float(payload.get("baseline_value", 0)),
        observation_value=_finite(payload.get("observation_value")),
        target_value=_finite(payload.get("target_value")),
        absolute_change=_finite(payload.get("absolute_change")),
        percentage_change=_finite(payload.get("percentage_change")),
        improvement_pct=_finite(payload.get("improvement_pct")),
        target_attainment_pct=_finite(payload.get("target_attainment_pct")),
        direction=OutcomeDirection(_text(payload.get("direction"), "unknown")),
        evidence_level=EvidenceLevel(_text(payload.get("evidence_level"), "none")),
        evidence_score=float(payload.get("evidence_score", 0)),
        attribution_confidence=float(payload.get("attribution_confidence", 0)),
        effectiveness_score=float(payload.get("effectiveness_score", 0)),
        observation_count=int(payload.get("observation_count", 0)),
        baseline_observation_count=int(payload.get("baseline_observation_count", 0)),
        measurement_consistency=float(payload.get("measurement_consistency", 0)),
        trend_slope=_finite(payload.get("trend_slope")),
        warnings=tup("warnings"),
        limitations=tup("limitations"),
        recommendations=tup("recommendations"),
        inputs_fingerprint=_text(payload.get("inputs_fingerprint")),
        metadata=dict(payload.get("metadata") or {}),
    )


def list_effectiveness_actions(
    interventions: Iterable[Intervention],
    analyses: Iterable[EffectivenessAnalysis],
) -> list[dict[str, Any]]:
    """Return deterministic, UI-friendly rows sorted by effectiveness."""
    by_id = {analysis.intervention_id: analysis for analysis in analyses}
    rows: list[dict[str, Any]] = []
    for intervention in interventions:
        analysis = by_id.get(intervention.id)
        rows.append(
            {
                "Intervention": intervention.name,
                "Category": intervention.category,
                "Status": intervention.status.value,
                "Metric": intervention.metric,
                "Effectiveness": analysis.effectiveness_score if analysis else None,
                "Improvement %": analysis.improvement_pct if analysis else None,
                "Evidence": analysis.evidence_level.value if analysis else "not analyzed",
                "Attribution confidence": (
                    round(analysis.attribution_confidence * 100, 1) if analysis else None
                ),
                "Observations": analysis.observation_count if analysis else 0,
                "Direction": analysis.direction.value if analysis else "unknown",
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -(row["Effectiveness"] if row["Effectiveness"] is not None else -1),
            row["Intervention"].lower(),
        ),
    )


def export_summary_csv(
    interventions: Iterable[Intervention],
    analyses: Iterable[EffectivenessAnalysis],
) -> str:
    import csv
    import io

    rows = list_effectiveness_actions(interventions, analyses)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()) if rows else [
        "Intervention", "Category", "Status", "Metric", "Effectiveness",
        "Improvement %", "Evidence", "Attribution confidence", "Observations", "Direction"
    ])
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


__all__ = [
    "ENGINE_VERSION",
    "SUPPORTED_METRICS",
    "DEFAULT_DB_PATH",
    "InterventionStatus",
    "OutcomeDirection",
    "EvidenceLevel",
    "ValidationError",
    "Intervention",
    "OutcomeObservation",
    "EffectivenessAnalysis",
    "InterventionComparison",
    "InterventionSummary",
    "InterventionStore",
    "create_intervention",
    "create_observation",
    "validate_intervention",
    "analyze_intervention",
    "compare_analyses",
    "build_summary",
    "calculate_absolute_change",
    "calculate_percentage_change",
    "calculate_improvement_pct",
    "determine_direction",
    "calculate_target_attainment",
    "calculate_measurement_consistency",
    "calculate_evidence_score",
    "calculate_attribution_confidence",
    "calculate_effectiveness_score",
    "summarize_observations",
    "serialize_intervention_bundle",
    "validate_bundle",
    "analysis_from_dict",
    "list_effectiveness_actions",
    "export_summary_csv",
]
