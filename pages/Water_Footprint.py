"""Water Footprint Tracker & Daily Activity Estimator Page for EcoBuddy AI."""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.environment.water import (
    calculate_water_footprint,
    validate_water_inputs,
    get_activity_categories,
    calculate_water_efficiency_score,
    calculate_potential_water_savings,
    liters_to_gallons,
    GLOBAL_WATER_AVERAGE_LITERS,
)
from src.ai.recommendations import generate_water_recommendations
from src.core.database import save_water_assessment, get_water_assessments
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown("<div class='section-header'>💧 Measure Your Water Footprint</div>", unsafe_allow_html=True)
st.markdown(
    "Estimate your total water consumption across common daily activities, discover your activity-wise breakdown, "
    "simulate potential savings, and explore tailored conservation advice."
)

st.markdown("---")

tab_measure, tab_analysis, tab_advice, tab_history = st.tabs([
    "🚰 Measure Consumption",
    "📊 Breakdown & Analytics",
    "💡 Conservation Advice & Simulator",
    "📈 Usage History",
])

with tab_measure:
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        unit_pref = st.radio(
            "Display Units",
            ["Liters (L)", "US Gallons (gal)"],
            horizontal=True,
            index=0,
            key="water_unit_pref",
        )
    with col_u2:
        household_size = st.number_input(
            "Household Size",
            min_value=1,
            max_value=20,
            value=1,
            step=1,
            help="Used to calculate your per-person daily average footprint."
        )
    is_gallons = "Gallon" in unit_pref

    st.markdown("### 🚿 1. Personal Hygiene Activities")
    col_hyg1, col_hyg2 = st.columns(2)
    with col_hyg1:
        shower_mins = st.number_input(
            "Shower Duration (minutes/day)",
            min_value=0.0,
            max_value=180.0,
            value=10.0,
            step=1.0,
            help="Average time spent showering per day.",
        )
        baths_week = st.number_input(
            "Full Baths (times/week)",
            min_value=0,
            max_value=21,
            value=0,
            step=1,
            help="A standard bathtub holds ~120-150 liters.",
        )
    with col_hyg2:
        teeth_mins = st.number_input(
            "Sink & Handwashing (minutes/day)",
            min_value=0.0,
            max_value=30.0,
            value=2.0,
            step=0.5,
            help="Time spent running water for teeth brushing, shaving, and washing hands.",
        )
        toilet_flushes = st.number_input(
            "Toilet Flushes (per day)",
            min_value=1,
            max_value=30,
            value=5,
            step=1,
            help="Standard toilets use 9L per flush, while dual-flush/low-flow use 4.5L.",
        )

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        tap_running = st.checkbox(
            "Leave tap running while brushing/soaping",
            value=False,
            help="Running taps consume ~8L/min vs ~2L/min when shut off between rinses.",
        )
    with col_opt2:
        low_flow = st.checkbox(
            "Equipped with Water-Saving / Low-Flow Fixtures",
            value=False,
            help="Low-flow showerheads, dual-flush toilets, and faucet aerators.",
        )

    st.markdown("---")
    st.markdown("### 🍽️ 2. Kitchen, Laundry & Domestic Chores")
    col_dom1, col_dom2 = st.columns(2)
    with col_dom1:
        laundry_loads = st.number_input(
            "Laundry Loads (per week)",
            min_value=0,
            max_value=50,
            value=2,
            step=1,
        )
        dishwasher_runs = st.number_input(
            "Dishwasher Runs (per week)",
            min_value=0,
            max_value=50,
            value=3,
            step=1,
        )
    with col_dom2:
        cooking_liters = st.number_input(
            "Cooking, Drinking & Kettle (Liters/day)",
            min_value=1.0,
            max_value=100.0,
            value=10.0,
            step=1.0,
        )
        cleaning_liters = st.number_input(
            "House Cleaning & Mopping (Liters/day)",
            min_value=0.0,
            max_value=50.0,
            value=5.0,
            step=1.0,
        )

    st.markdown("---")
    st.markdown("### 🌿 3. Outdoor & Diet (Virtual Water)")
    col_out1, col_out2 = st.columns(2)
    with col_out1:
        garden_mins = st.number_input(
            "Garden / Lawn Watering (minutes/week)",
            min_value=0.0,
            max_value=600.0,
            value=0.0,
            step=5.0,
        )
        car_washes = st.number_input(
            "Car Washes (times/month)",
            min_value=0,
            max_value=30,
            value=1,
            step=1,
        )
    with col_out2:
        diet = st.selectbox(
            "Dietary Habit (Virtual Water)",
            ["Vegan", "Vegetarian", "Omnivore", "Heavy Meat"],
            index=2,
            help="Diet accounts for over 70% of total embedded water footprint due to agricultural feed.",
        )

    st.markdown("---")
    calculate_btn = st.button("💧 Estimate Full Water Footprint", use_container_width=True, type="primary")

    if calculate_btn:
        warnings = validate_water_inputs(
            shower_mins=shower_mins,
            laundry_loads=laundry_loads,
            dishwasher_runs=dishwasher_runs,
            garden_mins=garden_mins,
            baths_per_week=baths_week,
            teeth_mins=teeth_mins,
            toilet_flushes=toilet_flushes,
            car_washes_month=car_washes,
        )
        for w in warnings:
            st.warning(w)

        with st.spinner("Calculating comprehensive daily water footprint..."):
            total_daily, contributors = calculate_water_footprint(
                shower_mins_per_day=shower_mins,
                laundry_loads_per_week=laundry_loads,
                dishwasher_runs_per_week=dishwasher_runs,
                garden_mins_per_week=garden_mins,
                diet=diet,
                baths_per_week=baths_week,
                teeth_handwash_mins_per_day=teeth_mins,
                tap_running_while_brushing=tap_running,
                toilet_flushes_per_day=toilet_flushes,
                low_flow_fixtures=low_flow,
                cooking_drinking_liters_per_day=cooking_liters,
                car_washes_per_month=car_washes,
                cleaning_liters_per_day=cleaning_liters,
            )

            insight, recommendations = generate_water_recommendations(contributors, total_daily, diet)
            categories = get_activity_categories(contributors)
            score_data = calculate_water_efficiency_score(total_daily)

            inputs_record = {
                "shower_mins": shower_mins,
                "baths_per_week": baths_week,
                "teeth_mins": teeth_mins,
                "toilet_flushes": toilet_flushes,
                "tap_running_while_brushing": tap_running,
                "low_flow_fixtures": low_flow,
                "laundry_loads": laundry_loads,
                "dishwasher_runs": dishwasher_runs,
                "garden_mins": garden_mins,
                "diet": diet,
                "car_washes": car_washes,
                "household_size": household_size,
            }

            savings_opps = calculate_potential_water_savings(inputs_record)

            save_water_assessment(
                user_id,
                shower_mins,
                laundry_loads,
                dishwasher_runs,
                garden_mins,
                diet,
                total_daily,
            )

            st.session_state.water_analysis = {
                "total_daily": total_daily,
                "contributors": contributors,
                "categories": categories,
                "score_data": score_data,
                "insight": insight,
                "recommendations": recommendations,
                "savings_opps": savings_opps,
                "inputs": inputs_record,
            }
            st.success("✅ Water footprint measured and saved to your history!")

