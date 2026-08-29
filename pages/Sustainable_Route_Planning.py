import streamlit as st
import pandas as pd
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.carbon.vehicle_emissions_data import VehicleEmissionsData
from src.utils.route_planning_engine import RoutePlanningEngine
from src.utils.logistics_optimization_service import LogisticsOptimizationService

st.set_page_config(page_title="Sustainable Logistics Fleet Optimizer", layout="wide", page_icon="🚚")

st.markdown("""
<style>
    .log-card {
        background: #1e293b;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #10b981;
        margin-bottom: 20px;
        color: white;
    }
    .val-large { font-size: 32px; font-weight: bold; color: #4ade80; }
    .val-warn { font-size: 32px; font-weight: bold; color: #f87171; }
    .val-neutral { font-size: 32px; font-weight: bold; color: #60a5fa; }
</style>
""", unsafe_allow_html=True)

st.title("🚚 Sustainable Logistics Fleet Optimizer")
st.write("Visualize and deploy AI-optimized multimodal routes to dramatically reduce your commercial fleet's supply chain footprint.")

# Generate Graph
@st.cache_data
def get_graph_and_engine():
    g = VehicleEmissionsData.generate_city_graph(num_nodes=15, seed=77)
    engine = RoutePlanningEngine(g)
    return g, engine

graph, engine = get_graph_and_engine()

# Configure Service
service = LogisticsOptimizationService(engine)

# Setup Jobs
col_setup, col_dash = st.columns([1, 2])

with col_setup:
    st.subheader("Route Dispatch")
    start_node = st.selectbox("Origin Hub", graph["nodes"], index=0)
    end_node = st.selectbox("Destination Hub", graph["nodes"], index=len(graph["nodes"])-1)
    
    if st.button("Calculate Optimal Zero-Carbon Route", type="primary"):
        st.session_state["active_route"] = engine.find_safest_eco_path(start_node, end_node)

with col_dash:
    if "active_route" in st.session_state:
        route = st.session_state["active_route"]
        if route["status"] == "success":
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<div class='log-card'>Distance<br><span class='val-neutral'>{route['total_dist_km']} km</span></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='log-card'>Emissions<br><span class='val-large'>{route['total_co2_kg']} kg</span></div>", unsafe_allow_html=True)
            with c3:
                # Comparison (Assuming ICE VAN)
                ice_van = route['total_dist_km'] * 0.25
                saved = ice_van - route['total_co2_kg']
                st.markdown(f"<div class='log-card' style='border-left: 5px solid #fbbf24;'>CO2 Avoided<br><span class='val-neutral'>⬇ {saved:.1f} kg</span></div>", unsafe_allow_html=True)
            
            st.subheader("Detailed Itinerary")
            df = pd.DataFrame(route["path"])
            st.dataframe(df.style.highlight_min(subset=['co2_kg'], color='darkgreen'))
        else:
            st.error(route["message"])

st.markdown("---")
st.subheader("Fleet Batch Processing Simulation")

if st.button("Generate & Optimize 50 Random Fleet Deliveries"):
    for _ in range(50):
        import random
        service.add_delivery_job(random.choice(graph["nodes"]), random.choice(graph["nodes"]))
        
    with st.spinner("Processing optimization matrix..."):
        batch_res = service.optimize_fleet()
        
    st.success("Batch Complete!")
    
    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("Total Jobs", batch_res["jobs_processed"])
    rc2.metric("Total Emissions (Optimized)", f"{batch_res['total_optimized_co2_kg']} kg", f"-{batch_res['savings_percentage']}% vs ICE Baseline")
    rc3.metric("Carbon Eliminated", f"{batch_res['total_co2_saved_kg']} kg")
