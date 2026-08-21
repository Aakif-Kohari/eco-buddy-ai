"""
Food Waste Prevention Dashboard.
Streamlit page displaying pantry health, spoilage timeline, and prevention tips.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from waste_prevention_engine import WastePreventionEngine
from database import add_pantry_item, get_pantry_inventory, remove_pantry_item

st.set_page_config(page_title="Food Waste Prevention", page_icon="🥬", layout="wide")

st.title("🥬 Food Spoilage Predictor & Waste Prevention")
st.markdown(
    "Track your pantry health and get AI-driven suggestions to use food before it spoils."
)

engine = WastePreventionEngine()

# --- Sidebar: Add Item ---
st.sidebar.header("🛒 Log New Purchase")
with st.sidebar.form("add_item_form"):
    item_name = st.text_input("Item Name (e.g., Spinach, Milk)")
    purchase_date = st.date_input("Purchase Date", value=datetime.now())
    storage = st.selectbox(
        "Storage Method", ["refrigerated", "pantry", "freezer", "counter"]
    )

    if st.form_submit_button("Add to Pantry"):
        if item_name:
            add_pantry_item(item_name, purchase_date.strftime("%Y-%m-%d"), storage)
            st.success(f"Added {item_name} to pantry!")
            st.rerun()
        else:
            st.error("Please enter an item name.")

# --- Main Dashboard ---
inventory = get_pantry_inventory()
analysis = engine.analyze_pantry(inventory)

col1, col2, col3 = st.columns(3)
col1.metric(
    "Pantry Health Score",
    f"{analysis['health_score']}/100",
    delta=f"{analysis['health_score'] - 100}"
    if analysis["health_score"] < 100
    else None,
)
col2.metric("Total Items", analysis["total_items"])
col3.metric(
    "Items Expiring Soon",
    analysis["expiring_items"],
    delta_color="inverse" if analysis["expiring_items"] > 0 else "off",
)

# --- Alerts Section ---
if analysis["alerts"]:
    st.subheader("⚠️ Action Required: Expiring Items")
    for alert in analysis["alerts"]:
        color = "red" if alert["urgency"] == "critical" else "orange"
        st.markdown(
            f":{color}[**{alert['item'].title()}**] - {alert['days_remaining']} days remaining"
        )
        st.info(alert["recommendation"])
        if st.button(
            f"Mark '{alert['item']}' as Used/Removed", key=f"remove_{alert['item']}"
        ):
            remove_pantry_item(alert["item"])
            st.rerun()
else:
    st.success("✅ Your pantry is in great shape! No items are expiring soon.")

# --- Inventory Table ---
st.divider()
st.subheader("📦 Current Pantry Inventory")
if inventory:
    df = pd.DataFrame(inventory)
    df["expiration_date"] = pd.to_datetime(df["expiration_date"]).dt.strftime(
        "%Y-%m-%d"
    )

    # Color code the urgency column
    def color_urgency(val):
        if val == "critical":
            return "color: red; font-weight: bold"
        if val == "warning":
            return "color: orange; font-weight: bold"
        if val == "expired":
            return "color: darkred; font-weight: bold"
        return "color: green"

    styled_df = df.style.applymap(color_urgency, subset=["urgency"])
    st.dataframe(styled_df, use_container_width=True)
else:
    st.info("Your pantry is empty. Add items using the sidebar to start tracking!")