with tab_analysis:
    if "water_analysis" not in st.session_state:
        st.info("Please fill in your daily activities and click **Estimate Full Water Footprint** in the first tab.")
    else:
        data = st.session_state.water_analysis
        total_l = data["total_daily"]
        total_disp = liters_to_gallons(total_l) if is_gallons else total_l
        unit_lbl = "Gallons/day" if is_gallons else "Liters/day"

        score = data["score_data"]
        h_size = data["inputs"].get("household_size", 1)
        per_person = total_disp / h_size if h_size > 0 else total_disp

        st.markdown(
            f"""
            <div style="background-color: #1e293b; padding: 20px; border-radius: 12px; border-left: 6px solid {score['color']}; margin-bottom: 20px;">
                <h3 style="margin: 0; color: {score['color']};">Efficiency Grade: {score['grade']} ({score['score']}/100) — {score['status']}</h3>
                <p style="margin: 5px 0 0 0; color: #cbd5e1;">Your daily water consumption is <strong>{score['comparison_text']}</strong>.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("💧 Daily Total", f"{total_disp:.0f} {unit_lbl}")
        with c2:
            st.metric("👤 Per Person (Daily)", f"{per_person:.0f} {unit_lbl}")
        with c3:
            weekly_disp = total_disp * 7
            st.metric("📅 Weekly Total", f"{weekly_disp:,.0f} {unit_lbl.replace('/day', '/wk')}")
        with c4:
            annual_disp = total_disp * 365
            st.metric("🌍 Annual Total", f"{annual_disp:,.0f} {unit_lbl.replace('/day', '/yr')}")

        st.markdown("---")
        st.markdown("### 📊 Activity-Wise Breakdown")

        col_pie, col_cat = st.columns(2)
        with col_pie:
            df_contrib = pd.DataFrame([
                {"Activity": k, "Volume": liters_to_gallons(v) if is_gallons else v}
                for k, v in data["contributors"].items()
            ])
            fig_pie = px.pie(
                df_contrib,
                values="Volume",
                names="Activity",
                title=f"Detailed Activity Breakdown ({unit_lbl})",
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Teal_r,
            )
            fig_pie.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_cat:
            df_cat = pd.DataFrame([
                {"Category": k, "Volume": liters_to_gallons(v) if is_gallons else v}
                for k, v in data["categories"].items()
            ])
            fig_cat = px.bar(
                df_cat,
                x="Category",
                y="Volume",
                color="Category",
                title=f"Major Category Breakdown ({unit_lbl})",
                color_discrete_sequence=px.colors.qualitative.Prism,
            )
            fig_cat.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_cat, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🌍 Global Benchmark Comparison")
        base_disp = liters_to_gallons(GLOBAL_WATER_AVERAGE_LITERS) if is_gallons else GLOBAL_WATER_AVERAGE_LITERS
        fig_bench = go.Figure(data=[
            go.Bar(name="Your Daily Footprint", x=["Consumption"], y=[total_disp], marker_color="#38bdf8"),
            go.Bar(name="Global Average (3,800 L)", x=["Consumption"], y=[base_disp], marker_color="#64748b"),
        ])
        fig_bench.update_layout(
            barmode="group",
            title=f"Comparison with Global Baseline ({unit_lbl})",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_bench, use_container_width=True)

with tab_advice:
    if "water_analysis" not in st.session_state:
        st.info("Run an assessment to view personalized conservation advice.")
    else:
        data = st.session_state.water_analysis
        st.markdown("### 💡 AI Insights & Recommendations")
        st.info(data["insight"])

        for rec in data["recommendations"]:
            st.markdown(f"- {rec}")

        st.markdown("---")
        st.markdown("### 🎯 Quantified Habit Savings Opportunities")
        savings = data.get("savings_opps", [])
        if savings:
            for s in savings:
                daily_s = liters_to_gallons(s["daily_liters_saved"]) if is_gallons else s["daily_liters_saved"]
                annual_s = liters_to_gallons(s["annual_liters_saved"]) if is_gallons else s["annual_liters_saved"]
                u = "gal" if is_gallons else "Liters"

                with st.container():
                    st.markdown(
                        f"""
                        <div style="border: 1px solid #334155; border-radius: 8px; padding: 14px; margin-bottom: 12px; background: rgba(30, 41, 59, 0.5);">
                            <h4 style="margin: 0 0 6px 0; color: #38bdf8;">✨ {s['action']} <span style="font-size: 0.85em; color: #4ade80;">(Save ~{annual_s:,.0f} {u}/year)</span></h4>
                            <p style="margin: 0 0 6px 0; color: #e2e8f0;">{s['tip']}</p>
                            <small style="color: #94a3b8;">Daily Savings: <strong>{daily_s:,.1f} {u}/day</strong> · Category: {s['category']}</small>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.success("🌟 Fantastic habits! Your activities are already highly optimized for water conservation.")

        st.markdown("---")
        st.markdown("### 🎛️ Interactive 'What-If' Savings Simulator")
        sim_mins = st.slider("Simulate reducing daily shower time by (minutes):", 0, 15, 3)
        sim_diet_days = st.slider("Simulate plant-based days per week:", 0, 7, 2)

        sim_shower_saved = sim_mins * 10.0 * 365.0
        sim_diet_saved = (sim_diet_days * 1500.0 / 7.0) * 365.0
        sim_total_saved_l = sim_shower_saved + sim_diet_saved
        sim_total_saved = liters_to_gallons(sim_total_saved_l) if is_gallons else sim_total_saved_l
        u_sim = "Gallons" if is_gallons else "Liters"

        st.metric("🎉 Potential Annual Water Saved", f"{sim_total_saved:,.0f} {u_sim} / year")

with tab_history:
    st.markdown("### 📈 Your Historical Water Assessments")
    water_history = get_water_assessments(user_id)

    if not water_history or len(water_history) == 0:
        st.info("No recorded water assessments found. Complete your first assessment to start tracking progress!")
    else:
        df_hist = pd.DataFrame(
            water_history,
            columns=[
                "id",
                "user_id",
                "shower_mins",
                "laundry_loads",
                "dishwasher_runs",
                "garden_mins",
                "diet",
                "total_liters",
                "created_at",
            ],
        )
        df_hist["created_at"] = pd.to_datetime(df_hist["created_at"])
        df_hist = df_hist.sort_values("created_at")

        if len(df_hist) >= 2:
            fig_trend = go.Figure()
            hist_y = (
                [liters_to_gallons(v) for v in df_hist["total_liters"]]
                if is_gallons
                else df_hist["total_liters"]
            )
            base_line_val = (
                liters_to_gallons(GLOBAL_WATER_AVERAGE_LITERS)
                if is_gallons
                else GLOBAL_WATER_AVERAGE_LITERS
            )

            fig_trend.add_trace(go.Scatter(
                x=df_hist["created_at"],
                y=hist_y,
                mode="lines+markers",
                name="Your Daily Footprint",
                line=dict(color="#38bdf8", width=3),
                marker=dict(size=8, color="#0284c7"),
            ))
            fig_trend.add_hline(
                y=base_line_val,
                line_dash="dash",
                line_color="#ef4444",
                annotation_text=f"Global Baseline ({base_line_val:.0f})",
            )
            fig_trend.update_layout(
                title=f"Water Footprint Over Time ({unit_lbl if 'unit_lbl' in locals() else 'Liters/day'})",
                xaxis_title="Date",
                yaxis_title="Volume per Day",
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("#### Assessment Records")
        display_df = df_hist.copy()
        if is_gallons:
            display_df["total_gallons"] = display_df["total_liters"].apply(liters_to_gallons)
        st.dataframe(display_df[["created_at", "total_liters", "diet", "shower_mins", "laundry_loads", "dishwasher_runs", "garden_mins"]], use_container_width=True)

        csv_data = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Export Water Assessment History (CSV)",
            data=csv_data,
            file_name="water_footprint_history.csv",
            mime="text/csv",
        )

# ==========================================
# CONSERVATION GOALS SECTION
# ==========================================
st.markdown("---")
st.markdown("### 🎯 Water Conservation Goals")

import sqlite3
from src.core.database import DB_NAME

def init_water_goals_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS water_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            target_liters REAL NOT NULL,
            deadline DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_active_water_goal(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT target_liters, deadline FROM water_goals WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def set_active_water_goal(user_id, target_l, deadline):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO water_goals (user_id, target_liters, deadline) VALUES (?, ?, ?)", (user_id, target_l, deadline))
    conn.commit()
    conn.close()

init_water_goals_db()

goal = get_active_water_goal(user_id)

col_g1, col_g2 = st.columns([1, 1])

with col_g1:
    st.markdown("#### Set a New Goal")
    with st.form("water_goal_form"):
        new_target = st.number_input("Target Daily Usage (Liters)", min_value=10.0, max_value=5000.0, value=200.0, step=10.0)
        import datetime
        new_deadline = st.date_input("Target Deadline", datetime.date.today() + datetime.timedelta(days=30))
        submitted = st.form_submit_button("Set Goal")
        if submitted:
            set_active_water_goal(user_id, new_target, new_deadline.isoformat())
            st.success("New conservation goal set successfully!")
            st.rerun()

with col_g2:
    st.markdown("#### Current Goal Progress")
    if goal:
        target_liters = goal[0]
        deadline = goal[1]
        
        water_history = get_water_assessments(user_id)
        current_liters = water_history[0]['total_liters'] if water_history else None
        
        if current_liters:
            st.metric("Target Usage", f"{target_liters:.0f} L/day", f"Deadline: {deadline}")
            st.metric("Current Usage", f"{current_liters:.0f} L/day")
            
            if current_liters <= target_liters:
                st.success("🎉 You are currently meeting your water conservation target!")
                st.progress(1.0)
            else:
                st.warning(f"You are {current_liters - target_liters:.0f} L above your target.")
                # Calculate progress from global avg to target
                from src.environment.water import GLOBAL_WATER_AVERAGE_LITERS
                if current_liters < GLOBAL_WATER_AVERAGE_LITERS:
                    progress = (GLOBAL_WATER_AVERAGE_LITERS - current_liters) / (GLOBAL_WATER_AVERAGE_LITERS - target_liters)
                    st.progress(min(max(progress, 0.0), 1.0))
                else:
                    st.progress(0.0)
        else:
            st.info("Log an assessment to see your progress against the goal.")
    else:
        st.info("You haven't set a water conservation goal yet.")

