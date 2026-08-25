"""
Plotly Visualizations for Eco-Habit Streak Tracker
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any


def build_habit_streak_bar_chart(habits: List[Dict[str, Any]]) -> go.Figure:
    """Builds a horizontal bar chart displaying current vs longest streak by habit."""
    if not habits:
        fig = go.Figure()
        fig.update_layout(title="No Habits Found")
        return fig

    df = pd.DataFrame(habits)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["title"],
        x=df["current_streak"],
        name="Current Streak (Days)",
        orientation="h",
        marker_color="#FF9800",
    ))
    fig.add_trace(go.Bar(
        y=df["title"],
        x=df["longest_streak"],
        name="Longest Streak (Days)",
        orientation="h",
        marker_color="#4CAF50",
    ))

    fig.update_layout(
        title="🔥 Current Streak vs. Longest Personal Record",
        barmode="group",
        xaxis_title="Streak Duration (Days)",
        yaxis_title="",
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_habit_category_co2_chart(habits: List[Dict[str, Any]]) -> go.Figure:
    """Creates a pie chart showing potential CO2 impact distribution across habit categories."""
    if not habits:
        fig = go.Figure()
        fig.update_layout(title="No Data Available")
        return fig

    df = pd.DataFrame(habits)
    df["potential_co2"] = df["target_value"] * df["co2_saved_per_unit"]
    grouped = df.groupby("category")["potential_co2"].sum().reset_index()

    fig = px.pie(
        grouped,
        names="category",
        values="potential_co2",
        hole=0.4,
        title="🌱 Daily CO₂ Savings Potential by Category",
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    return fig
