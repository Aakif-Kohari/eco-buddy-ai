"""Explainability and audit snapshots for EcoBuddy sustainability assessments.

This module is deliberately read-only with respect to the assessment src.core.database.
It reconstructs calculations from the immutable factor-set registry when the
assessment has a known factor version and refuses to invent historical factors
when that metadata is unavailable.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from src.carbon.emission_factors import (
    DEFAULT_VERSION,
    UnknownFactorSetError,
    get_factor_set,
    has_factor_set,
)

ENGINE_VERSION = "1.0"
SOURCE_UNAVAILABLE = "Source unavailable"
METHODOLOGY_CHANGED = "Calculation methodology changed since this assessment."


@dataclass(frozen=True)
class FactorReference:
    value: float | None
    unit: str
    source: str = SOURCE_UNAVAILABLE
    version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UnitConversionStep:
    name: str
    input_value: float
    input_unit: str
    normalized_value: float
    normalized_unit: str
    multiplier: float
    calculation: str


@dataclass(frozen=True)
class CalculationStep:
    category: str
    input_name: str
    input_value: float | str | None
    input_unit: str
    normalized_value: float | None
    normalized_unit: str
    factor: float | None
    factor_unit: str
    calculation: str
    result: float | None
    result_unit: str
    source: str = SOURCE_UNAVAILABLE
    factor_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CalculationTrace:
    assessment_id: int | str | None
    assessment_date: str | None
    factor_version: str | None
    methodology_available: bool
    steps: tuple[CalculationStep, ...] = ()
    conversions: tuple[UnitConversionStep, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def total_result(self) -> float:
        return round(sum(step.result or 0.0 for step in self.steps), 2)


@dataclass(frozen=True)
class CategoryContribution:
    category: str
    result: float
    percentage: float
    rank: int
    input_values: dict[str, Any]
    factor: float | None
    factor_unit: str
    source: str
    factor_version: str | None


@dataclass(frozen=True)
class AssessmentAudit:
    assessment_id: int | str | None
    user_id: int | str | None
    assessment_date: str | None
    created_at: str | None
    stored_footprint: float | None
    stored_eco_score: int | None
    factor_version: str | None
    factor_metadata: dict[str, Any]
    methodology_available: bool
    methodology_changed: bool
    inputs: dict[str, Any]
    trace: CalculationTrace
    contributions: tuple[CategoryContribution, ...]
    generated_at: str
    notes: tuple[str, ...] = ()


def _number(value: Any, name: str, *, minimum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return number


def _assessment_value(assessment: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in assessment:
            return assessment[name]
    return default


def normalize_assessment(assessment: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a database assessment mapping."""
    if not isinstance(assessment, Mapping):
        raise ValueError("assessment must be a mapping")

    transport = _assessment_value(assessment, "transport")
    diet = _assessment_value(assessment, "diet")
    if not isinstance(transport, str) or not transport.strip():
        raise ValueError("assessment.transport is required")
    if not isinstance(diet, str) or not diet.strip():
        raise ValueError("assessment.diet is required")

    return {
        "id": _assessment_value(assessment, "id", "assessment_id"),
        "user_id": _assessment_value(assessment, "user_id"),
        "date": _assessment_value(assessment, "date", "assessment_date"),
        "created_at": _assessment_value(assessment, "created_at"),
        "transport": transport.strip(),
        "distance": _number(_assessment_value(assessment, "distance"), "distance", minimum=0),
        "electricity": _number(_assessment_value(assessment, "electricity"), "electricity", minimum=0),
        "diet": diet.strip(),
        "flights": int(_number(_assessment_value(assessment, "flights"), "flights", minimum=0)),
        "footprint": _number(_assessment_value(assessment, "footprint"), "footprint")
        if _assessment_value(assessment, "footprint") is not None else None,
        "eco_score": int(_number(_assessment_value(assessment, "eco_score"), "eco_score"))
        if _assessment_value(assessment, "eco_score") is not None else None,
        "factor_version": _assessment_value(assessment, "factor_version") or DEFAULT_VERSION,
    }


