"""Seasonal Carbon Optimiser — time-aware footprint analysis page for EcoBuddy AI.

Provides users with seasonally-adjusted carbon footprint calculations,
weather-aware eco scoring, actionable seasonal recommendations, a 12-month
forecast, and a quarterly comparison — all tailored to their hemisphere.
"""

from __future__ import annotations

import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from styles.theme import apply_theme
from src.carbon.emissions import calculate_footprint, calculate_eco_score
from src.carbon.seasonal_carbon_optimizer import (
    calculate_seasonal_footprint,
    seasonal_eco_score,
    generate_seasonal_recommendations,
    generate_seasonal_report,
    generate_quarterly_comparison,
    generate_monthly_forecast,
    get_all_adjustments,
    HEMISPHERES,
    MONTHS,
)

# ── Auth ─────────────────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

# ── Page Header ──────────────────────────────────────────────────────────────
st.markdown(
    "<div class='section-header'>🌦️ Seasonal Carbon Optimiser</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Discover how your carbon footprint changes across seasons and hemispheres. "
    "Get time-sensitive recommendations, a 12-month forecast, and a quarterly "
    "comparison to plan your sustainability journey throughout the year."
)
st.markdown("---")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_input, tab_analysis, tab_forecast, tab_quarterly, tab_adjustments = st.tabs([
    "🌍 Enter Footprint Data",
    "📊 Seasonal Analysis",
    "📈 12-Month Forecast",
    "🗺️ Quarterly Comparison",
    "⚙️ Adjustment Factors",
])

# ── Store state ──────────────────────────────────────────────────────────────
if "seasonal_analysis" not in st.session_state:
    st.session_state.seasonal_analysis = None


# ── Tab 1: Input ─────────────────────────────────────────────────────────────
with tab_input:
    st.markdown("### 📝 Enter Your Carbon Footprint Data")
    st.markdown(
        "Provide your baseline annual footprint values. The optimiser will "
        "adjust them for seasonal effects based on your selected hemisphere."
    )

    col_h, col_m = st.columns(2)
    with col_h:
        hemisphere = st.selectbox(
            "🌍 Hemisphere",
            ["northern", "southern"],
            index=0,
            help="Seasons are inverted between hemispheres.",
        )
    with col_m:
        month = st.selectbox(
            "📅 Analysis Month",
            MONTHS,
            index=datetime.date.today().month - 1,
            format_func=lambda m: datetime.date(2025, m, 1).strftime("%B"),
            help="The target month for seasonal adjustments.",
        )

    st.markdown("---")
    st.markdown("#### 🚗 Transportation")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        transport = st.selectbox(
            "Primary Transport",
            ["Car", "Public Transport", "Bike", "Walking"],
            index=0,
        )
    with col_t2:
        distance = st.number_input(
            "Daily Distance (km)",
            min_value=0.0, value=15.0, step=1.0,
        )
    with col_t3:
        flights = st.number_input(
            "Annual Flights",
            min_value=0, value=2, step=1,
        )

    st.markdown("#### ⚡ Energy & Diet")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        electricity = st.number_input(
            "Monthly Electricity (kWh)",
            min_value=0.0, value=250.0, step=10.0,
        )
    with col_e2:
        diet = st.selectbox(
            "Diet Type",
            ["Vegetarian", "Non-Vegetarian", "Vegan", "Omnivore", "Heavy Meat"],
            index=1,
        )

    region = st.selectbox(
        "Region (for emission factors)",
        ["Global", "US", "UK", "EU"],
        index=0,
    )

    st.markdown("---")
    calc_btn = st.button(
        "🌦️ Run Seasonal Analysis",
        use_container_width=True,
        type="primary",
    )

    if calc_btn:
        with st.spinner("Calculating seasonally-adjusted footprint..."):
            raw_fp, contributors = calculate_footprint(
                transport=transport,
                distance=distance,
                electricity=electricity,
                diet=diet,
                flights=flights,
                region=region,
            )
            report = generate_seasonal_report(
                raw_footprint_kg=raw_fp,
                contributors=contributors,
                month=month,
                hemisphere=hemisphere,
            )
            st.session_state.seasonal_analysis = {
                "raw_fp": raw_fp,
                "contributors": contributors,
                "report": report,
                "transport": transport,
                "distance": distance,
                "electricity": electricity,
                "diet": diet,
                "flights": flights,
                "region": region,
                "month": month,
                "hemisphere": hemisphere,
            }
            st.success("✅ Seasonal analysis complete!")


