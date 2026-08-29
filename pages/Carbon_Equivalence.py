import streamlit as st
import json
from src.carbon.carbon_equivalence import translate_footprint, EQUIVALENCE_FACTORS
from src.core.database import save_equivalence_preferences, get_equivalence_preferences
from src.core.api_auth import get_current_user

st.set_page_config(page_title="Carbon Equivalence", page_icon="⚖️", layout="wide")

def get_sidebar_equivalence_widget(footprint: float):
    """
    Exportable sidebar widget to display carbon equivalences.
    """
    st.sidebar.markdown("### ⚖️ Real-World Impact")
    
    if footprint <= 0:
        st.sidebar.info("Enter a positive footprint to see equivalences.")
        return
        
    user = get_current_user()
    region = "Global"
    top_metrics = []
    if user:
        prefs = get_equivalence_preferences(user["id"])
        if prefs:
            try:
                top_metrics = json.loads(prefs["top_metrics"])
                region = prefs["region"]
            except Exception:
                pass
                
    equivalences = translate_footprint(footprint, region, top_n=5)
    
    # If user has specific preferred metrics, we can override or just show the translated ones
    if top_metrics:
        equivalences = []
        for key in top_metrics[:3]:
            data = EQUIVALENCE_FACTORS.get(key)
            if data and data["kg_per_unit"] > 0:
                units = footprint / data["kg_per_unit"]
                units = round(units) if units > 100 else round(units, 1) if units > 10 else round(units, 2)
                equivalences.append({
                    "name": data["name"],
                    "units": units,
                    "icon": data["icon"]
                })
                
    for eq in equivalences[:3]:
        st.sidebar.markdown(f"**{eq['icon']} {eq['units']}** {eq['name']}")

def main():
    st.title("⚖️ Carbon Equivalence")
    st.markdown("Contextualize your carbon footprint with real-world metrics.")
    
    user = get_current_user()
    
    # Input
    col1, col2 = st.columns([1, 2])
    with col1:
        footprint = st.number_input("Enter CO₂ Footprint (kg)", min_value=0.0, value=100.0, step=10.0)
        
    st.markdown("### Your Impact Translates To:")
    
    # Load Preferences
    region = "Global"
    preferred_keys = []
    if user:
        prefs = get_equivalence_preferences(user["id"])
        if prefs:
            try:
                preferred_keys = json.loads(prefs["top_metrics"])
                region = prefs["region"]
            except Exception:
                pass
                
    if not preferred_keys:
        # Default translation if no preferences
        equivalences = translate_footprint(footprint, region, top_n=6)
    else:
        # Use preferred keys
        equivalences = []
        for key in preferred_keys:
            data = EQUIVALENCE_FACTORS.get(key)
            if data and data["kg_per_unit"] > 0:
                units = footprint / data["kg_per_unit"]
                units = round(units) if units > 100 else round(units, 1) if units > 10 else round(units, 2)
                equivalences.append({
                    "key": key,
                    "name": data["name"],
                    "units": units,
                    "icon": data["icon"]
                })
                
    # Display cards
    if equivalences:
        cols = st.columns(3)
        for i, eq in enumerate(equivalences):
            with cols[i % 3]:
                st.info(f"### {eq['icon']} {eq['units']}\n**{eq['name']}**")
    else:
        st.write("Enter a valid footprint above.")
        
    st.divider()
    
    # Personalization Section
    st.header("⚙️ Personalize Your Metrics")
    if not user:
        st.warning("Please log in to save your equivalence preferences.")
        return
        
    all_options = {k: f"{v['icon']} {v['name']}" for k, v in EQUIVALENCE_FACTORS.items()}
    
    with st.form("personalize_form"):
        st.write("Select up to 6 metrics you find most relatable:")
        selected = st.multiselect(
            "Preferred Metrics", 
            options=list(all_options.keys()), 
            format_func=lambda x: all_options[x],
            default=preferred_keys if preferred_keys else list(all_options.keys())[:3]
        )
        
        region_sel = st.selectbox("Region", ["Global", "US", "EU", "Asia"], index=["Global", "US", "EU", "Asia"].index(region) if region in ["Global", "US", "EU", "Asia"] else 0)
        
        submitted = st.form_submit_button("Save Preferences")
        if submitted:
            if len(selected) > 6:
                st.error("Please select a maximum of 6 metrics.")
            elif len(selected) == 0:
                st.error("Please select at least 1 metric.")
            else:
                success = save_equivalence_preferences(user["id"], json.dumps(selected), region_sel)
                if success:
                    st.success("Preferences saved successfully!")
                    st.rerun()
                else:
                    st.error("Failed to save preferences.")
                    

if __name__ == "__main__":
    main()