def trace_input(assessment: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Return one normalized input descriptor without performing a calculation."""
    data = normalize_assessment(assessment)
    descriptors = {
        "transport": (data["transport"], "mode"),
        "distance": (data["distance"], "km/day"),
        "electricity": (data["electricity"], "kWh/month"),
        "diet": (data["diet"], "diet profile"),
        "flights": (data["flights"], "flights/year"),
    }
    if name not in descriptors:
        raise ValueError(f"unknown assessment input '{name}'")
    value, unit = descriptors[name]
    return {"name": name, "value": value, "unit": unit}


def trace_conversion(name: str, input_value: float, input_unit: str,
                     normalized_value: float, normalized_unit: str,
                     multiplier: float) -> UnitConversionStep:
    return UnitConversionStep(
        name=name,
        input_value=float(input_value),
        input_unit=input_unit,
        normalized_value=float(normalized_value),
        normalized_unit=normalized_unit,
        multiplier=float(multiplier),
        calculation=f"{input_value} {input_unit} × {multiplier} = {normalized_value} {normalized_unit}",
    )


def trace_factor(factor: float | None, unit: str, *, source: str = SOURCE_UNAVAILABLE,
                 version: str | None = None, metadata: dict[str, Any] | None = None) -> FactorReference:
    return FactorReference(
        value=None if factor is None else float(factor),
        unit=unit,
        source=source or SOURCE_UNAVAILABLE,
        version=version,
        metadata=dict(metadata or {}),
    )


def _source_text(factor_set: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    source = factor_set.get("source") or {}
    if not isinstance(source, Mapping):
        return SOURCE_UNAVAILABLE, {}
    name = source.get("name") or source.get("publisher")
    return str(name) if name else SOURCE_UNAVAILABLE, dict(source)


def _factor_value(factor_set: Mapping[str, Any], group: str, key: str | None = None) -> float:
    factors = factor_set["factors"][group]
    value = factors if key is None else factors.get(key)
    if value is None:
        raise KeyError(f"factor '{group}{'.' + key if key else ''}' is unavailable")
    return float(value)


def calculate_contribution(normalized_value: float, factor: float, multiplier: float = 1.0) -> float:
    """Calculate a contribution using explicit normalized input × factor × multiplier."""
    result = float(normalized_value) * float(factor) * float(multiplier)
    if not math.isfinite(result):
        raise ValueError("calculation result is not finite")
    return result


def _build_steps(data: Mapping[str, Any], factor_set: Mapping[str, Any]) -> tuple[list[CalculationStep], list[UnitConversionStep]]:
    version = factor_set["version"]
    source, source_meta = _source_text(factor_set)
    factors = factor_set["factors"]
    steps: list[CalculationStep] = []
    conversions: list[UnitConversionStep] = []

    distance_year = data["distance"] * 365.0
    conversions.append(trace_conversion("daily distance to annual distance", data["distance"], "km/day", distance_year, "km/year", 365.0))
    transport_factor = _factor_value(factor_set, "transport", data["transport"])
    transport_result = calculate_contribution(distance_year, transport_factor)
    steps.append(CalculationStep(
        category="Transportation", input_name="Car/transport distance", input_value=data["distance"],
        input_unit="km/day", normalized_value=distance_year, normalized_unit="km/year",
        factor=transport_factor, factor_unit="kg CO2e/km", calculation=f"{distance_year:g} × {transport_factor:g}",
        result=transport_result, result_unit="kg CO2e/year", source=source, factor_version=version,
        metadata={"transport_mode": data["transport"], "source_metadata": source_meta},
    ))

    electricity_year = data["electricity"] * 12.0
    conversions.append(trace_conversion("monthly electricity to annual electricity", data["electricity"], "kWh/month", electricity_year, "kWh/year", 12.0))
    electricity_factor = _factor_value(factor_set, "electricity")
    electricity_result = calculate_contribution(electricity_year, electricity_factor)
    steps.append(CalculationStep(
        category="Energy", input_name="Electricity", input_value=data["electricity"], input_unit="kWh/month",
        normalized_value=electricity_year, normalized_unit="kWh/year", factor=electricity_factor,
        factor_unit="kg CO2e/kWh", calculation=f"{electricity_year:g} × {electricity_factor:g}",
        result=electricity_result, result_unit="kg CO2e/year", source=source, factor_version=version,
        metadata={"source_metadata": source_meta},
    ))

    diet_factor = _factor_value(factor_set, "diet", data["diet"])
    steps.append(CalculationStep(
        category="Food", input_name="Diet profile", input_value=data["diet"], input_unit="profile",
        normalized_value=1.0, normalized_unit="year", factor=diet_factor,
        factor_unit="kg CO2e/year", calculation=f"annual diet factor = {diet_factor:g}", result=diet_factor,
        result_unit="kg CO2e/year", source=source, factor_version=version,
        metadata={"diet": data["diet"], "source_metadata": source_meta},
    ))

    flight_factor = _factor_value(factor_set, "flight")
    flight_result = calculate_contribution(data["flights"], flight_factor)
    steps.append(CalculationStep(
        category="Flights", input_name="Annual flights", input_value=data["flights"], input_unit="flights/year",
        normalized_value=float(data["flights"]), normalized_unit="flights/year", factor=flight_factor,
        factor_unit="kg CO2e/flight", calculation=f"{data['flights']} × {flight_factor:g}", result=flight_result,
        result_unit="kg CO2e/year", source=source, factor_version=version,
        metadata={"source_metadata": source_meta},
    ))
    return steps, conversions


def build_calculation_trace(assessment: Mapping[str, Any], *, allow_unavailable: bool = True) -> CalculationTrace:
    """Build a reproducible trace using the assessment's recorded factor version."""
    data = normalize_assessment(assessment)
    version = data["factor_version"]
    notes: list[str] = []
    try:
        factor_set = get_factor_set(version)
    except (UnknownFactorSetError, KeyError):
        if not allow_unavailable:
            raise
        notes.append(f"Factor set '{version}' is unavailable; historical calculations cannot be reconstructed safely.")
        notes.append(SOURCE_UNAVAILABLE)
        return CalculationTrace(
            assessment_id=data["id"], assessment_date=str(data["date"]) if data["date"] is not None else None,
            factor_version=version, methodology_available=False, notes=tuple(notes),
        )

    steps, conversions = _build_steps(data, factor_set)
    stored = data.get("footprint")
    calculated = sum(step.result or 0.0 for step in steps)
    if stored is not None and abs(calculated - stored) > 0.05:
        notes.append(f"Reconstructed total ({calculated:.2f} kg CO2e) differs from stored result ({stored:.2f} kg CO2e).")
        notes.append("The stored result is preserved; the trace is not silently substituted for it.")
    return CalculationTrace(
        assessment_id=data["id"], assessment_date=str(data["date"]) if data["date"] is not None else None,
        factor_version=version, methodology_available=True, steps=tuple(steps), conversions=tuple(conversions), notes=tuple(notes),
    )


def trace_category(trace: CalculationTrace, category: str) -> tuple[CalculationStep, ...]:
    return tuple(step for step in trace.steps if step.category.lower() == category.lower())


def _percentages(steps: Sequence[CalculationStep]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for step in steps:
        totals[step.category] = totals.get(step.category, 0.0) + float(step.result or 0.0)
    denominator = sum(totals.values())
    if denominator == 0:
        return {category: 0.0 for category in totals}
    return {category: (value / denominator) * 100.0 for category, value in totals.items()}


def aggregate_category_contributions(trace: CalculationTrace) -> tuple[CategoryContribution, ...]:
    totals: dict[str, float] = {}
    first_step: dict[str, CalculationStep] = {}
    for step in trace.steps:
        totals[step.category] = totals.get(step.category, 0.0) + float(step.result or 0.0)
        first_step.setdefault(step.category, step)
    percentages = _percentages(trace.steps)
    ordered = sorted(totals.items(), key=lambda item: (-abs(item[1]), item[0]))
    ranks = {category: index + 1 for index, (category, _) in enumerate(ordered)}
    result: list[CategoryContribution] = []
    for category, value in totals.items():
        step = first_step[category]
        result.append(CategoryContribution(
            category=category, result=round(value, 2), percentage=round(percentages.get(category, 0.0), 2),
            rank=ranks[category], input_values={"name": step.input_name, "value": step.input_value, "unit": step.input_unit},
            factor=step.factor, factor_unit=step.factor_unit, source=step.source or SOURCE_UNAVAILABLE,
            factor_version=step.factor_version,
        ))
    return tuple(sorted(result, key=lambda item: item.rank))


def _factor_metadata(version: str | None) -> dict[str, Any]:
    if not version or not has_factor_set(version):
        return {"version": version, "available": False, "source": SOURCE_UNAVAILABLE}
    factor_set = get_factor_set(version)
    source, metadata = _source_text(factor_set)
    return {
        "version": version, "available": True, "kind": factor_set.get("kind"),
        "effective_date": factor_set.get("effective_date"), "region": factor_set.get("region"),
        "fingerprint": factor_set.get("fingerprint"), "source": source, "source_metadata": metadata,
        "notes": factor_set.get("notes", ""),
    }


def build_assessment_audit(assessment: Mapping[str, Any], *, current_factor_version: str | None = None) -> AssessmentAudit:
    data = normalize_assessment(assessment)
    trace = build_calculation_trace(data)
    current_version = current_factor_version
    methodology_changed = bool(current_version and data["factor_version"] != current_version)
    notes = list(trace.notes)
    if methodology_changed:
        notes.append(METHODOLOGY_CHANGED)
    return AssessmentAudit(
        assessment_id=data["id"], user_id=data["user_id"], assessment_date=str(data["date"]) if data["date"] is not None else None,
        created_at=str(data["created_at"]) if data["created_at"] is not None else None,
        stored_footprint=data["footprint"], stored_eco_score=data["eco_score"], factor_version=data["factor_version"],
        factor_metadata=_factor_metadata(data["factor_version"]), methodology_available=trace.methodology_available,
        methodology_changed=methodology_changed, inputs={
            "transport": data["transport"], "distance": data["distance"], "electricity": data["electricity"],
            "diet": data["diet"], "flights": data["flights"],
        }, trace=trace, contributions=aggregate_category_contributions(trace),
        generated_at=datetime.now(timezone.utc).isoformat(), notes=tuple(notes),
    )


def _step_map(audit: AssessmentAudit) -> dict[str, CalculationStep]:
    return {step.category: step for step in audit.trace.steps}


def compare_audit_traces(previous: AssessmentAudit | CalculationTrace, current: AssessmentAudit | CalculationTrace) -> dict[str, Any]:
    """Compare two traces and classify input, factor, unit and methodology changes."""
    prev_trace = previous.trace if isinstance(previous, AssessmentAudit) else previous
    curr_trace = current.trace if isinstance(current, AssessmentAudit) else current
    prev_steps = {step.category: step for step in prev_trace.steps}
    curr_steps = {step.category: step for step in curr_trace.steps}
    categories = sorted(set(prev_steps) | set(curr_steps))
    rows: list[dict[str, Any]] = []
    input_changes = 0
    factor_changes = 0
    unit_changes = 0
    methodology_changes = prev_trace.factor_version != curr_trace.factor_version
    for category in categories:
        old = prev_steps.get(category)
        new = curr_steps.get(category)
        if old is None or new is None:
            rows.append({"category": category, "previous": old.result if old else None, "current": new.result if new else None,
                         "change": (new.result if new else 0) - (old.result if old else 0), "input_changed": True,
                         "factor_changed": True, "unit_changed": True, "methodology_changed": methodology_changes})
            input_changes += 1
            continue
        input_changed = old.input_value != new.input_value or old.normalized_value != new.normalized_value
        factor_changed = old.factor != new.factor or old.factor_unit != new.factor_unit
        unit_changed = old.input_unit != new.input_unit or old.normalized_unit != new.normalized_unit
        input_changes += int(input_changed)
        factor_changes += int(factor_changed)
        unit_changes += int(unit_changed)
        rows.append({"category": category, "previous": round(old.result or 0.0, 2), "current": round(new.result or 0.0, 2),
                     "change": round((new.result or 0.0) - (old.result or 0.0), 2),
                     "input_changed": input_changed, "factor_changed": factor_changed,
                     "unit_changed": unit_changed, "methodology_changed": methodology_changes})
    return {
        "previous_factor_version": prev_trace.factor_version, "current_factor_version": curr_trace.factor_version,
        "methodology_changed": methodology_changes, "input_changes": input_changes,
        "factor_changes": factor_changes, "unit_changes": unit_changes, "categories": rows,
        "previous_total": round(prev_trace.total_result, 2), "current_total": round(curr_trace.total_result, 2),
        "total_change": round(curr_trace.total_result - prev_trace.total_result, 2),
    }


def serialize_audit(audit: AssessmentAudit, *, indent: int = 2) -> str:
    """Serialize an audit snapshot to stable, human-readable JSON."""
    return json.dumps(asdict(audit), indent=indent, sort_keys=True, default=str)


def audit_from_json(payload: str | Mapping[str, Any]) -> AssessmentAudit:
    """Deserialize a previously exported audit snapshot."""
    raw = json.loads(payload) if isinstance(payload, str) else dict(payload)
    trace_raw = raw.get("trace") or {}
    steps = tuple(CalculationStep(**step) for step in trace_raw.get("steps", []))
    conversions = tuple(UnitConversionStep(**step) for step in trace_raw.get("conversions", []))
    trace = CalculationTrace(
        assessment_id=trace_raw.get("assessment_id"), assessment_date=trace_raw.get("assessment_date"),
        factor_version=trace_raw.get("factor_version"), methodology_available=bool(trace_raw.get("methodology_available")),
        steps=steps, conversions=conversions, notes=tuple(trace_raw.get("notes", [])),
    )
    contributions = tuple(CategoryContribution(**item) for item in raw.get("contributions", []))
    return AssessmentAudit(
        assessment_id=raw.get("assessment_id"), user_id=raw.get("user_id"), assessment_date=raw.get("assessment_date"),
        created_at=raw.get("created_at"), stored_footprint=raw.get("stored_footprint"), stored_eco_score=raw.get("stored_eco_score"),
        factor_version=raw.get("factor_version"), factor_metadata=dict(raw.get("factor_metadata", {})),
        methodology_available=bool(raw.get("methodology_available")), methodology_changed=bool(raw.get("methodology_changed")),
        inputs=dict(raw.get("inputs", {})), trace=trace, contributions=contributions,
        generated_at=str(raw.get("generated_at", "")), notes=tuple(raw.get("notes", [])),
    )
