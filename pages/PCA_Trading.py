"""
PCA Trading Dashboard.
Streamlit page featuring a trading dashboard, price charts, and simulated P2P transactions.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from pca_trading_engine import PCATradingEngine
from local_exchange_market import LocalExchangeMarket
from database import get_pca_balance, update_pca_balance, record_pca_trade

st.set_page_config(page_title="PCA Trading", page_icon="📈", layout="wide")

st.title("📈 Personal Carbon Allowance (PCA) Trading")
st.markdown(
    "Manage your monthly carbon allowance and participate in the local peer-to-peer exchange market."
)

# Initialize session state for demo purposes
if "pca_engine" not in st.session_state:
    st.session_state.pca_engine = PCATradingEngine(user_id="demo_user")
    st.session_state.pca_engine.initialize_allowance(500.0)

if "market" not in st.session_state:
    st.session_state.market = LocalExchangeMarket()

# --- Sidebar: User Balance ---
st.sidebar.header("💼 Your Portfolio")
current_balance = st.session_state.pca_engine.get_balance("demo_user")
st.sidebar.metric("Current Allowance Balance", f"{current_balance:.1f} kg CO₂e")

# --- Main Dashboard ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 Market Price History (24h Simulation)")
    # Generate simulated price history
    prices = st.session_state.market.simulate_trading_day(24)
    hours = list(range(24))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=prices,
            mode="lines+markers",
            name="Price per Tonne (USD)",
            line=dict(color="#2ca02c", width=3),
            marker=dict(size=6),
        )
    )
    fig.update_layout(
        title="Local Exchange Market Price Dynamics",
        xaxis_title="Hour of Day",
        yaxis_title="Price (USD / tonne CO₂e)",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🏦 Market Snapshot")
    snapshot = st.session_state.market.get_market_snapshot()
    st.metric(
        "Current Price", f"${snapshot['current_price_per_tonne_usd']:.2f} / tonne"
    )
    st.metric("Market Supply", f"{snapshot['total_supply_kg']:,.0f} kg")
    st.metric("Market Demand", f"{snapshot['total_demand_kg']:,.0f} kg")
    st.info(
        f"Price Trend: {snapshot['price_trend'].capitalize()} | Volatility: {snapshot['volatility_index']}%"
    )

# --- Trading Interface ---
st.divider()
st.subheader("💱 Execute Peer-to-Peer Trade")

trade_col1, trade_col2 = st.columns(2)
with trade_col1:
    st.markdown("#### Buy Allowance")
    buy_amount = st.number_input(
        "Amount to Buy (kg CO₂e)", min_value=10.0, step=10.0, value=50.0, key="buy_amt"
    )
    buy_cost = (buy_amount / 1000.0) * snapshot["current_price_per_tonne_usd"]
    st.write(f"Estimated Cost: **${buy_cost:.2f}**")
    if st.button("Confirm Purchase", type="primary", key="btn_buy"):
        try:
            # Simulate buying from "market_maker"
            trade = st.session_state.pca_engine.execute_trade(
                buyer_id="demo_user",
                seller_id="market_maker",
                amount=buy_amount,
                price_per_tonne=snapshot["current_price_per_tonne_usd"],
            )
            record_pca_trade(
                "demo_user",
                "market_maker",
                buy_amount,
                snapshot["current_price_per_tonne_usd"],
                "buy",
            )
            st.session_state.market.update_market_conditions(
                buy_amount
            )  # Increase demand
            st.success(f"Successfully purchased {buy_amount} kg CO₂e allowance!")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

with trade_col2:
    st.markdown("#### Sell Allowance")
    sell_amount = st.number_input(
        "Amount to Sell (kg CO₂e)",
        min_value=10.0,
        max_value=current_balance,
        step=10.0,
        value=50.0,
        key="sell_amt",
    )
    sell_revenue = (sell_amount / 1000.0) * snapshot["current_price_per_tonne_usd"]
    st.write(f"Estimated Revenue: **${sell_revenue:.2f}**")
    if st.button("Confirm Sale", type="primary", key="btn_sell"):
        try:
            # Simulate selling to "market_maker"
            trade = st.session_state.pca_engine.execute_trade(
                buyer_id="market_maker",
                seller_id="demo_user",
                amount=sell_amount,
                price_per_tonne=snapshot["current_price_per_tonne_usd"],
            )
            record_pca_trade(
                "market_maker",
                "demo_user",
                sell_amount,
                snapshot["current_price_per_tonne_usd"],
                "sell",
            )
            st.session_state.market.update_market_conditions(
                -sell_amount
            )  # Increase supply
            st.success(f"Successfully sold {sell_amount} kg CO₂e allowance!")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

# --- Trade History ---
st.divider()
st.subheader("📜 Recent Trade History")
history = st.session_state.pca_engine.get_trade_history("demo_user")
if history:
    df = pd.DataFrame(history)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(
        df[
            [
                "timestamp",
                "buyer_id",
                "seller_id",
                "amount_kg",
                "total_cost_usd",
                "status",
            ]
        ],
        use_container_width=True,
    )
else:
    st.info("No trades executed yet.")
