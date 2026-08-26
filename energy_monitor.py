"""Energy Monitoring Dashboard — main page component.

Real-time energy monitoring, appliance tracking, and AI-powered insights.
"""

import streamlit as st
from typing import List, Dict
from energy_types import (
    ApplianceCategory, EnergySource, APPLIANCE_ICONS,
)
from energy_data import (
    generate_mock_appliances, generate_mock_devices, generate_mock_alerts,
    generate_mock_goals, generate_mock_bills, generate_mock_insights,
    generate_mock_readings, generate_mock_stats,
)
from energy_cards import (
    render_metric_card, render_appliance_card, render_device_card,
    render_alert_card, render_goal_card, render_bill_card,
    render_insight_card,
)
from energy_charts import (
    create_hourly_pattern_chart, create_category_breakdown_pie,
    create_source_mix_chart, create_monthly_trend_chart,
    create_cost_comparison_gauge, create_category_bar_chart,
    create_peak_vs_offpeak_chart,
)


def render_energy_monitor_dashboard(user_id: str = None):
    """Render the full Energy Monitoring Dashboard."""

    # ─── Data ─────────────────────────────────────────────────────────
    appliances = generate_mock_appliances()
    devices = generate_mock_devices()
    alerts = generate_mock_alerts()
    goals = generate_mock_goals()
    bills = generate_mock_bills()
    insights = generate_mock_insights()
    readings = generate_mock_readings(48)
    stats = generate_mock_stats(bills, appliances, alerts)

    # ─── Header ───────────────────────────────────────────────────────
    st.markdown("""
    <div style='
        text-align: center;
        padding: 28px 20px;
        background: linear-gradient(145deg, rgba(245,158,11,0.06), rgba(14,165,233,0.04));
        border: 1px solid rgba(245,158,11,0.15);
        border-radius: 18px;
        margin-bottom: 24px;
    '>
        <div style='font-size: 36px; margin-bottom: 8px;'>⚡</div>
        <div style='font-size: 26px; font-weight: 800; color: #111827; margin-bottom: 6px;'>
            Energy Monitoring Dashboard
        </div>
        <div style='font-size: 14px; color: #6b7280; max-width: 600px; margin: 0 auto;'>
            Track real-time consumption, monitor appliances, and discover AI-powered savings opportunities.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── Stats Overview ───────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card(
            "Monthly Usage", f"{stats.total_kwh_month:.0f} kWh",
            subtitle=f"${stats.total_cost_month:.2f} total",
            icon="⚡",
            delta=f"{stats.comparison_last_month_percent:+.1f}% vs last month",
            delta_color="normal" if stats.comparison_last_month_percent < 0 else "inverse",
        )
    with col2:
        render_metric_card(
            "Daily Average", f"{stats.avg_daily_kwh:.1f} kWh",
            subtitle=f"Peak today: {stats.peak_kwh_today} kWh",
            icon="📊",
        )
    with col3:
        render_metric_card(
            "Renewable", f"{stats.renewable_percent:.0f}%",
            subtitle="solar + wind + hydro",
            icon="🌱",
        )
    with col4:
        render_metric_card(
            "Savings", f"${stats.savings_this_month_usd:.2f}",
            subtitle=f"{stats.alerts_count} active alerts",
            icon="💰",
        )

    st.markdown("---")

    # ─── Tabs ─────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🏠 Appliances",
        "📡 Devices",
        "💡 Insights",
        "📈 Bills & Goals",
    ])

    # ─── Tab 1: Overview ─────────────────────────────────────────────
    with tab1:
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.markdown("#### ⚡ Real-Time Consumption")
            fig_hourly = create_hourly_pattern_chart(stats.hourly_pattern)
            st.plotly_chart(fig_hourly, use_container_width=True)

            st.markdown("#### 📈 Monthly Trends")
            fig_monthly = create_monthly_trend_chart(stats.monthly_trend)
            st.plotly_chart(fig_monthly, use_container_width=True)

            st.markdown("#### 🏠 Peak vs Off-Peak")
            fig_peak = create_peak_vs_offpeak_chart(bills)
            st.plotly_chart(fig_peak, use_container_width=True)

        with col_right:
            st.markdown("#### 💰 Cost vs Target")
            fig_gauge = create_cost_comparison_gauge(stats.total_cost_month, 45.0)
            st.plotly_chart(fig_gauge, use_container_width=True)

            st.markdown("#### ⚡ Energy by Category")
            fig_cat = create_category_breakdown_pie(stats.category_breakdown)
            st.plotly_chart(fig_cat, use_container_width=True)

            st.markdown("#### 🌱 Source Mix")
            fig_source = create_source_mix_chart(stats.source_breakdown)
            st.plotly_chart(fig_source, use_container_width=True)

            st.markdown("#### 📊 Category Breakdown")
            fig_bar = create_category_bar_chart(stats.category_breakdown)
            st.plotly_chart(fig_bar, use_container_width=True)

    # ─── Tab 2: Appliances ───────────────────────────────────────────
    with tab2:
        st.markdown("### 🏠 Monitored Appliances")

        # Category Filter
        cat_filter = st.selectbox(
            "Filter by Category",
            ["All"] + [c.value.replace("_", " ").title() for c in ApplianceCategory],
            key="app_cat_filter",
        )

        filtered = appliances
        if cat_filter != "All":
            cat_enum = next((c for c in ApplianceCategory if c.value.replace("_", " ").title() == cat_filter), None)
            if cat_enum:
                filtered = [a for a in filtered if a.category == cat_enum]

        # Sort
        sort_by = st.selectbox("Sort by", ["Daily kWh", "Monthly Cost", "Power Rating", "Name"], key="app_sort")
        sort_key = {
            "Daily kWh": lambda a: a.avg_daily_kwh,
            "Monthly Cost": lambda a: a.monthly_cost_usd,
            "Power Rating": lambda a: a.rated_power_watts,
            "Name": lambda a: a.name,
        }.get(sort_by, lambda a: a.avg_daily_kwh)
        filtered = sorted(filtered, key=sort_key, reverse=(sort_by != "Name"))

        col_grid1, col_grid2 = st.columns(2)
        for i, appliance in enumerate(filtered):
            with col_grid1 if i % 2 == 0 else col_grid2:
                render_appliance_card(appliance)

        # Total
        total_daily = sum(a.avg_daily_kwh for a in filtered)
        total_monthly = sum(a.monthly_cost_usd for a in filtered)
        st.info(f"**{len(filtered)}** appliances · **{total_daily:.1f}** kWh/day · **${total_monthly:.2f}**/month")

    # ─── Tab 3: Devices ──────────────────────────────────────────────
    with tab3:
        st.markdown("### 📡 Smart Energy Devices")

        online = sum(1 for d in devices if d.is_online)
        st.markdown(f"**{online}/{len(devices)}** devices online")

        for device in devices:
            render_device_card(device)

        # Total power
        total_watts = sum(d.current_power_watts for d in devices if d.is_online)
        total_today = sum(d.today_kwh for d in devices)
        render_metric_card("Total Real-Time", f"{total_watts:,} W", subtitle=f"{total_today:.1f} kWh today", icon="⚡")

    # ─── Tab 4: Insights ─────────────────────────────────────────────
    with tab4:
        st.markdown("### 💡 AI Energy Insights")

        total_savings_kwh = sum(i.potential_savings_kwh for i in insights)
        total_savings_usd = sum(i.potential_savings_usd for i in insights)
        total_carbon = sum(i.potential_carbon_kg for i in insights)

        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            render_metric_card("Potential Savings", f"{total_savings_kwh:,.0f} kWh/year", icon="⚡")
        with ic2:
            render_metric_card("Cost Savings", f"${total_savings_usd:,.2f}/year", icon="💰")
        with ic3:
            render_metric_card("CO₂ Reduction", f"{total_carbon:,.0f} kg/year", icon="🌿")

        for insight in insights:
            render_insight_card(insight)

        # Alerts
        st.markdown("### 🚨 Active Alerts")
        unread_alerts = [a for a in alerts if not a.is_read]
        if unread_alerts:
            for alert in unread_alerts:
                render_alert_card(alert)
        else:
            st.success("✅ No unread alerts. Your system is running smoothly!")

    # ─── Tab 5: Bills & Goals ────────────────────────────────────────
    with tab5:
        col_bills, col_goals = st.columns([1, 1])

        with col_bills:
            st.markdown("### 📄 Monthly Bills")
            for bill in reversed(bills):
                render_bill_card(bill)

        with col_goals:
            st.markdown("### 🎯 Energy Goals")
            for goal in goals:
                render_goal_card(goal)

            completed = sum(1 for g in goals if g.is_completed)
            st.info(f"**{completed}/{len(goals)}** goals achieved!")

            # Add goal
            with st.expander("➕ Add New Goal"):
                g_title = st.text_input("Goal Title", key="energy_goal_title")
                g_target = st.number_input("Target Value", min_value=1.0, value=100.0, key="energy_goal_target")
                g_unit = st.text_input("Unit", value="kWh", key="energy_goal_unit")
                g_deadline = st.date_input("Deadline", key="energy_goal_deadline")

                if st.button("Create Goal", key="create_energy_goal"):
                    if g_title:
                        st.success(f"✅ Goal '{g_title}' created!")
                    else:
                        st.warning("Please enter a goal title.")

    # ─── Footer ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;'>
        ⚡ Energy Monitoring Dashboard · Track · Optimize · Save<br>
        Real-time monitoring powered by smart device integration.
    </div>
    """, unsafe_allow_html=True)
