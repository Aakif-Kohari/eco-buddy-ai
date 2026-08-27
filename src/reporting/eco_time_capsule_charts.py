"""
Eco Impact Time Capsule — Chart Components
=============================================
Plotly visualizations for capsule timeline, growth tracking, and mood distribution.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, List

COLORS = {"purple": "#6366f1", "violet": "#a855f7", "green": "#22c55e",
          "amber": "#f59e0b", "red": "#ef4444", "blue": "#3b82f6",
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

def render_timeline_chart(timeline: List[Dict[str, Any]]) -> go.Figure:
    if not timeline:
        return _layout(go.Figure(), "Capsule Timeline")
    data = list(reversed(timeline))
    dates = [d["date"] for d in data]
    scores = [d.get("eco_score", 0) for d in data]
    carbons = [d.get("carbon_kg", 0) for d in data]
    titles = [d.get("title", "") for d in data]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=dates, y=scores, mode="lines+markers", name="Eco Score",
        line=dict(color=COLORS["purple"], width=3),
        marker=dict(size=10, color=COLORS["purple"], line=dict(width=2, color="white")),
        text=titles, hovertemplate="%{text}<br>Score: %{y}<br>%{x}<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=dates, y=carbons, name="Carbon (kg)",
        marker_color="rgba(34,197,94,0.3)", marker_line=dict(color=COLORS["green"], width=1),
    ), secondary_y=True)
    fig.update_yaxes(title_text="Eco Score", secondary_y=False)
    fig.update_yaxes(title_text="Carbon (kg)", secondary_y=True, showgrid=False)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"))
    return _layout(fig, "📈 Your Eco Journey Timeline", 340)

def render_mood_distribution(capsules: List[Dict[str, Any]]) -> go.Figure:
    mood_counts = {}
    for c in capsules:
        m = c.get("mood", "neutral")
        mood_counts[m] = mood_counts.get(m, 0) + 1
    if not mood_counts:
        return _layout(go.Figure(), "Mood Distribution")
    emoji_map = {"amazing":"🤩","great":"😊","good":"🙂","neutral":"😐","struggling":"😔","terrible":"😢"}
    labels = [f"{emoji_map.get(k,'')} {k.title()}" for k in mood_counts.keys()]
    values = list(mood_counts.values())
    colors = ["#22c55e", "#86efac", "#a3e635", "#fbbf24", "#f97316", "#ef4444"][:len(labels)]
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.5,
        marker=dict(colors=colors, line=dict(width=2, color="white")),
        textinfo="label+percent", textposition="outside",
    )])
    fig.add_annotation(text=f"<b>{sum(values)}</b><br>Capsules", x=0.5, y=0.5,
                        font=dict(size=15, color=COLORS["text"]), showarrow=False)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"))
    return _layout(fig, "🎭 Mood Over Time", 320)

def render_comparison_radar(comparison: Dict[str, Any]) -> go.Figure:
    comp = comparison.get("comparison", {})
    if not comp:
        return _layout(go.Figure(), "Comparison Radar")
    metrics = [k for k in comp if k != "days_between"]
    # Normalize values to 0-100 scale for radar
    a_vals, b_vals = [], []
    for m in metrics:
        d = comp[m]
        max_val = max(abs(d["a"]), abs(d["b"]), 1)
        a_vals.append(round(d["a"] / max_val * 100, 1))
        b_vals.append(round(d["b"] / max_val * 100, 1))
    labels = [m.replace("_", " ").title() for m in metrics]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=a_vals + [a_vals[0]], theta=labels + [labels[0]],
        fill="toself", name=comparison.get("capsule_a", {}).get("title", "A")[:15],
        line=dict(color=COLORS["purple"]), fillcolor="rgba(99,102,241,0.15)"))
    fig.add_trace(go.Scatterpolar(
        r=b_vals + [b_vals[0]], theta=labels + [labels[0]],
        fill="toself", name=comparison.get("capsule_b", {}).get("title", "B")[:15],
        line=dict(color=COLORS["green"]), fillcolor="rgba(34,197,94,0.15)"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                      showlegend=True, legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"))
    return _layout(fig, "🎯 Capsule Comparison Radar", 380)

def render_score_gauge(score: float, title: str = "Eco Score") -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number=dict(font=dict(size=30, color=COLORS["text"])),
        gauge=dict(
            axis=dict(range=[0, 100]),
            bar=dict(color=COLORS["purple"], thickness=0.25),
            bgcolor="rgba(0,0,0,0.04)",
            steps=[dict(range=[0, 30], color="rgba(239,68,68,0.08)"),
                   dict(range=[30, 60], color="rgba(234,179,8,0.08)"),
                   dict(range=[60, 100], color="rgba(34,197,94,0.08)")],
            threshold=dict(line=dict(color=COLORS["purple"], width=3), thickness=0.8, value=score),
        )))
    return _layout(fig, title, 240)

def render_capsule_type_bar(capsules: List[Dict[str, Any]]) -> go.Figure:
    types = {}
    for c in capsules:
        t = c.get("capsule_type", "snapshot")
        types[t] = types.get(t, 0) + 1
    labels = [k.replace("_", " ").title() for k in types.keys()]
    values = list(types.values())
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=[COLORS["purple"], COLORS["violet"], COLORS["green"], COLORS["amber"], COLORS["blue"]][:len(labels)],
        text=values, textposition="auto",
    ))
    fig.update_layout(yaxis_title="Count")
    return _layout(fig, "📦 Capsule Types", 240)
