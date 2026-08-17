"""
Streamlit UI Page for Scope 3 Supply Chain Insetting & Decarbonization Planner
"""

import streamlit as st
from src.lib.supply_chain_insetting import SupplyChainInsettingPlanner, SCOPE3_CATEGORIES, INSETTING_INTERVENTIONS

def render_supply_chain_page():
    st.set_page_config(page_title="Supply Chain Insetting", page_icon="🌐", layout="wide")
    st.title("🌐 Scope 3 Supply Chain Insetting & Decarbonization")
    st.markdown("Transform indirect value chain emissions from unmanaged liabilities into verified in-value-chain climate interventions.")

    planner = SupplyChainInsettingPlanner()

    tab1, tab2 = st.tabs(["📊 Scope 3 Screening & Profiling", "🌱 Carbon Insetting Project Modeler"])

    with tab1:
        st.subheader("Scope 3 Category Screening")
        col1, col2 = st.columns(2)

        with col1:
            cat_choices = {k: v["name"] for k, v in SCOPE3_CATEGORIES.items()}
            selected_cat = st.selectbox("Scope 3 Category", list(cat_choices.keys()), format_func=lambda k: cat_choices[k])
            activity_spend = st.number_input("Annual Activity Spend / Throughput ($)", min_value=100.0, max_value=100000000.0, value=50000.0, step=5000.0)

        with col2:
            primary_discount = st.slider("Supplier Primary Clean Energy Adoption (%)", min_value=0, max_value=70, value=15, help="Reduction factor from audited direct supplier PPA / clean grid data")

        if st.button("Calculate Value Chain Impact", type="primary"):
            res = planner.calculate_category_emissions(selected_cat, activity_spend, primary_discount)
            c1, c2, c3 = st.columns(3)
            c1.metric("Raw Screening Footprint", f"{res['raw_emissions_tco2e']} tCO₂e")
            c2.metric("Adjusted Direct Footprint", f"{res['adjusted_emissions_tco2e']} tCO₂e")
            c3.metric("Data Quality Tier", res["primary_data_confidence"])

    with tab2:
        st.subheader("Design Insetting Interventions")
        col_a, col_b = st.columns(2)

        with col_a:
            intervention_type = st.selectbox("Intervention Program", list(INSETTING_INTERVENTIONS.keys()), format_func=lambda k: INSETTING_INTERVENTIONS[k]["title"])
            target_tons = st.number_input("Target Emissions Abatement (Tonnes CO₂e)", min_value=10.0, max_value=100000.0, value=250.0, step=25.0)

        with col_b:
            budget = st.number_input("Co-Investment Capital Allocation ($ USD)", min_value=500.0, max_value=10000000.0, value=5000.0, step=500.0)

        if st.button("Model Insetting Feasibility"):
            model_res = planner.evaluate_insetting_intervention(intervention_type, target_tons, budget)
            
            if model_res["is_fully_funded"]:
                st.success("✅ **Project Is Fully Funded within Allocated Budget!**")
            else:
                st.warning(f"⚠️ **Funding Gap Detected:** ${model_res['funding_gap_usd']:,} USD needed to reach 100% target abatement.")

            m1, m2, m3 = st.columns(3)
            m1.metric("Unit Cost", f"${model_res['cost_per_ton_co2']} / tCO₂e")
            m2.metric("Total Project Cost", f"${model_res['total_estimated_project_cost_usd']:,}")
            m3.metric("Achieved Abatement", f"{model_res['achievable_abatement_with_budget_tco2e']} tCO₂e")

            st.markdown("#### Program Co-Benefits:")
            for benefit in model_res["co_benefits"]:
                st.write(f"- 🌿 {benefit}")

if __name__ == "__main__":
    render_supply_chain_page()
