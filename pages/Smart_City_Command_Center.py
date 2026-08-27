import streamlit as st
import pandas as pd
import time
from plugins.smart_city.engine import SmartCitySimulation
from plugins.smart_city.telemetry_city import CityTelemetry

st.set_page_config(page_title="Smart City Traffic Emissions Simulator", layout="wide", page_icon="🏙️")

st.title("🏙️ Smart City Command Center")
st.markdown("Monitor macroscopic city-wide traffic emissions using a real-time Agent-Based A* simulation engine.")

# Initialize Simulation in Session State
if "city_engine" not in st.session_state:
    # 5x5 blocks, 200m each = 1km x 1km downtown grid
    st.session_state.city_engine = SmartCitySimulation(blocks_x=5, blocks_y=5)
    st.session_state.telemetry = CityTelemetry(st.session_state.city_engine)
    st.session_state.sim_running = False

engine = st.session_state.city_engine
telemetry = st.session_state.telemetry

# Controls
st.sidebar.header("Simulation Controls")
spawn_count = st.sidebar.slider("Spawn Commuters", 10, 500, 100)
ev_rate = st.sidebar.slider("EV Adoption Rate", 0.0, 1.0, 0.2)

if st.sidebar.button("Spawn Traffic"):
    engine.spawn_random_traffic(spawn_count, ev_rate)

st.sidebar.markdown("---")

run_button = st.sidebar.button("Start Simulation")
stop_button = st.sidebar.button("Pause")
if run_button:
    st.session_state.sim_running = True
if stop_button:
    st.session_state.sim_running = False

# Layout
col_metrics, col_viz = st.columns([1, 2])

# Placeholder for real-time updates
metrics_placeholder = col_metrics.empty()
chart_placeholder = col_viz.empty()
map_placeholder = col_viz.empty()

def render_dashboard():
    snap = telemetry.get_snapshot()
    
    # Render Metrics
    with metrics_placeholder.container():
        st.subheader("Live Metrics")
        m1, m2 = st.columns(2)
        m1.metric("Active Vehicles", snap["metrics"]["active_vehicles"])
        m2.metric("Completed Trips", snap["metrics"]["finished_vehicles"])
        
        st.metric("Total Carbon Emissions (kg CO₂e)", f"{snap['metrics']['total_co2_kg']:.2f}")
        st.metric("Simulation Time (s)", f"{snap['time_seconds']:.1f}")

    # Render Map (Scatterplot)
    if snap["agents"]:
        df_agents = pd.DataFrame(snap["agents"])
        # Map EV vs ICE colors
        df_agents["color"] = df_agents["is_ev"].apply(lambda x: "#00FF00" if x else "#FF0000")
        
        with map_placeholder.container():
            st.subheader("Live Traffic Map (Green=EV, Red=ICE)")
            st.scatter_chart(
                df_agents,
                x="x",
                y="y",
                color="color",
                size="speed_kmh",
                height=500
            )
    else:
        map_placeholder.info("No active traffic. Use the sidebar to spawn vehicles.")

# Auto-refresh loop
if st.session_state.sim_running:
    # Run 10 ticks (seconds) per UI refresh to speed things up
    for _ in range(10):
        engine.tick(dt_seconds=1.0)
        
    render_dashboard()
    time.sleep(0.1)
    st.rerun()
else:
    render_dashboard()
