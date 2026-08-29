"""Footprint Comparison & Benchmarking — rich analytics page for EcoBuddy AI.

Lets users compare their carbon footprint against global/national averages,
IPCC targets, lifestyle archetypes, and community peers.  Features include
interactive Plotly charts, category deep-dives, projection timelines,
and a green readiness scorecard.
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd

from styles.theme import apply_theme
from footprint_comparison import (
    COUNTRY_AVERAGES,
    IPCC_TARGETS,
    LIFESTYLE_ARCHETYPES,
    CATEGORY_META,
    READINESS_TIERS,
    compare_categories,
    compute_percentile,
    match_archetypes,
    compute_reduction_targets,
    compute_readiness_score,
    estimate_peer_group_average,
    generate_category_deep_dive,
    compute_projection_timeline,
    compute_equivalents,
    build_full_comparison_report,
    get_country_list,
    format_kg_to_tonnes,
    rating_color,
    get_benchmark_country,
)

# ── Auth ─────────────────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='section-header'>📊 Footprint Comparison & Benchmarking</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Discover how your carbon footprint compares against global averages, "
    "national benchmarks, IPCC targets, and lifestyle archetypes. "
    "Track your reduction pathway and receive a green readiness assessment."
)
st.markdown("---")

# ── Helper: get or compute footprint ─────────────────────────────────────────
def _get_or_calc_footprint() -> tuple[float, int, dict[str, float]]:
    """Return (footprint_kg, eco_score, contributors) from session or recalc."""
    transport = st.session_state.get("transport", "Car")
    distance = st.session_state.get("distance", 10.0)
    electricity = st.session_state.get("electricity", 200.0)
    diet = st.session_state.get("diet", "Vegetarian")
    flights = st.session_state.get("flights", 0)

    try:
        from src.carbon.emissions import calculate_footprint, calculate_eco_score
        footprint, contributors = calculate_footprint(
            transport, distance, electricity, diet, flights, "Global"
        )
        eco_score = calculate_eco_score(footprint, contributors)
    except Exception:
        # Fallback calculation
        contrib = {
            "transport": 0.21 * distance * 365,
            "electricity": electricity * 0.82 * 12,
            "diet": {"Vegetarian": 1700, "Non-Vegetarian": 2700, "Vegan": 1200, "Omnivore": 2200, "Heavy Meat": 3200}.get(diet, 1700),
            "flights": flights * 250.0,
        }
        footprint = sum(contrib.values())
        contributors = contrib
        eco_score = min(100, max(0, int(50)))

    return footprint, eco_score, contributors

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_overview, tab_countries, tab_archetypes, tab_deep_dive, tab_projection, tab_readiness = st.tabs([
    "🌍 Overview",
    "🏳️ Country Comparison",
    "👤 Archetype Match",
    "🔬 Category Deep-Dive",
    "📈 Projection Timeline",
    "🟢 Readiness Score",
])

footprint_kg, eco_score, contributors = _get_or_calc_footprint()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1: Overview
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_overview:
    st.subheader("🌍 Your Footprint at a Glance")

    report = build_full_comparison_report(footprint_kg, eco_score, contributors, user_id)

    # ── Key metrics row ──────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Your Footprint", f"{footprint_kg/1000:.2f} t CO₂")
    with m2:
        st.metric("Eco Score", f"{eco_score}/100")
    with m3:
        st.metric("Global Percentile", f"Top {report.country_percentile.percentile:.0f}%")
    with m4:
        st.metric("Best Archetype", f"{report.archetype_matches[0].avatar} {report.archetype_matches[0].archetype_name}")
    with m5:
        st.metric("Readiness", f"{report.readiness.score}/100")

    st.markdown("---")

    # ── Category bar chart ───────────────────────────────────────────────────
    st.subheader("📊 Category Breakdown vs EU Average")
    eu_bench = {k: v * 1000 for k, v in COUNTRY_AVERAGES["EU"].items() if k != "total_tonnes"}

    cat_labels = [CATEGORY_META[c]["label"] for c in CATEGORY_META]
    user_vals = [contributors.get(c, 0) for c in CATEGORY_META]
    bench_vals = [eu_bench.get(c, 0) for c in CATEGORY_META]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        name="Your Emissions",
        x=cat_labels, y=[round(v, 1) for v in user_vals],
        marker_color="#22c55e",
        text=[f"{v:.0f} kg" for v in user_vals],
        textposition="auto",
    ))
    fig_bar.add_trace(go.Bar(
        name="EU Average",
        x=cat_labels, y=[round(v, 1) for v in bench_vals],
        marker_color="#94a3b8",
        text=[f"{v:.0f} kg" for v in bench_vals],
        textposition="auto",
    ))
    fig_bar.update_layout(
        barmode="group",
        template="plotly_white",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=30, l=30, r=30),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Radar chart ──────────────────────────────────────────────────────────
    st.subheader("🕸️ Your Profile Radar")
    radar_cats = list(CATEGORY_META.keys())
    radar_user = [min(100, contributors.get(c, 0) / max(eu_bench.get(c, 1), 1) * 100) for c in radar_cats]
    radar_bench = [100.0] * len(radar_cats)  # EU average as 100% baseline

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=radar_user + [radar_user[0]],
        theta=[CATEGORY_META[c]["label"] for c in radar_cats] + [CATEGORY_META[radar_cats[0]]["label"]],
        fill="toself",
        name="You",
        fillcolor="rgba(34, 197, 94, 0.2)",
        line_color="#22c55e",
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=radar_bench + [radar_bench[0]],
        theta=[CATEGORY_META[c]["label"] for c in radar_cats] + [CATEGORY_META[radar_cats[0]]["label"]],
        fill="toself",
        name="EU Average",
        fillcolor="rgba(148, 163, 184, 0.1)",
        line_color="#94a3b8",
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(200, max(radar_user) * 1.2)]),
            bgcolor="rgba(255,255,255,0)",
        ),
        showlegend=True,
        template="plotly_white",
        height=450,
        margin=dict(t=60, b=30),
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # ── Equivalencies ────────────────────────────────────────────────────────
    st.subheader("🌳 What Does Your Footprint Mean?")
    equivs = compute_equivalents(footprint_kg)
    eq_cols = st.columns(5)
    eq_items = [
        ("🌳", "Trees Needed", f"{equivs['trees_needed']:.0f}", "to absorb your annual CO₂"),
        ("🚗", "Driving Distance", f"{equivs['driving_km']:.0f} km", "equivalent driving"),
        ("📱", "Phone Charges", f"{equivs['smartphone_charges']:.0f}", "smartphone charges"),
        ("🍽️", "Meals", f"{equivs['meals_equivalent']:.0f}", "average meals"),
        ("💧", "Water Saved", f"{equivs['liters_water']:.0f} L", "water footprint equivalent"),
    ]
    for i, (icon, label, value, sub) in enumerate(eq_items):
        with eq_cols[i]:
            st.markdown(f"<div style='text-align:center; padding:16px; background:rgba(34,197,94,0.05); border-radius:12px; border:1px solid rgba(34,197,94,0.15);'>"
                        f"<span style='font-size:32px;'>{icon}</span><br>"
                        f"<span style='font-size:20px; font-weight:700;'>{value}</span><br>"
                        f"<span style='font-size:12px; color:#6b7280;'>{label}<br>{sub}</span></div>",
                        unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2: Country Comparison
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_countries:
    st.subheader("🏳️ Compare Against Countries")

    selected_country = st.selectbox(
        "Select a country to compare against:",
        get_country_list(),
        index=get_country_list().index("Global"),
        key="country_compare",
    )

    country_data = get_benchmark_country(selected_country)
    country_bench = {k: v * 1000 for k, v in country_data.items() if k != "total_tonnes"}

    # ── Country comparison table ──────────────────────────────────────────────
    st.markdown(f"#### Your Footprint vs {selected_country} Average")
    comp_data = []
    for cat_key, meta in CATEGORY_META.items():
        user_val = contributors.get(cat_key, 0)
        bench_val = country_bench.get(cat_key, 0)
        diff = user_val - bench_val
        comp_data.append({
            "Category": meta["label"],
            "Your Emissions (kg)": round(user_val, 1),
            f"{selected_country} Average (kg)": round(bench_val, 1),
            "Difference (kg)": round(diff, 1),
            "Performance": "✅ Below" if diff <= 0 else "❌ Above",
        })

    st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

    # ── Horizontal bar chart ─────────────────────────────────────────────────
    fig_horiz = go.Figure()
    for cat_key, meta in CATEGORY_META.items():
        user_val = contributors.get(cat_key, 0)
        bench_val = country_bench.get(cat_key, 0)

        fig_horiz.add_trace(go.Bar(
            y=[meta["label"]],
            x=[user_val],
            name="You",
            orientation="h",
            marker_color=meta["color"],
            showlegend=(cat_key == "transport"),
            text=[f"{user_val:.0f}"],
            textposition="inside",
        ))
        fig_horiz.add_trace(go.Bar(
            y=[meta["label"]],
            x=[bench_val],
            name=f"{selected_country} Avg",
            orientation="h",
            marker_color="#d1d5db",
            showlegend=(cat_key == "transport"),
            text=[f"{bench_val:.0f}"],
            textposition="inside",
        ))

    fig_horiz.update_layout(
        barmode="group",
        template="plotly_white",
        height=350,
        xaxis_title="kg CO₂ / year",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=40, b=30),
    )
    st.plotly_chart(fig_horiz, use_container_width=True)

    # ── Total comparison ──────────────────────────────────────────────────────
    total_bench = country_data["total_tonnes"] * 1000
    diff_total = footprint_kg - total_bench
    if diff_total <= 0:
        st.success(f"🎉 You emit **{abs(diff_total):.0f} kg less** CO₂ than the average person in {selected_country}!")
    else:
        st.warning(f"⚠️ You emit **{diff_total:.0f} kg more** CO₂ than the average person in {selected_country}.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 3: Archetype Match
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_archetypes:
    st.subheader("👤 Your Lifestyle Archetype")

    archetypes = match_archetypes(contributors, footprint_kg)

    # Show top match prominently
    top = archetypes[0]
    st.markdown(
        f"<div style='text-align:center; padding:30px; background:linear-gradient(135deg, "
        f"rgba(34,197,94,0.08), rgba(34,197,94,0.02)); border-radius:16px; "
        f"border:2px solid rgba(34,197,94,0.2); margin-bottom:20px;'>"
        f"<span style='font-size:48px;'>{top.avatar}</span><br>"
        f"<span style='font-size:28px; font-weight:800;'>{top.archetype_name}</span><br>"
        f"<span style='font-size:16px; color:#6b7280;'>{top.description}</span><br>"
        f"<span style='font-size:14px; color:#22c55e;'>Match: {top.similarity_score*100:.1f}% | "
        f"Your footprint: {format_kg_to_tonnes(top.user_kg)} vs archetype: {format_kg_to_tonnes(top.typical_kg)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # All archetypes in cards
    st.markdown("#### All Lifestyle Archetypes")
    cols = st.columns(3)
    for i, arch in enumerate(archetypes):
        col = cols[i % 3]
        with col:
            is_top = (i == 0)
            border = "2px solid #22c55e" if is_top else "1px solid #e5e7eb"
            bg = "rgba(34,197,94,0.06)" if is_top else "rgba(255,255,255,0.8)"
            st.markdown(
                f"<div style='padding:18px; border-radius:12px; border:{border}; background:{bg}; margin-bottom:12px;'>"
                f"<span style='font-size:28px;'>{arch.avatar}</span> "
                f"<span style='font-weight:700;'>{arch.archetype_name}</span>"
                f"<br><span style='font-size:13px; color:#6b7280;'>{arch.description}</span>"
                f"<br><span style='font-size:12px; font-weight:600; color:{'#22c55e' if arch.similarity_score > 0.5 else '#6b7280'};'>"
                f"Similarity: {arch.similarity_score*100:.1f}% | Target: {format_kg_to_tonnes(arch.typical_kg)}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Archetype comparison chart ───────────────────────────────────────────
    st.markdown("#### Category Profile Comparison")
    fig_arch = go.Figure()
    cat_keys = list(CATEGORY_META.keys())
    user_pro = [contributors.get(c, 0) for c in cat_keys]

    fig_arch.add_trace(go.Bar(
        name="You", x=[CATEGORY_META[c]["label"] for c in cat_keys],
        y=user_pro, marker_color="#22c55e",
        text=[f"{v:.0f}" for v in user_pro], textposition="auto",
    ))
    fig_arch.add_trace(go.Bar(
        name=f"{top.archetype_name}", x=[CATEGORY_META[c]["label"] for c in cat_keys],
        y=[top.typical_kg / len(cat_keys)] * len(cat_keys),
        marker_color="#94a3b8",
    ))
    fig_arch.update_layout(
        barmode="group", template="plotly_white", height=350,
        yaxis_title="kg CO₂ / year",
        margin=dict(t=40, b=30),
    )
    st.plotly_chart(fig_arch, use_container_width=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 4: Category Deep-Dive
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_deep_dive:
    st.subheader("🔬 Category Deep-Dive Analysis")

    deep_dive = generate_category_deep_dive(contributors)

    for cat_label, dd in deep_dive.items():
        with st.expander(f"{cat_label} — {'✅' if dd['vs_eu_difference_kg'] <= 0 else '❌'} {dd['user_kg']:.0f} kg (EU avg: {dd['eu_average_kg']:.0f} kg)", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Your emissions:** {dd['user_kg']:.1f} kg CO₂/year")
                st.markdown(f"**EU average:** {dd['eu_average_kg']:.1f} kg CO₂/year")
                st.markdown(f"**Global average:** {dd['global_average_kg']:.1f} kg CO₂/year")
                st.markdown(f"**Difference vs EU:** {'+' if dd['vs_eu_difference_kg'] > 0 else ''}{dd['vs_eu_difference_kg']:.1f} kg")
                st.markdown(f"**Improvement potential:** {dd['improvement_potential_pct']:.0f}% ({dd['improvement_potential_kg']:.0f} kg)")
            with col_b:
                # Mini gauge chart
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=min(200, dd['user_kg'] / max(dd['eu_average_kg'], 1) * 100),
                    title={"text": f"% of EU Average", "font": {"size": 14}},
                    gauge=dict(
                        axis=dict(range=[0, 200]),
                        bar=dict(color=dd['color']),
                        steps=[
                            dict(range=[0, 100], color="rgba(34,197,94,0.1)"),
                            dict(range=[100, 200], color="rgba(239,68,68,0.1)"),
                        ],
                        threshold=dict(line=dict(color="red", width=2), thickness=0.75, value=100),
                    ),
                ))
                fig_gauge.update_layout(height=200, margin=dict(t=30, b=10, l=30, r=30))
                st.plotly_chart(fig_gauge, use_container_width=True)

            st.markdown("**💡 Improvement Tips:**")
            for tip in dd["tips"]:
                st.markdown(f"  - {tip}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 5: Projection Timeline
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_projection:
    st.subheader("📈 Reduction Projection Timeline")

    reduction_pct = st.slider(
        "Annual reduction rate (%)", min_value=1.0, max_value=20.0, value=5.0, step=0.5,
        help="How aggressively you reduce your footprint each year"
    )
    projection_years = st.slider(
        "Projection horizon (years)", min_value=3, max_value=30, value=10, step=1,
    )

    timeline = compute_projection_timeline(footprint_kg, reduction_pct, projection_years)

    # ── Projection chart ─────────────────────────────────────────────────────
    fig_proj = go.Figure()
    years_data = [t["year"] for t in timeline]
    kg_data = [t["projected_kg"] for t in timeline]

    fig_proj.add_trace(go.Scatter(
        x=years_data, y=kg_data, mode="lines+markers",
        name="Projected Footprint",
        line=dict(color="#22c55e", width=3),
        fill="tozeroy", fillcolor="rgba(34,197,94,0.1)",
    ))

    # Add IPCC target lines
    colors_target = {"2030": "#f59e0b", "2050_net_zero": "#ef4444", "15C_pathway": "#8b5cf6"}
    for target_name, target_data in IPCC_TARGETS.items():
        fig_proj.add_hline(
            y=target_data["target_kg"], line_dash="dash",
            line_color=colors_target.get(target_name, "#6b7280"),
            annotation_text=f"{target_data['description']}: {target_data['target_kg']:.0f} kg",
            annotation_position="right",
        )

    fig_proj.update_layout(
        template="plotly_white", height=450,
        xaxis_title="Years from Now",
        yaxis_title="Projected Annual CO₂ (kg)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=60, b=30),
    )
    st.plotly_chart(fig_proj, use_container_width=True)

    # ── Cumulative savings ───────────────────────────────────────────────────
    st.markdown("#### 💰 Cumulative CO₂ Savings Over Time")
    cum_cols = st.columns(4)
    milestones = [5, 10, 15, 20]
    for i, yr in enumerate(milestones):
        with cum_cols[i]:
            if yr <= projection_years:
                entry = next((t for t in timeline if t["year"] == yr), timeline[-1])
                st.metric(f"+{yr} Years", f"{entry['cumulative_saved_kg']/1000:.1f} t saved")
            else:
                st.metric(f"+{yr} Years", "—")

    # ── Target feasibility ───────────────────────────────────────────────────
    targets = compute_reduction_targets(footprint_kg, contributors)
    st.markdown("#### 🎯 IPCC Target Feasibility")
    for target in targets:
        icon = "🟢" if target.feasible else "🔴"
        status = "Achievable" if target.feasible else "Requires significant effort"
        st.markdown(
            f"{icon} **{target.description}**: Need to reduce **{target.gap_kg:.0f} kg** "
            f"({target.reduction_needed_pct:.0f}%) — *{status}*"
        )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 6: Readiness Score
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_readiness:
    st.subheader("🟢 Green Readiness Scorecard")

    readiness = compute_readiness_score(footprint_kg, contributors)

    # ── Score display ────────────────────────────────────────────────────────
    score_col, tier_col = st.columns([1, 2])
    with score_col:
        fig_score = go.Figure(go.Indicator(
            mode="gauge+number",
            value=readiness.score,
            title={"text": "Readiness Score", "font": {"size": 18}},
            gauge=dict(
                axis=dict(range=[0, 100]),
                bar=dict(color=readiness.tier_color),
                steps=[
                    dict(range=[0, 30], color="rgba(239,68,68,0.15)"),
                    dict(range=[30, 50], color="rgba(249,115,22,0.15)"),
                    dict(range=[50, 70], color="rgba(234,179,8,0.15)"),
                    dict(range=[70, 90], color="rgba(132,204,22,0.15)"),
                    dict(range=[90, 100], color="rgba(34,197,94,0.2)"),
                ],
            ),
        ))
        fig_score.update_layout(height=300, margin=dict(t=30, b=10))
        st.plotly_chart(fig_score, use_container_width=True)

    with tier_col:
        st.markdown(
            f"<div style='text-align:center; padding:30px; background:rgba(255,255,255,0.8); "
            f"border-radius:16px; border:2px solid {readiness.tier_color}; margin-top:40px;'>"
            f"<span style='font-size:36px;'>{readiness.tier_name}</span><br>"
            f"<span style='font-size:16px; color:#6b7280;'>{readiness.description}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Score breakdown ──────────────────────────────────────────────────────
    st.markdown("#### 📊 Score Breakdown")
    breakdown_data = []
    for key, score in readiness.breakdown.items():
        label = key.replace("_", " ").title()
        if key in CATEGORY_META:
            label = CATEGORY_META[key]["label"]
        max_val = 40.0 if key == "overall" else 10.0
        breakdown_data.append({
            "Component": label,
            "Score": score,
            "Max": max_val,
            "% of Max": round(score / max_val * 100, 1),
        })

    st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True, hide_index=True)

    # Breakdown bar chart
    fig_break = go.Figure()
    fig_break.add_trace(go.Bar(
        y=[b["Component"] for b in breakdown_data],
        x=[b["Score"] for b in breakdown_data],
        orientation="h",
        marker_color=[readiness.tier_color if b["% of Max"] >= 70 else "#f59e0b" if b["% of Max"] >= 40 else "#ef4444" for b in breakdown_data],
        text=[f"{b['Score']:.1f}/{b['Max']:.0f}" for b in breakdown_data],
        textposition="auto",
    ))
    fig_break.update_layout(
        template="plotly_white", height=300,
        xaxis_title="Score",
        margin=dict(t=20, b=30, l=120),
    )
    st.plotly_chart(fig_break, use_container_width=True)

    # ── Recommendations ──────────────────────────────────────────────────────
    st.markdown("#### 💡 Recommendations")
    for rec in readiness.recommendations:
        st.info(rec)

    # ── Tier legend ──────────────────────────────────────────────────────────
    st.markdown("#### 🏅 Tier Legend")
    tier_cols = st.columns(len(READINESS_TIERS))
    for i, (min_score, name, color, desc) in enumerate(READINESS_TIERS):
        with tier_cols[i]:
            is_current = readiness.score >= min_score and (i == 0 or readiness.score < READINESS_TIERS[i-1][0])
            border = f"2px solid {color}" if is_current else "1px solid #e5e7eb"
            opacity = "1" if is_current else "0.6"
            st.markdown(
                f"<div style='padding:10px; border-radius:8px; border:{border}; text-align:center; opacity:{opacity};'>"
                f"<span style='font-weight:700;'>{name}</span><br>"
                f"<span style='font-size:11px; color:#6b7280;'>≥{min_score} pts</span><br>"
                f"<span style='font-size:11px;'>{desc}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("📊 Footprint Comparison & Benchmarking Engine — Data sources: IPCC AR6, Our World in Data, national statistics.")
st.caption(f"Generated at: {report.generated_at}")
