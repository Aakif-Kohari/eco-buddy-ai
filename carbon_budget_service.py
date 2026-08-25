"""
Carbon Budget Planner — Service Layer
=======================================
Business logic for budget management, spending analysis, alerts, projections.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from carbon_budget_db import (
    init_budget_db, create_budget, get_active_budget, get_budget_by_id,
    update_budget, log_spending, get_spending_logs, get_monthly_spending,
    get_daily_spending, get_total_monthly_spent, create_alert,
    get_unread_alerts, mark_alert_read, save_monthly_history,
    get_budget_history, seed_default_categories, ACTIVITY_CO2_DATABASE,
)

# ── Budget Setup ───────────────────────────────────────────────────────

def setup_budget(user_id: int, monthly_limit_kg: float = 500.0,
                  custom_limits: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    defaults = seed_default_categories()
    limits = {k: v["default_limit_kg"] for k, v in defaults.items()}
    if custom_limits:
        limits.update(custom_limits)
    cid = create_budget(user_id, monthly_limit_kg=monthly_limit_kg, category_limits=limits)
    return {"success": True, "budget_id": cid}

def get_budget_summary(user_id: int) -> Dict[str, Any]:
    budget = get_active_budget(user_id)
    if not budget:
        return {"has_budget": False}
    now = datetime.utcnow()
    spent = get_total_monthly_spent(user_id, now.year, now.month)
    monthly_cat = get_monthly_spending(user_id, now.year, now.month)
    daily = get_daily_spending(user_id, 30)
    remaining = max(0, budget["monthly_limit_kg"] - spent)
    pct_used = (spent / budget["monthly_limit_kg"] * 100) if budget["monthly_limit_kg"] > 0 else 0
    days_in_month = 30
    days_passed = now.day
    daily_avg = spent / days_passed if days_passed > 0 else 0
    projected = daily_avg * days_in_month
    daily_budget = budget["monthly_limit_kg"] / days_in_month
    on_track = projected <= budget["monthly_limit_kg"]
    # Check alerts
    threshold = budget.get("alert_threshold_pct", 80)
    alerts_to_fire = []
    if pct_used >= 100:
        alerts_to_fire.append(("hard_cap", f"⛔ Carbon budget EXCEEDED! {spent:.1f}/{budget['monthly_limit_kg']:.1f} kg"))
    elif pct_used >= threshold:
        alerts_to_fire.append(("threshold", f"⚠️ Carbon budget at {pct_used:.0f}% — {remaining:.1f} kg remaining"))
    for atype, msg in alerts_to_fire:
        create_alert(user_id, budget["id"], atype, msg, pct_used)
    # Category status
    cat_status = {}
    cat_limits = budget.get("category_limits", {})
    for cat, limit in cat_limits.items():
        cat_spent = monthly_cat.get(cat, 0)
        cat_status[cat] = {
            "spent": cat_spent, "limit": limit,
            "pct": round((cat_spent / limit * 100), 1) if limit > 0 else 0,
            "remaining": max(0, limit - cat_spent),
            "status": "over" if cat_spent > limit else "warning" if cat_spent > limit * 0.8 else "ok",
        }
    return {
        "has_budget": True, "budget": budget,
        "monthly_spent": spent, "monthly_limit": budget["monthly_limit_kg"],
        "remaining": round(remaining, 2), "pct_used": round(pct_used, 1),
        "daily_avg": round(daily_avg, 2), "projected_month": round(projected, 2),
        "daily_budget": round(daily_budget, 2), "on_track": on_track,
        "category_breakdown": monthly_cat, "category_status": cat_status,
        "daily_history": daily,
    }

# ── Spending ───────────────────────────────────────────────────────────

def add_spending(user_id: int, category: str, activity: str, co2_kg: float,
                  log_date: Optional[str] = None) -> Dict[str, Any]:
    budget = get_active_budget(user_id)
    budget_id = budget["id"] if budget else None
    lid = log_spending(user_id, category, activity, co2_kg, budget_id=budget_id, log_date=log_date)
    # Re-check alerts after spending
    if budget:
        spent = get_total_monthly_spent(user_id)
        pct = (spent / budget["monthly_limit_kg"] * 100) if budget["monthly_limit_kg"] > 0 else 0
        threshold = budget.get("alert_threshold_pct", 80)
        if pct >= 100:
            create_alert(user_id, budget["id"], "hard_cap",
                         f"⛔ Budget EXCEEDED after logging {co2_kg:.1f} kg for '{activity}'! Total: {spent:.1f}/{budget['monthly_limit_kg']:.1f} kg", pct)
        elif pct >= threshold:
            create_alert(user_id, budget["id"], "threshold",
                         f"⚠️ At {pct:.0f}% after logging '{activity}'. {budget['monthly_limit_kg'] - spent:.1f} kg remaining.", pct)
    return {"success": True, "log_id": lid}

def quick_log(user_id: int, category: str, activity: str) -> Dict[str, Any]:
    db = ACTIVITY_CO2_DATABASE.get(category, {})
    if activity in db:
        return add_spending(user_id, category, activity, db[activity])
    return {"success": False, "error": f"Activity '{activity}' not found in {category}"}

# ── Projections ────────────────────────────────────────────────────────

def get_projection(user_id: int) -> Dict[str, Any]:
    now = datetime.utcnow()
    days_passed = now.day
    days_in_month = 30
    spent = get_total_monthly_spent(user_id, now.year, now.month)
    daily_avg = spent / days_passed if days_passed > 0 else 0
    projected = daily_avg * days_in_month
    budget = get_active_budget(user_id)
    limit = budget["monthly_limit_kg"] if budget else 500.0
    saving_needed = max(0, projected - limit) / max(1, days_in_month - days_passed) if days_passed < days_in_month else 0
    days_until_exceed = max(0, int((limit - spent) / daily_avg)) if daily_avg > 0 else 999
    return {
        "daily_avg": round(daily_avg, 2),
        "projected_total": round(projected, 2),
        "limit": limit,
        "will_exceed": projected > limit,
        "daily_saving_needed": round(saving_needed, 2),
        "days_until_exceed": days_until_exceed,
        "days_remaining": days_in_month - days_passed,
    }

def get_category_suggestions(user_id: int) -> List[Dict[str, Any]]:
    summary = get_budget_summary(user_id)
    suggestions = []
    cat_status = summary.get("category_status", {})
    tips = {
        "transport": "Consider cycling, carpooling, or public transit 2 days/week to save ~15 kg CO₂/month.",
        "energy": "Switch to LED bulbs, unplug idle devices, and lower thermostat by 2°C to save ~20 kg CO₂/month.",
        "diet": "Replace 3 meat meals/week with plant-based alternatives to save ~12 kg CO₂/month.",
        "flights": "Choose train for trips under 600km — saves up to 80% emissions vs flying.",
        "shopping": "Buy second-hand or repair instead of replacing — saves ~5 kg CO₂ per item.",
        "waste": "Start composting food scraps — reduces waste emissions by ~40%.",
        "water": "Shorter showers (5 min) and cold-water laundry save ~3 kg CO₂/month.",
        "digital": "Stream in standard definition and close unused tabs — small savings add up.",
    }
    for cat, status in cat_status.items():
        if status["status"] in ("over", "warning"):
            suggestions.append({
                "category": cat, "severity": "high" if status["status"] == "over" else "medium",
                "spent": status["spent"], "limit": status["limit"], "pct": status["pct"],
                "tip": tips.get(cat, "Reduce usage in this category to stay within budget."),
            })
    suggestions.sort(key=lambda x: x["pct"], reverse=True)
    return suggestions

def get_savings_tips(category: str) -> List[str]:
    tips_db = {
        "transport": ["Carpool with colleagues 2x/week", "Use an e-bike for short commutes", "Work from home when possible",
                       "Combine errands into single trips", "Use route optimization apps"],
        "energy": ["Set AC to 24°C in summer", "Use smart power strips", "Air-dry clothes instead of dryer",
                    "Insulate water heater", "Use ceiling fans over AC"],
        "diet": ["Meatless Mondays", "Buy local seasonal produce", "Reduce food waste with meal planning",
                  "Grow herbs at home", "Choose organic when possible"],
        "flights": ["Take trains for <600km trips", "Use video calls instead", "Offset remaining flight emissions",
                     "Choose direct flights", "Pack light to reduce fuel"],
        "shopping": ["Buy quality items that last", "Repair before replacing", "Use clothing swaps",
                      "Choose minimal packaging", "Borrow instead of buy"],
        "waste": ["Start composting", "Use reusable bags and containers", "Buy in bulk",
                   "Refuse single-use plastics", "Recycle electronics properly"],
        "water": ["Install low-flow showerhead", "Fix leaky faucets", "Use rain barrels for garden",
                   "Collect cold-water while waiting for hot", "Water garden in morning"],
        "digital": ["Stream in 720p instead of 4K", "Delete old cloud files", "Use ad blockers to reduce data",
                     "Unsubscribe from email lists", "Use dark mode on OLED screens"],
    }
    return tips_db.get(category, ["Stay mindful of your usage in this area."])
