import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
import tempfile
from datetime import datetime

from src.core.api_auth import get_current_user
from src.reporting.year_in_review_engine import (
    aggregate_annual_data,
    compute_yoy_trends,
    extract_milestones,
    compute_community_percentiles,
    generate_annual_pdf,
    generate_social_card
)

st.set_page_config(page_title="Year in Review", page_icon="🎉", layout="wide")

def render_year_in_review():
    st.title("🎉 Your Year in Review")
    st.markdown("Celebrate your sustainability milestones! View your annual progress, unlock your eco-story, and share your impact.")

    user = get_current_user()
    if not user:
        st.warning("Please log in to view your Year in Review.")
        return

    user_id = user["id"]
    today = datetime.today()
    
    # Select year (default to previous year if it's January, else current year)
    default_year = today.year - 1 if today.month == 1 else today.year
    selected_year = st.selectbox("Select Year", range(today.year - 5, today.year + 1), index=5 - (today.year - default_year))

    st.divider()

    with st.spinner(f"Generating your {selected_year} Eco-Story..."):
        report_data = aggregate_annual_data(user_id, selected_year)
        
        # We need data to show anything
        if report_data.get("assessments_count", 0) == 0:
            st.info(f"No assessments found for {selected_year}. Log some activities to generate a Year in Review!")
            return
            
        prev_data = aggregate_annual_data(user_id, selected_year - 1)
        
        trends = compute_yoy_trends(report_data, prev_data)
        report_data['trends'] = trends
        
        milestones = extract_milestones(user_id, selected_year, report_data)
        report_data['milestones'] = milestones
        
        percentiles = compute_community_percentiles(user_id, selected_year, report_data['total_footprint_kg'])
        report_data['percentile_data'] = percentiles

    # Hero Section - Milestones
    st.header(f"🌟 {selected_year} Highlights")
    
    m_cols = st.columns(len(milestones) if milestones else 1)
    if milestones:
        for i, (k, v) in enumerate(milestones.items()):
            with m_cols[i]:
                st.metric(label=k, value=v.split('(')[0].strip() if '(' in v else v, help=v)
    else:
        st.write("Keep logging to unlock milestones!")
        
    st.success(percentiles['narrative'])

    st.divider()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Overview & Trends", "Category Deep-Dive", "Export & Share"])

    with tab1:
        st.subheader("Year-over-Year Overview")
        colA, colB, colC = st.columns(3)
        
        footprint_trend = trends.get("footprint_trend", {})
        colA.metric(
            label="Total Footprint (kg CO2)",
            value=f"{report_data.get('total_footprint_kg', 0):.2f}",
            delta=f"{footprint_trend.get('change_pct', 0)}%" if footprint_trend.get('change_pct', 0) != 0 else None,
            delta_color="inverse"
        )
        
        score_trend = trends.get("eco_score_trend", {})
        colB.metric(
            label="Average Eco Score",
            value=f"{report_data.get('avg_eco_score', 0):.1f}",
            delta=f"{score_trend.get('change_pct', 0)}%" if score_trend.get('change_pct', 0) != 0 else None,
            delta_color="normal"
        )
        
        ass_trend = trends.get("assessments_trend", {})
        colC.metric(
            label="Assessments Logged",
            value=report_data.get("assessments_count", 0),
            delta=f"{ass_trend.get('absolute_diff', 0)}" if ass_trend.get('absolute_diff', 0) != 0 else None,
            delta_color="normal"
        )

        st.subheader("Monthly Progress")
        monthly = report_data.get("monthly_trends", [])
        if monthly:
            df_m = {
                "Month": [m["month_name"] for m in monthly],
                "Footprint": [m["total_footprint"] for m in monthly]
            }
            fig = px.bar(
                df_m, x="Month", y="Footprint", 
                title=f"Emissions throughout {selected_year}",
                color="Footprint", color_continuous_scale="Greens_r"
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Where did your emissions come from?")
        cats = report_data.get("category_breakdown", {})
        if sum(cats.values()) > 0:
            fig2 = px.pie(
                names=list(cats.keys()),
                values=list(cats.values()),
                title=f"Category Breakdown ({selected_year})",
                color_discrete_sequence=px.colors.sequential.Greens_r,
                hole=0.4
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            trees = report_data.get('total_footprint_kg', 0) / 21.77
            st.info(f"🌳 **Equivalence**: Your footprint this year is roughly equivalent to the CO2 absorbed by **{trees:.1f} mature trees**.")
        else:
            st.write("Not enough detailed data for category breakdown.")

    with tab3:
        st.subheader("Share Your Story")
        st.markdown("Download your full report or a social-ready card to share with friends and family.")
        
        col_pdf, col_img = st.columns(2)
        
        with col_pdf:
            if st.button("Generate Full PDF Report"):
                with st.spinner("Creating PDF..."):
                    fd, path = tempfile.mkstemp(suffix=".pdf")
                    os.close(fd)
                    pdf_path = generate_annual_pdf(report_data, path)
                    
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                        
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=f"EcoBuddy_YearInReview_{selected_year}.pdf",
                        mime="application/pdf"
                    )

        with col_img:
            if st.button("Generate Social Share Card"):
                with st.spinner("Creating Image..."):
                    fd, path = tempfile.mkstemp(suffix=".jpg")
                    os.close(fd)
                    img_path = generate_social_card(report_data, path)
                    
                    with open(img_path, "rb") as f:
                        img_bytes = f.read()
                        
                    st.image(img_bytes, caption=f"Your {selected_year} Eco-Story", width=400)
                    st.download_button(
                        label="⬇️ Download Image",
                        data=img_bytes,
                        file_name=f"EcoBuddy_SocialCard_{selected_year}.jpg",
                        mime="image/jpeg"
                    )

if __name__ == "__main__":
    render_year_in_review()
