"""
Community Green Pledges – Core Module
======================================
Lets users make weekly sustainability pledges, track completion streaks,
earn XP, and view aggregate community impact.

Dependencies: none beyond the Python stdlib.
"""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from database_connection import database_connection

DB_NAME = "eco_buddy.db"

# ──────────────────────────────────────────────────────────────────────
# Pledge catalogue
# ──────────────────────────────────────────────────────────────────────

PLEDGE_CATEGORIES = {
    "energy": {"label": "⚡ Energy", "color": "#f59e0b"},
    "transport": {"label": "🚗 Transport", "color": "#3b82f6"},
    "diet": {"label": "🥗 Diet", "color": "#22c55e"},
    "waste": {"label": "♻️ Waste", "color": "#a855f7"},
    "water": {"label": "💧 Water", "color": "#06b6d4"},
    "lifestyle": {"label": "🌿 Lifestyle", "color": "#10b981"},
}

PLEDGE_CATALOG: list[dict[str, Any]] = [
    # ── Energy ──
    {
        "id": "energy_no_standby",
        "category": "energy",
        "title": "Power Down Standby",
        "description": "Unplug all chargers and turn off devices on standby every night for a full week.",
        "difficulty": "easy",
        "weekly_co2_saved_kg": 1.8,
        "xp_reward": 25,
        "eco_points": 5,
    },
    {
        "id": "energy_cold_wash",
        "category": "energy",
        "title": "Cold-Wash Clothes",
        "description": "Wash every load of laundry on cold (30 °C) this week.",
        "difficulty": "easy",
        "weekly_co2_saved_kg": 2.4,
        "xp_reward": 30,
        "eco_points": 6,
    },
    {
        "id": "energy_led_swap",
        "category": "energy",
        "title": "LED Light Swap",
        "description": "Replace at least 3 incandescent / CFL bulbs with LEDs this week.",
        "difficulty": "medium",
        "weekly_co2_saved_kg": 3.5,
        "xp_reward": 50,
        "eco_points": 10,
    },
    {
        "id": "energy_no_ac",
        "category": "energy",
        "title": "Air-Conditioning Free Day",
        "description": "Go one full day without using the air conditioner or heater.",
        "difficulty": "hard",
        "weekly_co2_saved_kg": 6.0,
        "xp_reward": 80,
        "eco_points": 16,
    },
    # ── Transport ──
    {
        "id": "transport_bike_week",
        "category": "transport",
        "title": "Bike-to-Work Week",
        "description": "Cycle to work or school every day this week instead of driving.",
        "difficulty": "hard",
        "weekly_co2_saved_kg": 14.0,
        "xp_reward": 100,
        "eco_points": 20,
    },
    {
        "id": "transport_public_transit",
        "category": "transport",
        "title": "Public Transit Week",
        "description": "Use public transit for all commutes this week.",
        "difficulty": "medium",
        "weekly_co2_saved_kg": 8.5,
        "xp_reward": 60,
        "eco_points": 12,
    },
    {
        "id": "transport_no_flights",
        "category": "transport",
        "title": "Flight-Free Week",
        "description": "Avoid all flights this week — choose a local or virtual alternative.",
        "difficulty": "easy",
        "weekly_co2_saved_kg": 50.0,
        "xp_reward": 70,
        "eco_points": 14,
    },
    {
        "id": "transport_carpool",
        "category": "transport",
        "title": "Carpool Champion",
        "description": "Carpool with at least 2 other people for your main commute.",
        "difficulty": "medium",
        "weekly_co2_saved_kg": 7.0,
        "xp_reward": 55,
        "eco_points": 11,
    },
    # ── Diet ──
    {
        "id": "diet_meatless_week",
        "category": "diet",
        "title": "Meatless Week",
        "description": "Eat no meat or fish for 7 consecutive days.",
        "difficulty": "medium",
        "weekly_co2_saved_kg": 12.6,
        "xp_reward": 65,
        "eco_points": 13,
    },
    {
        "id": "diet_zero_waste_meal",
        "category": "diet",
        "title": "Zero-Waste Meal",
        "description": "Cook and eat one fully zero-waste meal with no packaging scraps.",
        "difficulty": "easy",
        "weekly_co2_saved_kg": 1.2,
        "xp_reward": 20,
        "eco_points": 4,
    },
    {
        "id": "diet_local_only",
        "category": "diet",
        "title": "Locally-Sourced Meals",
        "description": "Buy all groceries from local farmers or markets this week.",
        "difficulty": "hard",
        "weekly_co2_saved_kg": 5.0,
        "xp_reward": 90,
        "eco_points": 18,
    },
    {
        "id": "diet_compost",
        "category": "diet",
        "title": "Compost Kickstart",
        "description": "Start composting food scraps and continue for the entire week.",
        "difficulty": "easy",
        "weekly_co2_saved_kg": 3.0,
        "xp_reward": 35,
        "eco_points": 7,
    },
    # ── Waste ──
    {
        "id": "waste_no_plastic",
        "category": "waste",
        "title": "Plastic-Free Week",
        "description": "Refuse all single-use plastics for 7 days.",
        "difficulty": "hard",
        "weekly_co2_saved_kg": 4.2,
        "xp_reward": 85,
        "eco_points": 17,
    },
    {
        "id": "waste_reuse_jars",
        "category": "waste",
        "title": "Jar Reuse Streak",
        "description": "Reuse glass jars for storage instead of buying new containers.",
        "difficulty": "easy",
        "weekly_co2_saved_kg": 1.0,
        "xp_reward": 20,
        "eco_points": 4,
    },
    {
        "id": "waste_donate_clothes",
        "category": "waste",
        "title": "Closet Clean-Out",
        "description": "Donate or recycle at least 5 items of clothing this week.",
        "difficulty": "medium",
        "weekly_co2_saved_kg": 2.5,
        "xp_reward": 45,
        "eco_points": 9,
    },
    # ── Water ──
    {
        "id": "water_5min_shower",
        "category": "water",
        "title": "5-Minute Showers",
        "description": "Keep every shower to 5 minutes or less for the full week.",
        "difficulty": "medium",
        "weekly_co2_saved_kg": 1.5,
        "xp_reward": 40,
        "eco_points": 8,
    },
    {
        "id": "water_tap_only",
        "category": "water",
        "title": "Tap Water Only",
        "description": "Drink only tap water — no bottled water at all.",
        "difficulty": "easy",
        "weekly_co2_saved_kg": 1.0,
        "xp_reward": 25,
        "eco_points": 5,
    },
    {
        "id": "water_fix_leaks",
        "category": "water",
        "title": "Leak Fixer",
        "description": "Find and repair at least one dripping tap or running toilet.",
        "difficulty": "medium",
        "weekly_co2_saved_kg": 2.0,
        "xp_reward": 55,
        "eco_points": 11,
    },
    # ── Lifestyle ──
    {
        "id": "lifestyle_nature_hour",
        "category": "lifestyle",
        "title": "Nature Hour",
        "description": "Spend at least 1 hour outside in nature every day this week.",
        "difficulty": "easy",
        "weekly_co2_saved_kg": 0.5,
        "xp_reward": 30,
        "eco_points": 6,
    },
    {
        "id": "lifestyle_digital_detox",
        "category": "lifestyle",
        "title": "Digital Detox Day",
        "description": "Go 24 hours without screens for non-essential use.",
        "difficulty": "medium",
        "weekly_co2_saved_kg": 1.2,
        "xp_reward": 45,
        "eco_points": 9,
    },
    {
        "id": "lifestyle_plant_tree",
        "category": "lifestyle",
        "title": "Tree Planter",
        "description": "Plant a tree or seedling this week and care for it.",
        "difficulty": "hard",
        "weekly_co2_saved_kg": 22.0,
        "xp_reward": 120,
        "eco_points": 24,
    },
]


# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────

class PledgeDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


DIFFICULTY_MULTIPLIER = {
    PledgeDifficulty.EASY: 1.0,
    PledgeDifficulty.MEDIUM: 1.5,
    PledgeDifficulty.HARD: 2.0,
}


@dataclass
class PledgeTemplate:
    id: str
    category: str
    title: str
    description: str
    difficulty: str
    weekly_co2_saved_kg: float
    xp_reward: int
    eco_points: int

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PledgeTemplate":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ActivePledge:
    pledge_id: str
    template_id: str
    user_id: int
    week_start: str
    status: str = "active"       # active | completed | missed | abandoned
    day_checkins: int = 0
    days_completed: int = 0
    completion_pct: float = 0.0
    earned_xp: int = 0
    earned_eco_points: int = 0
    created_at: str = ""
    completed_at: str = ""


@dataclass
class UserPledgeStats:
    user_id: int
    total_pledges_made: int = 0
    total_pledges_completed: int = 0
    total_pledges_missed: int = 0
    current_streak: int = 0
    best_streak: int = 0
    total_xp_earned: int = 0
    total_eco_points: int = 0
    total_co2_saved_kg: float = 0.0
    completion_rate_pct: float = 0.0
    level: str = "Seedling"
    badges: list[str] = field(default_factory=list)


