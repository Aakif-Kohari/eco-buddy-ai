import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.core.database import save_iot_device, save_iot_reading_batch
from src.utils.device_registry import get_all_devices, get_device_by_id
from src.utils.iot_simulator import calculate_iot_savings, simulate_iot_energy_stream
from src.utils.units import format_quantity

st.set_page_config(page_title="Smart Devices", page_icon="📱", layout="wide")

st.title("📱 Smart Appliance IoT Simulator")
st.markdown(
    "Connect virtual smart devices to visualize real-time energy usage against your historical baseline."
)

# --- Sidebar Configuration ---
st.sidebar.header("⚙️ Simulation Settings")
devices = get_all_devices()
device_options = {d["name"]: d["id"] for d in devices}

selected_device_name = st.sidebar.selectbox(
    "Select Device", list(device_options.keys())
)
device_id = device_options[selected_device_name]
device_info = get_device_by_id(device_id)

days_to_simulate = st.sidebar.slider("Simulation Duration (Days)", 1, 7, 1)
baseline_daily_kwh = st.sidebar.number_input(
    "Your Historical Baseline (kWh/day)", min_value=0.1, step=0.1, value=5.0
)

# --- Main Content ---
st.subheader(f"Device: {device_info['name']}")
st.markdown(
    f"**Category:** {device_info['category']} | **Base Power:** {device_info['base_power_watts']}W | **Peak Power:** {device_info['peak_power_watts']}W"
)
st.info(device_info["description"])

if st.button("▶️ Run IoT Simulation", type="primary"):
    with st.spinner("Generating IoT telemetry data..."):
        readings = simulate_iot_energy_stream(device_id, days=days_to_simulate)
        savings = calculate_iot_savings(readings, baseline_daily_kwh, days_to_simulate)

        # Save to DB
        device_db_id = save_iot_device(device_id, device_info["name"])
        save_iot_reading_batch(device_db_id, readings)

        st.session_state.latest_readings = readings
        st.session_state.latest_savings = savings
        st.success("Simulation complete and telemetry saved!")

# --- Results Display ---
if "latest_readings" in st.session_state and "latest_savings" in st.session_state:
    readings = st.session_state.latest_readings
    savings = st.session_state.latest_savings

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Simulated Usage", f"{format_quantity(savings['simulated_total_kwh'], 'kWh')}"
    )
    col2.metric(
        "Baseline Usage", f"{format_quantity(savings['baseline_total_kwh'], 'kWh')}"
    )
    col3.metric(
        "Energy Savings",
        f"{format_quantity(savings['savings_kwh'], 'kWh')}",
        delta=f"-{savings['savings_pct']}%",
    )

    # Chart: Power Draw Over Time
    df = pd.DataFrame(readings)
    df["timestamp"] = pd.to_timedelta(df["hour_index"], unit="h")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["hour_index"],
            y=df["power_watts"],
            mode="lines",
            name="Simulated Power Draw (W)",
            line={"color": "#1f77b4", "width": 2},
        )
    )

    # Add baseline average line
    baseline_watts_avg = (baseline_daily_kwh * 1000) / 24
    fig.add_trace(
        go.Scatter(
            x=[0, df["hour_index"].max()],
            y=[baseline_watts_avg, baseline_watts_avg],
            mode="lines",
            name=f"Baseline Avg ({baseline_watts_avg:.1f} W)",
            line={"color": "#d62728", "dash": "dash"},
        )
    )

    fig.update_layout(
        title="IoT Power Draw vs Historical Baseline",
        xaxis_title="Hour",
        yaxis_title="Power (Watts)",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Data Table
    st.subheader("📊 Telemetry Data Preview")
    st.dataframe(df.head(24), use_container_width=True)  # Show first 24 hours
