"""
Carbon Budget Planner Engine
============================
Sets category-level carbon budgets, tracks actual usage against targets,
projects end-of-period status, and generates alerts when limits are
approached or exceeded.

Features:
- Per-category budget allocation (Transport, Energy, Diet, Flights)
- Monthly and annual budget tracking
- Real-time usage projection with linear regression
- Alert generation for approaching/exceeding limits
- Budget optimization recommendations
"""

import math
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ── Default Budget Templates (kg CO2/month) ──────────────────────────────────

DEFAULT_BUDGET_TEMPLATES: dict[str, dict[str, Any]] = {
    "conservative": {
        "label": "🌿 Conservative (Earth Guardian)",
        "Transport": 120.0,
        "Electricity": 100.0,
        "Diet": 70.0,
        "Flights": 20.0,
        "total_monthly_kg": 310.0,
        "description": "Aggressive reduction target aligned with 1.5°C pathway.",
    },
    "moderate": {
        "label": "🌍 Moderate (Green Achiever)",
        "Transport": 180.0,
        "Electricity": 150.0,
        "Diet": 100.0,
        "Flights": 40.0,
        "total_monthly_kg": 470.0,
        "description": "Balanced approach — achievable with consistent effort.",
    },
    "relaxed": {
        "label": "🌱 Relaxed (Eco Starter)",
        "Transport": 250.0,
        "Electricity": 200.0,
        "Diet": 130.0,
        "Flights": 60.0,
        "total_monthly_kg": 640.0,
        "description": "Gentle starting point for building sustainable habits.",
    },
}

ALERT_THRESHOLDS = {
    "safe": 0.50,      # Under 50% — all clear
    "caution": 0.75,   # 50-75% — caution
    "warning": 0.90,   # 75-90% — warning
    "critical": 1.00,  # 90-100% — critical
    "exceeded": 1.01,  # Over 100% — exceeded
}

# ── Core Functions ───────────────────────────────────────────────────────────

def get_budget_template(template_name: str) -> dict[str, Any]:
    """Get a budget template by name, falling back to moderate."""
    return DEFAULT_BUDGET_TEMPLATES.get(template_name, DEFAULT_BUDGET_TEMPLATES["moderate"])


