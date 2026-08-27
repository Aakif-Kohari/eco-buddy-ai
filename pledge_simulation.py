"""
Pledge Simulation Lab
======================
What-if scenarios, carbon budget simulation, strategy comparison,
pledge portfolio optimisation, seasonal projections, and long-term
impact modelling for green pledges.

Dependencies: green_pledge_tracker, pledge_impact_engine, database_connection.
"""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from database_connection import database_connection
from green_pledge_tracker import (
    DB_NAME,
    PLEDGE_CATEGORIES,
    PledgeDifficulty,
    PledgeTemplate,
    current_week_start,
    current_week_end,
    get_all_templates,
    get_template_by_id,
    get_user_all_pledges,
    get_user_pledge_stats,
    estimate_co2_equivalents,
    weeks_between,
)
from pledge_impact_engine import (
    get_weekly_impacts,
    analyse_trend,
    predict_future_impact,
    MILESTONE_DEFINITIONS,
)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

DEFAULT_BUDGET_TARGET_KG = 2000.0  # Annual CO₂ budget target (kg)
WEEKS_PER_YEAR = 52
MONTHS_PER_YEAR = 12
DAYS_PER_YEAR = 365

SCENARIO_PRESETS = {
    "conservative": {
        "title": "🐢 Conservative",
        "description": "Slow and steady — 1 easy pledge per week, minimal lifestyle change.",
        "pledges_per_week": 1,
        "difficulty_mix": {"easy": 0.7, "medium": 0.25, "hard": 0.05},
        "completion_rate": 0.70,
        "checkin_probability": 0.6,
    },
    "balanced": {
        "title": "⚖️ Balanced",
        "description": "Moderate effort — 2-3 mixed pledges, consistent check-ins.",
        "pledges_per_week": 2.5,
        "difficulty_mix": {"easy": 0.4, "medium": 0.4, "hard": 0.2},
        "completion_rate": 0.80,
        "checkin_probability": 0.75,
    },
    "aggressive": {
        "title": "🚀 Aggressive",
        "description": "All-in approach — 3+ pledges, hard difficulty, daily check-ins.",
        "pledges_per_week": 4,
        "difficulty_mix": {"easy": 0.2, "medium": 0.3, "hard": 0.5},
        "completion_rate": 0.85,
        "checkin_probability": 0.90,
    },
    "minimal": {
        "title": "🌱 Minimal",
        "description": "Just starting out — 1 very easy pledge, building the habit.",
        "pledges_per_week": 1,
        "difficulty_mix": {"easy": 1.0, "medium": 0.0, "hard": 0.0},
        "completion_rate": 0.90,
        "checkin_probability": 0.5,
    },
    "diverse": {
        "title": "🌈 Diverse",
        "description": "Try everything — one pledge from each category.",
        "pledges_per_week": 3,
        "difficulty_mix": {"easy": 0.33, "medium": 0.34, "hard": 0.33},
        "completion_rate": 0.75,
        "checkin_probability": 0.70,
    },
}

SEASONAL_FACTORS = {
    "spring": {"energy": 0.9, "transport": 1.0, "diet": 1.0, "waste": 0.95, "water": 0.9, "lifestyle": 1.1},
    "summer": {"energy": 1.1, "transport": 0.95, "diet": 1.0, "waste": 1.0, "water": 1.2, "lifestyle": 1.15},
    "autumn": {"energy": 1.0, "transport": 1.0, "diet": 1.0, "waste": 1.0, "water": 0.95, "lifestyle": 1.0},
    "winter": {"energy": 1.2, "transport": 0.9, "diet": 0.95, "waste": 1.05, "water": 0.85, "lifestyle": 0.9},
}

DIFFICULTY_MULTIPLIERS = {
    "easy": 1.0,
    "medium": 1.5,
    "hard": 2.5,
}


class SimulationType(str, Enum):
    WHAT_IF = "what_if"
    STRATEGY_COMPARE = "strategy_compare"
    CARBON_BUDGET = "carbon_budget"
    PORTFOLIO_OPTIMISE = "portfolio_optimise"
    SEASONAL = "seasonal"
    LONG_TERM = "long_term"


# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────

@dataclass
class SimulationResult:
    """Result of a simulation run."""
    simulation_id: str
    simulation_type: str
    user_id: int
    title: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    projections: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    created_at: str = ""


