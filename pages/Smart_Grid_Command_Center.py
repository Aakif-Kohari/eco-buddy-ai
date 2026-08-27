import streamlit as st
import asyncio
import time
import pandas as pd
import threading
import sys
import os

# Ensure plugins can be imported if running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from plugins.smart_grid.engine import SmartGridSimulation

st.set_page_config(
    page_title="Smart Grid Command Center",
    page_icon="⚡",
    layout="wide"
)

# --- Session State Initialization ---
if "sim_engine" not in st.session_state:
    st.session_state.sim_engine = SmartGridSimulation(region="US-CA", speed_multiplier=3600.0) # 1 sec = 1 hour
    st.session_state.sim_thread = None
    st.session_state.is_running = False
    st.session_state.history_data = []

engine = st.session_state.sim_engine

def run_sim_in_thread():
    """Runs the asyncio simulation in a separate thread to prevent blocking Streamlit."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run for 24 'real' seconds (which is 24 simulated hours at 3600x)
    loop.run_until_complete(engine.run_simulation(duration_real_seconds=24.0))
    st.session_state.is_running = False
    loop.close()

# --- UI Layout ---
st.title("⚡ Smart Grid Command Center")
st.markdown("""
Welcome to the Enterprise IoT Smart Grid Simulator. 
This dashboard visualizes a fully simulated smart home where an **AI Optimizer** schedules devices 
(like EV chargers and batteries) to minimize carbon emissions based on real-time grid forecasts.
""")

col1, col2, col3, col4 = st.columns(4)

# Control Panel
with st.sidebar:
    st.header("Simulation Controls")
    
    region = st.selectbox("Grid Region", ["US-CA", "US-TX", "FR", "DE", "IN"], index=0)
    if region != engine.region and not st.session_state.is_running:
        st.session_state.sim_engine = SmartGridSimulation(region=region, speed_multiplier=3600.0)
        engine = st.session_state.sim_engine
        
    speed = st.slider("Simulation Speed (x)", 1, 7200, 3600, help="3600x means 1 real second = 1 simulated hour")
    if not st.session_state.is_running:
        engine.speed_multiplier = speed
        
    if st.button("▶️ Start 24-Hour Simulation", disabled=st.session_state.is_running):
        st.session_state.is_running = True
        st.session_state.history_data = [] # Reset history
        thread = threading.Thread(target=run_sim_in_thread)
        thread.start()
        st.session_state.sim_thread = thread
        st.rerun()
        
    if st.session_state.is_running:
        st.warning("Simulation is actively running...")
        if st.button("🛑 Force Stop"):
            engine.is_running = False
            st.session_state.is_running = False
            st.rerun()

# --- Dynamic Dashboard ---

# Placeholders for dynamic content
metrics_ph = st.empty()
chart_ph = st.empty()
devices_ph = st.empty()

def update_dashboard():
    """Renders the current state of the simulation."""
    time_struct = time.localtime(engine.sim_time)
    formatted_time = time.strftime("%H:%M:%S (Day %j)", time_struct)
    
    # 1. Top Metrics
    with metrics_ph.container():
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Simulated Time", formatted_time)
        m2.metric("Net Grid Power", f"{engine.net_power_kw:.2f} kW")
        
        # Get battery SOC
        batt = next((d for d in engine.devices if d.device_type == "BATTERY_STORAGE"), None)
        if batt:
            soc = (batt.current_charge_kwh / batt.capacity_kwh) * 100
            m3.metric("Battery SOC", f"{soc:.1f}%")
            
        # Get EV status
        ev = next((d for d in engine.devices if d.device_type == "EV_CHARGER"), None)
        if ev:
            ev_kwh = ev.session_delivered_kwh
            m4.metric("EV Charged", f"{ev_kwh:.1f} kWh")

    # 2. Collect Historical Data for Charts
    # We poll the devices' current state to build a dataframe
    row = {"time": formatted_time}
    for d in engine.devices:
        row[d.name] = d.current_state.power_kw
    row["Net Power"] = engine.net_power_kw
    
    st.session_state.history_data.append(row)
    
    # Keep last 100 points
    if len(st.session_state.history_data) > 100:
        st.session_state.history_data.pop(0)
        
    df = pd.DataFrame(st.session_state.history_data)
    
    # 3. Main Chart
    with chart_ph.container():
        st.subheader("Real-Time Power Flow (kW)")
        if not df.empty:
            st.line_chart(df.set_index("time"))

    # 4. Device Status Cards
    with devices_ph.container():
        st.subheader("Connected IoT Devices")
        cols = st.columns(len(engine.devices))
        for i, dev in enumerate(engine.devices):
            with cols[i]:
                color = "green" if dev.current_state.power_kw < 0 else "red" if dev.current_state.power_kw > 0 else "gray"
                st.markdown(f"**{dev.name}**")
                st.markdown(f"*{dev.device_type}*")
                st.markdown(f"Status: `{dev.current_state.status}`")
                st.markdown(f"Power: <span style='color:{color}'>**{dev.current_state.power_kw:.2f} kW**</span>", unsafe_allow_html=True)
                
                # Show extra metadata
                if dev.current_state.metadata:
                    st.json(dev.current_state.metadata)

# If running, auto-refresh the UI
if st.session_state.is_running:
    update_dashboard()
    time.sleep(1.0) # Refresh rate
    st.rerun()
else:
    # Render final state
    update_dashboard()
    st.success("Simulation complete or stopped. Adjust settings to run again.")

st.markdown("---")
st.markdown("### How the Optimizer Works")
st.markdown("""
Behind the scenes, the `GridOptimizer` runs every 10 simulated minutes. It queries the `SmartGridForecaster` 
for the next 12 hours of expected carbon intensity (the famous "Duck Curve") and solar irradiance. 

Using this forecast, it solves a scheduling problem:
1. **EV Charging** is paused during high-carbon evening peaks and shifted to cheap, low-carbon overnight or mid-day solar hours.
2. **Battery Walls** proactively charge when solar is abundant, and discharge into the home precisely when the grid carbon intensity spikes, sheltering the user from dirty energy.
""")
