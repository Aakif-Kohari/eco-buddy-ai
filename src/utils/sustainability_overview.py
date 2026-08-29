"""Personal Sustainability Overview aggregation for EcoBuddy AI.

This module does not talk to the database and does not recompute any
emissions formulas itself. It only combines results already produced by
existing utilities (``src.carbon.emissions.calculate_footprint``,
``src.utils.goals.evaluate_progress``, ``src.ai.recommendations.generate_recommendations``)
into the single summary the overview page renders, so the calculation and
persistence logic keeps living in exactly one place each.
"""

from __future__ import annotations

from typing import Any

from src.carbon.emissions import calculate_footprint
from src.utils.goals import evaluate_progress, latest_footprint
from src.ai.recommendations import generate_recommendations


# Assessment rows can be a 10-column (id, date, created_at, transport,
# distance, electricity, diet, flights, footprint, eco_score) or legacy
# 9-column (no created_at) tuple. Anchoring on both known shapes keeps this
# safe instead of guessing with negative indices.
_ASSESSMENT_FIELDS_WITH_CREATED_AT = (
    "id", "date", "created_at", "transport", "distance",
    "electricity", "diet", "flights", "footprint", "eco_score",
)
_ASSESSMENT_FIELDS_LEGACY = (
    "id", "date", "transport", "distance", "electricity",
    "diet", "flights", "footprint", "eco_score",
)

# The three CO2-denominated categories the app already computes per
# assessment map onto the "Food"/"Transportation"/"Energy" language the
# overview uses. Flights are folded into Transportation since both are
# travel emissions and the dashboard groups by lifestyle area, not by input.
_LIFESTYLE_LABELS = {
    "Diet": "Food",
    "Transport": "Transportation",
    "Flights": "Transportation",
    "Electricity": "Energy",
}


def normalize_assessment_row(row: Any) -> dict[str, Any] | None:
    """Map one get_assessments() row (dict or tuple) onto named fields.

    Returns None for anything that cannot be safely interpreted, so callers
    can drop incomplete rows instead of crashing on them.
    """
    if isinstance(row, dict):
        return dict(row)
    if not isinstance(row, (list, tuple)):
        return None
    if len(row) >= len(_ASSESSMENT_FIELDS_WITH_CREATED_AT):
        return dict(zip(_ASSESSMENT_FIELDS_WITH_CREATED_AT, row))
    if len(row) >= len(_ASSESSMENT_FIELDS_LEGACY):
        return dict(zip(_ASSESSMENT_FIELDS_LEGACY, row))
    return None


def normalize_assessments(raw_assessments: Any) -> list[dict[str, Any]]:
    """Turn raw get_assessments() rows into clean dicts, oldest first."""
    records = [
        record
        for record in (normalize_assessment_row(row) for row in raw_assessments or [])
        if record and record.get("date") is not None and record.get("footprint") is not None
    ]
    records.sort(key=lambda record: str(record["date"]))
    return records


