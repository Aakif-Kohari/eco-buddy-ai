import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any, Tuple
from database import get_appliances
from energy_audit import calculate_appliance_energy
from styles.theme import apply_theme

# Constants
GRID_CARBON_INTENSITY_KG_KWH = 0.4  # kg CO2 per kWh
MONTHS_PER_YEAR = 12
DAYS_PER_YEAR = 365
AVG_DAILY_HOUSEHOLD_KWH = 28.0  # approximate global benchmark

def load_user_appliances(user_id: int) -> pd.DataFrame:
    """Load appliances from the database and calculate baseline metrics."""
    appliances = get_appliances(user_id)
    if not appliances:
        return pd.DataFrame()
        
    data = []
    for app in appliances:
        # DB fields: user_id, name, category, quantity, power_rating_watts, hours_used_per_day, standby_draw_watts
        total_daily_kwh, active_kwh, standby_kwh = calculate_appliance_energy(
            app['power_rating_watts'], 
            app['hours_used_per_day'], 
            app['standby_draw_watts'], 
            app['quantity']
        )
        
        # Default days_per_month is 30 for baseline
        days_per_month = 30
        monthly_kwh = total_daily_kwh * days_per_month
        
        data.append({
            "id": app['id'],
            "Name": app['name'],
            "Category": app['category'],
            "Quantity": app['quantity'],
            "Power (W)": app['power_rating_watts'],
            "Hours/Day": app['hours_used_per_day'],
            "Standby (W)": app['standby_draw_watts'],
            "Days/Month": days_per_month,
            "Daily kWh": total_daily_kwh,
            "Monthly kWh": monthly_kwh,
            "Monthly CO2 (kg)": monthly_kwh * GRID_CARBON_INTENSITY_KG_KWH
        })
        
    return pd.DataFrame(data)

