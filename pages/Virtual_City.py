import streamlit as st
import sys
import os

# Ensure the components path is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_total_xp, get_assessments
from virtual_city_engine import VirtualCityEngine
from components.virtual_city import virtual_city

st.set_page_config(page_title="Virtual Eco-City", page_icon="🏙️", layout="wide")

st.title("🏙️ Your Virtual Eco-City")
st.markdown("Watch your city grow as you log carbon savings!")

# Ensure user is logged in
if "user_id" not in st.session_state:
    st.warning("Please log in from the main app to view your city.")
    st.stop()

user_id = st.session_state.user_id

# In our app, we might need to calculate total carbon saved to feed into the engine
# For simplicity, we can just compute it from assessments or an avoided_emissions log.
# Let's use a dummy query or calculate from assessments if needed, but for now we'll 
# query the state. If we want it to dynamically update, we can compute total footprint 
# vs baseline or just pull `carbon_saved_kg` if it's already updated elsewhere.
# Here we'll simulate calculating some total savings based on assessments if carbon_saved_kg is 0.

# Fetch assessments
assessments = get_assessments(user_id=user_id)
# Calculate a rough "savings" based on footprint vs a baseline of 15 kg per day, just for demo
total_savings = 0.0
for _, date, transport, distance, electricity, diet, flights, footprint, eco_score, _, trip_id in assessments:
    if footprint is not None:
        savings = 15.0 - footprint  # assume 15 is baseline
        if savings > 0:
            total_savings += savings

engine = VirtualCityEngine(user_id=user_id)

# Update state with calculated savings
engine.update_city_state(total_savings)

# Get current state
city_state = engine.get_state()
unlocked_assets = city_state.get("unlocked_assets", [])

st.metric("Total Carbon Saved", f"{city_state['carbon_saved_kg']:.1f} kg")

st.markdown("### Your 3D City")
st.markdown("Interact with your city using your mouse to rotate and zoom.")

# Render the custom React component
virtual_city(unlocked_assets=unlocked_assets, key="virtual_city_component")

st.markdown("### Unlocked Assets")
if not unlocked_assets:
    st.info("Log more sustainable actions to start unlocking assets for your city!")
else:
    cols = st.columns(min(len(unlocked_assets), 4))
    for i, asset in enumerate(unlocked_assets):
        with cols[i % 4]:
            icon = "🌳" if asset['type'] == 'flora' else "⚡" if asset['type'] == 'energy' else "🏠"
            st.markdown(f"**{icon} {asset['name']}**")
