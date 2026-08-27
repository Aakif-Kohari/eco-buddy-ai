import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from src.core.database import (
    get_assessments,
    get_appliances,
    get_water_assessments,
    get_waste_assessments,
    get_active_goal
)
from src.ai.recommendations import generate_recommendations
from src.carbon.emissions import calculate_footprint

st.set_page_config(page_title="Sustainability Dashboard", page_icon="📊", layout="wide")

st.title("📊 Personal Sustainability Dashboard")
st.write("Monitor your comprehensive environmental footprint across transportation, diet, home energy, water, and src.environment.waste. Compare your impact against your historical records and active reduction src.utils.goals.")

user_id = st.session_state.get('user_id', 1)

# Fetch Data from various modules
assessments = get_assessments(user_id)
water_assessments = get_water_assessments(user_id)
waste_assessments = get_waste_assessments(user_id)
appliances = get_appliances(user_id)
active_goal = get_active_goal(user_id)

# ---------------------------------------------------------
# DATA PREPARATION
# ---------------------------------------------------------

# Convert to DataFrames and harmonize dates
df_assessments = pd.DataFrame(assessments, columns=[
    'id', 'date', 'created_at', 'transport', 'distance', 'electricity', 
    'diet', 'flights', 'footprint', 'eco_score'
]) if assessments else pd.DataFrame()

df_water = pd.DataFrame(water_assessments) if water_assessments else pd.DataFrame()
df_waste = pd.DataFrame(waste_assessments) if waste_assessments else pd.DataFrame()
df_appliances = pd.DataFrame(appliances) if appliances else pd.DataFrame()

for df, date_col in [(df_assessments, 'created_at'), (df_water, 'created_at'), (df_waste, 'created_at'), (df_appliances, 'created_at')]:
    if not df.empty and date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col]).dt.tz_localize(None)

# ---------------------------------------------------------
# 1. DATE-RANGE SELECTOR
# ---------------------------------------------------------
st.header("📅 Select Time Period")
col_date1, col_date2 = st.columns(2)

# Determine sensible date bounds based on available data
all_dates = pd.Series(dtype='datetime64[ns]')
for df in [df_assessments, df_water, df_waste, df_appliances]:
    if not df.empty and 'created_at' in df.columns:
        all_dates = pd.concat([all_dates, df['created_at']])

if not all_dates.empty:
    min_date = all_dates.min().date()
    max_date = all_dates.max().date()
else:
    min_date = datetime.now().date() - timedelta(days=30)
    max_date = datetime.now().date()

start_date = col_date1.date_input("Start Date", min_date)
end_date = col_date2.date_input("End Date", max_date)

def filter_by_date(df, col='created_at'):
    if df.empty or col not in df.columns:
        return df
    mask = (df[col].dt.date >= start_date) & (df[col].dt.date <= end_date)
    return df.loc[mask]

# For KPI comparison, calculate for the previous period of the same length
delta_days = max(1, (end_date - start_date).days)
prev_end = start_date - timedelta(days=1)
prev_start = prev_end - timedelta(days=delta_days)

def filter_prev_period(df, col='created_at'):
    if df.empty or col not in df.columns:
        return df
    mask = (df[col].dt.date >= prev_start) & (df[col].dt.date <= prev_end)
    return df.loc[mask]

curr_assessments = filter_by_date(df_assessments)
prev_assessments = filter_prev_period(df_assessments)

curr_water = filter_by_date(df_water)
prev_water = filter_prev_period(df_water)

curr_waste = filter_by_date(df_waste)
prev_waste = filter_prev_period(df_waste)

curr_appliances = filter_by_date(df_appliances)

# Calculate high level metrics
total_carbon = curr_assessments['footprint'].sum() if not curr_assessments.empty else 0
prev_carbon = prev_assessments['footprint'].sum() if not prev_assessments.empty else 0
carbon_delta = total_carbon - prev_carbon
carbon_delta_pct = (carbon_delta / prev_carbon * 100) if prev_carbon else 0

avg_eco_score = curr_assessments['eco_score'].mean() if not curr_assessments.empty else 0
prev_eco_score = prev_assessments['eco_score'].mean() if not prev_assessments.empty else 0
eco_delta = avg_eco_score - prev_eco_score

total_water_l = curr_water['total_liters'].sum() if not curr_water.empty else 0
total_waste_co2 = curr_waste['annual_co2'].sum() if not curr_waste.empty else 0

# ---------------------------------------------------------
# 2. KPI CARDS
# ---------------------------------------------------------
st.header("Overall Environmental Impact")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Avg Eco Score", f"{avg_eco_score:.1f}/100", f"{eco_delta:.1f} pts vs prev", delta_color="normal")
col2.metric("Total Carbon", f"{total_carbon:.2f} kg CO2", f"{carbon_delta_pct:.1f}% ({carbon_delta:.1f} kg)", delta_color="inverse")
col3.metric("Water Usage", f"{total_water_l:.1f} L")
col4.metric("Waste CO2", f"{total_waste_co2:.1f} kg")

st.divider()

# ---------------------------------------------------------
# 5. GOAL PROGRESS SECTION
# ---------------------------------------------------------
st.subheader("🎯 Goal Progress")
if active_goal:
    target_kg = float(active_goal.get('target_kg', 0))
    baseline_kg = float(active_goal.get('baseline_kg', 0))
    
    col_g1, col_g2, col_g3 = st.columns(3)
    col_g1.metric("Target Reduction", f"{target_kg:.1f} kg CO2", help="The goal you have set to achieve.")
    col_g2.metric("Current Footprint", f"{total_carbon:.1f} kg CO2", help="Your total footprint for the selected period.")
    
    # Calculate percentage complete for reduction goals
    if baseline_kg > target_kg:
        pct_complete = min(100.0, max(0.0, (baseline_kg - total_carbon) / (baseline_kg - target_kg) * 100))
        remaining = max(0.0, total_carbon - target_kg)
    else:
        pct_complete = 0.0
        remaining = 0.0
        
    col_g3.metric("Remaining to Target", f"{remaining:.1f} kg CO2")
    
    st.progress(pct_complete / 100.0)
    st.write(f"**Deadline:** {active_goal.get('target_date', 'N/A')} &nbsp; | &nbsp; **Completion:** {pct_complete:.1f}%")
