import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

import database as db

def render_energy_tracker(user_id: int):
    st.markdown("<div class='section-header'>📈 Energy Usage Tracker</div>", unsafe_allow_html=True)
    st.markdown("Record your daily or monthly electricity and gas consumption to visualize trends over time.", unsafe_allow_html=True)

    with st.expander("➕ Log New Reading", expanded=False):
        with st.form("energy_reading_form"):
            c1, c2, c3 = st.columns(3)
            
            record_date = c1.date_input("Date", value=date.today())
            electricity_kwh = c2.number_input("Electricity (kWh)", min_value=0.0, value=0.0, step=0.1)
            gas_kwh = c3.number_input("Gas (kWh or equivalent)", min_value=0.0, value=0.0, step=0.1)
            
            submit = st.form_submit_button("Save Reading")
            
            if submit:
                success = db.add_energy_record(
                    user_id=user_id,
                    electricity_kwh=electricity_kwh,
                    gas_kwh=gas_kwh,
                    record_date=record_date.isoformat()
                )
                if success:
                    st.success("Energy reading saved successfully!")
                    st.rerun()
                else:
                    st.error("Failed to save energy reading.")

    records = db.get_energy_records(user_id)
    
    if records:
        df = pd.DataFrame(records)
        df['record_date'] = pd.to_datetime(df['record_date'])
        df = df.sort_values('record_date')
        
        st.markdown("### 📊 Consumption Trends")
        
        # Plotting the electricity and gas usage
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['record_date'], 
            y=df['electricity_kwh'],
            mode='lines+markers',
            name='Electricity (kWh)',
            line=dict(color='#fbbf24', width=3),
            marker=dict(size=8)
        ))
        
        fig.add_trace(go.Scatter(
            x=df['record_date'], 
            y=df['gas_kwh'],
            mode='lines+markers',
            name='Gas (kWh)',
            line=dict(color='#ef4444', width=3),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title="Energy Consumption Over Time",
            xaxis_title="Date",
            yaxis_title="Energy (kWh)",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Data table
        with st.expander("📋 View Data Table"):
            display_df = df[['record_date', 'electricity_kwh', 'gas_kwh']].copy()
            display_df['record_date'] = display_df['record_date'].dt.strftime('%Y-%m-%d')
            display_df = display_df.rename(columns={
                'record_date': 'Date',
                'electricity_kwh': 'Electricity (kWh)',
                'gas_kwh': 'Gas (kWh)'
            })
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No energy readings found. Log your first reading to see trends!")
