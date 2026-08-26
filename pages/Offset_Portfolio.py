"""Carbon Offset Portfolio & Net-Zero Roadmap page for EcoBuddy AI.

Browse verified offset projects, build a portfolio, track progress
toward net-zero, generate offset certificates, and set offset goals.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from styles.theme import apply_theme
from offset_portfolio import (
    OFFSET_PROJECTS,
    calculate_offset_cost,
    calculate_portfolio_summary,
    project_net_zero_timeline,
    generate_certificate,
    format_certificate_text,
    save_offset_transaction,
    get_offset_transactions,
    save_offset_goal,
    get_offset_goal,
    list_offset_projects,
    list_regions,
    list_project_types,
)

# ── Auth ─────────────────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='section-header'>🌍 Carbon Offset Portfolio & Net-Zero Roadmap</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Browse verified offset projects, build your portfolio, project your "
    "net-zero timeline, and generate offset certificates."
)
st.markdown("---")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_browse, tab_portfolio, tab_roadmap, tab_certs, tab_goals = st.tabs([
    "🔍 Browse Projects",
    "💼 My Portfolio",
    "🗺️ Net-Zero Roadmap",
    "📜 Certificates",
    "🎯 Offset Goals",
])


# ── Tab 1: Browse Projects ──────────────────────────────────────────────────
with tab_browse:
    st.markdown("### 🔍 Available Offset Projects")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        region_filter = st.selectbox(
            "Filter by Region",
            ["All Regions"] + list_regions(),
        )
    with col_f2:
        type_filter = st.selectbox(
            "Filter by Project Type",
            ["All Types"] + list_project_types(),
        )

    projects = list_offset_projects(
        region=region_filter if region_filter != "All Regions" else None,
    )
    if type_filter != "All Types":
        projects = [p for p in projects if p["type"] == type_filter]

    # ── Project cards ───────────────────────────────────────────────────
    for proj in projects:
        key = proj["key"]
        info = OFFSET_PROJECTS[key]
        remaining_pct = (
            (info["remaining_capacity_tonnes"] / info["annual_capacity_tonnes"]) * 100
            if info["annual_capacity_tonnes"] > 0
            else 0
        )

        benefits_str = ", ".join(info["co_benefits"])

        st.markdown(
            f"""
            <div style="border:1px solid #334155;border-radius:12px;padding:16px;
                        margin-bottom:14px;background:rgba(30,41,59,0.5);
                        border-left:4px solid {'#22c55e' if remaining_pct > 50 else '#facc15' if remaining_pct > 20 else '#ef4444'};">
                <h4 style="margin:0 0 6px;color:#38bdf8;">
                    {info['name']}
                </h4>
                <p style="margin:0 0 6px;color:#e2e8f0;">{info['description']}</p>
                <div style="display:flex;gap:16px;flex-wrap:wrap;">
                    <span style="color:#94a3b8;">📍 {info['region']}</span>
                    <span style="color:#94a3b8;">🏷️ {info['type']}</span>
                    <span style="color:#94a3b8;">📋 {info['registry']}</span>
                    <span style="color:#facc15;">⭐ {info['rating']}/5.0</span>
                    <span style="color:#22c55e;">💰 ${info['price_per_tonne']:.2f}/tonne</span>
                    <span style="color:#38bdf8;">📦 {info['remaining_capacity_tonnes']:,}t remaining ({remaining_pct:.0f}%)</span>
                </div>
                <p style="margin:6px 0 0;color:#94a3b8;">🌿 Co-benefits: {benefits_str}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Purchase form ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💳 Purchase Offsets")

    with st.form("purchase_offset"):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            purchase_project = st.selectbox(
                "Select Project",
                list(OFFSET_PROJECTS.keys()),
                format_func=lambda k: OFFSET_PROJECTS[k]["name"],
            )
        with col_p2:
            purchase_tonnes = st.number_input(
                "Tonnes CO₂",
                min_value=0.1,
                value=1.0,
                step=0.5,
            )
        with col_p3:
            if purchase_project:
                cost_preview = calculate_offset_cost(purchase_project, purchase_tonnes)
                st.metric(
                    "Estimated Cost",
                    f"${cost_preview['total_cost_usd']:.2f}",
                    delta=f"{cost_preview['rating']:.1f}⭐ rated",
                )

        purchase_btn = st.form_submit_button("🌍 Purchase Offset", use_container_width=True, type="primary")

        if purchase_btn:
            with st.spinner("Processing offset purchase..."):
                cert = generate_certificate(user_id, purchase_project, purchase_tonnes, cost_preview["total_cost_usd"])
                row_id = save_offset_transaction(
                    user_id,
                    purchase_project,
                    purchase_tonnes,
                    cost_preview["total_cost_usd"],
                    cert.certificate_id,
                )
                if row_id:
                    st.success(
                        f"✅ Offset purchased! Certificate: **{cert.certificate_id}**\n\n"
                        f"{format_certificate_text(cert)}"
                    )
                else:
                    st.error("Failed to save offset purchase.")


