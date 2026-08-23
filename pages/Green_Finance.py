"""
Green Finance Tracker Page.
Streamlit page where users can input financial allocations and view their "financial footprint" alongside greener alternatives.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from green_investment_tracker import GreenInvestmentTracker
from banking_impact_analyzer import BankingImpactAnalyzer
from database import save_green_finance_profile

st.set_page_config(page_title="Green Finance", page_icon="💰", layout="wide")

st.title("💰 Personalized Eco-Friendly Investment & Green Banking Tracker")
st.markdown(
    "Estimate the hidden carbon footprint of your financial portfolio and bank deposits, and discover greener alternatives."
)

# --- Input Section ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Investment Portfolio")
    portfolio_value = st.number_input(
        "Total Portfolio Value ($)", min_value=0, step=1000, value=50000
    )

    st.markdown("#### Asset Allocation (%)")
    alloc_equities_dev = st.slider("Developed Market Equities", 0, 100, 40)
    alloc_equities_em = st.slider("Emerging Market Equities", 0, 100, 10)
    alloc_bonds_corp = st.slider("Corporate Bonds", 0, 100, 20)
    alloc_bonds_gov = st.slider("Government Bonds", 0, 100, 20)
    alloc_real_estate = st.slider("Real Estate", 0, 100, 0)
    alloc_esg = st.slider("ESG / Green Funds", 0, 100, 10)
    alloc_cash = st.slider("Cash", 0, 100, 0)

    total_alloc = (
        alloc_equities_dev
        + alloc_equities_em
        + alloc_bonds_corp
        + alloc_bonds_gov
        + alloc_real_estate
        + alloc_esg
        + alloc_cash
    )

with col2:
    st.subheader("🏦 Retail Banking")
    deposit_amount = st.number_input(
        "Total Checking/Savings Deposits ($)", min_value=0, step=1000, value=10000
    )
    current_bank_type = st.selectbox(
        "Current Bank Type",
        [
            "traditional_large_bank",
            "traditional_regional_bank",
            "credit_union",
            "certified_green_bank",
            "online_neobank",
        ],
        format_func=lambda x: x.replace("_", " ").title(),
    )

# --- Calculation ---
if st.button("🔍 Analyze Financial Footprint", type="primary"):
    if total_alloc != 100:
        st.error(f"Asset allocations must sum to 100%. Current total: {total_alloc}%")
    else:
        # 1. Investment Analysis
        tracker = GreenInvestmentTracker(portfolio_value)
        tracker.set_allocation("equities_developed", alloc_equities_dev)
        tracker.set_allocation("equities_emerging", alloc_equities_em)
        tracker.set_allocation("corporate_bonds", alloc_bonds_corp)
        tracker.set_allocation("government_bonds", alloc_bonds_gov)
        tracker.set_allocation("real_estate", alloc_real_estate)
        tracker.set_allocation("esg_funds", alloc_esg)
        tracker.set_allocation("cash", alloc_cash)

        investment_results = tracker.calculate_financed_emissions()
        suggestions = tracker.suggest_greener_alternatives()

        # 2. Banking Analysis
        banking_analyzer = BankingImpactAnalyzer(deposit_amount)
        banking_results = banking_analyzer.calculate_deposit_footprint(
            current_bank_type
        )
        banking_alternatives = banking_analyzer.compare_banking_options(
            current_bank_type
        )

        st.session_state.finance_results = {
            "investment": investment_results,
            "investment_suggestions": suggestions,
            "banking": banking_results,
            "banking_alternatives": banking_alternatives,
        }

        # Save to DB
        save_green_finance_profile(
            portfolio_value, deposit_amount, investment_results, banking_results
        )
        st.success("Financial footprint analyzed and saved!")

# --- Results Display ---
if "finance_results" in st.session_state:
    results = st.session_state.finance_results

    st.divider()
    st.subheader("📊 Your Financial Carbon Footprint")

    total_footprint = (
        results["investment"]["total_financed_emissions_tonnes"]
        + results["banking"]["annual_emissions_tonnes"]
    )

    col_a, col_b = st.columns(2)
    col_a.metric(
        "Total Annual Financed Emissions", f"{total_footprint:,.2f} tonnes CO₂e"
    )
    col_b.metric(
        "Equivalent to",
        f"{int(total_footprint * 1000 / 20)} Tree Seedlings grown for 10 years",
    )

    tab1, tab2 = st.tabs(["📈 Investment Breakdown", "🏦 Banking Alternatives"])

    with tab1:
        st.markdown("### Portfolio Emissions by Asset Class")
        breakdown = results["investment"]["breakdown"]

        fig = px.bar(
            x=list(breakdown.keys()),
            y=[v["emissions_tonnes"] for v in breakdown.values()],
            labels={"x": "Asset Class", "y": "Emissions (tonnes CO₂e)"},
            color_discrete_sequence=["#1f77b4"],
        )
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

        if results["investment_suggestions"]:
            st.markdown("### 💡 Greener Investment Suggestions")
            for sug in results["investment_suggestions"]:
                st.info(
                    f"**{sug['current_asset']}**: {sug['recommended_action']} (Potential savings: **{sug['potential_savings_tonnes']} tonnes**)"
                )
        else:
            st.success(
                "✅ Your portfolio is already well-aligned with low-carbon asset classes!"
            )

    with tab2:
        st.markdown(
            f"### Current Banking Footprint: **{results['banking']['annual_emissions_tonnes']} tonnes CO₂e/year**"
        )

        if results["banking_alternatives"]:
            st.markdown("#### 🌱 Recommended Green Banking Alternatives")
            for alt in results["banking_alternatives"][:3]:  # Show top 3
                st.success(f"**{alt['alternative_bank_type']}**")
                st.markdown(
                    f"- **Emissions:** {alt['annual_emissions_tonnes']} tonnes/year"
                )
                st.markdown(
                    f"- **Potential Savings:** {alt['potential_annual_savings_tonnes']} tonnes/year ({alt['savings_percentage']}% reduction)"
                )
        else:
            st.success("✅ You are already using a certified green banking option!")
