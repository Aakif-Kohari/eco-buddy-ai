import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import get_assessments
from styles.theme import apply_theme

# Food Database with detailed environmental impact
FOOD_DB = {
    "Beef": {"category": "Meat", "co2_per_kg": 60.0, "water_per_kg": 15000, "alt": "Lentils", "desc": "High impact due to methane and land use."},
    "Lamb": {"category": "Meat", "co2_per_kg": 24.0, "water_per_kg": 10000, "alt": "Beans", "desc": "High footprint, similar to beef."},
    "Chicken": {"category": "Meat", "co2_per_kg": 7.0, "water_per_kg": 4300, "alt": "Tofu", "desc": "Lower impact than red meat but significant water usage."},
    "Pork": {"category": "Meat", "co2_per_kg": 7.0, "water_per_kg": 6000, "alt": "Tempeh", "desc": "Moderate footprint."},
    "Fish": {"category": "Meat", "co2_per_kg": 5.0, "water_per_kg": 2500, "alt": "Plant-based seafood", "desc": "Depends on fishing methods, generally moderate."},
    "Cheese": {"category": "Dairy", "co2_per_kg": 21.0, "water_per_kg": 3180, "alt": "Vegan Cheese", "desc": "High impact due to milk concentration."},
    "Milk": {"category": "Dairy", "co2_per_kg": 3.0, "water_per_kg": 1020, "alt": "Oat Milk", "desc": "Moderate footprint, high land use."},
    "Eggs": {"category": "Dairy", "co2_per_kg": 4.5, "water_per_kg": 3300, "alt": "Flax Egg", "desc": "Moderate impact."},
    "Rice": {"category": "Grains", "co2_per_kg": 4.0, "water_per_kg": 2500, "alt": "Quinoa", "desc": "High water footprint and methane from paddies."},
    "Wheat/Bread": {"category": "Grains", "co2_per_kg": 1.4, "water_per_kg": 1600, "alt": "Oats", "desc": "Low impact staple."},
    "Apples": {"category": "Fruits", "co2_per_kg": 0.4, "water_per_kg": 822, "alt": "Local Fruits", "desc": "Very low impact, especially if locally sourced."},
    "Bananas": {"category": "Fruits", "co2_per_kg": 0.7, "water_per_kg": 790, "alt": "Local Fruits", "desc": "Low impact but often transported long distances."},
    "Tomatoes": {"category": "Vegetables", "co2_per_kg": 1.4, "water_per_kg": 214, "alt": "Seasonal Veggies", "desc": "Low impact if open-field, higher if greenhouse."},
    "Potatoes": {"category": "Vegetables", "co2_per_kg": 0.5, "water_per_kg": 287, "alt": "Sweet Potatoes", "desc": "Very low footprint."},
    "Lentils": {"category": "Plant-based", "co2_per_kg": 0.9, "water_per_kg": 1250, "alt": "Beans", "desc": "Excellent low-impact protein source."},
    "Tofu": {"category": "Plant-based", "co2_per_kg": 2.0, "water_per_kg": 2500, "alt": "Lentils", "desc": "Good alternative to meat."},
    "Processed Snacks": {"category": "Processed Foods", "co2_per_kg": 5.0, "water_per_kg": 2000, "alt": "Fresh Fruits", "desc": "High processing energy footprint."}
}

CATEGORIES = list(set(f["category"] for f in FOOD_DB.values()))

def calculate_item_impact(item_name, weekly_kg, is_local=True):
    data = FOOD_DB.get(item_name)
    if not data:
        return 0.0, 0.0
    
    co2 = data["co2_per_kg"] * weekly_kg
    water = data["water_per_kg"] * weekly_kg
    
    # Apply a 25% emissions penalty for imported/non-local goods due to transport & cold storage
    if not is_local:
        co2 *= 1.25
        
    return co2, water