@dataclass
class CommunityPledgeImpact:
    total_participants: int = 0
    total_pledges: int = 0
    total_completed: int = 0
    community_co2_saved_kg: float = 0.0
    top_categories: list[dict[str, Any]] = field(default_factory=list)
    weekly_trend: list[dict[str, Any]] = field(default_factory=list)
    active_this_week: int = 0


# ──────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    """Return a raw connection (caller must close)."""
    return sqlite3.connect(DB_NAME)


def init_pledge_tables() -> None:
    """Create pledge tables if they don't already exist."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS green_pledges (
                id              TEXT PRIMARY KEY,
                template_id     TEXT NOT NULL,
                user_id         INTEGER NOT NULL,
                week_start      TEXT NOT NULL,
                status          TEXT DEFAULT 'active',
                day_checkins    INTEGER DEFAULT 0,
                days_completed  INTEGER DEFAULT 0,
                completion_pct  REAL DEFAULT 0.0,
                earned_xp       INTEGER DEFAULT 0,
                earned_eco_pts  INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT '',
                completed_at    TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pledge_checkins (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pledge_id   TEXT NOT NULL,
                user_id     INTEGER NOT NULL,
                day_date    TEXT NOT NULL,
                note        TEXT DEFAULT '',
                checked_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pledge_id) REFERENCES green_pledges(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pledge_stats (
                user_id             INTEGER PRIMARY KEY,
                total_made          INTEGER DEFAULT 0,
                total_completed     INTEGER DEFAULT 0,
                total_missed        INTEGER DEFAULT 0,
                current_streak      INTEGER DEFAULT 0,
                best_streak         INTEGER DEFAULT 0,
                total_xp            INTEGER DEFAULT 0,
                total_eco_points    INTEGER DEFAULT 0,
                total_co2_saved_kg  REAL DEFAULT 0.0,
                updated_at          TEXT DEFAULT ''
            )
        """)
        conn.commit()


# ──────────────────────────────────────────────────────────────────────
# Template helpers
# ──────────────────────────────────────────────────────────────────────

def get_all_templates() -> list[PledgeTemplate]:
    """Return every pledge in the catalogue as dataclass instances."""
    return [PledgeTemplate.from_dict(p) for p in PLEDGE_CATALOG]


def get_templates_by_category(category: str) -> list[PledgeTemplate]:
    return [t for t in get_all_templates() if t.category == category]


def get_template_by_id(template_id: str) -> Optional[PledgeTemplate]:
    for t in get_all_templates():
        if t.id == template_id:
            return t
    return None


def get_categories() -> dict[str, dict[str, str]]:
    return dict(PLEDGE_CATEGORIES)


# ──────────────────────────────────────────────────────────────────────
# Week helpers
# ──────────────────────────────────────────────────────────────────────

def current_week_start(dt: Optional[datetime] = None) -> str:
    """Return ISO date string for Monday of the current week."""
    dt = dt or datetime.now()
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")


def current_week_end(dt: Optional[datetime] = None) -> str:
    """Return ISO date string for Sunday of the current week."""
    dt = dt or datetime.now()
    monday = dt - timedelta(days=dt.weekday())
    sunday = monday + timedelta(days=6)
    return sunday.strftime("%Y-%m-%d")


