"""
Pledge Habit Engine
====================
Behavioural-science-inspired smart scheduling and habit formation
for green pledges. Tracks habit stages, generates personalised nudges,
suggests optimal pledge combinations, handles difficulty ramping,
and provides a weekly planner with streak protection.

Dependencies: green_pledge_tracker, database_connection.
"""

from __future__ import annotations

import json
import math
import random
import sqlite3
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from database_connection import database_connection
from green_pledge_tracker import (
    DB_NAME,
    PLEDGE_CATALOG,
    PLEDGE_CATEGORIES,
    PledgeDifficulty,
    PledgeTemplate,
    current_week_start,
    current_week_end,
    get_all_templates,
    get_template_by_id,
    get_user_all_pledges,
    get_user_pledge_stats,
    get_pledge_checkin_dates,
    weeks_between,
)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

HABIT_FORMATION_WEEKS = 8  # Weeks to form a habit
HABIT_THRESHOLD_PCT = 80.0  # Completion % to consider a habit "formed"

MAX_ACTIVE_PLEDGES = 5
RECOMMENDED_ACTIVE_PLEDGES = 3

NUDGE_COOLDOWN_HOURS = 12
MAX_NUDGES_PER_DAY = 3

DIFFICULTY_RAMP_COOLDOWN_WEEKS = 2

STREAK_PROTECTION_EXTENSIONS = 1  # Allow 1 missed week before streak breaks


class HabitStage(str, Enum):
    """Stages of habit formation based on behavioral science."""
    EXPLORATION = "exploration"        # Week 1-2: Trying out, low commitment
    BUILDING = "building"              # Week 3-4: Establishing routine
    REINFORCING = "reinforcing"        # Week 5-6: Strengthening the habit
    CONSOLIDATING = "consolidating"    # Week 7-8: Making it stick
    AUTOMATIC = "automatic"            # Week 9+: Habit is automatic
    DORMANT = "dormant"                # Habit has lapsed


class NudgeType(str, Enum):
    CHECKIN_REMINDER = "checkin_reminder"
    STREAK_GUARD = "streak_guard"
    DIFFICULTY_BOOST = "difficulty_boost"
    CATEGORY_DIVERSIFY = "category_diversify"
    SOCIAL_BOOST = "social_boost"
    CELEBRATION = "celebration"
    RECOVERY = "recovery"
    OPTIMAL_CHALLENGE = "optimal_challenge"
    WEEKEND_HUSTLE = "weekend_hustle"
    HABIT_MILESTONE = "habit_milestone"


class ScheduleSlot(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    ANYTIME = "anytime"


class ComboStrategy(str, Enum):
    EASY_WARMUP = "easy_warmup"
    BALANCED = "balanced"
    HIGH_IMPACT = "high_impact"
    DIVERSITY = "diversity"
    STREAK_FOCUS = "streak_focus"
    CHALLENGE_MODE = "challenge_mode"


DIFFICULTY_WEIGHTS = {
    PledgeDifficulty.EASY: 1.0,
    PledgeDifficulty.MEDIUM: 2.0,
    PledgeDifficulty.HARD: 3.5,
}

DIFFICULTY_LABELS = {
    "easy": "🟢 Easy",
    "medium": "🟡 Medium",
    "hard": "🔴 Hard",
}

CATEGORY_EFFORT_SCORE = {
    "energy": 5,
    "transport": 7,
    "diet": 6,
    "waste": 4,
    "water": 3,
    "lifestyle": 2,
}


# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────

@dataclass
class HabitProfile:
    """Tracks a single pledge's habit formation progress."""
    user_id: int
    template_id: str
    stage: str
    weeks_enrolled: int = 0
    weeks_completed: int = 0
    completion_rate: float = 0.0
    habit_strength: float = 0.0  # 0.0 – 1.0
    last_checkin_date: str = ""
    consecutive_missed: int = 0
    total_checkins: int = 0
    avg_checkins_per_week: float = 0.0
    difficulty_history: list[str] = field(default_factory=list)
    category: str = ""
    template_title: str = ""


@dataclass
class Nudge:
    """A personalised nudge or reminder."""
    nudge_id: str
    nudge_type: str
    priority: str  # low | medium | high
    title: str
    message: str
    action_label: str = ""
    action_template_id: str = ""
    icon: str = "💡"
    expires_at: str = ""


@dataclass
class OptimalCombo:
    """A recommended pledge combination."""
    combo_id: str
    strategy: str
    title: str
    description: str
    pledges: list[dict[str, Any]] = field(default_factory=list)
    total_weekly_co2_kg: float = 0.0
    total_weekly_xp: int = 0
    total_effort_score: int = 0
    difficulty_label: str = ""
    fit_score: float = 0.0
    estimated_completion_pct: float = 0.0


@dataclass
class WeeklyPlanner:
    """A week-by-week pledge plan."""
    week_start: str
    pledges: list[dict[str, Any]] = field(default_factory=list)
    daily_focus: dict[str, str] = field(default_factory=dict)
    total_co2_kg: float = 0.0
    total_xp: int = 0
    difficulty_mix: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class StreakProtection:
    """Tracks streak protection status."""
    user_id: int
    current_streak: int = 0
    extensions_remaining: int = 1
    last_completed_week: str = ""
    streak_at_risk: bool = False
    protection_active: bool = False
    weeks_until_break: int = 0


@dataclass
class HabitInsight:
    """An insight about habit formation."""
    insight_type: str
    title: str
    body: str
    metric: float = 0.0
    recommendation: str = ""


@dataclass
class DifficultyRecommendation:
    """Recommendation for difficulty progression."""
    current_avg: str
    recommended: str
    reason: str
    ready: bool = False
    weeks_at_current: int = 0
    completion_rate_needed: float = 80.0


# ──────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────

def init_habit_tables() -> None:
    """Create habit tracking tables."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS habit_profiles (
                user_id             INTEGER NOT NULL,
                template_id         TEXT NOT NULL,
                stage               TEXT DEFAULT 'exploration',
                weeks_enrolled      INTEGER DEFAULT 0,
                weeks_completed     INTEGER DEFAULT 0,
                completion_rate     REAL DEFAULT 0.0,
                habit_strength      REAL DEFAULT 0.0,
                last_checkin_date   TEXT DEFAULT '',
                consecutive_missed  INTEGER DEFAULT 0,
                total_checkins      INTEGER DEFAULT 0,
                avg_checkins_week   REAL DEFAULT 0.0,
                difficulty_history  TEXT DEFAULT '[]',
                PRIMARY KEY (user_id, template_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS streak_protections (
                user_id                 INTEGER PRIMARY KEY,
                current_streak          INTEGER DEFAULT 0,
                extensions_remaining    INTEGER DEFAULT 1,
                last_completed_week     TEXT DEFAULT '',
                streak_at_risk          INTEGER DEFAULT 0,
                protection_active       INTEGER DEFAULT 0,
                weeks_until_break       INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nudge_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                nudge_type  TEXT NOT NULL,
                sent_at     TEXT NOT NULL,
                template_id TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedule_preferences (
                user_id             INTEGER PRIMARY KEY,
                preferred_slot      TEXT DEFAULT 'anytime',
                max_active_pledges  INTEGER DEFAULT 3,
                prefer_same_category INTEGER DEFAULT 0,
                prefer_variety      INTEGER DEFAULT 1,
                difficulty_preference TEXT DEFAULT 'auto',
                updated_at          TEXT DEFAULT ''
            )
        """)
        conn.commit()


