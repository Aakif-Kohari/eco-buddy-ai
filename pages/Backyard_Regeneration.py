"""
Backyard Regeneration Page.
Streamlit page where users can log their garden size, crops, and composting habits to view their "Regeneration Score".
"""

import streamlit as st
import plotly.graph_objects as go
from home_agriculture_tracker import HomeAgricultureTracker
from sequestration_calculator import SequestrationCalculator
from database import save_regeneration_log, get_regeneration_history

st.set_page_config(page_title="Backyard Regeneration", page_icon="🌻", layout="wide")

st.title("🌻 Regenerative Home Food Production & Sequestration Estimator")
st.markdown(
    "Quantify the positive climate impact of your backyard garden, composting, and regenerative landscaping practices."
)

# --- Input Section ---
st.sidebar.header("🏡 Backyard Profile")
area = st.sidebar.number_input(
    "Total Garden/Growing Area (sqm)", min_value=0.0, step=1.0, value=10.0
)
crops = st.sidebar.multiselect(
    "Crops Grown",
    options=["Tomatoes", "Lettuce", "Carrots", "Potatoes", "Herbs", "Berries"],
    default=["Tomatoes", "Herbs"],
)
composting = st.sidebar.checkbox("I Compost Food Scraps", value=True)
lawn_converted = st.sidebar.number_input(
    "Lawn Area Converted to Garden/Native Plants (sqm)",
    min_value=0.0,
    step=1.0,
    value=5.0,
)
perennials = st.sidebar.checkbox(
    "I Have Fruit Trees or Deep-Rooted Perennials", value=False
)

if st.sidebar.button("🔍 Calculate Regeneration Impact"):
    ag_tracker = HomeAgricultureTracker(
        garden_area_sqm=area, crops_grown=crops, composting=composting
    )
    ag_result = ag_tracker.calculate_avoided_emissions()

    seq_calc = SequestrationCalculator(
        composting=composting,
        lawn_converted_sqm=lawn_converted,
        has_perennials=perennials,
    )
    seq_result = seq_calc.calculate_sequestration()

    score = ag_tracker.get_regeneration_score(
        ag_result["total_avoided_emissions_kg"], seq_result["total_sequestered_kg"]
    )
    recs = seq_calc.get_practice_recommendations()

    st.session_state.regeneration_result = {
        "ag": ag_result,
        "seq": seq_result,
        "score": score,
        "recs": recs,
    }
    save_regeneration_log(area, len(crops), score)
    st.success("Regeneration impact calculated and saved!")

# --- Results Display ---
if "regeneration_result" in st.session_state:
    res = st.session_state.regeneration_result

    st.divider()
    st.subheader("🌟 Your Backyard Regeneration Score")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Regeneration Score", f"{res['score']:.0f}/100")
        st.markdown("*Based on emissions avoided + carbon sequestered.*")

    with col2:
        # Gauge chart for score
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=res["score"],
                domain={"x": [0, 1], "y": [0, 1]},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "#2ca02c"},
                    "steps": [
                        {"range": [0, 33], "color": "#f0f0f0"},
                        {"range": [33, 66], "color": "#d4edda"},
                        {"range": [66, 100], "color": "#c3e6cb"},
                    ],
                },
            )
        )
        fig_gauge.update_layout(height=200, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("### 🥬 Emissions Avoided (Supply Chain)")
        st.metric(
            "Total Avoided", f"{res['ag']['total_avoided_emissions_kg']} kg CO₂e/year"
        )
        for crop, val in res["ag"]["crop_breakdown_kg"].items():
            st.markdown(f"- {crop.title()}: {val} kg")

    with col4:
        st.markdown("### 🌱 Carbon Sequestered (Soil)")
        st.metric(
            "Total Sequestered", f"{res['seq']['total_sequestered_kg']} kg CO₂e/year"
        )
        st.markdown(f"- Composting: {res['seq']['composting_kg']} kg")
        st.markdown(f"- Lawn Conversion: {res['seq']['lawn_conversion_kg']} kg")
        st.markdown(f"- Perennials: {res['seq']['perennials_kg']} kg")

    st.divider()
    st.subheader("💡 Next Steps for Your Yard")
    for rec in res["recs"]:
        st.info(rec)