def weeks_between(start: str, end: str) -> int:
    """Number of full weeks between two ISO date strings."""
    d1 = datetime.strptime(start, "%Y-%m-%d")
    d2 = datetime.strptime(end, "%Y-%m-%d")
    return max(0, (d2 - d1).days // 7)


# ──────────────────────────────────────────────────────────────────────
# Pledge CRUD
# ──────────────────────────────────────────────────────────────────────

def create_pledge(user_id: int, template_id: str,
                  week: Optional[str] = None) -> ActivePledge | None:
    """Enrol the user in a pledge for the given week. Returns None on conflict."""
    tpl = get_template_by_id(template_id)
    if tpl is None:
        return None
    week = week or current_week_start()
    pledge_id = str(uuid.uuid4())[:12]

    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        # Check duplicate
        cur.execute(
            "SELECT id FROM green_pledges WHERE user_id=? AND template_id=? AND week_start=?",
            (user_id, template_id, week),
        )
        if cur.fetchone():
            return None

        now = datetime.now().isoformat(timespec="seconds")
        cur.execute("""
            INSERT INTO green_pledges
                (id, template_id, user_id, week_start, status, created_at)
            VALUES (?, ?, ?, ?, 'active', ?)
        """, (pledge_id, template_id, user_id, week, now))

        # Update stats total_made
        cur.execute("""
            INSERT INTO pledge_stats (user_id, total_made, updated_at)
            VALUES (?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                total_made = total_made + 1,
                updated_at = excluded.updated_at
        """, (user_id, now))
        conn.commit()

    return _row_to_active_pledge({
        "id": pledge_id, "template_id": template_id,
        "user_id": user_id, "week_start": week,
        "status": "active", "day_checkins": 0, "days_completed": 0,
        "completion_pct": 0.0, "earned_xp": 0, "earned_eco_pts": 0,
        "created_at": now, "completed_at": "",
    })


def checkin_pledge(user_id: int, pledge_id: str,
                   day_date: Optional[str] = None,
                   note: str = "") -> ActivePledge | None:
    """Record a daily check-in for a pledge. Returns updated pledge."""
    day_date = day_date or datetime.now().strftime("%Y-%m-%d")

    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM green_pledges WHERE id=? AND user_id=?",
            (pledge_id, user_id),
        )
        row = cur.fetchone()
        if not row or row["status"] != "active":
            return None

        # Prevent duplicate check-in on same day
        cur.execute(
            "SELECT id FROM pledge_checkins WHERE pledge_id=? AND day_date=?",
            (pledge_id, day_date),
        )
        if cur.fetchone():
            return None  # Already checked in today

        cur.execute("""
            INSERT INTO pledge_checkins (pledge_id, user_id, day_date, note)
            VALUES (?, ?, ?, ?)
        """, (pledge_id, user_id, day_date, note))

        new_checkins = (row["day_checkins"] or 0) + 1
        days_completed = 7 if new_checkins >= 7 else new_checkins
        completion_pct = round(min(new_checkins / 7.0, 1.0) * 100, 1)

        tpl = get_template_by_id(row["template_id"])
        earned_xp = 0
        earned_eco = 0
        new_status = "active"

        if new_checkins >= 7 and tpl:
            earned_xp = tpl.xp_reward
            earned_eco = tpl.eco_points
            new_status = "completed"

        cur.execute("""
            UPDATE green_pledges SET
                day_checkins=?, days_completed=?, completion_pct=?,
                earned_xp=?, earned_eco_pts=?, status=?,
                completed_at=CASE WHEN ?='completed' THEN ? ELSE completed_at END
            WHERE id=?
        """, (
            new_checkins, days_completed, completion_pct,
            earned_xp, earned_eco, new_status,
            new_status, datetime.now().isoformat(timespec="seconds"),
            pledge_id,
        ))

        # Update user stats if completed
        if new_status == "completed" and tpl:
            _update_stats_on_complete(cur, user_id, tpl)

        conn.commit()

    return get_active_pledge(user_id, pledge_id)


