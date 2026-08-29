"""
Home Renovation Carbon Page.
Streamlit page where users can input project dimensions, compare material alternatives side-by-side, and view a "Low-Carbon Renovation Score."
"""

import streamlit as st
import plotly.graph_objects as go
from renovation_carbon_estimator import RenovationCarbonEstimator
from sustainable_material_db import SustainableMaterialDB
from database import save_renovation_estimate, get_renovation_history

st.set_page_config(page_title="Home Renovation Carbon", page_icon="🔨", layout="wide")

st.title("🔨 Home Renovation & Construction Embodied Carbon Estimator")
st.markdown(
    "Make low-carbon choices for your home improvement projects by comparing the upfront embodied carbon of different materials."
)

db = SustainableMaterialDB()
materials = db.get_all_materials()

# --- Input Section ---
st.subheader("📐 Project Details")
col1, col2, col3 = st.columns(3)

with col1:
    material_key = st.selectbox(
        "Material Choice",
        options=materials,
        format_func=lambda x: db.get_material_display_name(x),
    )
with col2:
    volume = st.number_input(
        "Required Volume (cubic meters)", min_value=0.1, step=0.5, value=1.0
    )
with col3:
    distance = st.number_input(
        "Transport Distance (km)", min_value=0, step=10, value=50
    )

if st.button("🔍 Estimate Embodied Carbon"):
    try:
        estimator = RenovationCarbonEstimator(
            material_key=material_key, volume_m3=volume, transport_distance_km=distance
        )
        result = estimator.calculate_embodied_carbon()
        score = estimator.calculate_low_carbon_score(result["total_embodied_carbon_kg"])
        recs = estimator.get_green_swap_recommendations()

        st.session_state.renovation_result = {
            "result": result,
            "score": score,
            "recs": recs,
        }
        save_renovation_estimate(
            material_key, volume, result["total_embodied_carbon_kg"], score
        )
        st.success("Estimate calculated and saved!")
    except ValueError as e:
        st.error(str(e))

# --- Results Display ---
if "renovation_result" in st.session_state:
    res = st.session_state.renovation_result
    data = res["result"]

    st.divider()
    st.subheader(f"📊 Embodied Carbon Analysis: {data['material_name']}")

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Total Embodied Carbon", f"{data['total_embodied_carbon_kg']:,.1f} kg CO₂e"
    )
    col2.metric("Low-Carbon Score", f"{res['score']:.0f}/100")
    col3.metric("Recyclability", f"{data['recyclability_score']}/100")

    # Breakdown Chart
    fig = go.Figure(
        data=[
            go.Bar(
                name="Material Production",
                x=["Carbon Breakdown"],
                y=[data["material_carbon_kg"]],
                marker_color="#1f77b4",
            ),
            go.Bar(
                name="Transportation",
                x=["Carbon Breakdown"],
                y=[data["transport_carbon_kg"]],
                marker_color="#ff7f0e",
            ),
        ]
    )
    fig.update_layout(
        title="Upfront Carbon Breakdown",
        yaxis_title="kg CO₂e",
        template="plotly_white",
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 💡 Green Swap Recommendations")
    for rec in res["recs"]:
        st.info(rec)

    st.divider()
    st.subheader("🔄 Compare with Alternatives")
    st.markdown("See how your choice compares to other materials for the same volume:")

    comparison_data = []
    for mat_key in materials:
        try:
            est = RenovationCarbonEstimator(mat_key, volume, distance)
            res_data = est.calculate_embodied_carbon()
            comparison_data.append(
                {
                    "Material": res_data["material_name"],
                    "Total Carbon (kg)": res_data["total_embodied_carbon_kg"],
                    "Recyclability": res_data["recyclability_score"],
                    "Lifespan (yrs)": res_data["lifespan_years"],
                }
            )
        except ValueError:
            continue

    import pandas as pd

    df_comp = pd.DataFrame(comparison_data)
    # Highlight the lowest carbon option
    min_carbon = df_comp["Total Carbon (kg)"].min()

    def highlight_low_carbon(row):
        if row["Total Carbon (kg)"] == min_carbon:
            return ["background-color: #d4edda; font-weight: bold"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_comp.style.apply(highlight_low_carbon, axis=1),
        use_container_width=True,
        hide_index=True,
    )
