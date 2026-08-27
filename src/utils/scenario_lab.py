"""What-if carbon footprint scenario engine.

This module contains the non-UI logic for the Scenario Lab.  It deliberately
delegates emissions and Eco Score calculations to the existing ``emissions``
module so that scenarios cannot drift away from the application's canonical
calculation methodology.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from src.core.config import (
    MAX_DISTANCE,
    MAX_ELECTRICITY,
    MAX_FLIGHTS,
    TRANSPORT_EMISSION_FACTORS,
    DIET_EMISSION_FACTORS,
    VALID_REGIONS,
)
from src.carbon.emissions import (
    calculate_eco_score,
    calculate_footprint,
    validate_footprint_inputs,
)


class ScenarioValidationError(ValueError):
    """Raised when a scenario is invalid or cannot be safely calculated."""


@dataclass(frozen=True)
class ScenarioInput:
    """Complete set of inputs required to calculate a scenario."""

    name: str
    transport: str
    distance: float
    electricity: float
    diet: str
    flights: int
    region: str = "Global"

    def as_calculation_kwargs(self) -> dict[str, Any]:
        return {
            "transport": self.transport,
            "distance": self.distance,
            "electricity": self.electricity,
            "diet": self.diet,
            "flights": self.flights,
            "region": self.region,
        }


@dataclass(frozen=True)
class ScenarioResult:
    """Calculated scenario result and category breakdown."""

    scenario: ScenarioInput
    footprint: float
    eco_score: int
    contributors: dict[str, float]
    audit_log: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": asdict(self.scenario),
            "footprint": self.footprint,
            "eco_score": self.eco_score,
            "contributors": self.contributors,
            "audit_log": self.audit_log,
        }


@dataclass(frozen=True)
class ScenarioComparison:
    """Side-by-side comparison between a baseline and scenario."""

    baseline_footprint: float
    scenario_footprint: float
    baseline_eco_score: int
    scenario_eco_score: int
    footprint_delta: float
    percentage_change: float
    eco_score_delta: int
    category_deltas: dict[str, float]
    largest_improvement_category: str | None
    increased_categories: tuple[str, ...]
    reduction: float

    @property
    def is_reduction(self) -> bool:
        return self.footprint_delta < 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_footprint": self.baseline_footprint,
            "scenario_footprint": self.scenario_footprint,
            "baseline_eco_score": self.baseline_eco_score,
            "scenario_eco_score": self.scenario_eco_score,
            "footprint_delta": self.footprint_delta,
            "percentage_change": self.percentage_change,
            "eco_score_delta": self.eco_score_delta,
            "category_deltas": self.category_deltas,
            "largest_improvement_category": self.largest_improvement_category,
            "increased_categories": list(self.increased_categories),
            "reduction": self.reduction,
        }


def _coerce_number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ScenarioValidationError(f"{field} must be a number") from exc
    if not number >= 0:
        raise ScenarioValidationError(f"{field} cannot be negative")
    return number


def _coerce_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ScenarioValidationError(f"{field} must be an integer") from exc
    if number < 0:
        raise ScenarioValidationError(f"{field} cannot be negative")
    return number


def validate_scenario(scenario: ScenarioInput) -> ScenarioInput:
    """Validate and normalize a scenario using the canonical input validator."""
    if not isinstance(scenario.name, str) or not scenario.name.strip():
        raise ScenarioValidationError("Scenario name is required")

    if scenario.diet not in DIET_EMISSION_FACTORS:
        raise ScenarioValidationError(
            f"Invalid diet '{scenario.diet}'. Must be one of: "
            f"{', '.join(sorted(DIET_EMISSION_FACTORS.keys()))}"
        )

    if scenario.region not in VALID_REGIONS:
        raise ScenarioValidationError(
            f"Invalid region '{scenario.region}'. Choose one of: "
            f"{', '.join(sorted(VALID_REGIONS))}"
        )

    distance = _coerce_number(scenario.distance, "distance")
    electricity = _coerce_number(scenario.electricity, "electricity")
    flights = _coerce_int(scenario.flights, "flights")

    if distance > MAX_DISTANCE:
        raise ScenarioValidationError(f"distance cannot exceed {MAX_DISTANCE} km/day")
    if electricity > MAX_ELECTRICITY:
        raise ScenarioValidationError(
            f"electricity cannot exceed {MAX_ELECTRICITY} kWh/month"
        )
    if flights > MAX_FLIGHTS:
        raise ScenarioValidationError(
            f"flights cannot exceed {MAX_FLIGHTS} flights/year"
        )

    try:
        diet, distance, electricity, flights, region = validate_footprint_inputs(
            scenario.transport,
            distance,
            electricity,
            scenario.diet,
            flights,
            scenario.region,
        )
    except (ValueError, TypeError) as exc:
        raise ScenarioValidationError(str(exc)) from exc

    return ScenarioInput(
        name=scenario.name.strip(),
        transport=scenario.transport,
        distance=distance,
        electricity=electricity,
        diet=diet,
        flights=flights,
        region=region,
    )


def create_scenario(
    baseline: Mapping[str, Any],
    name: str,
    *,
    transport: str | None = None,
    distance: float | None = None,
    electricity: float | None = None,
    diet: str | None = None,
    flights: int | None = None,
    region: str | None = None,
) -> ScenarioInput:
    """Create a validated scenario by overriding selected baseline inputs."""
    scenario = ScenarioInput(
        name=name,
        transport=transport if transport is not None else baseline["transport"],
        distance=distance if distance is not None else baseline["distance"],
        electricity=(
            electricity if electricity is not None else baseline["electricity"]
        ),
        diet=diet if diet is not None else baseline["diet"],
        flights=flights if flights is not None else baseline["flights"],
        region=region if region is not None else baseline.get("region", "Global"),
    )
    return validate_scenario(scenario)


def calculate_scenario(scenario: ScenarioInput) -> ScenarioResult:
    """Calculate a scenario using the application's canonical emissions engine."""
    scenario = validate_scenario(scenario)
    footprint, contributors, audit_log = calculate_footprint(
        **scenario.as_calculation_kwargs(),
        return_audit=True,
    )
    eco_score = calculate_eco_score(footprint, contributors)
    return ScenarioResult(
        scenario=scenario,
        footprint=round(float(footprint), 2),
        eco_score=int(eco_score),
        contributors={key: float(value) for key, value in contributors.items()},
        audit_log=audit_log,
    )


