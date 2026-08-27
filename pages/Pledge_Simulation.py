"""
Pledge Simulation Lab – Streamlit Page
========================================
Interactive what-if scenarios, carbon budget tracking, strategy
comparison, portfolio optimisation, seasonal projections, and
long-term impact modelling.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
from datetime import datetime

from pledge_simulation import (
    init_simulation_tables,
    run_what_if,
    simulate_carbon_budget,
    compare_strategies,
    optimise_portfolio,
    project_seasonal_impact,
    project_long_term,
    run_simulation,
    get_simulation_history,
    export_simulations_json,
    SCENARIO_PRESETS,
    SEASONAL_FACTORS,
    SimulationType,
)
from green_pledge_tracker import (
    init_pledge_tables,
    get_all_templates,
    get_user_pledge_stats,
    current_week_start,
    PLEDGE_CATEGORIES,
)

st.set_page_config(page_title="Pledge Simulation Lab", page_icon="🧪", layout="wide")

# Initialise tables
init_pledge_tables()
init_simulation_tables()

# ── Auth gate ────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("🔒 Please sign in to use the Pledge Simulation Lab.")
    st.stop()

# ── Page header ──────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:10px 0 4px;'>
    <h1 style='margin:0;font-size:2.4rem;'>🧪 Pledge Simulation Lab</h1>
    <p style='color:#6b7280;margin-top:4px;font-size:1.05rem;'>
        Run what-if scenarios, compare strategies, and model your long-term environmental impact.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────────────
tab_whatif, tab_compare, tab_budget, tab_portfolio, tab_seasonal, tab_longterm, tab_history = st.tabs([
    "🔮 What-If",
    "⚖️ Strategy Compare",
    "📊 Carbon Budget",
    "🎯 Portfolio Optimiser",
    "🌦️ Seasonal",
    "📈 Long-Term",
    "📚 History",
])

# =====================================================================
# TAB: What-If
# =====================================================================
with tab_whatif:
    st.subheader("🔮 What-If Scenario")

    templates = get_all_templates()
    template_options = {f"{t.title} ({t.category})": t.id for t in templates}

    col1, col2 = st.columns(2)
    with col1:
        add_selected = st.multiselect(
            "Add these pledges",
            list(template_options.keys()),
            key="whatif_add",
        )
    with col2:
        remove_selected = st.multiselect(
            "Remove these pledges",
            list(template_options.keys()),
            key="whatif_remove",
        )

    completion_change = st.slider(
        "Completion rate change (%)",
        min_value=-50,
        max_value=50,
        value=0,
        key="whatif_completion",
    )

    if st.button("▶️ Run What-If", use_container_width=True):
        add_ids = [template_options[s] for s in add_selected]
        remove_ids = [template_options[s] for s in remove_selected]

        result = run_simulation(
            user_id,
            SimulationType.WHAT_IF,
            {
                "add_pledges": add_ids,
                "remove_pledges": remove_ids,
                "completion_rate_change": completion_change / 100.0,
            },
        )
        st.session_state["whatif_result"] = result

    if "whatif_result" in st.session_state:
        result = st.session_state["whatif_result"]
        summary = result.summary

        st.divider()

        # Impact delta
        delta_color = "normal" if summary.get("annual_delta_kg", 0) >= 0 else "inverse"
        st.markdown(f"""
        <div style='border:2px solid {"#22c55e" if summary.get("annual_delta_kg", 0) >= 0 else "#ef4444"}40;
                    border-radius:16px;padding:24px;
                    background:linear-gradient(135deg,{"#f0fdf4" if summary.get("annual_delta_kg", 0) >= 0 else "#fef2f2"},#fff);'>
            <h3 style='margin:0 0 12px;'>📊 Scenario Impact</h3>
            <div style='display:flex;gap:32px;flex-wrap:wrap;'>
                <div>
                    <div style='font-size:0.8rem;color:#9ca3af;'>Current Weekly</div>
                    <div style='font-size:1.6rem;font-weight:800;'>{summary.get("current_weekly_co2_kg", 0):.1f} kg</div>
                </div>
                <div>
                    <div style='font-size:0.8rem;color:#9ca3af;'>Simulated Weekly</div>
                    <div style='font-size:1.6rem;font-weight:800;'>{summary.get("simulated_weekly_co2_kg", 0):.1f} kg</div>
                </div>
                <div>
                    <div style='font-size:0.8rem;color:#9ca3af;'>Weekly Δ</div>
                    <div style='font-size:1.6rem;font-weight:800;color:{"#22c55e" if summary.get("weekly_delta_kg", 0) >= 0 else "#ef4444"};'>
                        {summary.get("weekly_delta_kg", 0):+.1f} kg
                    </div>
                </div>
                <div>
                    <div style='font-size:0.8rem;color:#9ca3af;'>Annual Δ</div>
                    <div style='font-size:1.6rem;font-weight:800;color:{"#22c55e" if summary.get("annual_delta_kg", 0) >= 0 else "#ef4444"};'>
                        {summary.get("annual_delta_kg", 0):+.1f} kg
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Projection chart
        if result.projections:
            df = pd.DataFrame(result.projections)
            fig = px.line(df, x="week", y="co2_kg", labels={"week": "Week", "co2_kg": "Cumulative CO₂ (kg)"})
            fig.update_traces(line_color="#4ade80")
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        # Added/removed
        if summary.get("pledges_added"):
            st.markdown("**➕ Pledges Added:**")
            for p in summary["pledges_added"]:
                st.markdown(f"- {p['title']} ({p['category']}) — +{p['weekly_co2_kg']:.1f} kg/week")

        if summary.get("pledges_removed"):
            st.markdown("**➖ Pledges Removed:**")
            for p in summary["pledges_removed"]:
                st.markdown(f"- {p['title']} — -{p['weekly_co2_kg']:.1f} kg/week")

# =====================================================================
# TAB: Strategy Compare
# =====================================================================
with tab_compare:
    st.subheader("⚖️ Strategy Comparison")

    if st.button("🔄 Compare All Strategies", use_container_width=True):
        result = run_simulation(user_id, SimulationType.STRATEGY_COMPARE)
        st.session_state["compare_result"] = result

    if "compare_result" in st.session_state:
        result = st.session_state["compare_result"]
        strategies = result.projections

        # Comparison chart
        df = pd.DataFrame(strategies)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Annual CO₂ (kg)", x=df["title"], y=df["annual_co2_kg"],
                             marker_color="#4ade80"))
        fig.add_trace(go.Bar(name="Annual XP", x=df["title"], y=df["annual_xp"],
                             marker_color="#f59e0b"))
        fig.update_layout(barmode="group", height=350, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # Strategy cards
        for strat in strategies:
            st.markdown(f"""
            <div style='border:1px solid #e5e7eb;border-radius:14px;padding:16px;
                        background:#fff;margin-bottom:10px;'>
                <h4 style='margin:0;'>{strat['title']}</h4>
                <p style='color:#6b7280;margin:4px 0 8px;font-size:0.85rem;'>{strat['description']}</p>
                <div style='display:flex;gap:16px;font-size:0.82rem;'>
                    <span>🌍 {strat['annual_co2_kg']:.1f} kg CO₂/yr</span>
                    <span>⭐ {strat['annual_xp']} XP/yr</span>
                    <span>📊 {strat['efficiency']:.2f} efficiency</span>
                    <span>✅ {strat['completion_rate']:.0%} completion</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Recommendation
        if result.recommendations:
            st.info(f"💡 {result.recommendations[0]}")

# =====================================================================
# TAB: Carbon Budget
# =====================================================================
with tab_budget:
    st.subheader("📊 Carbon Budget Simulator")

    target = st.number_input(
        "Annual CO₂ Budget Target (kg)",
        min_value=100.0,
        max_value=10000.0,
        value=2000.0,
        step=100.0,
        key="budget_target",
    )

    if st.button("📊 Simulate Budget", use_container_width=True):
        result = run_simulation(user_id, SimulationType.CARBON_BUDGET, {"annual_target_kg": target})
        st.session_state["budget_result"] = result

    if "budget_result" in st.session_state:
        result = st.session_state["budget_result"]
        budget = result.summary

        # Progress gauge
        usage = budget.get("current_annual_usage_kg", 0)
        target_val = budget.get("annual_target_kg", 2000)
        pct = min(usage / max(target_val, 1) * 100, 100)
        remaining = budget.get("remaining_budget_kg", 0)

        gauge_color = "#22c55e" if budget.get("on_track", True) else "#ef4444"

        st.markdown(f"""
        <div style='border:2px solid {gauge_color}40;border-radius:16px;padding:24px;
                    background:linear-gradient(135deg,{gauge_color}08,#fff);'>
            <h3 style='margin:0 0 12px;'>{"✅ On Track" if budget.get("on_track") else "⚠️ Behind Target"}</h3>
            <div style='display:flex;gap:32px;flex-wrap:wrap;'>
                <div>
                    <div style='font-size:0.8rem;color:#9ca3af;'>Used</div>
                    <div style='font-size:1.6rem;font-weight:800;'>{usage:.1f} kg</div>
                </div>
                <div>
                    <div style='font-size:0.8rem;color:#9ca3af;'>Target</div>
                    <div style='font-size:1.6rem;font-weight:800;'>{target_val:.0f} kg</div>
                </div>
                <div>
                    <div style='font-size:0.8rem;color:#9ca3af;'>Remaining</div>
                    <div style='font-size:1.6rem;font-weight:800;color:{gauge_color};'>{remaining:.1f} kg</div>
                </div>
                <div>
                    <div style='font-size:0.8rem;color:#9ca3af;'>Weeks Left</div>
                    <div style='font-size:1.6rem;font-weight:800;'>{budget.get("weeks_left", 0)}</div>
                </div>
                <div>
                    <div style='font-size:0.8rem;color:#9ca3af;'>Weekly Allowance</div>
                    <div style='font-size:1.6rem;font-weight:800;'>{budget.get("weekly_allowance_kg", 0):.1f} kg</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Progress bar
        st.progress(pct / 100, text=f"Budget used: {pct:.1f}%")

        # Recommendations
        for rec in budget.get("recommendations", []):
            st.markdown(f"- {rec}")

# =====================================================================
# TAB: Portfolio Optimiser
# =====================================================================
with tab_portfolio:
    st.subheader("🎯 Pledge Portfolio Optimiser")

    col1, col2 = st.columns(2)
    with col1:
        effort_budget = st.slider("Effort Budget", 1, 10, 3, key="portfolio_effort")
    with col2:
        difficulty = st.selectbox("Max Difficulty", ["Easy", "Medium", "Hard"], key="portfolio_diff")

    if st.button("🎯 Optimise Portfolio", use_container_width=True):
        diff_map = {"Easy": "easy", "Medium": "medium", "Hard": "hard"}
        result = run_simulation(
            user_id,
            SimulationType.PORTFOLIO_OPTIMISE,
            {"effort_budget": effort_budget, "difficulty_budget": diff_map[difficulty]},
        )
        st.session_state["portfolio_result"] = result

    if "portfolio_result" in st.session_state:
        result = st.session_state["portfolio_result"]
        portfolio = result.summary
        pledges = result.projections

        # Summary
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌍 CO₂ / week", f"{portfolio.get('total_co2_kg', 0):.1f} kg")
        c2.metric("⭐ XP / week", f"{portfolio.get('total_xp', 0)}")
        c3.metric("📊 Efficiency", f"{portfolio.get('efficiency', 0):.2f}")
        c4.metric("📂 Categories", len(portfolio.get("categories", [])))

        # Pledge list
        st.markdown("#### 📋 Selected Pledges")
        for p in pledges:
            diff_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(p["difficulty"], "⚪")
            st.markdown(f"""
            <div style='border:1px solid #e5e7eb;border-radius:12px;padding:14px;
                        background:#fff;margin-bottom:8px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <div>
                        <h4 style='margin:0;'>{p['title']}</h4>
                        <p style='color:#6b7280;margin:2px 0 0;font-size:0.82rem;'>
                            {PLEDGE_CATEGORIES.get(p['category'], {}).get('label', p['category'])}
                            · {diff_emoji} {p['difficulty'].title()}
                        </p>
                    </div>
                    <div style='text-align:right;'>
                        <div style='font-size:1rem;font-weight:700;color:#22c55e;'>{p['weekly_co2_kg']:.1f} kg</div>
                        <div style='font-size:0.7rem;color:#9ca3af;'>CO₂/week · {p['xp_reward']} XP</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    elif "portfolio_result" not in st.session_state:
        pass  # button not clicked yet
    else:
        result = st.session_state["portfolio_result"]
        portfolio = result.summary
        pledges = result.projections

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌍 CO₂ / week", f"{portfolio.get('total_co2_kg', 0):.1f} kg")
        c2.metric("⭐ XP / week", f"{portfolio.get('total_xp', 0)}")
        c3.metric("📊 Efficiency", f"{portfolio.get('efficiency', 0):.2f}")
        c4.metric("📂 Categories", len(portfolio.get("categories", [])))

        st.markdown("#### 📋 Selected Pledges")
        for p in pledges:
            diff_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(p["difficulty"], "⚪")
            st.markdown(f"- **{p['title']}** — {diff_emoji} {p['difficulty'].title()} · {p['weekly_co2_kg']:.1f} kg CO₂ · {p['xp_reward']} XP")

# =====================================================================
# TAB: Seasonal
# =====================================================================
with tab_seasonal:
    st.subheader("🌦️ Seasonal Impact Projection")

    if st.button("🌦️ Project Seasonal Impact", use_container_width=True):
        result = run_simulation(user_id, SimulationType.SEASONAL)
        st.session_state["seasonal_result"] = result

    if "seasonal_result" in st.session_state:
        result = st.session_state["seasonal_result"]
        projections = result.projections

        # Season comparison chart
        season_data = []
        for proj in projections:
            for cat in proj.get("category_projections", []):
                season_data.append({
                    "Season": proj["season"].title(),
                    "Category": cat.get("label", cat.get("category", "")),
                    "CO₂ (kg)": cat.get("seasonal_co2_kg", 0),
                })

        if season_data:
            df = pd.DataFrame(season_data)
            fig = px.bar(df, x="Season", y="CO₂ (kg)", color="Category",
                         barmode="group", height=400)
            fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        # Season cards
        season_emojis = {"spring": "🌸", "summer": "☀️", "autumn": "🍂", "winter": "❄️"}
        for proj in projections:
            emoji = season_emojis.get(proj.get("season", ""), "🌍")
            st.markdown(f"""
            <div style='border:1px solid #e5e7eb;border-radius:14px;padding:16px;
                        background:#fff;margin-bottom:10px;'>
                <h4 style='margin:0;'>{emoji} {proj.get("season", "").title()} {proj.get("year", "")}</h4>
                <p style='font-size:0.85rem;margin:4px 0 0;'>
                    Total projected: <strong>{proj.get("total_projected_co2_kg", 0):.1f} kg CO₂</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)

            for note in proj.get("notes", []):
                st.markdown(f"- {note}")

# =====================================================================
# TAB: Long-Term
# =====================================================================
with tab_longterm:
    st.subheader("📈 Long-Term Impact Projection")

    col1, col2 = st.columns(2)
    with col1:
        years = st.slider("Years to project", 1, 10, 3, key="lt_years")
    with col2:
        strategy = st.selectbox(
            "Strategy",
            ["Conservative", "Balanced", "Aggressive", "Minimal", "Diverse"],
            key="lt_strategy",
        )

    if st.button("📈 Project Long-Term", use_container_width=True):
        strat_map = {
            "Conservative": "conservative", "Balanced": "balanced",
            "Aggressive": "aggressive", "Minimal": "minimal", "Diverse": "diverse",
        }
        result = run_simulation(
            user_id,
            SimulationType.LONG_TERM,
            {"years": years, "strategy": strat_map[strategy]},
        )
        st.session_state["lt_result"] = result

    if "lt_result" in st.session_state:
        result = st.session_state["lt_result"]
        summary = result.summary

        # Cumulative impact
        st.markdown(f"""
        <div style='border:2px solid #4ade8040;border-radius:16px;padding:24px;
                    background:linear-gradient(135deg,#f0fdf4,#fff);text-align:center;'>
            <h2 style='margin:0;color:#16a34a;'>{years}-Year Projection</h2>
            <div style='display:flex;justify-content:center;gap:40px;margin-top:16px;'>
                <div>
                    <div style='font-size:2.2rem;font-weight:800;color:#16a34a;'>{summary.get("cumulative_co2_kg", 0):.0f}</div>
                    <div style='font-size:0.85rem;color:#6b7280;'>kg CO₂ Saved</div>
                </div>
                <div>
                    <div style='font-size:2.2rem;font-weight:800;color:#f59e0b;'>{summary.get("cumulative_xp", 0):,}</div>
                    <div style='font-size:0.85rem;color:#6b7280;'>Total XP</div>
                </div>
                <div>
                    <div style='font-size:2.2rem;font-weight:800;color:#22c55e;'>{summary.get("trees", 0):.0f}</div>
                    <div style='font-size:0.85rem;color:#6b7280;'>Trees Equivalent</div>
                </div>
                <div>
                    <div style='font-size:2.2rem;font-weight:800;color:#3b82f6;'>{summary.get("car_km", 0):.0f}</div>
                    <div style='font-size:0.85rem;color:#6b7280;'>Driving km Saved</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Annual chart
        if result.projections:
            df = pd.DataFrame(result.projections)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Annual CO₂ (kg)", x=df["year"], y=df["annual_co2_kg"],
                                 marker_color="#4ade80"))
            fig.add_trace(go.Scatter(name="Cumulative CO₂ (kg)", x=df["year"], y=df["cumulative_co2_kg"],
                                     mode="lines+markers", line=dict(color="#f59e0b", width=2)))
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        # Recommendations
        for rec in result.recommendations:
            st.markdown(f"- {rec}")

# =====================================================================
# TAB: History
# =====================================================================
with tab_history:
    st.subheader("📚 Simulation History")

    history = get_simulation_history(user_id, limit=20)

    if not history:
        st.info("No simulations run yet. Try any of the simulation tabs above!")
    else:
        for sim in history:
            st.markdown(f"""
            <div style='border:1px solid #e5e7eb;border-radius:12px;padding:14px;
                        background:#fff;margin-bottom:8px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <div>
                        <span style='font-size:0.75rem;color:#94a3b8;'>{sim.simulation_type.replace('_', ' ').title()}</span>
                        <h4 style='margin:2px 0;'>{sim.title}</h4>
                        <p style='color:#6b7280;margin:0;font-size:0.82rem;'>{sim.description[:120]}</p>
                    </div>
                    <span style='font-size:0.75rem;color:#9ca3af;'>{sim.created_at[:10]}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Export
        st.divider()
        json_data = export_simulations_json(user_id)
        st.download_button(
            label="📥 Export All Simulations",
            data=json_data,
            file_name="pledge_simulations.json",
            mime="application/json",
            use_container_width=True,
        )
