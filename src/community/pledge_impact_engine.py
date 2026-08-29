"""
Pledge Impact Engine
====================
Advanced analytics, trend analysis, predictive modelling, milestone
tracking, and personalised insight generation for green pledge data.

Dependencies: green_pledge_tracker, pledge_leaderboard, src.core.database_connection.
"""

from __future__ import annotations

import json
import math
import sqlite3
import statistics
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from src.core.database_connection import database_connection
from src.utils.green_pledge_tracker import (
    DB_NAME,
    PLEDGE_CATALOG,
    PLEDGE_CATEGORIES,
    PledgeTemplate,
    PledgeDifficulty,
    current_week_start,
    current_week_end,
    get_all_templates,
    get_template_by_id,
    get_user_all_pledges,
    get_user_pledge_stats,
    get_pledge_checkin_dates,
    weeks_between,
    estimate_co2_equivalents,
)
from src.community.pledge_leaderboard import (
    init_leaderboard_tables,
    get_user_groups,
    get_group_weekly_trend,
    get_group_members_leaderboard,
    get_leaderboard,
)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

TREND_WINDOW_WEEKS = 8
PREDICTION_WEEKS = 12
MOVING_AVERAGE_WINDOW = 4
INSIGHT_COOLDOWN_DAYS = 7

INSIGHT_CATEGORIES = {
    "streak": "🔥 Streak",
    "category": "📂 Category",
    "difficulty": "⚖️ Difficulty",
    "consistency": "📅 Consistency",
    "impact": "🌍 Impact",
    "social": "👥 Social",
    "opportunity": "💡 Opportunity",
    "milestone": "🏆 Milestone",
}


class InsightPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CELEBRATION = "celebration"


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    INSUFFICIENT = "insufficient_data"


class MilestoneType(str, Enum):
    FIRST_PLEDGE = "first_pledge"
    STREAK_3 = "streak_3_weeks"
    STREAK_6 = "streak_6_weeks"
    STREAK_12 = "streak_12_weeks"
    CO2_10 = "co2_10kg"
    CO2_50 = "co2_50kg"
    CO2_100 = "co2_100kg"
    CO2_500 = "co2_500kg"
    PLEDGES_5 = "pledges_5_completed"
    PLEDGES_10 = "pledges_10_completed"
    PLEDGES_25 = "pledges_25_completed"
    PLEDGES_50 = "pledges_50_completed"
    ALL_CATEGORIES = "all_categories_tried"
    PERFECT_WEEK = "perfect_week_7_7"
    HARD_PLEDGE = "hard_pledge_completed"
    DIVERSITY_3 = "diversity_3_categories"
    DIVERSITY_5 = "diversity_5_categories"
    WEEKEND_WARRIOR = "weekend_warrior"


MILESTONE_DEFINITIONS: dict[MilestoneType, dict[str, Any]] = {
    MilestoneType.FIRST_PLEDGE: {"title": "🌱 First Pledge", "description": "Completed your very first green pledge", "xp_bonus": 10},
    MilestoneType.STREAK_3: {"title": "⚡ 3-Week Streak", "description": "Maintained a 3-week completion streak", "xp_bonus": 30},
    MilestoneType.STREAK_6: {"title": "🌟 6-Week Streak", "description": "Maintained a 6-week completion streak", "xp_bonus": 75},
    MilestoneType.STREAK_12: {"title": "👑 Year-Round Warrior", "description": "Maintained a 12-week completion streak", "xp_bonus": 200},
    MilestoneType.CO2_10: {"title": "🌍 10 kg CO₂ Saved", "description": "Saved 10 kg of CO₂ through pledges", "xp_bonus": 20},
    MilestoneType.CO2_50: {"title": "🌎 50 kg CO₂ Saved", "description": "Saved 50 kg of CO₂ through pledges", "xp_bonus": 60},
    MilestoneType.CO2_100: {"title": "🌐 100 kg CO₂ Saved", "description": "Saved 100 kg of CO₂ through pledges", "xp_bonus": 120},
    MilestoneType.CO2_500: {"title": "🏔️ 500 kg CO₂ Saved", "description": "Saved 500 kg of CO₂ through pledges", "xp_bonus": 500},
    MilestoneType.PLEDGES_5: {"title": "🏅 5 Pledges Done", "description": "Completed 5 green pledges", "xp_bonus": 25},
    MilestoneType.PLEDGES_10: {"title": "🎯 10 Pledges Done", "description": "Completed 10 green pledges", "xp_bonus": 50},
    MilestoneType.PLEDGES_25: {"title": "💪 25 Pledges Done", "description": "Completed 25 green pledges", "xp_bonus": 100},
    MilestoneType.PLEDGES_50: {"title": "🏆 50 Pledges Done", "description": "Completed 50 green pledges", "xp_bonus": 250},
    MilestoneType.ALL_CATEGORIES: {"title": "🌈 Category Explorer", "description": "Completed pledges in every category", "xp_bonus": 80},
    MilestoneType.PERFECT_WEEK: {"title": "💎 Perfect Week", "description": "Completed all 7 days of a pledge", "xp_bonus": 15},
    MilestoneType.HARD_PLEDGE: {"title": "🔴 Hard Pledge Hero", "description": "Completed a hard-difficulty pledge", "xp_bonus": 40},
    MilestoneType.DIVERSITY_3: {"title": "🌿 Category Mixer", "description": "Active pledges in 3+ categories simultaneously", "xp_bonus": 20},
    MilestoneType.DIVERSITY_5: {"title": "🌳 Eco Polymath", "description": "Active pledges in 5+ categories simultaneously", "xp_bonus": 50},
    MilestoneType.WEEKEND_WARRIOR: {"title": "🏁 Weekend Warrior", "description": "Checked in on both Saturday and Sunday", "xp_bonus": 10},
}

# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────

@dataclass
class WeeklyImpact:
    week_start: str
    pledges_enrolled: int = 0
    pledges_completed: int = 0
    checkins: int = 0
    co2_saved_kg: float = 0.0
    xp_earned: int = 0
    eco_points_earned: int = 0
    categories_touched: list[str] = field(default_factory=list)
    difficulty_mix: dict[str, int] = field(default_factory=dict)


@dataclass
class TrendAnalysis:
    direction: str  # improving | stable | declining | insufficient_data
    confidence: float  # 0.0 – 1.0
    slope: float  # weekly change rate
    moving_average: list[float] = field(default_factory=list)
    forecast: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


@dataclass
class PredictionResult:
    predicted_co2_12w: float = 0.0
    predicted_xp_12w: int = 0
    predicted_pledges_12w: int = 0
    confidence_interval: dict[str, float] = field(default_factory=dict)
    scenario_better: dict[str, float] = field(default_factory=dict)
    scenario_worse: dict[str, float] = field(default_factory=dict)
    equivalents_12w: dict[str, Any] = field(default_factory=dict)


@dataclass
class Insight:
    insight_id: str
    category: str
    priority: str  # low | medium | high | celebration
    title: str
    body: str
    action_suggestion: str = ""
    metric_value: float = 0.0
    generated_at: str = ""


@dataclass
class Milestone:
    milestone_type: str
    title: str
    description: str
    achieved: bool
    achieved_at: str = ""
    xp_bonus: int = 0
    progress_pct: float = 0.0
    next_milestone: str = ""


@dataclass
class ComparisonReport:
    user_eco_score: float = 0.0
    community_avg_eco_score: float = 0.0
    percentile_rank: float = 0.0
    category_comparison: list[dict[str, Any]] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    improvement_areas: list[str] = field(default_factory=list)
    vs_community: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImpactReport:
    user_id: int
    generated_at: str = ""
    period_weeks: int = 0
    total_co2_saved_kg: float = 0.0
    total_xp: int = 0
    total_pledges_completed: int = 0
    total_checkins: int = 0
    avg_weekly_co2_kg: float = 0.0
    best_week: WeeklyImpact | None = None
    worst_week: WeeklyImpact | None = None
    trend: TrendAnalysis | None = None
    prediction: PredictionResult | None = None
    insights: list[Insight] = field(default_factory=list)
    milestones: list[Milestone] = field(default_factory=list)
    category_breakdown: list[dict[str, Any]] = field(default_factory=list)
    weekly_data: list[WeeklyImpact] = field(default_factory=list)


@dataclass
class CategoryBreakdown:
    category: str
    label: str
    color: str
    total_enrolled: int = 0
    total_completed: int = 0
    completion_rate: float = 0.0
    co2_saved_kg: float = 0.0
    avg_xp_per_pledge: float = 0.0
    favorite_pledge: str = ""


# ──────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────

def init_impact_tables() -> None:
    """Create tables for milestones and insights tracking."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_milestones (
                user_id         INTEGER NOT NULL,
                milestone_type  TEXT NOT NULL,
                achieved_at     TEXT NOT NULL,
                xp_bonus        INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, milestone_type)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_insights (
                id              TEXT PRIMARY KEY,
                user_id         INTEGER NOT NULL,
                category        TEXT NOT NULL,
                priority        TEXT DEFAULT 'medium',
                title           TEXT NOT NULL,
                body            TEXT DEFAULT '',
                action          TEXT DEFAULT '',
                metric_value    REAL DEFAULT 0.0,
                generated_at    TEXT NOT NULL,
                dismissed       INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS impact_reports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                report_data     TEXT NOT NULL,
                generated_at    TEXT NOT NULL
            )
        """)
        conn.commit()


