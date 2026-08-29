"""
Analytics Dashboard for EcoBuddy AI
Advanced analytics visualization with predictive insights and trend analysis.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import logging

from src.lib.analytics_engine import analyze_assessments, get_analysis_summary
from src.lib.predictive_model import generate_predictions, train_predictive_model
from src.lib.trend_analyzer import analyze_trends, get_trend_forecast
from src.lib.insight_generator import generate_insights, get_insight_generator

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Analytics Dashboard - EcoBuddy AI",
    page_icon="📊",
    layout="wide"
)


def render_analytics_dashboard():
    """Render the main analytics dashboard page."""
    
    st.markdown("""
    <style>
        .analytics-header {
            background: linear-gradient(135deg, #0f172a, #1a2e1a);
            padding: 30px 40px;
            border-radius: 20px;
            margin-bottom: 30px;
            border: 1px solid rgba(74, 222, 128, 0.2);
        }
        .analytics-header h1 {
            color: #4ade80;
            font-size: 36px;
            font-weight: 800;
        }
        .analytics-header p {
            color: #94a3b8;
            font-size: 16px;
        }
        .insight-card {
            background: rgba(15, 23, 42, 0.8);
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #4ade80;
            margin-bottom: 12px;
        }
        .insight-card.warning {
            border-left-color: #fbbf24;
        }
        .insight-card.high {
            border-left-color: #f87171;
        }
        .insight-card.achievement {
            border-left-color: #f472b6;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin: 20px 0;
        }
        .stat-card {
            background: rgba(15, 23, 42, 0.6);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid rgba(74, 222, 128, 0.15);
            text-align: center;
        }
        .stat-card .value {
            font-size: 28px;
            font-weight: 700;
            color: #4ade80;
        }
        .stat-card .label {
            font-size: 13px;
            color: #94a3b8;
            margin-top: 4px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="analytics-header">
        <h1>📊 Advanced Analytics Dashboard</h1>
        <p>AI-powered insights, predictive forecasting, and trend analysis for your sustainability journey</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get user ID from session
    user_id = st.session_state.get('user_id', None)
    
    if not user_id:
        st.warning("Please log in to access the analytics dashboard.")
        return
    
    # Get assessments
    from database import get_assessments
    assessments = get_assessments(user_id)
    
    if not assessments:
        st.info("""
        🚀 **Start Your Analytics Journey!**
        
        Complete at least 3 sustainability assessments to unlock:
        - 📈 Trend Analysis
        - 🔮 Predictive Forecasting
        - 💡 AI-Generated Insights
        - 📊 Advanced Visualizations
        """)
        return
    
    # Sidebar controls
    st.sidebar.markdown("### ⚙️ Analytics Controls")
    
    # Analysis mode
    analysis_mode = st.sidebar.selectbox(
        "Analysis Mode",
        ["Quick Overview", "Deep Analysis", "Forecast Focus", "Trend Focus"],
        help="Choose the analysis mode to focus on specific aspects"
    )
    
    # Horizon selector
    horizon_days = st.sidebar.slider(
        "Forecast Horizon (days)",
        min_value=7,
        max_value=365,
        value=30,
        step=7,
        help="How many days ahead to forecast"
    )
    
    # Auto-refresh
    auto_refresh = st.sidebar.checkbox(
        "Auto-refresh data",
        value=False,
        help="Automatically refresh analytics when new data is available"
    )
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Analytics", use_container_width=True):
        st.rerun()
    
    # Run analytics
    with st.spinner("Analyzing your data..."):
        # Analytics Engine
        analytics_result = analyze_assessments(assessments)
        
        if not analytics_result.success:
            st.error(f"Analysis failed: {analytics_result.message}")
            return
        
        analytics_data = analytics_result.data
        
        # Generate insights
        insight_result = generate_insights(assessments, analytics_data)
        
        # Train predictive model
        train_result = train_predictive_model(assessments)
        
        # Get trend analysis
        trend_result = analyze_trends(assessments)
    
    # Display stats
    st.markdown("### 📈 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Assessments",
            analytics_result.data_points_analyzed,
            help="Total number of assessments analyzed"
        )
    
    with col2:
        avg_footprint = analytics_data.get('descriptive_stats', {}).get('footprint', {}).get('mean', 0)
        st.metric(
            "Average Footprint",
            f"{avg_footprint:.1f} kg CO₂",
            help="Average carbon footprint across all assessments"
        )
    
    with col3:
        avg_score = analytics_data.get('descriptive_stats', {}).get('eco_score', {}).get('mean', 0)
        st.metric(
            "Average Eco Score",
            f"{avg_score:.1f}/100",
            help="Average Eco Score across all assessments"
        )
    
    with col4:
        trend = analytics_data.get('trend_analysis', {}).get('footprint_trend', {}).get('direction', 'stable')
        trend_icon = "📉" if trend == 'decreasing' else "📈" if trend == 'increasing' else "➡️"
        st.metric(
            "Current Trend",
            f"{trend_icon} {trend.title()}",
            help="Overall trend direction of your carbon footprint"
        )
    
    # Analysis mode specific content
    if analysis_mode == "Quick Overview":
        render_quick_overview(analytics_data, assessments, insight_result, horizon_days)
    
    elif analysis_mode == "Deep Analysis":
        render_deep_analysis(analytics_data, assessments, trend_result)
    
    elif analysis_mode == "Forecast Focus":
        render_forecast_focus(assessments, horizon_days, analytics_data)
    
    elif analysis_mode == "Trend Focus":
        render_trend_focus(analytics_data, trend_result, assessments)
    
    # Insights section (always visible)
    st.markdown("---")
    st.markdown("### 💡 AI-Powered Insights")
    
    if insight_result.success and insight_result.insights:
        for insight in insight_result.insights[:8]:  # Show top 8
            priority_class = "high" if insight.priority == "high" else "warning" if insight.priority == "medium" else ""
            type_class = "achievement" if insight.type == "achievement" else "warning" if insight.type == "warning" else ""
            
            st.markdown(f"""
            <div class="insight-card {priority_class} {type_class}">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <div style="font-weight: 600; font-size: 16px; color: #e5e7eb;">
                            {insight.title}
                        </div>
                        <div style="color: #94a3b8; font-size: 14px; margin-top: 4px;">
                            {insight.description}
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <span style="background: rgba(74, 222, 128, 0.2); padding: 2px 10px; border-radius: 10px; font-size: 11px; color: #4ade80;">
                            {insight.category}
                        </span>
                        <span style="background: rgba(148, 163, 184, 0.15); padding: 2px 10px; border-radius: 10px; font-size: 11px; color: #94a3b8;">
                            {insight.type}
                        </span>
                    </div>
                </div>
                {f'''
                <div style="margin-top: 8px; display: flex; gap: 12px;">
                    {''.join([f'<a href="#" style="color: #4ade80; text-decoration: none; font-size: 13px;">→ {link["label"]}</a>' for link in insight.action_links[:2]])}
                </div>
                ''' if insight.actionable else ''}
            </div>
            """, unsafe_allow_html=True)
        
        if len(insight_result.insights) > 8:
            st.caption(f"Showing 8 of {len(insight_result.insights)} insights. Complete more assessments to unlock more insights!")
    else:
        st.info("Complete more assessments to unlock AI-powered insights and recommendations.")


def render_quick_overview(analytics_data, assessments, insight_result, horizon_days):
    """Render quick overview mode."""
    
    st.markdown("### 📊 Quick Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Footprint trend chart
        st.markdown("#### Carbon Footprint Trend")
        
        df = pd.DataFrame(assessments)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['footprint'],
            mode='lines+markers',
            name='Footprint',
            line=dict(color='#4ade80', width=2),
            marker=dict(size=6, color='#4ade80')
        ))
        
        # Add trend line
        if len(df) > 3:
            x = np.arange(len(df))
            y = df['footprint'].values
            slope, intercept = np.polyfit(x, y, 1)
            trend_line = intercept + slope * x
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=trend_line,
                mode='lines',
                name='Trend',
                line=dict(color='#fbbf24', width=2, dash='dash')
            ))
        
        fig.update_layout(
            height=350,
            template='plotly_dark',
            xaxis_title='Date',
            yaxis_title='kg CO₂',
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Distribution of footprints
        st.markdown("#### Footprint Distribution")
        
        footprints = [a.get('footprint', 0) for a in assessments if a.get('footprint') is not None]
        
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=footprints,
            nbinsx=20,
            marker_color='#4ade80',
            opacity=0.7,
            name='Distribution'
        ))
        
        # Add mean line
        mean_fp = np.mean(footprints)
        fig.add_vline(
            x=mean_fp,
            line_dash="dash",
            line_color="#fbbf24",
            annotation_text=f"Mean: {mean_fp:.1f}",
            annotation_position="top"
        )
        
        fig.update_layout(
            height=350,
            template='plotly_dark',
            xaxis_title='kg CO₂',
            yaxis_title='Frequency',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Quick stats
    st.markdown("#### Quick Stats")
    
    stats_cols = st.columns(4)
    with stats_cols[0]:
        st.metric(
            "Best Footprint",
            f"{min(footprints):.1f} kg CO₂" if footprints else "N/A",
            help="Your lowest recorded footprint"
        )
    with stats_cols[1]:
        st.metric(
            "Worst Footprint",
            f"{max(footprints):.1f} kg CO₂" if footprints else "N/A",
            help="Your highest recorded footprint"
        )
    with stats_cols[2]:
        st.metric(
            "Assessments",
            len(assessments),
            help="Total number of assessments"
        )
    with stats_cols[3]:
        # Insight count
        st.metric(
            "Active Insights",
            len(insight_result.insights) if insight_result.success else 0,
            help="Number of active insights"
        )


def render_deep_analysis(analytics_data, assessments, trend_result):
    """Render deep analysis mode."""
    
    st.markdown("### 🔬 Deep Analysis")
    
    # Descriptive stats
    st.markdown("#### 📊 Descriptive Statistics")
    
    if 'descriptive_stats' in analytics_data:
        stats = analytics_data['descriptive_stats']
        
        cols = st.columns(4)
        for idx, (key, value) in enumerate(stats.items()):
            if idx < 4:
                with cols[idx]:
                    if isinstance(value, dict):
                        st.markdown(f"""
                        <div style="background: rgba(15, 23, 42, 0.6); padding: 15px; border-radius: 10px; border: 1px solid rgba(74, 222, 128, 0.15);">
                            <div style="font-weight: 600; color: #4ade80; font-size: 14px;">{key.title()}</div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                                Mean: {value.get('mean', 0):.1f}<br>
                                Std: {value.get('std', 0):.1f}<br>
                                Range: {value.get('range', 0):.1f}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
    
    # Correlation analysis
    st.markdown("#### 🔗 Correlation Analysis")
    
    if 'correlation_analysis' in analytics_data:
        corr_data = analytics_data['correlation_analysis']
        
        if corr_data.get('correlations'):
            df_corr = pd.DataFrame(corr_data['correlations'])
            
            fig = px.bar(
                df_corr,
                x='variable1',
                y='correlation',
                color='strength',
                title='Variable Correlations',
                template='plotly_dark'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No significant correlations found in your data.")
    
    # Change points
    if trend_result.success and trend_result.change_points:
        st.markdown("#### 🔄 Change Points Detected")
        
        for cp in trend_result.change_points[:5]:
            st.markdown(f"""
            <div style="background: rgba(15, 23, 42, 0.4); padding: 12px 16px; border-radius: 8px; border-left: 3px solid {'#f87171' if cp['direction'] == 'increasing' else '#4ade80'}; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #e5e7eb;">📅 {cp['date']}</span>
                    <span style="color: {'#f87171' if cp['direction'] == 'increasing' else '#4ade80'}">
                        {cp['direction'].title()} ({cp['impact']:.1f})
                    </span>
                </div>
                <div style="color: #94a3b8; font-size: 13px;">Value: {cp['value']:.1f} kg CO₂</div>
            </div>
            """, unsafe_allow_html=True)


def render_forecast_focus(assessments, horizon_days, analytics_data):
    """Render forecast focus mode."""
    
    st.markdown("### 🔮 Predictive Forecast")
    
    with st.spinner("Generating predictions..."):
        # Generate predictions
        prediction_result = generate_predictions(assessments, horizon_days)
    
    if not prediction_result.success:
        st.warning(prediction_result.message)
        return
    
    # Display forecast chart
    st.markdown(f"#### 📈 {horizon_days}-Day Forecast")
    
    # Historical data
    df = pd.DataFrame(assessments)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Create forecast dates
    last_date = df['date'].iloc[-1]
    forecast_dates = [last_date + timedelta(days=i+1) for i in range(horizon_days)]
    
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
    if prediction_result.predictions:
        fig.add_trace(go.Scatter(
            x=forecast_dates,
            y=prediction_result.predictions,
            mode='lines+markers',
            name='Forecast',
            line=dict(color='#fbbf24', width=2, dash='dash'),
            marker=dict(size=8, color='#fbbf24', symbol='diamond')
        ))
        
        # Confidence intervals
        if prediction_result.confidence_intervals:
            lower = [ci[0] for ci in prediction_result.confidence_intervals]
            upper = [ci[1] for ci in prediction_result.confidence_intervals]
            
            fig.add_trace(go.Scatter(
                x=forecast_dates + forecast_dates[::-1],
                y=upper + lower[::-1],
                fill='toself',
                fillcolor='rgba(251, 191, 36, 0.2)',
                line=dict(color='rgba(251, 191, 36, 0)'),
                name='Confidence Interval',
                showlegend=True
            ))
    
    fig.update_layout(
        height=400,
        template='plotly_dark',
        xaxis_title='Date',
        yaxis_title='kg CO₂',
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Forecast metrics
    if prediction_result.predictions:
        st.markdown("#### 📊 Forecast Metrics")
        
        cols = st.columns(4)
        
        with cols[0]:
            last_historical = df['footprint'].iloc[-1]
            last_forecast = prediction_result.predictions[-1]
            change = ((last_forecast - last_historical) / last_historical) * 100 if last_historical != 0 else 0
            
            st.metric(
                "Projected Change",
                f"{change:+.1f}%",
                help="Expected change over the forecast period"
            )
        
        with cols[1]:
            st.metric(
                "Final Forecast",
                f"{last_forecast:.1f} kg CO₂",
                help="Projected footprint at end of forecast period"
            )
        
        with cols[2]:
            trend = prediction_result.trend or "stable"
            trend_icon = "📉" if trend == "decreasing" else "📈" if trend == "increasing" else "➡️"
            st.metric(
                "Forecast Trend",
                f"{trend_icon} {trend.title()}",
                help="Predicted trend direction"
            )
        
        with cols[3]:
            st.metric(
                "Confidence",
                "±15%",
                help="Average confidence interval width"
            )


def render_trend_focus(analytics_data, trend_result, assessments):
    """Render trend focus mode."""
    
    st.markdown("### 📈 Trend Analysis")
    
    if trend_result.success:
        # Trend summary
        if trend_result.summary:
            summary = trend_result.summary
            
            cols = st.columns(4)
            with cols[0]:
                st.metric("Data Points", summary.get('data_points', 0))
            with cols[1]:
                st.metric("Change Points", summary.get('change_points_count', 0))
            with cols[2]:
                st.metric("Patterns Found", summary.get('patterns_count', 0))
            with cols[3]:
                if 'improvement' in summary:
                    improvement = summary['improvement']
                    st.metric(
                        "Overall Change",
                        f"{improvement.get('percentage', 0):+.1f}%",
                        help="Total improvement over all assessments"
                    )
        
        # Patterns
        if trend_result.patterns:
            st.markdown("#### 🧩 Detected Patterns")
            
            for pattern in trend_result.patterns:
                st.markdown(f"""
                <div style="background: rgba(15, 23, 42, 0.4); padding: 12px 16px; border-radius: 8px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #e5e7eb;">{pattern.get('description', 'Pattern')}</span>
                        <span style="color: #4ade80; font-size: 13px;">{pattern.get('type', '')}</span>
                    </div>
                    {f'<div style="color: #94a3b8; font-size: 13px;">💡 {pattern.get("suggestion", "")}</div>' if pattern.get('suggestion') else ''}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No significant patterns detected in your data yet.")
    
    # Seasonal patterns
    st.markdown("#### 📅 Seasonal Patterns")
    
    if 'seasonal_patterns' in analytics_data:
        seasonal = analytics_data['seasonal_patterns']
        
        if 'weekly_pattern' in seasonal:
            weekly = seasonal['weekly_pattern']
            
            df_weekly = pd.DataFrame({
                'Day': [f"Day {i}" for i in range(7)],
                'Footprint': [weekly.get(f'Day_{i}', 0) for i in range(7)]
            })
            
            fig = px.bar(
                df_weekly,
                x='Day',
                y='Footprint',
                title='Weekly Pattern',
                template='plotly_dark',
                color='Footprint',
                color_continuous_scale='Greens'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        if 'monthly_pattern' in seasonal:
            monthly = seasonal['monthly_pattern']
            
            df_monthly = pd.DataFrame({
                'Month': [f"Month {i}" for i in range(1, 13)],
                'Footprint': [monthly.get(str(i), 0) for i in range(1, 13)]
            })
            
            fig = px.line(
                df_monthly,
                x='Month',
                y='Footprint',
                title='Monthly Pattern',
                template='plotly_dark',
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)


def main():
    """Main entry point for the analytics dashboard page."""
    render_analytics_dashboard()


if __name__ == "__main__":
    main()