"""
Budget Gauge Component for EcoBuddy AI
Renders budget status gauge in the sidebar.
"""

import streamlit as st
from typing import Optional

from src.lib.budget_manager import get_active_budget, get_budget_progress


def render_budget_gauge(user_id: Optional[int] = None):
    """
    Render budget gauge widget.
    
    Args:
        user_id: User ID
    """
    if not user_id:
        return
    
    active_budget = get_active_budget(user_id)
    
    if not active_budget:
        st.markdown("""
        <div style="background: rgba(15, 23, 42, 0.6); border-radius: 12px; padding: 16px; border: 1px solid rgba(74, 222, 128, 0.15); text-align: center;">
            <div style="font-size: 14px; color: #94a3b8;">No active budget</div>
            <div style="font-size: 12px; color: #64748b; margin-top: 4px;">Create one in the Carbon Budget tab</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    progress = get_budget_progress(active_budget.id)
    
    status_colors = {
        'on_track': '#4ade80',
        'warning': '#fbbf24',
        'exceeded': '#f97316',
        'critical': '#ef4444'
    }
    color = status_colors.get(progress['status'], '#4ade80')
    
    st.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.6); border-radius: 12px; padding: 16px; border: 1px solid rgba(74, 222, 128, 0.15);">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 600; color: #e5e7eb; font-size: 14px;">💰 Budget</span>
            <span style="font-size: 12px; color: #94a3b8;">{active_budget.period.value}</span>
        </div>
        <div style="margin-top: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 13px;">
                <span style="color: #94a3b8;">Used</span>
                <span style="color: #e5e7eb; font-weight: 600;">{active_budget.current_usage:.1f} kg</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px;">
                <span style="color: #94a3b8;">Remaining</span>
                <span style="color: #e5e7eb; font-weight: 600;">{progress['remaining']:.1f} kg</span>
            </div>
            <div style="width: 100%; height: 8px; background: rgba(74, 222, 128, 0.15); border-radius: 10px; overflow: hidden; margin-top: 4px;">
                <div style="width: {progress['usage_percentage']:.1f}%; height: 100%; background: {color}; border-radius: 10px;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="font-size: 11px; color: #64748b;">{progress['usage_percentage']:.0f}%</span>
                <span style="font-size: 11px; color: {color};">{progress['status'].replace('_', ' ').title()}</span>
            </div>
        </div>
        <div style="margin-top: 8px; font-size: 12px; color: #94a3b8; text-align: center;">
            <span>📅 {progress['days_remaining']} days left</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_budget_quick_stats(user_id: Optional[int] = None):
    """
    Render quick budget stats.
    
    Args:
        user_id: User ID
    """
    if not user_id:
        return
    
    active_budget = get_active_budget(user_id)
    
    if not active_budget:
        return
    
    progress = get_budget_progress(active_budget.id)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Daily Budget",
            f"{progress['daily_target']:.1f} kg"
        )
    with col2:
        st.metric(
            "Remaining",
            f"{progress['remaining']:.1f} kg"
        )
    with col3:
        st.metric(
            "Status",
            progress['status'].replace('_', ' ').title()
        )