def render_sustainable_food_planner():
    apply_theme()
    st.title("🥗 Sustainable Food Planner & Tracker")
    st.markdown("Track your food consumption, compare environmental impacts, and build a sustainable meal plan.")

    user_id = st.session_state.get('user_id', 1)

    # State initialization
    if "meal_plan" not in st.session_state:
        st.session_state.meal_plan = []
    if "food_reduction_goal" not in st.session_state:
        st.session_state.food_reduction_goal = 20
    if "planner_reset" not in st.session_state:
        st.session_state.planner_reset = False

    if st.session_state.planner_reset:
        st.session_state.meal_plan = []
        st.session_state.planner_reset = False

    # Personalization via assessments
    try:
        assessments = get_assessments(user_id)
        current_diet = assessments[-1][5] if assessments else "Unknown"
    except Exception:
        current_diet = "Unknown"

    with st.expander("👤 Personalized Profile"):
        st.write(f"**Current Diet Profile:** {current_diet}")
        st.write("Your highest-impact food category is estimated to be **Meat** (if consumed) based on average dietary patterns. We recommend prioritizing plant-based alternatives.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📅 Meal Planner",
        "⚖️ Compare Foods",
        "🔮 What-If Analysis",
        "🗑️ Waste Tracker",
        "🎯 Goals & Progress"
    ])

    with tab1:
        st.subheader("Add Food to Your Weekly Plan")
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        with col1:
            selected_food = st.selectbox("Food Item", list(FOOD_DB.keys()))
        with col2:
            meal_type = st.selectbox("Meal", ["Breakfast", "Lunch", "Dinner", "Snacks"])
        with col3:
            portion_g = st.number_input("Portion (grams)", min_value=0, value=200, step=50)
        with col4:
            frequency = st.number_input("Times/week", min_value=1, value=3, max_value=21, step=1)
        with col5:
            st.markdown("<br>", unsafe_allow_html=True)
            is_local = st.checkbox("Locally Sourced?", value=True, help="Non-local foods have a 25% higher CO2 footprint due to transport.")

        if st.button("➕ Add to Plan"):
            if portion_g <= 0:
                st.warning("Portion must be greater than 0.")
            else:
                weekly_kg = (portion_g / 1000.0) * frequency
                co2, water = calculate_item_impact(selected_food, weekly_kg, is_local)
                st.session_state.meal_plan.append({
                    "Meal": meal_type,
                    "Food": selected_food,
                    "Category": FOOD_DB[selected_food]["category"],
                    "Local": "Yes" if is_local else "No",
                    "Portion (g)": portion_g,
                    "Frequency/Week": frequency,
                    "Weekly (kg)": weekly_kg,
                    "CO2 (kg)": co2,
                    "Water (L)": water
                })
                st.success(f"Added {selected_food} to your plan for {meal_type}!")

        if st.session_state.meal_plan:
            st.markdown("---")
            st.subheader("Your Weekly Food Plan")
            plan_df = pd.DataFrame(st.session_state.meal_plan)
            st.dataframe(plan_df, use_container_width=True)
            
            # Export Plan feature
            csv = plan_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Meal Plan (CSV)", data=csv, file_name="sustainable_meal_plan.csv", mime="text/csv")

            total_co2 = plan_df["CO2 (kg)"].sum()
            total_water = plan_df["Water (L)"].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Weekly CO₂", f"{total_co2:.1f} kg")
            c2.metric("Total Weekly Water", f"{total_water:,.0f} L")
            c3.metric("Total Monthly CO₂ (est)", f"{total_co2 * 4.33:.1f} kg")

            if st.button("🗑️ Clear Plan"):
                st.session_state.planner_reset = True
                st.rerun()

            # Visualizations
            st.markdown("#### Impact by Category")
            cat_df = plan_df.groupby("Category")[["CO2 (kg)", "Water (L)"]].sum().reset_index()
            fig_pie = px.pie(cat_df, names="Category", values="CO2 (kg)", title="CO₂ Emissions by Food Category", hole=0.3)
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Suggest alternatives for highest impact
            if total_co2 > 0:
                highest_impact_item = plan_df.loc[plan_df["CO2 (kg)"].idxmax()]
                alt = FOOD_DB[highest_impact_item["Food"]]["alt"]
                st.info(f"💡 **Suggestion:** Your highest impact item is **{highest_impact_item['Food']}**. Consider replacing some portions with **{alt}**.")

    with tab2:
        st.subheader("Compare Food Choices")
        st.write("Compare the environmental footprint of two foods per kg.")
        c1, c2 = st.columns(2)
        with c1:
            food_a = st.selectbox("Food A", list(FOOD_DB.keys()), index=0)
        with c2:
            food_b = st.selectbox("Food B", list(FOOD_DB.keys()), index=14)

        if food_a and food_b:
            fa_data = FOOD_DB[food_a]
            fb_data = FOOD_DB[food_b]
            
            diff_co2 = fa_data['co2_per_kg'] - fb_data['co2_per_kg']
            diff_water = fa_data['water_per_kg'] - fb_data['water_per_kg']

            st.markdown(f"**Savings per kg if switching from {food_a} to {food_b}:**")
            sc1, sc2 = st.columns(2)
            sc1.metric("CO₂ Savings", f"{diff_co2:.1f} kg", delta=f"{-diff_co2:.1f} kg" if diff_co2 > 0 else None, delta_color="inverse")
            sc2.metric("Water Savings", f"{diff_water:,.0f} L", delta=f"{-diff_water:,.0f} L" if diff_water > 0 else None, delta_color="inverse")

            comp_df = pd.DataFrame({
                "Food": [food_a, food_b],
                "CO2 (kg/kg)": [fa_data['co2_per_kg'], fb_data['co2_per_kg']],
                "Water (L/kg)": [fa_data['water_per_kg'], fb_data['water_per_kg']]
            })
            
            fig_comp = px.bar(comp_df, x="Food", y=["CO2 (kg/kg)", "Water (L/kg)"], barmode="group", title="Footprint Comparison (per kg)")
            st.plotly_chart(fig_comp, use_container_width=True)

    with tab3:
        st.subheader("What-If Analysis")
        st.write("Simulate reducing high-impact foods from your current meal plan.")
        
        if not st.session_state.meal_plan:
            st.warning("Please add items to your meal plan in the 'Meal Planner' tab first.")
        else:
            plan_df = pd.DataFrame(st.session_state.meal_plan)
            baseline_co2 = plan_df["CO2 (kg)"].sum()
            baseline_water = plan_df["Water (L)"].sum()

            target_cat = st.selectbox("Select Category to Reduce", CATEGORIES)
            reduction_pct = st.slider("Reduction Percentage", 0, 100, 50, 10)

            projected_co2 = 0
            projected_water = 0
            for idx, row in plan_df.iterrows():
                mult = (1 - reduction_pct/100.0) if row["Category"] == target_cat else 1.0
                projected_co2 += row["CO2 (kg)"] * mult
                projected_water += row["Water (L)"] * mult

            abs_reduction_co2 = baseline_co2 - projected_co2
            pct_reduction_co2 = (abs_reduction_co2 / baseline_co2 * 100) if baseline_co2 > 0 else 0

            st.markdown(f"### Results of reducing {target_cat} by {reduction_pct}%")
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Baseline CO₂", f"{baseline_co2:.1f} kg")
            mc2.metric("Projected CO₂", f"{projected_co2:.1f} kg", delta=f"{-abs_reduction_co2:.1f} kg")
            mc3.metric("Reduction %", f"{pct_reduction_co2:.1f}%")

            chart_data = pd.DataFrame({
                "Scenario": ["Baseline", "Projected"],
                "CO₂ Emissions (kg)": [baseline_co2, projected_co2]
            })
            fig_wi = px.bar(chart_data, x="Scenario", y="CO₂ Emissions (kg)", color="Scenario", title="Baseline vs Projected Emissions")
            st.plotly_chart(fig_wi, use_container_width=True)

    with tab4:
        st.subheader("Food Waste Tracker")
        st.write("Estimate your weekly food waste and its environmental impact.")
        
        waste_cat = st.selectbox("Waste Category", ["Fruits/Vegetables", "Meat/Dairy", "Grains/Bread", "Mixed/Other"])
        waste_kg = st.number_input("Estimated Weekly Waste (kg)", min_value=0.0, value=1.5, step=0.5)
        
        waste_factors = {
            "Fruits/Vegetables": {"co2": 1.5, "water": 300},
            "Meat/Dairy": {"co2": 15.0, "water": 5000},
            "Grains/Bread": {"co2": 2.5, "water": 1000},
            "Mixed/Other": {"co2": 4.0, "water": 1500},
        }

        if st.button("Calculate Waste Impact"):
            if waste_kg < 0.1:
                st.warning("Please enter a valid waste amount.")
            else:
                factor = waste_factors[waste_cat]
                w_co2 = factor["co2"] * waste_kg
                w_water = factor["water"] * waste_kg
                
                st.error(f"⚠️ Your weekly {waste_cat} waste generates approx **{w_co2:.1f} kg CO₂** and wastes **{w_water:,.0f} L** of water.")
                
                st.markdown("### Practical Waste Reduction Tips")
                st.markdown("- **Plan Meals:** Buy only what you need using a shopping list.")
                st.markdown("- **Store Properly:** Keep fruits/veggies in appropriate environments to extend life.")
                st.markdown("- **Compost:** Reduce methane emissions by composting unavoidable scraps.")
                st.markdown("- **Repurpose:** Use veggie scraps for broth and stale bread for croutons.")

    with tab5:
        st.subheader("Goals & Progress")
        goal = st.slider("Weekly Food Impact Reduction Goal (%)", 0, 100, st.session_state.food_reduction_goal, 5)
        st.session_state.food_reduction_goal = goal

        if not st.session_state.meal_plan:
            st.info("Start building your meal plan to track progress against your goals.")
        else:
            plan_df = pd.DataFrame(st.session_state.meal_plan)
            # Estimate a baseline if user had average meat-heavy diet (for demo purposes)
            total_co2 = plan_df["CO2 (kg)"].sum()
            assumed_baseline = total_co2 * 1.5 if total_co2 > 0 else 50.0 
            
            current_reduction = ((assumed_baseline - total_co2) / assumed_baseline) * 100
            
            st.markdown(f"**Assumed Typical Baseline:** {assumed_baseline:.1f} kg CO₂/week")
            st.markdown(f"**Your Plan:** {total_co2:.1f} kg CO₂/week")
            
            score = max(0, min(100, int((current_reduction / max(1, goal)) * 100)))
            
            st.markdown(f"**Goal Progress: {current_reduction:.1f}% / {goal}% Reduction**")
            st.progress(max(0.0, min(current_reduction / max(1, goal), 1.0)))

            if score >= 100:
                st.success(f"🏆 Incredible! Food Sustainability Score: **{score}/100**")
            elif score >= 50:
                st.info(f"🌟 Good work! Food Sustainability Score: **{score}/100**")
            else:
                st.warning(f"🌱 Room for improvement. Food Sustainability Score: **{score}/100**")
                
        st.markdown("---")
        st.markdown("### 🩺 Health Co-Benefits")
        st.info("Did you know? Shifting to a more plant-rich diet not only reduces carbon emissions and water usage, but is strongly correlated with lower risks of heart disease, type 2 diabetes, and certain cancers. Sustainable eating is healthy eating!")

if __name__ == "__main__":
    render_sustainable_food_planner()