# ──────────────────────────────────────────────────────────────────────
# Weekly impact aggregation
# ──────────────────────────────────────────────────────────────────────

def get_weekly_impacts(user_id: int, weeks: int = 26) -> list[WeeklyImpact]:
    """Build weekly impact summaries for the last N weeks."""
    stats = get_user_pledge_stats(user_id)
    all_pledges = get_user_all_pledges(user_id, limit=weeks * 10)

    # Group pledges by week
    week_map: dict[str, list] = defaultdict(list)
    for p in all_pledges:
        week_map[p.week_start].append(p)

    impacts: list[WeeklyImpact] = []
    now = datetime.now()

    for i in range(weeks - 1, -1, -1):
        d = now - timedelta(weeks=i)
        monday = d - timedelta(days=d.weekday())
        ws = monday.strftime("%Y-%m-%d")

        pledges = week_map.get(ws, [])
        enrolled = len(pledges)
        completed = sum(1 for p in pledges if p.status == "completed")
        checkins = sum(p.day_checkins for p in pledges)

        co2 = 0.0
        xp = 0
        eco_pts = 0
        categories = set()
        diff_mix: dict[str, int] = Counter()

        for p in pledges:
            tpl = get_template_by_id(p.template_id)
            if tpl:
                if p.status == "completed":
                    co2 += tpl.weekly_co2_saved_kg
                    xp += tpl.xp_reward
                    eco_pts += tpl.eco_points
                categories.add(tpl.category)
                diff_mix[tpl.difficulty] += 1

        impacts.append(WeeklyImpact(
            week_start=ws,
            pledges_enrolled=enrolled,
            pledges_completed=completed,
            checkins=checkins,
            co2_saved_kg=round(co2, 2),
            xp_earned=xp,
            eco_points_earned=eco_pts,
            categories_touched=sorted(categories),
            difficulty_mix=dict(diff_mix),
        ))

    return impacts


# ──────────────────────────────────────────────────────────────────────
# Trend analysis
# ──────────────────────────────────────────────────────────────────────

