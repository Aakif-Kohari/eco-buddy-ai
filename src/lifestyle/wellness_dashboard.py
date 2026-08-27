"""Eco Wellness Tracker Dashboard — main page component.

Track daily eco habits, monitor streaks, and visualize your wellness journey.
"""

import streamlit as st
from typing import List, Dict
from src.lifestyle.wellness_types import (
    EcoHabit, HabitStreak, DailyWellnessScore, WellnessGoal,
    WellnessWeeklyReport, WellnessStats, HabitCategory,
    CATEGORY_ICONS, CATEGORY_COLORS, MOOD_LABELS, ENERGY_LABELS,
)
from src.lifestyle.wellness_data import (
    generate_mock_habits, generate_mock_streaks, generate_mock_daily_scores,
    generate_mock_goals, generate_mock_weekly_reports, generate_mock_stats,
    generate_mock_logs, calculate_wellness_score,
)
from src.lifestyle.wellness_cards import (
    render_metric_card, render_habit_card, render_streak_leaderboard,
    render_goal_card, render_weekly_report_card, render_mood_energy_selector,
    render_log_entry,
)
from src.lifestyle.wellness_charts import (
    create_wellness_score_trend, create_habits_completion_bar,
    create_category_breakdown, create_streak_heatmap,
    create_mood_energy_radar, create_points_timeline,
    create_nature_mindfulness_area,
)


