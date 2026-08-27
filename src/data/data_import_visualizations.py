"""Import Data Visualization Engine.

Generates interactive Plotly charts for the imported data analytics dashboard,
showing time-series trends and data quality breakdowns.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List

def create_import_category_pie(category_distribution: Dict[str, Any]) -> go.Figure:
    """Create a pie chart showing emissions by category from imported data."""
    if not category_distribution:
        return _empty_figure("No category data available.")
        
    df_data = []
    for cat, data in category_distribution.items():
        df_data.append({"Category": cat, "Emissions": data["emissions"]})
        
    df = pd.DataFrame(df_data)
    
    if df["Emissions"].sum() == 0:
        return _empty_figure("Total emissions are zero.")
        
    fig = px.pie(
        df, 
        values='Emissions', 
        names='Category', 
        hole=0.4, 
        color_discrete_sequence=px.colors.sequential.Teal_r,
        title="Imported Emissions by Category"
    )
    fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    return fig

def create_import_time_series(monthly_trends: Dict[str, float]) -> go.Figure:
    """Create a time series bar chart of imported emissions over time."""
    if not monthly_trends:
        return _empty_figure("No trend data available.")
        
    df = pd.DataFrame(list(monthly_trends.items()), columns=["Month", "Emissions"])
    df = df.sort_values("Month")
    
    fig = px.bar(
        df, 
        x="Month", 
        y="Emissions",
        title="Monthly Emissions Trend (Imported Data)",
        labels={"Emissions": "kg CO2e", "Month": "Month"},
        color_discrete_sequence=["#1f77b4"]
    )
    fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    return fig

def create_data_quality_donut(stats: Dict[str, int]) -> go.Figure:
    """Create a donut chart summarizing valid, invalid, and duplicate records."""
    total = stats.get("total", 0)
    if total == 0:
        return _empty_figure("No data uploaded.")
        
    labels = ["Valid", "Invalid", "Duplicates"]
    values = [stats.get("valid", 0), stats.get("invalid", 0), stats.get("duplicates", 0)]
    colors = ['#2ca02c', '#d62728', '#ff7f0e']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values, 
        hole=.5,
        marker=dict(colors=colors)
    )])
    fig.update_layout(
        title_text="Data Quality Breakdown",
        margin=dict(t=40, b=0, l=0, r=0)
    )
    return fig

def _empty_figure(text: str) -> go.Figure:
    """Helper to return an empty placeholder figure."""
    fig = go.Figure()
    fig.add_annotation(
        text=text,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="gray")
    )
    fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig
