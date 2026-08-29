"""
Carbon Savings Tracker Engine
=============================
Tracks cumulative carbon savings over time, computes streaks,
milestone achievements, and generates actionable savings reports.
"""

import math
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

MILESTONES: list[dict[str, Any]] = [
    {"kg_threshold": 100, "badge": "🌱 Seedling Saver", "message": "You've saved 100 kg CO₂ — a seedling of change!"},
    {"kg_threshold": 500, "badge": "🌿 Green Guardian", "message": "500 kg saved — your impact is growing!"},
    {"kg_threshold": 1000, "badge": "🌳 Forest Fighter", "message": "1,000 kg saved — equivalent to planting 15 trees."},
    {"kg_threshold": 2500, "badge": "🌍 Planet Protector", "message": "2,500 kg saved — a true Earth champion."},
    {"kg_threshold": 5000, "badge": "⚡ Carbon Hero", "message": "5,000 kg saved — extraordinary commitment!"},
    {"kg_threshold": 10000, "badge": "🏆 Climate Legend", "message": "10,000 kg saved — legendary sustainability."},
]

EQUIVALENTS: list[dict[str, Any]] = [
    {"label": "Trees Planted", "factor": 22.0, "unit": "trees", "icon": "🌳"},
    {"label": "Driving Avoided (km)", "factor": 0.21, "unit": "km", "icon": "🚗"},
    {"label": "Flights Avoided", "factor": 250.0, "unit": "flights", "icon": "✈️"},
    {"label": "Meat-Free Days", "factor": 6.0, "unit": "days", "icon": "🥗"},
    {"label": "Homes Powered (1 day)", "factor": 10.0, "unit": "home-days", "icon": "🏠"},
]

STREAK_THRESHOLDS = {
    "bronze": 7,
    "silver": 30,
    "gold": 90,
    "platinum": 180,
    "diamond": 365,
}


# ── Core Functions ───────────────────────────────────────────────────────────

def calculate_baseline_footprint(transport: str, distance: float, electricity: float,
                                 diet: str, flights: int) -> float:
    """
    Calculate a user's estimated baseline footprint from raw inputs.
    Uses simplified emission factors for streak tracking (no API dependency).
    """
    transport_factors = {"Car": 0.19, "Public Transport": 0.07, "Bike": 0.0, "Walking": 0.0}
    diet_factors = {"Vegetarian": 950, "Non-Vegetarian": 1750}
    elec_factor = 0.82
    flight_factor = 250.0

    t = transport_factors.get(transport, 0.19)
    d = diet_factors.get(diet, 950)

    transport_emission = t * distance * 365
    electricity_emission = electricity * elec_factor * 12
    diet_emission = d
    flight_emission = flights * flight_factor

    return round(transport_emission + electricity_emission + diet_emission + flight_emission, 2)


def compute_savings_history(assessments: list[dict[str, Any]], baseline_kg: float | None = None) -> list[dict[str, Any]]:
    """
    Compute a running savings record for each assessment.

    Each assessment dict: {"date": str, "footprint": float, ...}
    If baseline_kg is provided, savings = baseline - footprint for each assessment.
    Otherwise, the first assessment's footprint is used as the baseline.

    Returns a list of dicts with date, footprint, savings_kg, cumulative_savings_kg, etc.
    """
    if not assessments:
        return []

    sorted_a = sorted(assessments, key=lambda a: a.get("date", ""))
    if baseline_kg is None:
        baseline_kg = sorted_a[0].get("footprint", 0.0)

    records = []
    cumulative = 0.0

    for a in sorted_a:
        fp = a.get("footprint", 0.0)
        savings = round(baseline_kg - fp, 2)
        cumulative += savings
        records.append({
            "date": a.get("date", ""),
            "footprint": fp,
            "baseline_kg": baseline_kg,
            "savings_kg": savings,
            "cumulative_savings_kg": round(cumulative, 2),
        })

    return records


