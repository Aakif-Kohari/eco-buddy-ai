import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Clean Energy Options | EcoBuddy",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Clean Energy Options")
st.write(
    "Explore cleaner energy sources and discover which options "
    "can help reduce your environmental impact."
)

st.divider()


ENERGY_DATA = {
    "☀️ Solar Energy": {
        "description": "Energy generated from sunlight using solar panels.",
        "renewable": "Yes",
        "emissions": "Very Low",
        "cost": "Medium",
        "best_for": "Homes, buildings, schools",
        "benefits": [
            "Reduces dependence on fossil fuels",
            "Low operating emissions",
            "Can reduce electricity bills",
            "Suitable for rooftops"
        ]
    },

    "🌬️ Wind Energy": {
        "description": "Electricity generated using wind turbines.",
        "renewable": "Yes",
        "emissions": "Very Low",
        "cost": "Medium–High",
        "best_for": "Large open areas",
        "benefits": [
            "Produces clean electricity",
            "No fuel required",
            "Low operating emissions",
            "Highly scalable"
        ]
    },

    "💧 Hydropower": {
        "description": "Electricity generated from flowing or falling src.environment.water.",
        "renewable": "Yes",
        "emissions": "Low",
        "cost": "High",
        "best_for": "Areas with suitable water resources",
        "benefits": [
            "Reliable electricity generation",
            "Renewable energy source",
            "Long operational lifetime",
            "Can provide large-scale electricity"
        ]
    },

    "🌱 Biogas": {
        "description": "Energy produced from organic waste and biomass.",
        "renewable": "Yes",
        "emissions": "Low–Medium",
        "cost": "Low–Medium",
        "best_for": "Farms, households, communities",
        "benefits": [
            "Converts organic waste into energy",
            "Reduces waste",
            "Can produce cooking gas",
            "Useful for rural communities"
        ]
    },

    "🌋 Geothermal Energy": {
        "description": "Energy generated using heat from beneath the Earth's surface.",
        "renewable": "Yes",
        "emissions": "Very Low",
        "cost": "High",
        "best_for": "Geologically suitable areas",
        "benefits": [
            "Reliable energy source",
            "Low greenhouse gas emissions",
            "Works continuously",
            "Small land footprint"
        ]
    }
}


# ==========================================
# ENERGY SELECTOR
# ==========================================

st.subheader("🔎 Explore Clean Energy")

selected_energy = st.selectbox(
    "Choose an energy option",
    list(ENERGY_DATA.keys())
)

energy = ENERGY_DATA[selected_energy]


# ==========================================
# ENERGY OVERVIEW
# ==========================================

st.info(energy["description"])

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "♻️ Renewable",
        energy["renewable"]
    )

with col2:
    st.metric(
        "🌍 Emissions",
        energy["emissions"]
    )

with col3:
    st.metric(
        "💰 Cost Level",
        energy["cost"]
    )


st.divider()


# ==========================================
# BEST FOR
# ==========================================

st.subheader("🏠 Best Suited For")

st.success(
    f"**{energy['best_for']}**"
)


# ==========================================
# BENEFITS
# ==========================================

st.subheader("🌱 Key Benefits")

for benefit in energy["benefits"]:
    st.write(f"✅ {benefit}")


# ==========================================
# ENERGY COMPARISON
# ==========================================

st.divider()

st.subheader("📊 Compare Clean Energy Sources")

comparison_data = []

for name, values in ENERGY_DATA.items():
    comparison_data.append({
        "Energy Source": name,
        "Renewable": values["renewable"],
        "Emissions": values["emissions"],
        "Cost": values["cost"],
        "Best For": values["best_for"]
    })

comparison_df = pd.DataFrame(comparison_data)

st.dataframe(
    comparison_df,
    use_container_width=True,
    hide_index=True
)


# ==========================================
# PERSONAL RECOMMENDATION
# ==========================================

st.divider()

st.subheader("💡 Find the Right Option")

location_type = st.selectbox(
    "What type of location are you considering?",
    [
        "🏠 Home",
        "🏢 Business",
        "🌾 Farm",
        "🏫 School / Institution",
        "🌳 Community"
    ]
)

if location_type == "🏠 Home":
    recommendation = "☀️ Solar Energy is a strong option for homes with suitable rooftop space."

elif location_type == "🏢 Business":
    recommendation = "☀️ Solar Energy can help businesses reduce grid electricity consumption."

elif location_type == "🌾 Farm":
    recommendation = "🌱 Biogas and ☀️ Solar Energy can be useful options for farms."

elif location_type == "🏫 School / Institution":
    recommendation = "☀️ Solar Energy can help institutions generate clean electricity."

else:
    recommendation = "☀️ Solar, 🌬️ Wind, and 🌱 Biogas can be considered depending on local resources."

st.success(recommendation)


# ==========================================
# CLEAN ENERGY TIPS
# ==========================================

st.divider()

st.subheader("🌎 Simple Ways to Use Cleaner Energy")

tips = [
    "☀️ Consider installing solar panels if suitable for your location.",
    "💡 Replace traditional bulbs with energy-efficient LED lighting.",
    "🔌 Turn off appliances when they are not being used.",
    "⚡ Choose energy-efficient appliances when replacing old ones.",
    "🌡️ Reduce unnecessary heating and cooling.",
    "🔋 Consider battery storage where renewable energy systems support it.",
    "🚲 Reduce unnecessary fuel consumption through walking, cycling, or public transport."
]

for tip in tips:
    st.write(tip)

st.divider()

st.caption(
    "⚡ EcoBuddy Clean Energy Guide | "
    "Energy suitability depends on location, resources, "
    "installation requirements, and local conditions."
)