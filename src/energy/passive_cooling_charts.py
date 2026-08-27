"""Plotly interactive visualization charts for Passive Cooling Simulation.
"""

from typing import List, Dict
import plotly.graph_objects as go
from src.energy.passive_cooling_types import HourlyComfortPoint, PassiveCoolingSimulationResult


def create_diurnal_thermal_chart(hourly_data: List[HourlyComfortPoint]) -> go.Figure:
    """Plots 24-hour temperature swing comparison with solar radiation."""
    hours = [f"{p.hour:02d}:00" for p in hourly_data]
    outdoor_t = [p.outdoor_temp_c for p in hourly_data]
    unconditioned_t = [p.indoor_temp_unconditioned_c for p in hourly_data]
    passive_t = [p.indoor_temp_passive_c for p in hourly_data]
    solar = [p.solar_radiation_w_m2 for p in hourly_data]

    fig = go.Figure()

    # Outdoor ambient
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=outdoor_t,
            name="Outdoor Ambient (°C)",
            line=dict(color="#f97316", width=2, dash="dot"),
        )
    )

    # Conventional Unconditioned
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=unconditioned_t,
            name="Unconditioned Standard (°C)",
            line=dict(color="#ef4444", width=3),
        )
    )

    # Passive Architecture
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=passive_t,
            name="Passive Optimized (°C)",
            line=dict(color="#10b981", width=3.5),
            fill="tonexty",
            fillcolor="rgba(16, 185, 129, 0.12)",
        )
    )

    # Solar Radiation bar on secondary y-axis
    fig.add_trace(
        go.Bar(
            x=hours,
            y=solar,
            name="Solar Insolation (W/m²)",
            marker=dict(color="rgba(234, 179, 8, 0.25)"),
            yaxis="y2",
        )
    )

    # Comfort zone band (20 - 26 C)
    fig.add_hrect(
        y0=20.0,
        y1=26.0,
        fillcolor="rgba(59, 130, 246, 0.08)",
        layer="below",
        line_width=0,
        annotation_text="ASHRAE Comfort Zone (20-26°C)",
        annotation_position="top left",
    )

    fig.update_layout(
        title="24-Hour Diurnal Temperature Profile & Passive Thermal Dampening",
        xaxis=dict(title="Hour of Day"),
        yaxis=dict(title="Temperature (°C)", side="left"),
        yaxis2=dict(
            title="Solar Radiation (W/m²)",
            side="right",
            overlaying="y",
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_pmv_ppd_comfort_chart(hourly_data: List[HourlyComfortPoint]) -> go.Figure:
    """Plots Predicted Percentage of Dissatisfied (PPD) across the day."""
    hours = [f"{p.hour:02d}:00" for p in hourly_data]
    ppd_vals = [p.predicted_percentage_dissatisfied_ppd for p in hourly_data]
    pmv_vals = [p.predicted_mean_vote_pmv for p in hourly_data]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=ppd_vals,
            name="PPD Dissatisfaction (%)",
            line=dict(color="#8b5cf6", width=3),
            fill="tozeroy",
            fillcolor="rgba(139, 92, 246, 0.15)",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=hours,
            y=pmv_vals,
            name="PMV Thermal Vote (-3 to +3)",
            line=dict(color="#06b6d4", width=2, dash="dash"),
            yaxis="y2",
        )
    )

    fig.update_layout(
        title="ISO 7730 Thermal Comfort Prediction (PMV & PPD)",
        xaxis=dict(title="Hour of Day"),
        yaxis=dict(title="PPD (%)", range=[0, 100]),
        yaxis2=dict(
            title="PMV Index",
            side="right",
            overlaying="y",
            range=[-3, 3],
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_cooling_strategy_breakdown_chart(breakdown: Dict[str, float]) -> go.Figure:
    """Renders donut chart of passive cooling energy contributions."""
    labels = list(breakdown.keys())
    values = list(breakdown.values())

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=["#10b981", "#3b82f6", "#f59e0b"]),
            )
        ]
    )
    fig.update_layout(
        title="Passive Energy Reduction Breakdown",
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig
