import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from admin_analytics import get_admin_platform_stats
from styles.theme import apply_theme, render_theme_selector

user_id = st.session_state.get('user_id')
if not user_id:
    st.warning('Please log in from the main application page.')
    st.stop()

apply_theme()
render_theme_selector()

st.markdown("<div class='section-header'>📊 Admin Dashboard — Platform Statistics</div>", unsafe_allow_html=True)
st.markdown("Anonymized, aggregate insights into platform usage, carbon score benchmarks, and popular recommendations.")

# Fetch anonymized stats
stats = get_admin_platform_stats()

total_assessments = stats["total_assessments"]
average_eco_score = stats["average_eco_score"]
active_users = stats["active_users"]
popular_recs = stats["popular_recommendations"]

st.markdown("### 📈 Key Platform Metrics")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"""
        <div class='metric-card'>
            <div style='font-size:14px; font-weight:600; color:var(--muted);'>Total Assessments</div>
            <div style='font-size:32px; font-weight:800; color:var(--ink); margin-top:4px;'>{total_assessments:,}</div>
            <div style='font-size:12px; color:var(--muted); margin-top:4px;'>Platform-wide submissions</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div class='metric-card'>
            <div style='font-size:14px; font-weight:600; color:var(--muted);'>Average Eco Score</div>
            <div style='font-size:32px; font-weight:800; color:#4ade80; margin-top:4px;'>{average_eco_score:.1f} <span style='font-size:18px; color:var(--muted);'>/ 100</span></div>
            <div style='font-size:12px; color:var(--muted); margin-top:4px;'>Platform average score</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"""
        <div class='metric-card'>
            <div style='font-size:14px; font-weight:600; color:var(--muted);'>Active Users</div>
            <div style='font-size:32px; font-weight:800; color:var(--ink); margin-top:4px;'>{active_users:,}</div>
            <div style='font-size:12px; color:var(--muted); margin-top:4px;'>Derived from assessment activity</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

st.markdown("### 💡 Popular Recommendations")

if popular_recs:
    # Top popular recommendations for visualization
    top_recs = popular_recs[:10]
    df_recs = pd.DataFrame(top_recs, columns=["Recommendation", "Frequency"])
    
    # Sort for horizontal bar chart (highest frequency on top)
    df_chart = df_recs.sort_values(by="Frequency", ascending=True)

    theme_is_dark = st.session_state.get("theme", "dark") == "dark"
    text_color = "#ffffff" if theme_is_dark else "#080b0a"

    fig = px.bar(
        df_chart,
        x="Frequency",
        y="Recommendation",
        orientation="h",
        labels={"Frequency": "Frequency Count", "Recommendation": "Recommendation Tip"},
        title="Top Generated Recommendations Across Platform",
        color="Frequency",
        color_continuous_scale=["#16a34a", "#4ade80", "#86efac"]
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=text_color, family="Inter, sans-serif"),
        margin=dict(l=20, r=20, t=50, b=30),
        height=max(350, len(df_chart) * 40),
        xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)"),
        yaxis=dict(showgrid=False)
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 📋 Detailed Recommendation Rankings")
    st.dataframe(
        df_recs,
        column_config={
            "Recommendation": st.column_config.TextColumn("Recommendation Tip"),
            "Frequency": st.column_config.NumberColumn("Frequency Count", format="%d")
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No assessment recommendations available yet. Complete assessments to generate platform statistics!")
