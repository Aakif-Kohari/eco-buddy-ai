"""
Textile Impact Comparator Page.
Streamlit page allowing users to input garment details and compare environmental footprints side-by-side.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.lifestyle.fashion_impact_comparator import FashionImpactComparator
from src.core.database import save_textile_comparison

st.set_page_config(page_title="Textile Impact", page_icon="👕", layout="wide")

st.title("👕 Sustainable Textile Lifecycle Impact Comparator")
st.markdown(
    "Compare the carbon, water, and microplastic footprint of different clothing choices."
)

comparator = FashionImpactComparator()

# --- Input Section ---
st.subheader("📝 Define Garments to Compare")
col1, col2, col3 = st.columns(3)

garments_input = []
for i in range(3):
    with st.container():
        st.markdown(f"#### Garment {i + 1}")
        material = st.selectbox(
            "Material",
            [
                "conventional cotton",
                "organic cotton",
                "polyester",
                "recycled polyester",
                "wool",
                "linen",
            ],
            key=f"mat_{i}",
        )
        weight = st.number_input(
            "Weight (kg)",
            min_value=0.1,
            max_value=5.0,
            step=0.1,
            value=0.5,
            key=f"wt_{i}",
        )
        wears = st.number_input(
            "Estimated Total Wears",
            min_value=1,
            max_value=500,
            step=10,
            value=30,
            key=f"wr_{i}",
        )
        wash_ratio = st.slider(
            "Wash Frequency (1 = every wear, 0.1 = every 10 wears)",
            0.1,
            1.0,
            0.5,
            step=0.1,
            key=f"wash_{i}",
        )

        garments_input.append(
            {
                "material": material,
                "weight_kg": weight,
                "estimated_wears": wears,
                "washes_per_wear_ratio": wash_ratio,
            }
        )

if st.button("🔍 Compare Impacts", type="primary"):
    results = comparator.compare_garments(garments_input)
    st.session_state.comparison_results = results

    # Save to DB
    save_textile_comparison(garments_input, results)

# --- Results Section ---
if "comparison_results" in st.session_state:
    results = st.session_state.comparison_results

    st.divider()
    st.subheader("📊 Impact Comparison")

    # Summary Metrics
    cols = st.columns(len(results))
    for idx, res in enumerate(results):
        with cols[idx]:
            st.metric(
                f"Garment {idx + 1} ({res['material'].title()})",
                f"{res['total_carbon_kg']} kg CO₂e",
                delta=f"{res['carbon_per_wear_kg']} kg/wear",
                delta_color="inverse"
                if idx == 0
                else "normal",  # Green for the winner (lowest)
            )

    # Detailed Breakdown Chart
    st.markdown("### Lifecycle Breakdown")
    categories = [
        f"Garment {i + 1} ({r['material'].title()})" for i, r in enumerate(results)
    ]
    prod_carbon = [r["breakdown"]["production_carbon_kg"] for r in results]
    wash_carbon = [r["breakdown"]["washing_carbon_kg"] for r in results]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Production Phase", x=categories, y=prod_carbon, marker_color="#1f77b4"
        )
    )
    fig.add_trace(
        go.Bar(
            name="Washing Phase", x=categories, y=wash_carbon, marker_color="#ff7f0e"
        )
    )

    fig.update_layout(
        barmode="stack",
        title="Total Carbon Footprint Breakdown (kg CO₂e)",
        xaxis_title="Garment",
        yaxis_title="kg CO₂e",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Microplastics Warning
    st.markdown("### ⚠️ Microplastic Shedding")
    mp_data = [
        {
            "Garment": f"Garment {i + 1}",
            "Material": r["material"],
            "Microplastics (mg)": r["total_microplastics_mg"],
        }
        for i, r in enumerate(results)
    ]
    mp_df = pd.DataFrame(mp_data)

    def highlight_mp(val):
        return "color: red; font-weight: bold" if val > 100 else "color: green"

    st.dataframe(
        mp_df.style.applymap(highlight_mp, subset=["Microplastics (mg)"]),
        use_container_width=True,
    )

    for res in results:
        st.info(f"**{res['material'].title()} Insight:** {res['description']}")
