"""Eco Impact Comparison Dashboard — main page component.

Renders a full comparison dashboard showing user impact metrics,
community benchmarks, trends, challenges, and goal tracking.
"""

import streamlit as st
from typing import List, Dict, Optional
from eco_impact_types import (
    UserProfile, CommunityStats, ImpactTrend, ComparisonResult,
    GoalProgress, EcoChallenge, ImpactCategory, ComparisonPeriod,
    REGIONAL_BENCHMARKS,
)
from eco_impact_data import (
    generate_mock_users, generate_community_stats,
    generate_impact_trends, generate_comparison_results,
    generate_mock_challenges, generate_mock_goals,
    generate_monthly_comparison_data, generate_id,
    calculate_carbon_footprint, calculate_water_footprint,
    calculate_eco_score, get_badge_level,
)
from eco_impact_cards import (
    render_metric_card, render_user_profile_card,
    render_comparison_card, render_goal_card,
    render_challenge_card, render_trend_indicator,
    render_leaderboard_row,
)
from eco_impact_charts import (
    create_eco_score_gauge, create_category_bar_chart,
    create_trend_line_chart, create_comparison_radar,
    create_pie_chart, create_grouped_bar_chart,
    create_heatmap_calendar,
)


def render_eco_impact_dashboard(user_id: str = None):
    """Render the full Eco Impact Comparison Dashboard."""

    # ─── Data Generation ──────────────────────────────────────────────
    users = generate_mock_users(20)
    community = generate_community_stats(users)
    current_user = users[0]
    if user_id:
        matched = next((u for u in users if u.user_id == user_id), None)
        if matched:
            current_user = matched

    trends = generate_impact_trends(current_user.user_id)
    comparisons = generate_comparison_results(current_user.user_id, users)
    challenges = generate_mock_challenges()
    goals = generate_mock_goals(current_user.user_id)
    monthly_data = generate_monthly_comparison_data(6)

    # ─── Page Header ──────────────────────────────────────────────────
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
            Eco Impact Comparison
        </div>
        <div style='font-size: 14px; color: #6b7280; max-width: 600px; margin: 0 auto;'>
            Compare your environmental impact with the community, track trends,
            and discover challenges to reduce your footprint.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── Stats Overview ───────────────────────────────────────────────
    st.markdown("### 📊 Your Impact at a Glance")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card(
            "Eco Score", f"{current_user.eco_score}",
            subtitle="out of 100",
            icon="🏆",
            delta=f"↑ {community.avg_eco_score - current_user.eco_score:.1f} vs avg",
            delta_color="normal" if current_user.eco_score > community.avg_eco_score else "inverse",
        )
    with col2:
        render_metric_card(
            "Carbon Saved", f"{current_user.carbon_saved_kg:.0f} kg",
            subtitle=f"≈ {current_user.trees_equivalent:.0f} trees",
            icon="🌱",
        )
    with col3:
        render_metric_card(
            "Water Saved", f"{current_user.water_saved_liters:,.0f} L",
            subtitle="annual conservation",
            icon="💧",
        )
    with col4:
        render_metric_card(
            "Community Rank",
            f"#{comparisons[0].rank}",
            subtitle=f"of {comparisons[0].total_participants}",
            icon="🏅",
            delta=f"Top {comparisons[0].percentile:.0f}%",
        )

    st.markdown("---")

    # ─── Tabs ─────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏆 Score & Comparison",
        "📈 Trends",
        "🎯 Goals & Challenges",
        "👥 Leaderboard",
        "🔬 Deep Analysis",
    ])

    # ─── Tab 1: Score & Comparison ────────────────────────────────────
    with tab1:
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("#### Your Eco Score")
            fig_gauge = create_eco_score_gauge(current_user.eco_score)
            st.plotly_chart(fig_gauge, use_container_width=True)

            st.markdown("#### Community Overview")
            render_metric_card(
                "Total Users", f"{community.total_users:,}",
                subtitle=f"{community.active_users_30d} active in last 30 days",
                icon="👥",
            )
            render_metric_card(
                "Community Avg Score", f"{community.avg_eco_score}",
                subtitle=f"{community.total_carbon_saved_tons:.1f} tons CO₂ saved",
                icon="🌍",
            )
            render_metric_card(
                "Trees Equivalent", f"{community.total_trees_equivalent:,}",
                subtitle=f"{community.total_water_saved_megaliters:.2f} ML water saved",
                icon="🌳",
            )

        with col_right:
            st.markdown("#### Comparison vs Community")
            fig_radar = create_comparison_radar(comparisons)
            st.plotly_chart(fig_radar, use_container_width=True)

            for result in comparisons:
                render_comparison_card(result)

            st.markdown("#### Impact Breakdown")
            carbon_data = calculate_carbon_footprint(
                "Car", 15.0, 250.0, "Vegetarian", 2, "Global"
            )
            fig_breakdown = create_pie_chart(
                values=[carbon_data["transport_kg"], carbon_data["energy_kg"],
                        carbon_data["food_kg"], carbon_data["flights_kg"]],
                labels=["Transport", "Energy", "Food", "Flights"],
                title="Carbon Footprint Breakdown (kg CO₂/year)",
            )
            st.plotly_chart(fig_breakdown, use_container_width=True)

    # ─── Tab 2: Trends ───────────────────────────────────────────────
    with tab2:
        st.markdown("#### 📈 Impact Trends (6-Month View)")

        for category, trend in trends.items():
            with st.expander(f"{category.value.title()} Trend", expanded=False):
                col_trend, col_indicator = st.columns([3, 1])
                with col_indicator:
                    render_trend_indicator(trend)
                    st.markdown(f"""
                    <div style='font-size: 11px; color: #9ca3af; margin-top: 8px;'>
                        Best: {trend.best_period}<br>
                        Worst: {trend.worst_period}<br>
                        Change: {trend.change_percent:+.1f}%
                    </div>
                    """, unsafe_allow_html=True)
                with col_trend:
                    fig_trend = create_trend_line_chart(trend, community_avg=150)
                    st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("#### 📊 Monthly Comparison")
        fig_monthly = create_grouped_bar_chart(
            periods=[d["period"] for d in monthly_data],
            user_data=[d["user_carbon"] for d in monthly_data],
            community_data=[d["community_avg"] for d in monthly_data],
            y_title="kg CO₂",
            title="Your Carbon vs Community Average (Monthly)",
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

        st.markdown("#### 💧 Water Usage Comparison")
        fig_water = create_grouped_bar_chart(
            periods=[d["period"] for d in monthly_data],
            user_data=[d["user_water"] for d in monthly_data],
            community_data=[d["community_water_avg"] for d in monthly_data],
            y_title="Liters",
            title="Your Water vs Community Average (Monthly)",
        )
        st.plotly_chart(fig_water, use_container_width=True)

    # ─── Tab 3: Goals & Challenges ───────────────────────────────────
    with tab3:
        col_goals, col_challenges = st.columns([1, 1])

        with col_goals:
            st.markdown("#### 🎯 Your Goals")
            for goal in goals:
                render_goal_card(goal)

            completed = sum(1 for g in goals if g.is_completed)
            st.info(f"**{completed}/{len(goals)}** goals completed. Keep going!")

        with col_challenges:
            st.markdown("#### 🏅 Active Challenges")
            for challenge in challenges:
                render_challenge_card(challenge)

            total_participants = sum(c.participants for c in challenges)
            st.info(f"**{total_participants:,}** participants across **{len(challenges)}** active challenges.")

    # ─── Tab 4: Leaderboard ──────────────────────────────────────────
    with tab4:
        st.markdown("#### 🏆 Community Leaderboard")

        sorted_users = sorted(users, key=lambda u: u.eco_score, reverse=True)

        col_filter, col_sort = st.columns([2, 1])
        with col_filter:
            region_filter = st.selectbox(
                "Filter by Region",
                ["All"] + list(set(u.region for u in users)),
                key="leaderboard_region",
            )
        with col_sort:
            sort_by = st.selectbox(
                "Sort by",
                ["Eco Score", "Carbon Saved", "Trees Equivalent"],
                key="leaderboard_sort",
            )

        filtered = sorted_users
        if region_filter != "All":
            filtered = [u for u in filtered if u.region == region_filter]

        sort_key = {
            "Eco Score": lambda u: u.eco_score,
            "Carbon Saved": lambda u: u.carbon_saved_kg,
            "Trees Equivalent": lambda u: u.trees_equivalent,
        }.get(sort_by, lambda u: u.eco_score)
        filtered = sorted(filtered, key=sort_key, reverse=True)

        for i, user in enumerate(filtered[:15]):
            is_current = user.user_id == current_user.user_id
            render_leaderboard_row(i + 1, user, is_current_user=is_current)

        # Regional Averages
        if community.regional_averages:
            st.markdown("#### 🌍 Regional Averages")
            fig_regional = create_grouped_bar_chart(
                periods=list(community.regional_averages.keys()),
                user_data=[community.avg_eco_score] * len(community.regional_averages),
                community_data=list(community.regional_averages.values()),
                y_title="Eco Score",
                title="Your Score vs Regional Averages",
            )
            st.plotly_chart(fig_regional, use_container_width=True)

    # ─── Tab 5: Deep Analysis ────────────────────────────────────────
    with tab5:
        st.markdown("#### 🔬 Impact Deep Analysis")

        col_carbon, col_water = st.columns(2)

        with col_carbon:
            st.markdown("**Carbon Footprint Calculator**")
            transport = st.selectbox("Transport", ["Car", "Bike", "Public Transport", "Walking", "Electric Car"], key="analysis_transport")
            distance = st.number_input("Daily Distance (km)", value=15.0, min_value=0.0, key="analysis_distance")
            electricity = st.number_input("Monthly Electricity (kWh)", value=250.0, min_value=0.0, key="analysis_electricity")
            diet = st.selectbox("Diet", ["Vegetarian", "Vegan", "Omnivore", "Heavy Meat"], key="analysis_diet")
            flights = st.number_input("Annual Flights", value=2, min_value=0, key="analysis_flights")

            if st.button("🧮 Calculate Impact", key="calc_impact"):
                carbon = calculate_carbon_footprint(transport, distance, electricity, diet, flights, "Global")
                water = calculate_water_footprint(8, 3, 4, 15, diet)

                st.success("✅ Calculation Complete!")

                col_c1, col_c2, col_c3, col_c4 = st.columns(4)
                with col_c1:
                    render_metric_card("Transport", f"{carbon['transport_kg']:.0f} kg", icon="🚗")
                with col_c2:
                    render_metric_card("Energy", f"{carbon['energy_kg']:.0f} kg", icon="⚡")
                with col_c3:
                    render_metric_card("Food", f"{carbon['food_kg']:.0f} kg", icon="🍽️")
                with col_c4:
                    render_metric_card("Total", f"{carbon['total_kg']:.0f} kg", icon="🌍")

                fig_calc = create_pie_chart(
                    values=[carbon["transport_kg"], carbon["energy_kg"],
                            carbon["food_kg"], carbon["flights_kg"]],
                    labels=["Transport", "Energy", "Food", "Flights"],
                    title="Your Carbon Breakdown",
                )
                st.plotly_chart(fig_calc, use_container_width=True)

                render_metric_card("Water Footprint", f"{water['total_liters']:,.0f} L/year", icon="💧")

        with col_water:
            st.markdown("**Regional Benchmarks**")
            benchmark_data = {}
            for region, data in REGIONAL_BENCHMARKS.items():
                benchmark_data[region] = data["avg_carbon_kg_year"]

            fig_benchmark = create_category_bar_chart(
                benchmark_data,
                title="Average Annual Carbon by Region (kg CO₂)",
            )
            st.plotly_chart(fig_benchmark, use_container_width=True)

            st.markdown("**Activity Heatmap**")
            fig_heatmap = create_heatmap_calendar(weeks=12, title="Your Eco Activity (Last 12 Weeks)")
            st.plotly_chart(fig_heatmap, use_container_width=True)

            st.markdown("**Impact Categories Weight**")
            fig_weights = create_pie_chart(
                values=[30, 20, 20, 15, 10, 5],
                labels=["Carbon", "Water", "Energy", "Waste", "Transport", "Food"],
                title="Eco Score Weight Distribution",
            )
            st.plotly_chart(fig_weights, use_container_width=True)

    # ─── Footer ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;'>
        🌱 Eco Impact Dashboard · Track · Compare · Improve<br>
        Data is for demonstration purposes. Connect your assessment data for real insights.
    </div>
    """, unsafe_allow_html=True)
