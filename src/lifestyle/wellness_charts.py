"""Chart visualizations for the Eco Wellness Tracker."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict
from src.lifestyle.wellness_types import (
    DailyWellnessScore, HabitStreak, EcoHabit,
    CATEGORY_COLORS, STREAK_COLORS, HabitCategory,
)


def create_wellness_score_trend(scores: List[DailyWellnessScore]) -> go.Figure:
    """Create a line chart of daily wellness scores."""
    dates = [s.date for s in scores]
    eco_scores = [s.eco_score for s in scores]
    moods = [s.mood * 20 for s in scores]  # Scale to 0-100

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates, y=eco_scores,
        mode="lines+markers",
        name="Eco Score",
        line=dict(color="#22c55e", width=3, shape="spline"),
        marker=dict(size=6, color="#22c55e"),
        fill="tozeroy",
        fillcolor="rgba(34,197,94,0.08)",
    ))

    fig.add_trace(go.Scatter(
        x=dates, y=moods,
        mode="lines",
        name="Mood (scaled)",
        line=dict(color="#ec4899", width=2, dash="dot"),
    ))

    fig.update_layout(
        title=dict(text="Wellness Score Trend", font=dict(size=14, color="#374151")),
        height=300,
        margin=dict(t=40, b=40, l=50, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#9ca3af"), tickangle=-45),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af"), range=[0, 105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_habits_completion_bar(scores: List[DailyWellnessScore]) -> go.Figure:
    """Create a bar chart of daily habit completions."""
    dates = [s.date[-5:] for s in scores[-14:]]  # Last 14 days, MM-DD format
    completed = [s.habits_completed for s in scores[-14:]]
    total = [s.habits_total for s in scores[-14:]]
    rates = [c / t * 100 if t > 0 else 0 for c, t in zip(completed, total)]

    colors = ["#22c55e" if r >= 70 else "#f59e0b" if r >= 40 else "#ef4444" for r in rates]

    fig = go.Figure(go.Bar(
        x=dates,
        y=completed,
        marker=dict(color=colors, cornerradius=4),
        text=[f"{r:.0f}%" for r in rates],
        textposition="auto",
        textfont=dict(size=9, color="white"),
    ))

    fig.add_trace(go.Scatter(
        x=dates,
        y=total,
        mode="lines",
        name="Total Habits",
        line=dict(color="#d1d5db", width=1, dash="dash"),
    ))

    fig.update_layout(
        title=dict(text="Daily Habit Completions", font=dict(size=14, color="#374151")),
        height=280,
        margin=dict(t=40, b=40, l=40, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#9ca3af")),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af")),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_category_breakdown(habits: List[EcoHabit]) -> go.Figure:
    """Create a pie chart of habits by category."""
    cat_counts = {}
    for h in habits:
        cat = h.category.value.title()
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    labels = list(cat_counts.keys())
    values = list(cat_counts.values())
    colors = [CATEGORY_COLORS.get(HabitCategory(l.lower()), "#6b7280") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker=dict(colors=colors, line=dict(width=2, color="white")),
        textinfo="percent+label",
        textfont=dict(size=11, color="#374151"),
    ))

    fig.update_layout(
        title=dict(text="Habits by Category", font=dict(size=14, color="#374151")),
        height=300,
        margin=dict(t=40, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5, font=dict(size=9)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_streak_heatmap(streaks: List[HabitStreak], habits: List[EcoHabit]) -> go.Figure:
    """Create a heatmap of streak performance."""
    habit_map = {h.habit_id: h for h in habits}
    labels = []
    current_vals = []
    longest_vals = []

    for s in sorted(streaks, key=lambda x: x.current_streak, reverse=True)[:10]:
        h = habit_map.get(s.habit_id)
        if h:
            labels.append(h.name[:20])
            current_vals.append(s.current_streak)
            longest_vals.append(s.longest_streak)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=labels,
        x=current_vals,
        orientation="h",
        name="Current",
        marker=dict(color="#22c55e", cornerradius=4),
        text=[f"{v}d" for v in current_vals],
        textposition="auto",
        textfont=dict(size=10, color="white"),
    ))

    fig.add_trace(go.Bar(
        y=labels,
        x=longest_vals,
        orientation="h",
        name="Best",
        marker=dict(color="#d1d5db", cornerradius=4),
        text=[f"{v}d" for v in longest_vals],
        textposition="auto",
        textfont=dict(size=10, color="#6b7280"),
    ))

    fig.update_layout(
        title=dict(text="Streak Comparison", font=dict(size=14, color="#374151")),
        barmode="overlay",
        height=350,
        margin=dict(t=40, b=20, l=160, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af")),
        yaxis=dict(autorange="reversed", tickfont=dict(size=10, color="#374151")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_mood_energy_radar(scores: List[DailyWellnessScore]) -> go.Figure:
    """Create a radar chart of mood and energy patterns."""
    recent = scores[-7:] if len(scores) >= 7 else scores
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    moods = [s.mood for s in recent]
    energy = [s.energy_level for s in recent]
    eco = [s.eco_score / 20 for s in recent]  # Scale to 0-5

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=moods + [moods[0]],
        theta=days[:len(moods)] + [days[0]],
        fill="toself",
        fillcolor="rgba(236,72,153,0.15)",
        line=dict(color="#ec4899", width=2),
        name="Mood",
    ))

    fig.add_trace(go.Scatterpolar(
        r=energy + [energy[0]],
        theta=days[:len(energy)] + [days[0]],
        fill="toself",
        fillcolor="rgba(245,158,11,0.15)",
        line=dict(color="#f59e0b", width=2),
        name="Energy",
    ))

    fig.add_trace(go.Scatterpolar(
        r=eco + [eco[0]],
        theta=days[:len(eco)] + [days[0]],
        fill="toself",
        fillcolor="rgba(34,197,94,0.15)",
        line=dict(color="#22c55e", width=2),
        name="Eco Score",
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 5.5], tickfont=dict(size=9, color="#9ca3af")),
            angularaxis=dict(tickfont=dict(size=10, color="#374151")),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        title=dict(text="Weekly Mood & Energy Pattern", font=dict(size=14, color="#374151")),
        height=350,
        margin=dict(t=40, b=50, l=60, r=60),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_points_timeline(scores: List[DailyWellnessScore]) -> go.Figure:
    """Create a stacked bar chart of daily eco points and carbon saved."""
    dates = [s.date[-5:] for s in scores[-14:]]
    points = [s.eco_points for s in scores[-14:]]
    carbon = [s.carbon_saved_kg * 20 for s in scores[-14:]]  # Scale for visibility

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=dates, y=points,
        name="Eco Points",
        marker=dict(color="#22c55e", cornerradius=4),
    ))

    fig.add_trace(go.Bar(
        x=dates, y=carbon,
        name="Carbon Saved (scaled)",
        marker=dict(color="#0ea5e9", cornerradius=4),
    ))

    fig.update_layout(
        title=dict(text="Daily Eco Points & Carbon Impact", font=dict(size=14, color="#374151")),
        barmode="stack",
        height=280,
        margin=dict(t=40, b=40, l=40, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#9ca3af")),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_nature_mindfulness_area(scores: List[DailyWellnessScore]) -> go.Figure:
    """Create an area chart of nature time and mindfulness."""
    dates = [s.date[-5:] for s in scores[-14:]]
    nature = [s.nature_time_minutes for s in scores[-14:]]
    mindfulness = [s.mindfulness_minutes for s in scores[-14:]]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates, y=nature,
        mode="lines",
        name="Nature Time",
        line=dict(color="#16a34a", width=2),
        fill="tozeroy",
        fillcolor="rgba(22,163,74,0.1)",
    ))

    fig.add_trace(go.Scatter(
        x=dates, y=mindfulness,
        mode="lines",
        name="Mindfulness",
        line=dict(color="#ec4899", width=2),
        fill="tozeroy",
        fillcolor="rgba(236,72,153,0.1)",
    ))

    fig.update_layout(
        title=dict(text="Nature & Mindfulness Minutes", font=dict(size=14, color="#374151")),
        height=280,
        margin=dict(t=40, b=40, l=40, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#9ca3af")),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        font={"family": "Inter, sans-serif"},
    )
    return fig