# ── Tab 2: Portfolio ────────────────────────────────────────────────────────
with tab_portfolio:
    st.markdown("### 💼 My Offset Portfolio")

    transactions = get_offset_transactions(user_id)
    goal = get_offset_goal(user_id)
    annual_fp = goal["annual_footprint_tonnes"] if goal else 0.0

    if not transactions:
        st.info(
            "No offset purchases yet. Browse projects and purchase offsets "
            "to build your portfolio."
        )
    else:
        portfolio = calculate_portfolio_summary(transactions, annual_fp)

        # ── Summary metrics ─────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌍 Total Offset", f"{portfolio.total_tonnes_offset:,.1f} tonnes")
        c2.metric("💰 Total Spent", f"${portfolio.total_cost_usd:,.2f}")
        c3.metric("📊 Projects", str(portfolio.total_projects))
        c4.metric("⭐ Portfolio Rating", f"{portfolio.portfolio_rating}/5.0")

        if annual_fp > 0:
            c5, c6 = st.columns(2)
            c5.metric(
                "📈 Offset vs Footprint",
                f"{portfolio.offset_vs_footprint_pct:.1f}%",
                delta=f"{portfolio.net_remaining_tonnes:+,.1f}t remaining",
                delta_color="inverse" if portfolio.net_remaining_tonnes > 0 else "normal",
            )
            if portfolio.is_net_zero:
                c6.metric("🎉 Status", "✅ Net Zero Achieved!")
            else:
                c6.metric("📉 Net Remaining", f"{portfolio.net_remaining_tonnes:,.1f} tonnes")

        # ── Project breakdown chart ─────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 Portfolio Breakdown")

        col_pie, col_bar = st.columns(2)
        with col_pie:
            proj_names = [
                OFFSET_PROJECTS.get(k, {}).get("name", k)
                for k in portfolio.project_breakdown
            ]
            fig_pie = px.pie(
                values=list(portfolio.project_breakdown.values()),
                names=proj_names,
                title="Tonnes by Project",
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Teal_r,
            )
            fig_pie.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_bar:
            # Transaction history bar chart
            tx_dates = [t.get("created_at", "")[:10] for t in reversed(transactions)]
            tx_tonnes = [t.get("tonnes_co2", 0) for t in reversed(transactions)]
            fig_tx = go.Figure()
            fig_tx.add_trace(go.Bar(
                x=tx_dates,
                y=tx_tonnes,
                marker_color="#22c55e",
                name="Tonnes Offset",
            ))
            fig_tx.update_layout(
                title="Offset Purchases Over Time",
                xaxis_title="Date",
                yaxis_title="Tonnes CO₂",
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_tx, use_container_width=True)

        # ── Transaction table ───────────────────────────────────────────
        st.markdown("### 📋 Transaction History")
        tx_rows = []
        for t in transactions:
            tx_rows.append({
                "Date": t.get("created_at", "")[:10],
                "Project": t.get("project_name", ""),
                "Tonnes": t.get("tonnes_co2", 0),
                "Cost ($)": t.get("cost_usd", 0),
                "Certificate": t.get("certificate_id", ""),
                "Status": t.get("status", ""),
            })
        st.dataframe(pd.DataFrame(tx_rows), use_container_width=True, hide_index=True)


