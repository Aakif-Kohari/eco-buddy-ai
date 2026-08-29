"""
Plotly Visualizations for Smart Pantry & Food Waste Analyzer
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List
from src.environment.eco_food_waste_pantry_types import PantryItem, FoodWasteSummary


def build_spoilage_risk_donut_chart(pantry_items: List[PantryItem]) -> go.Figure:
    """Creates a donut chart displaying pantry inventory breakdown by spoilage risk."""
    if not pantry_items:
        fig = go.Figure()
        fig.update_layout(title="No Pantry Items Tracked")
        return fig

    data = [{"risk": item.get_spoilage_risk(), "count": 1} for item in pantry_items]
    df = pd.DataFrame(data)
    grouped = df.groupby("risk").count().reset_index()

    fig = px.pie(
        grouped,
        names="risk",
        values="count",
        hole=0.4,
        title="⚠️ Pantry Inventory Spoilage Risk Profile",
        color_discrete_map={
            "EXPIRED": "#C62828",
            "HIGH_RISK": "#E65100",
            "MODERATE_RISK": "#F57F17",
            "LOW_RISK": "#2E7D32",
        },
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    return fig


def build_food_category_co2_chart(pantry_items: List[PantryItem]) -> go.Figure:
    """Creates a bar chart displaying total CO2 embedded per food category."""
    if not pantry_items:
        fig = go.Figure()
        fig.update_layout(title="No Data Available")
        return fig

    data = [
        {
            "category": item.category.value,
            "total_co2": item.co2_footprint_kg_per_unit * item.quantity,
        }
        for item in pantry_items
    ]
    df = pd.DataFrame(data)
    grouped = df.groupby("category")["total_co2"].sum().reset_index()

    fig = px.bar(
        grouped,
        x="category",
        y="total_co2",
        title="🌿 Embedded CO₂ Footprint by Food Category (kg)",
        labels={"total_co2": "Total CO₂ (kg)", "category": "Food Category"},
        color="total_co2",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(xaxis_tickangle=-30, margin=dict(t=40, b=40, l=20, r=20))
    return fig
