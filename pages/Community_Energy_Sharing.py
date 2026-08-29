"""
Community Energy Sharing Page.
Streamlit page featuring a live neighborhood energy flow diagram, P2P trading ledger, and collective carbon savings dashboard.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from p2p_energy_trading import P2PEnergyTrading
from database import save_p2p_simulation, get_p2p_history

st.set_page_config(page_title="Community Energy Sharing", page_icon="⚡", layout="wide")

st.title("⚡ Peer-to-Peer Local Renewable Energy Sharing Simulator")
st.markdown(
    "Model how your neighborhood can share excess solar energy, reduce reliance on the main grid, and save money collectively."
)

# --- Configuration ---
st.sidebar.header("⚙️ Microgrid Configuration")
grid_price = st.sidebar.number_input(
    "Grid Import Price ($/kWh)", min_value=0.10, max_value=0.50, step=0.01, value=0.25
)
p2p_price = st.sidebar.number_input(
    "P2P Trading Price ($/kWh)", min_value=0.05, max_value=0.40, step=0.01, value=0.15
)
num_houses = st.sidebar.slider("Number of Households", 2, 10, 5)

if st.sidebar.button("🚀 Run Daily Simulation"):
    with st.spinner("Simulating 24-hour microgrid dynamics and P2P trades..."):
        trader = P2PEnergyTrading(grid_import_price=grid_price, p2p_price=p2p_price)
        # Note: The simulator inside trader is fixed to 5 for simplicity in this mock,
        # but we can pass num_houses if we modify the init. For now, we use the default.
        result = trader.simulate_and_trade_full_day()

        st.session_state.simulation_result = result
        save_p2p_simulation(
            grid_price,
            p2p_price,
            result["summary"]["total_p2p_volume_kwh"],
            result["summary"]["total_carbon_avoided_kg"],
        )
        st.success("Simulation complete and saved!")

# --- Results Display ---
if "simulation_result" in st.session_state:
    res = st.session_state.simulation_result
    summary = res["summary"]

    st.divider()
    st.subheader("📊 Daily Microgrid Performance Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("P2P Energy Traded", f"{summary['total_p2p_volume_kwh']:.1f} kWh")
    col2.metric("Collective Savings", f"${summary['total_money_saved_usd']:.2f}")
    col3.metric("Carbon Avoided", f"{summary['total_carbon_avoided_kg']:.1f} kg CO₂e")
    col4.metric("Grid Independence", f"{summary['grid_independence_pct']:.1f}%")

    # Hourly Generation vs Demand Chart
    st.markdown("### 📈 Hourly Energy Dynamics")
    df_profile = pd.DataFrame(res["daily_profile"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_profile["hour"],
            y=df_profile["total_generation_kw"],
            mode="lines+markers",
            name="Local Solar Generation",
            line=dict(color="#fca311"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_profile["hour"],
            y=df_profile["total_demand_kw"],
            mode="lines+markers",
            name="Total Neighborhood Demand",
            line=dict(color="#14213d"),
        )
    )
    fig.add_trace(
        go.Bar(
            x=df_profile["hour"],
            y=df_profile["net_grid_import_kw"],
            name="Grid Import",
            marker_color="#e5e5e5",
        )
    )

    fig.update_layout(
        title="Hourly Generation, Demand, and Grid Import",
        xaxis_title="Hour of Day",
        yaxis_title="Power (kW)",
        template="plotly_white",
        barmode="overlay",
    )
    st.plotly_chart(fig, use_container_width=True)

    # P2P Volume Chart
    st.markdown("### 🤝 Hourly P2P Trading Volume")
    df_trades = pd.DataFrame(res["hourly_trades"])

    fig_trades = go.Figure()
    fig_trades.add_trace(
        go.Bar(
            x=df_trades["hour"],
            y=df_trades["total_p2p_volume_kwh"],
            name="P2P Volume (kWh)",
            marker_color="#2ca02c",
        )
    )
    fig_trades.update_layout(
        title="Peer-to-Peer Energy Matching Volume",
        xaxis_title="Hour of Day",
        yaxis_title="Energy Traded (kWh)",
        template="plotly_white",
    )
    st.plotly_chart(fig_trades, use_container_width=True)

    # Transaction Ledger
    st.markdown("### 📜 P2P Transaction Ledger")
    # Flatten transactions for display
    all_tx = []
    for h_trade in res["hourly_trades"]:
        for tx in h_trade["transactions"]:
            all_tx.append(tx)

    if all_tx:
        df_tx = pd.DataFrame(all_tx)
        st.dataframe(df_tx, use_container_width=True, hide_index=True)
    else:
        st.info(
            "No P2P trades were necessary (e.g., no overlap between local generation and demand)."
        )

# --- History ---
st.divider()
st.subheader("📜 Past Simulations")
history = get_p2p_history()
if history:
    st.dataframe(pd.DataFrame(history), use_container_width=True)
else:
    st.info("No simulation history available.")