# ── Tab 3: Net-Zero Roadmap ────────────────────────────────────────────────
with tab_roadmap:
    st.markdown("### 🗺️ Net-Zero Roadmap")

    goal = get_offset_goal(user_id)
    transactions = get_offset_transactions(user_id)
    portfolio = calculate_portfolio_summary(transactions, goal["annual_footprint_tonnes"] if goal else 0.0)

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        footprint_input = st.number_input(
            "Annual Footprint (tonnes CO₂)",
            min_value=0.1,
            value=goal["annual_footprint_tonnes"] if goal else 5.0,
            step=0.5,
        )
    with col_r2:
        reduction_rate = st.slider(
            "Annual Footprint Reduction Rate (%)",
            min_value=0.0,
            max_value=30.0,
            value=goal["target_reduction_pct"] if goal else 5.0,
            step=0.5,
        )

    new_offsets = st.number_input(
        "New Offsets Purchased Per Year (tonnes)",
        min_value=0.0,
        value=goal["target_new_offsets_per_year"] if goal else 2.0,
        step=0.5,
    )

    roadmap_btn = st.button("🗺️ Generate Roadmap", use_container_width=True, type="primary")

    if roadmap_btn:
        with st.spinner("Projecting net-zero timeline..."):
            projection = project_net_zero_timeline(
                current_footprint_tonnes=footprint_input,
                current_offset_tonnes=portfolio.total_tonnes_offset,
                annual_reduction_rate_pct=reduction_rate,
                annual_new_offsets_tonnes=new_offsets,
                years_ahead=30,
            )
            st.session_state.roadmap = projection
            st.session_state.roadmap_footprint = footprint_input

    roadmap = st.session_state.get("roadmap")
    if roadmap:
        # ── Timeline metrics ────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌍 Current Footprint", f"{roadmap.current_footprint_tonnes:.1f}t")
        c2.metric("🌿 Current Offset", f"{roadmap.current_offset_tonnes:.1f}t")
        if roadmap.years_to_net_zero is not None:
            c3.metric("🎯 Years to Net-Zero", f"{roadmap.years_to_net_zero:.1f}")
            c4.metric("📅 Target Year", str(roadmap.target_year))
        else:
            c3.metric("🎯 Years to Net-Zero", "Beyond horizon")
            c4.metric("📅 Target Year", "N/A")

        # ── Projection chart ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📈 Projection Chart")

        months = [m["month"] for m in roadmap.monthly_projection]
        footprints = [m["footprint_tonnes"] for m in roadmap.monthly_projection]
        offsets = [m["offset_tonnes"] for m in roadmap.monthly_projection]
        nets = [m["net_emissions"] for m in roadmap.monthly_projection]

        fig_proj = go.Figure()
        fig_proj.add_trace(go.Scatter(
            x=months, y=footprints,
            mode="lines", name="Footprint",
            line=dict(color="#ef4444", width=2),
        ))
        fig_proj.add_trace(go.Scatter(
            x=months, y=offsets,
            mode="lines", name="Cumulative Offsets",
            line=dict(color="#22c55e", width=2),
        ))
        fig_proj.add_trace(go.Scatter(
            x=months, y=nets,
            mode="lines", name="Net Emissions",
            line=dict(color="#38bdf8", width=2, dash="dot"),
        ))
        fig_proj.add_hline(y=0, line_dash="dash", line_color="#facc15", annotation_text="Net-Zero Line")

        if roadmap.years_to_net_zero:
            crossing_month = int(roadmap.years_to_net_zero * 12)
            fig_proj.add_vline(
                x=crossing_month,
                line_dash="dash",
                line_color="#22c55e",
                annotation_text=f"Net-Zero ({roadmap.target_year})",
            )

        fig_proj.update_layout(
            title="Net-Zero Projection",
            xaxis_title="Months from Now",
            yaxis_title="Tonnes CO₂",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_proj, use_container_width=True)

        # ── Milestones ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🏁 Roadmap Milestones")

        for ms in roadmap.milestones:
            icon = "✅" if ms["met"] else "⏳" if ms["type"] != "goal" else "🎯"
            year_text = f"+{ms['year_offset']:.1f} years" if ms["year_offset"] > 0 else "Now"
            st.markdown(
                f"""
                <div style="border:1px solid #334155;border-radius:8px;padding:12px;
                            margin-bottom:8px;background:rgba(30,41,59,0.5);
                            border-left:4px solid {'#22c55e' if ms['met'] else '#facc15'};">
                    <strong>{icon} {ms['label']}</strong>
                    <span style="color:#94a3b8;margin-left:12px;">{year_text}</span>
                    <br><small style="color:#cbd5e1;">{ms['description']}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Save goal ───────────────────────────────────────────────────
        st.markdown("---")
        if st.button("💾 Save Roadmap as Goal", use_container_width=True):
            row_id = save_offset_goal(user_id, footprint_input, reduction_rate, new_offsets)
            if row_id:
                st.success("✅ Offset goal saved!")
            else:
                st.error("Failed to save goal.")
    else:
        st.info("Set your parameters above and click **Generate Roadmap** to project your net-zero timeline.")


# ── Tab 4: Certificates ─────────────────────────────────────────────────────
with tab_certs:
    st.markdown("### 📜 Offset Certificates")

    transactions = get_offset_transactions(user_id)
    certs = [t for t in transactions if t.get("certificate_id")]

    if not certs:
        st.info("No certificates yet. Purchase offsets to generate certificates.")
    else:
        for tx in certs:
            cert = generate_certificate(
                user_id,
                tx["project_key"],
                tx["tonnes_co2"],
                tx["cost_usd"],
            )
            cert.certificate_id = tx["certificate_id"]
            cert.issued_date = tx.get("created_at", "")

            st.markdown(
                f"""
                <div style="border:2px solid #22c55e;border-radius:12px;padding:16px;
                            margin-bottom:14px;background:rgba(30,41,59,0.5);">
                    <h4 style="margin:0 0 8px;color:#22c55e;">📜 {cert.certificate_id}</h4>
                    <p style="margin:0;color:#e2e8f0;">
                        <strong>{cert.project_name}</strong> — {cert.project_type}
                    </p>
                    <p style="margin:4px 0;color:#cbd5e1;">
                        {cert.tonnes_co2:.2f} tonnes CO₂ offset &nbsp;|&nbsp;
                        ${cert.cost_usd:.2f} &nbsp;|&nbsp;
                        {cert.registry}
                    </p>
                    <p style="margin:4px 0;color:#94a3b8;">
                        Issued: {cert.issued_date} &nbsp;|&nbsp;
                        <a href="{cert.verification_url}" target="_blank" style="color:#38bdf8;">Verify ↗</a>
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Download all certificates as text ──────────────────────────
        all_certs_text = "\n\n".join(
            format_certificate_text(
                generate_certificate(user_id, t["project_key"], t["tonnes_co2"], t["cost_usd"])
            )
            for t in certs
        )
        st.download_button(
            "📥 Download All Certificates (TXT)",
            data=all_certs_text,
            file_name="offset_certificates.txt",
            mime="text/plain",
        )


# ── Tab 5: Offset Goals ────────────────────────────────────────────────────
with tab_goals:
    st.markdown("### 🎯 Offset Goals")

    goal = get_offset_goal(user_id)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("#### Set / Update Goal")
        with st.form("offset_goal_form"):
            new_footprint = st.number_input(
                "Annual Footprint (tonnes CO₂)",
                min_value=0.1,
                value=goal["annual_footprint_tonnes"] if goal else 5.0,
                step=0.5,
            )
            new_reduction = st.slider(
                "Annual Reduction Target (%)",
                0.0, 30.0,
                value=goal["target_reduction_pct"] if goal else 5.0,
                step=0.5,
            )
            new_offsets_yr = st.number_input(
                "New Offsets Per Year (tonnes)",
                min_value=0.0,
                value=goal["target_new_offsets_per_year"] if goal else 2.0,
                step=0.5,
            )
            if st.form_submit_button("🎯 Save Goal", use_container_width=True):
                save_offset_goal(user_id, new_footprint, new_reduction, new_offsets_yr)
                st.success("Goal saved!")
                st.rerun()

    with col_g2:
        st.markdown("#### Current Goal")
        if goal:
            fp = goal["annual_footprint_tonnes"]
            red = goal["target_reduction_pct"]
            off = goal["target_new_offsets_per_year"]

            transactions = get_offset_transactions(user_id)
            portfolio = calculate_portfolio_summary(transactions, fp)

            st.metric("🌍 Annual Footprint", f"{fp:.1f} tonnes")
            st.metric("📉 Annual Reduction", f"{red:.1f}%")
            st.metric("🌿 Annual New Offsets", f"{off:.1f} tonnes")
            st.metric("📊 Current Offset Total", f"{portfolio.total_tonnes_offset:.1f} tonnes")
            st.metric(
                "📈 Offset Coverage",
                f"{portfolio.offset_vs_footprint_pct:.1f}%",
                delta=f"{portfolio.net_remaining_tonnes:+,.1f}t remaining",
                delta_color="inverse" if portfolio.net_remaining_tonnes > 0 else "normal",
            )

            if portfolio.is_net_zero:
                st.success("🎉 You've achieved net-zero through offsets!")
        else:
            st.info("No goal set yet. Create one on the left.")
