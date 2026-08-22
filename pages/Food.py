import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Food Impact | EcoBuddy",
    page_icon="🍎",
    layout="wide"
)

FOOD_DATA = {
    "Beef": {
        "carbon": 27.0,
        "water": 15400,
        "impact": "Very High",
        "alternative": "Lentils / Beans"
    },
    "Lamb": {
        "carbon": 24.0,
        "water": 10400,
        "impact": "Very High",
        "alternative": "Chickpeas / Lentils"
    },
    "Cheese": {
        "carbon": 13.5,
        "water": 5600,
        "impact": "High",
        "alternative": "Plant-based alternatives"
    },
    "Pork": {
        "carbon": 7.2,
        "water": 6000,
        "impact": "High",
        "alternative": "Chicken / Beans"
    },
    "Chicken": {
        "carbon": 6.9,
        "water": 4300,
        "impact": "Medium",
        "alternative": "Lentils / Chickpeas"
    },
    "Eggs": {
        "carbon": 4.8,
        "water": 3300,
        "impact": "Medium",
        "alternative": "Plant-based protein"
    },
    "Rice": {
        "carbon": 2.7,
        "water": 2500,
        "impact": "Medium",
        "alternative": "Potatoes / Millets"
    },
    "Milk": {
        "carbon": 3.2,
        "water": 1000,
        "impact": "Medium",
        "alternative": "Oat / Soy milk"
    },
    "Tofu": {
        "carbon": 2.0,
        "water": 1800,
        "impact": "Low",
        "alternative": "Lentils"
    },
    "Potatoes": {
        "carbon": 0.7,
        "water": 290,
        "impact": "Very Low",
        "alternative": "Great choice!"
    },
    "Lentils": {
        "carbon": 0.9,
        "water": 1250,
        "impact": "Very Low",
        "alternative": "Great choice!"
    },
    "Vegetables": {
        "carbon": 0.4,
        "water": 300,
        "impact": "Very Low",
        "alternative": "Great choice!"
    }
}



st.title("🍽️ Food Impact Analyzer")
st.write(
    "Understand the environmental impact of your food choices "
    "and discover more sustainable alternatives."
)

st.divider()



col1, col2 = st.columns(2)

with col1:
    food = st.selectbox(
        "🥗 Select a food",
        list(FOOD_DATA.keys())
    )

with col2:
    quantity = st.number_input(
        "⚖️ Quantity (grams)",
        min_value=1,
        max_value=5000,
        value=100,
        step=10
    )


# ==========================================
# Calculate impact
# ==========================================

food_info = FOOD_DATA[food]

quantity_kg = quantity / 1000

carbon_impact = food_info["carbon"] * quantity_kg
water_usage = food_info["water"] * quantity_kg


# ==========================================
# Impact Score
# ==========================================

if carbon_impact >= 2.0:
    score = 30
elif carbon_impact >= 1.0:
    score = 55
elif carbon_impact >= 0.5:
    score = 75
else:
    score = 90


# ==========================================
# Results
# ==========================================

st.subheader("🌱 Your Food Impact")

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric(
        "🌍 Carbon Footprint",
        f"{carbon_impact:.2f} kg CO₂e"
    )

with metric2:
    st.metric(
        "💧 Water Usage",
        f"{water_usage:,.0f} L"
    )

with metric3:
    st.metric(
        "🌱 Eco Score",
        f"{score}/100"
    )


# ==========================================
# Impact Level
# ==========================================

st.subheader("📊 Impact Level")

impact = food_info["impact"]

if impact == "Very High":
    st.error(f"🔴 {impact} Environmental Impact")

elif impact == "High":
    st.warning(f"🟠 {impact} Environmental Impact")

elif impact == "Medium":
    st.info(f"🟡 {impact} Environmental Impact")

else:
    st.success(f"🟢 {impact} Environmental Impact")


# ==========================================
# Sustainable Alternative
# ==========================================

st.subheader("💡 Eco-Friendly Alternative")

st.success(
    f"Try **{food_info['alternative']}** as a more sustainable option."
)


# ==========================================
# Sustainability Tips
# ==========================================

st.subheader("🌎 Make Your Meal More Sustainable")

tips = [
    "🥦 Add more seasonal vegetables to your meals.",
    "🌱 Try plant-based protein such as lentils and beans.",
    "🛒 Choose locally produced food when possible.",
    "♻️ Avoid unnecessary food packaging.",
    "🍽️ Reduce food waste by planning your portions.",
    "🥡 Store leftovers properly instead of throwing them away."
]

for tip in tips:
    st.write(tip)


# ==========================================
# Food Comparison
# ==========================================

st.divider()

st.subheader("🔎 Compare Food Choices")

comparison_data = []

for name, values in FOOD_DATA.items():
    comparison_data.append({
        "Food": name,
        "CO₂e (kg/kg)": values["carbon"],
        "Water (L/kg)": values["water"],
        "Impact": values["impact"]
    })

df = pd.DataFrame(comparison_data)

df = df.sort_values(
    by="CO₂e (kg/kg)",
    ascending=True
)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)

st.divider()

st.caption(
    "🌱 EcoBuddy Food Impact Analyzer | "
    "Values are approximate estimates and may vary by "
    "production method, location, and supply chain."
)