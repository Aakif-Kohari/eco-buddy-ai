"""
Sustainable Event Planner Page.
Streamlit page featuring an interactive event builder, footprint breakdown charts, and a vendor recommendation dashboard.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from event_footprint_calculator import EventFootprintCalculator
from green_vendor_matcher import GreenVendorMatcher
from database import save_event_plan, get_event_history

st.set_page_config(
    page_title="Sustainable Event Planner", page_icon="🎉", layout="wide"
)

st.title("🎉 Sustainable Event & Gathering Footprint Planner")
st.markdown(
    "Plan your next event with the environment in mind. Calculate emissions, discover green swaps, and find certified sustainable vendors."
)

matcher = GreenVendorMatcher()

# --- Input Section ---
st.subheader("📝 Event Details")
col1, col2 = st.columns(2)

with col1:
    guest_count = st.number_input(
        "Expected Guest Count", min_value=0, step=10, value=50
    )
    duration_hours = st.number_input(
        "Event Duration (Hours)", min_value=1.0, step=0.5, value=4.0
    )
    catering_type = st.selectbox(
        "Catering Style", ["Vegan", "Vegetarian", "Poultry", "Beef Heavy"]
    )
    waste_management = st.selectbox(
        "Waste Management Plan",
        ["Zero Waste/Compost", "Standard Recycling", "Landfill Heavy"],
    )

with col2:
    avg_travel_distance_km = st.number_input(
        "Avg. Guest Travel Distance (One-way km)", min_value=0.0, step=5.0, value=15.0
    )
    travel_mode = st.selectbox(
        "Primary Guest Travel Mode",
        [
            "Walking/Biking",
            "Public Transit",
            "Carpool",
            "Single Occupancy Vehicle",
            "Flight (Short)",
        ],
    )
    venue_type = st.selectbox(
        "Venue Type", ["Renewable Energy", "Standard Grid", "Outdoor Natural"]
    )

if st.button("🔍 Calculate Event Footprint", type="primary"):
    with st.spinner("Analyzing event parameters..."):
        calculator = EventFootprintCalculator(
            guest_count=guest_count,
            catering_type=catering_type,
            avg_travel_distance_km=avg_travel_distance_km,
            travel_mode=travel_mode,
            venue_type=venue_type,
            waste_management=waste_management,
            duration_hours=duration_hours,
        )
        result = calculator.calculate_footprint()
        st.session_state.event_result = result
        save_event_plan(guest_count, catering_type, result["total_emissions_kg"])
        st.success("Footprint calculated and saved!")

# --- Results Display ---
if "event_result" in st.session_state:
    result = st.session_state.event_result

    st.divider()
    st.subheader("📊 Carbon Footprint Breakdown")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Total Event Emissions", f"{result['total_emissions_kg']:,.1f} kg CO₂e"
        )
        st.metric(
            "Per Guest Emissions", f"{result['per_guest_emissions_kg']:.1f} kg CO₂e"
        )

    with col2:
        # Pie chart for breakdown
        labels = ["Catering", "Travel", "Venue", "Waste"]
        values = [
            result["breakdown"]["catering_kg"],
            result["breakdown"]["travel_kg"],
            result["breakdown"]["venue_kg"],
            result["breakdown"]["waste_kg"],
        ]

        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
        fig.update_layout(title="Emissions by Category", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 💡 Recommended Green Swaps")
    for swap in result["green_swaps"]:
        st.info(swap)

    st.divider()
    st.subheader("🤝 Sustainable Vendor Recommendations")

    # Map UI selections to matcher categories
    category_map = {"Catering Style": "catering", "Venue Type": "venue"}

    st.markdown("Select a category to find certified green vendors:")
    vendor_cat = st.selectbox("Vendor Category", ["Catering", "Venue", "Decorations"])

    # For demonstration, we require at least one positive certification
    req_certs = ["zero_waste"] if vendor_cat == "Catering" else ["renewable_energy"]

    if st.button("Find Vendors"):
        matched_vendors = matcher.match_vendors(req_certs, category=vendor_cat.lower())
        if matched_vendors:
            for v in matched_vendors:
                with st.container():
                    st.markdown(f"### 🌟 {v['name']}")
                    st.markdown(
                        f"**Certifications:** {', '.join(v['certifications']).replace('_', ' ').title()}"
                    )
                    st.markdown(f"**Rating:** ⭐ {v['rating']}/5.0")
                    st.markdown(v["description"])
                    st.markdown("---")
        else:
            st.warning(
                f"No vendors found matching the criteria for {vendor_cat}. Try broadening your search."
            )

# --- History ---
st.divider()
st.subheader("📜 Past Event Plans")
history = get_event_history()
if history:
    st.dataframe(pd.DataFrame(history), use_container_width=True)
else:
    st.info("No event plans saved yet.")