def compute_streak(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute current streak of consecutive savings-positive months.

    A "savings-positive" month is one where the footprint is below the baseline.
    Streak counts consecutive months ending at the most recent assessment.
    """
    if not records:
        return {"current_streak_days": 0, "longest_streak_days": 0, "streak_tier": "none"}

    # Determine streak by counting consecutive savings-positive records from the end
    streak = 0
    for rec in reversed(records):
        if rec["savings_kg"] > 0:
            streak += 1
        else:
            break

    # Estimate streak length in days (approximate 30 days per record)
    streak_days = streak * 30

    # Longest streak
    longest = 0
    current_run = 0
    for rec in records:
        if rec["savings_kg"] > 0:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 0
    longest_days = longest * 30

    # Determine tier
    tier = "none"
    for tier_name, threshold in sorted(STREAK_THRESHOLDS.items(),
                                       key=lambda x: x[1], reverse=True):
        if streak_days >= threshold:
            tier = tier_name
            break

    return {
        "current_streak_days": streak_days,
        "longest_streak_days": longest_days,
        "streak_tier": tier,
        "current_streak_months": streak,
        "longest_streak_months": longest,
    }


def check_milestones(cumulative_savings_kg: float) -> list[dict[str, Any]]:
    """
    Check which milestones the user has achieved based on cumulative savings.
    Returns all achieved milestones.
    """
    achieved = []
    for m in MILESTONES:
        if cumulative_savings_kg >= m["kg_threshold"]:
            achieved.append(m.copy())
    return achieved


def next_milestone(cumulative_savings_kg: float) -> dict[str, Any] | None:
    """Return the next milestone the user hasn't reached yet."""
    for m in MILESTONES:
        if cumulative_savings_kg < m["kg_threshold"]:
            remaining = m["kg_threshold"] - cumulative_savings_kg
            progress_pct = (cumulative_savings_kg / m["kg_threshold"]) * 100.0
            return {
                "badge": m["badge"],
                "threshold_kg": m["kg_threshold"],
                "remaining_kg": round(remaining, 2),
                "progress_pct": round(progress_pct, 1),
            }
    return None


def compute_savings_equivalents(total_savings_kg: float) -> list[dict[str, Any]]:
    """
    Convert total savings into real-world equivalents like trees planted
    or flights avoided.
    """
    equivalents = []
    for eq in EQUIVALENTS:
        value = round(total_savings_kg / eq["factor"], 1) if eq["factor"] > 0 else 0
        equivalents.append({
            "label": eq["label"],
            "value": value,
            "unit": eq["unit"],
            "icon": eq["icon"],
        })
    return equivalents


def compute_monthly_savings_rate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate average monthly savings rate and project future savings.
    """
    if not records:
        return {"avg_monthly_savings_kg": 0.0, "projection_12m_kg": 0.0, "trend": "insufficient_data"}

    positive_records = [r for r in records if r["savings_kg"] > 0]
    avg_savings = sum(r["savings_kg"] for r in positive_records) / len(records) if records else 0
    projection_12m = avg_savings * 12

    # Trend: compare first half vs second half savings
    mid = len(records) // 2
    if mid > 0:
        first_half_avg = sum(r["savings_kg"] for r in records[:mid]) / mid
        second_half_avg = sum(r["savings_kg"] for r in records[mid:]) / (len(records) - mid)
        if second_half_avg > first_half_avg * 1.1:
            trend = "improving"
        elif second_half_avg < first_half_avg * 0.9:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    return {
        "avg_monthly_savings_kg": round(avg_savings, 2),
        "projection_12m_kg": round(projection_12m, 2),
        "trend": trend,
        "positive_months": len(positive_records),
        "total_months": len(records),
    }


def generate_savings_report(assessments: list[dict[str, Any]],
                            baseline_kg: float | None = None,
                            region: str = "Global") -> dict[str, Any]:
    """
    Main entry point — generates a comprehensive savings report.
    """
    records = compute_savings_history(assessments, baseline_kg)
    if not records:
        return {"records": [], "summary": "No assessment data available for savings tracking."}

    total_savings = records[-1]["cumulative_savings_kg"]
    current_fp = records[-1]["footprint"]
    baseline = records[0]["baseline_kg"]

    return {
        "records": records,
        "baseline_kg": baseline,
        "current_footprint_kg": current_fp,
        "total_savings_kg": total_savings,
        "savings_pct": round((total_savings / baseline * 100) if baseline > 0 else 0, 1),
        "streak": compute_streak(records),
        "milestones_achieved": check_milestones(total_savings),
        "next_milestone": next_milestone(total_savings),
        "equivalents": compute_savings_equivalents(total_savings),
        "monthly_rate": compute_monthly_savings_rate(records),
        "region": region,
        "generated_at": datetime.utcnow().isoformat(),
    }