@dataclass
class WhatIfScenario:
    """A what-if scenario for changing pledge behaviour."""
    scenario_id: str
    name: str
    current_weekly_co2_kg: float
    simulated_weekly_co2_kg: float
    weekly_delta_kg: float
    annual_delta_kg: float
    pledges_added: list[dict[str, Any]] = field(default_factory=list)
    pledges_removed: list[dict[str, Any]] = field(default_factory=list)
    completion_rate_change: float = 0.0
    xp_change: int = 0
    equivalent_change: str = ""


@dataclass
class CarbonBudget:
    """Carbon budget simulation."""
    budget_id: str
    user_id: int
    annual_target_kg: float
    current_annual_usage_kg: float
    remaining_budget_kg: float
    weeks_left: int
    weekly_allowance_kg: float
    on_track: bool
    projected_annual_kg: float
    surplus_deficit_kg: float
    burn_rate_per_week: float
    recommendations: list[str] = field(default_factory=list)


@dataclass
class StrategyComparison:
    """Comparison of different pledge strategies."""
    comparison_id: str
    strategies: list[dict[str, Any]] = field(default_factory=list)
    best_for_co2: str = ""
    best_for_xp: str = ""
    best_for_ease: str = ""
    recommendation: str = ""


@dataclass
class PortfolioOptimiser:
    """Optimal pledge portfolio for a given budget/effort."""
    portfolio_id: str
    effort_budget: int  # max pledges
    difficulty_budget: str  # max difficulty level
    selected_pledges: list[dict[str, Any]] = field(default_factory=list)
    total_weekly_co2_kg: float = 0.0
    total_weekly_xp: int = 0
    total_effort: float = 0.0
    efficiency_score: float = 0.0  # co2 per effort unit
    coverage_categories: list[str] = field(default_factory=list)


@dataclass
class SeasonalProjection:
    """Seasonal impact projection."""
    projection_id: str
    season: str
    year: int
    category_projections: list[dict[str, Any]] = field(default_factory=list)
    total_projected_co2_kg: float = 0.0
    seasonal_factor: float = 1.0
    notes: list[str] = field(default_factory=list)


@dataclass
class LongTermProjection:
    """Long-term (1-5 year) impact projection."""
    projection_id: str
    years: int
    annual_projections: list[dict[str, Any]] = field(default_factory=list)
    cumulative_co2_kg: float = 0.0
    cumulative_xp: int = 0
    equivalent_trees: float = 0.0
    equivalent_car_km: float = 0.0
    milestone_projection: list[dict[str, Any]] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────

def init_simulation_tables() -> None:
    """Create simulation tables."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                id              TEXT PRIMARY KEY,
                user_id         INTEGER NOT NULL,
                simulation_type TEXT NOT NULL,
                title           TEXT NOT NULL,
                description     TEXT DEFAULT '',
                parameters      TEXT DEFAULT '{}',
                projections     TEXT DEFAULT '[]',
                summary         TEXT DEFAULT '{}',
                recommendations TEXT DEFAULT '[]',
                created_at      TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carbon_budgets (
                id              TEXT PRIMARY KEY,
                user_id         INTEGER NOT NULL,
                target_kg       REAL NOT NULL,
                current_usage   REAL DEFAULT 0.0,
                created_at      TEXT NOT NULL,
                updated_at      TEXT DEFAULT ''
            )
        """)
        conn.commit()


# ──────────────────────────────────────────────────────────────────────
# What-if scenario engine
# ──────────────────────────────────────────────────────────────────────

