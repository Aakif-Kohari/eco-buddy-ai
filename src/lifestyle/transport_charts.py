"""Chart visualizations for the Green Transportation Planner."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict
from src.lifestyle.transport_types import (
    TransportMode, TransportStats, MODE_ICONS, MODE_COLORS,
)


def create_mode_distribution_pie(mode_dist: Dict[str, int]) -> go.Figure:
    """Create a pie chart of transport mode distribution."""
    labels = [k.replace("_", " ").title() for k in mode_dist.keys()]
    values = list(mode_dist.values())
    colors = ["#22c55e", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ef4444", "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#94a3b8"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker=dict(colors=colors[:len(labels)], line=dict(width=2, color="white")),
        textinfo="percent+label",
        textfont=dict(size=11, color="#374151"),
        hovertemplate="<b>%{label}</b><br>%{value} trips<br>%{percent}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Trips by Transport Mode", font=dict(size=14, color="#374151")),
        height=320,
        margin=dict(t=40, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5, font=dict(size=9)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_monthly_trend_chart(monthly: List[Dict]) -> go.Figure:
    """Create a grouped bar chart of monthly trends."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    periods = [d["period"] for d in monthly]
    trips = [d["trips"] for d in monthly]
    emission = [d["emission"] for d in monthly]
    cost = [d["cost"] for d in monthly]

    fig.add_trace(go.Bar(
        x=periods, y=trips,
        name="Trips",
        marker=dict(color="#22c55e", cornerradius=4),
        text=trips,
        textposition="auto",
        textfont=dict(size=10, color="white"),
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=periods, y=emission,
        name="Emission (kg)",
        mode="lines+markers",
        line=dict(color="#ef4444", width=2),
        marker=dict(size=6),
    ), secondary_y=True)

    fig.add_trace(go.Scatter(
        x=periods, y=cost,
        name="Cost ($)",
        mode="lines+markers",
        line=dict(color="#f59e0b", width=2, dash="dot"),
        marker=dict(size=6),
    ), secondary_y=True)

    fig.update_layout(
        title=dict(text="Monthly Transport Trends", font=dict(size=14, color="#374151")),
        height=320,
        margin=dict(t=40, b=40, l=50, r=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#9ca3af")),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af"), title="Trips"),
        yaxis2=dict(tickfont=dict(size=10, color="#9ca3af"), title="kg / $", gridcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_emission_comparison_bar(comparisons: List) -> go.Figure:
    """Create a horizontal bar chart comparing emissions across modes."""
    modes = [c.mode_name for c in comparisons]
    emissions = [c.emission_kg for c in comparisons]
    colors = [MODE_COLORS.get(c.mode, "#6b7280") for c in comparisons]

    fig = go.Figure(go.Bar(
        x=emissions,
        y=modes,
        orientation="h",
        marker=dict(color=colors, cornerradius=4),
        text=[f"{e:.3f} kg" for e in emissions],
        textposition="auto",
        textfont=dict(size=10, color="white"),
    ))

    fig.update_layout(
        title=dict(text="CO₂ Emissions by Mode (per km)", font=dict(size=14, color="#374151")),
        height=350,
        margin=dict(t=40, b=20, l=120, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af"), title="kg CO₂/km"),
        yaxis=dict(autorange="reversed", tickfont=dict(size=11, color="#374151")),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_cost_vs_emission_scatter(comparisons: List) -> go.Figure:
    """Create a scatter chart of cost vs emission."""
    modes = [c.mode_name for c in comparisons]
    costs = [c.cost_usd for c in comparisons]
    emissions = [c.emission_kg for c in comparisons]
    times = [c.time_minutes for c in comparisons]
    colors = [MODE_COLORS.get(c.mode, "#6b7280") for c in comparisons]

    fig = go.Figure(go.Scatter(
        x=costs,
        y=emissions,
        mode="markers+text",
        marker=dict(
            size=[max(t / 3, 8) for t in times],
            color=colors,
            opacity=0.8,
            line=dict(width=1, color="white"),
        ),
        text=modes,
        textposition="top center",
        textfont=dict(size=9, color="#6b7280"),
        hovertemplate="<b>%{text}</b><br>Cost: $%{x:.2f}<br>Emission: %{y:.3f} kg<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Cost vs Emission", font=dict(size=14, color="#374151")),
        height=320,
        margin=dict(t=40, b=40, l=50, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Cost ($)", showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af")),
        yaxis=dict(title="Emission (kg CO₂)", showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af")),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_emission_waterfall(total_emission: float, avoided: float) -> go.Figure:
    """Create a waterfall chart showing emission breakdown."""
    fig = go.Figure(go.Waterfall(
        name="Emissions",
        orientation="v",
        measure=["absolute", "relative", "total"],
        x=["Actual Emission", "Avoided (Green Choices)", "Net Impact"],
        y=[total_emission, -avoided, 0],
        text=[f"{total_emission:.1f}", f"-{avoided:.1f}", f"{total_emission - avoided:.1f}"],
        textposition="outside",
        textfont=dict(size=11, color="#374151"),
        connector=dict(line=dict(color="#d1d5db")),
        increasing=dict(marker=dict(color="#ef4444")),
        decreasing=dict(marker=dict(color="#22c55e")),
        totals=dict(marker=dict(color="#0ea5e9")),
    ))

    fig.update_layout(
        title=dict(text="Emission Impact Waterfall", font=dict(size=14, color="#374151")),
        height=300,
        margin=dict(t=40, b=40, l=50, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af"), title="kg CO₂"),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_route_radar(route1, route2) -> go.Figure:
    """Create a radar chart comparing two routes."""
    categories = ["Speed", "Low Emission", "Low Cost", "Comfort", "Calories"]

    def route_scores(r):
        max_time = 120
        max_cost = 10
        max_cal = 500
        return [
            max(0, 1 - r.duration_minutes / max_time) * 100,
            max(0, 1 - r.emission_kg / 5) * 100,
            max(0, 1 - r.cost_usd / max_cost) * 100,
            70,
            min(r.calories_burned / max_cal, 1.0) * 100,
        ]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=route_scores(route1) + [route_scores(route1)[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(34,197,94,0.15)",
        line=dict(color="#22c55e", width=2),
        name=route1.mode.value.replace("_", " ").title(),
    ))

    fig.add_trace(go.Scatterpolar(
        r=route_scores(route2) + [route_scores(route2)[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(239,68,68,0.1)",
        line=dict(color="#ef4444", width=2, dash="dash"),
        name=route2.mode.value.replace("_", " ").title(),
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9, color="#9ca3af")),
            angularaxis=dict(tickfont=dict(size=10, color="#374151")),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        title=dict(text="Route Comparison", font=dict(size=14, color="#374151")),
        height=350,
        margin=dict(t=40, b=50, l=60, r=60),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif"},
    )
    return fig
