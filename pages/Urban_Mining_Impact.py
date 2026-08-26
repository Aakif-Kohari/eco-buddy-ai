"""
Urban Mining Impact Page.
Streamlit page where users can log old devices, view their "recovery value" score, and find localized certified e-waste recycling info.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.utils.urban_mining_calculator import UrbanMiningCalculator
from src.utils.critical_mineral_db import CriticalMineralDB
from src.core.database import save_urban_mining_inventory, get_urban_mining_history

st.set_page_config(page_title="Urban Mining Impact", page_icon="⛏️", layout="wide")

st.title("⛏️ Urban Mining & Critical Mineral Recovery Estimator")
st.markdown(
    "Quantify the embedded critical minerals in your old electronics and the environmental benefit of certified recycling vs. landfill disposal."
)

calculator = UrbanMiningCalculator()
db = CriticalMineralDB()
devices = db.get_all_devices()

# --- Input Section ---
st.subheader("📱 Log Your End-of-Life Devices")
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    selected_device = st.selectbox(
        "Device Type",
        options=devices,
        format_func=lambda x: db.get_device_display_name(x),
    )
with col2:
    quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
with col3:
    st.write("")  # Spacer
    st.write("")  # Spacer
    if st.button("➕ Add to Inventory"):
        calculator.add_device(selected_device, quantity)
        st.success(f"Added {quantity}x {db.get_device_display_name(selected_device)}")
        st.rerun()

# Display current inventory
if calculator.logged_devices:
    st.markdown("#### Current Inventory")
    df_inventory = pd.DataFrame(calculator.logged_devices)
    st.dataframe(
        df_inventory[["device_name", "quantity"]],
        use_container_width=True,
        hide_index=True,
    )

# --- Calculation & Display ---
st.divider()
if st.button("⛏️ Calculate Urban Mining Value", type="primary"):
    result = calculator.calculate_recovery_value()
    st.session_state.mining_result = result
    st.session_state.recommendations = calculator.get_recycling_recommendations()

    # Save to DB
    save_urban_mining_inventory(calculator.logged_devices, result)
    st.success("Recovery value calculated and saved!")

if "mining_result" in st.session_state:
    result = st.session_state.mining_result

    st.subheader("📊 Recovery Value & Impact Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Devices Logged", result["total_devices"])
    col2.metric("Carbon Avoided", f"{result['total_carbon_avoided_kg']} kg CO₂e")
    col3.metric("Urban Mining Score", f"{result['urban_mining_score']}/100")

    # Mineral Breakdown Chart
    st.markdown("### 🔬 Recovered Critical Minerals (Grams)")
    minerals = list(result["recovered_minerals_g"].keys())
    weights = list(result["recovered_minerals_g"].values())

    if minerals:
        fig = go.Figure(
            data=[
                go.Bar(
                    x=minerals,
                    y=weights,
                    marker_color="#1f77b4",
                    text=[f"{w} g" for w in weights],
                    textposition="auto",
                )
            ]
        )
        fig.update_layout(
            title="Estimated Recoverable Mineral Weight by Type",
            xaxis_title="Mineral",
            yaxis_title="Grams Recovered",
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No minerals to display.")

    # Recommendations
    st.subheader("♻️ Responsible End-of-Life Management")
    for rec in st.session_state.recommendations:
        st.info(rec)

    if st.button("🗑️ Clear Inventory"):
        calculator.clear_inventory()
        st.rerun()

# --- History ---
st.divider()
st.subheader("📜 Historical Inventory Saves")
history = get_urban_mining_history()
if history:
    st.dataframe(pd.DataFrame(history), use_container_width=True)
