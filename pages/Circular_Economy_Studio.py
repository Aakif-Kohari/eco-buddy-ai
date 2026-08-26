"""
Streamlit Page for Enterprise Circular Economy Lifecycle Studio
"""

import streamlit as st
from src.utils.circular_economy_engine import CircularEconomyEngine, CircularMaterialComponent

st.set_page_config(
    page_title="Circular Economy Lifecycle Studio",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 Enterprise Circular Economy Lifecycle Studio")
st.caption("Perform Product Lifecycle Assessment (LCA), Material Circularity Index (MCI) scoring, and Scope 3 closed-loop recycling telemetry.")

if "circular_engine" not in st.session_state:
    st.session_state.circular_engine = CircularEconomyEngine()

engine: CircularEconomyEngine = st.session_state.circular_engine

# Top Metrics Bar
col1, col2, col3, col4 = st.columns(4)
profiles = engine.filter_profiles()

avg_mci = sum(p.material_circularity_index for p in profiles) / len(profiles) if profiles else 0.0
total_carbon = sum(p.embodied_carbon_total for p in profiles)
avg_diversion = sum(p.waste_diversion_rate_pct for p in profiles) / len(profiles) if profiles else 0.0

col1.metric("Average Material Circularity (MCI)", f"{avg_mci:.2f}", "+0.12 vs Target")
col2.metric("Total Embodied Carbon (kg CO2e)", f"{total_carbon:.1f}", "-18.4% Avoided")
col3.metric("Landfill Diversion Rate", f"{avg_diversion:.1f}%", "+5.2% YoY")
col4.metric("Active Product Lifecycles", f"{len(profiles)}", "Fully Audited")

st.markdown("---")

# Filter controls
st.subheader("📦 Audited Circular Product Catalog")
c1, c2 = st.columns([2, 1])

category_choice = c1.selectbox("Filter by Category", ["All", "Industrial Hardware", "Consumer Electronics", "Packaging Solutions"])
min_mci_input = c2.slider("Minimum Material Circularity Index (MCI)", 0.0, 1.0, 0.5, 0.05)

filtered = engine.filter_profiles(category_filter=category_choice, min_mci=min_mci_input)

for p in filtered:
    with st.expander(f"📌 {p.product_name} ({p.product_id}) - MCI: {p.material_circularity_index}"):
        st.write(f"**Category:** {p.category}")
        st.write(f"**Total Weight:** {p.total_weight_kg} kg | **Landfill Diversion:** {p.waste_diversion_rate_pct}%")
        st.write(f"**End-of-Life Pathway:** {p.eol_pathway}")
        
        st.markdown("#### Material Component Breakdown")
        for comp in p.components:
            st.info(f"• **{comp.material_name}**: {comp.weight_kg} kg | Recycled Content: {comp.recycled_content_pct}% | Recyclability Rate: {comp.recyclability_rate_pct}% | Carbon: {comp.embodied_carbon_kg_co2e} kg CO2e")

st.markdown("---")
st.subheader("➕ Register New Product Circular Lifecycle")

with st.form("new_circular_product_form"):
    prod_id = st.text_input("Product ID", value="PROD-CIRC-902")
    prod_name = st.text_input("Product Name", value="EcoFiber Modular Packaging Enclosure")
    category = st.selectbox("Category", ["Packaging Solutions", "Industrial Hardware", "Consumer Electronics"])
    eol = st.selectbox("End of Life Pathway", ["Closed-Loop Takeback & Remanufacturing", "Industrial Composting", "Chemical Recycling"])
    
    st.markdown("##### Material Component 1")
    m1_name = st.text_input("Component 1 Material", value="Recycled Kraft Cardboard")
    m1_weight = st.number_input("Component 1 Weight (kg)", value=2.5, min_value=0.1)
    m1_recycled = st.slider("Component 1 Recycled %", 0, 100, 95)
    
    submitted = st.form_submit_button("Register Product Lifecycle & Calculate MCI")
    
    if submitted:
        new_comp = CircularMaterialComponent(
            material_name=m1_name,
            weight_kg=m1_weight,
            virgin_content_pct=float(100 - m1_recycled),
            recycled_content_pct=float(m1_recycled),
            recyclability_rate_pct=95.0,
            toxicity_index=0.01,
            embodied_carbon_kg_co2e=1.8
        )
        engine.register_product_profile(prod_id, prod_name, category, [new_comp], eol)
        st.success(f"Product {prod_name} registered successfully with MCI calculated!")
        st.rerun()