else:
    st.info("No active reduction goal set. Navigate to the Goals page to set up a personalized reduction plan!")

st.divider()

# ---------------------------------------------------------
# 3. SCORE BREAKDOWN & 7. TOP IMPROVEMENT OPPORTUNITIES
# ---------------------------------------------------------
col_t1, col_t2 = st.columns(2)
with col_t1:
    st.subheader("Footprint Composition")
    if not curr_assessments.empty:
        latest = curr_assessments.iloc[-1]
        _, contribs = calculate_footprint(
            latest['transport'], latest['distance'], latest['electricity'], 
            latest['diet'], latest['flights']
        )
        contribs['Waste'] = total_waste_co2
        
        fig_comp = px.pie(
            names=list(contribs.keys()), 
            values=list(contribs.values()),
            hole=0.4,
            title="Emissions Breakdown by Category (kg CO2)",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_comp.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("Log an assessment in the selected date range to see your footprint composition.")

with col_t2:
    st.subheader("Top Improvement Opportunities")
    if not curr_assessments.empty:
        sorted_contribs = sorted(contribs.items(), key=lambda x: x[1], reverse=True)
        top_category = sorted_contribs[0][0]
        st.warning(f"**Highest Impact Category:** {top_category} ({sorted_contribs[0][1]:.1f} kg CO2)")
        st.write("Focusing your efforts on this area will yield the most significant emission reductions.")
        
        # Use existing recommendation engine
        insight, recs = generate_recommendations(
            latest['transport'], latest['electricity'], latest['diet'], latest['flights'], 
            {k: v for k, v in contribs.items() if k != 'Waste'}
        )
        for r in recs[:3]: 
            st.success(r)
    else:
        st.info("Start logging your daily activities to receive AI-powered environmental insights.")

st.divider()

# ---------------------------------------------------------
# 6. WEEKLY/MONTHLY COMPARISON (TRENDS)
# ---------------------------------------------------------
st.subheader("Carbon Footprint Trend")
if not df_assessments.empty:
    trend_type = st.radio("Group By", ["Daily", "Weekly", "Monthly"], horizontal=True)
    if trend_type == "Daily":
        grp = df_assessments['created_at'].dt.date
    elif trend_type == "Weekly":
        grp = df_assessments['created_at'].dt.to_period('W').apply(lambda r: r.start_time.date())
    else:
        grp = df_assessments['created_at'].dt.to_period('M').apply(lambda r: r.start_time.date())
        
    trend_df = df_assessments.groupby(grp)['footprint'].sum().reset_index()
    fig_trend = px.bar(
        trend_df, x='created_at', y='footprint', 
        title=f"{trend_type} Carbon Footprint", 
        labels={"created_at": "Time Period", "footprint": "kg CO2"},
        color='footprint',
        color_continuous_scale="Greens"
    )
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("No assessment data available to generate trends.")

st.divider()

# ---------------------------------------------------------
# 4. CATEGORY COMPARISON CHARTS
# ---------------------------------------------------------
st.subheader("Category Deep Dive")
tab1, tab2, tab3, tab4 = st.tabs(["Transport", "Diet", "Energy", "Waste"])

with tab1:
    if not curr_assessments.empty:
        transport_df = curr_assessments.groupby('transport')['distance'].sum().reset_index()
        fig_trans = px.pie(transport_df, values='distance', names='transport', title="Transport Distance (km) by Mode")
        fig_trans.update_traces(hoverinfo='label+percent', textinfo='value')
        st.plotly_chart(fig_trans, use_container_width=True)
    else:
        st.info("No transport data logged in this period.")

with tab2:
    if not curr_assessments.empty:
        diet_df = curr_assessments.groupby('diet')['id'].count().reset_index()
        fig_diet = px.bar(diet_df, x='diet', y='id', title="Diet Type Frequency", labels={"id": "Number of Meals Logged", "diet": "Diet Category"})
        st.plotly_chart(fig_diet, use_container_width=True)
    else:
        st.info("No diet data logged in this period.")

with tab3:
    if not curr_appliances.empty and 'name' in curr_appliances.columns:
        fig_app = px.bar(curr_appliances, x='name', y='daily_kwh', title="Daily Appliance Energy (kWh)", color='daily_kwh', color_continuous_scale="Reds")
        st.plotly_chart(fig_app, use_container_width=True)
    else:
        st.info("No appliance data logged in this period.")

with tab4:
    if not curr_waste.empty:
        latest_waste = curr_waste.iloc[0]
        waste_data = {
            'Category': ['Food Scraps', 'Plastic', 'Paper', 'Glass', 'Metal'],
            'Amount (kg)': [
                latest_waste.get('food_scraps', 0),
                latest_waste.get('plastic_packaging', 0),
                latest_waste.get('paper_cardboard', 0),
                latest_waste.get('glass', 0),
                latest_waste.get('metal_cans', 0)
            ]
        }
        df_w = pd.DataFrame(waste_data)
        fig_waste = px.bar(df_w, x='Category', y='Amount (kg)', title="Latest Waste Composition", color='Amount (kg)', color_continuous_scale="Blues")
        st.plotly_chart(fig_waste, use_container_width=True)
    else:
        st.info("No waste assessment data logged in this period.")
