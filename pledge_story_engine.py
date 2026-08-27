"""
Pledge Story Engine
====================
Transforms pledge data into compelling environmental narratives,
generates shareable impact stories, creates visual story cards,
and produces monthly eco-journal entries based on the user's
sustainability journey.

Dependencies: green_pledge_tracker, pledge_impact_engine, database_connection.
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
    PLEDGE_CATEGORIES,
    PledgeTemplate,
    current_week_start,
    current_week_end,
    get_all_templates,
    get_template_by_id,
    get_user_all_pledges,
    get_user_pledge_stats,
    get_pledge_checkin_dates,
    estimate_co2_equivalents,
    weeks_between,
)
from pledge_impact_engine import (
    get_weekly_impacts,
    analyse_trend,
    predict_future_impact,
    check_milestones,
    generate_insights,
    MILESTONE_DEFINITIONS,
)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

STORY_THEMES = {
    "hope": {
        "title": "A Story of Hope",
        "opening_templates": [
            "Every small action plants a seed of change.",
            "The journey to a greener world begins with a single step.",
            "In a world facing climate challenges, one person decided to act.",
        ],
        "color_primary": "#22c55e",
        "color_secondary": "#86efac",
        "icon": "🌱",
    },
    "adventure": {
        "title": "The Eco Adventure",
        "opening_templates": [
            "An epic quest for sustainability begins...",
            "Armed with determination and a reusable bag, a hero emerged.",
            "The challenge: reduce your footprint. The weapon: everyday choices.",
        ],
        "color_primary": "#3b82f6",
        "color_secondary": "#93c5fd",
        "icon": "🗺️",
    },
    "community": {
        "title": "Together We Grow",
        "opening_templates": [
            "Alone, we can do so little. Together, we can change the world.",
            "A community united by green pledges, driven by shared purpose.",
            "When eco-warriors join forces, the impact multiplies.",
        ],
        "color_primary": "#f59e0b",
        "color_secondary": "#fcd34d",
        "icon": "🤝",
    },
    "transformation": {
        "title": "A Greener Tomorrow",
        "opening_templates": [
            "From ordinary habits to extraordinary impact.",
            "The transformation began with awareness and grew with action.",
            "Every week brought new choices, new challenges, new victories.",
        ],
        "color_primary": "#a855f7",
        "color_secondary": "#c084fc",
        "icon": "🦋",
    },
    "resilience": {
        "title": "Never Give Up",
        "opening_templates": [
            "Setbacks are setups for comebacks.",
            "Streaks broken, spirits not. The eco-warrior persists.",
            "Resilience isn't about never falling — it's about rising every time.",
        ],
        "color_primary": "#ef4444",
        "color_secondary": "#fca5a5",
        "icon": "🔥",
    },
}

NARRATIVE_TEMPLATES = {
    "weekly_summary": [
        "This week, {name} enrolled in {n_pledges} pledge(s) across {categories} and completed {completed} of them, "
        "saving an estimated {co2:.1f} kg of CO₂ — equivalent to {equivalent}.",
        "Another week, another victory for the planet. {name} checked in {checkins} times, "
        "ticking off {completed} pledge(s) and preventing {co2:.1f} kg of CO₂ from entering the atmosphere.",
        "{name}'s green journey continued this week with {checkins} dedicated check-ins. "
        "Through {n_pledges} active pledge(s), they saved {co2:.1f} kg of CO₂.",
    ],
    "milestone_celebration": [
        "🎉 Milestone unlocked! {name} has just {achievement}! "
        "That's {metric_value:.1f} of pure environmental dedication.",
        "🏆 Achievement alert: {name} reached the {achievement} milestone! "
        "Their commitment to sustainability is truly inspiring.",
        "⭐ {name} just earned the {achievement} badge! "
        "Every milestone represents real impact on our planet.",
    ],
    "streak_narrative": [
        "🔥 {name} is on fire! A {streak}-week streak and counting — "
        "that's {streak} consecutive weeks of choosing the planet over convenience.",
        "⚡ Consistency is key, and {name} has found the rhythm. "
        "{streak} weeks of unbroken commitment to green pledges.",
        "🌟 {streak} weeks strong! {name}'s dedication is building "
        "something powerful — a habit that lasts.",
    ],
    "co2_impact": [
        "🌍 {name} has saved {co2:.1f} kg of CO₂ — that's like planting {trees:.0f} trees "
        "or taking a car off the road for {km:.0f} km.",
        "🍃 Through persistent action, {name} prevented {co2:.1f} kg of CO₂ emissions. "
        "Real numbers, real impact, real change.",
        "💪 {co2:.1f} kg of CO₂ kept out of the atmosphere. "
        "That's {equivalent} — all through everyday green choices.",
    ],
    "journey_beginning": [
        "📖 Every great story has a beginning. {name}'s sustainability journey started "
        "with a single pledge — a promise to the planet.",
        "🌟 The first step is always the hardest, but {name} took it. "
        "What started as one pledge is growing into a movement.",
        "🌱 Day one. One pledge. One decision to make a difference. "
        "This is where {name}'s green story begins.",
    ],
    "group_story": [
        "👥 In the group '{group_name}', {n_members} eco-warriors are writing "
        "a collective story of change — {co2:.1f} kg of CO₂ saved together.",
        "🤝 {group_name}: a band of sustainability champions. "
        "{n_members} members, {completed} pledges completed, one shared mission.",
        "🌍 The power of community: '{group_name}' has pooled "
        "{co2:.1f} kg of CO₂ savings. Together, they're unstoppable.",
    ],
    "prediction_story": [
        "🔮 If current trends continue, {name} will save an additional "
        "{predicted_co2:.1f} kg of CO₂ over the next 12 weeks — "
        "that's {equivalent} of real-world impact.",
        "📈 The future looks green. Based on {name}'s pace, "
        "the next 12 weeks could bring {predicted_co2:.1f} kg of CO₂ savings.",
        "🌟 Momentum is building. {name}'s trajectory points toward "
        "{predicted_co2:.1f} kg of additional CO₂ savings in the coming quarter.",
    ],
}

CO2_EQUIVALENTS = [
    ("planting {n:.0f} trees", lambda co2: co2 / 22.0),
    ("driving {n:.0f} fewer km", lambda co2: co2 / 0.19),
    ("saving {n:.0f} smartphone charges", lambda co2: co2 / 0.008),
    ("skipping {n:.0f} beef burgers", lambda co2: co2 / 3.6),
    ("avoiding {n:.0f} minutes of flying", lambda co2: co2 / 0.255),
    ("taking {n:.0f} fewer showers", lambda co2: co2 / 0.025),
]


class StoryType(str, Enum):
    WEEKLY_SUMMARY = "weekly_summary"
    MILESTONE_CELEBRATION = "milestone_celebration"
    STREAK_NARRATIVE = "streak_narrative"
    CO2_IMPACT = "co2_impact"
    JOURNEY_BEGINNING = "journey_beginning"
    GROUP_STORY = "group_story"
    PREDICTION_STORY = "prediction_story"
    MONTHLY_JOURNAL = "monthly_journal"
    CUSTOM = "custom"


# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────

@dataclass
class StoryCard:
    """A visual story card for sharing."""
    story_id: str
    user_id: int
    story_type: str
    theme: str
    title: str
    narrative: str
    headline_stat: str
    stat_value: float
    stat_unit: str
    icon: str = "🌍"
    color_primary: str = "#22c55e"
    color_secondary: str = "#86efac"
    background_gradient: str = ""
    tags: list[str] = field(default_factory=list)
    share_text: str = ""
    created_at: str = ""


@dataclass
class EcoJournalEntry:
    """A monthly eco-journal entry."""
    entry_id: str
    user_id: int
    month: str  # YYYY-MM
    title: str
    narrative: str
    highlights: list[str] = field(default_factory=list)
    stats_summary: dict[str, Any] = field(default_factory=dict)
    best_moment: str = ""
    challenge_faced: str = ""
    next_month_goal: str = ""
    story_cards: list[StoryCard] = field(default_factory=list)
    created_at: str = ""


@dataclass
class StoryScene:
    """A single scene in a multi-part story."""
    scene_id: str
    scene_type: str  # opening | conflict | resolution | celebration | reflection
    title: str
    narrative: str
    stat_highlight: str = ""
    icon: str = ""
    mood: str = "neutral"  # hopeful | triumphant | reflective | urgent | inspiring


@dataclass
class ImpactNarrative:
    """A human-readable impact narrative."""
    headline: str
    body: str
    equivalent: str
    call_to_action: str = ""
    tone: str = "inspiring"  # inspiring | urgent | celebratory | reflective


# ──────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────

def init_story_tables() -> None:
    """Create story and journal tables."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS story_cards (
                id              TEXT PRIMARY KEY,
                user_id         INTEGER NOT NULL,
                story_type      TEXT NOT NULL,
                theme           TEXT DEFAULT 'hope',
                title           TEXT NOT NULL,
                narrative       TEXT NOT NULL,
                headline_stat   TEXT DEFAULT '',
                stat_value      REAL DEFAULT 0.0,
                stat_unit       TEXT DEFAULT '',
                icon            TEXT DEFAULT '🌍',
                color_primary   TEXT DEFAULT '#22c55e',
                color_secondary TEXT DEFAULT '#86efac',
                tags            TEXT DEFAULT '[]',
                share_text      TEXT DEFAULT '',
                created_at      TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS eco_journal (
                id              TEXT PRIMARY KEY,
                user_id         INTEGER NOT NULL,
                month           TEXT NOT NULL,
                title           TEXT NOT NULL,
                narrative       TEXT NOT NULL,
                highlights      TEXT DEFAULT '[]',
                stats_summary   TEXT DEFAULT '{}',
                best_moment     TEXT DEFAULT '',
                challenge_faced TEXT DEFAULT '',
                next_month_goal TEXT DEFAULT '',
                created_at      TEXT NOT NULL,
                UNIQUE(user_id, month)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS story_favorites (
                user_id     INTEGER NOT NULL,
                story_id    TEXT NOT NULL,
                favorited_at TEXT NOT NULL,
                PRIMARY KEY (user_id, story_id)
            )
        """)
        conn.commit()


# ──────────────────────────────────────────────────────────────────────
# Narrative generation
# ──────────────────────────────────────────────────────────────────────

def _random_equivalent(co2_kg: float) -> str:
    """Generate a random CO₂ equivalent description."""
    template, fn = random.choice(CO2_EQUIVALENTS)
    n = fn(co2_kg)
    return template.format(n=n)


def _pick_narrative(story_type: str, **kwargs) -> str:
    """Pick and fill a narrative template."""
    templates = NARRATIVE_TEMPLATES.get(story_type, NARRATIVE_TEMPLATES["weekly_summary"])
    template = random.choice(templates)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def generate_weekly_story(user_id: int, username: str = "Eco Warrior") -> StoryCard:
    """Generate a weekly summary story card."""
    stats = get_user_pledge_stats(user_id)
    weekly = get_weekly_impacts(user_id, weeks=1)
    ws = current_week_start()

    week = weekly[0] if weekly else None
    co2 = week.co2_saved_kg if week else 0.0
    checkins = week.checkins if week else 0
    n_pledges = week.pledges_enrolled if week else 0
    completed = week.pledges_completed if week else 0
    categories = ", ".join(week.categories_touched) if week and week.categories_touched else "various"

    equivalent = _random_equivalent(co2)

    narrative = _pick_narrative(
        "weekly_summary",
        name=username,
        n_pledges=n_pledges,
        categories=categories,
        completed=completed,
        co2=co2,
        checkins=checkins,
        equivalent=equivalent,
    )

    theme = _select_theme(user_id)
    theme_data = STORY_THEMES[theme]

    story = StoryCard(
        story_id=str(uuid.uuid4())[:12],
        user_id=user_id,
        story_type=StoryType.WEEKLY_SUMMARY,
        theme=theme,
        title=f"{theme_data['icon']} {theme_data['title']}",
        narrative=narrative,
        headline_stat=f"{co2:.1f}",
        stat_value=co2,
        stat_unit="kg CO₂",
        icon=theme_data["icon"],
        color_primary=theme_data["color_primary"],
        color_secondary=theme_data["color_secondary"],
        tags=[f"week:{ws}", "weekly_summary"],
        share_text=f"🌍 I saved {co2:.1f} kg CO₂ this week through green pledges! {equivalent} #EcoBuddy #GreenPledges",
        created_at=datetime.now().isoformat(timespec="seconds"),
    )

    _save_story(story)
    return story


def generate_milestone_story(user_id: int, username: str = "Eco Warrior") -> StoryCard | None:
    """Generate a story card for a recently achieved milestone."""
    milestones = check_milestones(user_id)
    achieved = [m for m in milestones if m.achieved]

    if not achieved:
        return None

    latest = achieved[-1]
    defn = MILESTONE_DEFINITIONS.get(
        __import__("pledge_impact_engine", fromlist=["MilestoneType"]).MilestoneType(latest.milestone_type),
        {},
    )

    narrative = _pick_narrative(
        "milestone_celebration",
        name=username,
        achievement=defn.get("title", latest.title),
        metric_value=latest.xp_bonus,
    )

    theme = "hope"
    theme_data = STORY_THEMES[theme]

    story = StoryCard(
        story_id=str(uuid.uuid4())[:12],
        user_id=user_id,
        story_type=StoryType.MILESTONE_CELEBRATION,
        theme=theme,
        title=f"🏆 {latest.title}",
        narrative=narrative,
        headline_stat=str(len(achieved)),
        stat_value=float(len(achieved)),
        stat_unit="milestones",
        icon="🏆",
        color_primary="#f59e0b",
        color_secondary="#fcd34d",
        tags=["milestone", latest.milestone_type],
        share_text=f"🏆 I just unlocked: {latest.title}! {latest.description} #EcoBuddy #Milestone",
        created_at=datetime.now().isoformat(timespec="seconds"),
    )

    _save_story(story)
    return story


def generate_streak_story(user_id: int, username: str = "Eco Warrior") -> StoryCard | None:
    """Generate a streak narrative story card."""
    stats = get_user_pledge_stats(user_id)
    if stats.current_streak < 2:
        return None

    narrative = _pick_narrative(
        "streak_narrative",
        name=username,
        streak=stats.current_streak,
    )

    theme = "resilience"
    theme_data = STORY_THEMES[theme]

    story = StoryCard(
        story_id=str(uuid.uuid4())[:12],
        user_id=user_id,
        story_type=StoryType.STREAK_NARRATIVE,
        theme=theme,
        title=f"🔥 {stats.current_streak}-Week Streak",
        narrative=narrative,
        headline_stat=str(stats.current_streak),
        stat_value=float(stats.current_streak),
        stat_unit="weeks",
        icon="🔥",
        color_primary="#ef4444",
        color_secondary="#fca5a5",
        tags=["streak", f"streak:{stats.current_streak}"],
        share_text=f"🔥 I'm on a {stats.current_streak}-week green pledge streak! Consistency is key 🌱 #EcoBuddy #Streak",
        created_at=datetime.now().isoformat(timespec="seconds"),
    )

    _save_story(story)
    return story


def generate_impact_story(user_id: int, username: str = "Eco Warrior") -> StoryCard:
    """Generate a CO₂ impact story card."""
    stats = get_user_pledge_stats(user_id)
    co2 = stats.total_co2_saved_kg
    eq = estimate_co2_equivalents(co2)

    equivalent = _random_equivalent(co2)

    narrative = _pick_narrative(
        "co2_impact",
        name=username,
        co2=co2,
        trees=eq["trees_needed"],
        km=eq["car_km"],
        equivalent=equivalent,
    )

    theme = _select_theme(user_id)
    theme_data = STORY_THEMES[theme]

    story = StoryCard(
        story_id=str(uuid.uuid4())[:12],
        user_id=user_id,
        story_type=StoryType.CO2_IMPACT,
        theme=theme,
        title=f"🌍 Total Impact: {co2:.1f} kg CO₂",
        narrative=narrative,
        headline_stat=f"{co2:.1f}",
        stat_value=co2,
        stat_unit="kg CO₂ saved",
        icon="🌍",
        color_primary="#22c55e",
        color_secondary="#86efac",
        tags=["impact", f"co2:{int(co2)}"],
        share_text=f"🌍 My total CO₂ savings: {co2:.1f} kg! That's {equivalent} 🌱 #EcoBuddy #Impact",
        created_at=datetime.now().isoformat(timespec="seconds"),
    )

    _save_story(story)
    return story


def generate_prediction_story(user_id: int, username: str = "Eco Warrior") -> StoryCard:
    """Generate a future prediction story card."""
    prediction = predict_future_impact(user_id)
    predicted_co2 = prediction.predicted_co2_12w
    equivalent = _random_equivalent(predicted_co2)

    narrative = _pick_narrative(
        "prediction_story",
        name=username,
        predicted_co2=predicted_co2,
        equivalent=equivalent,
    )

    theme = "transformation"
    theme_data = STORY_THEMES[theme]

    story = StoryCard(
        story_id=str(uuid.uuid4())[:12],
        user_id=user_id,
        story_type=StoryType.PREDICTION_STORY,
        theme=theme,
        title=f"🔮 Next 12 Weeks: {predicted_co2:.1f} kg CO₂",
        narrative=narrative,
        headline_stat=f"{predicted_co2:.1f}",
        stat_value=predicted_co2,
        stat_unit="predicted kg CO₂",
        icon="🔮",
        color_primary="#a855f7",
        color_secondary="#c084fc",
        tags=["prediction", "12week"],
        share_text=f"🔮 At my current pace, I'll save {predicted_co2:.1f} kg CO₂ in the next 12 weeks! {equivalent} #EcoBuddy #FutureGreen",
        created_at=datetime.now().isoformat(timespec="seconds"),
    )

    _save_story(story)
    return story


def generate_journey_beginning_story(user_id: int, username: str = "Eco Warrior") -> StoryCard:
    """Generate a 'journey beginning' story card for new users."""
    narrative = _pick_narrative(
        "journey_beginning",
        name=username,
    )

    theme = "hope"
    theme_data = STORY_THEMES[theme]

    story = StoryCard(
        story_id=str(uuid.uuid4())[:12],
        user_id=user_id,
        story_type=StoryType.JOURNEY_BEGINNING,
        theme=theme,
        title="📖 My Green Journey Begins",
        narrative=narrative,
        headline_stat="Day 1",
        stat_value=1.0,
        stat_unit="pledge started",
        icon="📖",
        color_primary="#22c55e",
        color_secondary="#86efac",
        tags=["journey", "beginning"],
        share_text="📖 Today I started my green pledge journey! One step at a time 🌱 #EcoBuddy #GreenJourney",
        created_at=datetime.now().isoformat(timespec="seconds"),
    )

    _save_story(story)
    return story


# ──────────────────────────────────────────────────────────────────────
# Multi-part stories
# ──────────────────────────────────────────────────────────────────────

def generate_full_journey_story(user_id: int, username: str = "Eco Warrior") -> list[StoryScene]:
    """Generate a multi-scene story of the user's entire pledge journey."""
    stats = get_user_pledge_stats(user_id)
    weekly = get_weekly_impacts(user_id, weeks=12)
    milestones = check_milestones(user_id)
    achieved = [m for m in milestones if m.achieved]

    scenes: list[StoryScene] = []

    # Scene 1: The Beginning
    scenes.append(StoryScene(
        scene_id=str(uuid.uuid4())[:8],
        scene_type="opening",
        title="📖 Chapter 1: The Beginning",
        narrative=f"It all started with a single pledge. {username} decided to make a difference, "
                  f"one green commitment at a time.",
        stat_highlight="Day 1",
        icon="🌱",
        mood="hopeful",
    ))

    # Scene 2: The Building Phase
    if stats.total_pledges_completed >= 1:
        scenes.append(StoryScene(
            scene_id=str(uuid.uuid4())[:8],
            scene_type="conflict",
            title="🔨 Chapter 2: Building Momentum",
            narrative=f"With {stats.total_pledges_completed} pledge(s) completed, {username} "
                      f"was building something powerful — a habit that matters.",
            stat_highlight=f"{stats.total_pledges_completed} pledges completed",
            icon="💪",
            mood="inspiring",
        ))

    # Scene 3: The Impact
    co2 = stats.total_co2_saved_kg
    if co2 > 0:
        eq = estimate_co2_equivalents(co2)
        scenes.append(StoryScene(
            scene_id=str(uuid.uuid4())[:8],
            scene_type="resolution",
            title="🌍 Chapter 3: Real Impact",
            narrative=f"Through dedication, {username} saved {co2:.1f} kg of CO₂ — "
                      f"equivalent to {eq['trees_needed']:.0f} trees absorbing carbon for a year.",
            stat_highlight=f"{co2:.1f} kg CO₂ saved",
            icon="🌍",
            mood="triumphant",
        ))

    # Scene 4: Milestones
    if achieved:
        milestone_names = [MILESTONE_DEFINITIONS.get(
            __import__("pledge_impact_engine", fromlist=["MilestoneType"]).MilestoneType(m.milestone_type),
            {}).get("title", m.title) for m in achieved[:3]]
        scenes.append(StoryScene(
            scene_id=str(uuid.uuid4())[:8],
            scene_type="celebration",
            title="🏆 Chapter 4: Milestones Unlocked",
            narrative=f"Achievements earned: {', '.join(milestone_names)}. "
                      f"Each one a testament to {username}'s commitment.",
            stat_highlight=f"{len(achieved)} milestones",
            icon="🏆",
            mood="triumphant",
        ))

    # Scene 5: The Future
    prediction = predict_future_impact(user_id)
    if prediction.predicted_co2_12w > 0:
        scenes.append(StoryScene(
            scene_id=str(uuid.uuid4())[:8],
            scene_type="reflection",
            title="🔮 Chapter 5: The Road Ahead",
            narrative=f"At the current pace, {username} is projected to save "
                      f"{prediction.predicted_co2_12w:.1f} more kg of CO₂ in the next 12 weeks. "
                      f"The best chapters are yet to be written.",
            stat_highlight=f"{prediction.predicted_co2_12w:.1f} kg predicted",
            icon="🔮",
            mood="hopeful",
        ))

    return scenes


# ──────────────────────────────────────────────────────────────────────
# Eco journal
# ──────────────────────────────────────────────────────────────────────

def generate_monthly_journal(user_id: int, username: str = "Eco Warrior") -> EcoJournalEntry:
    """Generate a monthly eco-journal entry."""
    now = datetime.now()
    month_str = now.strftime("%Y-%m")
    month_name = now.strftime("%B %Y")

    stats = get_user_pledge_stats(user_id)
    weekly = get_weekly_impacts(user_id, weeks=4)
    milestones = check_milestones(user_id)
    achieved = [m for m in milestones if m.achieved]

    # Compute monthly stats
    total_co2 = sum(w.co2_saved_kg for w in weekly)
    total_xp = sum(w.xp_earned for w in weekly)
    total_checkins = sum(w.checkins for w in weekly)
    total_completed = sum(w.pledges_completed for w in weekly)

    # Highlights
    highlights: list[str] = []
    if total_completed > 0:
        highlights.append(f"Completed {total_completed} pledge(s) this month")
    if total_co2 > 0:
        highlights.append(f"Saved {total_co2:.1f} kg of CO₂")
    if total_checkins > 0:
        highlights.append(f"Made {total_checkins} daily check-ins")
    if stats.current_streak >= 3:
        highlights.append(f"Maintained a {stats.current_streak}-week streak")

    # Best moment
    best_week = max(weekly, key=lambda w: w.co2_saved_kg) if weekly else None
    best_moment = ""
    if best_week and best_week.co2_saved_kg > 0:
        best_moment = f"Best week: {best_week.week_start} — saved {best_week.co2_saved_kg:.1f} kg CO₂ with {best_week.checkins} check-ins"
    else:
        best_moment = "Starting the journey — every step counts!"

    # Challenge
    challenge = ""
    missed_weeks = sum(1 for w in weekly if w.pledges_enrolled > 0 and w.pledges_completed == 0)
    if missed_weeks > 0:
        challenge = f"{missed_weeks} week(s) with no completions — consistency is the next frontier"
    else:
        challenge = "Maintaining momentum across all weeks"

    # Next month goal
    prediction = predict_future_impact(user_id)
    if prediction.predicted_co2_12w > 0:
        next_month_goal = f"Save at least {prediction.predicted_co2_12w / 3:.1f} kg CO₂ next month"
    else:
        next_month_goal = "Complete at least 2 pledges next month"

    # Narrative
    narrative = (
        f"📗 {month_name} was a month of {username}'s sustainability journey. "
        f"With {total_completed} pledge(s) completed and {total_co2:.1f} kg of CO₂ saved, "
        f"every check-in was a vote for the planet. "
    )
    if highlights:
        narrative += f"Key highlights: {'; '.join(highlights[:3])}. "
    narrative += f"Looking ahead: {next_month_goal}."

    # Title
    if total_co2 > 10:
        title = f"📗 {month_name}: A Month of Impact"
    elif total_completed > 0:
        title = f"📗 {month_name}: Building Green Habits"
    else:
        title = f"📗 {month_name}: The Journey Continues"

    # Generate story cards for the journal
    cards: list[StoryCard] = []
    if total_co2 > 0:
        cards.append(generate_impact_story(user_id, username))
    if stats.current_streak >= 2:
        streak_card = generate_streak_story(user_id, username)
        if streak_card:
            cards.append(streak_card)

    entry = EcoJournalEntry(
        entry_id=str(uuid.uuid4())[:12],
        user_id=user_id,
        month=month_str,
        title=title,
        narrative=narrative,
        highlights=highlights,
        stats_summary={
            "total_co2_kg": round(total_co2, 2),
            "total_xp": total_xp,
            "total_checkins": total_checkins,
            "total_completed": total_completed,
            "current_streak": stats.current_streak,
            "milestones_achieved": len(achieved),
        },
        best_moment=best_moment,
        challenge_faced=challenge,
        next_month_goal=next_month_goal,
        story_cards=cards,
        created_at=datetime.now().isoformat(timespec="seconds"),
    )

    _save_journal(entry)
    return entry


# ──────────────────────────────────────────────────────────────────────
# Impact narrative
# ──────────────────────────────────────────────────────────────────────

def generate_impact_narrative(user_id: int, username: str = "Eco Warrior") -> ImpactNarrative:
    """Generate a human-readable impact narrative."""
    stats = get_user_pledge_stats(user_id)
    co2 = stats.total_co2_saved_kg
    eq = estimate_co2_equivalents(co2)
    equivalent = _random_equivalent(co2)

    if co2 == 0:
        return ImpactNarrative(
            headline="Your Green Journey Awaits",
            body=f"{username}, your sustainability story is just beginning. "
                 f"Enrol in your first pledge and start making a difference today.",
            equivalent="Your first pledge could save enough CO₂ to plant a tree",
            call_to_action="Browse pledges and enrol in your first one!",
            tone="inspiring",
        )
    elif co2 < 10:
        return ImpactNarrative(
            headline=f"You've Started Making a Difference",
            body=f"With {co2:.1f} kg of CO₂ saved, {username} is already on the path "
                 f"to a greener future. Every pledge completed is a step forward.",
            equivalent=equivalent,
            call_to_action="Keep going — you're building momentum!",
            tone="encouraging",
        )
    elif co2 < 50:
        return ImpactNarrative(
            headline=f"Growing Impact: {co2:.1f} kg CO₂ Saved",
            body=f"{username}'s commitment is paying off. {co2:.1f} kg of CO₂ prevented "
                 f"from entering the atmosphere — that's real, measurable change.",
            equivalent=equivalent,
            call_to_action="You're making a real difference. Share your story!",
            tone="celebratory",
        )
    elif co2 < 100:
        return ImpactNarrative(
            headline=f"Significant Impact: {co2:.1f} kg CO₂ Saved",
            body=f"Over {co2:.1f} kg of CO₂ saved! {username} has demonstrated that "
                 f"consistent small actions lead to significant environmental impact.",
            equivalent=equivalent,
            call_to_action="Your impact is significant. Inspire others by sharing!",
            tone="celebratory",
        )
    else:
        return ImpactNarrative(
            headline=f"Extraordinary Impact: {co2:.1f} kg CO₂ Saved",
            body=f"With {co2:.1f} kg of CO₂ saved, {username} is in a league of their own. "
                 f"That's the equivalent of {eq['trees_needed']:.0f} trees working for a year.",
            equivalent=equivalent,
            call_to_action="You're an eco legend. Share your story to inspire the world!",
            tone="triumphant",
        )


# ──────────────────────────────────────────────────────────────────────
# Story management
# ──────────────────────────────────────────────────────────────────────

def get_user_stories(user_id: int, limit: int = 20) -> list[StoryCard]:
    """Retrieve a user's story cards."""
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM story_cards WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))
        return [_row_to_story(dict(r)) for r in cur.fetchall()]