# ── Tab 2: Analysis ──────────────────────────────────────────────────────────
with tab_analysis:
    data = st.session_state.seasonal_analysis
    if data is None:
        st.info(
            "Please enter your footprint data in the **Enter Footprint Data** tab "
            "and click *Run Seasonal Analysis*."
        )
    else:
        report = data["report"]
        sc = src.reporting.report.score_data
        fp = src.reporting.report.footprint_result

        # ── Score banner ─────────────────────────────────────────────────
        st.markdown(
            f"""
            <div style="background-color:#1e293b;padding:24px;border-radius:14px;
                        border-left:6px solid {sc['color']};margin-bottom:24px;">
                <h3 style="margin:0;color:{sc['color']};">
                    Seasonal Eco Score: {sc['score']}/100 — Grade {sc['grade']}
                </h3>
                <p style="margin:6px 0 0;color:#cbd5e1;">
                    {sc['status']} &nbsp;|&nbsp;
                    Season: {sc['season'].title()} ({sc['hemisphere'].title()})
                    &nbsp;|&nbsp; Month: {sc['month']}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Key metrics ──────────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌍 Raw Footprint", f"{fp.raw_footprint_kg:,.0f} kg")
        c2.metric(
            "🌦️ Adjusted Footprint",
            f"{fp.adjusted_footprint_kg:,.0f} kg",
            delta=f"{fp.delta_pct:+.1f}%",
            delta_color="inverse",
        )
        c3.metric(
            "📈 vs Seasonal Benchmark",
            f"{sc['vs_benchmark_pct']:+.1f}%",
            delta=f"Benchmark: {sc['benchmark_kg']:,.0f} kg",
        )
        c4.metric(
            "💡 Monthly Savings Potential",
            f"{src.reporting.report.monthly_savings_potential_kg:,.0f} kg",
        )

        st.markdown("---")

        # ── Category breakdown comparison ────────────────────────────────
        st.markdown("### 📊 Category Breakdown: Raw vs Seasonally Adjusted")
        cats = list(fp.category_breakdown.keys())
        raw_vals = [fp.category_breakdown[c] for c in cats]
        adj_vals = [fp.adjusted_breakdown[c] for c in cats]

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name="Raw (Annual Baseline)",
            x=cats, y=raw_vals,
            marker_color="#64748b",
        ))
        fig_bar.add_trace(go.Bar(
            name=f"Adjusted ({src.reporting.report.season.title()})",
            x=cats, y=adj_vals,
            marker_color=sc["color"],
        ))
        fig_bar.update_layout(
            barmode="group",
            title="Category Emissions Comparison",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Pie chart of adjusted breakdown ──────────────────────────────
        col_pie1, col_pie2 = st.columns(2)
        with col_pie1:
            fig_pie = px.pie(
                values=adj_vals,
                names=cats,
                title="Adjusted Emission Share",
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Teal_r,
            )
            fig_pie.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_pie2:
            fig_pie2 = px.pie(
                values=raw_vals,
                names=cats,
                title="Raw Emission Share",
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Greys_r,
            )
            fig_pie2.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_pie2, use_container_width=True)

        # ── Recommendations ──────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🎯 Seasonal Recommendations")

        if src.reporting.report.recommendations:
            for rec in src.reporting.report.recommendations:
                diff_icon = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(
                    rec["difficulty"], "⚪"
                )
                st.markdown(
                    f"""
                    <div style="border:1px solid #334155;border-radius:10px;padding:14px;
                                margin-bottom:10px;background:rgba(30,41,59,0.5);">
                        <h4 style="margin:0 0 6px;color:#38bdf8;">
                            {diff_icon} {rec['action']}
                            <span style="font-size:0.85em;color:#4ade80;">
                                (Save ~{rec['impact_kg_year']} kg CO₂/year)
                            </span>
                        </h4>
                        <p style="margin:0 0 4px;color:#e2e8f0;">{rec['tip']}</p>
                        <small style="color:#94a3b8;">
                            Category: {rec['category'].title()}
                        </small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success(
                "🌟 No specific seasonal recommendations — your profile "
                "is well-optimised for this time of year!"
            )

        # ── Summary ──────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📋 Report Summary")
        st.code(src.reporting.report.summary_text, language="text")


# ── Tab 3: 12-Month Forecast ────────────────────────────────────────────────
with tab_forecast:
    data = st.session_state.seasonal_analysis
    if data is None:
        st.info("Run a seasonal analysis first to see the 12-month forecast.")
    else:
        st.markdown("### 📈 12-Month Seasonal Footprint Forecast")
        st.markdown(
            "This chart shows how your footprint would change each month "
            "based on seasonal adjustment factors."
        )

        forecast = generate_monthly_forecast(
            data["raw_fp"], data["contributors"], data["hemisphere"],
        )
        df_fc = pd.DataFrame(forecast)

        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(
            x=df_fc["month_name"],
            y=df_fc["adjusted_kg"],
            mode="lines+markers+text",
            name="Adjusted Footprint",
            line=dict(color="#38bdf8", width=3),
            marker=dict(size=10, color=df_fc["color"]),
            text=df_fc["adjusted_kg"].apply(lambda v: f"{v:,.0f}"),
            textposition="top center",
        ))
        # Raw baseline reference line
        fig_fc.add_hline(
            y=data["raw_fp"],
            line_dash="dash",
            line_color="#64748b",
            annotation_text=f"Annual Baseline ({data['raw_fp']:,.0f} kg)",
        )
        fig_fc.update_layout(
            title="Monthly Seasonal Footprint Forecast",
            xaxis_title="Month",
            yaxis_title="Adjusted Footprint (kg CO₂)",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_fc, use_container_width=True)

        # ── Score trend ──────────────────────────────────────────────────
        fig_sc = go.Figure()
        fig_sc.add_trace(go.Bar(
            x=df_fc["month_name"],
            y=df_fc["score"],
            marker_color=df_fc["color"],
            text=df_fc["grade"],
            textposition="outside",
            name="Eco Score",
        ))
        fig_sc.update_layout(
            title="Monthly Seasonal Eco Score",
            xaxis_title="Month",
            yaxis_title="Score (0–100)",
            yaxis=dict(range=[0, 105]),
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_sc, use_container_width=True)

        # ── Detailed table ───────────────────────────────────────────────
        st.markdown("### 📋 Detailed Monthly Breakdown")
        display_df = df_fc[["month_name", "season", "adjusted_kg", "score", "grade", "delta_pct"]].copy()
        display_df.columns = ["Month", "Season", "Adjusted (kg CO₂)", "Score", "Grade", "Δ vs Baseline (%)"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv = df_fc.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download 12-Month Forecast (CSV)",
            data=csv,
            file_name="seasonal_forecast_12months.csv",
            mime="text/csv",
        )


