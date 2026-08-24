"""Plotly visualization charts for Soil Organic Carbon (SOC) and Agroecology Dynamics.
"""

from typing import List
import plotly.graph_objects as go
from soil_carbon_types import AnnualSoilCarbonPoint


def create_soc_trajectory_chart(trajectory: List[AnnualSoilCarbonPoint]) -> go.Figure:
    years = [f"Yr {p.year}" for p in trajectory]
    soc_stocks = [p.soc_stock_tons_c_ha for p in trajectory]
    net_ghg = [p.net_ghg_balance_tons_co2e_ha for p in trajectory]

    fig = go.Figure()

    # SOC Stock line
    fig.add_trace(
        go.Scatter(
            x=years,
            y=soc_stocks,
            name="Soil Carbon Stock (Tons C/ha)",
            line=dict(color="#10b981", width=3.5),
            fill="tozeroy",
            fillcolor="rgba(16, 185, 129, 0.12)",
        )
    )

    # Net Annual GHG Balance Bar (secondary y-axis)
    fig.add_trace(
        go.Bar(
            x=years,
            y=net_ghg,
            name="Net Annual Sequestration (t CO₂e/ha/yr)",
            marker=dict(color="#3b82f6"),
            yaxis="y2",
        )
    )

    fig.update_layout(
        title="10-Year Soil Organic Carbon (SOC) Stock & Net Sequestration Trajectory",
        xaxis=dict(title="Timeline"),
        yaxis=dict(title="SOC Stock (Tons C / ha)", side="left"),
        yaxis2=dict(
            title="Annual Sequestration Rate (t CO₂e/ha)",
            side="right",
            overlaying="y",
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def create_cumulative_credits_chart(trajectory: List[AnnualSoilCarbonPoint]) -> go.Figure:
    years = [f"Yr {p.year}" for p in trajectory]
    credits_usd = [p.cumulative_carbon_credits_usd for p in trajectory]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years,
            y=credits_usd,
            name="Cumulative Verified Carbon Credits ($)",
            line=dict(color="#f59e0b", width=3),
            fill="tozeroy",
            fillcolor="rgba(245, 158, 11, 0.15)",
        )
    )

    fig.update_layout(
        title="Cumulative Carbon Offset Revenue Forecast (10-Year Horizon)",
        xaxis=dict(title="Year"),
        yaxis=dict(title="Revenue ($ USD)"),
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig
