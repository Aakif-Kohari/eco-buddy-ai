import pandas as pd
import plotly.express as px
import streamlit as st

from src.core.database import get_waste_analytics_history, save_waste_log
from src.utils.units import format_quantity
from src.environment.waste_analytics import get_waste_stream_metadata, process_waste_log

st.set_page_config(page_title="Waste Analytics", page_icon="♻️", layout="wide")

st.title("♻️ Advanced Waste Stream Analytics")
st.markdown(
    "Log your waste items to detect recycling contamination and track your recycling efficiency."
)

# --- Session State ---
if "waste_items" not in st.session_state:
    st.session_state.waste_items = []

# --- Input Form ---
with st.form("waste_form"):
    st.subheader("Log a Waste Item")
    col1, col2, col3 = st.columns(3)

    with col1:
        item_name = st.text_input("Item Name (e.g., 'Pizza Box', 'Plastic Bottle')")
    with col2:
        weight = st.number_input("Weight (kg)", min_value=0.01, step=0.1, value=0.5)
    with col3:
        stream = st.selectbox(
            "Intended Stream", ["recycling", "compost", "landfill", "hazardous"]
        )

    submitted = st.form_submit_button("Add Item")
    if submitted and item_name:
        st.session_state.waste_items.append(
            {"name": item_name, "weight_kg": weight, "stream": stream}
        )
        st.success(f"Added '{item_name}' to log.")

# --- Display Current List ---
if st.session_state.waste_items:
    st.subheader("Current Session Waste Log")
    df = pd.DataFrame(st.session_state.waste_items)
    st.dataframe(df, use_container_width=True)

    if st.button("🔍 Analyze Waste Stream", type="primary"):
        with st.spinner("Processing contamination checks..."):
            analytics = process_waste_log(st.session_state.waste_items)
            st.session_state.latest_analytics = analytics

            # Save to DB
            save_waste_log(
                analytics["total_weight_kg"], analytics["recycling_efficiency_score"]
            )
            st.success("Analysis complete and saved to history!")

# --- Results Display ---
if "latest_analytics" in st.session_state:
    data = st.session_state.latest_analytics
    metadata = get_waste_stream_metadata()

    col1, col2 = st.columns(2)
    col1.metric(
        "Total Waste Logged", f"{format_quantity(data['total_weight_kg'], 'kg')}"
    )

    # Efficiency Score with color coding
    score = data["recycling_efficiency_score"]
    if score >= 80:
        score_color = "green"
    elif score >= 50:
        score_color = "orange"
    else:
        score_color = "red"

    col2.metric("Recycling Efficiency Score", f"{score}/100", delta_color="off")

    # Contamination Warnings
    if data["contamination_warnings"]:
        st.warning(
            f"⚠️ **Contamination Detected:** {data['contaminated_weight_kg']} kg of waste was misdirected and diverted to landfill."
        )
        for warn in data["contamination_warnings"]:
            st.markdown(
                f"- **{warn['item']}** ({warn['weight_kg']} kg): {warn['reason']}"
            )
    else:
        st.success(
            "✅ **No Contamination Detected!** Your recycling and compost streams are clean."
        )

    # Chart
    if data["total_weight_kg"] > 0:
        breakdown = data["stream_breakdown"]
        labels = [metadata[k]["name"] for k, v in breakdown.items() if v > 0]
        values = [v for k, v in breakdown.items() if v > 0]
        colors = [metadata[k]["color"] for k, v in breakdown.items() if v > 0]

        fig = px.pie(
            values=values,
            names=labels,
            color_discrete_sequence=colors,
            title="Final Waste Stream Distribution (Post-Contamination Diversion)",
        )
        st.plotly_chart(fig, use_container_width=True)

# --- History ---
st.divider()
st.subheader("📜 Historical Waste Analytics")
history = get_waste_analytics_history()
if history:
    st.dataframe(pd.DataFrame(history), use_container_width=True)
