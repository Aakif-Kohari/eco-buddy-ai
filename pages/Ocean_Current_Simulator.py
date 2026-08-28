import streamlit as st
import pandas as pd
import time
import random
import uuid
from plugins.ocean_current import WorldMapGrid, OceanCurrentSolver, LagrangianTracker, PlasticParticle

st.set_page_config(page_title="Global Ocean Current Simulator", layout="wide", page_icon="🌊")

st.title("🌊 Global Ocean Current & Microplastic Simulator")
st.markdown("A fluid dynamics engine simulating macro and microplastics drifting into major ocean gyres.")

# Session State Initialization
if "ocean_grid" not in st.session_state:
    grid = WorldMapGrid(lat_resolution_deg=2.0, lon_resolution_deg=2.0)
    solver = OceanCurrentSolver(grid)
    tracker = LagrangianTracker(grid, solver)
    
    st.session_state.ocean_grid = grid
    st.session_state.ocean_solver = solver
    st.session_state.ocean_tracker = tracker
    st.session_state.sim_days = 0.0
    st.session_state.sim_running = False

grid = st.session_state.ocean_grid
solver = st.session_state.ocean_solver
tracker = st.session_state.ocean_tracker

# Sidebar Controls
st.sidebar.header("Simulator Controls")
spawn_count = st.sidebar.slider("Spawn Coastal Plastics", 100, 1000, 500)

if st.sidebar.button("Emit Plastics from Coastlines"):
    zones = grid.get_coastal_emission_zones()
    if zones:
        for _ in range(spawn_count):
            lat, lon = random.choice(zones)
            # Add some jitter
            lat += random.uniform(-1.0, 1.0)
            lon += random.uniform(-1.0, 1.0)
            mass = random.uniform(0.1, 5.0) # kg
            p = PlasticParticle(str(uuid.uuid4()), lat, lon, mass)
            tracker.add_particle(p)
            
run_button = st.sidebar.button("Run Simulation (Years)")
if run_button:
    st.session_state.sim_running = not st.session_state.sim_running
    
# Layout
col1, col2 = st.columns([1, 2])

map_placeholder = col2.empty()
metrics_placeholder = col1.empty()

def render():
    with metrics_placeholder.container():
        st.subheader("Global Metrics")
        st.metric("Simulation Time (Days)", f"{st.session_state.sim_days:.1f}")
        st.metric("Active Particles (Floating)", sum(1 for p in tracker.particles if not p.sunk))
        st.metric("Sunk Particles (Microplastics)", sum(1 for p in tracker.particles if p.sunk))
        
        st.subheader("Gyre Accumulation (kg)")
        accum = tracker.get_gyre_accumulation()
        df_gyre = pd.DataFrame(list(accum.items()), columns=["Gyre", "Mass (kg)"])
        st.dataframe(df_gyre)
        
    if tracker.particles:
        active = [p for p in tracker.particles if not p.sunk]
        if active:
            df = pd.DataFrame([{"lat": p.lat, "lon": p.lon, "mass": p.current_mass_kg} for p in active])
            with map_placeholder.container():
                st.subheader("Live Plastic Drift Map")
                # Using map layout for lat/lon plotting
                st.map(df, size="mass", color="#FF0000")
        else:
            map_placeholder.info("All plastics have sunk to the ocean floor.")
    else:
        map_placeholder.info("No plastics in the ocean. Use the sidebar to emit.")

if st.session_state.sim_running:
    # 1 tick = 30 days of simulation time to make things fast
    dt_seconds = 30 * 86400.0
    solver.step_simulation(dt_seconds)
    tracker.tick(dt_seconds, uv_index=8.0, surface_temp_c=25.0)
    st.session_state.sim_days += 30.0
    
    render()
    time.sleep(0.1)
    st.rerun()
else:
    render()
