"""Carbon Footprint Benchmarking — compare, rank, and improve page for EcoBuddy AI.

Lets users compare their footprint against global/country averages, discover
their lifestyle archetype, analyse historical trends, view the community
leaderboard, and receive a prioritised improvement plan.
"""

from __future__ import annotations

import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from styles.theme import apply_theme
from emissions import calculate_footprint, calculate_eco_score
from carbon_benchmarking import (
    COUNTRY_BENCHMARKS,
    LIFESTYLE_ARCHETYPES,
    compare_against_country,
    compare_against_all_countries,
    compute_global_percentile,
    find_closest_lifestyle,
    analyse_trend,
    generate_benchmark_insights,
    generate_improvement_actions,
    build_full_benchmark_report,
    get_user_assessment_history,
    get_leaderboard,
    get_user_rank,
    list_available_countries,
    list_lifestyle_archetypes,
    LeaderboardEntry,
    _score_to_badge,
)

# ── Auth ─────────────────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='section-header'>📊 Carbon Footprint Benchmarking</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Compare your footprint against countries, lifestyle archetypes, and the "
    "global community. Discover where you rank, track your trend, and receive "
    "a prioritised improvement plan."
)
st.markdown("---")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_overview, tab_countries, tab_lifestyle, tab_trend, tab_leaderboard, tab_plan = st.tabs([
    "🌍 Overview",
    "🏳️ Country Comparison",
    "👤 Lifestyle Match",
    "📈 Trend Analysis",
    "🏆 Leaderboard",
    "📋 Improvement Plan",
])


# ── Helper: build footprint from session state or recalculate ────────────────
def _get_or_calc_footprint() -> tuple[float, int, dict[str, float]]:
    """Return (footprint_kg, eco_score, contributors) from session or recalc."""
    if "benchmark_data" in st.session_state:
        d = st.session_state.benchmark_data
        return d["footprint"], d["eco_score"], d["contributors"]

    transport = st.session_state.get("transport", "Car")
    distance = st.session_state.get("distance", 10.0)
    electricity = st.session_state.get("electricity", 200.0)
    diet = st.session_state.get("diet", "Vegetarian")
    flights = st.session_state.get("flights", 0)
    region = st.session_state.get("region", "Global")

    fp, contributors = calculate_footprint(transport, distance, electricity, diet, flights, region)
    score = calculate_eco_score(fp, contributors)
    return fp, score, contributors


