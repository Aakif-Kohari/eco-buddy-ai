"""
Green Premium Analyzer Page.
Streamlit page where users can select product categories, input local utility costs, and view interactive payback timeline charts.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.utils.substitution_roi_engine import SubstitutionROIEngine
from src.utils.green_premium_calculator import GreenPremiumCalculator
from src.core.database import save_green_premium_analysis

st.set_page_config(page_title="Green Premium Analyzer", page_icon="💵", layout="wide")

st.title("💵 Green Premium & Sustainable Substitution ROI Engine")
st.markdown(
    "Quantify the upfront cost of sustainable choices and model their long-term financial and environmental payback."
)

engine = SubstitutionROIEngine()
calculator = GreenPremiumCalculator()
products = calculator.get_available_products()

# --- Input Section ---
st.subheader("⚙️ Configure Your Substitution")
col1, col2 = st.columns(2)

with col1:
    product_key = st.selectbox(
        "Select Product Category",
        options=products,
        format_func=lambda x: calculator.get_product_display_name(x),
    )

with col2:
    utility_inflation = (
        st.slider("Expected Annual Utility Cost Increase (%)", 0.0, 10.0, 3.0, step=0.5)
        / 100.0
    )
    subsidy = st.number_input(
        "Available Rebate/Subsidy ($)", min_value=0.0, step=50.0, value=0.0
    )

if st.button("📈 Calculate ROI & Payback", type="primary"):
    with st.spinner("Modeling financial and environmental returns..."):
        result = engine.calculate_roi(
            product_key=product_key,
            utility_inflation_rate=utility_inflation,
            subsidy_usd=subsidy,
        )
        st.session_state.roi_result = result
        save_green_premium_analysis(product_key, utility_inflation, subsidy, result)
        st.success("ROI analysis complete and saved!")

# --- Results Display ---
if "roi_result" in st.session_state:
    result = st.session_state.roi_result

    st.divider()
    st.subheader(f"📊 ROI Analysis: {result['product_name']}")

    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Green Premium",
        f"${result['effective_premium_usd']:,.2f}",
        delta=f"-${result['subsidy_applied_usd']}"
        if result["subsidy_applied_usd"] > 0
        else None,
    )
    col2.metric("Break-Even Point", f"{result['break_even_years']} years")
    col3.metric(
        "Net Financial ROI",
        f"${result['net_financial_roi_usd']:,.2f}",
        delta_color="normal" if result["net_financial_roi_usd"] > 0 else "inverse",
    )
    col4.metric("Total Carbon Saved", f"{result['total_carbon_savings_kg']:,.0f} kg")

    if result["is_financially_viable"]:
        st.success(
            "✅ **Financially Viable:** This sustainable investment pays for itself and generates net savings over its lifespan."
        )
    else:
        st.warning(
            "⚠️ **Not Financially Viable:** Based on current parameters, this investment does not break even within its lifespan. Consider higher subsidies or rising utility rates."
        )

    # Cumulative Savings Chart
    st.markdown("### 💰 Cumulative Net Savings Over Time")
    df = pd.DataFrame(result["yearly_projection"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["year"],
            y=df["cumulative_net_savings_usd"],
            mode="lines+markers",
            name="Cumulative Net Savings",
            line=dict(
                color="#2ca02c" if result["is_financially_viable"] else "#d62728",
                width=3,
            ),
            fill="tozeroy",
        )
    )

    # Add break-even line if applicable
    if isinstance(result["break_even_years"], float):
        fig.add_vline(
            x=result["break_even_years"],
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Break-even: {result['break_even_years']} yrs",
        )

    fig.update_layout(
        title="Cumulative Financial Position vs. Years Owned",
        xaxis_title="Years",
        yaxis_title="Net Savings (USD)",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Data Table
    st.subheader("📅 Year-by-Year Projection")
    st.dataframe(df, use_container_width=True, hide_index=True)
