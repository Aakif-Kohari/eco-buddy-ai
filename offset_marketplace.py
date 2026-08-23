"""Carbon Offset Marketplace — main page component.

Browse offset projects, track your portfolio, and calculate your impact.
"""

import streamlit as st
from typing import List, Dict, Optional
from offset_types import (
    OffsetProject, OffsetCategory, ProjectStatus, VerificationStandard,
    OffsetFilterOptions, CATEGORY_ICONS, CATEGORY_COLORS, CONTINENT_OPTIONS,
)
from offset_data import (
    generate_mock_projects, generate_mock_purchases, generate_user_portfolio,
    generate_marketplace_stats, generate_mock_reviews, calculate_offset_impact,
)
from offset_cards import (
    render_project_card, render_purchase_card, render_portfolio_summary,
    render_impact_calculator_card, render_certificate_card, render_review_card,
)
from offset_charts import (
    create_marketplace_overview, create_category_distribution,
    create_geographic_distribution, create_monthly_sales_chart,
    create_price_comparison_chart, create_funding_progress_chart,
    create_verification_distribution,
)


def render_carbon_offset_marketplace(user_id: str = None):
    """Render the full Carbon Offset Marketplace."""

    # ─── Data ─────────────────────────────────────────────────────────
    projects = generate_mock_projects(16)
    purchases = generate_mock_purchases("user_001", projects)
    portfolio = generate_user_portfolio("user_001", purchases)
    stats = generate_marketplace_stats(projects)

    # ─── Header ───────────────────────────────────────────────────────
    st.markdown("""
    <div style='
        text-align: center;
        padding: 28px 20px;
        background: linear-gradient(145deg, rgba(34,197,94,0.06), rgba(14,165,233,0.04));
        border: 1px solid rgba(74,222,128,0.15);
        border-radius: 18px;
        margin-bottom: 24px;
    '>
        <div style='font-size: 36px; margin-bottom: 8px;'>🌍</div>
        <div style='font-size: 26px; font-weight: 800; color: #111827; margin-bottom: 6px;'>
            Carbon Offset Marketplace
        </div>
        <div style='font-size: 14px; color: #6b7280; max-width: 600px; margin: 0 auto;'>
            Support verified carbon offset projects worldwide. Browse, invest, and track your climate impact.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── Stats Overview ───────────────────────────────────────────────
    fig_overview = create_marketplace_overview(stats)
    st.plotly_chart(fig_overview, use_container_width=True)

    # ─── Tabs ─────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🛒 Browse Projects",
        "📊 Marketplace Analytics",
        "💼 My Portfolio",
        "🧮 Impact Calculator",
    ])

    # ─── Tab 1: Browse Projects ──────────────────────────────────────
    with tab1:
        # Filter Bar
        with st.expander("🔍 Filter Projects", expanded=True):
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                search = st.text_input("Search", placeholder="Project name...", key="mp_search")
            with col_f2:
                cat_options = ["All"] + [c.value.replace("_", " ").title() for c in OffsetCategory]
                category = st.selectbox("Category", cat_options, key="mp_category")
            with col_f3:
                continent = st.selectbox("Region", CONTINENT_OPTIONS, key="mp_continent")
            with col_f4:
                sort_by = st.selectbox("Sort by", ["Rating", "Price: Low", "Price: High", "Funding %", "Tons Available"], key="mp_sort")

        col_filter, col_stats = st.columns([3, 1])
        with col_stats:
            st.markdown("#### Quick Stats")
            render_project_quick_stats(projects)

        with col_filter:
            # Apply filters
            filtered = projects
            if search:
                filtered = [p for p in filtered if search.lower() in p.name.lower() or search.lower() in p.description.lower()]
            if category != "All":
                cat_enum = next((c for c in OffsetCategory if c.value.replace("_", " ").title() == category), None)
                if cat_enum:
                    filtered = [p for p in filtered if p.category == cat_enum]
            if continent != "All":
                filtered = [p for p in filtered if p.continent == continent]

            # Sort
            if sort_by == "Rating":
                filtered = sorted(filtered, key=lambda p: p.rating, reverse=True)
            elif sort_by == "Price: Low":
                filtered = sorted(filtered, key=lambda p: p.price_per_ton)
            elif sort_by == "Price: High":
                filtered = sorted(filtered, key=lambda p: p.price_per_ton, reverse=True)
            elif sort_by == "Funding %":
                filtered = sorted(filtered, key=lambda p: p.funding_percent, reverse=True)
            elif sort_by == "Tons Available":
                filtered = sorted(filtered, key=lambda p: p.tons_remaining, reverse=True)

            st.markdown(f"**{len(filtered)}** projects found")

            for project in filtered:
                with st.expander(f"{CATEGORY_ICONS.get(project.category, '🌍')} {project.name} — ${project.price_per_ton}/ton", expanded=False):
                    render_project_card(project, show_details=True)

                    # Purchase Flow
                    st.markdown("---")
                    st.markdown("**Purchase Carbon Offsets**")
                    pc1, pc2, pc3 = st.columns([2, 1, 1])
                    with pc1:
                        tons = st.number_input(
                            "Tons of CO₂",
                            min_value=0.1,
                            max_value=float(project.tons_remaining),
                            value=1.0,
                            step=0.1,
                            key=f"buy_tons_{project.project_id}",
                        )
                    with pc2:
                        cost = tons * project.price_per_ton
                        st.metric("Total Cost", f"${cost:.2f}")
                    with pc3:
                        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                        if st.button("🌿 Purchase", key=f"buy_{project.project_id}", use_container_width=True):
                            st.success(f"✅ Purchased {tons:.2f} tons from {project.name}!")
                            render_impact_calculator_card(tons)

                    # Reviews
                    reviews = generate_mock_reviews(project.project_id, 3)
                    st.markdown("**Reviews**")
                    for review in reviews:
                        render_review_card(review)

    # ─── Tab 2: Analytics ────────────────────────────────────────────
    with tab2:
        col_a, col_b = st.columns(2)
        with col_a:
            fig_cat = create_category_distribution(stats)
            st.plotly_chart(fig_cat, use_container_width=True)
            fig_geo = create_geographic_distribution(stats)
            st.plotly_chart(fig_geo, use_container_width=True)
        with col_b:
            fig_monthly = create_monthly_sales_chart(stats.monthly_sales)
            st.plotly_chart(fig_monthly, use_container_width=True)
            fig_verify = create_verification_distribution(projects)
            st.plotly_chart(fig_verify, use_container_width=True)

        st.markdown("---")
        col_c, col_d = st.columns(2)
        with col_c:
            fig_scatter = create_price_comparison_chart(projects)
            st.plotly_chart(fig_scatter, use_container_width=True)
        with col_d:
            fig_funding = create_funding_progress_chart(projects)
            st.plotly_chart(fig_funding, use_container_width=True)

    # ─── Tab 3: Portfolio ────────────────────────────────────────────
    with tab3:
        render_portfolio_summary(portfolio)

        st.markdown("#### 📜 Purchase History")
        if portfolio.purchases:
            for purchase in sorted(portfolio.purchases, key=lambda p: p.purchase_date, reverse=True):
                render_purchase_card(purchase)
        else:
            st.info("No purchases yet. Browse projects to make your first offset!")

        st.markdown("#### 🏆 Your Certificates")
        if portfolio.certificates:
            col_cert1, col_cert2 = st.columns(2)
            for i, purchase in enumerate(portfolio.purchases[:4]):
                with col_cert1 if i % 2 == 0 else col_cert2:
                    render_certificate_card(
                        purchase.certificate_id,
                        purchase.project_name,
                        purchase.tons_purchased,
                        purchase.purchase_date,
                    )
        else:
            st.info("No certificates yet. Make a purchase to earn your first certificate!")

    # ─── Tab 4: Calculator ───────────────────────────────────────────
    with tab4:
        st.markdown("#### 🧮 Carbon Offset Calculator")
        st.markdown("Enter your annual carbon footprint to see how many offsets you need and what impact they'd have.")

        calc_col1, calc_col2 = st.columns([1, 1])

        with calc_col1:
            st.markdown("**Your Annual Footprint**")
            transport = st.number_input("Daily transport distance (km)", value=15.0, min_value=0.0, key="calc_dist")
            electricity = st.number_input("Monthly electricity (kWh)", value=250.0, min_value=0.0, key="calc_elec")
            flights = st.number_input("Annual flights", value=2, min_value=0, key="calc_flights")
            diet = st.selectbox("Diet type", ["Vegetarian", "Vegan", "Omnivore", "Heavy Meat"], key="calc_diet")

            if st.button("🧮 Calculate", key="run_calc"):
                # Simplified calculation
                transport_kg = 0.19 * transport * 365
                energy_kg = 0.475 * electricity * 12
                diet_kg = {"Vegan": 1.5, "Vegetarian": 2.0, "Omnivore": 3.3, "Heavy Meat": 4.5}.get(diet, 2.0) * 365
                flight_kg = flights * 250
                total_kg = transport_kg + energy_kg + diet_kg + flight_kg
                total_tons = total_kg / 1000

                st.session_state["calc_result"] = {
                    "total_kg": round(total_kg, 1),
                    "total_tons": round(total_tons, 2),
                    "breakdown": {
                        "Transport": round(transport_kg, 1),
                        "Energy": round(energy_kg, 1),
                        "Food": round(diet_kg, 1),
                        "Flights": round(flight_kg, 1),
                    },
                }

        with calc_col2:
            if "calc_result" in st.session_state:
                result = st.session_state["calc_result"]
                st.success(f"**Annual Footprint: {result['total_kg']:,.0f} kg CO₂** ({result['total_tons']:.2f} tons)")

                render_impact_calculator_card(result["total_tons"])

                # Offset cost estimate
                avg_price = stats.avg_price_per_ton
                offset_cost = result["total_tons"] * avg_price

                st.markdown(f"""
                <div style='
                    padding: 16px;
                    background: linear-gradient(145deg, rgba(34,197,94,0.05), rgba(255,255,255,0.95));
                    border: 1px solid rgba(74,222,128,0.15);
                    border-radius: 14px;
                '>
                    <div style='font-size: 14px; font-weight: 700; color: #111827; margin-bottom: 8px;'>💰 Estimated Offset Cost</div>
                    <div style='font-size: 24px; font-weight: 800; color: #22c55e;'>${offset_cost:.2f}</div>
                    <div style='font-size: 11px; color: #6b7280;'>Based on average price of ${avg_price:.2f}/ton across all projects</div>
                    <div style='font-size: 11px; color: #9ca3af; margin-top: 4px;'>That's just ${offset_cost / 12:.2f}/month to be carbon neutral! 🌱</div>
                </div>
                """, unsafe_allow_html=True)

                # Breakdown chart
                import plotly.graph_objects as go
                labels = list(result["breakdown"].keys())
                values = list(result["breakdown"].values())
                colors = ["#22c55e", "#0ea5e9", "#f59e0b", "#8b5cf6"]

                fig = go.Figure(go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.5,
                    marker=dict(colors=colors, line=dict(width=2, color="white")),
                    textinfo="percent+label",
                    textfont=dict(size=11),
                ))
                fig.update_layout(
                    title="Your Carbon Breakdown",
                    height=300,
                    margin=dict(t=40, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    font={"family": "Inter, sans-serif"},
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("👆 Enter your details and click Calculate to see your offset needs.")

    # ─── Footer ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;'>
        🌍 Carbon Offset Marketplace · Offset · Track · Impact<br>
        All projects are verified by recognized carbon standards.
    </div>
    """, unsafe_allow_html=True)