def calculate_projected_energy(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate the projected energy after user modifications in what-if scenarios."""
    df = df.copy()
    
    daily_kwh_list = []
    monthly_kwh_list = []
    monthly_co2_list = []
    
    for idx, row in df.iterrows():
        total_daily_kwh, active_kwh, standby_kwh = calculate_appliance_energy(
            row['Power (W)'], 
            row['Hours/Day'], 
            row['Standby (W)'], 
            row['Quantity']
        )
        
        monthly_kwh = total_daily_kwh * row['Days/Month']
        
        daily_kwh_list.append(total_daily_kwh)
        monthly_kwh_list.append(monthly_kwh)
        monthly_co2_list.append(monthly_kwh * GRID_CARBON_INTENSITY_KG_KWH)
        
    df['Projected Daily kWh'] = daily_kwh_list
    df['Projected Monthly kWh'] = monthly_kwh_list
    df['Projected Monthly CO2 (kg)'] = monthly_co2_list
    return df

def generate_efficiency_score(daily_kwh: float) -> Tuple[int, str]:
    """Generate a score out of 100 based on household energy consumption."""
    if daily_kwh == 0:
        return 100, "Excellent"
        
    ratio = daily_kwh / AVG_DAILY_HOUSEHOLD_KWH
    
    if ratio <= 0.5:
        score = 100
        rating = "Outstanding 🌟"
    elif ratio <= 0.8:
        score = 90
        rating = "Excellent ⭐"
    elif ratio <= 1.0:
        score = 75
        rating = "Good 👍"
    elif ratio <= 1.5:
        score = 50
        rating = "Fair ⚠️"
    else:
        score = max(0, 100 - int(ratio * 30))
        rating = "Needs Improvement 🛑"
        
    return int(score), rating

def get_recommendations(df: pd.DataFrame) -> List[str]:
    """Generate dynamic recommendations based on appliance usage."""
    recommendations = []
    
    if df.empty:
        return ["Add appliances to your registry to get personalized recommendations."]
        
    # Sort by impact
    df_sorted = df.sort_values(by="Monthly kWh", ascending=False)
    top_hog = df_sorted.iloc[0]
    
    recommendations.append(f"🔴 **Highest Impact**: Your **{top_hog['Name']}** consumes the most energy ({top_hog['Monthly kWh']:.1f} kWh/month). Consider reducing its usage by even 10%.")
    
    # Check for high standby power
    high_standby = df[df["Standby (W)"] > 15]
    for _, row in high_standby.iterrows():
        recommendations.append(f"🔌 **Phantom Load**: **{row['Name']}** draws {row['Standby (W)']}W while off. Use a smart plug or unplug it when not in use.")
        
    # Check for heavy heating/cooling usage
    climate_hogs = df[(df["Category"].isin(["AC", "Heat Pump"])) & (df["Hours/Day"] > 8)]
    if not climate_hogs.empty:
        recommendations.append("🌡️ **Climate Control**: Your AC/Heating usage is quite high. Consider adjusting the thermostat by 1-2 degrees or improving home insulation to drastically cut costs.")
        
    # Lighting efficiency
    lighting = df[df["Category"] == "Lighting"]
    if not lighting.empty:
        total_lighting_watts = (lighting["Power (W)"] * lighting["Quantity"]).sum()
        if total_lighting_watts > 300:
            recommendations.append("💡 **Lighting**: Your total lighting wattage is high. Switching to LED bulbs can reduce lighting energy by up to 80%.")
            
    # Add general tips if too few
    if len(recommendations) < 3:
        recommendations.append("🕒 **Time of Use**: Shift heavy appliance usage (like washing machines) to off-peak hours if your utility offers time-of-use rates.")
        recommendations.append("🌬️ **Maintenance**: Regularly clean appliance filters (AC, dryers) to maintain their efficiency.")
        
    return recommendations

def render_home_energy_optimization_center():
    apply_theme()
    st.title("⚡ Home Energy Optimization Center")
    st.markdown("Analyze your household energy consumption, run what-if scenarios, and discover high-impact ways to reduce your footprint.")
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.warning("Please log in from the main application page to use this feature.")
        st.stop()
        
    # Load data
    df_baseline = load_user_appliances(user_id)
    
    if df_baseline.empty:
        st.info("No appliances found in your registry. Please add appliances via the **Home Energy Audit** page first.")
        st.stop()

    # Calculate global metrics
    total_daily_kwh = df_baseline['Daily kWh'].sum()
    total_monthly_kwh = df_baseline['Monthly kWh'].sum()
    total_monthly_co2 = df_baseline['Monthly CO2 (kg)'].sum()
    score, rating = generate_efficiency_score(total_daily_kwh)
    
    tab1, tab2, tab3 = st.tabs(["📊 Overview & Scoring", "🎛️ What-If Scenarios", "💡 AI Recommendations"])
    
    # -------------------------------------------------------------------------
    # TAB 1: OVERVIEW
    # -------------------------------------------------------------------------
    with tab1:
        st.subheader("Household Energy Profile")
        
        # Top Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Efficiency Score", f"{score}/100", rating, delta_color="off")
        c2.metric("Daily Energy", f"{total_daily_kwh:.1f} kWh")
        c3.metric("Monthly Energy", f"{total_monthly_kwh:.1f} kWh")
        c4.metric("Monthly Carbon", f"{total_monthly_co2:.1f} kg")
        
        st.markdown("---")
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("### Energy by Appliance")
            fig_pie = px.pie(
                df_baseline, 
                names='Name', 
                values='Monthly kWh',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie.update_layout(margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_chart2:
            st.markdown("### Top Energy Consumers")
            top_df = df_baseline.sort_values(by="Monthly kWh", ascending=False).head(5)
            fig_bar = px.bar(
                top_df, 
                x="Monthly kWh", 
                y="Name",
                orientation='h',
                color="Category",
                text_auto='.1f'
            )
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.markdown("### Current Appliance Inventory")
        st.dataframe(
            df_baseline[["Name", "Category", "Quantity", "Power (W)", "Hours/Day", "Monthly kWh", "Monthly CO2 (kg)"]].style.format({
                "Power (W)": "{:.0f}",
                "Hours/Day": "{:.1f}",
                "Monthly kWh": "{:.1f}",
                "Monthly CO2 (kg)": "{:.1f}"
            }),
            use_container_width=True
        )

    # -------------------------------------------------------------------------
    # TAB 2: WHAT-IF SCENARIOS
    # -------------------------------------------------------------------------
    with tab2:
        st.subheader("What-If Simulation")
        st.write("Adjust the sliders and inputs below to see how changes in behavior or appliance upgrades affect your footprint.")
        
        # Initialize session state for what-if
        if 'what_if_df' not in st.session_state:
            st.session_state.what_if_df = df_baseline.copy()
            
        if st.button("🔄 Reset Scenarios"):
            st.session_state.what_if_df = df_baseline.copy()
            st.rerun()
            
        st.markdown("#### Adjust Usage Parameters")
        
        # Create an editable dataframe
        edited_df = st.data_editor(
            st.session_state.what_if_df[["Name", "Power (W)", "Hours/Day", "Days/Month", "Standby (W)"]],
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn("Appliance", disabled=True),
                "Power (W)": st.column_config.NumberColumn("Power (W)", min_value=0.0, step=10.0),
                "Hours/Day": st.column_config.NumberColumn("Hours/Day", min_value=0.0, max_value=24.0, step=0.5),
                "Days/Month": st.column_config.NumberColumn("Days/Month", min_value=0, max_value=31, step=1),
                "Standby (W)": st.column_config.NumberColumn("Standby (W)", min_value=0.0, step=1.0)
            }
        )
        
        # Calculate new metrics based on edits
        # First, merge the non-editable columns back (like Quantity)
        temp_df = st.session_state.what_if_df.copy()
        temp_df.update(edited_df)
        
        projected_df = calculate_projected_energy(temp_df)
        
        proj_monthly_kwh = projected_df['Projected Monthly kWh'].sum()
        proj_monthly_co2 = projected_df['Projected Monthly CO2 (kg)'].sum()
        
        savings_kwh = total_monthly_kwh - proj_monthly_kwh
        savings_co2 = total_monthly_co2 - proj_monthly_co2
        
        st.markdown("#### Projected Impact")
        wc1, wc2, wc3 = st.columns(3)
        wc1.metric(
            "Projected Monthly Energy", 
            f"{proj_monthly_kwh:.1f} kWh", 
            f"{-savings_kwh:.1f} kWh" if savings_kwh != 0 else None,
            delta_color="inverse"
        )
        wc2.metric(
            "Projected Monthly Carbon", 
            f"{proj_monthly_co2:.1f} kg", 
            f"{-savings_co2:.1f} kg" if savings_co2 != 0 else None,
            delta_color="inverse"
        )
        
        pct_saved = (savings_kwh / total_monthly_kwh * 100) if total_monthly_kwh > 0 else 0
        wc3.metric(
            "Overall Reduction",
            f"{pct_saved:.1f}%",
            "Great Job!" if pct_saved > 0 else None
        )
        
        # Comparison Chart
        chart_data = pd.DataFrame({
            "Scenario": ["Baseline", "Projected", "Baseline", "Projected"],
            "Metric": ["Energy (kWh)", "Energy (kWh)", "Carbon (kg)", "Carbon (kg)"],
            "Value": [total_monthly_kwh, proj_monthly_kwh, total_monthly_co2, proj_monthly_co2]
        })
        
        fig_comp = px.bar(
            chart_data, 
            x="Metric", 
            y="Value", 
            color="Scenario", 
            barmode="group",
            title="Baseline vs Projected Monthly Impact"
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 3: RECOMMENDATIONS
    # -------------------------------------------------------------------------
    with tab3:
        st.subheader("💡 Personalized Optimization Strategies")
        
        recs = get_recommendations(df_baseline)
        for i, rec in enumerate(recs):
            st.info(rec)
            
        st.markdown("### Why Optimize?")
        st.write("""
        Every kilowatt-hour of energy saved reduces grid strain and decreases fossil fuel dependency. 
        By identifying high-drain appliances and adjusting your usage patterns, you can make a measurable 
        impact on your household's carbon footprint while also lowering utility bills.
        """)

if __name__ == "__main__":
    render_home_energy_optimization_center()
