"""
Carbon Policy Simulator Page.
Streamlit page featuring interactive policy sliders, a net-financial-impact gauge, and an educational breakdown.
"""

import streamlit as st
import plotly.graph_objects as go
from carbon_tax_simulator import CarbonTaxSimulator
from dividend_rebate_calculator import DividendRebateCalculator
from database import save_policy_simulation, get_policy_history

st.set_page_config(page_title="Carbon Policy Simulator", page_icon="⚖️", layout="wide")

st.title("⚖️ Personal Carbon Tax Policy & Dividend Rebate Simulator")
st.markdown(
    "Explore how different carbon pricing policies might impact your household finances, and see if you would be a 'net gainer' or 'net payer'."
)

# --- Input Section ---
st.sidebar.header("🏠 Household Profile")
footprint_tonnes = st.sidebar.number_input(
    "Annual Household Footprint (Tonnes CO₂e)", min_value=0.1, step=0.5, value=10.0
)
adults = st.sidebar.number_input("Number of Adults", min_value=1, step=1, value=2)
children = st.sidebar.number_input("Number of Children", min_value=0, step=1, value=1)
income = st.sidebar.number_input(
    "Annual Household Income ($)", min_value=0, step=5000, value=75000
)

st.sidebar.header("⚙️ Policy Parameters")
tax_rate = st.sidebar.slider(
    "Carbon Tax Rate ($ per Tonne)", min_value=0, max_value=200, step=10, value=50
)

if st.sidebar.button("🔍 Simulate Policy Impact"):
    simulator = CarbonTaxSimulator(
        annual_household_footprint_tonnes=footprint_tonnes,
        tax_rate_per_tonne_usd=tax_rate,
    )
    tax_result = simulator.calculate_tax_liability()

    rebate_calc = DividendRebateCalculator(
        num_adults=adults, num_children=children, annual_household_income_usd=income
    )
    rebate_result = rebate_calc.calculate_rebate()
    net_result = rebate_calc.calculate_net_financial_impact(
        tax_result["total_annual_liability_usd"]
    )

    st.session_state.policy_result = {
        "tax": tax_result,
        "rebate": rebate_result,
        "net": net_result,
        "edu": simulator.get_policy_education_snippet(),
    }
    save_policy_simulation(
        footprint_tonnes, tax_rate, net_result["net_annual_impact_usd"]
    )
    st.success("Simulation complete and saved!")

# --- Results Display ---
if "policy_result" in st.session_state:
    res = st.session_state.policy_result

    st.divider()
    st.subheader("📊 Net Financial Impact")

    # Large gauge for net impact
    net_val = res["net"]["net_annual_impact_usd"]
    gauge_color = "#2ca02c" if res["net"]["is_net_positive"] else "#d62728"

    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=net_val,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Annual Net Financial Impact ($)"},
            delta={"reference": 0},
            gauge={
                "axis": {"range": [None, max(abs(net_val) * 1.2, 1000)]},
                "bar": {"color": gauge_color},
                "steps": [
                    {"range": [0, max(abs(net_val) * 1.2, 1000)], "color": "lightgreen"}
                    if res["net"]["is_net_positive"]
                    else {"range": [0, max(abs(net_val) * 1.2, 1000)], "color": "pink"}
                ],
            },
        )
    )
    fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

    st.info(res["net"]["interpretation"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💸 Tax Liability Breakdown")
        st.metric(
            "Total Annual Tax", f"${res['tax']['total_annual_liability_usd']:,.2f}"
        )
        st.markdown(
            f"- Scope 1 (Direct): ${res['tax']['breakdown']['scope1_direct_usd']:,.2f}"
        )
        st.markdown(
            f"- Scope 2 (Electricity): ${res['tax']['breakdown']['scope2_electricity_usd']:,.2f}"
        )
        st.markdown(
            f"- Scope 3 (Consumption): ${res['tax']['breakdown']['scope3_consumption_usd']:,.2f}"
        )

    with col2:
        st.markdown("### 💰 Dividend Rebate Breakdown")
        st.metric(
            "Final Annual Rebate", f"${res['rebate']['final_annual_rebate_usd']:,.2f}"
        )
        st.markdown(f"- Base Rebate: ${res['rebate']['base_rebate_usd']:,.2f}")
        st.markdown(
            f"- Income Reduction: -${res['rebate']['income_reduction_usd']:,.2f}"
        )
        st.markdown(
            f"- Monthly Payout: ~${res['rebate']['monthly_rebate_usd']:,.2f}/mo"
        )

    st.divider()
    st.subheader("📚 How It Works")
    st.markdown(res["edu"])
