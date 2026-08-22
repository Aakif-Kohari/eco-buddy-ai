import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import get_assessments
from styles.theme import apply_theme

# Advanced Emission Factors (kg CO2 per km)
MODE_FACTORS = {
    "Walking": 0.0,
    "Bicycle": 0.0,
    "Electric Bike (E-Bike)": 0.01,
    "Public Transit (Bus/Train)": 0.07,
    "Electric Vehicle (EV)": 0.05,
    "Motorcycle": 0.11,
    "Hybrid Car": 0.13,
    "Gasoline Car": 0.19,
    "Diesel Car": 0.21,
    "SUV/Truck": 0.27
}

def calculate_commute_emissions(mode: str, distance_km: float, frequency_days_per_week: int, passengers: int = 1) -> dict:
    """Calculates daily, weekly, monthly, and yearly emissions for a given commute profile."""
    base_factor = MODE_FACTORS.get(mode, 0.19)
    
    # Adjust for carpooling/passengers if the mode is a car/SUV type
    if mode in ["Gasoline Car", "Diesel Car", "SUV/Truck", "Hybrid Car", "Electric Vehicle (EV)"]:
        adjusted_factor = base_factor / max(1, passengers)
    else:
        adjusted_factor = base_factor

    daily_distance = distance_km * 2  # round trip assumption
    daily_emissions = daily_distance * adjusted_factor
    weekly_emissions = daily_emissions * frequency_days_per_week
    monthly_emissions = weekly_emissions * 4.33
    yearly_emissions = weekly_emissions * 52

    return {
        "Daily": daily_emissions,
        "Weekly": weekly_emissions,
        "Monthly": monthly_emissions,
        "Yearly": yearly_emissions,
        "Daily_Distance": daily_distance
    }

def generate_green_score(yearly_emissions_kg: float) -> tuple:
    """Generates a sustainability score (0-100) based on yearly commute emissions."""
    # Benchmark: Average commute footprint is ~2000 kg CO2/year
    if yearly_emissions_kg <= 0:
        return 100, "Perfect Net-Zero 🌟"
    elif yearly_emissions_kg < 500:
        return 90, "Excellent 🍃"
    elif yearly_emissions_kg < 1200:
        return 75, "Good 🌿"
    elif yearly_emissions_kg < 2500:
        return 50, "Average ⚖️"
    elif yearly_emissions_kg < 4000:
        return 30, "High Impact ⚠️"
    else:
        return 10, "Critical Impact 🛑"

def get_recommendations(mode: str, distance: float) -> list:
    """Provides actionable recommendations based on the current commute profile."""
    recs = []
    if mode in ["Walking", "Bicycle", "Electric Bike (E-Bike)"]:
        recs.append("🌟 Amazing! You are using an active, zero-emission mode of transport. Keep it up!")
    elif mode == "Public Transit (Bus/Train)":
        recs.append("🚇 Great choice. Public transit significantly reduces per-capita emissions compared to driving.")
        if distance < 5:
            recs.append("🚲 Since your commute is under 5km, consider a bicycle or e-bike on nice weather days for health and zero emissions.")
    elif mode in ["Gasoline Car", "Diesel Car", "SUV/Truck"]:
        if distance < 3:
            recs.append("🚶 Your commute is very short. Walking or cycling could easily replace this car trip!")
        elif distance < 15:
            recs.append("🚌 Consider checking if public transit options exist for this route.")
            recs.append("🚲 An E-Bike is a highly efficient alternative for commutes under 15km.")
        recs.append("🤝 If driving is a must, try organizing a carpool. Sharing a ride with just one person cuts your carbon footprint in half!")
        if mode == "SUV/Truck":
            recs.append("🔋 SUVs have high emission footprints. If you ever upgrade your vehicle, consider a Hybrid or EV for substantial daily savings.")
    elif mode == "Electric Vehicle (EV)":
        recs.append("⚡ Excellent! You're driving zero-tailpipe-emission tech. Note that grid energy still carries a small footprint unless powered entirely by renewables.")
        recs.append("🤝 Consider carpooling to maximize the efficiency of your EV.")
    return recs

