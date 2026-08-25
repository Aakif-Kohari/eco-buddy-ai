"""Plotly visualization charts for AI Workload Carbon Profiler.
"""

from typing import List
import plotly.graph_objects as go
from datacenter_carbon_types import AIWorkloadCarbonResult, OptimizationOpportunity


def create_scope_breakdown_waterfall(result: AIWorkloadCarbonResult) -> go.Figure:
    fig = go.Figure(
        go.Waterfall(
            name="Carbon Footprint",
            orientation="v",
            measure=["relative", "relative", "total"],
            x=["Scope 2 (Operational Grid)", "Scope 3 (Hardware Embodied)", "Total Job Footprint"],
            textposition="outside",
            text=[
                f"{result.operational_emissions_kg_co2:,.1f} kg",
                f"{result.embodied_hardware_emissions_kg_co2:,.1f} kg",
                f"{result.total_footprint_kg_co2:,.1f} kg",
            ],
            y=[
                result.operational_emissions_kg_co2,
                result.embodied_hardware_emissions_kg_co2,
                result.total_footprint_kg_co2,
            ],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#10b981"}},
            increasing={"marker": {"color": "#ef4444"}},
            totals={"marker": {"color": "#6366f1"}},
        )
    )

    fig.update_layout(
        title="AI Training Run Carbon Footprint Breakdown (kg CO₂e)",
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig


def create_regional_comparison_bar(alternatives: List[OptimizationOpportunity]) -> go.Figure:
    regions = [opt.target_region.value.split(" ")[0] for opt in alternatives]
    reductions = [opt.carbon_reduction_pct for opt in alternatives]
    savings_kg = [opt.avoided_emissions_kg for opt in alternatives]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=regions,
            y=reductions,
            name="Carbon Reduction (%)",
            marker=dict(color="#10b981"),
            text=[f"-{r:.1f}%" for r in reductions],
            textposition="auto",
        )
    )

    fig.update_layout(
        title="Decarbonization Potential by Cloud Region Relocation",
        xaxis=dict(title="Target Cloud Region"),
        yaxis=dict(title="Avoided Emissions (%)", range=[0, 100]),
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig
