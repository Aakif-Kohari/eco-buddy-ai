import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

from src.core.database import get_assessments
from src.carbon.emissions import calculate_footprint
from src.environment.waste import calculate_waste_footprint, WASTE_CATEGORIES
from src.environment.water import calculate_water_footprint
from styles.theme import apply_theme

apply_theme()

st.title("🌱 Carbon Footprint What-If Scenario Simulator")
st.markdown("""
Explore how lifestyle changes impact your carbon footprint. 
Adjust the scenario controls below to see your projected emissions compared to your baseline.
""")

user_id = st.session_state.get('user_id', 1)

if "sim_reset" not in st.session_state:
    st.session_state.sim_reset = False
if "scenario_history" not in st.session_state:
    st.session_state.scenario_history = []
if "best_scenario" not in st.session_state:
    st.session_state.best_scenario = None

try:
    assessments = get_assessments(user_id)
except Exception:
    assessments = []

DEFAULT_BASELINE = {
    'transport': 'Car',
    'distance': 20.0,
    'electricity': 300.0,
    'diet': 'Meat-heavy',
    'flights': 2,
    'region': 'Global'
}

if assessments and len(assessments) > 0:
    latest = assessments[-1]
    baseline = {
        'transport': latest[2] if len(latest) > 2 else DEFAULT_BASELINE['transport'],
        'distance': float(latest[3]) if len(latest) > 3 else DEFAULT_BASELINE['distance'],
        'electricity': float(latest[4]) if len(latest) > 4 else DEFAULT_BASELINE['electricity'],
        'diet': latest[5] if len(latest) > 5 else DEFAULT_BASELINE['diet'],
        'flights': int(latest[6]) if len(latest) > 6 else DEFAULT_BASELINE['flights'],
        'region': st.session_state.get('region', 'Global')
    }
else:
    baseline = DEFAULT_BASELINE

try:
    baseline_total, baseline_contributors = calculate_footprint(
        transport=baseline['transport'],
        distance=baseline['distance'],
        electricity=baseline['electricity'],
        diet=baseline['diet'],
        flights=baseline['flights'],
        region=baseline['region']
    )
except Exception as e:
    st.error(f"Error calculating baseline: {e}")
    st.stop()

st.sidebar.header("🎯 Sustainability Goal")
reduction_goal_pct = st.sidebar.slider("Target CO₂ Reduction (%)", min_value=0, max_value=100, value=20, step=5)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset Scenarios"):
    st.session_state.sim_reset = True
    st.rerun()

if st.session_state.sim_reset:
    st.session_state.sim_reset = False

st.subheader("⚙️ Scenario Controls")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**🚗 Transportation**")
    transport_modes = ["Car", "Bus", "Train", "Bicycle", "Walking", "Electric Vehicle", "Carpool"]
    sim_transport = st.selectbox(
        "Primary Transport", 
        options=transport_modes, 
        index=transport_modes.index(baseline['transport']) if baseline['transport'] in transport_modes else 0,
        key="sim_transport"
    )
    sim_distance = st.slider(
        "Daily Distance (km)", 
        0.0, 100.0, float(baseline['distance']), 1.0,
        key="sim_distance"
    )
    sim_flights = st.number_input(
        "Annual Flights", 
        min_value=0, max_value=50, value=int(baseline['flights']),
        key="sim_flights"
    )

with col2:
    st.markdown("**⚡ Household Energy**")
    sim_electricity = st.slider(
        "Monthly Electricity (kWh)", 
        0.0, 2000.0, float(baseline['electricity']), 10.0,
        key="sim_electricity"
    )
    
    st.markdown("**🥗 Diet**")
    diet_options = ["Meat-heavy", "Average", "Pescatarian", "Vegetarian", "Vegan"]
    sim_diet = st.selectbox(
        "Dietary Lifestyle", 
        options=diet_options,
        index=diet_options.index(baseline['diet']) if baseline['diet'] in diet_options else 1,
        key="sim_diet"
    )

with col3:
    st.markdown("**♻️ Waste & Water (Estimates)**")
    waste_reduction = st.slider(
        "Waste Reduction (%)", 
        0, 100, 0, 5,
        help="Reduce your weekly waste generation.",
        key="sim_waste"
    )
    water_reduction = st.slider(
        "Water Usage Reduction (%)", 
        0, 100, 0, 5,
        help="Reduce daily water usage.",
        key="sim_water"
    )

# Input Validation
validation_warnings = []
if sim_distance > 80:
    validation_warnings.append("Your daily commute distance is quite high. Consider carpooling or remote work.")
if sim_electricity > 1500:
    validation_warnings.append("High electricity consumption detected. A home energy audit might be beneficial.")
if sim_flights > 10:
    validation_warnings.append("Frequent flying contributes significantly to src.carbon.emissions. Explore train travel or virtual meetings.")

if validation_warnings:
    for w in validation_warnings:
        st.warning(f"⚠️ {w}")

try:
    projected_total, projected_contributors = calculate_footprint(
        transport=sim_transport,
        distance=sim_distance,
        electricity=sim_electricity,
        diet=sim_diet,
        flights=sim_flights,
        region=baseline['region']
    )
except Exception as e:
    st.error(f"Error calculating projection: {e}")
    st.stop()

AVG_ANNUAL_WASTE_CO2 = 500.0
AVG_ANNUAL_WATER_CO2 = 300.0

projected_waste_co2 = AVG_ANNUAL_WASTE_CO2 * (1 - (waste_reduction / 100.0))
projected_water_co2 = AVG_ANNUAL_WATER_CO2 * (1 - (water_reduction / 100.0))