def run_what_if(
    user_id: int,
    add_pledges: list[str] | None = None,
    remove_pledges: list[str] | None = None,
    completion_rate_change: float = 0.0,
    weeks: int = 12,
) -> WhatIfScenario:
    """Run a what-if scenario: add/remove pledges and see projected impact."""
    stats = get_user_pledge_stats(user_id)
    weekly = get_weekly_impacts(user_id, weeks=4)
    current_co2 = sum(w.co2_saved_kg for w in weekly) / max(len(weekly), 1)

    simulated_co2 = current_co2
    added_info: list[dict[str, Any]] = []
    removed_info: list[dict[str, Any]] = []

    # Add pledges
    if add_pledges:
        for tpl_id in add_pledges:
            tpl = get_template_by_id(tpl_id)
            if tpl:
                simulated_co2 += tpl.weekly_co2_saved_kg
                added_info.append({
                    "template_id": tpl_id,
                    "title": tpl.title,
                    "category": tpl.category,
                    "weekly_co2_kg": tpl.weekly_co2_saved_kg,
                    "xp_reward": tpl.xp_reward,
                })

    # Remove pledges
    if remove_pledges:
        for tpl_id in remove_pledges:
            tpl = get_template_by_id(tpl_id)
            if tpl:
                simulated_co2 = max(0, simulated_co2 - tpl.weekly_co2_saved_kg)
                removed_info.append({
                    "template_id": tpl_id,
                    "title": tpl.title,
                    "weekly_co2_kg": tpl.weekly_co2_saved_kg,
                })

    # Apply completion rate change
    if completion_rate_change != 0:
        simulated_co2 *= (1.0 + completion_rate_change)

    weekly_delta = simulated_co2 - current_co2
    annual_delta = weekly_delta * WEEKS_PER_YEAR

    # Equivalents
    eq = estimate_co2_equivalents(abs(annual_delta))
    equivalent = f"{eq['car_km']:.0f} km of driving" if annual_delta > 0 else f"{eq['car_km']:.0f} km more driving"

    return WhatIfScenario(
        scenario_id=str(uuid.uuid4())[:10],
        name=f"Add {len(add_pledges or [])} / Remove {len(remove_pledges or [])}",
        current_weekly_co2_kg=round(current_co2, 2),
        simulated_weekly_co2_kg=round(max(0, simulated_co2), 2),
        weekly_delta_kg=round(weekly_delta, 2),
        annual_delta_kg=round(annual_delta, 2),
        pledges_added=added_info,
        pledges_removed=removed_info,
        completion_rate_change=completion_rate_change,
        xp_change=sum(p.get("xp_reward", 0) for p in added_info),
        equivalent_change=equivalent,
    )


# ──────────────────────────────────────────────────────────────────────
# Carbon budget simulator
# ──────────────────────────────────────────────────────────────────────

def simulate_carbon_budget(
    user_id: int,
    annual_target_kg: float = DEFAULT_BUDGET_TARGET_KG,
) -> CarbonBudget:
    """Simulate a carbon budget for the user."""
    stats = get_user_pledge_stats(user_id)
    weekly = get_weekly_impacts(user_id, weeks=WEEKS_PER_YEAR)
    now = datetime.now()
    week_of_year = now.isocalendar()[1]
    weeks_left = max(1, WEEKS_PER_YEAR - week_of_year)

    # Estimate current annual usage (extrapolate from data)
    active_weeks = [w for w in weekly if w.pledges_enrolled > 0]
    if active_weeks:
        avg_weekly_co2 = sum(w.co2_saved_kg for w in active_weeks) / len(active_weeks)
        weeks_with_data = len(weekly)
        current_usage = avg_weekly_co2 * weeks_with_data
    else:
        avg_weekly_co2 = 0.0
        current_usage = 0.0

    remaining = max(0, annual_target_kg - current_usage)
    weekly_allowance = remaining / max(weeks_left, 1)
    on_track = current_usage <= (annual_target_kg * week_of_year / WEEKS_PER_YEAR)
    projected = avg_weekly_co2 * WEEKS_PER_YEAR
    surplus = projected - annual_target_kg
    burn_rate = avg_weekly_co2

    recommendations: list[str] = []
    if not on_track:
        recommendations.append("⚠️ You're behind your CO₂ target. Consider adding more pledges.")
        deficit_per_week = (annual_target_kg * week_of_year / WEEKS_PER_YEAR - current_usage) / max(weeks_left, 1)
        recommendations.append(f"📊 You need to save ~{deficit_per_week:.1f} extra kg CO₂/week to catch up.")
    else:
        recommendations.append("✅ You're on track! Keep up the great work.")
        if surplus < 0:
            recommendations.append(f"🎯 At this pace, you'll save {abs(surplus):.1f} kg under your budget.")

    if weekly_allowance < 2.0:
        recommendations.append("💡 Focus on high-impact pledges (transport, energy) to maximize your budget.")
    else:
        recommendations.append(f"📊 Your weekly allowance is {weekly_allowance:.1f} kg CO₂ — you have room for variety.")

    return CarbonBudget(
        budget_id=str(uuid.uuid4())[:10],
        user_id=user_id,
        annual_target_kg=annual_target_kg,
        current_annual_usage_kg=round(current_usage, 2),
        remaining_budget_kg=round(remaining, 2),
        weeks_left=weeks_left,
        weekly_allowance_kg=round(weekly_allowance, 2),
        on_track=on_track,
        projected_annual_kg=round(projected, 2),
        surplus_deficit_kg=round(surplus, 2),
        burn_rate_per_week=round(burn_rate, 2),
        recommendations=recommendations,
    )


