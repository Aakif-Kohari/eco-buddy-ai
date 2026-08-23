"""
Sustainable Travel Planner Page.
Streamlit page allowing users to input multi-city trips and view side-by-side comparisons of itinerary options.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from multimodal_router import MultimodalRouter
from database import save_travel_itinerary

st.set_page_config(page_title="Sustainable Travel", page_icon="✈️", layout="wide")

st.title("✈️ AI-Powered Sustainable Travel Itinerary Optimizer")
st.markdown(
    "Plan multi-city trips and discover lower-carbon, cost-effective multi-modal routing alternatives."
)

router = MultimodalRouter()

# --- Input Section ---
st.subheader("🗺️ Define Your Journey Legs")
st.markdown(
    "Add each segment of your trip. The optimizer will evaluate flights, trains, buses, and cars."
)

if "journey_legs" not in st.session_state:
    st.session_state.journey_legs = []

with st.form("add_leg_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        origin_dest = st.text_input("Route (e.g., London to Paris)")
    with col2:
        distance = st.number_input("Distance (km)", min_value=10, step=50, value=300)
    with col3:
        mode = st.selectbox(
            "Planned Transport Mode",
            ["flight_short", "flight_long", "train", "bus", "ice_car", "ev_car"],
            format_func=lambda x: x.replace("_", " ").title(),
        )

    if st.form_submit_button("Add Leg"):
        if origin_dest:
            st.session_state.journey_legs.append(
                {"route": origin_dest, "distance_km": distance, "mode": mode}
            )
            st.success(f"Added: {origin_dest}")
            st.rerun()

# Display current legs
if st.session_state.journey_legs:
    df_legs = pd.DataFrame(st.session_state.journey_legs)
    st.dataframe(df_legs, use_container_width=True)

    col_clear, col_optimize = st.columns([1, 3])
    if col_clear.button("Clear All"):
        st.session_state.journey_legs = []
        st.rerun()

    if col_optimize.button("🚀 Optimize Itinerary", type="primary"):
        with st.spinner(
            "Calculating multi-modal alternatives and carbon footprints..."
        ):
            report = router.generate_comprehensive_report(st.session_state.journey_legs)
            st.session_state.travel_report = report

            # Save to DB
            save_travel_itinerary(st.session_state.journey_legs, report)
            st.success("Itinerary optimized and saved!")

# --- Results Section ---
if "travel_report" in st.session_state:
    report = st.session_state.travel_report
    summary = report["optimization_summary"]

    st.divider()
    st.subheader("📊 Itinerary Comparison")

    # Comparison Metrics
    comp_col1, comp_col2, comp_col3 = st.columns(3)

    # Helper to display metric with delta
    def display_comparison(label, orig_val, green_val, unit):
        delta = round(green_val - orig_val, 2)
        comp_col1.metric(f"Original {label}", f"{orig_val} {unit}")
        comp_col2.metric(
            f"Greenest {label}",
            f"{green_val} {unit}",
            delta=f"{delta} {unit}",
            delta_color="normal" if delta < 0 else "inverse",
        )

    display_comparison(
        "Carbon",
        summary["original"]["total_carbon_kg"],
        summary["greenest"]["total_carbon_kg"],
        "kg CO₂e",
    )
    display_comparison(
        "Cost",
        summary["original"]["total_cost_usd"],
        summary["cheapest"]["total_cost_usd"],
        "USD",
    )
    display_comparison(
        "Time",
        summary["original"]["total_time_hours"],
        summary["fastest"]["total_time_hours"],
        "Hours",
    )

    # Stacked Bar Chart
    st.markdown("### Footprint Breakdown by Option")
    categories = ["Original", "Greenest", "Cheapest", "Fastest"]
    carbon_vals = [
        summary[k]["total_carbon_kg"]
        for k in ["original", "greenest", "cheapest", "fastest"]
    ]
    cost_vals = [
        summary[k]["total_cost_usd"]
        for k in ["original", "greenest", "cheapest", "fastest"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Carbon (kg CO₂e)", x=categories, y=carbon_vals, marker_color="#2ca02c"
        )
    )
    # Normalize cost for visualization (divide by 10 to fit on same scale roughly, or use secondary axis)
    # Using secondary axis for clarity
    fig.update_layout(
        title="Carbon Footprint Comparison (Lower is Better)",
        xaxis_title="Routing Option",
        yaxis_title="kg CO₂e",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Modal Shift Opportunities
    st.divider()
    st.subheader("💡 Modal Shift Opportunities")
    shifts = report["modal_shift_opportunities"]

    if shifts:
        st.success(
            f"By shifting modes, you can save an additional **{report['total_potential_carbon_savings_kg']} kg CO₂e**!"
        )
        for shift in shifts:
            st.markdown(f"""
            **{shift["distance_km"]} km Segment**
            - **Shift:** {shift["original_mode"].replace("_", " ").title()} ➔ {shift["recommended_mode"].replace("_", " ").title()}
            - **Carbon Saved:** {shift["carbon_saved_kg"]} kg CO₂e
            - **Cost Difference:** ${shift["cost_difference_usd"]}
            - **Time Difference:** {shift["time_difference_hours"]} hours
            """)
    else:
        st.info(
            "Your current itinerary is already highly optimized for low carbon emissions!"
        )