def render_green_transportation_planner():
    apply_theme()
    st.title("🚲 Green Transportation Planner")
    st.markdown("Analyze your daily commute, compare transit modes, and uncover lower-impact alternatives to optimize your carbon footprint.")

    user_id = st.session_state.get('user_id', 1)
    
    # Try to load defaults from latest assessment
    default_mode = "Gasoline Car"
    default_dist = 10.0
    try:
        assessments = get_assessments(user_id)
        if assessments:
            recent = assessments[0]
            db_mode = recent[3] # transport
            db_dist = recent[4] # distance
            if db_mode == "Car":
                default_mode = "Gasoline Car"
            elif db_mode == "Bike":
                default_mode = "Bicycle"
            elif db_mode == "Public Transport":
                default_mode = "Public Transit (Bus/Train)"
            elif db_mode == "Walking":
                default_mode = "Walking"
            default_dist = float(db_dist) if db_dist else 10.0
    except Exception:
        pass

    tab_planner, tab_whatif, tab_recommendations = st.tabs([
        "📍 Commute Impact Analyzer", 
        "🔮 What-If Comparison", 
        "💡 Route Optimization"
    ])

    with tab_planner:
        st.subheader("Your Current Commute Profile")
        col1, col2 = st.columns(2)
        with col1:
            current_mode = st.selectbox("Transportation Mode", list(MODE_FACTORS.keys()), index=list(MODE_FACTORS.keys()).index(default_mode))
            current_dist = st.number_input("One-way Distance (km)", min_value=0.1, max_value=500.0, value=default_dist, step=1.0)
        with col2:
            current_freq = st.number_input("Commute Days per Week", min_value=1, max_value=7, value=5, step=1)
            current_passengers = 1
            if current_mode in ["Gasoline Car", "Diesel Car", "SUV/Truck", "Hybrid Car", "Electric Vehicle (EV)"]:
                current_passengers = st.number_input("Total Passengers (Including you)", min_value=1, max_value=8, value=1, step=1)
        
        current_impact = calculate_commute_emissions(current_mode, current_dist, current_freq, current_passengers)
        score, rating = generate_green_score(current_impact["Yearly"])

        st.markdown("---")
        st.subheader("📊 Carbon Footprint Summary")
        
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Green Score", f"{score}/100", rating, delta_color="off")
        sc2.metric("Daily CO₂", f"{current_impact['Daily']:.2f} kg")
        sc3.metric("Monthly CO₂", f"{current_impact['Monthly']:.1f} kg")
        sc4.metric("Yearly CO₂", f"{current_impact['Yearly']:.0f} kg")

        # Breakdown chart
        chart_data = pd.DataFrame({
            "Timeframe": ["Daily", "Weekly", "Monthly"],
            "Emissions (kg CO2)": [current_impact["Daily"], current_impact["Weekly"], current_impact["Monthly"]]
        })
        fig = px.bar(chart_data, x="Timeframe", y="Emissions (kg CO2)", title="Emissions Progression", text_auto='.1f', color="Timeframe")
        fig.update_layout(showlegend=False, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    with tab_whatif:
        st.subheader("🔮 Alternative Commute Simulator")
        st.markdown("Experiment with different modes, carpooling, or remote work days to see your potential savings.")
        
        wc1, wc2 = st.columns(2)
        with wc1:
            alt_mode = st.selectbox("Alternative Mode", list(MODE_FACTORS.keys()), index=list(MODE_FACTORS.keys()).index("Public Transit (Bus/Train)"))
            alt_freq = st.number_input("Alternative Days per Week", min_value=0, max_value=7, value=current_freq, step=1, help="Set lower than current to simulate remote working days.")
        with wc2:
            alt_passengers = 1
            if alt_mode in ["Gasoline Car", "Diesel Car", "SUV/Truck", "Hybrid Car", "Electric Vehicle (EV)"]:
                alt_passengers = st.number_input("Alt Passengers", min_value=1, max_value=8, value=1, step=1)
            
            st.info("Simulating exact same distance: **{:.1f} km (one-way)**".format(current_dist))

        alt_impact = calculate_commute_emissions(alt_mode, current_dist, alt_freq, alt_passengers)
        
        savings_yearly = current_impact["Yearly"] - alt_impact["Yearly"]
        savings_monthly = current_impact["Monthly"] - alt_impact["Monthly"]
        
        st.markdown("### 💰 Potential Carbon Savings")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Alternative Yearly CO₂", f"{alt_impact['Yearly']:.0f} kg", f"{-savings_yearly:.0f} kg" if savings_yearly != 0 else None, delta_color="inverse")
        mc2.metric("Alternative Monthly CO₂", f"{alt_impact['Monthly']:.1f} kg", f"{-savings_monthly:.1f} kg" if savings_monthly != 0 else None, delta_color="inverse")
        
        pct_saved = (savings_yearly / current_impact["Yearly"] * 100) if current_impact["Yearly"] > 0 else 0
        mc3.metric("Reduction %", f"{pct_saved:.1f}%", "Greener!" if pct_saved > 0 else None)

        # Plotly comparison
        comp_df = pd.DataFrame({
            "Scenario": ["Current Setup", "Current Setup", "Current Setup", "Alternative", "Alternative", "Alternative"],
            "Timeframe": ["Daily", "Weekly", "Monthly", "Daily", "Weekly", "Monthly"],
            "Emissions (kg CO2)": [
                current_impact["Daily"], current_impact["Weekly"], current_impact["Monthly"],
                alt_impact["Daily"], alt_impact["Weekly"], alt_impact["Monthly"]
            ]
        })
        
        fig_comp = px.bar(comp_df, x="Timeframe", y="Emissions (kg CO2)", color="Scenario", barmode="group", title="Current vs Alternative Commute Emissions")
        st.plotly_chart(fig_comp, use_container_width=True)

    with tab_recommendations:
        st.subheader("💡 Smart Route Optimization")
        
        recs = get_recommendations(current_mode, current_dist)
        for r in recs:
            st.info(r)
            
        st.markdown("### 🌳 The Bigger Picture")
        st.write("""
        Transportation is one of the largest contributors to household greenhouse gas emissions. 
        Even small changes, like working from home one day a week or carpooling with a neighbor, 
        compound into massive carbon savings over the span of a year. 
        
        Explore the **What-If Comparison** tab to visualize how adopting minor changes 
        could drastically improve your Green Score!
        """)

if __name__ == "__main__":
    render_green_transportation_planner()