# ──────────────────────────────────────────────────────────────────────
# Strategy comparison
# ──────────────────────────────────────────────────────────────────────

def compare_strategies(user_id: int, weeks: int = 52) -> StrategyComparison:
    """Compare different pledge strategies side by side."""
    templates = get_all_templates()
    results: list[dict[str, Any]] = []

    for preset_key, preset in SCENARIO_PRESETS.items():
        # Simulate each strategy
        weekly_co2 = 0.0
        weekly_xp = 0
        effort = 0.0

        # Select pledges based on difficulty mix
        for diff, fraction in preset["difficulty_mix"].items():
            pool = [t for t in templates if t.difficulty == diff]
            n = max(1, int(preset["pledges_per_week"] * fraction))
            selected = pool[:n]

            for t in selected:
                weekly_co2 += t.weekly_co2_saved_kg * preset["completion_rate"]
                weekly_xp += int(t.xp_reward * preset["completion_rate"])
                effort += DIFFICULTY_MULTIPLIERS.get(diff, 1.0)

        annual_co2 = weekly_co2 * WEEKS_PER_YEAR
        annual_xp = weekly_xp * WEEKS_PER_YEAR
        efficiency = weekly_co2 / max(effort, 0.1)

        results.append({
            "strategy": preset_key,
            "title": preset["title"],
            "description": preset["description"],
            "pledges_per_week": preset["pledges_per_week"],
            "weekly_co2_kg": round(weekly_co2, 2),
            "annual_co2_kg": round(annual_co2, 1),
            "weekly_xp": weekly_xp,
            "annual_xp": annual_xp,
            "effort": round(effort, 1),
            "efficiency": round(efficiency, 2),
            "completion_rate": preset["completion_rate"],
        })

    # Find bests
    best_co2 = max(results, key=lambda r: r["annual_co2_kg"])
    best_xp = max(results, key=lambda r: r["annual_xp"])
    best_ease = max(results, key=lambda r: r["efficiency"])

    # Recommendation
    stats = get_user_pledge_stats(user_id)
    if stats.total_pledges_completed == 0:
        rec = "Start with the 🌱 Minimal strategy to build the habit first."
    elif stats.completion_rate_pct < 60:
        rec = "Focus on the 🐢 Conservative strategy to improve your completion rate."
    elif stats.current_streak >= 6:
        rec = "You're ready for the 🚀 Aggressive strategy — your consistency is strong!"
    else:
        rec = "The ⚖️ Balanced strategy is a great fit for your current level."

    return StrategyComparison(
        comparison_id=str(uuid.uuid4())[:10],
        strategies=results,
        best_for_co2=best_co2["strategy"],
        best_for_xp=best_xp["strategy"],
        best_for_ease=best_ease["strategy"],
        recommendation=rec,
    )


# ──────────────────────────────────────────────────────────────────────
# Portfolio optimiser
# ──────────────────────────────────────────────────────────────────────