def get_user_journals(user_id: int, limit: int = 12) -> list[EcoJournalEntry]:
    """Retrieve a user's eco-journal entries."""
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM eco_journal WHERE user_id = ?
            ORDER BY month DESC LIMIT ?
        """, (user_id, limit))
        return [_row_to_journal(dict(r)) for r in cur.fetchall()]


def favorite_story(user_id: int, story_id: str) -> bool:
    """Favorite a story."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        now = datetime.now().isoformat(timespec="seconds")
        cur.execute(
            "INSERT OR IGNORE INTO story_favorites (user_id, story_id, favorited_at) VALUES (?, ?, ?)",
            (user_id, story_id, now),
        )
        conn.commit()
        return cur.rowcount > 0


def unfavorite_story(user_id: int, story_id: str) -> bool:
    """Remove a favorite."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM story_favorites WHERE user_id = ? AND story_id = ?",
            (user_id, story_id),
        )
        conn.commit()
        return cur.rowcount > 0


def get_favorites(user_id: int) -> list[str]:
    """Get list of favorited story IDs."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT story_id FROM story_favorites WHERE user_id = ?",
            (user_id,),
        )
        return [r[0] for r in cur.fetchall()]


# ──────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────

def _select_theme(user_id: int) -> str:
    """Select a theme based on the user's journey stage."""
    stats = get_user_pledge_stats(user_id)
    if stats.total_pledges_completed == 0:
        return "hope"
    elif stats.current_streak >= 6:
        return "resilience"
    elif stats.total_co2_saved_kg >= 50:
        return "transformation"
    elif stats.total_pledges_completed >= 10:
        return "community"
    else:
        return "adventure"


def _save_story(story: StoryCard) -> None:
    """Persist a story card."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO story_cards
                (id, user_id, story_type, theme, title, narrative, headline_stat,
                 stat_value, stat_unit, icon, color_primary, color_secondary,
                 tags, share_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            story.story_id, story.user_id, story.story_type, story.theme,
            story.title, story.narrative, story.headline_stat,
            story.stat_value, story.stat_unit, story.icon,
            story.color_primary, story.color_secondary,
            json.dumps(story.tags), story.share_text, story.created_at,
        ))
        conn.commit()


def _save_journal(entry: EcoJournalEntry) -> None:
    """Persist a journal entry."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO eco_journal
                (id, user_id, month, title, narrative, highlights, stats_summary,
                 best_moment, challenge_faced, next_month_goal, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.entry_id, entry.user_id, entry.month, entry.title,
            entry.narrative, json.dumps(entry.highlights),
            json.dumps(entry.stats_summary), entry.best_moment,
            entry.challenge_faced, entry.next_month_goal, entry.created_at,
        ))
        conn.commit()


def _row_to_story(row: dict) -> StoryCard:
    """Convert a DB row to a StoryCard."""
    tags = json.loads(row.get("tags", "[]")) if isinstance(row.get("tags"), str) else row.get("tags", [])
    return StoryCard(
        story_id=row["id"],
        user_id=row["user_id"],
        story_type=row["story_type"],
        theme=row.get("theme", "hope"),
        title=row["title"],
        narrative=row["narrative"],
        headline_stat=row.get("headline_stat", ""),
        stat_value=row.get("stat_value", 0.0),
        stat_unit=row.get("stat_unit", ""),
        icon=row.get("icon", "🌍"),
        color_primary=row.get("color_primary", "#22c55e"),
        color_secondary=row.get("color_secondary", "#86efac"),
        tags=tags,
        share_text=row.get("share_text", ""),
        created_at=row.get("created_at", ""),
    )


