"""
Community Eco Challenge Hub — Chart Components
===============================================
Plotly-based visualizations for challenge progress, participation trends,
category breakdowns, and leaderboard comparisons.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


# ── Color Palette ────────────────────────────────────────────────────────

COLORS = {
    "primary": "#22c55e",
    "secondary": "#16a34a",
    "accent": "#86efac",
    "bg": "rgba(0,0,0,0)",
    "grid": "rgba(0,0,0,0.06)",
    "text": "#374151",
    "muted": "#9ca3af",
    "gold": "#f59e0b",
    "silver": "#94a3b8",
    "bronze": "#cd7f32",
    "categories": ["#22c55e", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
                    "#06b6d4", "#ec4899", "#f97316", "#14b8a6"],
}


def _apply_layout(fig: go.Figure, title: str = "", height: int = 350):
    """Apply consistent layout styling."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS["text"]), x=0.02),
        height=height,
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
        font=dict(family="Inter, sans-serif", color=COLORS["text"]),
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(gridcolor=COLORS["grid"], showgrid=True, zeroline=False),
        yaxis=dict(gridcolor=COLORS["grid"], showgrid=True, zeroline=False),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter"),
    )
    return fig


# ── Daily Progress Line Chart ───────────────────────────────────────────

def render_progress_line_chart(daily_data: List[Dict[str, Any]], title: str = "Daily Progress") -> go.Figure:
    """Line chart of daily progress values with active user overlay."""
    dates = [d["log_date"] for d in daily_data]
    values = [d.get("total_value", 0) for d in daily_data]
    users = [d.get("active_users", 0) for d in daily_data]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=dates, y=values,
            mode="lines+markers",
            name="Progress Value",
            line=dict(color=COLORS["primary"], width=3),
            marker=dict(size=8, color=COLORS["primary"], line=dict(width=2, color="white")),
            fill="tozeroy",
            fillcolor="rgba(34,197,94,0.08)",
        ),
        secondary_y=False,
    )

    if any(u > 0 for u in users):
        fig.add_trace(
            go.Bar(
                x=dates, y=users,
                name="Active Users",
                marker_color="rgba(59,130,246,0.25)",
                marker_line=dict(color="rgba(59,130,246,0.5)", width=1),
            ),
            secondary_y=True,
        )

    fig.update_yaxes(title_text="Progress", secondary_y=False)
    fig.update_yaxes(title_text="Active Users", secondary_y=True, showgrid=False)

    return _apply_layout(fig, title, height=320)


# ── Category Donut Chart ────────────────────────────────────────────────

def render_category_donut(category_data: Dict[str, int], title: str = "Challenge Categories") -> go.Figure:
    """Donut chart showing distribution of challenge categories."""
    labels = list(category_data.keys())
    values = list(category_data.values())

    if not labels:
        return _apply_layout(go.Figure(), title)

    category_icons = {
        "transport": "🚗", "energy": "⚡", "diet": "🥗", "waste": "♻️",
        "water": "💧", "nature": "🌳", "health": "💪", "community": "🤝", "general": "📋",
    }
    display_labels = [f"{category_icons.get(l, '')} {l.title()}" for l in labels]

    fig = go.Figure(data=[go.Pie(
        labels=display_labels, values=values,
        hole=0.55,
        marker=dict(colors=COLORS["categories"][:len(labels)], line=dict(width=2, color="white")),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=12, color=COLORS["text"]),
    )])

    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center", font=dict(size=11)),
    )

    # Center annotation
    fig.add_annotation(
        text=f"<b>{sum(values)}</b><br>Challenges",
        x=0.5, y=0.5, font=dict(size=16, color=COLORS["text"]),
        showarrow=False,
    )

    return _apply_layout(fig, title, height=340)


# ── Difficulty Bar Chart ────────────────────────────────────────────────

def render_difficulty_bar(difficulty_data: Dict[str, int], title: str = "By Difficulty") -> go.Figure:
    """Horizontal bar chart of challenge difficulty distribution."""
    order = ["easy", "medium", "hard"]
    labels = [d.title() for d in order if d in difficulty_data]
    values = [difficulty_data[d] for d in order if d in difficulty_data]
    colors_map = {"Easy": "#22c55e", "Medium": "#eab308", "Hard": "#ef4444"}

    fig = go.Figure(data=[go.Bar(
        y=labels, x=values, orientation="h",
        marker_color=[colors_map.get(l, "#888") for l in labels],
        marker_line=dict(width=0),
        text=values, textposition="auto",
        textfont=dict(size=14, color="white", family="Inter"),
    )])

    fig.update_layout(yaxis=dict(autorange="reversed"))
    return _apply_layout(fig, title, height=200)


# ── Team Comparison Chart ──────────────────────────────────────────────

