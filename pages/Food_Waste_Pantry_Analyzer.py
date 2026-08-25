"""
Streamlit Page: Eco-Food Waste & Smart Pantry Analyzer
Multi-page section in EcoBuddy AI allowing users to track pantry inventory, prevent food spoilage, and reduce greenhouse gas emissions.
"""

import streamlit as st
import pandas as pd
from datetime import date

from eco_food_waste_pantry_service import FoodWastePantryService
from eco_food_waste_pantry_types import FoodCategory, StorageCondition
from eco_food_waste_pantry_cards import render_pantry_summary_header, render_pantry_item_card
from eco_food_waste_pantry_charts import build_spoilage_risk_donut_chart, build_food_category_co2_chart

st.set_page_config(
    page_title="Smart Pantry & Food Waste - EcoBuddy AI",
    page_icon="🥗",
    layout="wide",
)

st.title("🥗 Smart Pantry & Food Waste Analyzer")
st.markdown(
    "Track perishable food inventory, receive early spoilage warnings, "
    "prevent unnecessary food waste, and eliminate wasted household carbon emissions."
)

service = FoodWastePantryService()
current_user_id = st.session_state.get("user_id", 1)

# Render Overview Header
summary = service.get_user_summary(current_user_id)
render_pantry_summary_header(summary)

st.divider()

# Navigation Tabs
tab_inventory, tab_at_risk, tab_add_item, tab_analytics = st.tabs([
    "📦 Active Pantry Inventory",
    "⚠️ At-Risk / Expiring Soon",
    "➕ Add Item to Pantry",
    "📊 Food Waste Analytics",
])

# -------------------------------------------------------------------
# Tab 1: Active Pantry Inventory
# -------------------------------------------------------------------
with tab_inventory:
    st.subheader("📋 Current Pantry Items")

    cat_options = ["All"] + [c.value for c in FoodCategory]
    selected_cat = st.selectbox("Filter by Category", cat_options)

    items = service.get_active_pantry(current_user_id, category_filter=selected_cat)

    def handle_consumed(item_id: int):
        if service.mark_consumed(item_id):
            st.success("😋 Item marked as consumed! Great job preventing waste.")
            st.rerun()

    def handle_wasted(item_id: int):
        if service.mark_wasted(item_id):
            st.warning("🗑️ Item marked as discarded.")
            st.rerun()

    if not items:
        st.info("Your pantry is currently empty. Add items using the 'Add Item' tab!")
    else:
        for item in items:
            render_pantry_item_card(item, on_consumed_cb=handle_consumed, on_wasted_cb=handle_wasted)

# -------------------------------------------------------------------
# Tab 2: At-Risk / Expiring Soon
# -------------------------------------------------------------------
with tab_at_risk:
    st.subheader("⚠️ Priority Items - Expiring Soon or Expired")

    at_risk_items = service.get_at_risk_items(current_user_id)
    if not at_risk_items:
        st.success("🎉 All items in your pantry are fresh! Zero immediate spoilage risks detected.")
    else:
        for item in at_risk_items:
            render_pantry_item_card(item, on_consumed_cb=handle_consumed, on_wasted_cb=handle_wasted)

# -------------------------------------------------------------------
# Tab 3: Add Item to Pantry
# -------------------------------------------------------------------
with tab_add_item:
    st.subheader("➕ Add New Item to Pantry")
    with st.form("add_pantry_item_form"):
        col1, col2 = st.columns(2)

        with col1:
            item_name = st.text_input("Item Name*", placeholder="e.g. Organic Almond Milk")
            category = st.selectbox("Category*", [c.value for c in FoodCategory])
            quantity = st.number_input("Quantity*", min_value=0.1, value=1.0, step=0.5)
            unit = st.text_input("Unit*", placeholder="e.g. carton, kg, loaf, items")

        with col2:
            purchase_date = st.date_input("Purchase Date*", value=date.today())
            shelf_life = st.number_input("Estimated Shelf Life (Days)*", min_value=1, value=7, step=1)
            storage = st.selectbox("Storage Condition*", [s.value for s in StorageCondition])
            co2_per_unit = st.number_input("CO₂ Footprint per Unit (kg)*", min_value=0.01, value=0.75, step=0.1)
            cost_per_unit = st.number_input("Cost per Unit ($ USD)*", min_value=0.01, value=3.99, step=0.5)

        submit = st.form_submit_button("🚀 Save to Pantry")
        if submit:
            if not item_name or not unit:
                st.error("Please provide an item name and unit.")
            else:
                new_item = service.add_item_to_pantry(
                    user_id=current_user_id,
                    item_name=item_name,
                    category=FoodCategory(category),
                    quantity=quantity,
                    unit=unit,
                    purchase_date=purchase_date.isoformat(),
                    shelf_life_days=int(shelf_life),
                    storage_condition=StorageCondition(storage),
                    co2_footprint_kg_per_unit=co2_per_unit,
                    cost_per_unit_usd=cost_per_unit,
                )
                if new_item:
                    st.success(f"Added '{item_name}' to pantry inventory!")
                    st.rerun()
                else:
                    st.error("Failed to add pantry item.")

# -------------------------------------------------------------------
# Tab 4: Food Waste Analytics
# -------------------------------------------------------------------
with tab_analytics:
    st.subheader("📊 Pantry Spoilage Risk & CO₂ Analytics")

    all_items = service.get_active_pantry(current_user_id)
    if all_items:
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            donut_chart = build_spoilage_risk_donut_chart(all_items)
            st.plotly_chart(donut_chart, use_container_width=True)

        with col_c2:
            bar_chart = build_food_category_co2_chart(all_items)
            st.plotly_chart(bar_chart, use_container_width=True)
    else:
        st.info("Add pantry items to view analytics.")