def render_eco_wellness_dashboard(user_id: str = None):
    """Render the full Eco Wellness Tracker Dashboard."""

    # ─── Data ─────────────────────────────────────────────────────────
    habits = generate_mock_habits()
    streaks = generate_mock_streaks(habits, "user_001")
    daily_scores = generate_mock_daily_scores(30)
    goals = generate_mock_goals("user_001")
    weekly_reports = generate_mock_weekly_reports(4)
    stats = generate_mock_stats(habits, streaks, daily_scores)
    logs = generate_mock_logs(habits, 30)

    # ─── Header ───────────────────────────────────────────────────────
    st.markdown("""
    <div style='
        text-align: center;
        padding: 28px 20px;
        background: linear-gradient(145deg, rgba(34,197,94,0.06), rgba(236,72,153,0.03));
        border: 1px solid rgba(74,222,128,0.15);
        border-radius: 18px;
        margin-bottom: 24px;
    '>
        <div style='font-size: 36px; margin-bottom: 8px;'>🌿</div>
        <div style='font-size: 26px; font-weight: 800; color: #111827; margin-bottom: 6px;'>
            Eco Wellness Tracker
        </div>
        <div style='font-size: 14px; color: #6b7280; max-width: 600px; margin: 0 auto;'>
            Build sustainable habits, track your streaks, and monitor your eco wellness journey.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── Stats Overview ───────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card(
            "Wellness Score", f"{stats.avg_daily_score}",
            subtitle=f"out of 100",
            icon="🏆",
            delta=f"{'📈' if stats.weekly_trend == 'improving' else '➡️' if stats.weekly_trend == 'stable' else '📉'} {stats.weekly_trend.title()}",
        )
    with col2:
        render_metric_card(
            "Best Streak", f"🔥 {stats.current_best_streak} days",
            subtitle=f"across all habits",
            icon="🔥",
        )
    with col3:
        render_metric_card(
            "Carbon Saved", f"{stats.total_carbon_saved_kg:.1f} kg",
            subtitle="total impact",
            icon="🌱",
        )
    with col4:
        render_metric_card(
            "Completion", f"{stats.completion_rate:.0%}",
            subtitle=f"{stats.total_completions} total completions",
            icon="📊",
            delta=f"{stats.active_habits}/{stats.total_habits} active",
        )

    st.markdown("---")

    # ─── Tabs ─────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "✅ Daily Habits",
        "📈 Trends & Charts",
        "🏆 Streaks & Goals",
        "📋 Weekly Reports",
        "📝 Activity Log",
    ])

    # ─── Tab 1: Daily Habits ─────────────────────────────────────────
    with tab1:
        st.markdown("### ✅ Today's Eco Habits")

        # Category Filter
        cat_filter = st.selectbox(
            "Filter by Category",
            ["All"] + [c.value.title() for c in HabitCategory],
            key="habit_cat_filter",
        )

        filtered_habits = habits
        if cat_filter != "All":
            cat_enum = next((c for c in HabitCategory if c.value.title() == cat_filter), None)
            if cat_enum:
                filtered_habits = [h for h in filtered_habits if h.category == cat_enum]

        # Mood & Energy
        mood, energy = render_mood_energy_selector()

        # Habit Cards
        completed_count = 0
        for habit in filtered_habits:
            streak = next((s for s in streaks if s.habit_id == habit.habit_id), None)
            completed = streak.is_active_today if streak else False
            if completed:
                completed_count += 1

            col_habit, col_check = st.columns([5, 1])
            with col_habit:
                render_habit_card(habit, streak, completed_today=completed)
            with col_check:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if not completed:
                    if st.button("✓", key=f"check_{habit.habit_id}", help="Mark as done"):
                        st.success(f"✅ {habit.name} completed! +{habit.eco_points} pts")
                        st.rerun()
                else:
                    st.markdown("<div style='text-align: center; color: #22c55e; font-size: 20px;'>✅</div>", unsafe_allow_html=True)

        # Summary
        rate = completed_count / max(len(filtered_habits), 1)
        if rate >= 0.8:
            st.success(f"🎉 Amazing! You've completed {completed_count}/{len(filtered_habits)} habits today!")
        elif rate >= 0.5:
            st.info(f"👍 Good progress! {completed_count}/{len(filtered_habits)} habits done. Keep going!")
        else:
            st.warning(f"💪 {completed_count}/{len(filtered_habits)} done. You've got this!")

    # ─── Tab 2: Trends & Charts ──────────────────────────────────────
    with tab2:
        st.markdown("### 📈 Wellness Trends")

        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            fig_trend = create_wellness_score_trend(daily_scores)
            st.plotly_chart(fig_trend, use_container_width=True)
            fig_completion = create_habits_completion_bar(daily_scores)
            st.plotly_chart(fig_completion, use_container_width=True)
        with col_chart2:
            fig_category = create_category_breakdown(habits)
            st.plotly_chart(fig_category, use_container_width=True)
            fig_points = create_points_timeline(daily_scores)
            st.plotly_chart(fig_points, use_container_width=True)

        st.markdown("---")
        col_chart3, col_chart4 = st.columns(2)
        with col_chart3:
            fig_radar = create_mood_energy_radar(daily_scores)
            st.plotly_chart(fig_radar, use_container_width=True)
        with col_chart4:
            fig_nature = create_nature_mindfulness_area(daily_scores)
            st.plotly_chart(fig_nature, use_container_width=True)

    # ─── Tab 3: Streaks & Goals ──────────────────────────────────────
    with tab3:
        col_streaks, col_goals = st.columns([1, 1])

        with col_streaks:
            st.markdown("### 🔥 Streak Leaderboard")
            render_streak_leaderboard(streaks, habits)

            st.markdown("### 📊 Streak Performance")
            fig_streaks = create_streak_heatmap(streaks, habits)
            st.plotly_chart(fig_streaks, use_container_width=True)

        with col_goals:
            st.markdown("### 🎯 Your Goals")
            for goal in goals:
                render_goal_card(goal)

            completed_goals = sum(1 for g in goals if g.is_completed)
            st.info(f"**{completed_goals}/{len(goals)}** goals completed!")

            # Add new goal
            with st.expander("➕ Add New Goal"):
                new_goal_title = st.text_input("Goal Title", key="new_goal_title")
                new_goal_cat = st.selectbox("Category", [c.value.title() for c in HabitCategory], key="new_goal_cat")
                new_goal_target = st.number_input("Target", min_value=1.0, value=30.0, key="new_goal_target")
                new_goal_unit = st.text_input("Unit", value="days", key="new_goal_unit")
                new_goal_deadline = st.date_input("Deadline", key="new_goal_deadline")

                if st.button("Create Goal", key="create_goal"):
                    if new_goal_title:
                        st.success(f"✅ Goal '{new_goal_title}' created!")
                    else:
                        st.warning("Please enter a goal title.")

    # ─── Tab 4: Weekly Reports ───────────────────────────────────────
    with tab4:
        st.markdown("### 📋 Weekly Wellness Reports")

        for report in reversed(weekly_reports):
            render_weekly_report_card(report)

        # Weekly comparison chart
        if weekly_reports:
            st.markdown("### 📊 Weekly Comparison")
            import plotly.graph_objects as go
            weeks = [r.week_start for r in weekly_reports]
            points = [r.total_eco_points for r in weekly_reports]
            carbon = [r.total_carbon_saved_kg for r in weekly_reports]
            completion = [r.completion_rate * 100 for r in weekly_reports]

            fig = go.Figure()
            fig.add_trace(go.Bar(x=weeks, y=points, name="Eco Points", marker=dict(color="#22c55e", cornerradius=4)))
            fig.add_trace(go.Scatter(x=weeks, y=carbon, name="Carbon Saved (kg)", mode="lines+markers",
                                    line=dict(color="#0ea5e9", width=3), yaxis="y2"))

            fig.update_layout(
                title="Weekly Performance",
                height=300,
                margin=dict(t=40, b=40, l=50, r=50),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(title="Eco Points", tickfont=dict(size=10, color="#9ca3af")),
                yaxis2=dict(title="Carbon (kg)", overlaying="y", side="right", tickfont=dict(size=10, color="#9ca3af")),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
                font={"family": "Inter, sans-serif"},
            )
            st.plotly_chart(fig, use_container_width=True)

    # ─── Tab 5: Activity Log ─────────────────────────────────────────
    with tab5:
        st.markdown("### 📝 Recent Activity")

        habit_map = {h.habit_id: h for h in habits}

        # Filter
        log_filter = st.selectbox(
            "Filter by Category",
            ["All"] + [c.value.title() for c in HabitCategory],
            key="log_cat_filter",
        )

        filtered_logs = logs
        if log_filter != "All":
            cat_enum = next((c for c in HabitCategory if c.value.title() == log_filter), None)
            if cat_enum:
                filtered_logs = [l for l in logs if habit_map.get(l.habit_id, None) and habit_map[l.habit_id].category == cat_enum]

        for log in filtered_logs[:20]:
            habit = habit_map.get(log.habit_id)
            render_log_entry(
                {"completed_at": log.completed_at, "eco_points_earned": log.eco_points_earned},
                habit_name=habit.name if habit else "Unknown",
                habit_icon=habit.icon if habit else "🌿",
            )

        if not filtered_logs:
            st.info("No activity logs found for this filter.")

    # ─── Footer ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;'>
        🌿 Eco Wellness Tracker · Build Habits · Track Streaks · Grow Green<br>
        Small daily actions create lasting environmental impact.
    </div>
    """, unsafe_allow_html=True)
