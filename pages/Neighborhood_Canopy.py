import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd

from neighborhood_canopy_engine import NeighborhoodCanopyEngine
import database

st.set_page_config(
    page_title="Neighborhood Canopy Simulator",
    page_icon="🌳",
    layout="wide"
)

st.title("🌳 Neighborhood Canopy Simulator")
st.markdown("""
Discover the environmental health of your local area! See your neighborhood's current Green Canopy Percentage, 
and simulate the impact of planting trees on carbon drawdown and urban cooling.
""")

engine = NeighborhoodCanopyEngine()

address = st.text_input("Enter your street address or neighborhood:", "1600 Amphitheatre Pkwy, Mountain View, CA")

if address:
    # 1. Fetch baseline
    with st.spinner("Analyzing satellite imagery and calculating green canopy..."):
        baseline = engine.get_baseline_for_address(address)
    
    # 2. Display metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Green Canopy", f"{baseline.green_canopy_percentage}%")
    
    st.subheader("Interactive Canopy Map")
    # 3. Interactive Map
    m = folium.Map(location=[baseline.latitude, baseline.longitude], zoom_start=15)
    folium.Marker(
        [baseline.latitude, baseline.longitude],
        popup="Your Neighborhood",
        tooltip="Neighborhood Center"
    ).add_to(m)
    
    # Simple folium circle to denote the analyzed area
    folium.Circle(
        radius=500,
        location=[baseline.latitude, baseline.longitude],
        popup="Analysis Area",
        color="green",
        fill=True,
    ).add_to(m)
    
    st_folium(m, width=800, height=400)

    # 4. Simulation
    st.subheader("Simulation: Plant Trees")
    st.markdown("How many trees would you like to plant in your neighborhood?")
    added_trees = st.slider("Number of Trees", min_value=0, max_value=500, value=50, step=10)
    
    if added_trees > 0:
        projection = engine.project_carbon_sequestration(baseline.green_canopy_percentage, added_trees)
        
        col2.metric("Projected UHI Cooling", f"-{projection.temperature_reduction_c} °C")
        
        # Save target to DB
        with database.database_connection(database.DB_NAME) as conn:
            cursor = conn.cursor()
            # Insert baseline (ignore if exists)
            cursor.execute('''
                INSERT OR IGNORE INTO neighborhood_canopy_baselines (address, latitude, longitude, green_canopy_percentage)
                VALUES (?, ?, ?, ?)
            ''', (baseline.address, baseline.latitude, baseline.longitude, baseline.green_canopy_percentage))
            
            # Get baseline ID
            cursor.execute('SELECT id FROM neighborhood_canopy_baselines WHERE address = ?', (baseline.address,))
            row = cursor.fetchone()
            if row:
                baseline_id = row[0]
                # Insert target
                cursor.execute('''
                    INSERT INTO neighborhood_canopy_targets 
                    (baseline_id, added_trees, carbon_drawdown_10y, carbon_drawdown_20y, carbon_drawdown_50y)
                    VALUES (?, ?, ?, ?, ?)
                ''', (baseline_id, added_trees, projection.drawdown_10y_kg, projection.drawdown_20y_kg, projection.drawdown_50y_kg))
            conn.commit()

        # 5. Plotly Chart
        data = {
            "Timeframe": ["10 Years", "20 Years", "50 Years"],
            "Carbon Drawdown (kg CO2)": [
                projection.drawdown_10y_kg, 
                projection.drawdown_20y_kg, 
                projection.drawdown_50y_kg
            ]
        }
        df = pd.DataFrame(data)
        
        fig = px.bar(
            df, 
            x="Timeframe", 
            y="Carbon Drawdown (kg CO2)", 
            title="Projected Carbon Sequestration over Time",
            text="Carbon Drawdown (kg CO2)",
            color="Timeframe",
            color_discrete_sequence=px.colors.sequential.Greens[3:]
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
