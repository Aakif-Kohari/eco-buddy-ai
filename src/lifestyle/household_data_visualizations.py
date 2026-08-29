"""Household Sustainability Visualization Engine.

This module provides dedicated Plotly graph generators for visualizing
household data. It separates complex chart generation from Streamlit UI logic.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List

from src.lifestyle.household_metrics import get_household_analytics_summary
from src.lifestyle.household_budgeting import evaluate_budgets
from src.lifestyle.household_activities import VALID_CATEGORIES

def create_category_pie_chart(category_breakdown: Dict[str, float]) -> go.Figure:
    """Create a pie chart for household carbon footprint by category."""
    if sum(category_breakdown.values()) == 0:
        return _empty_figure("No category data available.")
        
    df = pd.DataFrame(list(category_breakdown.items()), columns=['Category', 'Footprint'])
    fig = px.pie(
        df, 
        values='Footprint', 
        names='Category', 
        hole=0.4, 
        color_discrete_sequence=px.colors.sequential.Greens_r,
        title="Footprint by Category"
    )
    fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    return fig


def create_member_contribution_stacked_bar(member_breakdown: Dict[str, Any]) -> go.Figure:
    """Create a stacked bar chart of individual vs. allocated shared footprints."""
    if member_breakdown.get("household_total", 0.0) == 0:
        return _empty_figure("No member contribution data available.")
        
    mem_data = member_breakdown["members"]
    mem_list = []
    
    for m_id, m_info in mem_data.items():
        mem_list.append({
            "Member": m_info["name"],
            "Individual (kg)": m_info["individual"],
            "Shared Allocated (kg)": m_info["allocated"]
        })
        
    df = pd.DataFrame(mem_list)
    fig = go.Figure(data=[
        go.Bar(name='Individual', x=df['Member'], y=df['Individual (kg)']),
        go.Bar(name='Shared Allocated', x=df['Member'], y=df['Shared Allocated (kg)'])
    ])
    
    fig.update_layout(
        barmode='stack', 
        colorway=['#2ca02c', '#98df8a'],
        title="Member Footprint Breakdown",
        xaxis_title="Household Member",
        yaxis_title="kg CO2e",
        margin=dict(t=40, b=0, l=0, r=0)
    )
    return fig


def create_budget_gauge_chart(budget_evaluation: Dict[str, Any]) -> go.Figure:
    """Create a gauge chart representing a single budget's consumption."""
    budget = budget_evaluation["budget"]
    spent = budget_evaluation["spent"]
    limit = budget["limit_value"]
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = spent,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"{budget['category']} Budget ({budget['period']})"},
        gauge = {
            'axis': {'range': [None, limit]},
            'bar': {'color': "darkgreen" if spent <= limit else "red"},
            'steps' : [
                {'range': [0, limit * 0.8], 'color': "lightgray"},
                {'range': [limit * 0.8, limit], 'color': "gray"}
            ],
            'threshold' : {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': limit
            }
        }
    ))
    
    fig.update_layout(margin=dict(t=50, b=20, l=20, r=20), height=300)
    return fig


def create_household_radar_chart(household_id: int) -> go.Figure:
    """Create a radar chart comparing household footprint across categories to benchmarks."""
    from household_metrics import BENCHMARKS
    from household import get_members
    
    # Get current footprint
    analytics = get_household_analytics_summary(household_id)
    cat_data = analytics["score_data"].get("category_breakdown", {})
    members_count = analytics["metrics"]["total_members"]
    
    if not cat_data:
        return _empty_figure("No radar data available.")
        
    categories = list(VALID_CATEGORIES)
    
    actuals = [cat_data.get(c, 0.0) for c in categories]
    targets = [(BENCHMARKS.get(c, 100.0) * members_count) for c in categories]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=targets,
        theta=categories,
        fill='toself',
        name='Recommended Benchmark',
        line_color='rgba(44, 160, 44, 0.5)',
        fillcolor='rgba(44, 160, 44, 0.2)'
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=actuals,
        theta=categories,
        fill='toself',
        name='Household Actual',
        line_color='rgba(214, 39, 40, 0.8)' if sum(actuals) > sum(targets) else 'rgba(31, 119, 180, 0.8)',
        fillcolor='rgba(214, 39, 40, 0.3)' if sum(actuals) > sum(targets) else 'rgba(31, 119, 180, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(max(actuals, default=0), max(targets, default=0)) * 1.1]
            )),
        showlegend=True,
        title="Benchmark Radar",
        margin=dict(t=50, b=20, l=20, r=20)
    )
    
    return fig


def create_goal_progress_bullet_chart(goals: List[Dict[str, Any]]) -> go.Figure:
    """Create a bullet chart for multiple active src.utils.goals."""
    if not goals:
        return _empty_figure("No active src.utils.goals.")
        
    fig = go.Figure()
    
    for i, g in enumerate(goals):
        if g['status'] == 'active':
            fig.add_trace(go.Indicator(
                mode = "number+gauge",
                value = g['current_value'],
                domain = {'x': [0.2, 1], 'y': [i/len(goals), (i+0.8)/len(goals)]},
                title = {'text' : g['title']},
                gauge = {
                    'shape': "bullet",
                    'axis': {'range': [None, g['target_value']]},
                    'threshold': {
                        'line': {'color': "black", 'width': 2},
                        'thickness': 0.75,
                        'value': g['target_value']
                    },
                    'bar': {'color': "#2ca02c"}
                }
            ))
            
    fig.update_layout(height=max(150, 100 * len(goals)), margin=dict(t=20, b=20, l=0, r=0))
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