def render_team_comparison_chart(teams: List[Dict[str, Any]], title: str = "Team Leaderboard") -> go.Figure:
    """Radar/comparison chart for team scores."""
    if not teams:
        return _apply_layout(go.Figure(), title)

    names = [t["team_name"] for t in teams]
    scores = [t["total_score"] for t in teams]
    members = [t.get("member_count", 1) for t in teams]
    per_member = [s / m if m > 0 else 0 for s, m in zip(scores, members)]

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Total Score", "Per-Member Avg"))

    fig.add_trace(go.Bar(
        x=names, y=scores, name="Total Score",
        marker_color=COLORS["primary"],
        text=scores, textposition="auto",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=names, y=per_member, name="Avg Per Member",
        marker_color=COLORS["accent"],
        text=[f"{v:.1f}" for v in per_member], textposition="auto",
    ), row=1, col=2)

    fig.update_layout(showlegend=False)
    fig.update_yaxes(title_text="Score", row=1, col=1)
    fig.update_yaxes(title_text="Avg", row=1, col=2)

    return _apply_layout(fig, title, height=320)


# ── Progress Heatmap ───────────────────────────────────────────────────

def render_progress_heatmap(daily_data: List[Dict[str, Any]], title: str = "Activity Heatmap") -> go.Figure:
    """Weekly heatmap showing daily activity intensity."""
    if not daily_data:
        return _apply_layout(go.Figure(), title)

    # Build week/day matrix
    dates_vals = {d["log_date"]: d.get("total_value", 0) for d in daily_data}
    all_dates = sorted(dates_vals.keys())

    if not all_dates:
        return _apply_layout(go.Figure(), title)

    start = datetime.strptime(all_dates[0], "%Y-%m-%d")
    end = datetime.strptime(all_dates[-1], "%Y-%m-%d")

    weeks = []
    days_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    current = start - timedelta(days=start.weekday())
    while current <= end + timedelta(days=6):
        week = []
        for day_offset in range(7):
            d = current + timedelta(days=day_offset)
            ds = d.strftime("%Y-%m-%d")
            week.append(dates_vals.get(ds, 0))
        weeks.append(week)
        current += timedelta(days=7)

    fig = go.Figure(data=go.Heatmap(
        z=weeks,
        x=days_labels,
        y=[f"W{i+1}" for i in range(len(weeks))],
        colorscale=[
            [0, "rgba(240,253,244,0.6)"],
            [0.25, "rgba(134,239,172,0.6)"],
            [0.5, "rgba(34,197,94,0.6)"],
            [0.75, "rgba(22,163,74,0.8)"],
            [1, "rgba(5,46,22,0.9)"],
        ],
        hovertemplate="Day: %{x}<br>Week: %{y}<br>Value: %{z}<extra></extra>",
        showscale=True,
        colorbar=dict(title="Progress", thickness=12),
    ))

    return _apply_layout(fig, title, height=280)


# ── Streak Calendar ────────────────────────────────────────────────────

def render_streak_calendar(streak_dates: List[str], title: str = "Activity Calendar") -> go.Figure:
    """Simple timeline view of active days."""
    if not streak_dates:
        return _apply_layout(go.Figure(), title)

    active = set(streak_dates)
    all_dates = sorted(active)
    start = datetime.strptime(all_dates[0], "%Y-%m-%d")
    end = datetime.strptime(all_dates[-1], "%Y-%m-%d")

    current = start
    dates = []
    is_active = []
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        is_active.append(1 if current.strftime("%Y-%m-%d") in active else 0)
        current += timedelta(days=1)

    fig = go.Figure(data=go.Bar(
        x=dates, y=is_active,
        marker_color=[
            COLORS["primary"] if a else "rgba(200,200,200,0.2)" for a in is_active
        ],
        hovertemplate="%{x}: %{customdata}<extra></extra>",
        customdata=["Active ✅" if a else "Inactive" for a in is_active],
    ))

    fig.update_layout(yaxis=dict(visible=False, showticklabels=False))
    return _apply_layout(fig, title, height=180)


# ── Completion Gauge ───────────────────────────────────────────────────

def render_completion_gauge(progress_pct: float, title: str = "Completion") -> go.Figure:
    """Gauge chart showing overall completion percentage."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=progress_pct,
        number=dict(suffix="%", font=dict(size=28, color=COLORS["text"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1),
            bar=dict(color=COLORS["primary"], thickness=0.3),
            bgcolor="rgba(0,0,0,0.04)",
            steps=[
                dict(range=[0, 33], color="rgba(239,68,68,0.08)"),
                dict(range=[33, 66], color="rgba(234,179,8,0.08)"),
                dict(range=[66, 100], color="rgba(34,197,94,0.08)"),
            ],
            threshold=dict(line=dict(color=COLORS["secondary"], width=3), thickness=0.8, value=progress_pct),
        ),
    ))

    return _apply_layout(fig, title, height=240)
