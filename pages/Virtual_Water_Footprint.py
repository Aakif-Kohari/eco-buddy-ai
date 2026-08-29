"""
Virtual Water Footprint Page.
Streamlit page featuring an interactive consumption logger, a global water stress visualization, and a "water saved" dashboard.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from virtual_water_tracker import VirtualWaterTracker
from consumer_goods_water_db import ConsumerGoodsWaterDB
from database import save_virtual_water_log, get_virtual_water_history

st.set_page_config(page_title="Virtual Water Footprint", page_icon="💧", layout="wide")

st.title("💧 Dynamic Virtual Water Footprint & Consumer Goods Analyzer")
st.markdown(
    "Discover the hidden water footprint embedded in your everyday purchases and understand your impact on global water scarcity."
)

tracker = VirtualWaterTracker()
db = ConsumerGoodsWaterDB()
products = db.get_all_products()
regions = db.get_all_regions()

# --- Sidebar: Logger ---
st.sidebar.header("🛒 Log a Purchase")
with st.sidebar.form("log_purchase_form"):
    product = st.selectbox(
        "Product", options=products, format_func=lambda x: x.replace("_", " ").title()
    )
    quantity = st.number_input("Quantity", min_value=0.1, step=0.1, value=1.0)
    region = st.selectbox(
        "Region of Origin",
        options=regions,
        format_func=lambda x: x.replace("_", " ").title(),
    )

    if st.form_submit_button("Log Purchase"):
        try:
            record = tracker.log_purchase(product, quantity, region)
            save_virtual_water_log(
                product, quantity, region, record["scarcity_weighted_total_l"]
            )
            st.sidebar.success(
                f"Logged {quantity} {record['unit']} of {product.replace('_', ' ')}!"
            )
            st.rerun()
        except ValueError as e:
            st.sidebar.error(str(e))

# --- Main Dashboard ---
aggregation = tracker.get_aggregated_footprint()

if aggregation["total_purchases"] > 0:
    st.subheader("📊 Your Virtual Water Footprint")

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Total Raw Water",
        f"{aggregation['total_raw_water_l']:,.0f} L",
        help="Sum of blue, green, and grey water.",
    )
    col2.metric(
        "Scarcity-Weighted Water",
        f"{aggregation['total_scarcity_weighted_l']:,.0f} L",
        help="Adjusts blue/grey water by regional water stress.",
    )
    col3.metric(
        "Equivalent Bathtubs",
        f"{int(aggregation['total_raw_water_l'] / 150)}",
        help="Based on a 150L bathtub.",
    )

    # Water Type Breakdown Chart
    st.markdown("### 💧 Water Footprint Breakdown")
    fig_pie = go.Figure(
        data=[
            go.Pie(
                labels=[
                    "Blue Water (Surface/Ground)",
                    "Green Water (Rain)",
                    "Grey Water (Pollution Dilution)",
                ],
                values=[
                    aggregation["total_blue_water_l"],
                    aggregation["total_green_water_l"],
                    aggregation["total_grey_water_l"],
                ],
                hole=0.4,
                marker_colors=["#1f77b4", "#2ca02c", "#7f7f7f"],
            )
        ]
    )
    fig_pie.update_layout(template="plotly_white")
    st.plotly_chart(fig_pie, use_container_width=True)

    # Regional Impact Chart
    st.markdown("### 🌍 Global Water Trade Impact")
    if aggregation["regional_impact"]:
        region_df = pd.DataFrame(
            [
                {
                    "Region": k.replace("_", " ").title(),
                    "Scarcity-Weighted Water (L)": v["scarcity_weighted_l"],
                    "Items": v["items"],
                }
                for k, v in aggregation["regional_impact"].items()
            ]
        )

        # Add stress category for coloring
        region_df["Stress Category"] = region_df["Region"].apply(
            lambda x: db.get_stress_category(
                db.get_regional_stress(x.lower().replace(" ", "_"))
            )
        )

        fig_bar = px.bar(
            region_df,
            x="Region",
            y="Scarcity-Weighted Water (L)",
            color="Stress Category",
            color_discrete_map={
                "Low Stress": "#2ca02c",
                "Medium Stress": "#ff7f0e",
                "High Stress": "#d62728",
                "Extreme Stress": "#8c564b",
            },
            title="Water Footprint by Region of Origin",
            text="Items",
        )
        fig_bar.update_layout(template="plotly_white")
        st.plotly_chart(fig_bar, use_container_width=True)

    # High Impact Items & Suggestions
    st.markdown("### ⚠️ High-Impact Purchases & Green Swaps")
    high_impact = tracker.get_high_impact_items()

    for item in high_impact:
        with st.expander(
            f"{item['product'].replace('_', ' ').title()} ({item['quantity']} {item['unit']}) - {item['scarcity_weighted_total_l']:,.0f} L scarcity-weighted"
        ):
            st.write(
                f"**Region:** {item['region'].replace('_', ' ').title()} (Stress Index: {item['water_stress_index']})"
            )
            st.write(
                f"**Blue:** {item['blue_water_l']:,.0f} L | **Green:** {item['green_water_l']:,.0f} L | **Grey:** {item['grey_water_l']:,.0f} L"
            )
            st.markdown("💡 **Suggestions:**")
            for suggestion in tracker.suggest_alternatives(item["product"]):
                st.markdown(f"- {suggestion}")
else:
    st.info(
        "No purchases logged yet. Use the sidebar to start tracking your virtual water footprint!"
    )

# --- History ---
st.divider()
st.subheader("📜 Logged Purchase History")
history = get_virtual_water_history()
if history:
    st.dataframe(pd.DataFrame(history), use_container_width=True)