# ── Tab 4: Quarterly Comparison ─────────────────────────────────────────────
with tab_quarterly:
    data = st.session_state.seasonal_analysis
    if data is None:
        st.info("Run a seasonal analysis first to see the quarterly comparison.")
    else:
        st.markdown("### 🗺️ Quarterly Footprint Comparison")
        st.markdown(
            "Compare your seasonally-adjusted footprint across all four "
            "calendar quarters to identify the best and worst periods."
        )

        comp = generate_quarterly_comparison(
            data["raw_fp"], data["contributors"], data["hemisphere"],
        )

        # ── Quarterly metrics ────────────────────────────────────────────
        cols = st.columns(4)
        for idx, (q_num, q_data) in enumerate(comp.quarters.items()):
            with cols[idx]:
                st.metric(
                    label=f"Q{q_num} ({q_data['season'].title()})",
                    value=f"{q_data['adjusted_kg']:,.0f} kg",
                    delta=f"{q_data['delta_pct']:+.1f}%",
                    delta_color="inverse",
                )
                st.caption(
                    f"Score: {q_data['score']}/100 ({q_data['grade']})  |  "
                    f"Recs: {q_data['recommendation_count']}"
                )

        st.markdown("---")

        # ── Bar chart ────────────────────────────────────────────────────
        q_data_list = list(comp.quarters.values())
        fig_q = go.Figure()
        fig_q.add_trace(go.Bar(
            name="Raw Baseline",
            x=[f"Q{q['quarter']}" for q in q_data_list],
            y=[q["raw_kg"] for q in q_data_list],
            marker_color="#64748b",
        ))
        fig_q.add_trace(go.Bar(
            name="Seasonally Adjusted",
            x=[f"Q{q['quarter']}" for q in q_data_list],
            y=[q["adjusted_kg"] for q in q_data_list],
            marker_color=["#22c55e" if q["quarter"] == comp.best_quarter
                          else "#ef4444" if q["quarter"] == comp.worst_quarter
                          else "#38bdf8"
                          for q in q_data_list],
        ))
        fig_q.update_layout(
            barmode="group",
            title="Quarterly Footprint Comparison",
            yaxis_title="kg CO₂",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_q, use_container_width=True)

        # ── Summary ──────────────────────────────────────────────────────
        st.info(
            f"🏆 **Best Quarter:** Q{comp.best_quarter} "
            f"({comp.quarters[comp.best_quarter]['adjusted_kg']:,.0f} kg)  |  "
            f"⚠️ **Worst Quarter:** Q{comp.worst_quarter} "
            f"({comp.quarters[comp.worst_quarter]['adjusted_kg']:,.0f} kg)  |  "
            f"📊 **Annual Adjusted Total:** {comp.annual_adjusted_kg:,.0f} kg"
        )


