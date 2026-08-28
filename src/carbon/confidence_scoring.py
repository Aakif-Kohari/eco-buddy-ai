"""
Data Quality Confidence Scoring for Assessments (#1260).

Two assessments can report the same footprint while resting on very
different data quality. This module scores how much an assessment's numbers
can be trusted, completely separately from `calculate_eco_score`
(src/carbon/emissions.py), which scores how good the footprint is
environmentally. Nothing here reads footprint totals, category weights, or
the eco-score baseline/sensitivity, and the eco-score path never reads this
module - the two scores cannot bleed into each other.

The score is a deterministic, pure function of the assessment's own stored
fields plus a handful of optional context arguments (region, unit system,
external validation warnings, and an explicit `as_of` timestamp). Recomputing
it later from the same assessment and the same `as_of` always reproduces the
exact same score, so a confidence value is inherently "associated" with the
assessment it was derived from - the same reproducibility property
`assessment_explainability.py` relies on for calculation traces.

Factors scored:
    * input completeness        - were optional fields (region, date, factor
                                   version) actually recorded?
    * estimated vs. measured    - did a raw input have to be capped by
                                   emissions.validate_footprint_inputs, which
                                   is a sign it was a rough guess rather than
                                   a measured value?
    * data age                  - how long ago was the assessment taken?
    * emission-factor provenance - is the underlying factor set dynamic or
                                   static, and how much uncertainty does its
                                   source carry (see emission_factors.py)?
    * unit-conversion reliability - was the input entered in the app's
                                   canonical metric units, or converted from
                                   a preferred unit system first?
    * missing-category coverage - how many of the quantitative categories
                                   (distance, electricity, flights) are at
                                   zero, which in this app usually means
                                   "left untouched" rather than "measured"?
    * validation warnings       - any warnings raised while scoring the
                                   assessment, plus any the caller supplies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from src.carbon.emission_factors import DEFAULT_VERSION, get_factor_set, has_factor_set
from src.carbon.emissions import validate_footprint_inputs
from src.utils.assessment_explainability import normalize_assessment

# Weights sum to 100. Each factor contributes weight * (score / 100).
CONFIDENCE_WEIGHTS: dict[str, float] = {
    "input_completeness": 20.0,
    "estimated_vs_measured": 15.0,
    "data_age": 15.0,
    "factor_provenance": 20.0,
    "unit_conversion": 10.0,
    "category_coverage": 15.0,
    "validation_warnings": 5.0,
}

# Classification bands, highest threshold first.
CONFIDENCE_BANDS: tuple[tuple[float, str], ...] = (
    (85.0, "High"),
    (60.0, "Medium"),
    (0.0, "Low"),
)


@dataclass(frozen=True)
class ConfidenceFactor:
    name: str
    weight: float
    score: float
    explanation: str


@dataclass(frozen=True)
class ConfidenceScore:
    assessment_id: int | str | None
    total_score: float
    classification: str
    factors: tuple[ConfidenceFactor, ...]
    warnings: tuple[str, ...]
    generated_at: str


def _classify(total_score: float) -> str:
    for threshold, label in CONFIDENCE_BANDS:
        if total_score >= threshold:
            return label
    return CONFIDENCE_BANDS[-1][1]


def _score_completeness(data: dict[str, Any], region: str | None) -> ConfidenceFactor:
    optional_fields = {
        "region provided": region is not None,
        "date recorded": data.get("date") is not None,
        "factor version recorded": data.get("factor_version") not in (None, DEFAULT_VERSION),
    }
    present = sum(1 for is_present in optional_fields.values() if is_present)
    score = (present / len(optional_fields)) * 100.0
    missing = [name for name, is_present in optional_fields.items() if not is_present]
    explanation = "All optional metadata recorded." if not missing else f"Missing: {', '.join(missing)}."
    return ConfidenceFactor("input_completeness", CONFIDENCE_WEIGHTS["input_completeness"], score, explanation)


def _score_estimated_vs_measured(data: dict[str, Any]) -> tuple[ConfidenceFactor, list[str]]:
    try:
        _, clamped_distance, clamped_electricity, clamped_flights, _ = validate_footprint_inputs(
            data["transport"], data["distance"], data["electricity"], data["diet"], data["flights"], "Global",
        )
    except ValueError:
        factor = ConfidenceFactor(
            "estimated_vs_measured", CONFIDENCE_WEIGHTS["estimated_vs_measured"], 0.0,
            "Inputs could not be validated by the calculation engine.",
        )
        return factor, ["Inputs failed calculation engine validation."]

    clamped_fields = []
    if clamped_distance != data["distance"]:
        clamped_fields.append("distance")
    if clamped_electricity != data["electricity"]:
        clamped_fields.append("electricity")
    if clamped_flights != data["flights"]:
        clamped_fields.append("flights")

    if not clamped_fields:
        factor = ConfidenceFactor(
            "estimated_vs_measured", CONFIDENCE_WEIGHTS["estimated_vs_measured"], 100.0,
            "All inputs are within realistic bounds.",
        )
        return factor, []

    warnings = [f"'{field}' was out of realistic range and had to be capped." for field in clamped_fields]
    score = max(0.0, 100.0 - 30.0 * len(clamped_fields))
    factor = ConfidenceFactor(
        "estimated_vs_measured", CONFIDENCE_WEIGHTS["estimated_vs_measured"], score,
        f"Out-of-range values capped for: {', '.join(clamped_fields)}.",
    )
    return factor, warnings


def _score_data_age(date_value: Any, as_of: datetime) -> ConfidenceFactor:
    if not date_value:
        return ConfidenceFactor(
            "data_age", CONFIDENCE_WEIGHTS["data_age"], 50.0,
            "No assessment date recorded; freshness cannot be verified.",
        )
    try:
        parsed = date_value if isinstance(date_value, datetime) else datetime.fromisoformat(str(date_value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return ConfidenceFactor(
            "data_age", CONFIDENCE_WEIGHTS["data_age"], 50.0,
            "Assessment date could not be parsed; freshness cannot be verified.",
        )

    age_days = max(0.0, (as_of - parsed).total_seconds() / 86400.0)
    if age_days <= 30:
        score, label = 100.0, "within the last 30 days"
    elif age_days <= 90:
        score, label = 80.0, "within the last 90 days"
    elif age_days <= 180:
        score, label = 60.0, "within the last 6 months"
    elif age_days <= 365:
        score, label = 40.0, "within the last year"
    else:
        score, label = 20.0, "over a year old"
    return ConfidenceFactor(
        "data_age", CONFIDENCE_WEIGHTS["data_age"], score, f"Assessment is {label} ({int(age_days)} days).",
    )


def _score_factor_provenance(factor_version: str | None) -> ConfidenceFactor:
    version = factor_version or DEFAULT_VERSION
    if not has_factor_set(version):
        return ConfidenceFactor(
            "factor_provenance", CONFIDENCE_WEIGHTS["factor_provenance"], 40.0,
            f"Factor set '{version}' is unavailable; provenance cannot be verified.",
        )
    factor_set = get_factor_set(version)
    uncertainty = factor_set["source"]["uncertainty_percent"]
    score = max(0.0, 100.0 - uncertainty * 2.0)
    kind = factor_set["kind"]
    return ConfidenceFactor(
        "factor_provenance", CONFIDENCE_WEIGHTS["factor_provenance"], score,
        f"{kind.capitalize()} factor set '{version}' from {factor_set['source']['publisher']} "
        f"(\u00b1{uncertainty:.0f}% uncertainty).",
    )


def _score_unit_conversion(input_unit_system: str) -> ConfidenceFactor:
    if input_unit_system == "metric":
        return ConfidenceFactor(
            "unit_conversion", CONFIDENCE_WEIGHTS["unit_conversion"], 100.0,
            "Inputs entered directly in the app's canonical metric units.",
        )
    return ConfidenceFactor(
        "unit_conversion", CONFIDENCE_WEIGHTS["unit_conversion"], 85.0,
        f"Inputs converted from '{input_unit_system}' units before calculation; "
        "conversion introduces a small rounding margin.",
    )


def _score_category_coverage(data: dict[str, Any]) -> ConfidenceFactor:
    quantitative_categories = {
        "distance": data["distance"],
        "electricity": data["electricity"],
        "flights": data["flights"],
    }
    zero_categories = [name for name, value in quantitative_categories.items() if not value]
    coverage = len(quantitative_categories) - len(zero_categories)
    score = (coverage / len(quantitative_categories)) * 100.0
    if not zero_categories:
        explanation = "All quantitative categories have non-zero activity recorded."
    else:
        explanation = (
            f"{', '.join(zero_categories)} recorded as zero; this may mean the "
            "category genuinely doesn't apply, or that it was left untouched."
        )
    return ConfidenceFactor("category_coverage", CONFIDENCE_WEIGHTS["category_coverage"], score, explanation)


def _score_validation_warnings(warning_count: int) -> ConfidenceFactor:
    score = max(0.0, 100.0 - 20.0 * warning_count)
    explanation = (
        "No validation warnings raised." if warning_count == 0
        else f"{warning_count} validation warning(s) raised for this assessment."
    )
    return ConfidenceFactor("validation_warnings", CONFIDENCE_WEIGHTS["validation_warnings"], score, explanation)


def calculate_assessment_confidence(
    assessment: Mapping[str, Any],
    *,
    region: str | None = None,
    input_unit_system: str = "metric",
    extra_warnings: Sequence[str] | None = None,
    as_of: datetime | None = None,
) -> ConfidenceScore:
    """
    Score how much an assessment's inputs and provenance can be trusted.

    This is independent from `calculate_eco_score` (emissions.py): it never
    reads footprint totals, category weights, or the eco-score baseline/
    sensitivity, so data quality and environmental performance are never
    confused with one another.
    """
    data = normalize_assessment(assessment)
    as_of = as_of or datetime.now(timezone.utc)

    estimated_factor, engine_warnings = _score_estimated_vs_measured(data)

    factors = [
        _score_completeness(data, region),
        estimated_factor,
        _score_data_age(data["date"] or data["created_at"], as_of),
        _score_factor_provenance(data["factor_version"]),
        _score_unit_conversion(input_unit_system),
        _score_category_coverage(data),
    ]

    all_warnings = list(engine_warnings) + list(extra_warnings or [])
    factors.append(_score_validation_warnings(len(all_warnings)))

    total_weight = sum(CONFIDENCE_WEIGHTS.values())
    total_score = round(sum(f.score * f.weight for f in factors) / total_weight, 2)

    return ConfidenceScore(
        assessment_id=data["id"],
        total_score=total_score,
        classification=_classify(total_score),
        factors=tuple(factors),
        warnings=tuple(all_warnings),
        generated_at=as_of.isoformat(),
    )


def explain_confidence(confidence: ConfidenceScore) -> list[str]:
    """
    Human-readable explanation of the factors that most affected this score,
    ordered by weighted distance from a perfect 100 (biggest drag first).
    """
    ranked = sorted(confidence.factors, key=lambda f: (100.0 - f.score) * f.weight, reverse=True)
    explanations = [f"{f.name.replace('_', ' ').title()}: {f.explanation}" for f in ranked if f.score < 100.0]
    return explanations or ["All confidence factors scored at maximum."]