def optimise_portfolio(
    user_id: int,
    effort_budget: int = 3,
    difficulty_budget: str = "medium",
) -> PortfolioOptimiser:
    """Find the optimal pledge portfolio within effort constraints."""
    templates = get_all_templates()
    stats = get_user_pledge_stats(user_id)

    # Filter by difficulty constraint
    max_difficulty = {"easy": 1, "medium": 2, "hard": 3}.get(difficulty_budget, 2)
    eligible = [
        t for t in templates
        if {"easy": 1, "medium": 2, "hard": 3}.get(t.difficulty, 1) <= max_difficulty
    ]

    # Sort by CO₂ savings per effort unit (greedy knapsack)
    scored = []
    for t in eligible:
        effort = DIFFICULTY_MULTIPLIERS.get(PledgeDifficulty(t.difficulty), 1.0)
        score = t.weekly_co2_saved_kg / max(effort, 0.1)
        scored.append((score, t))
    scored.sort(key=lambda x: x[0], reverse=True)

    # Greedy selection
    selected: list[dict[str, Any]] = []
    total_effort = 0.0
    total_co2 = 0.0
    total_xp = 0
    used_categories: set[str] = set()

    for score, t in scored:
        effort = DIFFICULTY_MULTIPLIERS.get(PledgeDifficulty(t.difficulty), 1.0)
        if total_effort + effort <= effort_budget:
            selected.append({
                "template_id": t.id,
                "title": t.title,
                "category": t.category,
                "difficulty": t.difficulty,
                "weekly_co2_kg": t.weekly_co2_saved_kg,
                "xp_reward": t.xp_reward,
                "effort": effort,
                "score": round(score, 2),
            })
            total_effort += effort
            total_co2 += t.weekly_co2_saved_kg
            total_xp += t.xp_reward
            used_categories.add(t.category)

    efficiency = total_co2 / max(total_effort, 0.1)

    return PortfolioOptimiser(
        portfolio_id=str(uuid.uuid4())[:10],
        effort_budget=effort_budget,
        difficulty_budget=difficulty_budget,
        selected_pledges=selected,
        total_weekly_co2_kg=round(total_co2, 2),
        total_weekly_xp=total_xp,
        total_effort=round(total_effort, 1),
        efficiency_score=round(efficiency, 2),
        coverage_categories=sorted(used_categories),
    )


# ──────────────────────────────────────────────────────────────────────
# Seasonal projection
# ──────────────────────────────────────────────────────────────────────

def project_seasonal_impact(
    user_id: int,
    year: int | None = None,
) -> list[SeasonalProjection]:
    """Project seasonal impact based on historical patterns and seasonal factors."""
    year = year or datetime.now().year
    weekly = get_weekly_impacts(user_id, weeks=WEEKS_PER_YEAR)
    templates = get_all_templates()

    # Determine which templates the user typically uses
    user_templates: set[str] = set()
    for w in weekly:
        for cat in w.categories_touched:
            for t in templates:
                if t.category == cat:
                    user_templates.add(t.id)

    projections: list[SeasonalProjection] = []

    for season, factors in SEASONAL_FACTORS.items():
        cat_projections: list[dict[str, Any]] = []
        total_co2 = 0.0

        for cat, factor in factors.items():
            cat_templates = [t for t in templates if t.category == cat and t.id in user_templates]
            if not cat_templates:
                cat_templates = [t for t in templates if t.category == cat][:2]

            weekly_co2 = sum(t.weekly_co2_saved_kg for t in cat_templates[:2]) * factor
            seasonal_co2 = weekly_co2 * 13  # ~13 weeks per season

            cat_projections.append({
                "category": cat,
                "label": PLEDGE_CATEGORIES.get(cat, {}).get("label", cat),
                "seasonal_factor": factor,
                "weekly_co2_kg": round(weekly_co2, 2),
                "seasonal_co2_kg": round(seasonal_co2, 1),
            })
            total_co2 += seasonal_co2

        avg_factor = sum(factors.values()) / len(factors)

        notes: list[str] = []
        if season == "winter":
            notes.append("💡 Energy pledges have higher impact in winter (heating).")
        elif season == "summer":
            notes.append("💧 Water pledges matter more in summer (gardening, cooling).")
        elif season == "spring":
            notes.append("🌿 Lifestyle pledges peak in spring (outdoor activities).")

        projections.append(SeasonalProjection(
            projection_id=str(uuid.uuid4())[:8],
            season=season,
            year=year,
            category_projections=cat_projections,
            total_projected_co2_kg=round(total_co2, 1),
            seasonal_factor=round(avg_factor, 3),
            notes=notes,
        ))

    return projections


# ──────────────────────────────────────────────────────────────────────
# Long-term projection
# ──────────────────────────────────────────────────────────────────────