# ──────────────────────────────────────────────────────────────────────
# Habit profile management
# ──────────────────────────────────────────────────────────────────────

def build_habit_profiles(user_id: int) -> list[HabitProfile]:
    """Build habit profiles for all pledges a user has engaged with."""
    all_pledges = get_user_all_pledges(user_id, limit=200)
    profiles: list[HabitProfile] = []

    # Group by template_id
    by_template: dict[str, list] = defaultdict(list)
    for p in all_pledges:
        by_template[p.template_id].append(p)

    for tpl_id, pledges in by_template.items():
        tpl = get_template_by_id(tpl_id)
        if not tpl:
            continue

        weeks_enrolled = len(set(p.week_start for p in pledges))
        weeks_completed = sum(1 for p in pledges if p.status == "completed")
        total_checkins = sum(p.day_checkins for p in pledges)
        completion_rate = (weeks_completed / weeks_enrolled * 100) if weeks_enrolled > 0 else 0.0
        avg_checkins = total_checkins / max(weeks_enrolled, 1)

        # Habit strength: blend of consistency, recency, and volume
        consistency_score = completion_rate / 100.0
        volume_score = min(total_checkins / 28.0, 1.0)  # 28 checkins = 4 perfect weeks
        recency_score = _recency_score(pledges)

        habit_strength = round(
            consistency_score * 0.4 + volume_score * 0.3 + recency_score * 0.3,
            3,
        )

        # Determine stage
        stage = _determine_stage(weeks_enrolled, completion_rate, habit_strength)

        # Last checkin
        all_dates = []
        for p in pledges:
            all_dates.extend(get_pledge_checkin_dates(p.pledge_id))
        last_checkin = max(all_dates) if all_dates else ""

        # Consecutive missed
        consecutive_missed = 0
        if pledges:
            sorted_pledges = sorted(pledges, key=lambda p: p.week_start, reverse=True)
            for p in sorted_pledges:
                if p.status in ("missed", "abandoned"):
                    consecutive_missed += 1
                elif p.status == "active":
                    consecutive_missed += 1  # active but not yet completed
                else:
                    break

        # Difficulty history
        diff_history = [tpl.difficulty for p in pledges for _ in range(max(p.day_checkins, 1))]

        profile = HabitProfile(
            user_id=user_id,
            template_id=tpl_id,
            stage=stage,
            weeks_enrolled=weeks_enrolled,
            weeks_completed=weeks_completed,
            completion_rate=round(completion_rate, 1),
            habit_strength=habit_strength,
            last_checkin_date=last_checkin,
            consecutive_missed=consecutive_missed,
            total_checkins=total_checkins,
            avg_checkins_per_week=round(avg_checkins, 1),
            difficulty_history=diff_history[-10:],
            category=tpl.category,
            template_title=tpl.title,
        )

        _persist_habit_profile(user_id, profile)
        profiles.append(profile)

    return profiles