baseline_adjusted_total = baseline_total + AVG_ANNUAL_WASTE_CO2 + AVG_ANNUAL_WATER_CO2
projected_adjusted_total = projected_total + projected_waste_co2 + projected_water_co2

baseline_contributors["Waste"] = AVG_ANNUAL_WASTE_CO2
baseline_contributors["Water"] = AVG_ANNUAL_WATER_CO2
projected_contributors["Waste"] = projected_waste_co2
projected_contributors["Water"] = projected_water_co2

absolute_reduction = baseline_adjusted_total - projected_adjusted_total
percentage_reduction = (absolute_reduction / baseline_adjusted_total) * 100 if baseline_adjusted_total > 0 else 0

st.sidebar.markdown("---")
if st.sidebar.button("💾 Save Current Scenario"):
    scenario_data = {
        "name": f"Scenario {len(st.session_state.scenario_history) + 1}",
        "transport": sim_transport,
        "distance": sim_distance,
        "electricity": sim_electricity,
        "diet": sim_diet,
        "flights": sim_flights,
        "waste_reduction": waste_reduction,
        "water_reduction": water_reduction,
        "projected_total": projected_adjusted_total,
        "reduction_pct": percentage_reduction
    }
    st.session_state.scenario_history.append(scenario_data)
    
    if st.session_state.best_scenario is None or projected_adjusted_total < st.session_state.best_scenario["projected_total"]:
        st.session_state.best_scenario = scenario_data
    
    st.sidebar.success(f"Saved {scenario_data['name']}!")

st.markdown("---")
st.subheader("📊 What-If Scenario Comparison")

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
with metric_col1:
    st.metric("Baseline Footprint", f"{baseline_adjusted_total:,.0f} kg CO₂")
with metric_col2:
    st.metric("Projected Footprint", f"{projected_adjusted_total:,.0f} kg CO₂", delta=f"{-absolute_reduction:,.0f} kg CO₂" if absolute_reduction > 0 else None, delta_color="inverse")
with metric_col3:
    st.metric("CO₂ Reduction", f"{absolute_reduction:,.0f} kg CO₂")
with metric_col4:
    st.metric("Reduction %", f"{percentage_reduction:.1f}%")

# Sustainability Impact Score
impact_score = max(0, min(100, int((percentage_reduction / max(1, reduction_goal_pct)) * 100)))
if impact_score >= 100:
    st.success(f"🏆 Outstanding! Sustainability Impact Score: **{impact_score}/100**")
elif impact_score >= 50:
    st.info(f"🌟 Great progress! Sustainability Impact Score: **{impact_score}/100**")
else:
    st.warning(f"🌱 Keep going! Sustainability Impact Score: **{impact_score}/100**")

st.markdown(f"**Goal Progress: {percentage_reduction:.1f}% / {reduction_goal_pct}% Reduction**")
progress_val = min(percentage_reduction / reduction_goal_pct if reduction_goal_pct > 0 else 0, 1.0)
st.progress(max(0.0, float(progress_val)))

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    df_comparison = pd.DataFrame({
        "Category": list(baseline_contributors.keys()) + list(projected_contributors.keys()),
        "Emissions (kg CO₂)": list(baseline_contributors.values()) + list(projected_contributors.values()),
        "Scenario": ["Baseline"] * len(baseline_contributors) + ["Projected"] * len(projected_contributors)
    })
    
    fig_bar = px.bar(
        df_comparison, 
        x="Category", 
        y="Emissions (kg CO₂)", 
        color="Scenario",
        barmode="group",
        title="Baseline vs. Projected Emissions"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with chart_col2:
    df_projected = pd.DataFrame({
        "Category": list(projected_contributors.keys()),
        "Emissions (kg CO₂)": list(projected_contributors.values())
    })
    fig_pie = px.pie(
        df_projected,
        names="Category",
        values="Emissions (kg CO₂)",
        title="Projected Footprint Breakdown",
        hole=0.4
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("### 💡 Recommendations")
improvements = {}
for cat in baseline_contributors.keys():
    diff = baseline_contributors[cat] - projected_contributors[cat]
    if diff > 0:
        improvements[cat] = diff

if improvements:
    best_cat = max(improvements, key=improvements.get)
    saved = improvements[best_cat]
    st.info(f"**Top Impact Area:** Your changes in **{best_cat}** provided the largest reduction, saving **{saved:,.0f} kg CO₂**!")
else:
    st.info("Try adjusting the controls to see how lifestyle changes can reduce your src.carbon.emissions.")

if st.session_state.scenario_history:
    st.markdown("---")
    st.subheader("📜 Scenario History & Best Simulation")
    
    if st.session_state.best_scenario:
        st.success(f"**Best Scenario So Far:** {st.session_state.best_scenario['name']} "
                   f"({st.session_state.best_scenario['reduction_pct']:.1f}% reduction, "
                   f"{st.session_state.best_scenario['projected_total']:,.0f} kg CO₂ total)")
    
    history_df = pd.DataFrame(st.session_state.scenario_history)
    st.dataframe(history_df[["name", "transport", "distance", "electricity", "diet", "flights", "projected_total", "reduction_pct"]], use_container_width=True)
    
    export_json = json.dumps(st.session_state.scenario_history, indent=2)
    st.download_button(
        label="📥 Download Scenario History (JSON)",
        data=export_json,
        file_name="scenario_history.json",
        mime="application/json"
    )