# ── Tab 1: Overview ──────────────────────────────────────────────────────────
with tab_overview:
    st.markdown("### 🌍 Benchmark Overview")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        footprint_input = st.number_input(
            "Your Annual Footprint (kg CO₂)",
            min_value=0.0,
            value=5000.0,
            step=100.0,
            help="Enter your total annual carbon footprint to compare.",
        )
    with col_r2:
        country_code = st.selectbox(
            "Compare Against",
            [c["code"] for c in list_available_countries()],
            index=0,
            format_func=lambda x: COUNTRY_BENCHMARKS[x]["name"],
        )

    run_btn = st.button("📊 Run Benchmark Analysis", use_container_width=True, type="primary")

    if run_btn:
        with st.spinner("Running benchmark analysis..."):
            # Build contributors from the footprint proportionally if not in session
            if "benchmark_data" not in st.session_state:
                fp, score, contributors = _get_or_calc_footprint()
                # Override footprint if user entered a specific value
                if footprint_input != 5000.0:
                    fp = footprint_input
                    score = calculate_eco_score(fp)
                    # Distribute contributors proportionally
                    total_raw = sum(contributors.values()) or 1.0
                    contributors = {k: round(v / total_raw * fp, 2) for k, v in contributors.items()}
            else:
                fp, score, contributors = _get_or_calc_footprint()

            report = build_full_benchmark_report(
                user_id=user_id,
                footprint_kg=fp,
                eco_score=score,
                contributors=contributors,
                country_code=country_code,
            )
            st.session_state.benchmark_report = report
            st.session_state.benchmark_data = {
                "footprint": fp,
                "eco_score": score,
                "contributors": contributors,
            }
            st.success("✅ Benchmark analysis complete!")

    # ── Display Report ───────────────────────────────────────────────────
    report = st.session_state.get("benchmark_report")
    if report:
        # ── Score banner ────────────────────────────────────────────────
        st.markdown("---")
        st.markdown(
            f"""
            <div style="background:#1e293b;padding:20px;border-radius:14px;
                        border-left:6px solid #38bdf8;margin-bottom:20px;">
                <h3 style="margin:0;color:#38bdf8;">
                    Your Footprint: {report.footprint_kg:,.0f} kg CO₂/year
                    &nbsp;|&nbsp; Eco Score: {report.eco_score}/100
                </h3>
                <p style="margin:6px 0 0;color:#cbd5e1;">
                    Global Percentile: Top {report.global_percentile}% &nbsp;|&nbsp;
                    {report.lifestyle_match.archetype_name if report.lifestyle_match else 'N/A'}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Key Metrics ─────────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌍 Global Percentile", f"Top {report.global_percentile}%")
        paris = COUNTRY_BENCHMARKS["Paris_Agreement_Target"]
        c2.metric(
            "🌡️ vs Paris Target",
            f"{report.footprint_kg - paris['per_capita_kg']:+,.0f} kg",
            delta=f"Target: {paris['per_capita_kg']:,} kg",
            delta_color="inverse",
        )
        c3.metric(
            f"🏳️ vs {country_code}",
            f"{report.footprint_kg - COUNTRY_BENCHMARKS.get(country_code, COUNTRY_BENCHMARKS['Global'])['per_capita_kg']:+,.0f} kg",
            delta=f"Avg: {COUNTRY_BENCHMARKS.get(country_code, COUNTRY_BENCHMARKS['Global'])['per_capita_kg']:,} kg",
            delta_color="inverse",
        )
        c4.metric("💡 Actions", f"{len(report.improvement_actions)}")

        # ── Insights ────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 💡 Key Insights")
        for insight in report.insights:
            st.markdown(f"- {insight}")

        # ── Radar chart ─────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 Category Breakdown vs Benchmark")

        ref_result = compare_against_country(
            report.footprint_kg, report.contributors, country_code,
        )
        ref_breakdown = COUNTRY_BENCHMARKS.get(country_code, COUNTRY_BENCHMARKS["Global"]).get(
            "category_breakdown", {}
        )

        cats = list(report.contributors.keys())
        user_vals = [report.contributors[c] for c in cats]
        ref_vals = [ref_breakdown.get(c, 0) for c in cats]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=user_vals + [user_vals[0]],
            theta=cats + [cats[0]],
            fill="toself",
            name="Your Footprint",
            line=dict(color="#38bdf8"),
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=ref_vals + [ref_vals[0]],
            theta=cats + [cats[0]],
            fill="toself",
            name=f"{COUNTRY_BENCHMARKS.get(country_code, COUNTRY_BENCHMARKS['Global'])['name']} Avg",
            line=dict(color="#64748b"),
            opacity=0.5,
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            title="Footprint Radar Comparison",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_radar, use_container_width=True)


# ── Tab 2: Country Comparison ────────────────────────────────────────────────
with tab_countries:
    st.markdown("### 🏳️ Country-Level Comparison")

    fp, score, contributors = _get_or_calc_footprint()
    country_results = compare_against_all_countries(fp, contributors)

    # Build dataframe
    rows = []
    for r in country_results:
        rows.append({
            "Country": r.reference_name,
            "Avg (kg CO₂)": r.reference_kg,
            "Your Footprint": r.user_kg,
            "Difference": r.delta_kg,
            "Δ (%)": r.delta_pct,
            "You Emit Less": "✅" if r.is_below else "❌",
        })

    df_countries = pd.DataFrame(rows)
    st.dataframe(
        df_countries.style.background_gradient(
            subset=["Difference"],
            cmap="RdYlGn_r",
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("### 📊 Bar Chart Comparison")
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        name="Your Footprint",
        x=df_countries["Country"],
        y=[fp] * len(df_countries),
        marker_color="#38bdf8",
    ))
    fig_bar.add_trace(go.Bar(
        name="Country Average",
        x=df_countries["Country"],
        y=df_countries["Avg (kg CO₂)"],
        marker_color="#64748b",
    ))
    fig_bar.update_layout(
        barmode="group",
        title="Your Footprint vs Country Averages",
        yaxis_title="kg CO₂/year",
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_bar, use_container_width=True)


# ── Tab 3: Lifestyle Match ──────────────────────────────────────────────────
with tab_lifestyle:
    st.markdown("### 👤 Lifestyle Archetype Matching")

    fp, score, contributors = _get_or_calc_footprint()
    match = find_closest_lifestyle(fp, contributors)

    st.markdown(
        f"""
        <div style="background:#1e293b;padding:20px;border-radius:14px;
                    border-left:6px solid #22c55e;margin-bottom:20px;">
            <h3 style="margin:0;color:#22c55e;">
                {match.archetype_name}
            </h3>
            <p style="margin:6px 0 0;color:#cbd5e1;">
                {match.description}
            </p>
            <p style="margin:6px 0 0;color:#94a3b8;">
                Your Similarity: {match.similarity_score:.0f}% &nbsp;|&nbsp;
                Their Footprint: {match.archetype_kg:,.0f} kg &nbsp;|&nbsp;
                Yours: {match.user_kg:,.0f} kg
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── All archetypes ──────────────────────────────────────────────────
    st.markdown("### 📋 All Lifestyle Archetypes")
    archetypes = list_lifestyle_archetypes()
    rows = []
    for a in archetypes:
        diff = fp - a["footprint_kg"]
        rows.append({
            "Archetype": a["name"],
            "Footprint (kg)": a["footprint_kg"],
            "Difference": diff,
            "Closest?": "⭐" if a["key"] == match.archetype_key else "",
        })

    df_arch = pd.DataFrame(rows).sort_values("Footprint (kg)")
    st.dataframe(df_arch, use_container_width=True, hide_index=True)

    # ── Category comparison chart ───────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Category Comparison with Match")
    matched_arch = LIFESTYLE_ARCHETYPES.get(match.archetype_key, {})
    matched_cats = matched_arch.get("category_breakdown", {})

    cats = list(contributors.keys())
    fig_cat = go.Figure()
    fig_cat.add_trace(go.Bar(
        name="You",
        x=cats,
        y=[contributors[c] for c in cats],
        marker_color="#38bdf8",
    ))
    fig_cat.add_trace(go.Bar(
        name=match.archetype_name,
        x=cats,
        y=[matched_cats.get(c, 0) for c in cats],
        marker_color="#22c55e",
    ))
    fig_cat.update_layout(
        barmode="group",
        title=f"Category Breakdown: You vs {match.archetype_name}",
        yaxis_title="kg CO₂/year",
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_cat, use_container_width=True)


# ── Tab 4: Trend Analysis ───────────────────────────────────────────────────
with tab_trend:
    st.markdown("### 📈 Historical Trend Analysis")

    history = get_user_assessment_history(user_id, limit=24)

    if not history:
        st.info(
            "No assessment history found. Complete assessments in the "
            "**Carbon Footprint** page to track your trend over time."
        )
    else:
        trend = analyse_trend(history)

        # ── Trend Metrics ───────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📅 Assessments", str(trend.months_of_data))
        direction_emoji = {"improving": "📈", "worsening": "📉", "stable": "➡️"}.get(
            trend.direction, "❓"
        )
        c2.metric(
            "Direction",
            f"{direction_emoji} {trend.direction.title()}",
            delta=f"{trend.total_change_kg:+,.0f} kg ({trend.total_change_pct:+.1f}%)",
            delta_color="inverse" if trend.direction == "improving" else "normal",
        )
        c3.metric("🏆 Best", f"{trend.best_kg:,.0f} kg")
        c4.metric("📊 Average", f"{trend.avg_footprint_kg:,.0f} kg")

        if trend.streak_improving > 0:
            st.success(f"🔥 Improving streak: {trend.streak_improving} consecutive assessments!")
        elif trend.streak_worsening > 0:
            st.warning(f"⚠️ Worsening streak: {trend.streak_worsening} consecutive assessments.")

        # ── Trend Chart ─────────────────────────────────────────────────
        st.markdown("---")
        dates = [e.date for e in trend.entries]
        footprints = [e.footprint_kg for e in trend.entries]

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=dates,
            y=footprints,
            mode="lines+markers",
            name="Footprint",
            line=dict(color="#38bdf8", width=3),
            marker=dict(size=8),
        ))
        # Reference lines
        paris_kg = COUNTRY_BENCHMARKS["Paris_Agreement_Target"]["per_capita_kg"]
        global_kg = COUNTRY_BENCHMARKS["Global"]["per_capita_kg"]
        fig_trend.add_hline(
            y=paris_kg,
            line_dash="dash",
            line_color="#22c55e",
            annotation_text=f"Paris Target ({paris_kg:,} kg)",
        )
        fig_trend.add_hline(
            y=global_kg,
            line_dash="dot",
            line_color="#ef4444",
            annotation_text=f"Global Average ({global_kg:,} kg)",
        )
        # Trend line
        if len(footprints) >= 2:
            x_idx = list(range(len(footprints)))
            mean_x = sum(x_idx) / len(x_idx)
            mean_y = sum(footprints) / len(footprints)
            slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_idx, footprints))
            slope /= sum((x - mean_x) ** 2 for x in x_idx) or 1
            intercept = mean_y - slope * mean_x
            trend_line = [slope * x + intercept for x in x_idx]
            fig_trend.add_trace(go.Scatter(
                x=dates,
                y=trend_line,
                mode="lines",
                name="Trend",
                line=dict(color="#facc15", width=2, dash="dot"),
            ))

        fig_trend.update_layout(
            title="Footprint Over Time",
            xaxis_title="Date",
            yaxis_title="kg CO₂/year",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_trend, use_container_width=True)