def analyse_trend(user_id: int, weeks: int = TREND_WINDOW_WEEKS) -> TrendAnalysis:
    """Analyse the trend of a user's pledge activity over time."""
    impacts = get_weekly_impacts(user_id, weeks=weeks + 2)

    # Use only weeks with at least some activity
    active_weeks = [w for w in impacts if w.pledges_enrolled > 0]

    if len(active_weeks) < 3:
        return TrendAnalysis(
            direction=TrendDirection.INSUFFICIENT,
            confidence=0.0,
            slope=0.0,
            summary="Not enough data to determine a trend. Keep pledging!",
        )

    values = [w.co2_saved_kg for w in active_weeks]
    n = len(values)

    # Simple linear regression
    x_vals = list(range(n))
    x_mean = sum(x_vals) / n
    y_mean = sum(values) / n
    ss_xy = sum((x_vals[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    ss_xx = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

    slope = ss_xy / ss_xx if ss_xx > 0 else 0.0

    # R² for confidence
    y_pred = [y_mean + slope * (x - x_mean) for x in x_vals]
    ss_res = sum((values[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    confidence = max(0.0, min(1.0, r_squared))

    # Direction
    if slope > 0.5:
        direction = TrendDirection.IMPROVING
        summary = f"Your CO₂ savings are increasing by ~{slope:.1f} kg/week. Great momentum!"
    elif slope < -0.5:
        direction = TrendDirection.DECLINING
        summary = f"Your CO₂ savings have dipped by ~{abs(slope):.1f} kg/week. Try enrolling in new pledges!"
    else:
        direction = TrendDirection.STABLE
        summary = "Your CO₂ savings are holding steady. Consider a harder pledge for a boost!"

    # Moving average
    ma_values = _moving_average(values, MOVING_AVERAGE_WINDOW)

    # Simple forecast (extrapolate trend line)
    forecast = []
    for j in range(1, PREDICTION_WEEKS + 1):
        predicted = max(0, y_mean + slope * (n + j - 1 - x_mean))
        forecast.append({
            "week_offset": j,
            "predicted_co2_kg": round(predicted, 2),
        })

    return TrendAnalysis(
        direction=direction,
        confidence=round(confidence, 3),
        slope=round(slope, 3),
        moving_average=[round(v, 2) for v in ma_values],
        forecast=forecast,
        summary=summary,
    )


# ──────────────────────────────────────────────────────────────────────
# Prediction
# ──────────────────────────────────────────────────────────────────────

def predict_future_impact(user_id: int, weeks: int = PREDICTION_WEEKS) -> PredictionResult:
    """Predict the user's impact over the next N weeks."""
    impacts = get_weekly_impacts(user_id, weeks=TREND_WINDOW_WEEKS + 2)
    active = [w for w in impacts if w.pledges_enrolled > 0]

    if len(active) < 2:
        return PredictionResult(
            equivalents_12w=estimate_co2_equivalents(0),
        )

    co2_values = [w.co2_saved_kg for w in active]
    xp_values = [w.xp_earned for w in active]
    pledge_values = [w.pledges_completed for w in active]

    avg_co2 = statistics.mean(co2_values)
    avg_xp = statistics.mean(xp_values)
    avg_pledges = statistics.mean(pledge_values)

    std_co2 = statistics.stdev(co2_values) if len(co2_values) > 1 else avg_co2 * 0.2
    std_xp = statistics.stdev(xp_values) if len(xp_values) > 1 else avg_xp * 0.2

    predicted_co2 = round(avg_co2 * weeks, 2)
    predicted_xp = round(avg_xp * weeks)
    predicted_pledges = round(avg_pledges * weeks)

    # Better scenario (+20% activity)
    better_co2 = round(avg_co2 * 1.2 * weeks, 2)
    worse_co2 = round(avg_co2 * 0.7 * weeks, 2)

    # Confidence interval (rough: ±1 standard deviation)
    ci_lower = round(predicted_co2 - std_co2 * math.sqrt(weeks), 2)
    ci_upper = round(predicted_co2 + std_co2 * math.sqrt(weeks), 2)

    return PredictionResult(
        predicted_co2_12w=max(0, predicted_co2),
        predicted_xp_12w=max(0, predicted_xp),
        predicted_pledges_12w=max(0, predicted_pledges),
        confidence_interval={"lower": max(0, ci_lower), "upper": ci_upper},
        scenario_better={
            "co2_kg": max(0, better_co2),
            "xp": round(avg_xp * 1.2 * weeks),
            "pledges": round(avg_pledges * 1.2 * weeks),
        },
        scenario_worse={
            "co2_kg": max(0, worse_co2),
            "xp": round(avg_xp * 0.7 * weeks),
            "pledges": round(avg_pledges * 0.7 * weeks),
        },
        equivalents_12w=estimate_co2_equivalents(max(0, predicted_co2)),
    )


# ──────────────────────────────────────────────────────────────────────
# Milestone tracking
# ──────────────────────────────────────────────────────────────────────

def check_milestones(user_id: int) -> list[Milestone]:
    """Check and record new milestones, returning the full milestone status."""
    stats = get_user_pledge_stats(user_id)
    all_pledges = get_user_all_pledges(user_id, limit=200)
    completed = [p for p in all_pledges if p.status == "completed"]

    achieved_types: set[str] = set()
    newly_achieved: list[Milestone] = []

    # Load already-achieved milestones from DB
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT milestone_type, achieved_at, xp_bonus FROM user_milestones WHERE user_id = ?", (user_id,))
        for row in cur.fetchall():
            achieved_types.add(row[0])

    def _try_achieve(mtype: MilestoneType) -> bool:
        if mtype.value in achieved_types:
            return False
        defn = MILESTONE_DEFINITIONS[mtype]
        now = datetime.now().isoformat(timespec="seconds")
        with database_connection(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR IGNORE INTO user_milestones (user_id, milestone_type, achieved_at, xp_bonus) VALUES (?, ?, ?, ?)",
                (user_id, mtype.value, now, defn["xp_bonus"]),
            )
            conn.commit()
        achieved_types.add(mtype.value)
        return True

    # ── Check milestones ──
    if stats.total_pledges_completed >= 1:
        _try_achieve(MilestoneType.FIRST_PLEDGE)
    if stats.total_pledges_completed >= 5:
        _try_achieve(MilestoneType.PLEDGES_5)
    if stats.total_pledges_completed >= 10:
        _try_achieve(MilestoneType.PLEDGES_10)
    if stats.total_pledges_completed >= 25:
        _try_achieve(MilestoneType.PLEDGES_25)
    if stats.total_pledges_completed >= 50:
        _try_achieve(MilestoneType.PLEDGES_50)

    if stats.current_streak >= 3:
        _try_achieve(MilestoneType.STREAK_3)
    if stats.current_streak >= 6:
        _try_achieve(MilestoneType.STREAK_6)
    if stats.current_streak >= 12:
        _try_achieve(MilestoneType.STREAK_12)

    if stats.total_co2_saved_kg >= 10:
        _try_achieve(MilestoneType.CO2_10)
    if stats.total_co2_saved_kg >= 50:
        _try_achieve(MilestoneType.CO2_50)
    if stats.total_co2_saved_kg >= 100:
        _try_achieve(MilestoneType.CO2_100)
    if stats.total_co2_saved_kg >= 500:
        _try_achieve(MilestoneType.CO2_500)

    # Category diversity
    categories_seen = set()
    active_categories = set()
    for p in all_pledges:
        tpl = get_template_by_id(p.template_id)
        if tpl:
            categories_seen.add(tpl.category)
            if p.status == "active":
                active_categories.add(tpl.category)
    all_categories = {t.category for t in get_all_templates()}
    if categories_seen >= all_categories:
        _try_achieve(MilestoneType.ALL_CATEGORIES)
    if len(active_categories) >= 3:
        _try_achieve(MilestoneType.DIVERSITY_3)
    if len(active_categories) >= 5:
        _try_achieve(MilestoneType.DIVERSITY_5)

    # Hard pledge
    for p in completed:
        tpl = get_template_by_id(p.template_id)
        if tpl and tpl.difficulty == "hard":
            _try_achieve(MilestoneType.HARD_PLEDGE)
            break

    # Perfect week (7 checkins)
    for p in completed:
        if p.day_checkins >= 7:
            _try_achieve(MilestoneType.PERFECT_WEEK)
            break

    # Weekend warrior
    for p in completed:
        dates = get_pledge_checkin_dates(p.pledge_id)
        for d in dates:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d")
                if dt.weekday() in (5, 6):  # Saturday or Sunday
                    weekend_dates = {dd for dd in dates if datetime.strptime(dd, "%Y-%m-%d").weekday() in (5, 6)}
                    if len(weekend_dates) >= 2:
                        _try_achieve(MilestoneType.WEEKEND_WARRIOR)
                        break
            except ValueError:
                continue
        if MilestoneType.WEEKEND_WARRIOR.value in achieved_types:
            break

    # Build milestone list
    milestones: list[Milestone] = []
    for mtype, defn in MILESTONE_DEFINITIONS.items():
        achieved = mtype.value in achieved_types
        milestones.append(Milestone(
            milestone_type=mtype.value,
            title=defn["title"],
            description=defn["description"],
            achieved=achieved,
            xp_bonus=defn["xp_bonus"],
            progress_pct=100.0 if achieved else 0.0,
        ))

    return milestones


def get_user_milestones(user_id: int) -> list[dict[str, Any]]:
    """Retrieve all achieved milestones for a user."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT milestone_type, achieved_at, xp_bonus FROM user_milestones WHERE user_id = ? ORDER BY achieved_at",
            (user_id,),
        )
        results = []
        for row in cur.fetchall():
            mtype = row[0]
            defn = MILESTONE_DEFINITIONS.get(MilestoneType(mtype), {})
            results.append({
                "milestone_type": mtype,
                "title": defn.get("title", mtype),
                "description": defn.get("description", ""),
                "achieved_at": row[1],
                "xp_bonus": row[2],
            })
        return results


# ──────────────────────────────────────────────────────────────────────
# Insight generation
# ──────────────────────────────────────────────────────────────────────

def generate_insights(user_id: int) -> list[Insight]:
    """Generate personalised insights based on the user's pledge behaviour."""
    stats = get_user_pledge_stats(user_id)
    all_pledges = get_user_all_pledges(user_id, limit=50)
    completed = [p for p in all_pledges if p.status == "completed"]
    active = [p for p in all_pledges if p.status == "active"]
    trend = analyse_trend(user_id)
    insights: list[Insight] = []

    now_str = datetime.now().isoformat(timespec="seconds")

    def _add(cat: str, pri: str, title: str, body: str, action: str = "", metric: float = 0.0):
        insights.append(Insight(
            insight_id=str(uuid.uuid4())[:10],
            category=cat,
            priority=pri,
            title=title,
            body=body,
            action_suggestion=action,
            metric_value=metric,
            generated_at=now_str,
        ))

    # ── Streak insights ──
    if stats.current_streak >= 6:
        _add("streak", "celebration", "🔥 Amazing Streak!",
             f"You're on a {stats.current_streak}-week streak! You're in the top tier of eco-warriors.",
             metric=float(stats.current_streak))
    elif stats.current_streak >= 3:
        _add("streak", "high", "⚡ Strong Streak",
             f"{stats.current_streak} weeks and counting. Push for 6 weeks for the 🌟 badge!",
             metric=float(stats.current_streak))
    elif stats.current_streak == 0 and stats.total_pledges_completed > 0:
        _add("streak", "medium", "🔄 Streak Reset",
             "Your streak was reset. Enrol in a new pledge this week to start building momentum again!",
             action="Browse pledges and enrol in at least one this week.")

    # ── Category insights ──
    categories_completed = set()
    for p in completed:
        tpl = get_template_by_id(p.template_id)
        if tpl:
            categories_completed.add(tpl.category)

    all_cats = {t.category for t in get_all_templates()}
    missing = all_cats - categories_completed

    if missing and len(categories_completed) >= 3:
        cat_labels = [PLEDGE_CATEGORIES.get(c, {}).get("label", c) for c in list(missing)[:3]]
        _add("category", "medium", "📂 Try Something New",
             f"You haven't tried {', '.join(cat_labels)} pledges yet. Diversifying boosts your impact!",
             action=f"Browse pledges in {', '.join(cat_labels)}.",
             metric=float(len(missing)))

    if len(categories_completed) >= 5:
        _add("category", "celebration", "🌈 Category Master",
             f"You've completed pledges in {len(categories_completed)} categories! Impressive diversity!",
             metric=float(len(categories_completed)))

    # ── Difficulty insights ──
    hard_completed = sum(1 for p in completed if (
        get_template_by_id(p.template_id) and get_template_by_id(p.template_id).difficulty == "hard"
    ))
    if hard_completed == 0 and stats.total_pledges_completed >= 3:
        _add("difficulty", "medium", "🔴 Ready for Hard Mode",
             "You've mastered easier pledges. Try a hard pledge for 2x CO₂ savings!",
             action="Filter by 'Hard' difficulty in Browse Pledges.")

    # ── Consistency insights ──
    if len(completed) >= 3:
        completion_rate = stats.completion_rate_pct
        if completion_rate >= 90:
            _add("consistency", "high", "🎯 Excellent Consistency",
                 f"{completion_rate:.0f}% completion rate! You're extremely reliable.",
                 metric=completion_rate)
        elif completion_rate < 50:
            _add("consistency", "medium", "📅 Improve Consistency",
                 f"Your completion rate is {completion_rate:.0f}%. Try fewer pledges but complete them all!",
                 action="Focus on 1-2 pledges per week instead of many.")

    # ── Impact insights ──
    if stats.total_co2_saved_kg >= 100:
        eq = estimate_co2_equivalents(stats.total_co2_saved_kg)
        _add("impact", "celebration", "🌍 Massive Impact",
             f"You've saved {stats.total_co2_saved_kg:.1f} kg CO₂ — equivalent to {eq['trees_needed']:.0f} trees!",
             metric=stats.total_co2_saved_kg)
    elif stats.total_co2_saved_kg >= 10:
        _add("impact", "high", "🌍 Growing Impact",
             f"{stats.total_co2_saved_kg:.1f} kg CO₂ saved so far. Keep going for the 50 kg badge!",
             metric=stats.total_co2_saved_kg)

    # ── Trend insights ──
    if trend.direction == "improving":
        _add("impact", "high", "📈 Trending Up",
             trend.summary, metric=trend.slope)
    elif trend.direction == "declining":
        _add("impact", "medium", "📉 Declining Activity",
             trend.summary, action="Check in daily and try a new pledge category.")

    # ── Social / group insights ──
    groups = get_user_groups(user_id)
    if not groups:
        _add("social", "low", "👥 Join a Group",
             "You're flying solo! Accountability groups boost completion rates by 40%.",
             action="Create or join an accountability group.")
    elif len(groups) >= 1:
        _add("social", "medium", "👥 Group Member",
             f"You're in {len(groups)} group(s). Engage with your team for extra XP bonuses!",
             metric=float(len(groups)))

    # ── Opportunity insights ──
    if stats.total_pledges_completed == 0 and stats.total_pledges_made > 0:
        _add("opportunity", "high", "💡 Complete Your Pledge",
             "You enrolled but haven't completed any pledges yet. Start checking in today!",
             action="Go to My Pledges and check in today.")

    if len(active) > 0 and len(active) < 3:
        _add("opportunity", "low", "💡 Room for More",
             f"You have {len(active)} active pledge(s). You can enrol in up to 3 for maximum impact!",
             action="Browse pledges and add 1-2 more.")

    return insights


def dismiss_insight(user_id: int, insight_id: str) -> bool:
    """Mark an insight as dismissed."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE user_insights SET dismissed = 1 WHERE user_id = ? AND id = ?",
            (user_id, insight_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ──────────────────────────────────────────────────────────────────────
# Category breakdown
# ──────────────────────────────────────────────────────────────────────

def get_category_breakdown(user_id: int) -> list[CategoryBreakdown]:
    """Get per-category pledge stats for a user."""
    all_pledges = get_user_all_pledges(user_id, limit=200)
    cat_data: dict[str, dict[str, Any]] = {}

    for cat_key, cat_info in PLEDGE_CATEGORIES.items():
        cat_data[cat_key] = {
            "category": cat_key,
            "label": cat_info["label"],
            "color": cat_info["color"],
            "enrolled": 0,
            "completed": 0,
            "co2": 0.0,
            "xp_total": 0,
            "pledges": [],
        }

    for p in all_pledges:
        tpl = get_template_by_id(p.template_id)
        if not tpl:
            continue
        cat = tpl.category
        if cat not in cat_data:
            cat_data[cat] = {
                "category": cat,
                "label": PLEDGE_CATEGORIES.get(cat, {}).get("label", cat),
                "color": PLEDGE_CATEGORIES.get(cat, {}).get("color", "#888"),
                "enrolled": 0,
                "completed": 0,
                "co2": 0.0,
                "xp_total": 0,
                "pledges": [],
            }
        cat_data[cat]["enrolled"] += 1
        cat_data[cat]["pledges"].append(p.template_id)
        if p.status == "completed":
            cat_data[cat]["completed"] += 1
            cat_data[cat]["co2"] += tpl.weekly_co2_saved_kg
            cat_data[cat]["xp_total"] += tpl.xp_reward

    breakdowns: list[CategoryBreakdown] = []
    for cat_key, data in cat_data.items():
        enrolled = data["enrolled"]
        completed = data["completed"]
        rate = (completed / enrolled * 100) if enrolled > 0 else 0.0
        avg_xp = (data["xp_total"] / completed) if completed > 0 else 0.0

        # Find most-used pledge in this category
        if data["pledges"]:
            counter = Counter(data["pledges"])
            fav_id = counter.most_common(1)[0][0]
            fav_tpl = get_template_by_id(fav_id)
            fav_name = fav_tpl.title if fav_tpl else fav_id
        else:
            fav_name = "—"

        breakdowns.append(CategoryBreakdown(
            category=cat_key,
            label=data["label"],
            color=data["color"],
            total_enrolled=enrolled,
            total_completed=completed,
            completion_rate=round(rate, 1),
            co2_saved_kg=round(data["co2"], 2),
            avg_xp_per_pledge=round(avg_xp, 1),
            favorite_pledge=fav_name,
        ))

    return breakdowns


# ──────────────────────────────────────────────────────────────────────
# Comparison report
# ──────────────────────────────────────────────────────────────────────

def generate_comparison_report(user_id: int) -> ComparisonReport:
    """Compare a user's performance against the community average."""
    stats = get_user_pledge_stats(user_id)
    cat_breakdown = get_category_breakdown(user_id)

    # Community averages from leaderboard
    leaderboard = get_leaderboard(limit=100)

    if not leaderboard:
        return ComparisonReport(
            user_eco_score=stats.completion_rate_pct,
            category_comparison=[],
            strengths=[],
            improvement_areas=[],
        )

    # Calculate averages from leaderboard
    total_xp = sum(e.total_xp for e in leaderboard)
    total_co2 = sum(e.total_co2_saved_kg for e in leaderboard)
    total_completed = sum(e.pledges_completed for e in leaderboard)
    total_members = max(1, len(leaderboard))

    avg_xp = total_xp / total_members
    avg_co2 = total_co2 / total_members
    avg_completed = total_completed / total_members

    # Percentile rank (by XP)
    user_rank = sum(1 for e in leaderboard if e.total_xp > stats.total_xp_earned)
    percentile = round((1 - user_rank / total_members) * 100, 1)

    # Category comparison
    category_comparison = []
    for cb in cat_breakdown:
        above_avg = cb.completion_rate > 50
        category_comparison.append({
            "category": cb.label,
            "color": cb.color,
            "completion_rate": cb.completion_rate,
            "co2_saved_kg": cb.co2_saved_kg,
            "above_average": above_avg,
        })

    # Strengths & improvement areas
    strengths: list[str] = []
    improvement_areas: list[str] = []

    if stats.total_xp_earned > avg_xp:
        strengths.append(f"XP: {stats.total_xp_earned} vs community avg {avg_xp:.0f}")
    else:
        improvement_areas.append(f"XP: {stats.total_xp_earned} vs community avg {avg_xp:.0f}")

    if stats.total_co2_saved_kg > avg_co2:
        strengths.append(f"CO₂ saved: {stats.total_co2_saved_kg:.1f} vs avg {avg_co2:.1f} kg")
    else:
        improvement_areas.append(f"CO₂ saved: {stats.total_co2_saved_kg:.1f} vs avg {avg_co2:.1f} kg")

    if stats.total_pledges_completed > avg_completed:
        strengths.append(f"Pledges completed: {stats.total_pledges_completed} vs avg {avg_completed:.0f}")
    else:
        improvement_areas.append(f"Pledges completed: {stats.total_pledges_completed} vs avg {avg_completed:.0f}")

    for cb in cat_breakdown:
        if cb.completion_rate >= 80 and cb.total_completed >= 2:
            strengths.append(f"Strong in {cb.label} ({cb.completion_rate:.0f}% completion)")
        elif cb.total_enrolled > 0 and cb.completion_rate < 30:
            improvement_areas.append(f"Struggling in {cb.label} ({cb.completion_rate:.0f}% completion)")

    return ComparisonReport(
        user_eco_score=stats.completion_rate_pct,
        community_avg_eco_score=round(avg_completed * 10, 1),
        percentile_rank=percentile,
        category_comparison=category_comparison,
        strengths=strengths,
        improvement_areas=improvement_areas,
        vs_community={
            "user_xp": stats.total_xp_earned,
            "avg_xp": round(avg_xp),
            "user_co2_kg": stats.total_co2_saved_kg,
            "avg_co2_kg": round(avg_co2, 1),
            "user_pledges": stats.total_pledges_completed,
            "avg_pledges": round(avg_completed),
            "community_size": total_members,
        },
    )


# ──────────────────────────────────────────────────────────────────────
# Full impact report
# ──────────────────────────────────────────────────────────────────────

def generate_full_report(user_id: int, period_weeks: int = 12) -> ImpactReport:
    """Generate a comprehensive impact src.reporting.report."""
    stats = get_user_pledge_stats(user_id)
    weekly = get_weekly_impacts(user_id, weeks=period_weeks)
    trend = analyse_trend(user_id)
    prediction = predict_future_impact(user_id)
    insights = generate_insights(user_id)
    milestones = check_milestones(user_id)
    cat_breakdown = get_category_breakdown(user_id)

    active_weeks = [w for w in weekly if w.pledges_enrolled > 0]

    total_co2 = sum(w.co2_saved_kg for w in active_weeks)
    total_xp = sum(w.xp_earned for w in active_weeks)
    total_completed = sum(w.pledges_completed for w in active_weeks)
    total_checkins = sum(w.checkins for w in active_weeks)
    avg_co2 = total_co2 / max(len(active_weeks), 1)

    best_week = max(active_weeks, key=lambda w: w.co2_saved_kg) if active_weeks else None
    worst_week = min(active_weeks, key=lambda w: w.co2_saved_kg) if active_weeks else None

    report = ImpactReport(
        user_id=user_id,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        period_weeks=period_weeks,
        total_co2_saved_kg=round(total_co2, 2),
        total_xp=total_xp,
        total_pledges_completed=total_completed,
        total_checkins=total_checkins,
        avg_weekly_co2_kg=round(avg_co2, 2),
        best_week=best_week,
        worst_week=worst_week,
        trend=trend,
        prediction=prediction,
        insights=insights,
        milestones=milestones,
        category_breakdown=[asdict(cb) for cb in cat_breakdown],
        weekly_data=weekly,
    )

    # Persist report
    _save_report(user_id, report)

    return report


def _save_report(user_id: int, report: ImpactReport) -> None:
    """Persist the report to DB for history."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        data = {
            "period_weeks": src.reporting.report.period_weeks,
            "total_co2_saved_kg": src.reporting.report.total_co2_saved_kg,
            "total_xp": src.reporting.report.total_xp,
            "total_pledges_completed": src.reporting.report.total_pledges_completed,
            "total_checkins": src.reporting.report.total_checkins,
            "avg_weekly_co2_kg": src.reporting.report.avg_weekly_co2_kg,
        }
        cur.execute(
            "INSERT INTO impact_reports (user_id, report_data, generated_at) VALUES (?, ?, ?)",
            (user_id, json.dumps(data, default=str), src.reporting.report.generated_at),
        )
        conn.commit()


def get_report_history(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve historical impact reports."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT report_data, generated_at FROM impact_reports WHERE user_id = ? ORDER BY generated_at DESC LIMIT ?",
            (user_id, limit),
        )
        results = []
        for row in cur.fetchall():
            data = json.loads(row[0])
            data["generated_at"] = row[1]
            results.append(data)
        return results


# ──────────────────────────────────────────────────────────────────────
# Utility functions
# ──────────────────────────────────────────────────────────────────────

def _moving_average(values: list[float], window: int) -> list[float]:
    """Compute simple moving average."""
    if len(values) < window:
        return values[:]
    result = []
    for i in range(len(values) - window + 1):
        avg = sum(values[i:i + window]) / window
        result.append(avg)
    return result


def impact_report_to_dict(report: ImpactReport) -> dict[str, Any]:
    """Serialise report to dict for JSON export."""
    d = asdict(report)
    if src.reporting.report.best_week:
        d["best_week"] = asdict(src.reporting.report.best_week)
    if src.reporting.report.worst_week:
        d["worst_week"] = asdict(src.reporting.report.worst_week)
    if src.reporting.report.trend:
        d["trend"] = asdict(src.reporting.report.trend)
    if src.reporting.report.prediction:
        d["prediction"] = asdict(src.reporting.report.prediction)
    d["insights"] = [asdict(i) for i in src.reporting.report.insights]
    d["milestones"] = [asdict(m) for m in src.reporting.report.milestones]
    return d


def export_report_json(user_id: int, period_weeks: int = 12) -> str:
    """Generate and export a full impact report as JSON."""
    report = generate_full_report(user_id, period_weeks)
    return json.dumps(impact_report_to_dict(report), indent=2, default=str)
