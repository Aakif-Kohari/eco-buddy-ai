"""Streamlit card components for the Eco Impact Comparison Dashboard."""

import streamlit as st
from typing import List, Dict, Optional
from src.reporting.eco_impact_types import (
    UserProfile, CommunityStats, ComparisonResult,
    ImpactTrend, GoalProgress, EcoChallenge,
    ImpactCategory, TrendDirection, BadgeLevel,
)


def render_metric_card(
    title: str, value: str, subtitle: str = "",
    icon: str = "📊", delta: str = "", delta_color: str = "normal"
):
    """Render a styled metric card."""
    delta_html = ""
    if delta:
        color = "#22c55e" if delta_color == "normal" else "#ef4444"
        delta_html = f"""
        <div style='margin-top: 6px; font-size: 13px; font-weight: 600; color: {color};'>
            {delta}
        </div>
        """

    st.markdown(f"""
    <div style='
        padding: 20px 24px;
        background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(232,244,216,0.82));
        border: 1px solid rgba(74, 222, 128, 0.2);
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(57, 86, 47, 0.12);
        margin-bottom: 16px;
        transition: transform 180ms ease;
    '>
        <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 8px;'>
            <span style='font-size: 24px;'>{icon}</span>
            <span style='font-size: 13px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;'>{title}</span>
        </div>
        <div style='font-size: 28px; font-weight: 800; color: #111827; line-height: 1.2;'>{value}</div>
        {f'<div style="font-size: 12px; color: #6b7280; margin-top: 4px;">{subtitle}</div>' if subtitle else ''}
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_user_profile_card(user: UserProfile, is_current_user: bool = False):
    """Render a user profile comparison card."""
    badge_colors = {
        "Bronze": ("#cd7f32", "#8b5a2b"),
        "Silver": ("#c0c0c0", "#708090"),
        "Gold": ("#ffd700", "#b8860b"),
        "Platinum": ("#e5e4e2", "#8e8d8c"),
        "Diamond": ("#b9f2ff", "#4fc3f7"),
    }

    badges_html = ""
    for badge in user.badges[:3]:
        bg, fg = badge_colors.get(badge, ("#9ca3af", "#374151"))
        badges_html += f"""
        <span style='
            display: inline-block;
            padding: 2px 8px;
            background: {bg};
            color: {fg};
            border-radius: 12px;
            font-size: 10px;
            font-weight: 700;
            margin-right: 4px;
        '>{badge}</span>
        """

    border_style = "2px solid #22c55e" if is_current_user else "1px solid rgba(0,0,0,0.08)"

    st.markdown(f"""
    <div style='
        padding: 18px;
        background: {"linear-gradient(145deg, rgba(34,197,94,0.08), rgba(255,255,255,0.95))" if is_current_user else "rgba(255,255,255,0.9)"};
        border: {border_style};
        border-radius: 14px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    '>
        <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 10px;'>
            <div style='
                width: 42px; height: 42px;
                border-radius: 50%;
                background: linear-gradient(135deg, #22c55e, #16a34a);
                display: flex; align-items: center; justify-content: center;
                color: white; font-weight: 800; font-size: 16px;
            '>{user.display_name[0]}</div>
            <div>
                <div style='font-size: 14px; font-weight: 700; color: #111827;'>{user.display_name} {"(You)" if is_current_user else ""}</div>
                <div style='font-size: 11px; color: #6b7280;'>@{user.username} · {user.region}</div>
            </div>
        </div>
        <div style='display: flex; gap: 16px; margin-bottom: 8px;'>
            <div style='text-align: center;'>
                <div style='font-size: 18px; font-weight: 800; color: #16a34a;'>{user.eco_score}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>Eco Score</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 18px; font-weight: 800; color: #0ea5e9;'>{user.carbon_saved_kg:.0f}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>kg Saved</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 18px; font-weight: 800; color: #8b5cf6;'>{user.trees_equivalent:.0f}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>Trees Eq.</div>
            </div>
        </div>
        <div style='margin-top: 6px;'>{badges_html}</div>
    </div>
    """, unsafe_allow_html=True)


def render_comparison_card(result: ComparisonResult):
    """Render a comparison result card."""
    icon = "🏆" if result.is_above_average else "📈"
    color = "#22c55e" if result.is_above_average else "#f59e0b"
    status_text = "Above Average" if result.is_above_average else "Room to Improve"

    st.markdown(f"""
    <div style='
        padding: 18px;
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(0,0,0,0.08);
        border-left: 4px solid {color};
        border-radius: 14px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    '>
        <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 10px;'>
            <span style='font-size: 20px;'>{icon}</span>
            <span style='font-size: 14px; font-weight: 700; color: #111827; text-transform: capitalize;'>{result.category.value}</span>
            <span style='
                margin-left: auto;
                padding: 2px 10px;
                background: {color}22;
                color: {color};
                border-radius: 10px;
                font-size: 11px;
                font-weight: 700;
            '>{status_text}</span>
        </div>
        <div style='display: flex; gap: 20px; margin-bottom: 8px;'>
            <div>
                <div style='font-size: 11px; color: #6b7280; text-transform: uppercase;'>Your Value</div>
                <div style='font-size: 16px; font-weight: 800; color: #111827;'>{result.user_value:.1f}</div>
            </div>
            <div>
                <div style='font-size: 11px; color: #6b7280; text-transform: uppercase;'>Community Avg</div>
                <div style='font-size: 16px; font-weight: 800; color: #6b7280;'>{result.community_avg:.1f}</div>
            </div>
            <div>
                <div style='font-size: 11px; color: #6b7280; text-transform: uppercase;'>Percentile</div>
                <div style='font-size: 16px; font-weight: 800; color: {color};'>{result.percentile:.0f}%</div>
            </div>
        </div>
        <div style='display: flex; gap: 12px; font-size: 11px; color: #6b7280;'>
            <span>Rank: #{result.rank}/{result.total_participants}</span>
            <span>·</span>
            <span>Potential: {result.improvement_potential_kg:.1f} kg</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_goal_card(goal: GoalProgress):
    """Render a goal progress card."""
    progress = goal.progress_percent
    color = "#22c55e" if progress >= 80 else "#f59e0b" if progress >= 50 else "#ef4444"
    status = "Completed ✅" if goal.is_completed else f"{goal.days_remaining} days left"

    st.markdown(f"""
    <div style='
        padding: 16px;
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    '>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
            <span style='font-size: 13px; font-weight: 700; color: #111827;'>{goal.title}</span>
            <span style='font-size: 11px; color: {color}; font-weight: 600;'>{status}</span>
        </div>
        <div style='font-size: 12px; color: #6b7280; margin-bottom: 8px;'>
            {goal.current_value:.0f} / {goal.target_value:.0f} {goal.unit}
        </div>
        <div style='
            width: 100%;
            height: 8px;
            background: #e5e7eb;
            border-radius: 999px;
            overflow: hidden;
        '>
            <div style='
                width: {progress}%;
                height: 100%;
                background: linear-gradient(90deg, {color}, {color}cc);
                border-radius: 999px;
                transition: width 600ms ease;
            '></div>
        </div>
        <div style='font-size: 11px; color: #9ca3af; margin-top: 6px;'>{progress:.0f}% complete</div>
    </div>
    """, unsafe_allow_html=True)


def render_challenge_card(challenge: EcoChallenge):
    """Render an eco challenge card."""
    fill_percent = (challenge.participants / challenge.max_participants) * 100
    cat_colors = {
        ImpactCategory.CARBON: "#22c55e",
        ImpactCategory.WATER: "#0ea5e9",
        ImpactCategory.ENERGY: "#f59e0b",
        ImpactCategory.WASTE: "#8b5cf6",
        ImpactCategory.TRANSPORT: "#ec4899",
        ImpactCategory.FOOD: "#14b8a6",
    }
    color = cat_colors.get(challenge.category, "#6b7280")

    st.markdown(f"""
    <div style='
        padding: 18px;
        background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(232,244,216,0.72));
        border: 1px solid rgba(0,0,0,0.08);
        border-top: 3px solid {color};
        border-radius: 14px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    '>
        <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 8px;'>
            <span style='
                padding: 2px 8px;
                background: {color}22;
                color: {color};
                border-radius: 8px;
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
            '>{challenge.category.value}</span>
            <span style='font-size: 11px; color: #9ca3af;'>{challenge.duration_days} days</span>
        </div>
        <div style='font-size: 14px; font-weight: 700; color: #111827; margin-bottom: 4px;'>{challenge.title}</div>
        <div style='font-size: 12px; color: #6b7280; margin-bottom: 10px;'>{challenge.description}</div>
        <div style='display: flex; justify-content: space-between; font-size: 11px; color: #6b7280; margin-bottom: 6px;'>
            <span>{challenge.participants:,} / {challenge.max_participants:,} participants</span>
            <span style='color: {color}; font-weight: 600;'>🎯 {challenge.target_reduction_percent:.0f}% target</span>
        </div>
        <div style='width: 100%; height: 6px; background: #e5e7eb; border-radius: 999px; overflow: hidden;'>
            <div style='width: {fill_percent}%; height: 100%; background: {color}; border-radius: 999px;'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_trend_indicator(trend: ImpactTrend):
    """Render a trend indicator card."""
    direction_config = {
        TrendDirection.IMPROVING: ("📉", "#22c55e", "Improving"),
        TrendDirection.STABLE: ("➡️", "#6b7280", "Stable"),
        TrendDirection.WORSENING: ("📈", "#ef4444", "Worsening"),
    }
    icon, color, label = direction_config.get(trend.direction, ("➡️", "#6b7280", "Unknown"))

    st.markdown(f"""
    <div style='
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        background: {color}15;
        border: 1px solid {color}30;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        color: {color};
    '>
        <span>{icon}</span>
        <span>{label}</span>
        <span style='font-weight: 800;'>{abs(trend.change_percent):.1f}%</span>
    </div>
    """, unsafe_allow_html=True)


def render_leaderboard_row(
    rank: int, user: UserProfile, is_current_user: bool = False
):
    """Render a single leaderboard row."""
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
    bg = "rgba(34,197,94,0.06)" if is_current_user else "transparent"

    st.markdown(f"""
    <div style='
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        background: {bg};
        border-radius: 10px;
        margin-bottom: 4px;
    '>
        <span style='font-size: 18px; width: 32px; text-align: center;'>{medal}</span>
        <div style='
            width: 34px; height: 34px;
            border-radius: 50%;
            background: linear-gradient(135deg, #22c55e, #16a34a);
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: 800; font-size: 14px;
        '>{user.display_name[0]}</div>
        <div style='flex: 1;'>
            <div style='font-size: 13px; font-weight: 700; color: #111827;'>{user.display_name} {"(You)" if is_current_user else ""}</div>
            <div style='font-size: 10px; color: #9ca3af;'>{user.region} · {user.diet_type}</div>
        </div>
        <div style='text-align: right;'>
            <div style='font-size: 16px; font-weight: 800; color: #16a34a;'>{user.eco_score}</div>
            <div style='font-size: 9px; color: #9ca3af;'>eco score</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
