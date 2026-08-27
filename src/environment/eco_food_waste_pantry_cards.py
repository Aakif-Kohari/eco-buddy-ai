"""
Streamlit Component Renderers for Smart Pantry & Food Waste Analyzer
"""

import streamlit as st
from typing import Dict, Any, Callable
from src.environment.eco_food_waste_pantry_types import PantryItem, FoodWasteSummary


def render_pantry_summary_header(summary: FoodWasteSummary) -> None:
    """Renders top summary metrics for smart pantry food waste prevention."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🥗 Consumed Rate",
            value=f"{summary.waste_reduction_rate_pct:.1f}%",
            delta=f"{summary.items_consumed} Consumed",
        )

    with col2:
        st.metric(
            label="🌿 CO₂ Saved",
            value=f"{summary.co2_prevented_kg:,.1f} kg",
            delta="Prevented Emissions",
        )

    with col3:
        st.metric(
            label="💵 Money Saved",
            value=f"${summary.money_saved_usd:,.2f}",
            delta="USD Retained",
        )

    with col4:
        st.metric(
            label="⚠️ CO₂ Lost to Waste",
            value=f"{summary.co2_lost_to_waste_kg:,.1f} kg",
            delta=f"${summary.money_lost_usd:,.2f} Lost",
        )


def render_pantry_item_card(item: PantryItem, on_consumed_cb: Callable = None, on_wasted_cb: Callable = None) -> None:
    """Renders an individual pantry item card with spoilage risk alert badge."""
    risk = item.get_spoilage_risk()
    days_left = item.days_until_expiration()

    if risk == "EXPIRED":
        badge_bg, badge_fg, badge_text = "#FFEBEE", "#C62828", "🚨 EXPIRED"
    elif risk == "HIGH_RISK":
        badge_bg, badge_fg, badge_text = "#FFF3E0", "#E65100", f"⚠️ Eat Soon ({days_left}d left)"
    elif risk == "MODERATE_RISK":
        badge_bg, badge_fg, badge_text = "#FFFDE7", "#F57F17", f"⏳ Use Soon ({days_left}d left)"
    else:
        badge_bg, badge_fg, badge_text = "#E8F5E9", "#2E7D32", f"✅ Fresh ({days_left}d left)"

    with st.container():
        st.markdown(
            f"""
            <div style="
                border: 1px solid #E0E0E0;
                border-radius: 10px;
                padding: 14px;
                margin-bottom: 12px;
                background-color: #FFFFFF;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: #1B5E20;">{item.item_name}</h4>
                    <span style="
                        background-color: {badge_bg};
                        color: {badge_fg};
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-size: 0.85rem;
                        font-weight: 700;
                    ">{badge_text}</span>
                </div>
                <p style="color: #666; margin-top: 4px; font-size: 0.9rem;">
                    <b>Quantity:</b> {item.quantity} {item.unit} &nbsp;|&nbsp; 
                    <b>Category:</b> {item.category.value} &nbsp;|&nbsp; 
                    <b>Storage:</b> {item.storage_condition.value}
                </p>
                <div style="display: flex; gap: 16px; font-size: 0.85rem; color: #555;">
                    <span>🌿 CO₂: {item.co2_footprint_kg_per_unit * item.quantity:.2f} kg</span>
                    <span>💵 Cost: ${item.cost_per_unit_usd * item.quantity:.2f} USD</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_c, col_w, _ = st.columns([1, 1, 3])
        with col_c:
            if st.button("😋 Consumed", key=f"btn_con_{item.id}"):
                if on_consumed_cb:
                    on_consumed_cb(item.id)
        with col_w:
            if st.button("🗑️ Discarded", key=f"btn_was_{item.id}"):
                if on_wasted_cb:
                    on_wasted_cb(item.id)