# ── Tab 5: Leaderboard ──────────────────────────────────────────────────────
with tab_leaderboard:
    st.markdown("### 🏆 Community Leaderboard")

    board = get_leaderboard(limit=20, user_id=user_id, include_surrounding=True, surrounding_range=3)

    if not board:
        st.info("No leaderboard data available. Complete an assessment to join the leaderboard!")
    else:
        rows = []
        for entry in board:
            is_self = entry.user_id == user_id
            rows.append({
                "Rank": entry.rank,
                "User": f"{'👉 ' if is_self else ''}{entry.username}",
                "Eco Score": f"{entry.eco_score}/100",
                "Footprint (kg)": f"{entry.footprint_kg:,.0f}",
                "Badge": entry.badge,
                "You": "⭐" if is_self else "",
            })

        df_board = pd.DataFrame(rows)
        st.dataframe(df_board, use_container_width=True, hide_index=True)

        # ── User's own rank ─────────────────────────────────────────────
        user_rank = get_user_rank(user_id)
        if user_rank["rank"] > 0:
            st.markdown("---")
            st.markdown("### 📊 Your Position")
            c1, c2, c3 = st.columns(3)
            c1.metric("🏅 Rank", f"#{user_rank['rank']}")
            c2.metric("📊 Percentile", f"Top {user_rank['percentile']}%")
            c3.metric("Badge", user_rank.get("badge", "🍃"))