def _row_to_journal(row: dict) -> EcoJournalEntry:
    """Convert a DB row to an EcoJournalEntry."""
    highlights = json.loads(row.get("highlights", "[]")) if isinstance(row.get("highlights"), str) else row.get("highlights", [])
    stats = json.loads(row.get("stats_summary", "{}")) if isinstance(row.get("stats_summary"), str) else row.get("stats_summary", {})
    return EcoJournalEntry(
        entry_id=row["id"],
        user_id=row["user_id"],
        month=row["month"],
        title=row["title"],
        narrative=row["narrative"],
        highlights=highlights,
        stats_summary=stats,
        best_moment=row.get("best_moment", ""),
        challenge_faced=row.get("challenge_faced", ""),
        next_month_goal=row.get("next_month_goal", ""),
        created_at=row.get("created_at", ""),
    )


def story_to_dict(s: StoryCard) -> dict[str, Any]:
    return asdict(s)


def journal_to_dict(j: EcoJournalEntry) -> dict[str, Any]:
    d = asdict(j)
    d["story_cards"] = [asdict(c) for c in j.story_cards]
    return d


def export_stories_json(user_id: int) -> str:
    """Export all user stories as JSON."""
    stories = get_user_stories(user_id, limit=100)
    journals = get_user_journals(user_id, limit=12)
    favorites = get_favorites(user_id)

    data = {
        "stories": [story_to_dict(s) for s in stories],
        "journals": [journal_to_dict(j) for j in journals],
        "favorites": favorites,
        "total_stories": len(stories),
        "total_journals": len(journals),
    }
    return json.dumps(data, indent=2, default=str)
