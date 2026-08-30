import streamlit as st
import pandas as pd
import datetime
from src.core.rate_limiter import CompositeRateLimiter
from src.core.api_auth import list_api_keys
from src.core.database_connection import database_connection
import os

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

st.set_page_config(page_title="API Usage Dashboard", page_icon="📊", layout="wide")

st.title("API Usage Dashboard 📊")
st.markdown("Monitor API usage, traffic, and rate limiting metrics.")

def get_admin_override():
    with st.expander("Admin override"):
        st.write("Modify rate limits for specific keys.")
        keys = list_api_keys()
        if not keys:
            st.warning("No API keys found.")
            return
        
        key_options = {f"{k['app_name']} ({k['key_prefix']})": k['id'] for k in keys}
        selected_key = st.selectbox("Select API Key", list(key_options.keys()))
        
        if selected_key:
            k_id = key_options[selected_key]
            current_limit = next(k['rate_limit'] for k in keys if k['id'] == k_id)
            new_limit = st.number_input("New Rate Limit (req/hr)", min_value=1, value=current_limit)
            
            if st.button("Update Limit"):
                with database_connection(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE api_keys SET rate_limit = ? WHERE id = ?", (new_limit, k_id))
                    conn.commit()
                st.success("Limit updated successfully!")

tabs = st.tabs(["Overview", "My Usage", "Admin Dashboard"])

with tabs[0]:
    st.header("Platform Overview")
    st.write("Welcome to the API Usage Dashboard. Here you can track how your applications consume the EcoBuddy REST API.")
    
with tabs[1]:
    st.header("My Usage")
    
    user_id = st.text_input("Enter your User ID to view your keys", "default_user")
    keys = list_api_keys(user_id=user_id)
    
    if not keys:
        st.info("No API keys found for this user.")
    else:
        st.write("Your active keys:")
        for k in keys:
            st.write(f"- **{k['app_name']}** (Limit: {k['rate_limit']}/hr) - Prefix: {k['key_prefix']}")
            
        selected_my_key = st.selectbox("Select key to view logs", [k['app_name'] for k in keys])
        if selected_my_key:
            k_id = next(k['id'] for k in keys if k['app_name'] == selected_my_key)
            stats = CompositeRateLimiter.get_usage_stats(key_id=k_id, limit=500)
            
            if stats:
                df = pd.DataFrame(stats)
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                
                # Chart
                st.subheader("Traffic over Time")
                df['status'] = df['status_code'].apply(lambda x: 'Allowed' if x == 200 else 'Blocked')
                chart_data = df.groupby([df['timestamp'].dt.floor('Min'), 'status']).size().unstack(fill_value=0)
                st.line_chart(chart_data)
                
                st.subheader("Recent Requests")
                st.dataframe(df)
            else:
                st.info("No usage data found for this key.")

with tabs[2]:
    st.header("Admin Dashboard")
    st.warning("Restricted Area - System Administrators Only")
    
    get_admin_override()
    
    st.subheader("System-Wide Traffic")
    stats = CompositeRateLimiter.get_usage_stats(limit=1000)
    
    if stats:
        df = pd.DataFrame(stats)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Top Endpoints")
            st.bar_chart(df['endpoint'].value_counts())
            
        with col2:
            st.write("Response Codes")
            st.bar_chart(df['status_code'].value_counts())
            
        st.write("Recent Global Requests")
        st.dataframe(df)
    else:
        st.info("No system-wide usage data available yet.")
