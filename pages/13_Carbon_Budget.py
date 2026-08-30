"""
Carbon Budget Page for EcoBuddy AI
Displays carbon budget, goals, and forecasting.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Optional

from src.lib.budget_manager import (
    get_budget_manager,
    create_budget,
    get_user_budgets,
    get_active_budget,
    update_budget_usage,
    get_budget_progress,
    BudgetPeriod,
    BudgetStatus
)
from src.lib.goal_tracker import (
    get_goal_tracker,
    create_goal,
    get_user_goals,
    update_goal_progress,
    get_goal_recommendations,
    GoalType,
    GoalStatus
)
from src.lib.carbon_forecaster import (
    get_carbon_forecaster,
    forecast_carbon,
    forecast_goal
)


def render_carbon_budget(user_id: Optional[int] = None):
    """Render the carbon budget page."""
    
    if not user_id:
        st.warning("Please log in to access the carbon budget.")
        return
    
    st.markdown("""
    <style>
        .budget-card {
            background: rgba(15, 23, 42, 0.8);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(74, 222, 128, 0.2);
            margin-bottom: 16px;
        }
        .budget-card.on-track {
            border-color: #4ade80;
        }
        .budget-card.warning {
            border-color: #fbbf24;
        }
        .budget-card.exceeded {
            border-color: #f97316;
        }
        .budget-card.critical {
            border-color: #ef4444;
        }
        .budget-title {
            font-size: 20px;
            font-weight: 700;
            color: #e5e7eb;
        }
        .budget-amount {
            font-size: 32px;
            font-weight: 800;
            color: #4ade80;
        }
        .budget-status {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-on-track { background: rgba(74, 222, 128, 0.2); color: #4ade80; }
        .status-warning { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
        .status-exceeded { background: rgba(249, 115, 22, 0.2); color: #f97316; }
        .status-critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .goal-card {
            background: rgba(15, 23, 42, 0.6);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(74, 222, 128, 0.15);
            margin-bottom: 12px;
        }
        .goal-card.completed {
            border-color: #4ade80;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0f172a, #1a2e1a); padding: 30px 40px; border-radius: 20px; margin-bottom: 30px; border: 1px solid rgba(74, 222, 128, 0.2);">
        <h1 style="color: #4ade80; font-size: 36px; font-weight: 800; margin: 0;">💰 Carbon Budget & Goals</h1>
        <p style="color: #94a3b8; font-size: 16px; margin-top: 8px;">Set and track your carbon budget, goals, and forecast your progress.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Budget Overview",
        "🎯 Goals",
        "🔮 Forecast",
        "⚙️ Settings"
    ])
    
    with tab1:
        render_budget_overview(user_id)
    
    with tab2:
        render_goals(user_id)
    
    with tab3:
        render_forecast(user_id)
    
    with tab4:
        render_budget_settings(user_id)


def render_budget_overview(user_id: int):
    """Render budget overview."""
    st.markdown("### 📊 Current Budget")
    
    budget_manager = get_budget_manager()
    active_budget = get_active_budget(user_id)
    
    if active_budget:
        progress = get_budget_progress(active_budget.id)
        
        status_class = {
            'on_track': 'on-track',
            'warning': 'warning',
            'exceeded': 'exceeded',
            'critical': 'critical'
        }.get(progress['status'], 'on-track')
        
        st.markdown(f"""
        <div class="budget-card {status_class}">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <div class="budget-title">{active_budget.name}</div>
                    <div style="color: #94a3b8; font-size: 14px;">{active_budget.period.value.title()}</div>
                </div>
                <div>
                    <span class="budget-status status-{progress['status']}">{progress['status'].replace('_', ' ').title()}</span>
                </div>
            </div>
            <div style="margin-top: 16px;">
                <div style="display: flex; justify-content: space-between; font-size: 14px; color: #94a3b8;">
                    <span>Used: {active_budget.current_usage:.1f} kg CO₂</span>
                    <span>Remaining: {progress['remaining']:.1f} kg CO₂</span>
                    <span>Target: {active_budget.amount:.1f} kg CO₂</span>
                </div>
                <div style="width: 100%; height: 10px; background: rgba(74, 222, 128, 0.15); border-radius: 10px; overflow: hidden; margin-top: 8px;">
                    <div style="width: {progress['usage_percentage']:.1f}%; height: 100%; background: linear-gradient(90deg, {'#ef4444' if progress['status'] == 'critical' else '#f97316' if progress['status'] == 'exceeded' else '#fbbf24' if progress['status'] == 'warning' else '#4ade80'}, {'#22c55e' if progress['status'] not in ['critical', 'exceeded'] else '#ef4444'}); border-radius: 10px;"></div>
                </div>
            </div>
            <div style="display: flex; gap: 20px; margin-top: 12px; font-size: 13px; color: #94a3b8;">
                <span>📅 {progress['days_elapsed']} days elapsed</span>
                <span>⏰ {progress['days_remaining']} days remaining</span>
                <span>🎯 Daily target: {progress['daily_target']:.1f} kg</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add usage update
        with st.expander("📝 Update Usage"):
            col1, col2 = st.columns([2, 1])
            with col1:
                add_amount = st.number_input(
                    "Add CO₂ (kg)",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key="add_usage"
                )
            with col2:
                if st.button("Add to Budget", use_container_width=True):
                    if add_amount > 0:
                        if update_budget_usage(active_budget.id, add_amount):
                            st.success(f"✅ Added {add_amount:.1f} kg CO₂ to budget!")
                            st.rerun()
                        else:
                            st.error("Failed to update budget.")
    else:
        st.info("No active budget found. Create one in the Settings tab!")
        
        # Show budget creation form
        with st.expander("➕ Create Budget", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                budget_name = st.text_input("Budget Name", value="Monthly Carbon Budget")
                budget_amount = st.number_input("Budget Amount (kg CO₂)", min_value=1.0, value=100.0, step=10.0)
            with col2:
                budget_period = st.selectbox(
                    "Period",
                    options=[p.value for p in BudgetPeriod],
                    key="budget_period"
                )
                start_date = st.date_input("Start Date", value=datetime.now().date())
            
            if st.button("Create Budget", use_container_width=True):
                budget = create_budget(
                    user_id=user_id,
                    name=budget_name,
                    amount=budget_amount,
                    period=BudgetPeriod(budget_period),
                    start_date=datetime.combine(start_date, datetime.min.time())
                )
                st.success(f"✅ Budget '{budget_name}' created!")
                st.rerun()


def render_goals(user_id: int):
    """Render goals section."""
    st.markdown("### 🎯 Your Goals")
    
    goal_tracker = get_goal_tracker()
    goals = get_user_goals(user_id, active_only=False)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        active_goals = len([g for g in goals if g.status == GoalStatus.ACTIVE])
        st.metric("Active Goals", active_goals)
    with col2:
        completed_goals = len([g for g in goals if g.status == GoalStatus.COMPLETED])
        st.metric("Completed", completed_goals)
    with col3:
        completion_rate = (completed_goals / len(goals) * 100) if goals else 0
        st.metric("Completion Rate", f"{completion_rate:.1f}%")
    
    st.markdown("---")
    
    # Active goals
    active_goals = [g for g in goals if g.status == GoalStatus.ACTIVE]
    
    if active_goals:
        st.markdown("#### 🔥 Active Goals")
        for goal in active_goals:
            st.markdown(f"""
            <div class="goal-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 600; color: #e5e7eb;">{goal.title}</div>
                        <div style="color: #94a3b8; font-size: 13px;">{goal.description}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 14px; color: #94a3b8;">{goal.current_value:.1f} / {goal.target_value:.1f} {goal.unit}</div>
                        <div style="color: #4ade80; font-weight: 600;">{goal.progress:.1f}%</div>
                    </div>
                </div>
                <div style="width: 100%; height: 6px; background: rgba(74, 222, 128, 0.15); border-radius: 10px; overflow: hidden; margin-top: 8px;">
                    <div style="width: {goal.progress:.1f}%; height: 100%; background: linear-gradient(90deg, #4ade80, #22c55e); border-radius: 10px;"></div>
                </div>
                <div style="margin-top: 8px; display: flex; gap: 12px; font-size: 12px; color: #94a3b8;">
                    <span>📅 Target: {goal.target_date.strftime('%b %d, %Y') if goal.target_date else 'N/A'}</span>
                    <span>🏷️ {goal.type.value.title()}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Update goal progress
            with st.expander(f"Update Progress - {goal.title}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    new_value = st.number_input(
                        f"Current {goal.unit}",
                        min_value=0.0,
                        value=goal.current_value,
                        step=1.0,
                        key=f"goal_progress_{goal.id}"
                    )
                with col2:
                    if st.button("Update", key=f"update_goal_{goal.id}", use_container_width=True):
                        if update_goal_progress(goal.id, new_value):
                            st.success("✅ Progress updated!")
                            st.rerun()
                        else:
                            st.error("Failed to update progress.")
    else:
        st.info("No active goals. Create one below!")
    
    # Goal recommendations
    st.markdown("---")
    st.markdown("#### 💡 Recommended Goals")
    
    recommendations = get_goal_recommendations(user_id)
    
    if recommendations:
        for rec in recommendations:
            st.markdown(f"""
            <div style="background: rgba(74, 222, 128, 0.05); padding: 12px 16px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #4ade80;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 600; color: #e5e7eb;">{rec['title']}</div>
                        <div style="color: #94a3b8; font-size: 13px;">{rec['description']}</div>
                    </div>
                    <button onclick="window.location.href='?create_goal={rec['title']}'" style="background: rgba(74, 222, 128, 0.15); border: 1px solid rgba(74, 222, 128, 0.3); color: #4ade80; padding: 4px 16px; border-radius: 6px; cursor: pointer;">
                        Create
                    </button>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("Complete more assessments to get personalized goal recommendations!")
    
    # Create goal form
    with st.expander("➕ Create New Goal"):
        col1, col2 = st.columns(2)
        with col1:
            goal_title = st.text_input("Goal Title")
            goal_description = st.text_area("Description", max_chars=200)
            goal_type = st.selectbox(
                "Goal Type",
                options=[g.value for g in GoalType]
            )
        with col2:
            goal_target = st.number_input("Target Value", min_value=1.0, value=100.0, step=10.0)
            goal_unit = st.text_input("Unit", value="kg CO₂")
            target_date = st.date_input("Target Date", value=(datetime.now() + timedelta(days=30)).date())
        
        if st.button("Create Goal", use_container_width=True):
            if goal_title and goal_description:
                create_goal(
                    user_id=user_id,
                    title=goal_title,
                    description=goal_description,
                    type=GoalType(goal_type),
                    target_value=goal_target,
                    target_date=datetime.combine(target_date, datetime.min.time()),
                    unit=goal_unit
                )
                st.success(f"✅ Goal '{goal_title}' created!")
                st.rerun()
            else:
                st.error("Please fill in all fields.")


def render_forecast(user_id: int):
    """Render forecast section."""
    st.markdown("### 🔮 Carbon Forecast")
    
    from database import get_assessments
    
    assessments = get_assessments(user_id)
    
    if not assessments or len(assessments) < 3:
        st.info("Complete at least 3 assessments to enable forecasting!")
        return
    
    # Forecast controls
    col1, col2 = st.columns(2)
    with col1:
        forecast_days = st.slider(
            "Forecast Days",
            min_value=7,
            max_value=365,
            value=30,
            step=7
        )
    with col2:
        forecast_method = st.selectbox(
            "Method",
            options=["linear", "moving_average", "exponential"],
            index=0,
            help="Forecasting method to use"
        )
    
    # Generate forecast
    with st.spinner("Generating forecast..."):
        result = forecast_carbon(assessments, days=forecast_days, method=forecast_method)
    
    if result.success:
        # Historical data
        df = pd.DataFrame(assessments)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Forecast dates
        forecast_dates = [datetime.fromisoformat(d) for d in result.dates]
        
        # Create chart
        fig = go.Figure()
        
        # Historical data
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['footprint'],
            mode='lines+markers',
            name='Historical',
            line=dict(color='#4ade80', width=2),
            marker=dict(size=6, color='#4ade80')
        ))
        
        # Forecast
        fig.add_trace(go.Scatter(
            x=forecast_dates,
            y=result.predictions,
            mode='lines+markers',
            name='Forecast',
            line=dict(color='#fbbf24', width=2, dash='dash'),
            marker=dict(size=8, color='#fbbf24', symbol='diamond')
        ))
        
        # Confidence intervals
        if result.confidence_intervals:
            lower = [ci[0] for ci in result.confidence_intervals]
            upper = [ci[1] for ci in result.confidence_intervals]
            
            fig.add_trace(go.Scatter(
                x=forecast_dates + forecast_dates[::-1],
                y=upper + lower[::-1],
                fill='toself',
                fillcolor='rgba(251, 191, 36, 0.2)',
                line=dict(color='rgba(251, 191, 36, 0)'),
                name='Confidence Interval'
            ))
        
        fig.update_layout(
            height=400,
            template='plotly_dark',
            title='Carbon Footprint Forecast',
            xaxis_title='Date',
            yaxis_title='kg CO₂',
            hovermode='x unified',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Forecast metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Projected Total",
                f"{result.projected_total:.1f} kg"
            )
        with col2:
            st.metric(
                "Projected Average",
                f"{result.projected_average:.1f} kg"
            )
        with col3:
            trend_icon = "📉" if result.trend == "decreasing" else "📈" if result.trend == "increasing" else "➡️"
            st.metric(
                "Trend",
                f"{trend_icon} {result.trend.title()}"
            )
        with col4:
            st.metric(
                "Days Forecasted",
                result.days_forecasted
            )
        
        # Goal forecast
        st.markdown("---")
        st.markdown("#### 🎯 Goal Achievement Forecast")
        
        target = st.number_input(
            "Target CO₂ (kg)",
            min_value=0.0,
            value=500.0,
            step=50.0,
            key="forecast_target"
        )
        
        if st.button("Forecast Goal Achievement", use_container_width=True):
            goal_result = forecast_goal(assessments, target)
            
            if goal_result['success']:
                if goal_result.get('target_date'):
                    st.success(f"🎯 Target of {target} kg CO₂ projected to be reached on {goal_result['target_date']}")
                    st.info(f"📅 {goal_result['days_to_target']} days from now")
                else:
                    st.warning(goal_result.get('message', "Target not reached within forecast period"))
    else:
        st.error(f"Forecast failed: {result.message}")


def render_budget_settings(user_id: int):
    """Render budget settings."""
    st.markdown("### ⚙️ Budget Settings")
    
    budget_manager = get_budget_manager()
    budgets = get_user_budgets(user_id, active_only=False)
    
    if budgets:
        st.markdown("#### 📋 Your Budgets")
        
        for budget in budgets:
            status_icon = "🟢" if budget.is_active else "🔴"
            st.markdown(f"""
            <div style="background: rgba(15, 23, 42, 0.6); padding: 12px 16px; border-radius: 8px; margin-bottom: 8px; border: 1px solid {('rgba(74, 222, 128, 0.2)' if budget.is_active else 'rgba(239, 68, 68, 0.2)')};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-weight: 600; color: #e5e7eb;">{status_icon} {budget.name}</span>
                        <span style="color: #94a3b8; font-size: 13px; margin-left: 12px;">{budget.amount} kg {budget.period.value}</span>
                    </div>
                    <div style="font-size: 13px; color: #94a3b8;">
                        {budget.start_date.strftime('%b %d')} - {budget.end_date.strftime('%b %d, %Y')}
                        <span style="margin-left: 12px; color: {'#4ade80' if budget.is_active else '#ef4444'}">{'Active' if budget.is_active else 'Archived'}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No budgets created yet.")
    
    # Create new budget
    st.markdown("---")
    st.markdown("#### ➕ Create New Budget")
    
    col1, col2 = st.columns(2)
    with col1:
        budget_name = st.text_input("Budget Name", value="Monthly Carbon Budget")
        budget_amount = st.number_input("Budget Amount (kg CO₂)", min_value=1.0, value=100.0, step=10.0)
    with col2:
        budget_period = st.selectbox(
            "Period",
            options=[p.value for p in BudgetPeriod],
            key="settings_budget_period"
        )
        start_date = st.date_input("Start Date", value=datetime.now().date())
    
    warning_threshold = st.slider(
        "Warning Threshold",
        min_value=50,
        max_value=95,
        value=80,
        step=5,
        help="Alert when budget usage reaches this percentage"
    ) / 100
    
    if st.button("Create Budget", use_container_width=True, key="create_budget_settings"):
        budget = create_budget(
            user_id=user_id,
            name=budget_name,
            amount=budget_amount,
            period=BudgetPeriod(budget_period),
            start_date=datetime.combine(start_date, datetime.min.time()),
            warning_threshold=warning_threshold,
            critical_threshold=0.95
        )
        st.success(f"✅ Budget '{budget_name}' created!")
        st.rerun()


def main():
    """Main entry point."""
    user_id = st.session_state.get('user_id')
    render_carbon_budget(user_id)


if __name__ == "__main__":
    main()