def project_long_term(
    user_id: int,
    years: int = 3,
    strategy: str = "balanced",
) -> LongTermProjection:
    """Project impact over multiple years."""
    stats = get_user_pledge_stats(user_id)
    prediction = predict_future_impact(user_id)

    preset = SCENARIO_PRESETS.get(strategy, SCENARIO_PRESETS["balanced"])
    templates = get_all_templates()

    # Calculate weekly CO₂ for this strategy
    weekly_co2 = 0.0
    weekly_xp = 0
    for diff, fraction in preset["difficulty_mix"].items():
        pool = [t for t in templates if t.difficulty == diff]
        n = max(1, int(preset["pledges_per_week"] * fraction))
        for t in pool[:n]:
            weekly_co2 += t.weekly_co2_saved_kg * preset["completion_rate"]
            weekly_xp += int(t.xp_reward * preset["completion_rate"])

    # Apply growth factor (users tend to improve over time)
    growth_factor = 1.05  # 5% improvement per year

    annual_projections: list[dict[str, Any]] = []
    cumulative_co2 = 0.0
    cumulative_xp = 0

    for year_num in range(1, years + 1):
        year_factor = growth_factor ** (year_num - 1)
        annual_co2 = weekly_co2 * WEEKS_PER_YEAR * year_factor
        annual_xp = int(weekly_xp * WEEKS_PER_YEAR * year_factor)
        cumulative_co2 += annual_co2
        cumulative_xp += annual_xp

        annual_projections.append({
            "year": year_num,
            "annual_co2_kg": round(annual_co2, 1),
            "annual_xp": annual_xp,
            "cumulative_co2_kg": round(cumulative_co2, 1),
            "cumulative_xp": cumulative_xp,
            "growth_factor": round(year_factor, 3),
        })

    # Equivalents
    eq_total = estimate_co2_equivalents(cumulative_co2)

    # Milestone projection
    milestone_proj: list[dict[str, Any]] = []
    co2_milestones = [
        (10, "🌍 10 kg CO₂ Saved"),
        (50, "🌎 50 kg CO₂ Saved"),
        (100, "🌐 100 kg CO₂ Saved"),
        (500, "🏔️ 500 kg CO₂ Saved"),
        (1000, "🌟 1,000 kg CO₂ Saved"),
    ]
    for threshold, label in co2_milestones:
        weeks_to_reach = math.ceil(threshold / max(weekly_co2, 0.01))
        years_to_reach = weeks_to_reach / WEEKS_PER_YEAR
        milestone_proj.append({
            "milestone": label,
            "threshold_kg": threshold,
            "weeks_to_reach": weeks_to_reach,
            "years_to_reach": round(years_to_reach, 1),
        })

    return LongTermProjection(
        projection_id=str(uuid.uuid4())[:10],
        years=years,
        annual_projections=annual_projections,
        cumulative_co2_kg=round(cumulative_co2, 1),
        cumulative_xp=cumulative_xp,
        equivalent_trees=eq_total["trees_needed"],
        equivalent_car_km=eq_total["car_km"],
        milestone_projection=milestone_proj,
    )


# ──────────────────────────────────────────────────────────────────────
# Full simulation runner
# ──────────────────────────────────────────────────────────────────────

