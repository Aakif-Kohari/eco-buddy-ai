"""
Streamlit UI Page for Smart Circular Economy & Upcycling Exchange
"""

import streamlit as st
from src.lib.circular_economy import CircularEconomyEngine, MATERIAL_CIRCULARITY_FACTORS, UPCYCLING_IDEAS

def render_circular_economy_page():
    st.set_page_config(page_title="Circular Economy & Upcycling", page_icon="🔄", layout="wide")
    st.title("🔄 Smart Circular Economy & Upcycling Exchange")
    st.markdown("Assess material retention, extended lifecycle value, and discover AI-guided upcycling transformations for common household items.")

    engine = CircularEconomyEngine()

    tab1, tab2, tab3 = st.tabs(["📦 Item Assessment", "♻️ Upcycling Ideas Library", "📊 Batch Exchange Impact"])

    with tab1:
        st.subheader("Evaluate Item Circularity & Retention Potential")
        col1, col2 = st.columns(2)

        with col1:
            category_options = [c.replace("_", " ").title() for c in MATERIAL_CIRCULARITY_FACTORS.keys()]
            selected_cat = st.selectbox("Material / Category", category_options, key="circ_cat")
            age = st.number_input("Current Item Age (Years)", min_value=0.1, max_value=50.0, value=2.5, step=0.5)
            lifespan = st.number_input("Expected Product Lifespan (Years)", min_value=0.5, max_value=50.0, value=5.0, step=0.5)

        with col2:
            condition = st.slider("Current Physical Condition Rating", min_value=1, max_value=5, value=3, help="1 = Damaged/Scrap, 5 = Like New")
            repairs = st.number_input("Number of Past Repairs / Refurbishments", min_value=0, max_value=20, value=1)

        if st.button("Calculate Circularity & Recommended Pathway", type="primary"):
            res = engine.calculate_circularity_score(
                category=selected_cat.lower().replace(" ", "_"),
                current_age_years=age,
                expected_lifespan_years=lifespan,
                condition_rating=condition,
                repair_attempts=repairs
            )

            st.success(f"### Recommended Action: {res['recommended_pathway']}")

            m1, m2, m3 = st.columns(3)
            m1.metric("Circularity Score", f"{res['circularity_index']} / 100")
            m2.metric("Retained Embodied CO2", f"{res['retained_embodied_co2_kg']} kg CO₂e")
            m3.metric("Avoided Replacement CO2", f"{res['avoided_replacement_co2_kg']} kg CO₂e")

            if res["upcycling_recommendations"]:
                st.markdown("#### Suggested High-Impact Upcycling Projects:")
                for proj in res["upcycling_recommendations"]:
                    with st.expander(f"✨ {proj['title']} (Difficulty: {proj['difficulty']})"):
                        st.write(f"**Estimated CO2 Avoided:** {proj['co2_saved_kg']} kg")
                        st.write(f"**Tools Required:** {', '.join(proj['tools_needed'])}")

    with tab2:
        st.subheader("Browse Comprehensive Upcycling Repository")
        for cat, ideas in UPCYCLING_IDEAS.items():
            with st.expander(f"🏷️ Category: {cat.replace('_', ' ').title()}"):
                for idea in ideas:
                    st.markdown(f"- **{idea['title']}** ({idea['difficulty']}) — Avoids ~{idea['co2_saved_kg']} kg CO2e | Tools: `{', '.join(idea['tools_needed'])}`")

    with tab3:
        st.subheader("Community Upcycling & Swap Batch Impact")
        st.info("Simulate aggregated savings across community reuse hubs and swap events.")
        
        sample_items = [
            {"category": "electronics", "age_years": 3.0, "expected_lifespan_years": 4.0, "condition": 4, "repairs": 1},
            {"category": "textiles", "age_years": 1.5, "expected_lifespan_years": 2.0, "condition": 3, "repairs": 0},
            {"category": "furniture_wood", "age_years": 6.0, "expected_lifespan_years": 10.0, "condition": 4, "repairs": 2},
            {"category": "metals", "age_years": 4.0, "expected_lifespan_years": 8.0, "condition": 3, "repairs": 1}
        ]

        if st.button("Run Community Batch Simulation"):
            batch_res = engine.assess_item_exchange_impact(sample_items)
            c1, c2, c3 = st.columns(3)
            c1.metric("Items Processed", batch_res["total_items"])
            c2.metric("Total CO2 Diverted", f"{batch_res['total_co2_saved_kg']} kg")
            c3.metric("Average Circularity", f"{batch_res['average_circularity_score']} / 100")
            st.json(batch_res["category_breakdown"])

if __name__ == "__main__":
    render_circular_economy_page()