def calculate_category_budgets(
    total_monthly_budget: float,
    category_weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """
    Distribute a total monthly budget across categories based on weights.
    Default weights mirror typical household emission distribution.
    """
    weights = category_weights or {
        "Transport": 0.35,
        "Electricity": 0.30,
        "Diet": 0.20,
        "Flights": 0.15,
    }
    total_weight = sum(weights.values())
    budgets = {}
    for cat, w in weights.items():
        budgets[cat] = round(total_monthly_budget * (w / total_weight), 2)
    return budgets


def evaluate_budget_usage(
    budgets: dict[str, float],
    actuals: dict[str, float],
) -> list[dict[str, Any]]:
    """
    Evaluate actual usage against budget for each category.
    Returns a list of category evaluation dicts sorted by usage ratio descending.
    """
    evaluations = []
    for category in budgets:
        budget = budgets.get(category, 0)
        actual = actuals.get(category, 0)
        remaining = budget - actual
        ratio = actual / budget if budget > 0 else float("inf")

        # Determine alert level
        if ratio >= ALERT_THRESHOLDS["exceeded"]:
            alert = "exceeded"
            alert_icon = "🔴"
        elif ratio >= ALERT_THRESHOLDS["critical"]:
            alert = "critical"
            alert_icon = "🟠"
        elif ratio >= ALERT_THRESHOLDS["warning"]:
            alert = "warning"
            alert_icon = "🟡"
        elif ratio >= ALERT_THRESHOLDS["caution"]:
            alert = "caution"
            alert_icon = "🔵"
        else:
            alert = "safe"
            alert_icon = "🟢"

        evaluations.append({
            "category": category,
            "budget_kg": round(budget, 2),
            "actual_kg": round(actual, 2),
            "remaining_kg": round(remaining, 2),
            "usage_ratio": round(ratio, 4),
            "usage_percent": round(ratio * 100, 1),
            "alert_level": alert,
            "alert_icon": alert_icon,
        })

    evaluations.sort(key=lambda e: e["usage_ratio"], reverse=True)
    return evaluations


def project_month_end_usage(
    actuals: dict[str, float],
    day_of_month: int,
    days_in_month: int = 30,
) -> dict[str, dict[str, Any]]:
    """
    Project end-of-month usage based on current daily burn rate.
    """
    projections = {}
    for category, actual in actuals.items():
        daily_rate = actual / max(day_of_month, 1)
        projected_total = daily_rate * days_in_month
        remaining_days = max(days_in_month - day_of_month, 0)
        projections[category] = {
            "current_kg": round(actual, 2),
            "daily_rate_kg": round(daily_rate, 2),
            "projected_month_end_kg": round(projected_total, 2),
            "remaining_days": remaining_days,
        }
    return projections


def generate_budget_alerts(
    evaluations: list[dict[str, Any]],
    projections: dict[str, dict[str, Any]],
    budgets: dict[str, float],
) -> list[dict[str, Any]]:
    """
    Generate actionable alerts based on current usage and projections.
    """
    alerts = []
    for ev in evaluations:
        cat = ev["category"]
        budget = budgets.get(cat, 0)
        proj = projections.get(cat, {})

        if ev["alert_level"] == "exceeded":
            overage = ev["actual_kg"] - budget
            alerts.append({
                "category": cat,
                "severity": "critical",
                "icon": "🔴",
                "title": f"{cat} Budget Exceeded!",
                "message": f"You've exceeded your {cat} budget by {overage:.1f} kg. "
                           f"Consider reducing {cat.lower()} activities this month.",
                "action": f"Reduce {cat.lower()} by {overage:.1f} kg to get back on track.",
            })
        elif ev["alert_level"] == "critical":
            alerts.append({
                "category": cat,
                "severity": "high",
                "icon": "🟠",
                "title": f"{cat} Approaching Limit",
                "message": f"You've used {ev['usage_percent']:.0f}% of your {cat} budget with "
                           f"{proj.get('remaining_days', 0)} days remaining.",
                "action": f"Limit {cat.lower()} spending to {ev['remaining_kg']:.1f} kg for the rest of the month.",
            })
        elif ev["alert_level"] == "warning":
            proj_exceed = proj.get("projected_month_end_kg", 0)
            if proj_exceed > budget:
                overshoot = proj_exceed - budget
                alerts.append({
                    "category": cat,
                    "severity": "medium",
                    "icon": "🟡",
                    "title": f"{cat} On Track to Exceed",
                    "message": f"At current rate, {cat} will exceed budget by {overshoot:.1f} kg.",
                    "action": f"Reduce daily {cat.lower()} rate by "
                             f"{(proj.get('daily_rate_kg', 0) * (overshoot / proj_exceed)):.1f} kg/day.",
                })

    alerts.sort(key=lambda a: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(a["severity"], 4))
    return alerts


def calculate_budget_score(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate an overall budget adherence score (0-100).
    Higher is better — means staying within budget.
    """
    if not evaluations:
        return {"score": 100, "grade": "A+", "description": "No data — perfect by default!"}

    # Score = 100 - average penalty for overshoot
    penalties = []
    for ev in evaluations:
        ratio = ev["usage_ratio"]
        if ratio <= 1.0:
            penalty = 0
        else:
            penalty = (ratio - 1.0) * 100  # 100 penalty per 100% over budget
        penalties.append(penalty)

    avg_penalty = sum(penalties) / len(penalties)
    score = max(0, min(100, 100 - avg_penalty))

    # Grade
    if score >= 95: grade, desc = "A+", "Excellent — well within budget!"
    elif score >= 85: grade, desc = "A", "Great — minor overages only."
    elif score >= 75: grade, desc = "B", "Good — some categories need attention."
    elif score >= 60: grade, desc = "C", "Fair — multiple categories over budget."
    elif score >= 40: grade, desc = "D", "Needs work — significant overages detected."
    else: grade, desc = "F", "Critical — major budget violations across categories."

    return {"score": round(score, 1), "grade": grade, "description": desc}


def generate_budget_recommendations(
    evaluations: list[dict[str, Any]],
    budgets: dict[str, float],
) -> list[str]:
    """
    Generate specific recommendations based on budget evaluation.
    """
    recs = []
    over_budget = [e for e in evaluations if e["usage_ratio"] > 1.0]
    near_budget = [e for e in evaluations if 0.75 < e["usage_ratio"] <= 1.0]

    if over_budget:
        worst = over_budget[0]
        overage = worst["actual_kg"] - worst["budget_kg"]
        recs.append(
            f"🔴 **{worst['category']}** is {overage:.1f} kg over budget. "
            f"Prioritize reducing {worst['category'].lower()} activities immediately."
        )

    if near_budget:
        cats = ", ".join(e["category"] for e in near_budget)
        recs.append(
            f"🟡 **{cats}** approaching budget limits. "
            f"Monitor closely and consider reducing usage."
        )

    safe = [e for e in evaluations if e["usage_ratio"] <= 0.50]
    if safe:
        cats = ", ".join(e["category"] for e in safe)
        recs.append(
            f"🟢 **{cats}** well under budget — great job! "
            f"Consider if budget could be redistributed to high-pressure categories."
        )

    if not recs:
        recs.append("✅ All categories are within budget. Keep up the great work!")

    recs.extend([
        "📊 Review your monthly trend to spot patterns.",
        "🎯 Consider switching to a stricter budget template for faster progress.",
        "🔄 Set up weekly check-ins to stay on track.",
    ])

    return recs


def generate_budget_report(
    budgets: dict[str, float],
    actuals: dict[str, float],
    day_of_month: int,
    days_in_month: int = 30,
    template_name: str = "moderate",
) -> dict[str, Any]:
    """
    Main entry point — generates a comprehensive budget report.
    """
    evaluations = evaluate_budget_usage(budgets, actuals)
    projections = project_month_end_usage(actuals, day_of_month, days_in_month)
    alerts = generate_budget_alerts(evaluations, projections, budgets)
    score = calculate_budget_score(evaluations)
    recommendations = generate_budget_recommendations(evaluations, budgets)

    total_budget = sum(budgets.values())
    total_actual = sum(actuals.values())
    total_remaining = total_budget - total_actual

    return {
        "template_name": template_name,
        "template_label": get_budget_template(template_name)["label"],
        "budgets": budgets,
        "actuals": actuals,
        "evaluations": evaluations,
        "projections": projections,
        "alerts": alerts,
        "score": score,
        "recommendations": recommendations,
        "totals": {
            "budget_kg": round(total_budget, 2),
            "actual_kg": round(total_actual, 2),
            "remaining_kg": round(total_remaining, 2),
            "usage_percent": round((total_actual / total_budget * 100) if total_budget > 0 else 0, 1),
        },
        "day_of_month": day_of_month,
        "days_in_month": days_in_month,
        "generated_at": datetime.utcnow().isoformat(),
    }