def _percent_change(baseline: float, scenario: float) -> float:
    if baseline == 0:
        return 0.0 if scenario == 0 else 100.0
    return round(((scenario - baseline) / baseline) * 100, 2)


def calculate_category_deltas(
    baseline_contributors: Mapping[str, float],
    scenario_contributors: Mapping[str, float],
) -> dict[str, float]:
    """Return scenario minus baseline for every category present in either set."""
    categories = set(baseline_contributors) | set(scenario_contributors)
    return {
        category: round(
            float(scenario_contributors.get(category, 0))
            - float(baseline_contributors.get(category, 0)),
            2,
        )
        for category in sorted(categories)
    }


def compare_scenario_to_baseline(
    baseline: ScenarioResult,
    scenario: ScenarioResult,
) -> ScenarioComparison:
    """Compare two calculated results without mutating either result."""
    category_deltas = calculate_category_deltas(
        baseline.contributors,
        scenario.contributors,
    )
    improvements = {
        category: -delta
        for category, delta in category_deltas.items()
        if delta < 0
    }
    largest = max(improvements, key=improvements.get) if improvements else None
    increased = tuple(sorted(category for category, delta in category_deltas.items() if delta > 0))
    delta = round(scenario.footprint - baseline.footprint, 2)

    return ScenarioComparison(
        baseline_footprint=baseline.footprint,
        scenario_footprint=scenario.footprint,
        baseline_eco_score=baseline.eco_score,
        scenario_eco_score=scenario.eco_score,
        footprint_delta=delta,
        percentage_change=_percent_change(baseline.footprint, scenario.footprint),
        eco_score_delta=scenario.eco_score - baseline.eco_score,
        category_deltas=category_deltas,
        largest_improvement_category=largest,
        increased_categories=increased,
        reduction=round(max(0.0, baseline.footprint - scenario.footprint), 2),
    )


def rank_scenarios(
    baseline: ScenarioResult,
    scenarios: Iterable[ScenarioResult],
) -> list[tuple[ScenarioResult, ScenarioComparison]]:
    """Rank scenarios by reduction, then percentage reduction, then name."""
    ranked = []
    for scenario in scenarios:
        comparison = compare_scenario_to_baseline(baseline, scenario)
        ranked.append((scenario, comparison))
    return sorted(
        ranked,
        key=lambda item: (
            -item[1].reduction,
            -max(0.0, -item[1].percentage_change),
            item[0].scenario.name.lower(),
        ),
    )


