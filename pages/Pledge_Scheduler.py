"""
Pledge Smart Scheduler – Streamlit Page
=========================================
AI-powered pledge scheduling: personalised nudges, habit formation
tracking, optimal pledge combinations, weekly planner, difficulty
ramping, and streak protection.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from pledge_habit_engine import (
    init_habit_tables,
    build_habit_profiles,
    generate_nudges,
    suggest_optimal_combos,
    recommend_difficulty,
    generate_weekly_plan,
    get_streak_protection,
    use_streak_protection,
    generate_habit_insights,
    get_schedule_preferences,
    save_schedule_preferences,
    habit_profile_to_dict,
    nudge_to_dict,
    combo_to_dict,
    planner_to_dict,
    HABIT_FORMATION_WEEKS,
    HABIT_THRESHOLD_PCT,
    DIFFICULTY_LABELS,
    ComboStrategy,
)
from green_pledge_tracker import (
    init_pledge_tables,
    current_week_start,
    current_week_end,
    get_user_pledge_stats,
    get_user_weekly_pledges,
    PLEDGE_CATEGORIES,
)

st.set_page_config(page_title="Pledge Scheduler", page_icon="📅", layout="wide")

# Initialise tables
init_pledge_tables()
init_habit_tables()

# ── Auth gate ────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("🔒 Please sign in to use the Pledge Scheduler.")
    st.stop()

# ── Page header ──────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:10px 0 4px;'>
    <h1 style='margin:0;font-size:2.4rem;'>📅 Pledge Smart Scheduler</h1>
    <p style='color:#6b7280;margin-top:4px;font-size:1.05rem;'>
        Build lasting eco-habits with personalised nudges, smart scheduling, and streak protection.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────────────
tab_nudges, tab_habits, tab_combos, tab_planner, tab_difficulty, tab_streak, tab_settings = st.tabs([
    "🔔 Nudges",
    "🧠 Habit Profiles",
    "🎯 Optimal Combos",
    "📋 Weekly Planner",
    "⬆️ Difficulty",
    "🔥 Streak Guard",
    "⚙️ Settings",
])

# =====================================================================
# TAB: Nudges
# =====================================================================
with tab_nudges:
    st.subheader("🔔 Personalised Nudges")

    nudges = generate_nudges(user_id)

    if not nudges:
        st.info("No nudges right now. Keep pledging and checking in to unlock personalised nudges!")
    else:
        priority_styles = {
            "high": ("🚨", "#ef4444", "#fef2f2"),
            "medium": ("⚡", "#f59e0b", "#fffbeb"),
            "low": ("💡", "#3b82f6", "#eff6ff"),
        }

        for nudge in sorted(nudges, key=lambda n: {"high": 0, "medium": 1, "low": 2}.get(n.priority, 3)):
            pri_emoji, pri_color, pri_bg = priority_styles.get(nudge.priority, ("💡", "#6b7280", "#f9fafb"))

            st.markdown(f"""
            <div style='border:1px solid {pri_color}30;border-radius:14px;padding:18px;
                        background:linear-gradient(135deg,{pri_bg},#fff);margin-bottom:12px;'>
                <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                    <div>
                        <span style='font-size:0.75rem;color:{pri_color};font-weight:600;'>
                            {pri_emoji} {nudge.nudge_type.replace('_', ' ').title()}
                        </span>
                        <h4 style='margin:4px 0;'>{nudge.icon} {nudge.title}</h4>
                        <p style='color:#6b7280;margin:4px 0 0;font-size:0.9rem;'>{nudge.message}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if nudge.action_label and nudge.action_template_id:
                if st.button(
                    f"✅ {nudge.action_label}",
                    key=f"nudge_action_{nudge.nudge_id}",
                ):
                    st.session_state["nudge_action"] = nudge.action_template_id
                    st.info("Head to the **Browse Pledges** page to enrol!")
            elif nudge.action_label:
                st.caption(f"→ {nudge.action_label}")

    # Habit insights
    st.divider()
    st.markdown("#### 📊 Habit Formation Insights")
    habit_insights = generate_habit_insights(user_id)
    if habit_insights:
        for hi in habit_insights:
            st.markdown(f"- **{hi.title}**: {hi.body}")
    else:
        st.info("Complete some pledges to unlock habit insights!")

# =====================================================================
# TAB: Habit Profiles
# =====================================================================
with tab_habits:
    st.subheader("🧠 Habit Formation Profiles")

    profiles = build_habit_profiles(user_id)

    if not profiles:
        st.info("No habit profiles yet. Enrol in pledges to start tracking habit formation!")
    else:
        # Stage overview
        stage_order = ["exploration", "building", "reinforcing", "consolidating", "automatic", "dormant"]
        stage_emojis = {
            "exploration": "🔍",
            "building": "🔨",
            "reinforcing": "💪",
            "consolidating": "🏗️",
            "automatic": "⚡",
            "dormant": "😴",
        }
        stage_colors = {
            "exploration": "#6b7280",
            "building": "#3b82f6",
            "reinforcing": "#f59e0b",
            "consolidating": "#a855f7",
            "automatic": "#22c55e",
            "dormant": "#ef4444",
        }

        # Stage summary bar
        stage_counts = {}
        for s in stage_order:
            stage_counts[s] = sum(1 for p in profiles if p.stage == s)

        st.markdown("#### 📊 Stage Distribution")
        cols = st.columns(len(stage_order))
        for i, (stage, count) in enumerate(stage_counts.items()):
            with cols[i]:
                emoji = stage_emojis.get(stage, "❓")
                color = stage_colors.get(stage, "#6b7280")
                st.markdown(f"""
                <div style='text-align:center;padding:12px;border-radius:12px;
                            border:1px solid {color}30;background:{color}08;'>
                    <div style='font-size:1.5rem;'>{emoji}</div>
                    <div style='font-size:1.4rem;font-weight:800;color:{color};'>{count}</div>
                    <div style='font-size:0.75rem;color:#6b7280;'>{stage.title()}</div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # Individual profiles
        for p in sorted(profiles, key=lambda x: x.habit_strength):
            stage_color = stage_colors.get(p.stage, "#6b7280")
            stage_emoji = stage_emojis.get(p.stage, "❓")

            st.markdown(f"""
            <div style='border:1px solid {stage_color}30;border-radius:14px;padding:18px;
                        background:linear-gradient(135deg,{stage_color}08,#fff);margin-bottom:12px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <div>
                        <span style='font-size:0.8rem;color:{stage_color};font-weight:600;'>
                            {stage_emoji} {p.stage.replace('_', ' ').title()}
                        </span>
                        <h4 style='margin:4px 0;'>{p.template_title}</h4>
                        <p style='color:#6b7280;margin:0;font-size:0.85rem;'>
                            {PLEDGE_CATEGORIES.get(p.category, {}).get('label', p.category)}
                            · Week {p.weeks_enrolled}/{HABIT_FORMATION_WEEKS}
                        </p>
                    </div>
                    <div style='text-align:right;'>
                        <div style='font-size:1.2rem;font-weight:800;color:{stage_color};'>
                            {p.habit_strength:.0%}
                        </div>
                        <div style='font-size:0.7rem;color:#9ca3af;'>Habit Strength</div>
                    </div>
                </div>
                <div style='margin-top:10px;'>
                    <div style='height:8px;background:#e5e7eb;border-radius:4px;overflow:hidden;'>
                        <div style='width:{p.habit_strength*100:.0f}%;height:100%;
                                    background:linear-gradient(90deg,{stage_color}80,{stage_color});
                                    border-radius:4px;'></div>
                    </div>
                </div>
                <div style='display:flex;gap:16px;margin-top:10px;font-size:0.8rem;color:#6b7280;'>
                    <span>📊 {p.completion_rate:.0f}% completion</span>
                    <span>📅 {p.total_checkins} total checkins</span>
                    <span>🔄 {p.consecutive_missed} missed weeks</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Formation progress
            progress = min(p.weeks_enrolled / HABIT_FORMATION_WEEKS, 1.0)
            st.progress(progress, text=f"Habit formation: Week {p.weeks_enrolled}/{HABIT_FORMATION_WEEKS} "
                         f"({p.completion_rate:.0f}% completion, need {HABIT_THRESHOLD_PCT:.0f}%)")

# =====================================================================
# TAB: Optimal Combos
# =====================================================================
with tab_combos:
    st.subheader("🎯 Optimal Pledge Combinations")

    strategy = st.selectbox(
        "Strategy",
        ["Balanced", "Easy Warmup", "High Impact", "Diversity", "Streak Focus", "Challenge Mode"],
        key="combo_strategy",
    )
    strategy_map = {
        "Balanced": ComboStrategy.BALANCED,
        "Easy Warmup": ComboStrategy.EASY_WARMUP,
        "High Impact": ComboStrategy.HIGH_IMPACT,
        "Diversity": ComboStrategy.DIVERSITY,
        "Streak Focus": ComboStrategy.STREAK_FOCUS,
        "Challenge Mode": ComboStrategy.CHALLENGE_MODE,
    }

    combos = suggest_optimal_combos(user_id, strategy=strategy_map[strategy], n=3)

    if not combos:
        st.info("No optimal combinations found. Try enrolling in some pledges first!")
    else:
        for combo in combos:
            st.markdown(f"""
            <div style='border:1px solid #e5e7eb;border-radius:16px;padding:20px;
                        background:linear-gradient(135deg,#f0fdf4,#fff);margin-bottom:14px;'>
                <h4 style='margin:0;'>{combo.title}</h4>
                <p style='color:#6b7280;margin:4px 0 12px;font-size:0.9rem;'>{combo.description}</p>
                <div style='display:flex;gap:20px;flex-wrap:wrap;'>
                    <div>
                        <span style='font-size:0.8rem;color:#9ca3af;'>CO₂ / week</span>
                        <div style='font-size:1.2rem;font-weight:700;color:#22c55e;'>{combo.total_weekly_co2_kg:.1f} kg</div>
                    </div>
                    <div>
                        <span style='font-size:0.8rem;color:#9ca3af;'>XP / week</span>
                        <div style='font-size:1.2rem;font-weight:700;color:#f59e0b;'>{combo.total_weekly_xp}</div>
                    </div>
                    <div>
                        <span style='font-size:0.8rem;color:#9ca3af;'>Effort</span>
                        <div style='font-size:1.2rem;font-weight:700;color:#3b82f6;'>{combo.total_effort_score:.1f}</div>
                    </div>
                    <div>
                        <span style='font-size:0.8rem;color:#9ca3af;'>Est. Completion</span>
                        <div style='font-size:1.2rem;font-weight:700;color:#a855f7;'>{combo.estimated_completion_pct:.0f}%</div>
                    </div>
                    <div>
                        <span style='font-size:0.8rem;color:#9ca3af;'>Fit Score</span>
                        <div style='font-size:1.2rem;font-weight:700;color:#06b6d4;'>{combo.fit_score:.1f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Pledge list
            for pledge in combo.pledges:
                diff_emoji = DIFFICULTY_LABELS.get(pledge["difficulty"], pledge["difficulty"])
                st.markdown(f"- **{pledge['title']}** — {diff_emoji}")

            # Enrol button
            if st.button(f"🤝 Enrol in {combo.title}", key=f"enrol_combo_{combo.combo_id}"):
                from green_pledge_tracker import create_pledge
                enrolled = 0
                for pledge in combo.pledges:
                    result = create_pledge(user_id=user_id, template_id=pledge["id"])
                    if result:
                        enrolled += 1
                if enrolled > 0:
                    st.success(f"✅ Enrolled in {enrolled} pledge(s) from {combo.title}!")
                    st.rerun()
                else:
                    st.warning("Some pledges could not be enrolled (maybe already active).")

            st.divider()

# =====================================================================
# TAB: Weekly Planner
# =====================================================================
with tab_planner:
    st.subheader("📋 Weekly Pledge Planner")

    planner = generate_weekly_plan(user_id)

    if not planner.pledges:
        st.info("No pledges to plan. Start by enrolling in some pledges!")
    else:
        st.caption(f"Plan for week: **{planner.week_start}** → **{current_week_end()}**")

        # Summary
        c1, c2, c3 = st.columns(3)
        c1.metric("🌍 Total CO₂", f"{planner.total_co2_kg:.1f} kg/wk")
        c2.metric("⭐ Total XP", f"{planner.total_xp}/wk")
        c3.metric("📋 Active Pledges", len(planner.pledges))

        # Pledge cards
        st.markdown("#### 📋 This Week's Pledges")
        for p in planner.pledges:
            stage = p.get("habit_stage", "active")
            stage_colors = {
                "new": "#3b82f6",
                "exploration": "#6b7280",
                "building": "#3b82f6",
                "reinforcing": "#f59e0b",
                "consolidating": "#a855f7",
                "automatic": "#22c55e",
                "dormant": "#ef4444",
                "dormant_recovery": "#f59e0b",
            }
            color = stage_colors.get(stage, "#6b7280")
            diff_emoji = DIFFICULTY_LABELS.get(p["difficulty"], p["difficulty"])

            st.markdown(f"""
            <div style='border:1px solid {color}30;border-radius:12px;padding:14px;
                        background:linear-gradient(135deg,{color}08,#fff);margin-bottom:8px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <div>
                        <span style='font-size:0.75rem;color:{color};font-weight:600;'>
                            {stage.replace('_', ' ').title()}
                        </span>
                        <h4 style='margin:2px 0;'>{p['title']}</h4>
                        <p style='color:#6b7280;margin:0;font-size:0.82rem;'>
                            {PLEDGE_CATEGORIES.get(p['category'], {}).get('label', p['category'])}
                            · {diff_emoji}
                            · {p['weekly_co2_kg']:.1f} kg CO₂
                            · {p['xp_reward']} XP
                        </p>
                    </div>
                    <div style='text-align:right;'>
                        <div style='font-size:1rem;font-weight:700;color:{color};'>
                            {p.get('habit_strength', 0):.0%}
                        </div>
                        <div style='font-size:0.65rem;color:#9ca3af;'>Strength</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Daily focus
        if planner.daily_focus:
            st.divider()
            st.markdown("#### 📅 Daily Focus")
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_cols = st.columns(7)
            for i, day in enumerate(days):
                with day_cols[i]:
                    focus = planner.daily_focus.get(day, "")
                    day_abbr = day[:3]
                    st.markdown(f"""
                    <div style='text-align:center;padding:10px;border-radius:10px;
                                border:1px solid #e5e7eb;background:#f9fafb;min-height:80px;'>
                        <div style='font-weight:700;font-size:0.85rem;'>{day_abbr}</div>
                        <div style='font-size:0.7rem;color:#6b7280;margin-top:4px;'>{focus}</div>
                    </div>
                    """, unsafe_allow_html=True)

        # Notes
        if planner.notes:
            st.divider()
            st.markdown("#### 📝 Notes")
            for note in planner.notes:
                st.markdown(f"- 💡 {note}")

        # Difficulty mix
        if planner.difficulty_mix:
            st.divider()
            st.markdown("#### ⚖️ Difficulty Mix")
            fig = go.Figure(data=[
                go.Pie(
                    labels=list(planner.difficulty_mix.keys()),
                    values=list(planner.difficulty_mix.values()),
                    hole=0.4,
                    marker=dict(colors=["#22c55e", "#f59e0b", "#ef4444"]),
                )
            ])
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

# =====================================================================
# TAB: Difficulty
# =====================================================================
with tab_difficulty:
    st.subheader("⬆️ Difficulty Ramp-up")

    rec = recommend_difficulty(user_id)

    # Current level
    current_label = DIFFICULTY_LABELS.get(rec.current_avg, rec.current_avg)
    recommended_label = DIFFICULTY_LABELS.get(rec.recommended, rec.recommended)

    st.markdown(f"""
    <div style='border:1px solid #e0e7ff;border-radius:16px;padding:24px;
                background:linear-gradient(135deg,#eef2ff,#fff);'>
        <div style='display:flex;gap:40px;align-items:center;'>
            <div style='text-align:center;'>
                <div style='font-size:0.8rem;color:#9ca3af;'>Current Level</div>
                <div style='font-size:1.8rem;font-weight:800;'>{current_label}</div>
            </div>
            <div style='font-size:2rem;color:#94a3b8;'>→</div>
            <div style='text-align:center;'>
                <div style='font-size:0.8rem;color:#9ca3af;'>Recommended</div>
                <div style='font-size:1.8rem;font-weight:800;'>{recommended_label}</div>
            </div>
        </div>
        <p style='color:#6b7280;margin:12px 0 0;font-size:0.9rem;'>{rec.reason}</p>
    </div>
    """, unsafe_allow_html=True)

    if rec.ready:
        st.success(f"🎯 You're ready to try **{recommended_label}** pledges!")
        st.markdown("Head to **Browse Pledges** and filter by the new difficulty level.")
    else:
        weeks_needed = max(0, 4 - rec.weeks_at_current)
        st.info(f"Keep building consistency at your current level. "
                f"Estimated {weeks_needed} more weeks needed.")

    # Difficulty comparison chart
    st.divider()
    st.markdown("#### 📊 Difficulty Impact Comparison")
    diff_data = pd.DataFrame([
        {"Difficulty": "🟢 Easy", "CO₂ Savings": 1.5, "XP Reward": 25, "Effort": 1.0},
        {"Difficulty": "🟡 Medium", "CO₂ Savings": 5.0, "XP Reward": 55, "Effort": 2.0},
        {"Difficulty": "🔴 Hard", "CO₂ Savings": 12.0, "XP Reward": 100, "Effort": 3.5},
    ])

    fig = go.Figure()
    fig.add_trace(go.Bar(name="CO₂ Savings", x=diff_data["Difficulty"], y=diff_data["CO₂ Savings"],
                         marker_color="#22c55e"))
    fig.add_trace(go.Bar(name="XP Reward", x=diff_data["Difficulty"], y=diff_data["XP Reward"],
                         marker_color="#f59e0b"))
    fig.update_layout(barmode="group", height=300, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)

# =====================================================================
# TAB: Streak Guard
# =====================================================================
with tab_streak:
    st.subheader("🔥 Streak Protection")

    protection = get_streak_protection(user_id)
    stats = get_user_pledge_stats(user_id)

    # Streak status
    streak_color = "#22c55e" if not protection.streak_at_risk else "#ef4444"
    st.markdown(f"""
    <div style='border:2px solid {streak_color}40;border-radius:16px;padding:24px;
                background:linear-gradient(135deg,{streak_color}08,#fff);text-align:center;'>
        <div style='font-size:3rem;'>{'🔥' if not protection.streak_at_risk else '⚠️'}</div>
        <h2 style='margin:4px 0;color:{streak_color};'>
            {stats.current_streak} Week{'s' if stats.current_streak != 1 else ''} Streak
        </h2>
        <p style='color:#6b7280;margin:0;'>
            {'Your streak is active! Keep it going!' if not protection.streak_at_risk else
             'Your streak is at risk! Use protection or check in this week.'}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Protection status
    c1, c2, c3 = st.columns(3)
    c1.metric("🛡️ Extensions Left", protection.extensions_remaining)
    c2.metric("📊 Best Streak", f"{stats.best_streak} weeks")
    c3.metric("📅 Weeks Until Break", protection.weeks_until_break)

    # Use protection
    if protection.streak_at_risk and protection.extensions_remaining > 0:
        st.divider()
        st.warning("⚠️ Your streak is at risk! You can use a streak protection extension.")
        if st.button("🛡️ Use Streak Protection", type="primary"):
            if use_streak_protection(user_id):
                st.success("✅ Streak protection used! Your streak is saved for this week.")
                st.rerun()
            else:
                st.error("Could not use protection.")

    # Streak history
    st.divider()
    st.markdown("#### 📈 Streak Milestones")
    milestones = [
        (3, "⚡ 3-Week Warrior", "#3b82f6"),
        (6, "🌟 6-Week Champion", "#f59e0b"),
        (12, "👑 12-Week Legend", "#a855f7"),
        (24, "🏆 24-Week Master", "#22c55e"),
        (52, "🌍 52-Week Eco Hero", "#ef4444"),
    ]

    for weeks, label, color in milestones:
        achieved = stats.best_streak >= weeks
        icon = "✅" if achieved else "🔒"
        opacity = "1.0" if achieved else "0.4"
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:12px;padding:8px 0;
                    opacity:{opacity};'>
            <span style='font-size:1.2rem;'>{icon}</span>
            <span style='font-weight:600;'>{label}</span>
            <span style='color:#6b7280;font-size:0.85rem;'>{weeks} weeks</span>
        </div>
        """, unsafe_allow_html=True)

# =====================================================================
# TAB: Settings
# =====================================================================
with tab_settings:
    st.subheader("⚙️ Schedule Preferences")

    prefs = get_schedule_preferences(user_id)

    with st.form("prefs_form"):
        preferred_slot = st.selectbox(
            "Preferred Time Slot",
            ["Morning", "Afternoon", "Evening", "Anytime"],
            index=["morning", "afternoon", "evening", "anytime"].index(prefs["preferred_slot"]),
        )
        max_active = st.slider(
            "Max Active Pledges",
            min_value=1,
            max_value=5,
            value=prefs["max_active_pledges"],
        )
        prefer_variety = st.checkbox("Prefer variety across categories", value=prefs["prefer_variety"])
        difficulty_pref = st.selectbox(
            "Difficulty Preference",
            ["Auto", "Easy", "Medium", "Hard"],
            index=["auto", "easy", "medium", "hard"].index(prefs["difficulty_preference"]),
        )

        if st.form_submit_button("💾 Save Preferences"):
            save_schedule_preferences(
                user_id=user_id,
                preferred_slot=preferred_slot.lower(),
                max_active_pledges=max_active,
                prefer_variety=prefer_variety,
                difficulty_preference=difficulty_pref.lower(),
            )
            st.success("Preferences saved!")
            st.rerun()

    st.divider()
    st.markdown("#### 📊 Current Status")
    stats = get_user_pledge_stats(user_id)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌱 Level", stats.level)
    c2.metric("🔥 Streak", f"{stats.current_streak} wks")
    c3.metric("🌍 CO₂ Saved", f"{stats.total_co2_saved_kg:.1f} kg")
    c4.metric("⭐ XP", stats.total_xp_earned)
