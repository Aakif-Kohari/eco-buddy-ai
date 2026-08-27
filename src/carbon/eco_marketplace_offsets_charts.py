"""
Plotly Visualizations for Verified Carbon Offsets Marketplace
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any


def build_offset_project_type_chart(projects: List[Any]) -> go.Figure:
    """Creates a donut chart displaying carbon offset project types in catalog."""
    if not projects:
        fig = go.Figure()
        fig.update_layout(title="No Projects Available")
        return fig

    data = [{"type": p.project_type.value, "available_tonnes": p.total_available_tonnes} for p in projects]
    df = pd.DataFrame(data)
    grouped = df.groupby("type")["available_tonnes"].sum().reset_index()

    fig = px.pie(
        grouped,
        names="type",
        values="available_tonnes",
        hole=0.4,
        title="🌿 Available Offset Credit Volume by Project Type (Tonnes)",
        color_discrete_sequence=px.colors.qualitative.Dark2,
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    return fig


def build_portfolio_spending_chart(transactions: List[Dict[str, Any]]) -> go.Figure:
    """Creates a bar chart displaying retired carbon offset history."""
    if not transactions:
        fig = go.Figure()
        fig.update_layout(title="No Transactions Recorded")
        return fig

    df = pd.DataFrame(transactions)

    fig = px.bar(
        df,
        x="purchased_at",
        y="tonnes",
        color="project_type",
        title="📜 Retired Carbon Offsets History (Tonnes CO₂)",
        labels={"tonnes": "Tonnes Retired", "purchased_at": "Transaction Date"},
        color_discrete_sequence=px.colors.qualitative.Prism,
    )
    fig.update_layout(margin=dict(t=40, b=40, l=20, r=20))
    return fig
