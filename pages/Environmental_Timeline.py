"""Streamlit page for Environmental Timeline."""

import streamlit as st
from src.utils.environmental_timeline import render_environmental_timeline

user_id = st.session_state.get("user_id") or 1
render_environmental_timeline(user_id=user_id)
