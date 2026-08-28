"""Plotly visualization charts for Industrial Symbiosis & Heat Cascade.
"""

from typing import Any
import plotly.graph_objects as go
from src.environment.industrial_symbiosis_types import HeatRecoveryResult


def create_energy_cascade_waterfall(result: HeatRecoveryResult) -> go.Figure:
    unrecovered_kw = max(0.0, result.thermal_power_available_kw - result.thermal_power_recovered_kw)
    fig = go.Figure(
        go.Waterfall(
            name="Thermal Cascade",
            orientation="v",
            measure=["absolute", "relative", "total"],
            x=["Gross Thermal Available", "Unrecovered Stack Loss", "Net Useful Energy"],
            textposition="outside",
            text=[
                f"{result.thermal_power_available_kw:,.0f} kW",
                f"-{unrecovered_kw:,.0f} kW",
                f"{result.thermal_power_recovered_kw:,.0f} kW",
            ],
            y=[
                result.thermal_power_available_kw,
                -unrecovered_kw,
                result.thermal_power_recovered_kw,
            ],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#ef4444"}},
            increasing={"marker": {"color": "#f59e0b"}},
            totals={"marker": {"color": "#10b981"}},
        )
    )

    fig.update_layout(
        title="Industrial Stream Energy Balance & Thermal Capture (kW)",
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig
