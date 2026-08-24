"""Green Transportation Planner — main page component.

Plan green routes, compare transport modes, and track your travel footprint.
"""

import streamlit as st
from typing import List, Dict
from transport_types import (
    TransportMode, TripCategory, Route, TripLog, EmissionComparison,
    MODE_ICONS, MODE_COLORS,
)
from transport_data import (
    generate_route_options, generate_mock_trip_logs, generate_mock_vehicles,
    generate_mock_commute_stats, generate_mock_transport_stats,
    generate_emission_comparison, generate_id,
)
from transport_cards import (
    render_metric_card, render_route_card, render_trip_log_card,
    render_emission_comparison_card, render_vehicle_card,
    render_commute_insight_card,
)
from transport_charts import (
    create_mode_distribution_pie, create_monthly_trend_chart,
    create_emission_comparison_bar, create_cost_vs_emission_scatter,
    create_emission_waterfall, create_route_radar,
)


def render_green_transport_planner(user_id: str = None):
    """Render the full Green Transportation Planner."""

    # ─── Data ─────────────────────────────────────────────────────────
    trip_logs = generate_mock_trip_logs(40)
    vehicles = generate_mock_vehicles()
    commute_stats = generate_mock_commute_stats()
    transport_stats = generate_mock_transport_stats(trip_logs)

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
        <div style='font-size: 36px; margin-bottom: 8px;'>🚲</div>
        <div style='font-size: 26px; font-weight: 800; color: #111827; margin-bottom: 6px;'>
            Green Transportation Planner
        </div>
        <div style='font-size: 14px; color: #6b7280; max-width: 600px; margin: 0 auto;'>
            Plan eco-friendly routes, compare transport modes, and reduce your travel carbon footprint.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── Stats Overview ───────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card(
            "Total Trips", f"{transport_stats.total_trips}",
            subtitle="in tracking period",
            icon="🚗",
        )
    with col2:
        render_metric_card(
            "CO₂ Avoided", f"{transport_stats.co2_avoided_kg:.1f} kg",
            subtitle=f"≈ {transport_stats.trees_equivalent} trees",
            icon="🌿",
        )
    with col3:
        render_metric_card(
            "Total Distance", f"{transport_stats.total_distance_km:.0f} km",
            subtitle=f"${transport_stats.total_cost_usd:.0f} total cost",
            icon="📏",
        )
    with col4:
        render_metric_card(
            "Calories Burned", f"{transport_stats.total_calories:,.0f}",
            subtitle="from active transport",
            icon="🔥",
        )

    st.markdown("---")

    # ─── Tabs ─────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ Route Planner",
        "📊 Mode Comparison",
        "📋 Trip History",
        "📈 Analytics",
        "🚗 My Vehicles",
    ])

    # ─── Tab 1: Route Planner ────────────────────────────────────────
    with tab1:
        st.markdown("### 🗺️ Plan Your Route")

        col_input, col_results = st.columns([1, 2])

        with col_input:
            origin = st.text_input("From", value="Home", key="route_origin")
            destination = st.text_input("To", value="Office", key="route_dest")
            distance = st.number_input("Distance (km)", min_value=0.1, value=5.0, step=0.5, key="route_dist")
            pref = st.selectbox("Preference", ["Greenest", "Fastest", "Cheapest", "Shortest"], key="route_pref")

            if st.button("🔍 Find Routes", key="find_routes", use_container_width=True):
                routes = generate_route_options(origin, destination, distance)
                st.session_state["route_results"] = routes
                st.session_state["compare_routes"] = True

        with col_results:
            if "route_results" in st.session_state and st.session_state.get("compare_routes"):
                routes = st.session_state["route_results"]

                # Sort by preference
                pref_sort = {
                    "Greenest": lambda r: r.emission_kg,
                    "Fastest": lambda r: r.duration_minutes,
                    "Cheapest": lambda r: r.cost_usd,
                    "Shortest": lambda r: r.distance_km,
                }
                routes = sorted(routes, key=pref_sort.get(pref, lambda r: r.emission_kg))

                st.markdown(f"**{len(routes)} routes found** from {origin} to {destination}")
                for i, route in enumerate(routes):
                    render_route_card(route, i)

                # Compare top 2
                if len(routes) >= 2:
                    st.markdown("---")
                    st.markdown("### ⚖️ Route Comparison")
                    fig_radar = create_route_radar(routes[0], routes[-1])
                    st.plotly_chart(fig_radar, use_container_width=True)

                # Emission comparison
                st.markdown("---")
                st.markdown("### 🌿 Emission Comparison")
                comparisons = generate_emission_comparison(distance)
                for comp in comparisons:
                    render_emission_comparison_card(comp)

                fig_bar = create_emission_comparison_bar(comparisons)
                st.plotly_chart(fig_bar, use_container_width=True)

                fig_scatter = create_cost_vs_emission_scatter(comparisons)
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("👆 Enter your route details and click Find Routes to compare options.")

    # ─── Tab 2: Mode Comparison ──────────────────────────────────────
    with tab2:
        st.markdown("### 📊 Transport Mode Comparison")

        comparison_dist = st.slider("Distance for comparison (km)", 1, 50, 10, key="comp_dist")

        comparisons = generate_emission_comparison(comparison_dist)
        for comp in comparisons:
            render_emission_comparison_card(comp)

        st.markdown("---")
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            fig_bar = create_emission_comparison_bar(comparisons)
            st.plotly_chart(fig_bar, use_container_width=True)
        with col_chart2:
            fig_scatter = create_cost_vs_emission_scatter(comparisons)
            st.plotly_chart(fig_scatter, use_container_width=True)

        # Waterfall
        car_emission = comparison_dist * 0.19
        greenest_emission = comparison_dist * 0.0
        avoided = car_emission - greenest_emission
        fig_waterfall = create_emission_waterfall(car_emission, avoided)
        st.plotly_chart(fig_waterfall, use_container_width=True)

    # ─── Tab 3: Trip History ─────────────────────────────────────────
    with tab3:
        st.markdown("### 📋 Trip History")

        col_filter, col_stats = st.columns([3, 1])
        with col_stats:
            st.markdown("#### Quick Stats")
            render_commute_insight_card(commute_stats)

        with col_filter:
            # Filters
            with st.expander("🔍 Filter Trips", expanded=True):
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    cat_filter = st.selectbox("Category", ["All"] + [c.value.title() for c in TripCategory], key="trip_cat")
                with fc2:
                    mode_filter = st.selectbox("Mode", ["All"] + [m.value.replace("_", " ").title() for m in TransportMode], key="trip_mode")
                with fc3:
                    sort_by = st.selectbox("Sort by", ["Date", "Distance", "Emission", "Cost"], key="trip_sort")

            # Apply filters
            filtered = trip_logs
            if cat_filter != "All":
                filtered = [l for l in filtered if l.category.value.title() == cat_filter]
            if mode_filter != "All":
                mode_enum = next((m for m in TransportMode if m.value.replace("_", " ").title() == mode_filter), None)
                if mode_enum:
                    filtered = [l for l in filtered if l.mode == mode_enum]

            st.markdown(f"**{len(filtered)}** trips found")

            for log in filtered[:20]:
                render_trip_log_card(log)

    # ─── Tab 4: Analytics ────────────────────────────────────────────
    with tab4:
        st.markdown("### 📈 Transport Analytics")

        col_a, col_b = st.columns(2)
        with col_a:
            fig_pie = create_mode_distribution_pie(transport_stats.mode_distribution)
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_b:
            fig_trend = create_monthly_trend_chart(transport_stats.monthly_trend)
            st.plotly_chart(fig_trend, use_container_width=True)

        # Key metrics
        st.markdown("---")
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            render_metric_card("Avg Emission/Trip", f"{transport_stats.avg_emission_per_trip:.3f} kg", icon="🌿")
        with mc2:
            render_metric_card("Greenest Mode", transport_stats.greenest_mode.value.replace("_", " ").title(), icon="🏆")
        with mc3:
            render_metric_card("Most Used", transport_stats.most_used_mode.value.replace("_", " ").title(), icon="🚀")
        with mc4:
            render_metric_card("CO₂ Saved", f"{transport_stats.co2_avoided_kg:.1f} kg", icon="💚")

    # ─── Tab 5: My Vehicles ──────────────────────────────────────────
    with tab5:
        st.markdown("### 🚗 My Vehicles")
        for vehicle in vehicles:
            render_vehicle_card(vehicle)

        # Add vehicle form
        with st.expander("➕ Add New Vehicle"):
            vc1, vc2 = st.columns(2)
            with vc1:
                v_name = st.text_input("Vehicle Name", key="v_name")
                v_type = st.selectbox("Type", [t.value.replace("_", " ").title() for t in
                    __import__('transport_types', fromlist=['VehicleType']).VehicleType], key="v_type")
                v_year = st.number_input("Year", min_value=1990, max_value=2026, value=2022, key="v_year")
            with vc2:
                v_make = st.text_input("Make", key="v_make")
                v_model = st.text_input("Model", key="v_model")
                v_efficiency = st.number_input("Fuel Efficiency (km/L)", min_value=1.0, value=12.0, key="v_eff")

            if st.button("Add Vehicle", key="add_vehicle"):
                if v_name:
                    st.success(f"✅ Vehicle '{v_name}' added!")
                else:
                    st.warning("Please enter a vehicle name.")

    # ─── Footer ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;'>
        🚲 Green Transportation Planner · Plan · Compare · Reduce<br>
        Choose greener transport options to reduce your carbon footprint.
    </div>
    """, unsafe_allow_html=True)