def render_project_quick_stats(projects: List[OffsetProject]):
    """Render quick stats sidebar for project browsing."""
    active = sum(1 for p in projects if p.status == ProjectStatus.ACTIVE)
    total_tons = sum(p.tons_remaining for p in projects)
    avg_price = sum(p.price_per_ton for p in projects) / len(projects) if projects else 0

    st.markdown(f"""
    <div style='
        padding: 16px;
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 14px;
        margin-bottom: 12px;
    '>
        <div style='font-size: 13px; font-weight: 700; color: #111827; margin-bottom: 10px;'>📊 Quick Stats</div>
        <div style='display: flex; flex-direction: column; gap: 8px;'>
            <div style='display: flex; justify-content: space-between;'>
                <span style='font-size: 11px; color: #6b7280;'>Total Projects</span>
                <span style='font-size: 12px; font-weight: 700; color: #111827;'>{len(projects)}</span>
            </div>
            <div style='display: flex; justify-content: space-between;'>
                <span style='font-size: 11px; color: #6b7280;'>Active</span>
                <span style='font-size: 12px; font-weight: 700; color: #22c55e;'>{active}</span>
            </div>
            <div style='display: flex; justify-content: space-between;'>
                <span style='font-size: 11px; color: #6b7280;'>Tons Available</span>
                <span style='font-size: 12px; font-weight: 700; color: #0ea5e9;'>{total_tons:,.0f}</span>
            </div>
            <div style='display: flex; justify-content: space-between;'>
                <span style='font-size: 11px; color: #6b7280;'>Avg Price/Ton</span>
                <span style='font-size: 12px; font-weight: 700; color: #8b5cf6;'>${avg_price:.2f}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
