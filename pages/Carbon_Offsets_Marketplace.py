"""
Streamlit Page: Verified Carbon Offsets Marketplace & Retirement Ledger
Multi-page section in EcoBuddy AI allowing users to explore verified carbon projects, purchase credits, and manage certificates.
"""

import streamlit as st
import pandas as pd

from eco_marketplace_offsets_service import EcoMarketplaceOffsetsService
from eco_marketplace_offsets_types import OffsetProjectType, OffsetCertificationStandard
from eco_marketplace_offsets_cards import render_portfolio_header, render_offset_project_card
from eco_marketplace_offsets_charts import build_offset_project_type_chart, build_portfolio_spending_chart

st.set_page_config(
    page_title="Carbon Offsets Marketplace - EcoBuddy AI",
    page_icon="🌿",
    layout="wide",
)

st.title("🌿 Verified Carbon Offsets Marketplace & Retirement Ledger")
st.markdown(
    "Support Gold Standard and Verra-certified carbon removal projects, "
    "retire verified carbon credits to balance residual emissions, and track your retirement certificates."
)

service = EcoMarketplaceOffsetsService()
current_user_id = st.session_state.get("user_id", 1)

# Render Portfolio Overview Header
portfolio = service.get_portfolio(current_user_id)
render_portfolio_header(portfolio["summary"])

st.divider()

# Navigation Tabs
tab_explore, tab_portfolio, tab_analytics = st.tabs([
    "🔍 Browse Offset Projects",
    "📜 My Offset Portfolio & Certificates",
    "📊 Market Inventory Analytics",
])

# -------------------------------------------------------------------
# Tab 1: Browse Offset Projects
# -------------------------------------------------------------------
with tab_explore:
    st.subheader("🎯 Verified Carbon Credit Projects")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        type_options = ["All"] + [t.value for t in OffsetProjectType]
        selected_type = st.selectbox("Filter by Project Type", type_options)

    with col_f2:
        cert_options = ["All"] + [c.value for c in OffsetCertificationStandard]
        selected_cert = st.selectbox("Filter by Standard", cert_options)

    projects = service.get_catalog_projects(
        project_type_filter=selected_type,
        certification_filter=selected_cert,
    )

    def handle_buy_offset(project_id: int, tonnes: float):
        tx = service.buy_offsets(current_user_id, project_id, tonnes)
        if tx:
            st.balloons()
            st.success(
                f"🎉 Purchase Successful! Retired {tx.tonnes_purchased} tonnes of CO₂. "
                f"Certificate ID: **{tx.certificate_id}**"
            )
            st.rerun()
        else:
            st.error("Error processing offset transaction. Please check inventory.")

    if not projects:
        st.info("No projects match your filter criteria.")
    else:
        for project in projects:
            render_offset_project_card(project, on_buy_callback=handle_buy_offset)

# -------------------------------------------------------------------
# Tab 2: My Offset Portfolio & Certificates
# -------------------------------------------------------------------
with tab_portfolio:
    st.subheader("📜 Retired Offset Certificates")

    tx_list = portfolio["transactions"]
    if not tx_list:
        st.info("You haven't purchased or retired any carbon offset credits yet.")
    else:
        df_tx = pd.DataFrame(tx_list)[[
            "certificate_id", "project_title", "project_type", "tonnes", "cost_usd", "purchased_at"
        ]]
        df_tx.columns = ["Certificate ID", "Project Name", "Type", "Tonnes Retired", "Cost ($ USD)", "Retirement Date"]
        st.dataframe(df_tx, use_container_width=True)

# -------------------------------------------------------------------
# Tab 3: Market Inventory Analytics
# -------------------------------------------------------------------
with tab_analytics:
    st.subheader("📊 Carbon Market Volume & Diversification")

    all_projects = service.get_catalog_projects()
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        pie_chart = build_offset_project_type_chart(all_projects)
        st.plotly_chart(pie_chart, use_container_width=True)

    with col_c2:
        if tx_list:
            spend_chart = build_portfolio_spending_chart(tx_list)
            st.plotly_chart(spend_chart, use_container_width=True)
        else:
            st.info("Retire carbon offsets to view your personal spending timeline.")
