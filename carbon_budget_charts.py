"""
Carbon Budget Planner — Chart Components
==========================================
Plotly visualizations for budget tracking, category breakdowns, and projections.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, List, Optional

COLORS = {
    "green": "#22c55e", "red": "#ef4444", "yellow": "#f59e0b", "blue": "#3b82f6",
    "grid": "rgba(0,0,0,0.06)", "text": "#374151", "bg": "rgba(0,0,0,0)",
    "cat": ["#22c55e", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#0ea5e9"],
}

def _layout(fig, title="", height=350):
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=COLORS["text"]), x=0.02),
        height=height, paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"],
        font=dict(family="Inter, sans-serif", color=COLORS["text"]),
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(gridcolor=COLORS["grid"]), yaxis=dict(gridcolor=COLORS["grid"]),
    )
    return fig

def render_gauge_chart(used: float, limit: float, title: str = "Budget Used") -> go.Figure:
    pct = min(100, (used / limit * 100)) if limit > 0 else 0
    color = COLORS["red"] if pct >= 100 else COLORS["yellow"] if pct >= 80 else COLORS["green"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=pct, number=dict(suffix="%", font=dict(size=32, color=COLORS["text"])),
        delta=dict(reference=80, increasing=dict(color=COLORS["red"]), decreasing=dict(color=COLORS["green"])),
        gauge=dict(
            axis=dict(range=[0, 100]),
            bar=dict(color=color, thickness=0.25),
            bgcolor="rgba(0,0,0,0.04)",
            steps=[dict(range=[0, 60], color="rgba(34,197,94,0.08)"),
                   dict(range=[60, 80], color="rgba(234,179,8,0.08)"),
                   dict(range=[80, 100], color="rgba(239,68,68,0.1)")],
            threshold=dict(line=dict(color=color, width=3), thickness=0.8, value=pct),
        )))
    return _layout(fig, title, 260)

def render_category_bar_chart(cat_data: Dict[str, float], cat_limits: Dict[str, float],
                               cat_labels: Optional[Dict[str, str]] = None) -> go.Figure:
    cats = list(cat_data.keys())
    spent = [cat_data.get(c, 0) for c in cats]
    limits = [cat_limits.get(c, 0) for c in cats]
    labels = [cat_labels.get(c, c) if cat_labels else c for c in cats]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=limits, name="Budget", orientation="h",
                          marker_color="rgba(148,163,184,0.25)", marker_line=dict(width=0)))
    fig.add_trace(go.Bar(y=labels, x=spent, name="Spent", orientation="h",
                          marker_color=[COLORS["red"] if s > l else COLORS["green"] for s, l in zip(spent, limits)],
                          text=[f"{s:.1f}" for s in spent], textposition="auto"))
    fig.update_layout(barmode="overlay", yaxis=dict(autorange="reversed"), showlegend=True,
                      legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"))
    return _layout(fig, "Category Spending vs Budget", 320)

def render_daily_trend(daily_data: List[Dict[str, Any]], daily_budget: float = 16.7) -> go.Figure:
    dates = [d["log_date"] for d in daily_data]
    values = [d.get("total_kg", 0) for d in daily_data]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=values, mode="lines+markers", name="Daily CO₂",
        line=dict(color=COLORS["green"], width=3),
        marker=dict(size=7, color=COLORS["green"], line=dict(width=2, color="white")),
        fill="tozeroy", fillcolor="rgba(34,197,94,0.08)"))
    fig.add_hline(y=daily_budget, line_dash="dash", line_color=COLORS["yellow"],
                  annotation_text=f"Daily Budget: {daily_budget:.1f} kg",
                  annotation_position="top right")
    return _layout(fig, "Daily Carbon Spending Trend", 300)

def render_projection_chart(projected: float, limit: float, daily_avg: float, days_remaining: int) -> go.Figure:
    months = ["Current", "Projected"]
    values = [0, projected]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=months, y=[limit, limit], name="Budget Limit",
                          marker_color="rgba(148,163,184,0.2)", marker_line=dict(width=0)))
    color = COLORS["red"] if projected > limit else COLORS["green"]
    fig.add_trace(go.Bar(x=months, y=[0, projected], name="Projected Spend",
                          marker_color=color, text=[f"", f"{projected:.0f} kg"],
                          textposition="auto"))
    fig.update_layout(barmode="group", showlegend=True,
                      legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
                      annotations=[dict(text=f"📊 Avg: {daily_avg:.1f} kg/day · {days_remaining} days left",
                                        x=0.5, y=1.12, xref="paper", yref="paper", showarrow=False,
                                        font=dict(size=12, color=COLORS["text"]))])
    return _layout(fig, "Monthly Projection", 280)

def render_history_line(history: List[Dict[str, Any]]) -> go.Figure:
    if not history:
        return _layout(go.Figure(), "Budget History")
    months = [h["month"] for h in reversed(history)]
    spent = [h["total_spent_kg"] for h in reversed(history)]
    limits = [h["monthly_limit_kg"] for h in reversed(history)]
    savings = [h["savings_kg"] for h in reversed(history)]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=months, y=spent, name="Spent", mode="lines+markers",
                              line=dict(color=COLORS["green"], width=3),
                              marker=dict(size=6)), secondary_y=False)
    fig.add_trace(go.Scatter(x=months, y=limits, name="Limit", mode="lines",
                              line=dict(color=COLORS["yellow"], width=2, dash="dash")), secondary_y=False)
    fig.add_trace(go.Bar(x=months, y=savings, name="Savings", marker_color="rgba(34,197,94,0.2)"),
                   secondary_y=True)
    fig.update_yaxes(title_text="kg CO₂", secondary_y=False)
    fig.update_yaxes(title_text="Saved", secondary_y=True, showgrid=False)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"))
    return _layout(fig, "Budget History (12 Months)", 320)

def render_pie_chart(cat_data: Dict[str, float], cat_labels: Optional[Dict[str, str]] = None) -> go.Figure:
    labels = [cat_labels.get(k, k) if cat_labels else k for k in cat_data.keys()]
    values = list(cat_data.values())
    if not any(values):
        return _layout(go.Figure(), "Spending Distribution")
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.5,
        marker=dict(colors=COLORS["cat"][:len(labels)], line=dict(width=2, color="white")),
        textinfo="label+percent", textposition="outside",
    )])
    fig.add_annotation(text=f"<b>{sum(values):.1f}</b><br>kg CO₂", x=0.5, y=0.5,
                        font=dict(size=15, color=COLORS["text"]), showarrow=False)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"))
    return _layout(fig, "Spending by Category", 340)

def render_co2_equivalence(saved_kg: float) -> go.Figure:
    trees = saved_kg / 21.0
    miles_not_driven = saved_kg / 0.21
    smartphones = saved_kg / 70.0
    fig = go.Figure(go.Bar(
        x=["🌳 Trees Planted", "🚗 Miles Not Driven", "📱 Smartphones Avoided"],
        y=[trees, miles_not_driven, smartphones],
        marker_color=[COLORS["green"], COLORS["blue"], COLORS["yellow"]],
        text=[f"{trees:.1f}", f"{miles_not_driven:.0f}", f"{smartphones:.1f}"],
        textposition="auto",
    ))
    fig.update_layout(yaxis_title="Equivalent Amount")
    return _layout(fig, f"🌍 Your {saved_kg:.1f} kg Saved Equals...", 250)
