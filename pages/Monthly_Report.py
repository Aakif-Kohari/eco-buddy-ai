import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import calendar
import os
import tempfile
import json
from datetime import datetime

from api_auth import get_current_user
from monthly_report_engine import (
    aggregate_monthly_data,
    compute_monthly_trends,
    generate_actionable_insights,
    generate_monthly_pdf
)
from database_connection import database_connection

st.set_page_config(page_title="Monthly Report", page_icon="📅", layout="wide")

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

def get_cached_report(user_id: int, month_year: str) -> dict:
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT report_data FROM monthly_reports WHERE user_id = ? AND month_year = ?", (user_id, month_year))
        row = cursor.fetchone()
        if row and row[0]:
            return json.loads(row[0])
    return None

def save_cached_report(user_id: int, month_year: str, report_data: dict, pdf_path: str = ""):
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO monthly_reports (user_id, month_year, report_data, pdf_path)
            VALUES (?, ?, ?, ?)
        """, (user_id, month_year, json.dumps(report_data), pdf_path))
        conn.commit()

def render_monthly_report():
    st.title("📅 Your Monthly Report")
    st.markdown("View comprehensive monthly summaries containing trend analysis, category breakdowns, and personalized actionable insights.")

    user = get_current_user()
    if not user:
        st.warning("Please log in to view your monthly report.")
        return

    user_id = user["id"]

    # Month/Year selection
    today = datetime.today()
    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        selected_month = st.selectbox("Month", range(1, 13), index=today.month - 1, format_func=lambda x: calendar.month_name[x])
    with col2:
        selected_year = st.selectbox("Year", range(today.year - 5, today.year + 1), index=5)

    month_year_str = f"{selected_year}-{selected_month:02d}"

    st.divider()

    # Try to fetch from DB first (if generated this session, or maybe past month)
    report_data = get_cached_report(user_id, month_year_str)
    
    if not report_data:
        with st.spinner("Aggregating monthly data..."):
            report_data = aggregate_monthly_data(user_id, selected_year, selected_month)
            report_data['insights'] = generate_actionable_insights(report_data)
            
            # calculate previous month
            prev_month = selected_month - 1
            prev_year = selected_year
            if prev_month == 0:
                prev_month = 12
                prev_year -= 1
                
            prev_data = aggregate_monthly_data(user_id, prev_year, prev_month)
            trends = compute_monthly_trends(report_data, prev_data)
            report_data['trends'] = trends
            
            # Save to cache (optional, could just generate dynamically)
            # save_cached_report(user_id, month_year_str, report_data)

    if report_data.get("assessments_count", 0) == 0:
        st.info("No assessments found for this month. Log some activities to see your report!")
        return

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Breakdown", "Trends", "Recommendations"])

    with tab1:
        st.subheader("Overview")
        colA, colB, colC = st.columns(3)
        trends = report_data.get("trends", {})
        
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

    with tab2:
        st.subheader("Category Breakdown")
        cats = report_data.get("category_breakdown", {})
        if sum(cats.values()) > 0:
            fig = px.pie(
                names=list(cats.keys()),
                values=list(cats.values()),
                title="Emissions by Category",
                color_discrete_sequence=px.colors.sequential.Greens_r
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Not enough detailed data for category breakdown.")

    with tab3:
        st.subheader("6-Month Historical Trends")
        # Generate last 6 months data dynamically for the chart
        with st.spinner("Loading historical trends..."):
            hist_months = []
            hist_footprints = []
            
            curr_y, curr_m = selected_year, selected_month
            for _ in range(6):
                hist_months.append(f"{calendar.month_abbr[curr_m]} {curr_y}")
                # simplified fetch for chart
                d = aggregate_monthly_data(user_id, curr_y, curr_m)
                hist_footprints.append(d.get("total_footprint_kg", 0))
                
                curr_m -= 1
                if curr_m == 0:
                    curr_m = 12
                    curr_y -= 1
            
            hist_months.reverse()
            hist_footprints.reverse()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist_months, y=hist_footprints, mode='lines+markers', name='Total Footprint', line=dict(color='green', width=3)))
            fig.update_layout(title="Carbon Footprint Trend", xaxis_title="Month", yaxis_title="Footprint (kg CO2)")
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.subheader("Actionable Insights")
        for idx, insight in enumerate(report_data.get("insights", [])):
            st.info(f"💡 {insight}")

    st.divider()
    
    # PDF Download
    st.subheader("Export Report")
    
    if st.button("Generate PDF Report"):
        with st.spinner("Generating PDF..."):
            fd, path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            
            pdf_path = generate_monthly_pdf(report_data, path)
            
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
                
            st.download_button(
                label="Download PDF",
                data=pdf_bytes,
                file_name=f"EcoBuddy_Monthly_Report_{month_year_str}.pdf",
                mime="application/pdf"
            )
            
            # optional: save_cached_report with pdf_path

if __name__ == "__main__":
    render_monthly_report()
