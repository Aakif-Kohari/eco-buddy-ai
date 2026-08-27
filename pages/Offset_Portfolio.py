"""
Offset Portfolio Dashboard.
Streamlit page featuring a portfolio dashboard, risk heatmaps, and rebalancing recommendations.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from src.carbon.offset_portfolio_manager import OffsetPortfolioManager
from src.carbon.carbon_risk_analyzer import CarbonRiskAnalyzer
from src.core.database import save_offset_portfolio, get_offset_portfolio

st.set_page_config(page_title="Offset Portfolio", page_icon="📊", layout="wide")

st.title("📊 Dynamic Carbon Offset Portfolio Manager")
st.markdown(
    "Track, analyze, and rebalance your personal carbon offset portfolio for maximum long-term impact."
)

# Initialize session state
if "portfolio_manager" not in st.session_state:
    st.session_state.portfolio_manager = OffsetPortfolioManager(user_id="demo_user")
    # Add some dummy data for demonstration
    st.session_state.portfolio_manager.add_holding(
        "proj_1", "reforestation", "South America", "Gold Standard", 50.0, 15.0
    )
    st.session_state.portfolio_manager.add_holding(
        "proj_2", "renewable_energy", "India", "Verra", 30.0, 10.5
    )
    st.session_state.portfolio_manager.add_holding(
        "proj_3", "direct_air_capture", "Iceland", "Puro.earth", 5.0, 350.0
    )

manager = st.session_state.portfolio_manager
summary = manager.get_portfolio_summary()
analyzer = CarbonRiskAnalyzer(summary)
risk_profile = analyzer.evaluate_portfolio_risk()

# --- Top Level Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Offset (Tonnes)", f"{summary['total_tonnes']:.1f} tCO₂e")
col2.metric("Total Investment", f"${summary['total_cost']:,.2f}")
col3.metric("Avg Cost / Tonne", f"${summary['average_cost_per_tonne']:.2f}")
col4.metric(
    "Diversification Score",
    f"{risk_profile['diversification_score']}/100",
    delta="Good" if risk_profile["diversification_score"] > 60 else "Needs Improvement",
)

# --- Main Dashboard ---
tab1, tab2, tab3 = st.tabs(
    ["📈 Portfolio Breakdown", "⚠️ Risk Analysis", "⚖️ Rebalancing Simulator"]
)

with tab1:
    st.subheader("Portfolio Composition")
    col_a, col_b = st.columns(2)

    with col_a:
        if summary["type_breakdown"]:
            fig_type = px.pie(
                values=list(summary["type_breakdown"].values()),
                names=list(summary["type_breakdown"].keys()),
                title="Allocation by Project Type",
            )
            st.plotly_chart(fig_type, use_container_width=True)

    with col_b:
        if summary["region_breakdown"]:
            fig_region = px.pie(
                values=list(summary["region_breakdown"].values()),
                names=list(summary["region_breakdown"].keys()),
                title="Allocation by Region",
            )
            st.plotly_chart(fig_region, use_container_width=True)

with tab2:
    st.subheader("Risk & Co-Benefit Profile")
    col_c, col_d = st.columns(2)

    with col_c:
        # Risk Gauge
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=risk_profile["weighted_permanence_risk"],
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Permanence Risk Score (Lower is Better)"},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {"range": [0, 30], "color": "lightgreen"},
                        {"range": [30, 60], "color": "yellow"},
                        {"range": [60, 100], "color": "red"},
                    ],
                },
            )
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_d:
        st.markdown(f"### Overall Rating: **{risk_profile['overall_risk_rating']}**")
        st.markdown(
            f"- **HHI Concentration Score:** {risk_profile['hhi_score']} (Lower is more diversified)"
        )
        st.markdown(
            f"- **Co-Benefit Score:** {risk_profile['weighted_co_benefit_score']}/100"
        )

        st.markdown("#### 💡 Recommendations")
        for rec in analyzer.generate_risk_recommendations():
            st.markdown(rec)

with tab3:
    st.subheader("Rebalancing Simulator")
    st.markdown(
        "The following trades are recommended to align your portfolio with the optimal target allocation:"
    )

    trades = manager.calculate_rebalancing_trades()
    if trades:
        df_trades = pd.DataFrame(trades)

        # Color code the action
        def color_action(val):
            return (
                "color: green; font-weight: bold"
                if val == "buy"
                else "color: red; font-weight: bold"
            )

        styled_df = df_trades.style.applymap(color_action, subset=["action"])
        st.dataframe(styled_df, use_container_width=True)

        if st.button("Execute Rebalancing Trades"):
            st.success(
                "Simulated trades executed successfully! Portfolio is now optimized."
            )
            # In a real app, this would update the database and session state
    else:
        st.success(
            "✅ Your portfolio is already perfectly balanced according to the target allocation!"
        )

# --- Save to DB ---
if st.button("💾 Save Portfolio Snapshot"):
    save_offset_portfolio("demo_user", summary, risk_profile)
    st.success("Portfolio snapshot saved to history!")
