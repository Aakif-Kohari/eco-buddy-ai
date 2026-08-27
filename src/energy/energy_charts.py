"""Chart visualizations for the Energy Monitoring Dashboard."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict
from src.energy.energy_types import (
    ApplianceCategory, EnergySource, APPLIANCE_COLORS, SOURCE_COLORS,
)


def create_hourly_pattern_chart(hourly: List[Dict]) -> go.Figure:
    """Create an area chart of hourly energy consumption."""
    hours = [d["hour"] for d in hourly]
    kwh = [d["kwh"] for d in hourly]
    colors = ["#f59e0b" if 8 <= h <= 20 else "#0ea5e9" for h in hours]

    fig = go.Figure(go.Bar(
        x=hours,
        y=kwh,
        marker=dict(color=colors, cornerradius=3),
        text=[f"{v:.1f}" for v in kwh],
        textposition="auto",
        textfont=dict(size=8, color="white"),
    ))

    fig.update_layout(
        title=dict(text="24-Hour Consumption Pattern", font=dict(size=14, color="#374151")),
        height=280,
        margin=dict(t=40, b=40, l=40, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Hour", showgrid=False, tickfont=dict(size=10, color="#9ca3af")),
        yaxis=dict(title="kWh", showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af")),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_category_breakdown_pie(category_breakdown: Dict[str, float]) -> go.Figure:
    """Create a pie chart of energy by appliance category."""
    labels = [k.replace("_", " ").title() for k in category_breakdown.keys()]
    values = list(category_breakdown.values())
    colors = list(APPLIANCE_COLORS.values())[:len(labels)]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker=dict(colors=colors, line=dict(width=2, color="white")),
        textinfo="percent+label",
        textfont=dict(size=11, color="#374151"),
    ))

    fig.update_layout(
        title=dict(text="Energy by Category", font=dict(size=14, color="#374151")),
        height=320,
        margin=dict(t=40, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5, font=dict(size=9)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_source_mix_chart(source_breakdown: Dict[str, float]) -> go.Figure:
    """Create a donut chart of energy sources."""
    labels = [k.title() for k in source_breakdown.keys()]
    values = list(source_breakdown.values())
    colors = list(SOURCE_COLORS.values())[:len(labels)]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors, line=dict(width=2, color="white")),
        textinfo="percent+label",
        textfont=dict(size=10, color="#374151"),
    ))

    fig.add_annotation(
        text=f"{sum(v for k, v in source_breakdown.items() if k in ['solar', 'wind', 'hydro']):.0f}%<br>Renewable",
        x=0.5, y=0.5, font=dict(size=14, color="#22c55e", family="Inter"),
        showarrow=False,
    )

    fig.update_layout(
        title=dict(text="Energy Source Mix", font=dict(size=14, color="#374151")),
        height=320,
        margin=dict(t=40, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5, font=dict(size=9)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_monthly_trend_chart(monthly: List[Dict]) -> go.Figure:
    """Create a combined bar and line chart of monthly trends."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    periods = [d["period"] for d in monthly]
    kwh = [d["kwh"] for d in monthly]
    cost = [d["cost"] for d in monthly]
    renewable = [d["renewable"] for d in monthly]

    fig.add_trace(go.Bar(
        x=periods, y=kwh,
        name="Total kWh",
        marker=dict(color="#6b7280", cornerradius=4),
        text=[f"{v:.0f}" for v in kwh],
        textposition="auto",
        textfont=dict(size=9, color="white"),
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        x=periods, y=renewable,
        name="Renewable kWh",
        marker=dict(color="#22c55e", cornerradius=4),
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=periods, y=cost,
        name="Cost ($)",
        mode="lines+markers",
        line=dict(color="#f59e0b", width=3),
        marker=dict(size=8),
    ), secondary_y=True)

    fig.update_layout(
        title=dict(text="Monthly Energy Trends", font=dict(size=14, color="#374151")),
        barmode="stack",
        height=320,
        margin=dict(t=40, b=40, l=50, r=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#9ca3af")),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af"), title="kWh"),
        yaxis2=dict(tickfont=dict(size=10, color="#9ca3af"), title="Cost ($)", gridcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_cost_comparison_gauge(current: float, target: float) -> go.Figure:
    """Create a gauge chart for cost vs target."""
    color = "#22c55e" if current <= target else "#f59e0b" if current <= target * 1.2 else "#ef4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current,
        delta={"reference": target, "suffix": " vs target"},
        number={"prefix": "$", "font": {"size": 36, "color": color}},
        gauge={
            "axis": {"range": [0, target * 1.5], "tickwidth": 1},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [
                {"range": [0, target * 0.8], "color": "#f0fdf4"},
                {"range": [target * 0.8, target], "color": "#fffbeb"},
                {"range": [target, target * 1.5], "color": "#fef2f2"},
            ],
            "threshold": {
                "line": {"color": "#111827", "width": 3},
                "thickness": 0.8,
                "value": target,
            },
        },
    ))

    fig.update_layout(
        height=250,
        margin=dict(t=40, b=10, l=30, r=30),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_category_bar_chart(category_breakdown: Dict[str, float]) -> go.Figure:
    """Create a horizontal bar chart of energy by category."""
    labels = [k.replace("_", " ").title() for k in category_breakdown.keys()]
    values = list(category_breakdown.values())
    colors = list(APPLIANCE_COLORS.values())[:len(labels)]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(color=colors, cornerradius=4),
        text=[f"{v:.1f} kWh" for v in values],
        textposition="auto",
        textfont=dict(size=10, color="white"),
    ))

    fig.update_layout(
        title=dict(text="Daily Energy by Category", font=dict(size=14, color="#374151")),
        height=350,
        margin=dict(t=40, b=20, l=120, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af"), title="kWh"),
        yaxis=dict(autorange="reversed", tickfont=dict(size=11, color="#374151")),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_peak_vs_offpeak_chart(bills: List) -> go.Figure:
    """Create a stacked bar chart of peak vs off-peak consumption."""
    periods = [b.month for b in bills]
    peak = [b.peak_kwh for b in bills]
    off_peak = [b.off_peak_kwh for b in bills]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=periods, y=peak,
        name="Peak",
        marker=dict(color="#f59e0b", cornerradius=4),
    ))

    fig.add_trace(go.Bar(
        x=periods, y=off_peak,
        name="Off-Peak",
        marker=dict(color="#0ea5e9", cornerradius=4),
    ))

    fig.update_layout(
        title=dict(text="Peak vs Off-Peak Consumption", font=dict(size=14, color="#374151")),
        barmode="stack",
        height=300,
        margin=dict(t=40, b=40, l=40, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#9ca3af")),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af"), title="kWh"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        font={"family": "Inter, sans-serif"},
    )
    return fig
