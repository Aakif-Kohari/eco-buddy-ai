"""
Streamlit Component Renderers for Verified Carbon Offsets Marketplace
"""

import streamlit as st
from typing import Dict, Any, Callable
from eco_marketplace_offsets_types import CarbonOffsetProject, UserOffsetPortfolioSummary


def render_portfolio_header(summary: UserOffsetPortfolioSummary) -> None:
    """Renders top summary metrics for retired carbon offset portfolio."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🌿 Retired Carbon Credits",
            value=f"{summary.total_tonnes_retired:,.2f} Tonnes",
            delta="Verified Offsets",
        )

    with col2:
        st.metric(
            label="💳 Total Investment",
            value=f"${summary.total_spent_usd:,.2f}",
            delta="USD Spent",
        )

    with col3:
        st.metric(
            label="📜 Certificates Issued",
            value=f"{summary.total_certificates}",
            delta="Verifiable Proofs",
        )

    with col4:
        st.metric(
            label="📊 Diversification Score",
            value=f"{summary.diversification_score:.0f} / 100",
            delta="Portfolio Rating",
        )


def render_offset_project_card(project: CarbonOffsetProject, on_buy_callback: Callable = None) -> None:
    """Renders a verified offset project card with pricing, certification, and buy button."""
    with st.container():
        st.markdown(
            f"""
            <div style="
                border: 1px solid #E0E0E0;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 14px;
                background-color: #FFFFFF;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #1B5E20;">{project.title}</h3>
                    <span style="
                        background-color: #E8F5E9;
                        color: #2E7D32;
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-weight: 600;
                    ">⭐ {project.rating_stars} / 5.0</span>
                </div>
                <p style="color: #555; margin-top: 6px;">{project.description}</p>
                <div style="display: flex; gap: 16px; font-size: 0.88rem; color: #666; margin-top: 8px;">
                    <span><b>Type:</b> {project.project_type.value}</span>
                    <span><b>Standard:</b> {project.certification_standard.value}</span>
                    <span><b>Location:</b> 📍 {project.location}</span>
                    <span><b>Permanence:</b> ⏳ {project.permanence_years} Years</span>
                </div>
                <div style="margin-top: 12px; font-size: 1.1rem; color: #2E7D32;">
                    <b>Price:</b> ${project.price_per_tonne_usd:.2f} / tonne CO₂e &nbsp;|&nbsp; 
                    <b>Available:</b> {project.total_available_tonnes:,.0f} tonnes
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"💳 Purchase & Retire Offsets from '{project.title}'"):
            with st.form(key=f"buy_offset_form_{project.id}"):
                tonnes = st.number_input(
                    "Tonnes of CO₂ to Retire",
                    min_value=0.1,
                    value=1.0,
                    step=0.5,
                    key=f"tonnes_{project.id}",
                )
                est_cost = tonnes * project.price_per_tonne_usd
                st.write(f"**Total Estimated Cost:** ${est_cost:,.2f} USD")
                submit = st.form_submit_button("Confirm & Issue Retirement Certificate 📜")
                if submit and on_buy_callback:
                    on_buy_callback(project.id, tonnes)