def compare_with_previous(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare the latest footprint with the assessment before it, if any."""
    if not records:
        return {"current_kg": None, "previous_kg": None, "delta_kg": None, "percent_change": None}

    current = float(records[-1]["footprint"])
    if len(records) < 2:
        return {"current_kg": current, "previous_kg": None, "delta_kg": None, "percent_change": None}

    previous = float(records[-2]["footprint"])
    delta = current - previous
    percent_change = (delta / previous * 100.0) if previous > 0 else None
    return {
        "current_kg": current,
        "previous_kg": previous,
        "delta_kg": round(delta, 2),
        "percent_change": round(percent_change, 1) if percent_change is not None else None,
    }


def category_breakdown(latest: dict[str, Any] | None, region: str = "Global") -> dict[str, float] | None:
    """Recompute the per-category CO2 split for the latest assessment.

    Reuses src.carbon.emissions.calculate_footprint instead of re-deriving emission
    factors here. Returns None when the latest assessment is missing the
    inputs needed to recompute it (e.g. an incomplete row).
    """
    if not latest:
        return None
    try:
        _, contributors = calculate_footprint(
            latest.get("transport"),
            latest.get("distance"),
            latest.get("electricity"),
            latest.get("diet"),
            latest.get("flights"),
            region,
        )
    except (ValueError, TypeError, KeyError):
        return None
    return contributors


def map_to_lifestyle_categories(contributors: dict[str, float] | None) -> dict[str, float]:
    """Fold Transport/Flights/Electricity/Diet into Food/Transportation/Energy."""
    mapped: dict[str, float] = {}
    for category, value in (contributors or {}).items():
        label = _LIFESTYLE_LABELS.get(category)
        if not label:
            continue
        mapped[label] = mapped.get(label, 0.0) + float(value)
    return mapped


def highest_impact_category(mapped_categories: dict[str, float]) -> tuple[str, float] | None:
    """The lifestyle category with the most CO2 among the mapped, CO2-valued categories.

    Water is intentionally excluded from this comparison (and from
    ``mapped_categories`` upstream) since it is tracked in liters/day, not
    kg CO2, and is not directly comparable to the other categories.
    """
    if not mapped_categories:
        return None
    name = max(mapped_categories, key=mapped_categories.get)
    return name, mapped_categories[name]


def biggest_opportunity(mapped_categories: dict[str, float]) -> dict[str, Any] | None:
    """The category offering the greatest potential improvement, with a share."""
    top = highest_impact_category(mapped_categories)
    if not top:
        return None
    name, value = top
    total = sum(mapped_categories.values())
    share = (value / total * 100.0) if total > 0 else 0.0
    return {"category": name, "kg_co2": round(value, 2), "share_pct": round(share, 1)}


def personalized_insights(latest: dict[str, Any] | None, contributors: dict[str, float] | None) -> list[str]:
    """Reuse the existing recommendation engine for personalized tips."""
    if not latest or not contributors:
        return []
    try:
        _, tips = generate_recommendations(
            latest.get("transport"),
            latest.get("electricity"),
            latest.get("diet"),
            latest.get("flights"),
            contributors,
        )
    except (ValueError, TypeError, KeyError):
        return []
    return tips


def goal_progress(active_goal: dict[str, Any] | None, records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Reuse src.utils.goals.evaluate_progress for the user's active reduction goal, if any."""
    if not active_goal:
        return None
    try:
        return evaluate_progress(active_goal, records)
    except Exception:
        return None


def build_overview(
    raw_assessments: Any,
    active_goal: dict[str, Any] | None = None,
    water_row: dict[str, Any] | None = None,
    waste_row: dict[str, Any] | None = None,
    region: str = "Global",
) -> dict[str, Any]:
    """Assemble the full Personal Sustainability Overview.

    Every piece degrades gracefully: with no assessments at all, this
    returns an overview with has_data=False rather than raising.
    """
    records = normalize_assessments(raw_assessments)
    if not records:
        return {
            "has_data": False,
            "latest": None,
            "comparison": {"current_kg": None, "previous_kg": None, "delta_kg": None, "percent_change": None},
            "eco_score": None,
            "contributors": None,
            "lifestyle_categories": {},
            "highest_impact": None,
            "opportunity": None,
            "insights": [],
            "water": None,
            "waste": None,
            "goal": None,
        }

    latest = records[-1]
    comparison = compare_with_previous(records)
    contributors = category_breakdown(latest, region=region)
    mapped = map_to_lifestyle_categories(contributors)

    water = None
    if water_row and water_row.get("total_liters") is not None:
        water = {"liters_per_day": round(float(water_row["total_liters"]), 1)}

    waste = None
    if waste_row and waste_row.get("annual_co2") is not None:
        waste = {
            "annual_co2_kg": round(float(waste_row["annual_co2"]), 1),
            "recyclable_pct": round(float(waste_row.get("recyclable_pct") or 0.0), 1),
        }
        mapped["Waste"] = waste["annual_co2_kg"]

    eco_score = latest.get("eco_score")

    return {
        "has_data": True,
        "latest": latest,
        "comparison": comparison,
        "eco_score": int(eco_score) if eco_score is not None else None,
        "contributors": contributors,
        "lifestyle_categories": mapped,
        "highest_impact": highest_impact_category(mapped),
        "opportunity": biggest_opportunity(mapped),
        "insights": personalized_insights(latest, contributors),
        "water": water,
        "waste": waste,
        "goal": goal_progress(active_goal, records),
    }