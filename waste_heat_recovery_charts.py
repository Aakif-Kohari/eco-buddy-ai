"""Plotly visualization charts for Waste Heat Recovery and Exergy Analysis.
"""

from typing import List, Dict
import plotly.graph_objects as go
from waste_heat_recovery_types import HeatPinchPoint


def create_pinch_point_chart(pinch_points: List[HeatPinchPoint]) -> go.Figure:
    fig = go.Figure()

    for p in pinch_points:
        is_hot = "Hot" in p.stream_name
        color = "#ef4444" if is_hot else "#3b82f6"

        fig.add_trace(
            go.Scatter(
                x=[0, p.heat_transferred_kw],
                y=[p.inlet_temp_c, p.outlet_temp_c],
                mode="lines+markers",
                name=p.stream_name,
                line=dict(color=color, width=3.5),
            )
        )

    fig.update_layout(
        title="Heat Exchanger T-Q (Temperature vs Heat Transferred) Pinch Diagram",
        xaxis=dict(title="Heat Transferred / Enthalpy Rate (kW)"),
        yaxis=dict(title="Stream Temperature (°C)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_cashflow_waterfall(cashflows: List[Dict[str, float]]) -> go.Figure:
    years = [f"Yr {c['year']}" for c in cashflows]
    cum_vals = [c["cumulative_usd"] for c in cashflows]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years,
            y=cum_vals,
            name="Cumulative Cashflow ($)",
            line=dict(color="#10b981", width=3),
            fill="tozeroy",
            fillcolor="rgba(16, 185, 129, 0.12)",
        )
    )

    fig.add_hline(y=0.0, line_dash="dash", line_color="black", annotation_text="Breakeven Horizon")

    fig.update_layout(
        title="10-Year Cumulative Project Cashflow & ROI Payback",
        xaxis=dict(title="Operating Year"),
        yaxis=dict(title="Cumulative Net Cashflow ($ USD)"),
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig
