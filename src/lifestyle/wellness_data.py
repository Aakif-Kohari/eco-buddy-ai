"""Mock data generator and calculations for the Eco Wellness Tracker."""

import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from src.lifestyle.wellness_types import (
    EcoHabit, HabitLog, HabitStreak, DailyWellnessScore,
    WellnessGoal, WellnessWeeklyReport, WellnessStats,
    HabitCategory, HabitFrequency, StreakTier,
    STREAK_THRESHOLDS, STREAK_COLORS,
)


def generate_id(prefix: str, seed: int = None) -> str:
    """Generate a deterministic ID."""
    if seed is not None:
        h = hashlib.md5(f"{prefix}_{seed}".encode()).hexdigest()[:8]
    else:
        h = hashlib.md5(f"{prefix}_{random.random()}".encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


def get_streak_tier(streak: int) -> StreakTier:
    """Determine streak tier from current streak count."""
    for tier in reversed(list(StreakTier)):
        if streak >= STREAK_THRESHOLDS[tier]:
            return tier
    return StreakTier.STARTER


def calculate_wellness_score(
    habits_completed: int, habits_total: int,
    mood: int, energy: int,
    nature_min: int, mindfulness_min: int
) -> float:
    """Calculate composite wellness score (0-100)."""
    completion_score = (habits_completed / max(habits_total, 1)) * 40
    mood_score = (mood / 5) * 20
    energy_score = (energy / 5) * 15
    nature_score = min(nature_min / 30, 1.0) * 15
    mindfulness_score = min(mindfulness_min / 20, 1.0) * 10

    return round(min(completion_score + mood_score + energy_score + nature_score + mindfulness_score, 100), 1)


def generate_mock_habits() -> List[EcoHabit]:
    """Generate a set of eco-friendly habits."""
    habits_data = [
        ("Turn off lights when leaving room", "Switch off all lights when leaving any room for 5+ minutes", HabitCategory.ENERGY, HabitFrequency.DAILY, 10, 0.5, 0, "💡", "#f59e0b"),
        ("Take a 5-minute shorter shower", "Reduce shower time by 5 minutes to save water and energy", HabitCategory.WATER, HabitFrequency.DAILY, 15, 0.3, 40, "🚿", "#0ea5e9"),
        ("Walk or bike to work", "Use active transport for your commute instead of driving", HabitCategory.TRANSPORT, HabitFrequency.DAILY, 25, 2.1, 0, "🚲", "#22c55e"),
        ("Eat a plant-based meal", "Choose a fully plant-based meal for one sitting", HabitCategory.FOOD, HabitFrequency.DAILY, 12, 1.5, 0, "🥗", "#14b8a6"),
        ("Recycle all packaging", "Sort and recycle all packaging from today's purchases", HabitCategory.WASTE, HabitFrequency.DAILY, 8, 0.4, 0, "♻️", "#8b5cf6"),
        ("Spend 20 minutes in nature", "Walk in a park, garden, or natural area for 20+ minutes", HabitCategory.NATURE, HabitFrequency.DAILY, 15, 0.2, 0, "🌿", "#16a34a"),
        ("10-minute meditation", "Practice mindfulness meditation for 10+ minutes", HabitCategory.MINDFULNESS, HabitFrequency.DAILY, 10, 0.1, 0, "🧘", "#ec4899"),
        ("Bring reusable bags when shopping", "Use your own bags instead of receiving plastic ones", HabitCategory.SHOPPING, HabitFrequency.WEEKLY, 20, 0.8, 0, "🛍️", "#f97316"),
        ("Unplug unused electronics", "Unplug chargers, appliances, and devices not in use", HabitCategory.ENERGY, HabitFrequency.DAILY, 10, 0.6, 0, "🔌", "#f59e0b"),
        ("Take a cold shower", "End your shower with 30 seconds of cold water", HabitCategory.WATER, HabitFrequency.DAILY, 12, 0.4, 30, "❄️", "#0ea5e9"),
        ("Use public transport today", "Take bus, train, or metro instead of driving", HabitCategory.TRANSPORT, HabitFrequency.DAILY, 20, 1.8, 0, "🚌", "#22c55e"),
        ("Compost food scraps", "Compost fruit peels, coffee grounds, and food waste", HabitCategory.WASTE, HabitFrequency.DAILY, 12, 0.5, 0, "🌱", "#8b5cf6"),
        ("Read about sustainability", "Read an article or chapter about environmental topics", HabitCategory.MINDFULNESS, HabitFrequency.DAILY, 8, 0.1, 0, "📖", "#ec4899"),
        ("Choose seasonal produce", "Buy locally grown, seasonal fruits and vegetables", HabitCategory.FOOD, HabitFrequency.WEEKLY, 15, 1.0, 0, "🍎", "#14b8a6"),
        ("Do a 5-minute breathing exercise", "Practice deep breathing for relaxation and focus", HabitCategory.MINDFULNESS, HabitFrequency.DAILY, 8, 0.1, 0, "🌬️", "#ec4899"),
    ]

    habits = []
    for i, (name, desc, cat, freq, points, carbon, water, icon, color) in enumerate(habits_data):
        habits.append(EcoHabit(
            habit_id=generate_id("habit", i),
            name=name,
            description=desc,
            category=cat,
            frequency=freq,
            eco_points=points,
            carbon_save_kg=carbon,
            water_save_liters=water,
            icon=icon,
            color=color,
            is_active=True,
            created_at=(datetime.now() - timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d"),
        ))

    return habits


def generate_mock_streaks(habits: List[EcoHabit], user_id: str) -> List[HabitStreak]:
    """Generate mock streak data for habits."""
    streaks = []
    for i, habit in enumerate(habits[:12]):
        current = random.randint(0, 45)
        longest = max(current, random.randint(5, 60))
        total = random.randint(current, 200)
        tier = get_streak_tier(current)
        last_days_ago = random.randint(0, 3)

        streaks.append(HabitStreak(
            habit_id=habit.habit_id,
            user_id=user_id,
            current_streak=current,
            longest_streak=longest,
            total_completions=total,
            last_completed_at=(datetime.now() - timedelta(days=last_days_ago)).strftime("%Y-%m-%d %H:%M:%S"),
            tier=tier,
            streak_started_at=(datetime.now() - timedelta(days=current + random.randint(0, 10))).strftime("%Y-%m-%d"),
        ))

    return streaks


def generate_mock_daily_scores(days: int = 30) -> List[DailyWellnessScore]:
    """Generate mock daily wellness scores."""
    scores = []
    base_score = 65

    for d in range(days):
        date = (datetime.now() - timedelta(days=days - d - 1)).strftime("%Y-%m-%d")
        variation = random.uniform(-10, 15)
        score = min(max(base_score + variation, 30), 100)
        habits_done = random.randint(3, 12)
        habits_total = 12

        scores.append(DailyWellnessScore(
            date=date,
            eco_score=round(score, 1),
            habits_completed=habits_done,
            habits_total=habits_total,
            eco_points=random.randint(50, 200),
            carbon_saved_kg=round(random.uniform(0.5, 5.0), 2),
            water_saved_liters=round(random.uniform(20, 150), 0),
            mood=random.randint(2, 5),
            energy_level=random.randint(2, 5),
            nature_time_minutes=random.randint(0, 45),
            mindfulness_minutes=random.randint(0, 30),
        ))

        base_score = score + random.uniform(-3, 3)

    return scores


def generate_mock_goals(user_id: str) -> List[WellnessGoal]:
    """Generate mock wellness goals."""
    goals_data = [
        ("30-Day Walking Streak", HabitCategory.TRANSPORT, 30, 18, "days", "2026-09-30"),
        ("Save 1000 Liters Water", HabitCategory.WATER, 1000, 650, "liters", "2026-10-15"),
        ("100 Plant-Based Meals", HabitCategory.FOOD, 100, 67, "meals", "2026-12-31"),
        ("7-Day Mindfulness Streak", HabitCategory.MINDFULNESS, 7, 5, "days", "2026-09-10"),
        ("500 Eco Points", HabitCategory.ENERGY, 500, 380, "points", "2026-09-30"),
    ]

    goals = []
    for i, (title, cat, target, current, unit, deadline) in enumerate(goals_data):
        goals.append(WellnessGoal(
            goal_id=generate_id("goal", i),
            user_id=user_id,
            title=title,
            category=cat,
            target_value=float(target),
            current_value=float(current),
            unit=unit,
            deadline=deadline,
            created_at=(datetime.now() - timedelta(days=random.randint(10, 60))).strftime("%Y-%m-%d"),
            is_completed=current >= target,
        ))

    return goals


def generate_mock_weekly_reports(weeks: int = 4) -> List[WellnessWeeklyReport]:
    """Generate mock weekly wellness reports."""
    reports = []
    habits_list = ["Walk to work", "Plant-based meal", "Shorter shower", "Recycle", "Meditate"]

    for w in range(weeks):
        start = datetime.now() - timedelta(weeks=weeks - w)
        end = start + timedelta(days=6)

        reports.append(WellnessWeeklyReport(
            week_start=start.strftime("%Y-%m-%d"),
            week_end=end.strftime("%Y-%m-%d"),
            total_habits_completed=random.randint(35, 70),
            total_eco_points=random.randint(300, 800),
            total_carbon_saved_kg=round(random.uniform(5, 25), 2),
            total_water_saved_liters=round(random.uniform(200, 800), 0),
            avg_mood=round(random.uniform(3.0, 4.8), 1),
            avg_energy=round(random.uniform(2.8, 4.5), 1),
            total_nature_minutes=random.randint(60, 300),
            total_mindfulness_minutes=random.randint(30, 150),
            completion_rate=round(random.uniform(0.55, 0.92), 2),
            top_habit=random.choice(habits_list),
            streak_highlights=[
                {"habit": random.choice(habits_list), "streak": f"{random.randint(5, 30)} days"},
                {"habit": random.choice(habits_list), "streak": f"{random.randint(3, 15)} days"},
            ],
        ))

    return reports


def generate_mock_stats(habits: List[EcoHabit], streaks: List[HabitStreak], scores: List[DailyWellnessScore]) -> WellnessStats:
    """Generate aggregate wellness statistics."""
    total_completions = sum(s.total_completions for s in streaks)
    total_points = sum(s.total_completions * 10 for s in streaks)
    total_carbon = sum(h.carbon_save_kg for h in habits) * total_completions * 0.1
    total_water = sum(h.water_save_liters for h in habits) * total_completions * 0.1
    avg_score = sum(s.eco_score for s in scores) / len(scores) if scores else 0
    best_streak = max((s.current_streak for s in streaks), default=0)
    active = sum(1 for h in habits if h.is_active)

    recent_scores = scores[-7:] if len(scores) >= 7 else scores
    older_scores = scores[-14:-7] if len(scores) >= 14 else scores
    recent_avg = sum(s.eco_score for s in recent_scores) / len(recent_scores) if recent_scores else 0
    older_avg = sum(s.eco_score for s in older_scores) / len(older_scores) if older_scores else 0
    trend = "improving" if recent_avg > older_avg + 2 else "declining" if recent_avg < older_avg - 2 else "stable"

    cat_counts = {}
    for h in habits:
        cat = h.category.value
        cat_counts[cat] = cat_counts.get(cat, 0) + h.carbon_save_kg
    top_cat = max(cat_counts, key=cat_counts.get) if cat_counts else "energy"

    return WellnessStats(
        total_habits=len(habits),
        active_habits=active,
        total_completions=total_completions,
        total_eco_points=total_points,
        total_carbon_saved_kg=round(total_carbon, 2),
        total_water_saved_liters=round(total_water, 0),
        avg_daily_score=round(avg_score, 1),
        current_best_streak=best_streak,
        total_days_tracked=len(scores),
        completion_rate=round(random.uniform(0.60, 0.88), 2),
        top_category=top_cat,
        weekly_trend=trend,
    )


def generate_mock_logs(habits: List[EcoHabit], count: int = 40) -> List[HabitLog]:
    """Generate mock habit completion logs."""
    logs = []
    for i in range(count):
        habit = random.choice(habits)
        hours_ago = random.randint(0, 168)
        logs.append(HabitLog(
            log_id=generate_id("log", i),
            habit_id=habit.habit_id,
            user_id="user_001",
            completed_at=(datetime.now() - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S"),
            notes=random.choice(["", "Felt great!", "Easy today", "Quick one", ""]),
            eco_points_earned=habit.eco_points,
        ))

    return sorted(logs, key=lambda l: l.completed_at, reverse=True)