def run_simulation(
    user_id: int,
    sim_type: str,
    parameters: dict[str, Any] | None = None,
) -> SimulationResult:
    """Run a simulation of the specified type."""
    params = parameters or {}
    result = SimulationResult(
        simulation_id=str(uuid.uuid4())[:10],
        simulation_type=sim_type,
        user_id=user_id,
        title="",
        description="",
        parameters=params,
        created_at=datetime.now().isoformat(timespec="seconds"),
    )

    if sim_type == SimulationType.WHAT_IF:
        scenario = run_what_if(
            user_id,
            add_pledges=params.get("add_pledges"),
            remove_pledges=params.get("remove_pledges"),
            completion_rate_change=params.get("completion_rate_change", 0.0),
        )
        result.title = f"What If: {scenario.name}"
        result.description = (
            f"Current: {scenario.current_weekly_co2_kg:.1f} kg/week → "
            f"Simulated: {scenario.simulated_weekly_co2_kg:.1f} kg/week "
            f"(Δ {scenario.weekly_delta_kg:+.1f} kg/week)"
        )
        result.projections = [
            {"week": i + 1, "co2_kg": round(scenario.simulated_weekly_co2_kg * (i + 1) / 4, 1)}
            for i in range(12)
        ]
        result.summary = asdict(scenario)
        result.recommendations = [
            f"Annual impact: {scenario.annual_delta_kg:+.1f} kg CO₂",
            f"XP change: {scenario.xp_change:+d}",
        ]

    elif sim_type == SimulationType.STRATEGY_COMPARE:
        comparison = compare_strategies(user_id)
        result.title = "Strategy Comparison"
        result.description = "Comparing 5 different pledge strategies side by side."
        result.projections = comparison.strategies
        result.summary = {
            "best_co2": comparison.best_for_co2,
            "best_xp": comparison.best_for_xp,
            "best_ease": comparison.best_for_ease,
        }
        result.recommendations = [comparison.recommendation]

    elif sim_type == SimulationType.CARBON_BUDGET:
        target = params.get("annual_target_kg", DEFAULT_BUDGET_TARGET_KG)
        budget = simulate_carbon_budget(user_id, annual_target_kg=target)
        result.title = f"Carbon Budget: {target:.0f} kg Target"
        result.description = f"Remaining: {budget.remaining_budget_kg:.1f} kg | {budget.weeks_left} weeks left"
        result.summary = asdict(budget)
        result.recommendations = budget.recommendations

    elif sim_type == SimulationType.PORTFOLIO_OPTIMISE:
        effort = params.get("effort_budget", 3)
        diff = params.get("difficulty_budget", "medium")
        portfolio = optimise_portfolio(user_id, effort_budget=effort, difficulty_budget=diff)
        result.title = f"Optimal Portfolio ({effort} effort, {diff} difficulty)"
        result.description = f"{len(portfolio.selected_pledges)} pledges selected, {portfolio.total_weekly_co2_kg:.1f} kg CO₂/week"
        result.projections = portfolio.selected_pledges
        result.summary = {
            "total_co2_kg": portfolio.total_weekly_co2_kg,
            "total_xp": portfolio.total_weekly_xp,
            "efficiency": portfolio.efficiency_score,
            "categories": portfolio.coverage_categories,
        }

    elif sim_type == SimulationType.SEASONAL:
        projections = project_seasonal_impact(user_id)
        result.title = "Seasonal Impact Projection"
        result.description = "How your impact varies across seasons."
        result.projections = [asdict(p) for p in projections]
        result.summary = {"total_annual_projected": sum(p.total_projected_co2_kg for p in projections)}

    elif sim_type == SimulationType.LONG_TERM:
        yrs = params.get("years", 3)
        strat = params.get("strategy", "balanced")
        lt = project_long_term(user_id, years=yrs, strategy=strat)
        result.title = f"Long-Term Projection ({yrs} years, {strat})"
        result.description = f"Cumulative: {lt.cumulative_co2_kg:.1f} kg CO₂ over {yrs} years"
        result.projections = lt.annual_projections
        result.summary = {
            "cumulative_co2_kg": lt.cumulative_co2_kg,
            "cumulative_xp": lt.cumulative_xp,
            "trees": lt.equivalent_trees,
            "car_km": lt.equivalent_car_km,
        }
        result.recommendations = [
            f"Over {yrs} years, you could save {lt.cumulative_co2_kg:.1f} kg CO₂.",
            f"That's equivalent to {lt.equivalent_trees:.0f} trees or {lt.equivalent_car_km:.0f} km of driving.",
        ]

    # Persist
    _save_simulation(result)
    return result


# ──────────────────────────────────────────────────────────────────────
# Simulation history
# ──────────────────────────────────────────────────────────────────────

def get_simulation_history(user_id: int, limit: int = 20) -> list[SimulationResult]:
    """Retrieve past simulation runs."""
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM simulation_runs WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))
        return [_row_to_simulation(dict(r)) for r in cur.fetchall()]


def _save_simulation(result: SimulationResult) -> None:
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO simulation_runs
                (id, user_id, simulation_type, title, description,
                 parameters, projections, summary, recommendations, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.simulation_id, result.user_id, result.simulation_type,
            result.title, result.description,
            json.dumps(result.parameters, default=str),
            json.dumps(result.projections, default=str),
            json.dumps(result.summary, default=str),
            json.dumps(result.recommendations),
            result.created_at,
        ))
        conn.commit()


def _row_to_simulation(row: dict) -> SimulationResult:
    return SimulationResult(
        simulation_id=row["id"],
        user_id=row["user_id"],
        simulation_type=row["simulation_type"],
        title=row["title"],
        description=row["description"],
        parameters=json.loads(row.get("parameters", "{}")),
        projections=json.loads(row.get("projections", "[]")),
        summary=json.loads(row.get("summary", "{}")),
        recommendations=json.loads(row.get("recommendations", "[]")),
        created_at=row.get("created_at", ""),
    )


def simulation_to_dict(s: SimulationResult) -> dict[str, Any]:
    return asdict(s)


def export_simulations_json(user_id: int) -> str:
    """Export all simulations as JSON."""
    sims = get_simulation_history(user_id, limit=50)
    return json.dumps([simulation_to_dict(s) for s in sims], indent=2, default=str)
