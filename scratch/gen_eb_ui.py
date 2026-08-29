import os

base_dir = r"F:\ECSoC'26 Contributions\eco-buddy-ai"
page_file = os.path.join(base_dir, "pages", "25_Environmental_Benchmarking.py")

page_code = '''\
"""
Streamlit UI for Environmental Benchmarking & Comparison.
Provides category-wise comparison, historical trends, percentiles, and regional profiling.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from environmental_benchmarking.engine import BenchmarkEngine
from environmental_benchmarking.history import HistoryAnalyzer
from environmental_benchmarking.models import UserAssessment, ReferenceProfile, CategoryComparison

def create_radar_chart(comparisons: dict, profile_name: str) -> go.Figure:
    """Create a radar chart comparing user vs profile for all categories."""
    categories = []
    user_scores = []
    profile_scores = [] # Normalized profile average is always 50 in our normalized scale
    
    for cat, comp in comparisons.items():
        # Exclude overall footprint and eco score for the category breakdown
        if cat in ["footprint", "eco_score"]:
            continue
        categories.append(cat.capitalize())
        user_scores.append(comp.normalized_score)
        profile_scores.append(50.0) # 50 is the mean on a 0-100 scale by definition
        
    categories.append(categories[0]) # close loop
    user_scores.append(user_scores[0])
    profile_scores.append(profile_scores[0])
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=user_scores,
        theta=categories,
        fill='toself',
        name='You',
        line_color='#2ca02c'
    ))
    fig.add_trace(go.Scatterpolar(
        r=profile_scores,
        theta=categories,
        fill='toself',
        name=profile_name,
        line_color='#1f77b4',
        opacity=0.6
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=True,
        title="Category Comparison (Normalized 0-100, Higher is Better)"
    )
    return fig

def create_bar_chart(comparisons: dict, profile_name: str) -> go.Figure:
    """Create a bar chart comparing absolute values."""
    categories = []
    user_vals = []
    profile_vals = []
    
    for cat, comp in comparisons.items():
        if cat in ["footprint", "eco_score"]:
            continue
        categories.append(cat.capitalize())
        user_vals.append(comp.user_value)
        profile_vals.append(comp.reference_mean)
        
    fig = go.Figure(data=[
        go.Bar(name='You', x=categories, y=user_vals, marker_color='#2ca02c'),
        go.Bar(name=profile_name, x=categories, y=profile_vals, marker_color='#1f77b4')
    ])
    fig.update_layout(
        barmode='group',
        title="Absolute Values vs Reference Mean (kg CO2e)",
        yaxis_title="kg CO2e"
    )
    return fig

def create_trend_chart(trend_data, profile_name: str) -> go.Figure:
    """Create a historical trend chart of percentiles."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend_data.dates,
        y=trend_data.percentiles,
        mode='lines+markers',
        name='Overall Percentile',
        line=dict(color='#ff7f0e', width=3)
    ))
    fig.update_layout(
        title=f"Historical Percentile vs {profile_name}",
        xaxis_title="Date",
        yaxis_title="Percentile (0-100)",
        yaxis=dict(range=[0, 100])
    )
    return fig

def render_page():
    st.set_page_config(page_title="Environmental Benchmarking", page_icon="📊", layout="wide")
    st.title("📊 Environmental Benchmarking & Comparison")
    st.markdown("""
    Compare your environmental footprint against various global, regional, and target profiles. 
    Discover your strengths, identify areas for improvement, and track your percentile ranking over time.
    """)
    
    engine = BenchmarkEngine()
    analyzer = HistoryAnalyzer()
    
    user_id = st.session_state.get('user_id', 1)
    history = analyzer.get_user_history(user_id)
    
    if not history:
        st.warning("No assessment history found. Please complete an environmental assessment first to view benchmarks.")
        return
        
    latest_assessment = history[0]
    
    # Sidebar Profile Selection
    st.sidebar.header("Benchmark Settings")
    profiles = engine.get_all_profiles()
    profile_options = {p.id: p.name for p in profiles}
    selected_profile_id = st.sidebar.selectbox(
        "Select Reference Profile",
        options=list(profile_options.keys()),
        format_func=lambda x: profile_options[x]
    )
    
    selected_profile = engine.get_profile(selected_profile_id)
    st.sidebar.info(f"**{selected_profile.name}**\\n\\n{selected_profile.description}")
    
    # Compute Comparison
    result = engine.compare_assessment(latest_assessment, selected_profile_id)
    
    # Overview Section
    st.header("Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Overall Percentile",
            value=f"{result.overall_percentile:.1f}%",
            delta=f"Top {100-result.overall_percentile:.1f}%" if result.overall_percentile > 50 else f"Bottom {result.overall_percentile:.1f}%",
            delta_color="normal"
        )
    with col2:
        fp_comp = result.categories['footprint']
        st.metric(
            label="Your Footprint (kg CO2e)",
            value=f"{fp_comp.user_value:,.0f}",
            delta=f"{fp_comp.difference_from_mean:+,.0f} vs Avg",
            delta_color="inverse"
        )
    with col3:
        es_comp = result.categories['eco_score']
        st.metric(
            label="Your Eco Score",
            value=f"{es_comp.user_value:.0f}",
            delta=f"{es_comp.difference_from_mean:+.0f} vs Avg",
            delta_color="normal"
        )
        
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Category Breakdown", "📈 Historical Trends", "💡 Action Plan", "🌍 Data Explorer"])
    
    with tab1:
        st.subheader("Category Comparison")
        st.markdown(f"How your specific activities compare against the **{selected_profile.name}**.")
        
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            radar = create_radar_chart(result.categories, selected_profile.name)
            st.plotly_chart(radar, use_container_width=True)
            
        with col_chart2:
            bar = create_bar_chart(result.categories, selected_profile.name)
            st.plotly_chart(bar, use_container_width=True)
            
        st.subheader("Detailed Metrics")
        metrics_data = []
        for cat, comp in result.categories.items():
            if cat in ["footprint", "eco_score"]:
                continue
            metrics_data.append({
                "Category": cat.capitalize(),
                "Your Value": f"{comp.user_value:,.1f}",
                "Profile Avg": f"{comp.reference_mean:,.1f}",
                "% Difference": f"{comp.percentage_difference:+.1f}%",
                "Percentile": f"{comp.percentile:.1f}",
                "Status": "✅ Better" if comp.is_better_than_average else "❌ Worse"
            })
        st.dataframe(pd.DataFrame(metrics_data), use_container_width=True)

    with tab2:
        st.subheader("Historical Trends")
        trends = analyzer.calculate_trends(user_id, selected_profile_id)
        if trends and len(trends.dates) > 1:
            st.markdown("Track how your percentile ranking has changed over time.")
            trend_fig = create_trend_chart(trends, selected_profile.name)
            st.plotly_chart(trend_fig, use_container_width=True)
        else:
            st.info("Complete more assessments over time to view your historical trends.")
            
    with tab3:
        st.subheader("Action Plan & Insights")
        
        st.markdown("### Personalized Insights")
        for insight in result.insights:
            st.info(f"💡 {insight}")
            
        col_str, col_wk = st.columns(2)
        with col_str:
            st.markdown("### Your Strengths 🌟")
            if result.strengths:
                for s in result.strengths:
                    st.success(f"**{s.capitalize()}**: You are performing significantly better than average.")
            else:
                st.write("No major strengths identified against this profile yet. Keep pushing!")
                
        with col_wk:
            st.markdown("### Areas for Improvement ⚠️")
            if result.weaknesses:
                for w in result.weaknesses:
                    st.warning(f"**{w.capitalize()}**: Your footprint here is higher than average.")
            else:
                st.write("No major weaknesses identified against this profile!")

    with tab4:
        st.subheader("Profile Data Explorer")
        st.markdown(f"Raw statistical distribution data for the **{selected_profile.name}**.")
        
        dist_data = []
        for cat in ["transport", "electricity", "diet", "flights", "footprint", "eco_score"]:
            stat = selected_profile.get_stat(cat)
            dist_data.append({
                "Category": cat.capitalize(),
                "Mean": stat.mean,
                "Median": stat.median,
                "Top 10% (p90)": stat.p90 if cat == "eco_score" else stat.p10,
                "Bottom 10% (p10)": stat.p10 if cat == "eco_score" else stat.p90,
            })
        st.dataframe(pd.DataFrame(dist_data), use_container_width=True)

if __name__ == "__main__":
    render_page()
'''

with open(page_file, 'w', encoding='utf-8') as f:
    f.write(page_code)
    
