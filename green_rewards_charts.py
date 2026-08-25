"""
Green Rewards Marketplace — Chart Components
===============================================
Plotly charts for points history, level progress, and category breakdown.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, List

COLORS = {"green": "#22c55e", "blue": "#3b82f6", "amber": "#f59e0b", "purple": "#8b5cf6",
          "grid": "rgba(0,0,0,0.06)", "text": "#374151", "bg": "rgba(0,0,0,0)"}

def _layout(fig, title="", height=350):
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=COLORS["text"]), x=0.02),
        height=height, paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"],
        font=dict(family="Inter, sans-serif", color=COLORS["text"]),
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(gridcolor=COLORS["grid"]), yaxis=dict(gridcolor=COLORS["grid"]),
    )
    return fig

def render_points_history_chart(transactions: List[Dict[str, Any]]) -> go.Figure:
    if not transactions:
        return _layout(go.Figure(), "Points History")
    txs = list(reversed(transactions))
    dates = [t.get("created_at", "")[:10] for t in txs]
    running = 0
    cumulative = []
    for t in txs:
        running += t.get("points", 0)
        cumulative.append(running)
    colors = [COLORS["green"] if t.get("points", 0) > 0 else "#ef4444" for t in txs]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=cumulative, mode="lines+markers", name="Balance",
        line=dict(color=COLORS["green"], width=3),
        marker=dict(size=8, color=COLORS["green"], line=dict(width=2, color="white")),
        fill="tozeroy", fillcolor="rgba(34,197,94,0.08)"))
    fig.add_trace(go.Bar(
        x=dates, y=[t.get("points", 0) for t in txs],
        name="Transaction", marker_color=colors, opacity=0.6))
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"))
    return _layout(fig, "💰 Points History", 300)

def render_level_progress_gauge(progress: float, level: int, title: str = "Level Progress") -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=progress,
        number=dict(suffix="%", font=dict(size=28, color=COLORS["text"])),
        gauge=dict(
            axis=dict(range=[0, 100]),
            bar=dict(color=COLORS["green"], thickness=0.25),
            bgcolor="rgba(0,0,0,0.04)",
            steps=[dict(range=[0, 33], color="rgba(34,197,94,0.06)"),
                   dict(range=[33, 66], color="rgba(34,197,94,0.1)"),
                   dict(range=[66, 100], color="rgba(34,197,94,0.15)")],
            threshold=dict(line=dict(color=COLORS["green"], width=3), thickness=0.8, value=progress),
        )))
    fig.add_annotation(text=f"Level {level}", x=0.5, y=0.45, font=dict(size=14, color=COLORS["text"]), showarrow=False)
    return _layout(fig, title, 260)

def render_category_bar(actions_today: List[Dict[str, Any]]) -> go.Figure:
    cat_counts = {}
    for a in actions_today:
        c = a.get("action_category", "other")
        cat_counts[c] = cat_counts.get(c, 0) + 1
    if not cat_counts:
        return _layout(go.Figure(), "Today's Activity")
    labels = [k.title() for k in cat_counts.keys()]
    values = list(cat_counts.values())
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=[COLORS["green"], COLORS["blue"], COLORS["amber"], COLORS["purple"],
                       "#06b6d4", "#ec4899", "#f97316", "#14b8a6", "#ef4444"][:len(labels)],
        text=values, textposition="auto"))
    fig.update_layout(yaxis_title="Actions Completed")
    return _layout(fig, "📋 Today's Actions by Category", 240)

def render_category_donut(transactions: List[Dict[str, Any]]) -> go.Figure:
    cats = {}
    for t in transactions:
        if t.get("points", 0) > 0:
            desc = t.get("description", "Other")
            cats[desc[:20]] = cats.get(desc[:20], 0) + t.get("points", 0)
    if not cats:
        return _layout(go.Figure(), "Points by Source")
    fig = go.Figure(data=[go.Pie(
        labels=list(cats.keys()), values=list(cats.values()), hole=0.5,
        marker=dict(colors=[COLORS["green"], COLORS["blue"], COLORS["amber"], COLORS["purple"],
                            "#06b6d4", "#ec4899"][:len(cats)]),
        textinfo="label+percent", textposition="outside")])
    fig.add_annotation(text=f"<b>{sum(cats.values())}</b><br>pts", x=0.5, y=0.5,
                        font=dict(size=15, color=COLORS["text"]), showarrow=False)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"))
    return _layout(fig, "🎯 Points by Source", 320)

def render_leaderboard_chart(leaderboard: List[Dict[str, Any]]) -> go.Figure:
    if not leaderboard:
        return _layout(go.Figure(), "🏆 Leaderboard")
    names = [l.get("username", f"User-{l['user_id']}")[:15] for l in leaderboard[:10]]
    points = [l.get("total_points", 0) for l in leaderboard[:10]]
    fig = go.Figure(go.Bar(
        y=list(reversed(names)), x=list(reversed(points)), orientation="h",
        marker_color=[COLORS["green"] if i == 0 else COLORS["amber"] if i < 3 else COLORS["blue"]
                      for i in range(len(names)-1, -1, -1)],
        text=list(reversed(points)), textposition="auto"))
    fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Total Points")
    return _layout(fig, "🏆 Top Green Champions", 350)
