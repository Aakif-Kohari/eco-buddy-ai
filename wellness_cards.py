"""Streamlit card components for the Eco Wellness Tracker."""

import streamlit as st
from typing import List, Dict
from wellness_types import (
    EcoHabit, HabitStreak, DailyWellnessScore, WellnessGoal,
    WellnessWeeklyReport, HabitCategory, StreakTier,
    CATEGORY_ICONS, CATEGORY_COLORS, STREAK_COLORS,
    MOOD_LABELS, ENERGY_LABELS,
)


def render_metric_card(
    title: str, value: str, subtitle: str = "",
    icon: str = "📊", delta: str = "", delta_color: str = "normal"
):
    """Render a styled metric card."""
    delta_html = ""
    if delta:
        color = "#22c55e" if delta_color == "normal" else "#ef4444"
        delta_html = f"<div style='margin-top: 4px; font-size: 12px; font-weight: 600; color: {color};'>{delta}</div>"

    st.markdown(f"""
    <div style='
        padding: 18px 20px;
        background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(240,253,244,0.85));
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 14px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        margin-bottom: 12px;
    '>
        <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 6px;'>
            <span style='font-size: 20px;'>{icon}</span>
            <span style='font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;'>{title}</span>
        </div>
        <div style='font-size: 26px; font-weight: 800; color: #111827; line-height: 1.2;'>{value}</div>
        {f'<div style="font-size: 11px; color: #6b7280; margin-top: 2px;">{subtitle}</div>' if subtitle else ''}
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_habit_card(habit: EcoHabit, streak: HabitStreak = None, completed_today: bool = False):
    """Render a habit card with streak info."""
    tier = streak.tier if streak else StreakTier.STARTER
    streak_val = streak.current_streak if streak else 0
    tier_color = STREAK_COLORS.get(tier, "#94a3b8")
    cat_color = CATEGORY_COLORS.get(habit.category, "#6b7280")
    cat_icon = CATEGORY_ICONS.get(habit.category, "🌿")

    streak_html = ""
    if streak:
        streak_html = f"""
        <div style='display: flex; align-items: center; gap: 6px; margin-top: 8px;'>
            <span style='
                padding: 2px 8px;
                background: {tier_color}20;
                color: {tier_color};
                border-radius: 8px;
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
            '>{tier.value}</span>
            <span style='font-size: 12px; font-weight: 700; color: {tier_color};'>🔥 {streak_val} days</span>
            <span style='font-size: 10px; color: #9ca3af;'>Best: {streak.longest_streak}</span>
        </div>
        """

    check_bg = "#22c55e" if completed_today else "transparent"
    check_border = "#22c55e" if completed_today else "#d1d5db"
    check_icon = "✓" if completed_today else ""

    st.markdown(f"""
    <div style='
        padding: 16px;
        background: {"linear-gradient(145deg, rgba(34,197,94,0.06), rgba(255,255,255,0.95))" if completed_today else "rgba(255,255,255,0.9)"};
        border: 1px solid {"rgba(34,197,94,0.2)" if completed_today else "rgba(0,0,0,0.06)"};
        border-left: 4px solid {cat_color};
        border-radius: 14px;
        margin-bottom: 10px;
    '>
        <div style='display: flex; align-items: center; gap: 10px;'>
            <div style='
                width: 32px; height: 32px;
                border-radius: 50%;
                background: {check_bg};
                border: 2px solid {check_border};
                display: flex; align-items: center; justify-content: center;
                color: white; font-size: 14px; font-weight: 800;
                flex-shrink: 0;
            '>{check_icon}</div>
            <div style='flex: 1; min-width: 0;'>
                <div style='display: flex; align-items: center; gap: 6px;'>
                    <span style='font-size: 14px;'>{habit.icon}</span>
                    <span style='font-size: 13px; font-weight: 700; color: #111827;'>{habit.name}</span>
                </div>
                <div style='font-size: 11px; color: #6b7280; margin-top: 2px;'>{habit.description[:80]}...</div>
                <div style='display: flex; gap: 10px; margin-top: 4px; font-size: 10px; color: #9ca3af;'>
                    <span>{cat_icon} {habit.category.value.title()}</span>
                    <span>🌟 {habit.eco_points} pts</span>
                    <span>🌿 {habit.carbon_save_kg} kg CO₂</span>
                    {f'<span>💧 {habit.water_save_liters} L</span>' if habit.water_save_liters > 0 else ''}
                </div>
                {streak_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_streak_leaderboard(streaks: List[HabitStreak], habits: List[EcoHabit]):
    """Render a streak leaderboard."""
    habit_map = {h.habit_id: h for h in habits}
    sorted_streaks = sorted(streaks, key=lambda s: s.current_streak, reverse=True)

    rows_html = ""
    for i, streak in enumerate(sorted_streaks[:8]):
        habit = habit_map.get(streak.habit_id)
        if not habit:
            continue
        tier_color = STREAK_COLORS.get(streak.tier, "#94a3b8")
        medal = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"#{i+1}")

        rows_html += f"""
        <div style='display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: {"rgba(34,197,94,0.04)" if i < 3 else "transparent"}; border-radius: 8px; margin-bottom: 3px;'>
            <span style='font-size: 16px; width: 28px; text-align: center;'>{medal}</span>
            <span style='font-size: 16px;'>{habit.icon}</span>
            <div style='flex: 1;'>
                <div style='font-size: 12px; font-weight: 600; color: #111827;'>{habit.name[:30]}</div>
            </div>
            <span style='font-size: 14px; font-weight: 800; color: {tier_color};'>🔥 {streak.current_streak}</span>
            <span style='
                padding: 1px 6px;
                background: {tier_color}20;
                color: {tier_color};
                border-radius: 6px;
                font-size: 9px;
                font-weight: 700;
            '>{streak.tier.value}</span>
        </div>
        """

    st.markdown(f"""
    <div style='
        padding: 16px;
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 14px;
        margin-bottom: 12px;
    '>
        <div style='font-size: 14px; font-weight: 700; color: #111827; margin-bottom: 10px;'>🔥 Streak Leaderboard</div>
        {rows_html}
    </div>
    """, unsafe_allow_html=True)


def render_goal_card(goal: WellnessGoal):
    """Render a wellness goal progress card."""
    progress = goal.progress_percent
    color = "#22c55e" if progress >= 80 else "#f59e0b" if progress >= 50 else "#ef4444"
    status = "✅ Done" if goal.is_completed else f"{goal.days_remaining}d left"

    st.markdown(f"""
    <div style='
        padding: 14px;
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 12px;
        margin-bottom: 10px;
    '>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
            <span style='font-size: 12px; font-weight: 700; color: #111827;'>{goal.title}</span>
            <span style='font-size: 10px; color: {color}; font-weight: 600;'>{status}</span>
        </div>
        <div style='font-size: 11px; color: #6b7280; margin-bottom: 6px;'>
            {goal.current_value:.0f} / {goal.target_value:.0f} {goal.unit}
        </div>
        <div style='width: 100%; height: 7px; background: #e5e7eb; border-radius: 999px; overflow: hidden;'>
            <div style='width: {progress}%; height: 100%; background: {color}; border-radius: 999px;'></div>
        </div>
        <div style='font-size: 10px; color: #9ca3af; margin-top: 4px;'>{progress:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)


def render_weekly_report_card(report: WellnessWeeklyReport):
    """Render a weekly wellness report card."""
    trend_icon = "📈" if report.completion_rate > 0.7 else "➡️" if report.completion_rate > 0.5 else "📉"

    streaks_html = ""
    for sh in report.streak_highlights:
        streaks_html += f"<span style='margin-right: 8px;'>🔥 {sh['habit']}: {sh['streak']}</span>"

    st.markdown(f"""
    <div style='
        padding: 20px;
        background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(240,253,244,0.85));
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 16px;
        margin-bottom: 14px;
    '>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
            <div>
                <div style='font-size: 14px; font-weight: 700; color: #111827;'>Week of {report.week_start}</div>
                <div style='font-size: 11px; color: #9ca3af;'>{report.week_start} to {report.week_end}</div>
            </div>
            <span style='font-size: 20px;'>{trend_icon}</span>
        </div>
        <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px;'>
            <div style='text-align: center;'>
                <div style='font-size: 20px; font-weight: 800; color: #22c55e;'>{report.total_habits_completed}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>Habits Done</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 20px; font-weight: 800; color: #0ea5e9;'>{report.total_eco_points}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>Eco Points</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 20px; font-weight: 800; color: #16a34a;'>{report.total_carbon_saved_kg:.1f}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>kg CO₂ Saved</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 20px; font-weight: 800; color: #8b5cf6;'>{report.completion_rate:.0%}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>Completion</div>
            </div>
        </div>
        <div style='display: flex; gap: 16px; font-size: 11px; color: #6b7280; margin-bottom: 8px;'>
            <span>😊 Mood: {report.avg_mood}/5</span>
            <span>⚡ Energy: {report.avg_energy}/5</span>
            <span>🌿 Nature: {report.total_nature_minutes} min</span>
            <span>🧘 Mindful: {report.total_mindfulness_minutes} min</span>
        </div>
        <div style='font-size: 11px; color: #9ca3af;'>🏆 Top: {report.top_habit}</div>
    </div>
    """, unsafe_allow_html=True)


def render_mood_energy_selector():
    """Render mood and energy level selectors."""
    col_mood, col_energy = st.columns(2)

    with col_mood:
        st.markdown("**How are you feeling?**")
        mood = st.radio(
            "Mood",
            options=list(MOOD_LABELS.keys()),
            format_func=lambda x: MOOD_LABELS[x],
            horizontal=True,
            key="wellness_mood",
        )

    with col_energy:
        st.markdown("**Energy level?**")
        energy = st.radio(
            "Energy",
            options=list(ENERGY_LABELS.keys()),
            format_func=lambda x: ENERGY_LABELS[x],
            horizontal=True,
            key="wellness_energy",
        )

    return mood, energy


def render_log_entry(log: Dict, habit_name: str = "", habit_icon: str = "🌿"):
    """Render a single activity log entry."""
    st.markdown(f"""
    <div style='
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        background: rgba(255,255,255,0.6);
        border-radius: 8px;
        margin-bottom: 4px;
    '>
        <span style='font-size: 16px;'>{habit_icon}</span>
        <div style='flex: 1;'>
            <div style='font-size: 12px; font-weight: 600; color: #111827;'>{habit_name or log.get('habit_id', '')}</div>
            <div style='font-size: 10px; color: #9ca3af;'>{log.get('completed_at', '')}</div>
        </div>
        <span style='font-size: 11px; font-weight: 700; color: #22c55e;'>+{log.get('eco_points_earned', 0)} pts</span>
    </div>
    """, unsafe_allow_html=True)
