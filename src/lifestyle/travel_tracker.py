import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from src.utils.marketplace import EMISSION_FACTORS, calculate_trip_emissions

from src.core import database as db

def render_travel_tracker(user_id: int):
    st.markdown("---")
    st.markdown("<div class='section-header'>🗺️ Travel Footprint Tracker</div>", unsafe_allow_html=True)
    st.markdown("Log your trips to estimate and track emissions generated through different modes of transportation over time.", unsafe_allow_html=True)

    with st.expander("➕ Log New Trip", expanded=False):
        with st.form("travel_reading_form"):
            c1, c2 = st.columns(2)
            
            record_date = c1.date_input("Date", value=date.today())
            mode = c2.selectbox("Mode of Transport", list(EMISSION_FACTORS.keys()))
            
            c3, c4 = st.columns(2)
            distance_km = c3.number_input("Distance (km)", min_value=0.1, value=10.0, step=1.0)
            passengers = c4.number_input("Passengers", min_value=1, value=1, step=1)
            
            submit = st.form_submit_button("Save Trip")
            
            if submit:
                # Calculate emissions
                try:
                    emissions_kg = calculate_trip_emissions(distance_km, mode, passengers)
                    success = db.add_travel_record(
                        user_id=user_id,
                        record_date=record_date.isoformat(),
                        mode=mode,
                        distance_km=distance_km,
                        passengers=passengers,
                        emissions_kg=emissions_kg
                    )
                    if success:
                        st.success(f"Trip saved! Estimated emissions: {emissions_kg:.2f} kg CO2e")
                        st.rerun()
                    else:
                        st.error("Failed to save trip.")
                except Exception as e:
                    st.error(f"Error calculating emissions: {e}")

    records = db.get_travel_records(user_id)
    
    if records:
        df = pd.DataFrame(records)
        df['record_date'] = pd.to_datetime(df['record_date'])
        
        st.markdown("### 📊 Footprint History")
        
        # Aggregate by date for the timeline
        df_daily = df.groupby('record_date', as_index=False)['emissions_kg'].sum()
        df_daily = df_daily.sort_values('record_date')
        
        fig = px.bar(
            df_daily, 
            x='record_date', 
            y='emissions_kg',
            title='Daily Travel Emissions (kg CO2e)',
            labels={'record_date': 'Date', 'emissions_kg': 'Emissions (kg)'},
            color='emissions_kg', 
            color_continuous_scale='Reds'
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Breakdown by mode
        df_mode = df.groupby('mode', as_index=False)['emissions_kg'].sum()
        fig_pie = px.pie(
            df_mode, 
            names='mode', 
            values='emissions_kg',
            title='Total Emissions by Transport Mode',
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Teal
        )
        fig_pie.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Data table
        with st.expander("📋 View All Trips"):
            display_df = df[['record_date', 'mode', 'distance_km', 'passengers', 'emissions_kg']].copy()
            display_df['record_date'] = display_df['record_date'].dt.strftime('%Y-%m-%d')
            display_df['emissions_kg'] = display_df['emissions_kg'].round(2)
            display_df = display_df.sort_values('record_date', ascending=False)
            display_df = display_df.rename(columns={
                'record_date': 'Date',
                'mode': 'Mode',
                'distance_km': 'Distance (km)',
                'passengers': 'Passengers',
                'emissions_kg': 'Emissions (kg CO2e)'
            })
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No trips logged yet. Log a trip to see your travel footprint!")