# ── Tab 6: Improvement Plan ─────────────────────────────────────────────────
with tab_plan:
    st.markdown("### 📋 Prioritised Improvement Plan")

    report = st.session_state.get("benchmark_report")
    if report and report.improvement_actions:
        for i, action in enumerate(report.improvement_actions, 1):
            diff_badge = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(
                action["difficulty"], "⚪"
            )
            impact_badge = {"high": "🔥", "medium": "💪", "low": "🌱"}.get(
                action["impact"], ""
            )
            st.markdown(
                f"""
                <div style="border:1px solid #334155;border-radius:10px;padding:14px;
                            margin-bottom:10px;background:rgba(30,41,59,0.5);">
                    <h4 style="margin:0 0 6px;color:#38bdf8;">
                        #{i} {diff_badge} {action['action']}
                        <span style="font-size:0.85em;color:#4ade80;">
                            (Save ~{action['potential_savings_kg']:,.0f} kg CO₂/year)
                        </span>
                        {impact_badge}
                    </h4>
                    <small style="color:#94a3b8;">
                        Category: {action['category']} &nbsp;|&nbsp;
                        Difficulty: {action['difficulty'].title()} &nbsp;|&nbsp;
                        Impact: {action['impact'].title()}
                    </small>
                </div>
                """,
                unsafe_allow_html=True,
            )

        total_savings = sum(a["potential_savings_kg"] for a in report.improvement_actions)
        st.markdown("---")
        st.metric(
            "🎯 Total Potential Savings",
            f"{total_savings:,.0f} kg CO₂/year",
            delta=f"Reduce by {total_savings / report.footprint_kg * 100:.0f}%",
        )
    elif report:
        st.success(
            "🌟 Great news! Your footprint is already well-optimised. "
            "No major improvement actions needed."
        )
    else:
        st.info(
            "Run a benchmark analysis in the **Overview** tab to generate "
            "your personalised improvement plan."
        )