def compare_multiple_scenarios(
    baseline: ScenarioResult,
    scenarios: Iterable[ScenarioResult],
) -> list[dict[str, Any]]:
    """Return ranked, UI-friendly scenario comparison dictionaries."""
    rows = []
    for rank, (scenario, comparison) in enumerate(
        rank_scenarios(baseline, scenarios), start=1
    ):
        rows.append(
            {
                "rank": rank,
                "name": scenario.scenario.name,
                "footprint_kg_co2e": scenario.footprint,
                "reduction_kg_co2e": comparison.reduction,
                "percentage_change": comparison.percentage_change,
                "eco_score": scenario.eco_score,
                "eco_score_change": comparison.eco_score_delta,
                "largest_improvement_category": comparison.largest_improvement_category
                or "None",
                "increased_categories": ", ".join(comparison.increased_categories)
                or "None",
            }
        )
    return rows


def serialize_scenario(scenario: ScenarioInput) -> str:
    """Serialize a scenario to a stable JSON representation."""
    return json.dumps(asdict(validate_scenario(scenario)), sort_keys=True)


def deserialize_scenario(payload: str | Mapping[str, Any]) -> ScenarioInput:
    """Deserialize and validate a scenario from JSON or a mapping."""
    try:
        data = json.loads(payload) if isinstance(payload, str) else dict(payload)
        return validate_scenario(ScenarioInput(**data))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ScenarioValidationError(f"Invalid scenario payload: {exc}") from exc


# Presets are data-driven.  The transformations are intentionally small and
# composable so new presets can be added without changing the Streamlit page.
SCENARIO_PRESETS: dict[str, dict[str, Any]] = {
    "Reduce car distance by 25%": {"distance_multiplier": 0.75},
    "Reduce car distance by 50%": {"distance_multiplier": 0.50},
    "Reduce electricity by 25%": {"electricity_multiplier": 0.75},
    "Reduce annual flights by 25%": {"flights_multiplier": 0.75},
    "Reduce annual flights by 50%": {"flights_multiplier": 0.50},
    "Switch to Public Transport": {"transport": "Public Transport"},
    "Switch to Bike": {"transport": "Bike"},
    "Switch to Walking": {"transport": "Walking"},
    "Switch to Vegetarian": {"diet": "Vegetarian"},
    "Combined transport + energy reduction": {
        "distance_multiplier": 0.75,
        "electricity_multiplier": 0.75,
    },
}


def apply_preset(
    baseline: Mapping[str, Any],
    preset_name: str,
    *,
    name: str | None = None,
) -> ScenarioInput:
    """Build a scenario from a named, configuration-driven preset."""
    if preset_name not in SCENARIO_PRESETS:
        raise ScenarioValidationError(f"Unknown scenario preset: {preset_name}")

    config = dict(SCENARIO_PRESETS[preset_name])
    distance = baseline["distance"]
    electricity = baseline["electricity"]
    flights = baseline["flights"]

    if "distance_multiplier" in config:
        distance = max(0.0, float(distance) * float(config["distance_multiplier"]))
    if "electricity_multiplier" in config:
        electricity = max(
            0.0, float(electricity) * float(config["electricity_multiplier"])
        )
    if "flights_multiplier" in config:
        flights = max(0, int(round(float(flights) * float(config["flights_multiplier"]))))

    return create_scenario(
        baseline,
        name or preset_name,
        transport=src.core.config.get("transport"),
        distance=distance,
        electricity=electricity,
        diet=src.core.config.get("diet"),
        flights=flights,
    )


def find_best_single_change(
    baseline: ScenarioResult,
    scenarios: Iterable[ScenarioResult],
) -> ScenarioResult | None:
    """Return the scenario with the largest positive footprint reduction."""
    ranked = rank_scenarios(baseline, scenarios)
    return ranked[0][0] if ranked and ranked[0][1].reduction > 0 else None


def summarize_scenario(
    scenario: ScenarioResult,
    comparison: ScenarioComparison,
) -> str:
    """Create a concise human-readable scenario summary."""
    if comparison.footprint_delta < 0:
        direction = f"reduces footprint by {comparison.reduction:.2f} kg CO₂e/year"
    elif comparison.footprint_delta > 0:
        direction = (
            f"increases footprint by {abs(comparison.footprint_delta):.2f} "
            "kg CO₂e/year"
        )
    else:
        direction = "does not change the annual footprint"

    return (
        f"{scenario.scenario.name}: {direction} "
        f"({comparison.percentage_change:+.2f}%), "
        f"Eco Score {comparison.baseline_eco_score} → {comparison.scenario_eco_score}."
    )
