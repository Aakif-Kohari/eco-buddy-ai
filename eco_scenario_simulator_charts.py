"""
Plotly Visualizations for Eco-Footprint Scenario Simulator
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List
from eco_scenario_simulator_types import ScenarioProjectionPoint, ScenarioLever


def build_trajectory_forecast_chart(projections: List[ScenarioProjectionPoint]) -> go.Figure:
    """Builds a multi-year line chart comparing baseline vs simulated emissions trajectory."""
    if not projections:
        fig = go.Figure()
        fig.update_layout(title="No Projection Data")
        return fig

    df = pd.DataFrame([
        {
            "Year": p.year,
            "Baseline Footprint": p.baseline_co2_kg,
            "Simulated Trajectory": p.simulated_co2_kg,
            "Cumulative Savings": p.cumulative_savings_kg,
        }
        for p in projections
    ])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Year"],
        y=df["Baseline Footprint"],
        name="Baseline (Business As Usual)",
        line=dict(color="#E53935", width=3, dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=df["Year"],
        y=df["Simulated Trajectory"],
        name="Simulated Scenario Trajectory",
        line=dict(color="#4CAF50", width=4),
        fill="tonexty",
        fillcolor="rgba(76, 175, 80, 0.15)",
    ))

    fig.update_layout(
        title="📈 Multi-Year Decarbonization Trajectory (kg CO₂/year)",
        xaxis_title="Year",
        yaxis_title="Annual CO₂ Footprint (kg)",
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_lever_waterfall_chart(levers: List[ScenarioLever]) -> go.Figure:
    """Creates a waterfall chart breaking down CO2 reductions per lever."""
    if not levers:
        fig = go.Figure()
        fig.update_layout(title="No Levers Configured")
        return fig

    names = [l.name for l in levers]
    deltas = [l.calculate_co2_delta_kg() for l in levers]

    fig = go.Figure(go.Waterfall(
        name="CO2 Delta",
        orientation="v",
        measure=["relative"] * len(levers),
        x=names,
        text=[f"{d:+.1f} kg" for d in deltas],
        y=deltas,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "#4CAF50"}},
        increasing={"marker": {"color": "#E53935"}},
    ))

    fig.update_layout(
        title="📊 Carbon Reduction Impact by Lifestyle Lever (kg CO₂)",
        xaxis_tickangle=-30,
        margin=dict(t=40, b=40, l=20, r=20),
    )
    return fig
