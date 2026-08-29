"""
Sustainability Scenario Simulation and What-If Analysis Engine.

Implements GitHub issue #1296 as a pure, non-persistent simulation layer.
Scenarios are evaluated against a copy of assessment inputs and therefore
cannot mutate the user's real assessment history.

The engine deliberately delegates carbon calculations to the canonical
``src.carbon.emissions.calculate_footprint`` function. This prevents a
second, drifting emissions formula from being introduced for hypothetical
results.

Supported scenario operations:
* percentage changes to numeric inputs
* absolute numeric overrides
* transport/diet switches
* combined multi-change scenarios
* scenario comparison and ranking
* sensitivity analysis
* deterministic serialization
* validation and safe clamping
* reduction/percentage calculations
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping, Sequence

try:
    from src.carbon.emissions import calculate_footprint
except ImportError:  # pragma: no cover - useful when the module is inspected alone
    calculate_footprint = None


ENGINE_VERSION = "1.0"
SCENARIO_SOURCE = "MODELED_WHAT_IF"
SUPPORTED_INPUTS = (
    "transport",
    "distance",
    "electricity",
    "diet",
    "flights",
    "region",
)

NUMERIC_INPUTS = {"distance", "electricity", "flights"}
CATEGORICAL_INPUTS = {"transport", "diet"}
MAX_PERCENT_CHANGE = 100.0

DEFAULT_INPUTS = {
    "transport": "Car",
    "distance": 0.0,
    "electricity": 0.0,
    "diet": "Vegetarian",
    "flights": 0,
    "region": "Global",
}

TRANSPORT_OPTIONS = (
    "Car",
    "Bike",
    "Public Transport",
    "Walking",
)

DIET_OPTIONS = (
    "Vegetarian",
    "Non-Vegetarian",
)


class ScenarioValidationError(ValueError):
    """Raised when a scenario cannot be evaluated safely."""


@dataclass(frozen=True)
class ScenarioChange:
    """One hypothetical change applied to a copied assessment."""

    field: str
    operation: str
    value: Any
    label: str = ""
    unit: str = ""

    def __post_init__(self) -> None:
        if self.field not in SUPPORTED_INPUTS:
            raise ScenarioValidationError(f"Unsupported assessment field: {self.field}")
        if self.operation not in {"percent", "absolute", "set"}:
            raise ScenarioValidationError(
                "operation must be 'percent', 'absolute', or 'set'"
            )

        if self.operation == "percent":
            number = _finite_float(self.value, "percent change")
            if abs(number) > MAX_PERCENT_CHANGE:
                raise ScenarioValidationError(
                    f"percent change must be between -{MAX_PERCENT_CHANGE} and "
                    f"{MAX_PERCENT_CHANGE}"
                )

        if self.field in NUMERIC_INPUTS and self.operation in {"absolute", "set"}:
            _finite_float(self.value, f"value for {self.field}")

        if self.field in CATEGORICAL_INPUTS and self.operation == "percent":
            raise ScenarioValidationError(
                f"percent changes are not valid for categorical field '{self.field}'"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioDefinition:
    """A named collection of hypothetical changes."""

    id: str
    name: str
    description: str
    changes: tuple[ScenarioChange, ...]
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ScenarioValidationError("scenario id is required")
        if not self.name.strip():
            raise ScenarioValidationError("scenario name is required")
        if not self.changes:
            raise ScenarioValidationError("scenario must contain at least one change")
        if len({change.field for change in self.changes}) != len(self.changes):
            raise ScenarioValidationError(
                "a scenario cannot contain multiple changes for the same field"
            )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["changes"] = [change.to_dict() for change in self.changes]
        data["tags"] = list(self.tags)
        return data


@dataclass(frozen=True)
class ScenarioResult:
    """Immutable result of a what-if calculation."""

    scenario_id: str
    scenario_name: str
    baseline_total_kg: float
    scenario_total_kg: float
    absolute_change_kg: float
    reduction_kg: float
    reduction_percent: float
    baseline_inputs: Mapping[str, Any]
    scenario_inputs: Mapping[str, Any]
    category_baseline: Mapping[str, float]
    category_scenario: Mapping[str, float]
    category_changes: Mapping[str, float]
    changes: tuple[Mapping[str, Any], ...]
    source: str = SCENARIO_SOURCE
    engine_version: str = ENGINE_VERSION
    valid: bool = True
    warnings: tuple[str, ...] = ()

    @property
    def direction(self) -> str:
        if self.reduction_kg > 1e-9:
            return "reduction"
        if self.reduction_kg < -1e-9:
            return "increase"
        return "unchanged"

    @property
    def result_id(self) -> str:
        payload = json.dumps(
            {
                "scenario_id": self.scenario_id,
                "baseline": self.baseline_inputs,
                "scenario": self.scenario_inputs,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["baseline_inputs"] = dict(self.baseline_inputs)
        data["scenario_inputs"] = dict(self.scenario_inputs)
        data["category_baseline"] = dict(self.category_baseline)
        data["category_scenario"] = dict(self.category_scenario)
        data["category_changes"] = dict(self.category_changes)
        data["changes"] = [dict(change) for change in self.changes]
        data["warnings"] = list(self.warnings)
        data["direction"] = self.direction
        data["result_id"] = self.result_id
        return data


@dataclass(frozen=True)
class SensitivityPoint:
    """One point in a one-variable sensitivity curve."""

    field: str
    value: float
    total_kg: float
    reduction_kg: float
    reduction_percent: float
    valid: bool = True
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioComparison:
    """Comparison of multiple modeled scenarios."""

    baseline_total_kg: float
    results: tuple[ScenarioResult, ...]
    best_reduction_id: str | None
    lowest_total_id: str | None
    largest_increase_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_total_kg": self.baseline_total_kg,
            "results": [result.to_dict() for result in self.results],
            "best_reduction_id": self.best_reduction_id,
            "lowest_total_id": self.lowest_total_id,
            "largest_increase_id": self.largest_increase_id,
        }


def _finite_float(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ScenarioValidationError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise ScenarioValidationError(f"{name} must be finite")
    return result


def _non_negative(value: Any, name: str) -> float:
    return max(0.0, _finite_float(value, name))


def _coerce_inputs(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize an assessment into the canonical calculation shape."""

    data = dict(DEFAULT_INPUTS)
    data.update({key: value for key, value in inputs.items() if key in SUPPORTED_INPUTS})

    if not str(data.get("transport", "")).strip():
        raise ScenarioValidationError("transport is required")
    if not str(data.get("diet", "")).strip():
        raise ScenarioValidationError("diet is required")

    data["distance"] = _non_negative(data.get("distance", 0), "distance")
    data["electricity"] = _non_negative(
        data.get("electricity", 0), "electricity"
    )
    flights = _finite_float(data.get("flights", 0), "flights")
    if flights < 0:
        raise ScenarioValidationError("flights cannot be negative")
    if abs(flights - round(flights)) > 1e-9:
        raise ScenarioValidationError("flights must be a whole number")
    data["flights"] = int(round(flights))
    data["transport"] = str(data["transport"]).strip()
    data["diet"] = str(data["diet"]).strip()
    data["region"] = str(data.get("region") or "Global").strip() or "Global"
    return data


def copy_assessment_inputs(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deep copy so simulation code cannot mutate the caller's data."""

    return copy.deepcopy(_coerce_inputs(inputs))


def apply_change(
    inputs: Mapping[str, Any],
    change: ScenarioChange,
) -> tuple[dict[str, Any], str | None]:
    """Apply one change to a copy and return the new inputs plus a warning."""

    result = copy_assessment_inputs(inputs)
    warning: str | None = None

    if change.operation == "percent":
        old = _finite_float(result[change.field], change.field)
        new = old * (1.0 + float(change.value) / 100.0)
        if new < 0:
            new = 0.0
            warning = f"{change.field} was clamped at zero after the percentage change."
        result[change.field] = int(round(new)) if change.field == "flights" else new
        return result, warning

    if change.field in CATEGORICAL_INPUTS:
        new_value = str(change.value).strip()
        if not new_value:
            raise ScenarioValidationError(f"{change.field} cannot be empty")
        result[change.field] = new_value
        return result, None

    new_number = _finite_float(change.value, change.field)
    if new_number < 0:
        raise ScenarioValidationError(f"{change.field} cannot be negative")
    result[change.field] = (
        int(round(new_number)) if change.field == "flights" else new_number
    )
    return result, None


def apply_changes(
    inputs: Mapping[str, Any],
    changes: Iterable[ScenarioChange],
) -> tuple[dict[str, Any], list[str]]:
    """Apply a sequence of changes to a fresh copy."""

    current = copy_assessment_inputs(inputs)
    warnings: list[str] = []
    seen: set[str] = set()

    for change in changes:
        if change.field in seen:
            raise ScenarioValidationError(
                f"field '{change.field}' has more than one scenario change"
            )
        seen.add(change.field)
        current, warning = apply_change(current, change)
        if warning:
            warnings.append(warning)

    return current, warnings


def _canonical_calculate(inputs: Mapping[str, Any]) -> tuple[float, dict[str, float]]:
    """Call the application's canonical emissions engine."""

    if calculate_footprint is None:
        raise RuntimeError(
            "The canonical emissions engine could not be imported. "
            "Run the simulator from the repository root."
        )

    data = _coerce_inputs(inputs)
    total, contributors = calculate_footprint(
        data["transport"],
        data["distance"],
        data["electricity"],
        data["diet"],
        data["flights"],
        data["region"],
    )
    return float(total), {str(k): float(v) for k, v in contributors.items()}


def calculate_baseline(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Calculate the real baseline without changing any stored data."""

    normalized = copy_assessment_inputs(inputs)
    total, contributors = _canonical_calculate(normalized)
    return {
        "inputs": normalized,
        "total_kg": round(total, 2),
        "contributors": contributors,
        "source": "CANONICAL_ASSESSMENT_ENGINE",
    }


def simulate_scenario(
    baseline_inputs: Mapping[str, Any],
    scenario: ScenarioDefinition,
) -> ScenarioResult:
    """Evaluate a scenario against a copied baseline."""

    baseline = calculate_baseline(baseline_inputs)
    scenario_inputs, warnings = apply_changes(baseline["inputs"], scenario.changes)
    scenario_total, scenario_categories = _canonical_calculate(scenario_inputs)

    baseline_total = float(baseline["total_kg"])
    absolute_change = round(scenario_total - baseline_total, 2)
    reduction = round(baseline_total - scenario_total, 2)
    reduction_percent = (
        round(reduction / baseline_total * 100.0, 2)
        if baseline_total > 0
        else 0.0
    )

    all_categories = set(baseline["contributors"]) | set(scenario_categories)
    category_changes = {
        category: round(
            float(baseline["contributors"].get(category, 0.0))
            - float(scenario_categories.get(category, 0.0)),
            2,
        )
        for category in sorted(all_categories)
    }

    return ScenarioResult(
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        baseline_total_kg=baseline_total,
        scenario_total_kg=round(scenario_total, 2),
        absolute_change_kg=absolute_change,
        reduction_kg=reduction,
        reduction_percent=reduction_percent,
        baseline_inputs=baseline["inputs"],
        scenario_inputs=scenario_inputs,
        category_baseline=baseline["contributors"],
        category_scenario=scenario_categories,
        category_changes=category_changes,
        changes=tuple(change.to_dict() for change in scenario.changes),
        warnings=tuple(warnings),
    )


def make_percentage_scenario(
    scenario_id: str,
    name: str,
    field: str,
    percent_change: float,
    *,
    description: str = "",
    unit: str = "",
    tags: Sequence[str] = (),
) -> ScenarioDefinition:
    """Convenience factory for numeric what-if scenarios."""

    return ScenarioDefinition(
        id=scenario_id,
        name=name,
        description=description or f"Change {field} by {percent_change:g}%.",
        changes=(
            ScenarioChange(
                field=field,
                operation="percent",
                value=percent_change,
                label=f"{field} {percent_change:+g}%",
                unit=unit,
            ),
        ),
        tags=tuple(tags),
    )


def make_set_scenario(
    scenario_id: str,
    name: str,
    field: str,
    value: Any,
    *,
    description: str = "",
    unit: str = "",
    tags: Sequence[str] = (),
) -> ScenarioDefinition:
    """Convenience factory for absolute/categorical scenarios."""

    operation = "set" if field in CATEGORICAL_INPUTS else "absolute"
    return ScenarioDefinition(
        id=scenario_id,
        name=name,
        description=description or f"Set {field} to {value}.",
        changes=(
            ScenarioChange(
                field=field,
                operation=operation,
                value=value,
                label=f"{field} → {value}",
                unit=unit,
            ),
        ),
        tags=tuple(tags),
    )


def combine_scenarios(
    scenario_id: str,
    name: str,
    scenarios: Sequence[ScenarioDefinition],
    *,
    description: str = "",
    tags: Sequence[str] = (),
) -> ScenarioDefinition:
    """Combine independent scenario definitions into one multi-change scenario."""

    if not scenarios:
        raise ScenarioValidationError("at least one scenario is required")
    changes: list[ScenarioChange] = []
    for scenario in scenarios:
        changes.extend(scenario.changes)

    return ScenarioDefinition(
        id=scenario_id,
        name=name,
        description=description
        or "Combined hypothetical changes from multiple scenarios.",
        changes=tuple(changes),
        tags=tuple(tags),
    )


def rank_scenarios(
    results: Sequence[ScenarioResult],
    *,
    descending: bool = True,
) -> list[ScenarioResult]:
    """Rank scenarios by modeled carbon reduction."""

    return sorted(
        results,
        key=lambda result: (
            result.reduction_kg,
            -result.scenario_total_kg,
            result.scenario_id,
        ),
        reverse=descending,
    )


def compare_scenarios(
    results: Sequence[ScenarioResult],
) -> ScenarioComparison:
    """Produce stable comparison metadata for a set of results."""

    items = tuple(results)
    if not items:
        return ScenarioComparison(
            baseline_total_kg=0.0,
            results=(),
            best_reduction_id=None,
            lowest_total_id=None,
            largest_increase_id=None,
        )

    best = max(items, key=lambda item: (item.reduction_kg, item.scenario_id))
    lowest = min(items, key=lambda item: (item.scenario_total_kg, item.scenario_id))
    increase = min(items, key=lambda item: (item.reduction_kg, item.scenario_id))

    return ScenarioComparison(
        baseline_total_kg=items[0].baseline_total_kg,
        results=items,
        best_reduction_id=best.scenario_id,
        lowest_total_id=lowest.scenario_id,
        largest_increase_id=increase.scenario_id,
    )


def sensitivity_analysis(
    baseline_inputs: Mapping[str, Any],
    field: str,
    values: Sequence[float],
) -> list[SensitivityPoint]:
    """Evaluate a sequence of values for one numeric input."""

    if field not in NUMERIC_INPUTS:
        raise ScenarioValidationError(
            f"sensitivity analysis requires a numeric field: {field}"
        )
    baseline = calculate_baseline(baseline_inputs)
    points: list[SensitivityPoint] = []

    for value in values:
        try:
            candidate = copy_assessment_inputs(baseline["inputs"])
            candidate[field] = (
                int(round(value)) if field == "flights" else float(value)
            )
            if float(value) < 0:
                raise ScenarioValidationError("value cannot be negative")
            total, _ = _canonical_calculate(candidate)
            reduction = round(baseline["total_kg"] - total, 2)
            percent = (
                round(reduction / baseline["total_kg"] * 100.0, 2)
                if baseline["total_kg"] > 0
                else 0.0
            )
            points.append(
                SensitivityPoint(
                    field=field,
                    value=float(value),
                    total_kg=round(total, 2),
                    reduction_kg=reduction,
                    reduction_percent=percent,
                )
            )
        except (ValueError, TypeError, ScenarioValidationError) as exc:
            points.append(
                SensitivityPoint(
                    field=field,
                    value=float(value),
                    total_kg=0.0,
                    reduction_kg=0.0,
                    reduction_percent=0.0,
                    valid=False,
                    warning=str(exc),
                )
            )
    return points


def default_scenarios() -> tuple[ScenarioDefinition, ...]:
    """Return the built-in scenarios required by the issue."""

    return (
        make_percentage_scenario(
            "car-minus-30",
            "Reduce car travel by 30%",
            "distance",
            -30,
            description="Model a 30% reduction in the current daily travel distance.",
            unit="km/day",
            tags=("transport", "quick-win"),
        ),
        make_set_scenario(
            "public-transport",
            "Switch to public transportation",
            "transport",
            "Public Transport",
            description="Keep the current travel distance but switch the transport mode.",
            unit="mode",
            tags=("transport",),
        ),
        make_percentage_scenario(
            "electricity-minus-20",
            "Reduce electricity by 20%",
            "electricity",
            -20,
            description="Model a 20% reduction in monthly household electricity use.",
            unit="kWh/month",
            tags=("energy",),
        ),
        make_set_scenario(
            "vegetarian-diet",
            "Switch to vegetarian diet",
            "diet",
            "Vegetarian",
            description="Model a switch to the canonical vegetarian diet category.",
            unit="diet",
            tags=("food",),
        ),
        make_percentage_scenario(
            "flights-minus-50",
            "Reduce flights by 50%",
            "flights",
            -50,
            description="Model cutting annual flight count in half.",
            unit="flights/year",
            tags=("travel",),
        ),
    )


def run_default_scenarios(
    baseline_inputs: Mapping[str, Any],
) -> list[ScenarioResult]:
    """Evaluate all built-in scenarios."""

    return [
        simulate_scenario(baseline_inputs, scenario)
        for scenario in default_scenarios()
    ]


def export_result(result: ScenarioResult, *, indent: int = 2) -> str:
    """Serialize one result as portable JSON."""

    return json.dumps(result.to_dict(), indent=indent, sort_keys=True, default=str)


def export_comparison(
    comparison: ScenarioComparison,
    *,
    indent: int = 2,
) -> str:
    """Serialize a comparison as portable JSON."""

    return json.dumps(
        comparison.to_dict(),
        indent=indent,
        sort_keys=True,
        default=str,
    )


def validate_result(result: ScenarioResult) -> list[str]:
    """Validate internal invariants without mutating the result."""

    errors: list[str] = []

    if result.source != SCENARIO_SOURCE:
        errors.append("result source is not marked as a modeled what-if")
    if result.engine_version != ENGINE_VERSION:
        errors.append("result was produced by a different engine version")
    if result.scenario_total_kg < -1e-9:
        errors.append("scenario total cannot be negative")

    expected_reduction = round(
        result.baseline_total_kg - result.scenario_total_kg, 2
    )
    if abs(expected_reduction - result.reduction_kg) > 0.01:
        errors.append("reduction does not reconcile with baseline and scenario totals")

    expected_change = round(
        result.scenario_total_kg - result.baseline_total_kg, 2
    )
    if abs(expected_change - result.absolute_change_kg) > 0.01:
        errors.append("absolute change does not reconcile")

    return errors


def safe_scenario(
    baseline_inputs: Mapping[str, Any],
    scenario: ScenarioDefinition,
) -> ScenarioResult:
    """Evaluate a scenario and surface validation failures as a result-like object."""

    try:
        result = simulate_scenario(baseline_inputs, scenario)
        errors = validate_result(result)
        if errors:
            return ScenarioResult(
                **{
                    **result.to_dict(),
                    "changes": tuple(result.changes),
                    "warnings": tuple(result.warnings) + tuple(errors),
                    "valid": False,
                }
            )
        return result
    except (ScenarioValidationError, ValueError, TypeError) as exc:
        baseline = copy_assessment_inputs(baseline_inputs)
        return ScenarioResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            baseline_total_kg=0.0,
            scenario_total_kg=0.0,
            absolute_change_kg=0.0,
            reduction_kg=0.0,
            reduction_percent=0.0,
            baseline_inputs=baseline,
            scenario_inputs=baseline,
            category_baseline={},
            category_scenario={},
            category_changes={},
            changes=tuple(change.to_dict() for change in scenario.changes),
            valid=False,
            warnings=(str(exc),),
        )


def build_custom_scenario(
    *,
    scenario_id: str,
    name: str,
    changes: Sequence[Mapping[str, Any]],
    description: str = "",
) -> ScenarioDefinition:
    """Build a scenario from UI/API dictionaries."""

    parsed = tuple(
        ScenarioChange(
            field=str(change["field"]),
            operation=str(change.get("operation", "absolute")),
            value=change.get("value"),
            label=str(change.get("label", "")),
            unit=str(change.get("unit", "")),
        )
        for change in changes
    )
    return ScenarioDefinition(
        id=scenario_id,
        name=name,
        description=description or "Custom user-defined what-if scenario.",
        changes=parsed,
    )


def summarize_result(result: ScenarioResult) -> dict[str, Any]:
    """Create concise UI-friendly result data."""

    return {
        "scenario": result.scenario_name,
        "baseline_kg": result.baseline_total_kg,
        "scenario_kg": result.scenario_total_kg,
        "reduction_kg": result.reduction_kg,
        "reduction_percent": result.reduction_percent,
        "direction": result.direction,
        "warnings": list(result.warnings),
        "valid": result.valid,
    }


def category_contribution_table(result: ScenarioResult) -> list[dict[str, Any]]:
    """Return per-category before/after/change rows."""

    rows: list[dict[str, Any]] = []
    categories = sorted(
        set(result.category_baseline) | set(result.category_scenario)
    )
    for category in categories:
        before = float(result.category_baseline.get(category, 0.0))
        after = float(result.category_scenario.get(category, 0.0))
        rows.append(
            {
                "category": category,
                "baseline_kg": round(before, 2),
                "scenario_kg": round(after, 2),
                "change_kg": round(before - after, 2),
            }
        )
    return rows


def explain_change(result: ScenarioResult) -> list[str]:
    """Generate transparent, non-guaranteed explanations."""

    messages: list[str] = []
    if result.direction == "reduction":
        messages.append(
            f"This scenario models an estimated reduction of "
            f"{result.reduction_kg:.2f} kg CO2/year."
        )
    elif result.direction == "increase":
        messages.append(
            f"This scenario models an estimated increase of "
            f"{abs(result.reduction_kg):.2f} kg CO2/year."
        )
    else:
        messages.append("This scenario produces no modeled change in total footprint.")

    for change in result.changes:
        label = change.get("label") or (
            f"{change['field']} {change['operation']} {change['value']}"
        )
        messages.append(f"Modeled input change: {label}.")

    if result.warnings:
        messages.extend(f"Warning: {warning}" for warning in result.warnings)
    messages.append(
        "The scenario is a projection only; it does not create or overwrite an assessment."
    )
    return messages


__all__ = [
    "ENGINE_VERSION",
    "SCENARIO_SOURCE",
    "SUPPORTED_INPUTS",
    "ScenarioValidationError",
    "ScenarioChange",
    "ScenarioDefinition",
    "ScenarioResult",
    "SensitivityPoint",
    "ScenarioComparison",
    "copy_assessment_inputs",
    "apply_change",
    "apply_changes",
    "calculate_baseline",
    "simulate_scenario",
    "make_percentage_scenario",
    "make_set_scenario",
    "combine_scenarios",
    "rank_scenarios",
    "compare_scenarios",
    "sensitivity_analysis",
    "default_scenarios",
    "run_default_scenarios",
    "export_result",
    "export_comparison",
    "validate_result",
    "safe_scenario",
    "build_custom_scenario",
    "summarize_result",
    "category_contribution_table",
    "explain_change",
]