def abandon_pledge(user_id: int, pledge_id: str) -> bool:
    """Mark a pledge as abandoned."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE green_pledges SET status='abandoned' WHERE id=? AND user_id=?",
            (pledge_id, user_id),
        )
        if cur.rowcount:
            conn.commit()
            return True
    return False


def get_active_pledge(user_id: int, pledge_id: str) -> Optional[ActivePledge]:
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM green_pledges WHERE id=? AND user_id=?",
            (pledge_id, user_id),
        )
        row = cur.fetchone()
        if row:
            return _row_to_active_pledge(dict(row))
    return None


def get_user_weekly_pledges(user_id: int, week: Optional[str] = None) -> list[ActivePledge]:
    week = week or current_week_start()
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM green_pledges WHERE user_id=? AND week_start=? ORDER BY created_at",
            (user_id, week),
        )
        return [_row_to_active_pledge(dict(r)) for r in cur.fetchall()]


def get_user_all_pledges(user_id: int, limit: int = 50) -> list[ActivePledge]:
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM green_pledges WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [_row_to_active_pledge(dict(r)) for r in cur.fetchall()]


def get_pledge_checkin_dates(pledge_id: str) -> list[str]:
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT day_date FROM pledge_checkins WHERE pledge_id=? ORDER BY day_date",
            (pledge_id,),
        )
        return [r[0] for r in cur.fetchall()]


# ──────────────────────────────────────────────────────────────────────
# User stats
# ──────────────────────────────────────────────────────────────────────

def get_user_pledge_stats(user_id: int) -> UserPledgeStats:
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM pledge_stats WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if row:
            stats = UserPledgeStats(
                user_id=user_id,
                total_pledges_made=row["total_made"],
                total_pledges_completed=row["total_completed"],
                total_pledges_missed=row["total_missed"],
                current_streak=row["current_streak"],
                best_streak=row["best_streak"],
                total_xp_earned=row["total_xp"],
                total_eco_points=row["total_eco_points"],
                total_co2_saved_kg=row["total_co2_saved_kg"],
            )
        else:
            stats = UserPledgeStats(user_id=user_id)

        if stats.total_pledges_made > 0:
            stats.completion_rate_pct = round(
                stats.total_pledges_completed / stats.total_pledges_made * 100, 1
            )
        stats.level = _compute_level(stats)
        stats.badges = _compute_badges(stats)
        return stats


def _update_stats_on_complete(cur: sqlite3.Cursor, user_id: int, tpl: PledgeTemplate) -> None:
    cur.execute("""
        INSERT INTO pledge_stats (user_id, total_completed, total_xp, total_eco_points, total_co2_saved_kg, updated_at)
        VALUES (?, 1, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            total_completed = total_completed + 1,
            total_xp = total_xp + excluded.total_xp,
            total_eco_points = total_eco_points + excluded.total_eco_points,
            total_co2_saved_kg = total_co2_saved_kg + excluded.total_co2_saved_kg,
            updated_at = excluded.updated_at
    """, (
        user_id, tpl.xp_reward, tpl.eco_points,
        tpl.weekly_co2_saved_kg,
        datetime.now().isoformat(timespec="seconds"),
    ))


# ──────────────────────────────────────────────────────────────────────
# Level & badges
# ──────────────────────────────────────────────────────────────────────

LEVEL_THRESHOLDS: list[tuple[str, int]] = [
    ("Seedling", 0),
    ("Sapling", 50),
    ("Sprout", 150),
    ("Guardian", 400),
    ("Champion", 800),
    ("Eco Legend", 1500),
]


def _compute_level(stats: UserPledgeStats) -> str:
    xp = stats.total_xp_earned
    level_name = "Seedling"
    for name, threshold in LEVEL_THRESHOLDS:
        if xp >= threshold:
            level_name = name
        else:
            break
    return level_name


def _compute_badges(stats: UserPledgeStats) -> list[str]:
    badges: list[str] = []
    if stats.total_pledges_completed >= 1:
        badges.append("🌱 First Pledge")
    if stats.total_pledges_completed >= 5:
        badges.append("🔥 Pledge Starter")
    if stats.total_pledges_completed >= 10:
        badges.append("💪 Pledge Warrior")
    if stats.total_pledges_completed >= 25:
        badges.append("🏆 Pledge Master")
    if stats.current_streak >= 3:
        badges.append("⚡ 3-Week Streak")
    if stats.current_streak >= 6:
        badges.append("🌟 6-Week Streak")
    if stats.current_streak >= 12:
        badges.append("👑 12-Week Streak")
    if stats.total_co2_saved_kg >= 10:
        badges.append("🌍 10 kg CO₂ Saved")
    if stats.total_co2_saved_kg >= 50:
        badges.append("🌎 50 kg CO₂ Saved")
    if stats.total_co2_saved_kg >= 100:
        badges.append("🌐 100 kg CO₂ Saved")
    if stats.completion_rate_pct >= 90 and stats.total_pledges_completed >= 5:
        badges.append("🎯 90% Completion")
    if stats.total_eco_points >= 100:
        badges.append("💎 100 Eco Points")
    return badges


# ──────────────────────────────────────────────────────────────────────
# Streak calculation
# ──────────────────────────────────────────────────────────────────────

def calculate_streak(user_id: int) -> tuple[int, int]:
    """Return (current_streak, best_streak) in completed weeks."""
    pledges = get_user_all_pledges(user_id, limit=200)
    completed_weeks = sorted(
        {p.week_start for p in pledges if p.status == "completed"},
        reverse=True,
    )
    if not completed_weeks:
        return 0, 0

    # Current streak: consecutive weeks ending at latest completed week
    current = 1
    expected = datetime.strptime(completed_weeks[0], "%Y-%m-%d")
    for ws in completed_weeks[1:]:
        d = datetime.strptime(ws, "%Y-%m-%d")
        if (expected - d).days == 7:
            current += 1
            expected = d
        else:
            break

    # Best streak: scan all
    sorted_weeks = sorted({ws for ws in completed_weeks})
    best = 1
    run = 1
    for i in range(1, len(sorted_weeks)):
        d_prev = datetime.strptime(sorted_weeks[i - 1], "%Y-%m-%d")
        d_cur = datetime.strptime(sorted_weeks[i], "%Y-%m-%d")
        if (d_cur - d_prev).days == 7:
            run += 1
            best = max(best, run)
        else:
            run = 1

    return current, best


# ──────────────────────────────────────────────────────────────────────
# Community impact
# ──────────────────────────────────────────────────────────────────────

def get_community_impact() -> CommunityPledgeImpact:
    impact = CommunityPledgeImpact()
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT COUNT(DISTINCT user_id) AS cnt FROM green_pledges")
        row = cur.fetchone()
        impact.total_participants = row["cnt"] if row else 0

        cur.execute("SELECT COUNT(*) AS cnt FROM green_pledges")
        row = cur.fetchone()
        impact.total_pledges = row["cnt"] if row else 0

        cur.execute("SELECT COUNT(*) AS cnt FROM green_pledges WHERE status='completed'")
        row = cur.fetchone()
        impact.total_completed = row["cnt"] if row else 0

        cur.execute("SELECT SUM(total_co2_saved_kg) AS total FROM pledge_stats")
        row = cur.fetchone()
        impact.community_co2_saved_kg = round(row["total"] or 0.0, 2)

        cur.execute("""
            SELECT g.template_id, COUNT(*) AS cnt
            FROM green_pledges g
            JOIN pledge_stats p ON g.user_id = p.user_id
            GROUP BY g.template_id
            ORDER BY cnt DESC
            LIMIT 5
        """)
        impact.top_categories = [
            {"template_id": r["template_id"], "count": r["cnt"]}
            for r in cur.fetchall()
        ]

        week = current_week_start()
        cur.execute(
            "SELECT COUNT(DISTINCT user_id) AS cnt FROM green_pledges WHERE week_start=?",
            (week,),
        )
        row = cur.fetchone()
        impact.active_this_week = row["cnt"] if row else 0

        # Weekly trend (last 8 weeks)
        trend: list[dict[str, Any]] = []
        for i in range(8):
            d = datetime.now() - timedelta(weeks=i)
            ws = (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")
            cur.execute("""
                SELECT COUNT(*) AS completed, COUNT(DISTINCT user_id) AS users
                FROM green_pledges WHERE week_start=?
            """, (ws,))
            r = cur.fetchone()
            trend.append({
                "week": ws,
                "completed": r["completed"] if r else 0,
                "users": r["users"] if r else 0,
            })
        impact.weekly_trend = list(reversed(trend))

    return impact


# ──────────────────────────────────────────────────────────────────────
# Impact calculations
# ──────────────────────────────────────────────────────────────────────

def estimate_co2_equivalents(co2_kg: float) -> dict[str, Any]:
    """Convert CO₂ kg into relatable everyday equivalents."""
    return {
        "co2_kg": round(co2_kg, 2),
        "car_km": round(co2_kg / 0.19, 1),
        "trees_needed": round(co2_kg / 22.0, 2),
        "smartphone_charges": round(co2_kg / 0.008, 0),
        "beef_burgers": round(co2_kg / 3.6, 1),
        "flight_minutes": round(co2_kg / 0.255, 0),
        "shower_minutes": round(co2_kg / 0.025, 0),
    }


def score_pledge_fit(user_footprint: float, template: PledgeTemplate) -> dict[str, Any]:
    """Rank how well a pledge fits a user's footprint profile."""
    if user_footprint <= 0:
        impact_ratio = 0.0
    else:
        impact_ratio = template.weekly_co2_saved_kg / user_footprint * 100

    difficulty_score = {"easy": 3, "medium": 6, "hard": 9}.get(template.difficulty, 5)
    fit_score = round(impact_ratio * 2 + difficulty_score, 1)

    return {
        "template_id": template.id,
        "title": template.title,
        "category": template.category,
        "difficulty": template.difficulty,
        "weekly_co2_saved_kg": template.weekly_co2_saved_kg,
        "impact_ratio_pct": round(impact_ratio, 2),
        "difficulty_score": difficulty_score,
        "fit_score": fit_score,
    }


def suggest_pledges_for_user(
    user_footprint: float,
    user_pledges: list[ActivePledge],
    n: int = 4,
) -> list[dict[str, Any]]:
    """Suggest the top N pledges based on fit score, avoiding already-enrolled ones."""
    enrolled_ids = {p.template_id for p in user_pledges}
    suggestions = []
    for tpl in get_all_templates():
        if tpl.id in enrolled_ids:
            continue
        fit = score_pledge_fit(user_footprint, tpl)
        suggestions.append(fit)
    suggestions.sort(key=lambda x: x["fit_score"], reverse=True)
    return suggestions[:n]


# ──────────────────────────────────────────────────────────────────────
# Projections
# ──────────────────────────────────────────────────────────────────────

def project_annual_co2_saved(user_id: int) -> dict[str, Any]:
    """Estimate annual CO₂ savings based on current pace."""
    stats = get_user_pledge_stats(user_id)
    weeks_tracked = max(
        weeks_between(
            get_user_all_pledges(user_id, limit=1)[-1].week_start,
            current_week_start(),
        ),
        1,
    )
    weekly_avg = stats.total_co2_saved_kg / weeks_tracked
    annual_estimate = weekly_avg * 52
    return {
        "weeks_tracked": weeks_tracked,
        "weekly_avg_co2_kg": round(weekly_avg, 2),
        "annual_estimate_kg": round(annual_estimate, 2),
        "equivalents": estimate_co2_equivalents(annual_estimate),
    }


def weekly_streak_calendar(user_id: int, weeks: int = 12) -> list[dict[str, Any]]:
    """Return a list of recent weeks with completion status for calendar display."""
    pledges = get_user_all_pledges(user_id, limit=weeks * 5)
    completed_weeks = {p.week_start for p in pledges if p.status == "completed"}
    active_weeks = {p.week_start for p in pledges if p.status == "active"}

    calendar: list[dict[str, Any]] = []
    now = datetime.now()
    for i in range(weeks - 1, -1, -1):
        d = now - timedelta(weeks=i)
        monday = d - timedelta(days=d.weekday())
        ws = monday.strftime("%Y-%m-%d")
        calendar.append({
            "week_start": ws,
            "status": "completed" if ws in completed_weeks else ("active" if ws in active_weeks else "empty"),
        })
    return calendar


# ──────────────────────────────────────────────────────────────────────
# Utility / serialisation
# ──────────────────────────────────────────────────────────────────────

def _row_to_active_pledge(row: dict[str, Any]) -> ActivePledge:
    return ActivePledge(
        pledge_id=row["id"],
        template_id=row["template_id"],
        user_id=row["user_id"],
        week_start=row["week_start"],
        status=row["status"],
        day_checkins=row.get("day_checkins", 0),
        days_completed=row.get("days_completed", 0),
        completion_pct=row.get("completion_pct", 0.0),
        earned_xp=row.get("earned_xp", 0),
        earned_eco_points=row.get("earned_eco_pts", row.get("earned_eco_points", 0)),
        created_at=row.get("created_at", ""),
        completed_at=row.get("completed_at", ""),
    )


def pledge_to_dict(p: ActivePledge) -> dict[str, Any]:
    d = asdict(p)
    tpl = get_template_by_id(p.template_id)
    if tpl:
        d["title"] = tpl.title
        d["description"] = tpl.description
        d["category"] = tpl.category
        d["difficulty"] = tpl.difficulty
        d["category_info"] = PLEDGE_CATEGORIES.get(tpl.category, {})
    return d


def export_user_pledges_json(user_id: int) -> str:
    """Serialise all user pledges as a JSON string."""
    pledges = get_user_all_pledges(user_id)
    data = [pledge_to_dict(p) for p in pledges]
    return json.dumps(data, indent=2, default=str)
