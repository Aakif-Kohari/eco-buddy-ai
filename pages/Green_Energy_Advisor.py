"""Green Energy Advisor & Solar ROI Calculator page for EcoBuddy AI.

Compare solar panel systems, model battery storage economics, match
green energy providers, and receive a personalised clean energy plan.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from styles.theme import apply_theme
from green_energy_advisor import (
    GRID_INTENSITY,
    SOLAR_SYSTEMS,
    BATTERY_OPTIONS,
    calculate_solar_roi,
    calculate_battery_value,
    find_green_providers,
    build_energy_advisor_report,
    save_energy_assessment,
    get_energy_assessments,
    list_solar_systems,
    list_battery_options,
    list_green_providers,
    list_regions,
)

# ── Auth ─────────────────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='section-header'>⚡ Green Energy Advisor & Solar ROI Calculator</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Compare solar panel systems, model battery storage economics, find the "
    "best green energy provider, and build your personalised clean energy plan."
)
st.markdown("---")

# ── Global Input ─────────────────────────────────────────────────────────────
col_input1, col_input2, col_input3 = st.columns(3)
with col_input1:
    monthly_kwh = st.number_input(
        "Monthly Electricity (kWh)",
        min_value=10.0,
        value=st.session_state.get("electricity", 300.0),
        step=10.0,
    )
with col_input2:
    region = st.selectbox(
        "Region",
        list_regions(),
        index=0,
    )
with col_input3:
    roof_area = st.number_input(
        "Available Roof Area (m²)",
        min_value=0.0,
        value=50.0,
        step=5.0,
    )

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_solar, tab_battery, tab_providers, tab_report = st.tabs([
    "☀️ Solar Analysis",
    "🔋 Battery Storage",
    "⚡ Green Providers",
    "📋 Full Report",
])


# ── Tab 1: Solar Analysis ───────────────────────────────────────────────────
with tab_solar:
    st.markdown("### ☀️ Solar Panel System Analysis")

    systems = list_solar_systems()

    # System comparison table
    rows = []
    for s in systems:
        fits_roof = "✅" if s["roof_area_m2"] <= roof_area else "❌"
        rows.append({
            "System": s["name"],
            "Capacity": f"{s['capacity_kwp']} kWp",
            "Panels": s["panels"],
            "Roof Needed": f"{s['roof_area_m2']} m²",
            "Fits Roof": fits_roof,
            "Cost": f"${s['upfront_cost']:,}",
            "Annual kWh": f"{s['annual_kwh']:,}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Run analysis
    selected_system = st.selectbox(
        "Select System to Analyse",
        list(SOLAR_SYSTEMS.keys()),
        format_func=lambda k: SOLAR_SYSTEMS[k]["name"],
    )
    self_consumption = st.slider(
        "Self-Consumption Rate (%)",
        min_value=30,
        max_value=95,
        value=70,
        help="Percentage of solar energy consumed on-site vs exported to grid",
    ) / 100.0

    solar_btn = st.button("☀️ Run Solar Analysis", use_container_width=True, type="primary")

    if solar_btn:
        with st.spinner("Calculating solar ROI..."):
            result = calculate_solar_roi(
                selected_system, monthly_kwh, region,
                roof_area_m2=roof_area,
                self_consumption_pct=self_consumption,
            )
            st.session_state.solar_result = result

    solar_result = st.session_state.get("solar_result")
    if solar_result:
        r = solar_result

        # ── Summary metrics ─────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Net Upfront Cost", f"${r.net_upfront_cost:,.0f}", delta=f"Tax credit: ${r.tax_credit_usd:,.0f}")
        c2.metric("⏱️ Payback Period", f"{r.payback_years} years" if r.payback_years else "Beyond horizon")
        c3.metric("📈 Lifetime Savings", f"${r.lifetime_savings_usd:,.0f}")
        c4.metric("📊 ROI", f"{r.roi_pct:.0f}%")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("⚡ Annual Generation", f"{r.annual_kwh:,.0f} kWh")
        c6.metric("💵 Annual Savings", f"${r.annual_savings_usd:,.0f}")
        c7.metric("🌍 CO₂ Avoided", f"{r.annual_co2_avoided_kg:,.0f} kg/yr")
        c8.metric("💲 LCOE", f"${r.lcoe_kwh:.4f}/kWh")

        # ── Projection chart ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📈 25-Year Financial Projection")

        years = [p["year"] for p in r.yearly_projection]
        savings = [p["savings_usd"] for p in r.yearly_projection]
        cumulative = [p["cumulative_savings_usd"] for p in r.yearly_projection]

        fig_proj = go.Figure()
        fig_proj.add_trace(go.Bar(
            x=years, y=savings,
            name="Annual Savings",
            marker_color="#22c55e",
        ))
        fig_proj.add_trace(go.Scatter(
            x=years, y=cumulative,
            name="Cumulative Savings",
            line=dict(color="#38bdf8", width=3),
            yaxis="y2",
        ))
        fig_proj.add_hline(y=r.net_upfront_cost, line_dash="dash", line_color="#ef4444",
                          annotation_text=f"Net Upfront: ${r.net_upfront_cost:,.0f}")
        fig_proj.update_layout(
            title="Solar ROI Projection",
            xaxis_title="Year",
            yaxis_title="Annual Savings ($)",
            yaxis2=dict(title="Cumulative ($)", overlaying="y", side="right"),
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_proj, use_container_width=True)

        # ── CO₂ avoidance chart ─────────────────────────────────────────
        co2_vals = [p["co2_avoided_kg"] for p in r.yearly_projection]
        fig_co2 = go.Figure()
        fig_co2.add_trace(go.Bar(
            x=years, y=co2_vals,
            marker_color="#4ade80",
            name="CO₂ Avoided (kg)",
        ))
        fig_co2.update_layout(
            title="Annual CO₂ Avoided (kg)",
            xaxis_title="Year",
            yaxis_title="kg CO₂",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_co2, use_container_width=True)


# ── Tab 2: Battery Storage ──────────────────────────────────────────────────
with tab_battery:
    st.markdown("### 🔋 Battery Storage Analysis")

    surplus = st.number_input(
        "Estimated Daily Solar Surplus (kWh)",
        min_value=0.0,
        value=5.0,
        step=0.5,
        help="Average daily excess solar energy available to store",
    )

    battery_results = []
    for key in BATTERY_OPTIONS:
        result = calculate_battery_value(key, monthly_kwh, region, surplus)
        battery_results.append(result)

    # ── Comparison table ────────────────────────────────────────────────
    rows = []
    for b in battery_results:
        rows.append({
            "Battery": b.battery_name,
            "Capacity": f"{b.capacity_kwh} kWh",
            "Cost": f"${b.upfront_cost:,}",
            "Annual Value": f"${b.annual_value_usd:,.0f}",
            "Payback": f"{b.payback_years} years" if b.payback_years else "N/A",
            "Lifetime Value": f"${b.lifetime_value_usd:,.0f}",
            "Eff. Capacity": f"{b.effective_capacity_kwh} kWh",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Battery value chart ─────────────────────────────────────────────
    fig_bat = go.Figure()
    names = [b.battery_name for b in battery_results]
    upfronts = [b.upfront_cost for b in battery_results]
    lifetimes = [b.lifetime_value_usd for b in battery_results]

    fig_bat.add_trace(go.Bar(name="Upfront Cost", x=names, y=upfronts, marker_color="#ef4444"))
    fig_bat.add_trace(go.Bar(name="Lifetime Value", x=names, y=lifetimes, marker_color="#22c55e"))
    fig_bat.update_layout(
        barmode="group",
        title="Battery: Cost vs Lifetime Value",
        yaxis_title="USD",
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_bat, use_container_width=True)


# ── Tab 3: Green Providers ──────────────────────────────────────────────────
with tab_providers:
    st.markdown("### ⚡ Green Energy Provider Matching")

    providers = find_green_providers(region, monthly_kwh)

    if not providers:
        st.warning(f"No green energy providers found for region: {region}")
    else:
        for p in providers:
            price_vs = p.monthly_cost_usd - (monthly_kwh * GRID_INTENSITY.get(region, GRID_INTENSITY["Global"])["avg_electricity_cost_kwh"])
            price_delta = f"${price_vs:+,.0f}/mo vs current" if price_vs != 0 else "Same as current"

            st.markdown(
                f"""
                <div style="border:1px solid #334155;border-radius:12px;padding:16px;
                            margin-bottom:14px;background:rgba(30,41,59,0.5);
                            border-left:4px solid #22c55e;">
                    <h4 style="margin:0 0 6px;color:#38bdf8;">
                        {p.provider_name}
                        <span style="font-size:0.85em;color:#facc15;margin-left:12px;">
                            ⭐ {p.rating}/5.0 | Match: {p.match_score:.0f}%
                        </span>
                    </h4>
                    <p style="margin:0;color:#e2e8f0;">{p.plan_type}</p>
                    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:6px;">
                        <span style="color:#22c55e;">💰 ${p.monthly_cost_usd:,.0f}/mo ({price_delta})</span>
                        <span style="color:#4ade80;">🌍 Saves {p.annual_co2_savings_kg:,.0f} kg CO₂/yr</span>
                        <span style="color:#94a3b8;">📋 {', '.join(p.features[:3])}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Provider comparison chart ───────────────────────────────────
        st.markdown("---")
        fig_prov = go.Figure()
        fig_prov.add_trace(go.Bar(
            name="Monthly Cost",
            x=[p.provider_name for p in providers],
            y=[p.monthly_cost_usd for p in providers],
            marker_color="#38bdf8",
        ))
        current_monthly = monthly_kwh * GRID_INTENSITY.get(region, GRID_INTENSITY["Global"])["avg_electricity_cost_kwh"]
        fig_prov.add_hline(y=current_monthly, line_dash="dash", line_color="#ef4444",
                          annotation_text=f"Current: ${current_monthly:,.0f}/mo")
        fig_prov.update_layout(
            title="Provider Monthly Cost Comparison",
            yaxis_title="USD/month",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_prov, use_container_width=True)


# ── Tab 4: Full Report ──────────────────────────────────────────────────────
with tab_report:
    st.markdown("### 📋 Comprehensive Energy Advisor Report")

    report_btn = st.button("📋 Generate Full Report", use_container_width=True, type="primary")

    if report_btn:
        with st.spinner("Building comprehensive energy report..."):
            report = build_energy_advisor_report(user_id, monthly_kwh, region)
            st.session_state.energy_report = report

    report = st.session_state.get("energy_report")
    if report:
        # ── Summary banner ──────────────────────────────────────────────
        st.markdown(
            f"""
            <div style="background:#1e293b;padding:20px;border-radius:14px;
                        border-left:6px solid #22c55e;margin-bottom:20px;">
                <h3 style="margin:0;color:#22c55e;">
                    ⚡ Your Clean Energy Potential
                </h3>
                <p style="margin:6px 0 0;color:#cbd5e1;">
                    Monthly Usage: {report.monthly_kwh:,.0f} kWh &nbsp;|&nbsp;
                    Region: {report.region} &nbsp;|&nbsp;
                    Grid Intensity: {report.grid_intensity} kg CO₂/kWh
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Current Annual Cost", f"${report.current_annual_cost:,.0f}")
        c2.metric("🌍 Current CO₂", f"{report.current_annual_co2_kg:,.0f} kg/yr")
        c3.metric(
            "💵 Savings Potential",
            f"${report.total_annual_savings_potential:,.0f}/yr",
        )
        c4.metric(
            "🌿 CO₂ Reduction",
            f"{report.total_annual_co2_reduction_kg:,.0f} kg/yr",
        )

        # ── Best picks ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🏆 Recommended Setup")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if report.best_solar:
                s = report.best_solar
                st.markdown(
                    f"**☀️ Solar:** {s.system_name}\n\n"
                    f"Payback: {s.payback_years} years | "
                    f"Savings: ${s.annual_savings_usd:,.0f}/yr\n\n"
                    f"ROI: {s.roi_pct:.0f}% | NPV: ${s.npv_usd:,.0f}"
                )
        with col_b:
            if report.best_battery:
                b = report.best_battery
                st.markdown(
                    f"**🔋 Battery:** {b.battery_name}\n\n"
                    f"Payback: {b.payback_years} years | "
                    f"Value: ${b.annual_value_usd:,.0f}/yr\n\n"
                    f"Capacity: {b.capacity_kwh} kWh"
                )
        with col_c:
            if report.best_provider:
                p = report.best_provider
                st.markdown(
                    f"**⚡ Provider:** {p.provider_name}\n\n"
                    f"Plan: {p.plan_type}\n\n"
                    f"Cost: ${p.monthly_cost_usd:,.0f}/mo | "
                    f"CO₂ saved: {p.annual_co2_savings_kg:,.0f} kg/yr"
                )

        # ── Recommendations ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 💡 Recommendations")
        for rec in report.recommendations:
            st.markdown(f"- {rec}")

        # ── System comparison table ─────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 All Solar Systems Comparison")
        solar_rows = []
        for s in report.solar_options:
            solar_rows.append({
                "System": s.system_name,
                "Capacity": f"{s.capacity_kwp} kWp",
                "Cost": f"${s.net_upfront_cost:,.0f}",
                "Annual kWh": f"{s.annual_kwh:,.0f}",
                "Payback": f"{s.payback_years} yr" if s.payback_years else "N/A",
                "25yr Savings": f"${s.lifetime_savings_usd:,.0f}",
                "ROI": f"{s.roi_pct:.0f}%",
                "NPV": f"${s.npv_usd:,.0f}",
                "LCOE": f"${s.lcoe_kwh:.4f}",
            })
        st.dataframe(pd.DataFrame(solar_rows), use_container_width=True, hide_index=True)

        # ── Save assessment ─────────────────────────────────────────────
        st.markdown("---")
        if st.button("💾 Save Energy Assessment", use_container_width=True):
            row_id = save_energy_assessment(user_id, report)
            if row_id:
                st.success(f"✅ Energy assessment saved (ID: {row_id})!")
            else:
                st.error("Failed to save assessment.")