def _determine_stage(weeks_enrolled: int, completion_rate: float, habit_strength: float) -> str:
    """Determine habit formation stage."""
    if weeks_enrolled <= 2:
        return HabitStage.EXPLORATION
    elif weeks_enrolled <= 4:
        if completion_rate >= 60:
            return HabitStage.BUILDING
        return HabitStage.EXPLORATION
    elif weeks_enrolled <= 6:
        if completion_rate >= 70:
            return HabitStage.REINFORCING
        return HabitStage.BUILDING
    elif weeks_enrolled <= 8:
        if completion_rate >= 75 and habit_strength >= 0.5:
            return HabitStage.CONSOLIDATING
        return HabitStage.REINFORCING
    else:
        if completion_rate >= HABIT_THRESHOLD_PCT and habit_strength >= 0.7:
            return HabitStage.AUTOMATIC
        elif habit_strength < 0.3:
            return HabitStage.DORMANT
        return HabitStage.CONSOLIDATING


def _recency_score(pledges: list) -> float:
    """Score how recently the user engaged with this pledge."""
    if not pledges:
        return 0.0
    now = datetime.now()
    most_recent = max(
        (p.completed_at or p.created_at or "") for p in pledges
    )
    if not most_recent:
        return 0.3
    try:
        dt = datetime.fromisoformat(most_recent.replace("Z", "+00:00").split("+")[0])
        days_ago = (now - dt).days
        return max(0.0, 1.0 - days_ago / 28.0)
    except (ValueError, TypeError):
        return 0.3


def _persist_habit_profile(user_id: int, profile: HabitProfile) -> None:
    """Save habit profile to DB."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO habit_profiles
                (user_id, template_id, stage, weeks_enrolled, weeks_completed,
                 completion_rate, habit_strength, last_checkin_date,
                 consecutive_missed, total_checkins, avg_checkins_week, difficulty_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, template_id) DO UPDATE SET
                stage = excluded.stage,
                weeks_enrolled = excluded.weeks_enrolled,
                weeks_completed = excluded.weeks_completed,
                completion_rate = excluded.completion_rate,
                habit_strength = excluded.habit_strength,
                last_checkin_date = excluded.last_checkin_date,
                consecutive_missed = excluded.consecutive_missed,
                total_checkins = excluded.total_checkins,
                avg_checkins_week = excluded.avg_checkins_week,
                difficulty_history = excluded.difficulty_history
        """, (
            user_id, profile.template_id, profile.stage,
            profile.weeks_enrolled, profile.weeks_completed,
            profile.completion_rate, profile.habit_strength,
            profile.last_checkin_date, profile.consecutive_missed,
            profile.total_checkins, profile.avg_checkins_per_week,
            json.dumps(profile.difficulty_history),
        ))
        conn.commit()


# ──────────────────────────────────────────────────────────────────────
# Nudge generation
# ──────────────────────────────────────────────────────────────────────

def generate_nudges(user_id: int) -> list[Nudge]:
    """Generate personalised nudges based on habit profiles and behaviour."""
    profiles = build_habit_profiles(user_id)
    stats = get_user_pledge_stats(user_id)
    nudges: list[Nudge] = []

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # Check nudge cooldown
    recent_nudges = _get_recent_nudge_count(user_id, hours=24)

    def _add(ntype: str, pri: str, title: str, message: str,
             action: str = "", tpl_id: str = "", icon: str = "💡"):
        if recent_nudges < MAX_NUDGES_PER_DAY:
            nudges.append(Nudge(
                nudge_id=str(uuid.uuid4())[:10],
                nudge_type=ntype,
                priority=pri,
                title=title,
                message=message,
                action_label=action,
                action_template_id=tpl_id,
                icon=icon,
                expires_at=(now + timedelta(hours=24)).isoformat(timespec="seconds"),
            ))

    # ── Checkin reminders ──
    for p in profiles:
        if p.stage in (HabitStage.EXPLORATION, HabitStage.BUILDING):
            if p.consecutive_missed >= 1:
                _add(
                    NudgeType.CHECKIN_REMINDER, "high",
                    f"🔄 Don't break the streak!",
                    f"You haven't checked in for **{p.template_title}** in a while. "
                    f"It takes {HABIT_FORMATION_WEEKS} weeks to build a habit — you're at {p.weeks_enrolled} weeks.",
                    action="Check in now",
                    tpl_id=p.template_id,
                    icon="🔄",
                )

    # ── Streak guard ──
    if stats.current_streak >= 2 and stats.current_streak < stats.best_streak:
        _add(
            NudgeType.STREAK_GUARD, "high",
            f"🔥 Protect your {stats.current_streak}-week streak!",
            f"You're {stats.best_streak - stats.current_streak} weeks from your best streak. Keep going!",
            icon="🔥",
        )

    # ── Difficulty boost ──
    difficulty_rec = recommend_difficulty(user_id)
    if difficulty_rec.ready:
        _add(
            NudgeType.DIFFICULTY_BOOST, "medium",
            f"⬆️ Ready for {DIFFICULTY_LABELS.get(difficulty_rec.recommended, difficulty_rec.recommended)}!",
            difficulty_rec.reason,
            action="Try a harder pledge",
            icon="⬆️",
        )

    # ── Category diversify ──
    active_profiles = [p for p in profiles if p.stage != HabitStage.DORMANT]
    active_cats = set(p.category for p in active_profiles)
    all_cats = set(PLEDGE_CATEGORIES.keys())
    missing = all_cats - active_cats
    if missing and len(active_cats) >= 2:
        cat_label = PLEDGE_CATEGORIES.get(list(missing)[0], {}).get("label", list(missing)[0])
        _add(
            NudgeType.CATEGORY_DIVERSIFY, "low",
            f"📂 Try {cat_label} pledges",
            f"You haven't explored {cat_label} pledges yet. Diversifying your eco-habits multiplies your impact!",
            action=f"Browse {cat_label} pledges",
            icon="📂",
        )

    # ── Celebration ──
    for p in profiles:
        if p.stage == HabitStage.AUTOMATIC:
            _add(
                NudgeType.CELEBRATION, "medium",
                f"🎉 Habit formed!",
                f"**{p.template_title}** is now an automatic habit! Your consistency is inspiring.",
                icon="🎉",
            )

    # ── Recovery ──
    dormant = [p for p in profiles if p.stage == HabitStage.DORMANT]
    for p in dormant:
        _add(
            NudgeType.RECOVERY, "medium",
            f"🌱 Rekindle **{p.template_title}**",
            f"This pledge went dormant after {p.consecutive_missed} missed weeks. "
            f"Start with just 1 check-in to reignite the habit.",
            action="Check in today",
            tpl_id=p.template_id,
            icon="🌱",
        )

    # ── Weekend hustle ──
    if now.weekday() in (4, 5):  # Friday or Saturday
        _add(
            NudgeType.WEEKEND_HUSTLE, "low",
            "🏁 Weekend is here!",
            "Weekend check-ins count too! Use this time to solidify your eco-habits.",
            icon="🏁",
        )

    # ── Optimal challenge ──
    if stats.total_pledges_completed >= 5:
        _add(
            NudgeType.OPTIMAL_CHALLENGE, "low",
            "🎯 Challenge suggestion",
            "Based on your progress, you're ready for a group challenge. Rally your accountability team!",
            icon="🎯",
        )

    # Log nudges
    for n in nudges:
        _log_nudge(user_id, n)

    return nudges


def _get_recent_nudge_count(user_id: int, hours: int = 24) -> int:
    """Count nudges sent in the last N hours."""
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat(timespec="seconds")
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM nudge_log WHERE user_id = ? AND sent_at > ?",
            (user_id, cutoff),
        )
        return cur.fetchone()[0]


def _log_nudge(user_id: int, nudge: Nudge) -> None:
    """Log a nudge to prevent duplicates."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO nudge_log (user_id, nudge_type, sent_at, template_id) VALUES (?, ?, ?, ?)",
            (user_id, nudge.nudge_type, datetime.now().isoformat(timespec="seconds"), nudge.action_template_id),
        )
        conn.commit()


# ──────────────────────────────────────────────────────────────────────
# Optimal pledge combinations
# ──────────────────────────────────────────────────────────────────────

def suggest_optimal_combos(
    user_id: int,
    strategy: str = "balanced",
    n: int = 3,
    user_footprint: float = 5000.0,
) -> list[OptimalCombo]:
    """Suggest optimal pledge combinations based on strategy."""
    profiles = build_habit_profiles(user_id)
    enrolled_ids = {p.template_id for p in profiles}
    templates = [t for t in get_all_templates() if t.id not in enrolled_ids]

    if not templates:
        templates = get_all_templates()  # fallback to all

    combos: list[OptimalCombo] = []

    if strategy == ComboStrategy.EASY_WARMUP:
        combos = _combo_easy_warmup(templates, n)
    elif strategy == ComboStrategy.HIGH_IMPACT:
        combos = _combo_high_impact(templates, n)
    elif strategy == ComboStrategy.DIVERSITY:
        combos = _combo_diversity(templates, n)
    elif strategy == ComboStrategy.STREAK_FOCUS:
        combos = _combo_streak_focus(templates, user_id, n)
    elif strategy == ComboStrategy.CHALLENGE_MODE:
        combos = _combo_challenge_mode(templates, n)
    else:
        combos = _combo_balanced(templates, user_footprint, n)

    return combos


def _combo_balanced(templates: list[PledgeTemplate], footprint: float, n: int) -> list[OptimalCombo]:
    """Balanced combo: mix of difficulty levels, good CO₂ impact."""
    combos: list[OptimalCombo] = []
    for i in range(min(n, 3)):
        # Pick 1 easy, 1 medium, 1 hard if available
        easy = [t for t in templates if t.difficulty == "easy"]
        medium = [t for t in templates if t.difficulty == "medium"]
        hard = [t for t in templates if t.difficulty == "hard"]

        selected = []
        for pool in [easy, medium, hard]:
            if pool:
                selected.append(random.choice(pool))

        if not selected:
            break

        total_co2 = sum(t.weekly_co2_saved_kg for t in selected)
        total_xp = sum(t.xp_reward for t in selected)
        effort = sum(DIFFICULTY_WEIGHTS.get(PledgeDifficulty(t.difficulty), 1.0) for t in selected)

        combos.append(OptimalCombo(
            combo_id=str(uuid.uuid4())[:8],
            strategy="balanced",
            title=f"Balanced Mix {i+1}",
            description="A mix of easy, medium, and hard pledges for steady progress.",
            pledges=[{"id": t.id, "title": t.title, "difficulty": t.difficulty} for t in selected],
            total_weekly_co2_kg=round(total_co2, 1),
            total_weekly_xp=total_xp,
            total_effort_score=round(effort, 1),
            difficulty_label="Mixed",
            fit_score=round(total_co2 * 2 + total_xp * 0.5, 1),
            estimated_completion_pct=75.0,
        ))

    return combos


def _combo_easy_warmup(templates: list[PledgeTemplate], n: int) -> list[OptimalCombo]:
    """Easy warmup: only easy pledges for new users."""
    easy = [t for t in templates if t.difficulty == "easy"]
    random.shuffle(easy)
    combos = []

    for i in range(min(n, max(1, len(easy) // 3))):
        batch = easy[i*3:(i+1)*3]
        if not batch:
            break
        total_co2 = sum(t.weekly_co2_saved_kg for t in batch)
        total_xp = sum(t.xp_reward for t in batch)

        combos.append(OptimalCombo(
            combo_id=str(uuid.uuid4())[:8],
            strategy="easy_warmup",
            title=f"Easy Start {i+1}",
            description="Gentle pledges to build confidence and establish habits.",
            pledges=[{"id": t.id, "title": t.title, "difficulty": t.difficulty} for t in batch],
            total_weekly_co2_kg=round(total_co2, 1),
            total_weekly_xp=total_xp,
            total_effort_score=len(batch),
            difficulty_label="🟢 Easy",
            fit_score=round(total_co2 * 1.5 + total_xp * 0.3, 1),
            estimated_completion_pct=90.0,
        ))

    return combos


def _combo_high_impact(templates: list[PledgeTemplate], n: int) -> list[OptimalCombo]:
    """High impact: prioritise CO₂ savings."""
    sorted_tpls = sorted(templates, key=lambda t: t.weekly_co2_saved_kg, reverse=True)
    combos = []

    for i in range(min(n, max(1, len(sorted_tpls) // 3))):
        batch = sorted_tpls[i*3:(i+1)*3]
        if not batch:
            break
        total_co2 = sum(t.weekly_co2_saved_kg for t in batch)
        total_xp = sum(t.xp_reward for t in batch)

        combos.append(OptimalCombo(
            combo_id=str(uuid.uuid4())[:8],
            strategy="high_impact",
            title=f"Maximum Impact {i+1}",
            description="Top CO₂-saving pledges for maximum environmental benefit.",
            pledges=[{"id": t.id, "title": t.title, "difficulty": t.difficulty} for t in batch],
            total_weekly_co2_kg=round(total_co2, 1),
            total_weekly_xp=total_xp,
            total_effort_score=round(sum(DIFFICULTY_WEIGHTS.get(PledgeDifficulty(t.difficulty), 1.0) for t in batch), 1),
            difficulty_label="Mixed",
            fit_score=round(total_co2 * 3 + total_xp * 0.2, 1),
            estimated_completion_pct=65.0,
        ))

    return combos


def _combo_diversity(templates: list[PledgeTemplate], n: int) -> list[OptimalCombo]:
    """Diversity: one pledge per category."""
    by_cat: dict[str, list[PledgeTemplate]] = defaultdict(list)
    for t in templates:
        by_cat[t.category].append(t)

    combos = []
    categories = list(by_cat.keys())

    for i in range(min(n, len(categories) // 2 + 1)):
        selected = []
        used_cats = set()
        for cat in categories:
            if cat not in used_cats and by_cat[cat]:
                selected.append(random.choice(by_cat[cat]))
                used_cats.add(cat)
                if len(selected) >= 3:
                    break

        if len(selected) < 2:
            continue

        total_co2 = sum(t.weekly_co2_saved_kg for t in selected)
        total_xp = sum(t.xp_reward for t in selected)

        combos.append(OptimalCombo(
            combo_id=str(uuid.uuid4())[:8],
            strategy="diversity",
            title=f"Eco Explorer {i+1}",
            description="One pledge from each category for maximum habit diversity.",
            pledges=[{"id": t.id, "title": t.title, "difficulty": t.difficulty} for t in selected],
            total_weekly_co2_kg=round(total_co2, 1),
            total_weekly_xp=total_xp,
            total_effort_score=round(sum(DIFFICULTY_WEIGHTS.get(PledgeDifficulty(t.difficulty), 1.0) for t in selected), 1),
            difficulty_label="Mixed",
            fit_score=round(total_co2 * 1.5 + total_xp * 0.5 + len(used_cats) * 10, 1),
            estimated_completion_pct=70.0,
        ))

    return combos


def _combo_streak_focus(templates: list[PledgeTemplate], user_id: int, n: int) -> list[OptimalCombo]:
    """Streak focus: pick pledges most likely to sustain streaks."""
    stats = get_user_pledge_stats(user_id)
    easy = [t for t in templates if t.difficulty == "easy"]
    medium = [t for t in templates if t.difficulty == "medium"]

    # Prefer easy for streak building
    pool = easy + medium[:len(easy)]
    random.shuffle(pool)
    combos = []

    for i in range(min(n, max(1, len(pool) // 3))):
        batch = pool[i*3:(i+1)*3]
        if not batch:
            break
        total_co2 = sum(t.weekly_co2_saved_kg for t in batch)
        total_xp = sum(t.xp_reward for t in batch)

        combos.append(OptimalCombo(
            combo_id=str(uuid.uuid4())[:8],
            strategy="streak_focus",
            title=f"Streak Builder {i+1}",
            description="Easy-to-maintain pledges designed for building long streaks.",
            pledges=[{"id": t.id, "title": t.title, "difficulty": t.difficulty} for t in batch],
            total_weekly_co2_kg=round(total_co2, 1),
            total_weekly_xp=total_xp,
            total_effort_score=round(sum(DIFFICULTY_WEIGHTS.get(PledgeDifficulty(t.difficulty), 1.0) for t in batch), 1),
            difficulty_label="🟢 Easy",
            fit_score=round(total_co2 * 1.0 + total_xp * 0.3 + 20, 1),
            estimated_completion_pct=92.0,
        ))

    return combos


def _combo_challenge_mode(templates: list[PledgeTemplate], n: int) -> list[OptimalCombo]:
    """Challenge mode: hard pledges for maximum XP."""
    hard = [t for t in templates if t.difficulty == "hard"]
    random.shuffle(hard)
    combos = []

    for i in range(min(n, max(1, len(hard) // 3))):
        batch = hard[i*3:(i+1)*3]
        if not batch:
            break
        total_co2 = sum(t.weekly_co2_saved_kg for t in batch)
        total_xp = sum(t.xp_reward for t in batch)

        combos.append(OptimalCombo(
            combo_id=str(uuid.uuid4())[:8],
            strategy="challenge_mode",
            title=f"Eco Warrior {i+1}",
            description="Hard pledges for maximum XP and CO₂ impact.",
            pledges=[{"id": t.id, "title": t.title, "difficulty": t.difficulty} for t in batch],
            total_weekly_co2_kg=round(total_co2, 1),
            total_weekly_xp=total_xp,
            total_effort_score=round(sum(DIFFICULTY_WEIGHTS.get(PledgeDifficulty(t.difficulty), 1.0) for t in batch), 1),
            difficulty_label="🔴 Hard",
            fit_score=round(total_co2 * 2.5 + total_xp * 0.8, 1),
            estimated_completion_pct=50.0,
        ))

    return combos


# ──────────────────────────────────────────────────────────────────────
# Difficulty ramping
# ──────────────────────────────────────────────────────────────────────

def recommend_difficulty(user_id: int) -> DifficultyRecommendation:
    """Recommend whether the user should try harder pledges."""
    profiles = build_habit_profiles(user_id)
    stats = get_user_pledge_stats(user_id)

    # Determine current average difficulty
    diff_scores = []
    for p in profiles:
        if p.difficulty_history:
            latest = p.difficulty_history[-1]
            diff_scores.append(DIFFICULTY_WEIGHTS.get(PledgeDifficulty(latest), 1.0))

    avg_difficulty = statistics.mean(diff_scores) if diff_scores else 1.0

    if avg_difficulty < 1.5:
        current_avg = "easy"
    elif avg_difficulty < 2.5:
        current_avg = "medium"
    else:
        current_avg = "hard"

    # Check readiness
    ready = False
    recommended = current_avg
    reason = ""

    # Ready to level up if completion rate >= 80% for 2+ weeks
    strong_profiles = [p for p in profiles if p.completion_rate >= 80 and p.weeks_enrolled >= 2]

    if current_avg == "easy" and len(strong_profiles) >= 1:
        ready = True
        recommended = "medium"
        reason = (f"Your easy pledges have {strong_profiles[0].completion_rate:.0f}% completion rate. "
                  f"You're ready for medium-difficulty pledges that save more CO₂!")
    elif current_avg == "medium" and len(strong_profiles) >= 2:
        ready = True
        recommended = "hard"
        reason = (f"Multiple pledges at 80%+ completion. Hard pledges give 2x CO₂ savings and 3x XP!")
    elif current_avg == "hard":
        reason = "You're already at maximum difficulty. Focus on maintaining streaks!"
    else:
        reason = f"Keep building consistency at your current level (completion rate needs to reach 80%)."

    return DifficultyRecommendation(
        current_avg=current_avg,
        recommended=recommended,
        reason=reason,
        ready=ready,
        weeks_at_current=max((p.weeks_enrolled for p in profiles), default=0),
        completion_rate_needed=HABIT_THRESHOLD_PCT,
    )


# ──────────────────────────────────────────────────────────────────────
# Weekly planner
# ──────────────────────────────────────────────────────────────────────

def generate_weekly_plan(user_id: int) -> WeeklyPlanner:
    """Generate a suggested weekly pledge plan."""
    profiles = build_habit_profiles(user_id)
    stats = get_user_pledge_stats(user_id)
    ws = current_week_start()

    active_profiles = [p for p in profiles if p.stage not in (HabitStage.DORMANT,)]
    dormant_profiles = [p for p in profiles if p.stage == HabitStage.DORMANT]

    # Priority: habit-forming pledges first, then dormant recovery, then new
    priority_pledges = []
    for p in active_profiles:
        tpl = get_template_by_id(p.template_id)
        if tpl:
            priority_pledges.append((p, tpl))

    # Sort by habit strength (weakest first = more need for attention)
    priority_pledges.sort(key=lambda x: x[0].habit_strength)

    # Fill up to recommended limit
    selected = []
    notes = []

    for profile, tpl in priority_pledges[:RECOMMENDED_ACTIVE_PLEDGES]:
        selected.append({
            "template_id": tpl.id,
            "title": tpl.title,
            "category": tpl.category,
            "difficulty": tpl.difficulty,
            "weekly_co2_kg": tpl.weekly_co2_saved_kg,
            "xp_reward": tpl.xp_reward,
            "habit_stage": profile.stage,
            "habit_strength": profile.habit_strength,
        })
        if profile.habit_strength < 0.3:
            notes.append(f"Focus on {tpl.title} — habit strength is low ({profile.habit_strength:.0%})")

    # Suggest dormant recovery
    for p in dormant_profiles[:1]:
        tpl = get_template_by_id(p.template_id)
        if tpl and len(selected) < MAX_ACTIVE_PLEDGES:
            selected.append({
                "template_id": tpl.id,
                "title": tpl.title,
                "category": tpl.category,
                "difficulty": tpl.difficulty,
                "weekly_co2_kg": tpl.weekly_co2_saved_kg,
                "xp_reward": tpl.xp_reward,
                "habit_stage": "dormant_recovery",
                "habit_strength": p.habit_strength,
            })
            notes.append(f"Rekindle {tpl.title} — start with just 1 check-in this week")

    # If room for more, suggest new pledges
    if len(selected) < RECOMMENDED_ACTIVE_PLEDGES:
        enrolled_ids = {s["template_id"] for s in selected}
        enrolled_ids |= {p.template_id for p in profiles}
        new_suggestions = suggest_optimal_combos(user_id, strategy="balanced", n=1)
        if new_suggestions:
            for pledge in new_suggestions[0].pledges:
                if pledge["id"] not in enrolled_ids and len(selected) < MAX_ACTIVE_PLEDGES:
                    tpl = get_template_by_id(pledge["id"])
                    if tpl:
                        selected.append({
                            "template_id": tpl.id,
                            "title": tpl.title,
                            "category": tpl.category,
                            "difficulty": tpl.difficulty,
                            "weekly_co2_kg": tpl.weekly_co2_saved_kg,
                            "xp_reward": tpl.xp_reward,
                            "habit_stage": "new",
                            "habit_strength": 0.0,
                        })
                        notes.append(f"Try {tpl.title} as a new pledge this week")

    # Daily focus suggestions
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    daily_focus: dict[str, str] = {}
    for i, day in enumerate(days):
        if selected:
            idx = i % len(selected)
            daily_focus[day] = f"Focus on {selected[idx]['title']}"

    total_co2 = sum(s["weekly_co2_kg"] for s in selected)
    total_xp = sum(s["xp_reward"] for s in selected)
    diff_mix = Counter(s["difficulty"] for s in selected)

    return WeeklyPlanner(
        week_start=ws,
        pledges=selected,
        daily_focus=daily_focus,
        total_co2_kg=round(total_co2, 1),
        total_xp=total_xp,
        difficulty_mix=dict(diff_mix),
        notes=notes,
    )


# ──────────────────────────────────────────────────────────────────────
# Streak protection
# ──────────────────────────────────────────────────────────────────────

def get_streak_protection(user_id: int) -> StreakProtection:
    """Check streak protection status."""
    stats = get_user_pledge_stats(user_id)
    ws = current_week_start()

    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM streak_protections WHERE user_id = ?", (user_id,))
        row = cur.fetchone()

        if not row:
            # Initialise
            cur.execute("""
                INSERT INTO streak_protections
                    (user_id, current_streak, extensions_remaining, last_completed_week)
                VALUES (?, ?, ?, ?)
            """, (user_id, stats.current_streak, STREAK_PROTECTION_EXTENSIONS, ws))
            conn.commit()
            return StreakProtection(
                user_id=user_id,
                current_streak=stats.current_streak,
                extensions_remaining=STREAK_PROTECTION_EXTENSIONS,
                last_completed_week=ws,
            )

        columns = [d[0] for d in cur.description]
        data = dict(zip(columns, row))

        # Calculate if streak is at risk
        last_completed = data["last_completed_week"]
        if last_completed:
            weeks_since = weeks_between(last_completed, ws)
            streak_at_risk = weeks_since >= 1
            protection_active = data["extensions_remaining"] > 0 and weeks_since <= 1
            weeks_until_break = max(0, STREAK_PROTECTION_EXTENSIONS - weeks_since + 1) if streak_at_risk else STREAK_PROTECTION_EXTENSIONS
        else:
            streak_at_risk = False
            protection_active = False
            weeks_until_break = STREAK_PROTECTION_EXTENSIONS

    return StreakProtection(
        user_id=user_id,
        current_streak=data["current_streak"],
        extensions_remaining=data["extensions_remaining"],
        last_completed_week=last_completed,
        streak_at_risk=streak_at_risk,
        protection_active=protection_active,
        weeks_until_break=weeks_until_break,
    )


def use_streak_protection(user_id: int) -> bool:
    """Use a streak protection extension."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT extensions_remaining FROM streak_protections WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row or row[0] <= 0:
            return False

        cur.execute("""
            UPDATE streak_protections
            SET extensions_remaining = extensions_remaining - 1,
                protection_active = 1
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()
        return cur.rowcount > 0


# ──────────────────────────────────────────────────────────────────────
# Habit insights
# ──────────────────────────────────────────────────────────────────────

def generate_habit_insights(user_id: int) -> list[HabitInsight]:
    """Generate insights specifically about habit formation."""
    profiles = build_habit_profiles(user_id)
    stats = get_user_pledge_stats(user_id)
    insights: list[HabitInsight] = []

    # Overall habit strength
    if profiles:
        avg_strength = sum(p.habit_strength for p in profiles) / len(profiles)
        insights.append(HabitInsight(
            insight_type="overall_strength",
            title="📊 Average Habit Strength",
            body=f"Your average habit strength across {len(profiles)} pledge(s) is {avg_strength:.0%}.",
            metric=avg_strength,
            recommendation="Focus on the weakest habit to improve overall consistency.",
        ))

    # Stage distribution
    stage_counts = Counter(p.stage for p in profiles)
    for stage, count in stage_counts.items():
        label = stage.replace("_", " ").title()
        insights.append(HabitInsight(
            insight_type=f"stage_{stage}",
            title=f"📋 {label} Pledges",
            body=f"You have {count} pledge(s) in the {label} stage.",
            metric=float(count),
        ))

    # Weakest habit
    if profiles:
        weakest = min(profiles, key=lambda p: p.habit_strength)
        if weakest.habit_strength < 0.4:
            insights.append(HabitInsight(
                insight_type="weakest_habit",
                title="⚠️ Weakest Habit",
                body=f"**{weakest.template_title}** has the lowest habit strength ({weakest.habit_strength:.0%}). "
                     f"Consider checking in more frequently or reducing difficulty.",
                metric=weakest.habit_strength,
                recommendation="Check in daily for this pledge to rebuild habit strength.",
            ))

    # Habit formation progress
    forming = [p for p in profiles if p.stage in (HabitStage.BUILDING, HabitStage.REINFORCING)]
    if forming:
        for p in forming:
            weeks_left = max(0, HABIT_FORMATION_WEEKS - p.weeks_enrolled)
            if weeks_left > 0:
                insights.append(HabitInsight(
                    insight_type="formation_progress",
                    title=f"🔄 Habit Forming: {p.template_title}",
                    body=f"~{weeks_left} more weeks until this becomes automatic. "
                         f"You're at week {p.weeks_enrolled}/{HABIT_FORMATION_WEEKS}.",
                    metric=float(p.weeks_enrolled / HABIT_FORMATION_WEEKS),
                    recommendation=f"Keep checking in for {p.template_title} every week!",
                ))

    return insights


# ──────────────────────────────────────────────────────────────────────
# Schedule preferences
# ──────────────────────────────────────────────────────────────────────

def get_schedule_preferences(user_id: int) -> dict[str, Any]:
    """Get user's scheduling preferences."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM schedule_preferences WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            columns = [d[0] for d in cur.description]
            data = dict(zip(columns, row))
            return {
                "preferred_slot": data["preferred_slot"],
                "max_active_pledges": data["max_active_pledges"],
                "prefer_same_category": bool(data["prefer_same_category"]),
                "prefer_variety": bool(data["prefer_variety"]),
                "difficulty_preference": data["difficulty_preference"],
            }

    return {
        "preferred_slot": "anytime",
        "max_active_pledges": 3,
        "prefer_same_category": False,
        "prefer_variety": True,
        "difficulty_preference": "auto",
    }


def save_schedule_preferences(
    user_id: int,
    preferred_slot: str = "anytime",
    max_active_pledges: int = 3,
    prefer_same_category: bool = False,
    prefer_variety: bool = True,
    difficulty_preference: str = "auto",
) -> None:
    """Save user's scheduling preferences."""
    now = datetime.now().isoformat(timespec="seconds")
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO schedule_preferences
                (user_id, preferred_slot, max_active_pledges, prefer_same_category,
                 prefer_variety, difficulty_preference, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                preferred_slot = excluded.preferred_slot,
                max_active_pledges = excluded.max_active_pledges,
                prefer_same_category = excluded.prefer_same_category,
                prefer_variety = excluded.prefer_variety,
                difficulty_preference = excluded.difficulty_preference,
                updated_at = excluded.updated_at
        """, (user_id, preferred_slot, max_active_pledges,
              int(prefer_same_category), int(prefer_variety), difficulty_preference, now))
        conn.commit()


# ──────────────────────────────────────────────────────────────────────
# Serialisation
# ──────────────────────────────────────────────────────────────────────

def habit_profile_to_dict(p: HabitProfile) -> dict[str, Any]:
    return asdict(p)


def nudge_to_dict(n: Nudge) -> dict[str, Any]:
    return asdict(n)


def combo_to_dict(c: OptimalCombo) -> dict[str, Any]:
    return asdict(c)


def planner_to_dict(p: WeeklyPlanner) -> dict[str, Any]:
    return asdict(p)
