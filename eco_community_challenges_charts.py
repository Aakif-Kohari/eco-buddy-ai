"""
Plotly Chart Visualizations for Eco-Community Challenges
Generates interactive charts for challenge participation, CO2 savings, and progress analytics.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any


def build_challenge_category_chart(challenges_list: List[Any]) -> go.Figure:
    """Creates a pie/donut chart showing the breakdown of active challenges by category."""
    if not challenges_list:
        fig = go.Figure()
        fig.update_layout(title="No Active Challenges Found")
        return fig

    data = [{"category": c.category.value, "co2_impact": c.co2_impact_kg} for c in challenges_list]
    df = pd.DataFrame(data)
    grouped = df.groupby("category").agg({"co2_impact": ["count", "sum"]}).reset_index()
    grouped.columns = ["Category", "Challenge Count", "Total CO2 Impact (kg)"]

    fig = px.pie(
        grouped,
        names="Category",
        values="Total CO2 Impact (kg)",
        hole=0.4,
        title="🌿 Potential CO₂ Reduction by Challenge Category",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>CO₂ Impact: %{value} kg")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    return fig


def build_user_progress_bar_chart(enrollments: List[Dict[str, Any]]) -> go.Figure:
    """Creates a horizontal bar chart displaying current progress percentage across enrolled challenges."""
    if not enrollments:
        fig = go.Figure()
        fig.update_layout(title="No Active Enrollments")
        return fig

    df = pd.DataFrame(enrollments)

    fig = px.bar(
        df,
        x="percentage",
        y="title",
        orientation="h",
        title="📊 Active Challenge Progress (%)",
        labels={"percentage": "Completion (%)", "title": "Challenge Title"},
        color="percentage",
        color_continuous_scale="Gregs",
        range_x=[0, 100],
    )
    fig.update_layout(
        showlegend=False,
        xaxis_title="Completion Percentage (%)",
        yaxis_title="",
        margin=dict(t=40, b=20, l=20, r=20),
    )
    return fig


def build_community_leaderboard_chart(leaderboard_data: List[tuple]) -> go.Figure:
    """Builds a bar chart showing top community eco-score & XP leaderboard performance."""
    if not leaderboard_data:
        fig = go.Figure()
        fig.update_layout(title="No Leaderboard Data Available")
        return fig

    df = pd.DataFrame(leaderboard_data[:10], columns=["User", "Eco Score", "Total XP", "Completed Challenges"])

    fig = px.bar(
        df,
        x="User",
        y="Total XP",
        color="Eco Score",
        title="🏆 Top 10 Community Eco Champions (XP & Eco Score)",
        labels={"Total XP": "Total XP", "User": "Community Member"},
        color_continuous_scale="Viridis",
    )
    fig.update_layout(xaxis_tickangle=-45, margin=dict(t=40, b=40, l=20, r=20))
    return fig
