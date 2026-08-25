"""Plotly visualization charts for V2G Energy Orchestration.
"""

from typing import List
import plotly.graph_objects as go
from v2g_orchestrator_types import V2GHourlyDispatch


def create_v2g_dispatch_chart(schedule: List[V2GHourlyDispatch]) -> go.Figure:
    hours = [f"{d.hour:02d}:00" for d in schedule]
    charge_kw = [d.fleet_charging_kw for d in schedule]
    discharge_kw = [-d.fleet_discharging_kw for d in schedule]
    solar_kw = [d.solar_generation_kw for d in schedule]
    tariff = [d.tariff_price_usd_kwh for d in schedule]

    fig = go.Figure()

    # Solar generation
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=solar_kw,
            name="Rooftop Solar (kW)",
            line=dict(color="#eab308", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(234, 179, 8, 0.15)",
        )
    )

    # EV Fleet Charge (positive)
    fig.add_trace(
        go.Bar(
            x=hours,
            y=charge_kw,
            name="EV Charging (kW)",
            marker=dict(color="#3b82f6"),
        )
    )

    # EV Fleet Discharge to Grid (negative)
    fig.add_trace(
        go.Bar(
            x=hours,
            y=discharge_kw,
            name="V2G Grid Injection (kW)",
            marker=dict(color="#10b981"),
        )
    )

    # Tariff price line on secondary axis
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=tariff,
            name="TOU Tariff ($/kWh)",
            line=dict(color="#ef4444", width=2, dash="dot"),
            yaxis="y2",
        )
    )

    fig.update_layout(
        title="24-Hour V2G Bi-Directional Power Dispatch vs Electricity Tariff",
        barmode="relative",
        xaxis=dict(title="Hour of Day"),
        yaxis=dict(title="Power (kW)", side="left"),
        yaxis2=dict(
            title="Electricity Price ($/kWh)",
            side="right",
            overlaying="y",
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_fleet_soc_curve(schedule: List[V2GHourlyDispatch]) -> go.Figure:
    hours = [f"{d.hour:02d}:00" for d in schedule]
    soc_pct = [d.average_fleet_soc_pct for d in schedule]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=soc_pct,
            name="Average Fleet State of Charge (SoC %)",
            line=dict(color="#6366f1", width=3),
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.12)",
        )
    )

    fig.add_hrect(
        y0=20.0,
        y1=80.0,
        fillcolor="rgba(16, 185, 129, 0.08)",
        layer="below",
        line_width=0,
        annotation_text="Battery Longevity Sweet Spot (20-80%)",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title="Fleet Aggregate State-of-Charge (SoC %) Trajectory",
        xaxis=dict(title="Hour of Day"),
        yaxis=dict(title="State of Charge (%)", range=[0, 100]),
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig
