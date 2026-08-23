"""Chart visualization components for the Eco Impact Comparison Dashboard."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict, Optional
from eco_impact_types import (
    ImpactCategory, TrendDirection, ImpactTrend, ComparisonResult,
)


def create_eco_score_gauge(score: float, max_score: float = 100) -> go.Figure:
    """Create a gauge chart for eco score."""
    color = "#22c55e" if score >= 70 else "#f59e0b" if score >= 40 else "#ef4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Eco Score", "font": {"size": 16, "color": "#374151"}},
        number={"font": {"size": 48, "color": color}},
        gauge={
            "axis": {"range": [0, max_score], "tickwidth": 1, "tickcolor": "#d1d5db"},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 40], "color": "#fef2f2"},
                {"range": [40, 70], "color": "#fffbeb"},
                {"range": [70, 100], "color": "#f0fdf4"},
            ],
            "threshold": {
                "line": {"color": "#111827", "width": 3},
                "thickness": 0.8,
                "value": score,
            },
        },
    ))

    fig.update_layout(
        height=280,
        margin=dict(t=50, b=20, l=30, r=30),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_category_bar_chart(
    categories: Dict[str, float],
    title: str = "Impact by Category"
) -> go.Figure:
    """Create a horizontal bar chart for impact categories."""
    labels = list(categories.keys())
    values = list(categories.values())
    colors = ["#22c55e", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(
            color=colors[:len(labels)],
            line=dict(width=0),
            cornerradius=6,
        ),
        text=[f"{v:.1f}" for v in values],
        textposition="auto",
        textfont=dict(size=12, color="white", family="Inter"),
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#374151")),
        height=300,
        margin=dict(t=40, b=20, l=120, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(autorange="reversed", tickfont=dict(size=12, color="#374151")),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_trend_line_chart(
    trend: ImpactTrend,
    community_avg: Optional[float] = None
) -> go.Figure:
    """Create a line chart for trend data."""
    periods = [d["period"] for d in trend.data_points]
    values = [d["value"] for d in trend.data_points]

    color = "#22c55e" if trend.direction == TrendDirection.IMPROVING else \
            "#ef4444" if trend.direction == TrendDirection.WORSENING else "#6b7280"

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=periods,
        y=values,
        mode="lines+markers",
        name="Your Impact",
        line=dict(color=color, width=3, shape="spline"),
        marker=dict(size=8, color=color, line=dict(width=2, color="white")),
        fill="tozeroy",
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.1)",
    ))

    if community_avg is not None:
        fig.add_trace(go.Scatter(
            x=periods,
            y=[community_avg] * len(periods),
            mode="lines",
            name="Community Avg",
            line=dict(color="#9ca3af", width=2, dash="dash"),
        ))

    fig.update_layout(
        height=300,
        margin=dict(t=20, b=40, l=50, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=11, color="#9ca3af"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.05)",
            tickfont=dict(size=11, color="#9ca3af"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_comparison_radar(
    results: List[ComparisonResult]
) -> go.Figure:
    """Create a radar chart comparing user vs community."""
    categories = [r.category.value.title() for r in results]
    user_vals = [r.percentile for r in results]
    community_vals = [50] * len(results)

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=user_vals + [user_vals[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(34,197,94,0.15)",
        line=dict(color="#22c55e", width=2),
        name="You",
        marker=dict(size=8, color="#22c55e"),
    ))

    fig.add_trace(go.Scatterpolar(
        r=community_vals + [community_vals[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(156,163,175,0.1)",
        line=dict(color="#9ca3af", width=1, dash="dash"),
        name="Community Avg",
        marker=dict(size=5, color="#9ca3af"),
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=9, color="#9ca3af"),
                gridcolor="rgba(0,0,0,0.05)",
            ),
            angularaxis=dict(
                tickfont=dict(size=11, color="#374151"),
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        height=350,
        margin=dict(t=30, b=50, l=60, r=60),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_pie_chart(
    values: List[float],
    labels: List[str],
    title: str = "Distribution"
) -> go.Figure:
    """Create a donut pie chart."""
    colors = ["#22c55e", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(
            colors=colors[:len(labels)],
            line=dict(width=2, color="white"),
        ),
        textinfo="percent",
        textfont=dict(size=11, color="#374151"),
        hovertemplate="<b>%{label}</b><br>%{value:.1f}<br>%{percent}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#374151")),
        height=300,
        margin=dict(t=40, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=10),
        ),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_grouped_bar_chart(
    periods: List[str],
    user_data: List[float],
    community_data: List[float],
    y_title: str = "Value",
    title: str = "Monthly Comparison"
) -> go.Figure:
    """Create a grouped bar chart comparing user vs community."""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=periods,
        y=user_data,
        name="You",
        marker=dict(color="#22c55e", cornerradius=4),
        text=[f"{v:.0f}" for v in user_data],
        textposition="auto",
        textfont=dict(size=10, color="white"),
    ))

    fig.add_trace(go.Bar(
        x=periods,
        y=community_data,
        name="Community Avg",
        marker=dict(color="#d1d5db", cornerradius=4),
        text=[f"{v:.0f}" for v in community_data],
        textposition="auto",
        textfont=dict(size=10, color="#6b7280"),
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#374151")),
        barmode="group",
        height=320,
        margin=dict(t=40, b=40, l=50, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#9ca3af")),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.05)",
            title=dict(text=y_title, font=dict(size=11, color="#9ca3af")),
            tickfont=dict(size=11, color="#9ca3af"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_heatmap_calendar(
    weeks: int = 12,
    title: str = "Activity Heatmap"
) -> go.Figure:
    """Create a heatmap calendar showing eco activity."""
    import random

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    week_labels = [f"W{i+1}" for i in range(weeks)]

    z = [[random.randint(0, 10) for _ in range(weeks)] for _ in range(7)]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=week_labels,
        y=days,
        colorscale=[
            [0, "#f0fdf4"],
            [0.25, "#bbf7d0"],
            [0.5, "#4ade80"],
            [0.75, "#16a34a"],
            [1, "#052e16"],
        ],
        showscale=True,
        colorbar=dict(
            title=dict(text="Score", font=dict(size=10)),
            tickfont=dict(size=9),
            thickness=12,
            len=0.8,
        ),
        hovertemplate="<b>%{y}, %{x}</b><br>Score: %{z}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#374151")),
        height=250,
        margin=dict(t=40, b=20, l=50, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#9ca3af")),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=10, color="#9ca3af"),
        ),
        font={"family": "Inter, sans-serif"},
    )
    return fig
