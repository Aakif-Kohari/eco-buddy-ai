import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.energy.smart_building_iot_sim import SmartBuildingIoTSimulator
from src.energy.smart_building_logic import SmartBuildingLogic
from src.energy.smart_building_alerts import SmartBuildingAlerts

st.set_page_config(page_title="Smart Building IoT Command Center", layout="wide", page_icon="🏢")

st.markdown("""
<style>
    .sensor-card {
        background: linear-gradient(145deg, #1f2937, #111827);
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
        color: white;
        text-align: center;
        border-left: 4px solid #3b82f6;
    }
    .sensor-title { font-size: 16px; font-weight: 500; color: #9ca3af; text-transform: uppercase; }
    .sensor-value { font-size: 38px; font-weight: 700; color: #60a5fa; margin-top: 8px;}
    .alert-row { background: #ef4444; color: white; padding: 10px; border-radius: 8px; margin-bottom: 8px;}
    .warn-row { background: #f59e0b; color: white; padding: 10px; border-radius: 8px; margin-bottom: 8px;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def fetch_telemetry_batch():
    sim = SmartBuildingIoTSimulator(seed=datetime.datetime.now().second)
    devices = sim.generate_devices(count=80)
    # Generate last 24 hours of data
    df = sim.generate_telemetry(devices, hours=24)
    return devices, df

devices, telemetry_df = fetch_telemetry_batch()
logic = SmartBuildingLogic(telemetry_df)
alerts_engine = SmartBuildingAlerts()
alerts_engine.analyze_batch(telemetry_df)

score_dict = logic.calculate_building_score()

st.title("🏢 Smart Building IoT Command Center")
st.markdown("Real-time telemetry, carbon emissions tracking, and anomaly detection overlay for corporate real estate.")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"<div class='sensor-card'><div class='sensor-title'>Overall Efficiency Score</div><div class='sensor-value'>{score_dict['score']} / 100</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='sensor-card' style='border-left: 4px solid #10b981;'><div class='sensor-title'>Total Emissions (24h)</div><div class='sensor-value' style='color:#10b981;'>{score_dict['total_co2_kg']} kg</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='sensor-card' style='border-left: 4px solid #f59e0b;'><div class='sensor-title'>Total Energy (24h)</div><div class='sensor-value' style='color:#f59e0b;'>{score_dict['total_kwh']} kWh</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='sensor-card' style='border-left: 4px solid #ef4444;'><div class='sensor-title'>Active Anomalies</div><div class='sensor-value' style='color:#ef4444;'>{len(alerts_engine.alerts)}</div></div>", unsafe_allow_html=True)

st.markdown("<br><hr>", unsafe_allow_html=True)

col_chart1, col_chart2 = st.columns([2, 1])

with col_chart1:
    st.subheader("Time Series: Building Emissions Profile")
    ts_data = logic.get_time_series_data()
    fig1 = px.area(ts_data, x="timestamp", y="carbon_emissions_kg", 
                  title="Carbon Density Over Time", template="plotly_dark",
                  color_discrete_sequence=["#10b981"])
    st.plotly_chart(fig1, use_container_width=True)

with col_chart2:
    st.subheader("Energy Source Distribution")
    type_data = logic.get_device_type_aggregates()
    fig2 = px.pie(type_data, values="energy_kwh", names="type", hole=0.5,
                  title="kWh by Subsystem", template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Floor-by-Floor Breakdown")
floor_df = logic.get_floor_aggregates()

if not floor_df.empty:
    fig_bar = px.bar(floor_df, x="floor", y=["carbon_emissions_kg", "cost_usd"], barmode="group",
                    template="plotly_dark", title="Impact Assessment by Floor")
    st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("⚠️ Predictive Reliability Alerts")
alerts_df = alerts_engine.get_all_alerts()

if alerts_df.empty:
    st.success("No anomalies detected across the entire building stack. Systems nominal.")
else:
    for _, row in alerts_df.head(5).iterrows():
        alert_class = "alert-row" if row["level"] == "CRITICAL" else "warn-row"
        icon = "🚨" if row["level"] == "CRITICAL" else "⚠️"
        st.markdown(f"<div class='{alert_class}'><strong>{icon} {row['timestamp'].strftime('%H:%M')} | {row['device_id']}:</strong> {row['reason']}</div>", unsafe_allow_html=True)
    
    if len(alerts_df) > 5:
        st.write(f"... and {len(alerts_df)-5} more suppressed alerts.")
