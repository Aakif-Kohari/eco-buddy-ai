"""
Grocery Efficiency Page.
Streamlit page featuring an interactive shopping list builder, price-vs-carbon scatter plots, and substitution recommendations.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
from price_carbon_analyzer import PriceCarbonAnalyzer
from smart_shopping_list import SmartShoppingList
from database import save_grocery_optimization, get_grocery_history

st.set_page_config(page_title="Grocery Efficiency", page_icon="🛒", layout="wide")

st.title("🛒 Sustainable Grocery Price-to-Carbon Efficiency Analyzer")
st.markdown(
    "Optimize your shopping list to minimize carbon footprint per dollar spent without sacrificing nutrition."
)

analyzer = PriceCarbonAnalyzer()
builder = SmartShoppingList()

# --- Tab 1: Item Analyzer & Substitutions ---
tab1, tab2 = st.tabs(["🔍 Item Analyzer", "📝 Smart List Builder"])

with tab1:
    st.subheader("Analyze & Find Substitutions")
    items = analyzer.get_all_items_with_efficiency()
    df_items = pd.DataFrame(items)

    # Scatter plot: Price vs Carbon, sized by Nutrition, colored by Efficiency
    fig = px.scatter(
        df_items,
        x="price_per_kg",
        y="carbon_per_kg",
        size="nutrition_score",
        color="efficiency_score",
        hover_name="name",
        labels={
            "price_per_kg": "Price per kg ($)",
            "carbon_per_kg": "Carbon per kg (kg CO₂e)",
            "efficiency_score": "Eco-Efficiency Score",
        },
        color_continuous_scale="Viridis",
        title="Price vs. Carbon Footprint (Larger = More Nutritious, Darker = More Efficient)",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Find a Better Alternative")
    target_item = st.selectbox(
        "Select an item you usually buy:", options=[item["name"] for item in items]
    )

    if st.button("Find Substitutions"):
        subs = analyzer.find_substitutions(target_item)
        if subs:
            st.success(
                f"Great news! Here are better alternatives to **{target_item}**:"
            )
            for sub in subs:
                st.markdown(
                    f"- **{sub['name'].replace('_', ' ').title()}**: "
                    f"Saves **{sub['carbon_savings_pct']}%** carbon and **{sub['price_savings_pct']}%** cost, "
                    f"with a higher efficiency score of **{sub['efficiency_score']}**."
                )
        else:
            st.info(
                f"**{target_item}** is already one of the most efficient choices in its category!"
            )

# --- Tab 2: Smart List Builder ---
with tab2:
    st.subheader("Build an Optimized Shopping List")
    col1, col2 = st.columns(2)

    with col1:
        budget = st.number_input(
            "Total Grocery Budget ($)", min_value=10.0, step=5.0, value=50.0
        )
        categories = st.multiselect(
            "Required Food Categories",
            options=["meat", "plant_protein", "grain", "nuts", "vegetable"],
            default=["plant_protein", "grain", "vegetable"],
        )

    if st.button("🚀 Generate Optimized List"):
        if not categories:
            st.error("Please select at least one food category.")
        else:
            result = builder.generate_optimized_list(budget, categories)
            st.session_state.optimized_list = result
            save_grocery_optimization(budget, categories, result)
            st.success("List generated successfully!")

    if "optimized_list" in st.session_state:
        res = st.session_state.optimized_list

        st.divider()
        st.markdown("#### 📊 Optimization Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Budget Used",
            f"${budget - res['remaining_budget_usd']:.2f} / ${budget:.2f}",
        )
        c2.metric("Total Carbon", f"{res['total_carbon_kg']:.2f} kg CO₂e")
        c3.metric(
            "Avg Carbon per Dollar", f"{res['average_carbon_per_dollar']:.2f} kg/$"
        )

        st.markdown("#### 🛒 Your Optimized Shopping List")
        df_list = pd.DataFrame(res["items"])
        st.dataframe(df_list, use_container_width=True, hide_index=True)
