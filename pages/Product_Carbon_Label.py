"""
Product Carbon Label Generator Page.
Streamlit page for inputting product data and viewing a visual PCF label and supply chain breakdown.
"""

import streamlit as st
import plotly.graph_objects as go
from pcf_label_generator import PCFLabelGenerator
from supply_chain_transparency import SupplyChainTransparency
from database import save_pcf_label

st.set_page_config(page_title="Product Carbon Label", page_icon="🏷️", layout="wide")

st.title("🏷️ Product Carbon Footprint (PCF) Label Generator")
st.markdown(
    "Estimate the embodied carbon of your product and generate a standardized transparency label."
)

pcf_gen = PCFLabelGenerator()
sc_transparency = SupplyChainTransparency()

# --- Input Section ---
st.subheader("📦 Product Details")
col1, col2 = st.columns(2)

with col1:
    product_name = st.text_input("Product Name", value="My Sustainable Widget")
    st.markdown("#### Materials")
    mat1_name = st.selectbox(
        "Material 1", ["plastic", "metal", "wood", "glass", "paper"], index=2
    )
    mat1_weight = st.number_input(
        "Weight (kg)", min_value=0.0, step=0.1, value=0.5, key="w1"
    )

    mat2_name = st.selectbox(
        "Material 2 (Optional)", ["none", "plastic", "metal", "wood", "glass", "paper"]
    )
    mat2_weight = (
        st.number_input("Weight (kg)", min_value=0.0, step=0.1, value=0.0, key="w2")
        if mat2_name != "none"
        else 0.0
    )

with col2:
    st.markdown("#### Manufacturing & Transport")
    energy_kwh = st.number_input(
        "Manufacturing Energy (kWh)", min_value=0.0, step=1.0, value=10.0
    )
    grid_factor = st.slider(
        "Grid Carbon Intensity (kg CO2e/kWh)", 0.1, 1.0, 0.4, step=0.1
    )

    distance_km = st.number_input(
        "Transport Distance (km)", min_value=0, step=100, value=500
    )
    transport_mode = st.selectbox("Transport Mode", ["truck", "ship", "air"])

# --- Supply Chain Transparency Inputs ---
st.divider()
st.subheader("🔍 Supply Chain Transparency")
transparency_inputs = {}
for stage in SupplyChainTransparency.STAGES:
    col_a, col_b = st.columns(2)
    with col_a:
        data_prov = st.checkbox(
            f"Data provided for {stage.replace('_', ' ').title()}",
            value=True,
            key=f"data_{stage}",
        )
    with col_b:
        cert = st.selectbox(
            f"Certification for {stage.replace('_', ' ').title()}",
            ["none", "Fairtrade", "FSC", "ISO14001", "Cradle2Cradle"],
            key=f"cert_{stage}",
        )
    transparency_inputs[stage] = {"data_provided": data_prov, "certification": cert}

# --- Generation ---
if st.button("🏷️ Generate PCF Label", type="primary"):
    materials = [{"name": mat1_name, "weight_kg": mat1_weight}]
    if mat2_name != "none":
        materials.append({"name": mat2_name, "weight_kg": mat2_weight})

    label = pcf_gen.generate_label(
        product_name=product_name,
        materials=materials,
        manufacturing_energy_kwh=energy_kwh,
        transport_distance_km=distance_km,
        transport_mode=transport_mode,
    )

    stage_evals = [
        sc_transparency.evaluate_stage(
            stage, inputs["data_provided"], inputs["certification"]
        )
        for stage, inputs in transparency_inputs.items()
    ]
    transparency_score = sc_transparency.calculate_overall_score(stage_evals)

    st.session_state.generated_label = label
    st.session_state.transparency_score = transparency_score

    # Save to DB
    save_pcf_label(product_name, label, transparency_score)
    st.success("Label generated and saved!")

# --- Output Display ---
if "generated_label" in st.session_state:
    label = st.session_state.generated_label
    score = st.session_state.transparency_score

    st.divider()
    st.subheader("📊 Generated Sustainability Label")

    # Visual Label Card
    st.markdown(
        f"""
    <div style="border: 3px solid #2ca02c; border-radius: 10px; padding: 20px; background-color: #f0fdf4;">
        <h2 style="color: #166534; margin: 0;">🌱 {label["product_name"]}</h2>
        <h1 style="color: #166534; font-size: 48px; margin: 10px 0;">{label["total_pcf_kg_co2e"]} <span style="font-size: 24px;">kg CO₂e</span></h1>
        <p style="color: #166534;"><strong>Carbon Grade:</strong> <span style="font-size: 24px; font-weight: bold; background-color: #2ca02c; color: white; padding: 2px 8px; border-radius: 4px;">{label["grade"]}</span></p>
        <p style="color: #166534; font-size: 14px;">{label["methodology"]}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Breakdown Chart
    cols = st.columns(2)
    with cols[0]:
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=["Materials", "Manufacturing", "Transport"],
                    values=[
                        label["breakdown"]["materials_kg_co2e"],
                        label["breakdown"]["manufacturing_kg_co2e"],
                        label["breakdown"]["transport_kg_co2e"],
                    ],
                    hole=0.4,
                )
            ]
        )
        fig.update_layout(title="Carbon Footprint Breakdown", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with cols[1]:
        st.markdown(
            f"### 🔗 Supply Chain Transparency: **{score['overall_score_pct']}%** ({score['grade']})"
        )
        for stage_detail in score["stage_details"]:
            icon = (
                "✅"
                if stage_detail["score"] >= 80
                else "⚠️"
                if stage_detail["score"] >= 50
                else "❌"
            )
            st.markdown(
                f"- {icon} **{stage_detail['stage'].replace('_', ' ').title()}**: {stage_detail['score']}/100 (Cert: {stage_detail['certification']})"
            )

        if score["identified_risks"]:
            st.warning(
                "**Identified Risks:**\n- " + "\n- ".join(score["identified_risks"])
            )
