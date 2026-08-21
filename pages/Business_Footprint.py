import pandas as pd
import plotly.express as px
import streamlit as st

from business_footprint import (
    calculate_business_footprint,
    generate_b2b_recommendations,
)
from database import get_business_footprint_history, save_business_footprint
from scope3_screener import SCOPE3_CATEGORIES
from units import format_co2

st.set_page_config(page_title="Business Footprint", page_icon="🏢", layout="wide")

st.title("🏢 Corporate Scope 3 Emission Screener")
st.markdown(
    "Estimate and manage your micro-business or freelance supply chain emissions."
)

# --- Session State for Expenses ---
if "business_expenses" not in st.session_state:
    st.session_state.business_expenses = []

# --- Input Form ---
with st.form("expense_form"):
    st.subheader("Log a Business Expense")
    col1, col2 = st.columns(2)

    with col1:
        expense_type = st.selectbox(
            "Expense Type",
            options=list(SCOPE3_CATEGORIES.keys()),
            format_func=lambda x: (
                SCOPE3_CATEGORIES[x]["category_name"]
                + " - "
                + x.replace("_", " ").title()
            ),
        )
        amount = st.number_input("Amount", min_value=0.0, step=0.1, value=100.0)

    with col2:
        unit = st.selectbox("Unit", ["usd", "km", "kg"])
        st.write(f"*{SCOPE3_CATEGORIES[expense_type]['description']}*")

    submitted = st.form_submit_button("Add Expense")
    if submitted:
        st.session_state.business_expenses.append(
            {"type": expense_type, "amount": amount, "unit": unit}
        )
        st.success("Expense added!")

# --- Display Current List ---
if st.session_state.business_expenses:
    st.subheader("Current Session Expenses")
    df = pd.DataFrame(st.session_state.business_expenses)
    st.dataframe(df, use_container_width=True)

    if st.button("Calculate Footprint & Save"):
        with st.spinner("Analyzing Scope 3 emissions..."):
            footprint = calculate_business_footprint(st.session_state.business_expenses)

            # Save to DB
            save_business_footprint(
                footprint["total_emissions_kg"], footprint["business_eco_score"]
            )

            st.session_state.latest_footprint = footprint
            st.success("Footprint calculated and saved to history!")

# --- Results Display ---
if "latest_footprint" in st.session_state:
    fp = st.session_state.latest_footprint

    col1, col2 = st.columns(2)
    col1.metric("Total Scope 3 Emissions", format_co2(fp["total_emissions_kg"]))
    col2.metric("Business Eco-Score", f"{fp['business_eco_score']}/100")

    # Chart
    if fp["category_breakdown"]:
        fig = px.pie(
            values=list(fp["category_breakdown"].values()),
            names=list(fp["category_breakdown"].keys()),
            title="Emissions by Scope 3 Category",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Recommendations
    st.subheader("💼 B2B Sustainability Recommendations")
    for rec in generate_b2b_recommendations(fp):
        st.markdown(f"- {rec}")

# --- History ---
st.divider()
st.subheader("📜 Historical Business Assessments")
history = get_business_footprint_history()
if history:
    st.dataframe(pd.DataFrame(history), use_container_width=True)
else:
    st.info("No historical business assessments found.")

