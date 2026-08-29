import streamlit as st
import pandas as pd
from plugins.fashion_impact import FashionImpactCalculator

st.set_page_config(
    page_title="Fashion Impact Calculator",
    page_icon="👕",
    layout="wide"
)

st.title("👕 Sustainable Fashion & Textile Calculator")
st.markdown("""
Welcome to the Fashion Impact Calculator! The fashion industry is responsible for 10% of annual global carbon emissions and is a major consumer of src.environment.water.
Use this tool to evaluate the true environmental cost of your clothing purchases.
""")

@st.cache_resource
def get_calculator():
    return FashionImpactCalculator()

calc = get_calculator()

col1, col2 = st.columns([1, 1])

with col1:
    st.header("Garment Details")
    
    garment_type = st.selectbox(
        "Item Type (for weight estimation)",
        ["T-Shirt (150g)", "Jeans (500g)", "Sweater (400g)", "Jacket (800g)", "Socks (50g)", "Custom Weight"]
    )
    
    if garment_type == "Custom Weight":
        weight_kg = st.number_input("Custom Weight (kg)", min_value=0.01, max_value=5.0, value=0.2)
    else:
        # Extract the grams from the string, e.g. "T-Shirt (150g)" -> 150
        grams = int(garment_type.split("(")[1].replace("g)", ""))
        weight_kg = grams / 1000.0
        
    is_second_hand = st.checkbox("Bought Second-Hand / Thrifted", value=False)
    lifespan = st.slider("Expected Lifespan (Years)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

    st.subheader("Material Blend")
    st.markdown("Specify the fabric composition (must total 100%).")
    
    available_materials = calc.get_available_materials()
    
    # Simple dynamic UI for blending
    num_materials = st.number_input("How many different materials in this garment?", min_value=1, max_value=4, value=1)
    
    blend = {}
    total_pct = 0.0
    
    for i in range(num_materials):
        mc1, mc2 = st.columns([2, 1])
        with mc1:
            mat = st.selectbox(f"Material {i+1}", available_materials, key=f"mat_{i}")
        with mc2:
            pct = st.number_input(f"Percentage %", min_value=0.0, max_value=100.0, value=100.0 if i==0 else 0.0, key=f"pct_{i}")
            
        if pct > 0:
            if mat in blend:
                blend[mat] += pct / 100.0
            else:
                blend[mat] = pct / 100.0
        total_pct += pct
        
    if abs(total_pct - 100.0) > 0.01:
        st.error(f"Total percentage is {total_pct}%. It must equal exactly 100%.")
        st.stop()

with col2:
    st.header("Impact Analysis")
    
    if st.button("Calculate Environmental Impact", type="primary"):
        with st.spinner("Analyzing supply chain data..."):
            try:
                impact = calc.calculate_garment_impact(
                    garment_weight_kg=weight_kg,
                    material_blend=blend,
                    is_second_hand=is_second_hand,
                    lifespan_years=lifespan
                )
                
                # Metrics Row
                m1, m2 = st.columns(2)
                m1.metric("Carbon Footprint", f"{impact['total_carbon_kg']} kg CO₂e")
                m2.metric("Water Footprint", f"{impact['total_water_liters']} Liters")
                
                # Context
                st.info(f"That's equivalent to driving a gas car for **{round(impact['total_carbon_kg'] * 4)} km** and drinking **{round(impact['total_water_liters'] / 2)} days** worth of src.environment.water.")
                
                # Yearly
                st.markdown(f"**Amortized Carbon:** {impact['carbon_per_year_kg']} kg CO₂e / year based on a {lifespan}-year lifespan.")
                
                if impact['contains_microplastics']:
                    st.warning("⚠️ Contains synthetics. High risk of microplastic shedding during washing.")
                
                # Recommendations
                st.subheader("💡 Actionable Recommendations")
                recs = calc.generate_recommendations(impact)
                if not recs:
                    st.success("Great job! This is a highly sustainable purchase.")
                else:
                    for r in recs:
                        st.markdown(f"- {r}")
                        
            except Exception as e:
                st.error(f"Calculation Error: {e}")

st.markdown("---")
st.subheader("📚 Fabric Dataset Reference")
st.dataframe(calc.df, use_container_width=True)
