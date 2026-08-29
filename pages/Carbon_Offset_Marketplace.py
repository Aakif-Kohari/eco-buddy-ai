"""
Page: Carbon Offset Marketplace
Browse, purchase, and track verified carbon offset projects.
"""

import streamlit as st
from styles.theme import apply_theme
from carbon_offset_marketplace import render_carbon_offset_marketplace

st.set_page_config(page_title="Carbon Offset Marketplace", page_icon="🌍", layout="wide")
apply_theme()
render_carbon_offset_marketplace()
