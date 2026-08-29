import streamlit as st
from src.reporting.health_environment_dashboard import render_health_environment_dashboard

st.set_page_config(page_title="Health & Environment", page_icon="🏃", layout="wide")

if 'user_id' not in st.session_state or not st.session_state['user_id']:
    st.warning("Please sign in from the main app to view this dashboard.")
else:
    render_health_environment_dashboard(st.session_state['user_id'])
