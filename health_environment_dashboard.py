import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from database import get_fitness_oauth_token, get_health_transport_metrics
from fitness_integration import handle_oauth_callback, fetch_and_process_activities, get_oauth_url

def render_health_environment_dashboard(user_id: str):
    st.title("🏃 Health vs. Environment")
    st.markdown("""
        Link your physical health with your environmental impact! 
        Connect your fitness apps to automatically log active transport and see how your 
        walking or cycling reduces your carbon footprint compared to driving.
    """)
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🔌 Connections")
        provider = "Strava"
        token = get_fitness_oauth_token(user_id, provider)
        
        if token:
            st.success(f"Connected to {provider}")
            
            if st.button("Sync Data"):
                with st.spinner("Syncing activities..."):
                    new_activities = fetch_and_process_activities(user_id, provider)
                    if new_activities > 0:
                        st.success(f"Successfully synced {new_activities} new activities!")
                    else:
                        st.info("No new activities found.")
        else:
            st.info(f"Not connected to {provider}")
            # Mock connection flow
            auth_url = get_oauth_url(provider)
            st.markdown(f"*(Mock Auth URL: {auth_url})*")
            if st.button(f"Connect to {provider}"):
                # Simulate redirect and callback
                with st.spinner("Authorizing..."):
                    if handle_oauth_callback(provider, "mock_auth_code_123", user_id):
                        st.success("Successfully authorized!")
                        st.rerun()
                        
    # Display Metrics and Chart
    metrics = get_health_transport_metrics(user_id)
    
    if metrics:
        df = pd.DataFrame(metrics)
        # Ensure date is datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Summaries
        st.markdown("---")
        st.subheader("📊 Your Impact")
        
        c1, c2, c3 = st.columns(3)
        total_calories = df['calories_burned'].sum()
        total_distance = df['distance_km'].sum()
        total_co2 = df['avoided_co2_kg'].sum()
        
        c1.metric("Total Calories Burned", f"{total_calories:,.0f} kcal")
        c2.metric("Total Active Distance", f"{total_distance:,.1f} km")
        c3.metric("Avoided CO2", f"{total_co2:,.2f} kg", delta=f"-{total_co2:,.2f} kg", delta_color="inverse")
        
        st.markdown("### 📈 Health Metrics vs CO2 Avoided")
        
        # Aggregate by date
        daily_df = df.groupby('date').agg({
            'duration_minutes': 'sum',
            'calories_burned': 'sum',
            'avoided_co2_kg': 'sum'
        }).reset_index()
        
        daily_df = daily_df.sort_values('date')
        
        # Dual-axis chart
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add bars for active minutes
        fig.add_trace(
            go.Bar(
                x=daily_df['date'],
                y=daily_df['duration_minutes'],
                name="Active Minutes",
                marker_color="#3b82f6",
                opacity=0.7
            ),
            secondary_y=False,
        )
        
        # Add line for avoided CO2
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=daily_df['avoided_co2_kg'],
                name="Avoided CO2 (kg)",
                mode='lines+markers',
                line=dict(color="#10b981", width=3),
                marker=dict(size=8)
            ),
            secondary_y=True,
        )
        
        fig.update_layout(
            title_text="Active Minutes vs. Avoided CO2",
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=50, b=20)
        )
        
        fig.update_yaxes(title_text="<b>Active Minutes</b>", secondary_y=False)
        fig.update_yaxes(title_text="<b>Avoided CO2 (kg)</b>", secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Raw Activity Data"):
            st.dataframe(df[['date', 'activity_type', 'duration_minutes', 'distance_km', 'calories_burned', 'avoided_co2_kg']].sort_values('date', ascending=False))
            
    else:
        st.info("No activity data found. Connect your provider and sync data to see your metrics here.")