# ── Tab 5: Adjustment Factors ───────────────────────────────────────────────
with tab_adjustments:
    st.markdown("### ⚙️ Seasonal Adjustment Factors Reference")
    st.markdown(
        "These multipliers are applied to your baseline emissions to account "
        "for seasonal behavioural and climate-driven changes. A factor of 1.20 "
        "means emissions in that season are 20% higher than the annual baseline."
    )

    hemisphere_ref = st.selectbox(
        "View factors for hemisphere",
        ["northern", "southern"],
        index=0,
        key="adj_hem_ref",
    )

    all_adj = {}
    for cat in ["electricity", "transport", "diet", "flights", "water"]:
        all_adj[cat] = {}
        for m in MONTHS:
            all_adj[cat][m] = get_all_adjustments(m, hemisphere_ref)[cat]

    df_adj = pd.DataFrame(all_adj)
    df_adj.index = [
        datetime.date(2025, m, 1).strftime("%B") for m in MONTHS
    ]
    df_adj.index.name = "Month"
    df_adj.columns = [c.title() for c in df_adj.columns]

    st.dataframe(
        df_adj.style.format("{:.2f}").background_gradient(
            cmap="RdYlGn_r", axis=None,
        ),
        use_container_width=True,
    )

    # ── Heatmap ──────────────────────────────────────────────────────────
    fig_heat = px.imshow(
        df_adj.values,
        labels=dict(x="Category", y="Month", color="Factor"),
        x=df_adj.columns,
        y=df_adj.index,
        color_continuous_scale="RdYlGn_r",
        aspect="auto",
        title=f"Seasonal Adjustment Heatmap ({hemisphere_ref.title()} Hemisphere)",
    )
    fig_heat.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 📖 How to Interpret")
    st.markdown(
        "- **Factor > 1.0** — Emissions are *higher* than baseline (e.g. winter heating)\n"
        "- **Factor < 1.0** — Emissions are *lower* than baseline (e.g. spring mild weather)\n"
        "- **Factor = 1.0** — No seasonal adjustment (baseline)"
    )
