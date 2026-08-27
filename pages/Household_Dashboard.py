"""Streamlit page for the Household Sustainability Management System."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

import src.lifestyle.household
from src.lifestyle.household_activities import (
    log_activity, get_activities, delete_activity, 
    VALID_CATEGORIES, init_activities_db
)
from src.lifestyle.household_goals import (
    create_goal, get_goals, update_goal_progress, 
    update_goal_status, VALID_METRICS, init_goals_db, check_overdue_goals
)
from src.lifestyle.household_metrics import get_household_analytics_summary
from src.lifestyle.household_budgeting import (
    init_budgeting_db, set_budget, get_budgets, evaluate_budgets, 
    deactivate_budget, check_and_generate_alerts, get_unread_alerts, mark_alerts_read, VALID_BUDGET_PERIODS
)
from src.lifestyle.household_gamification import (
    init_household_gamification_db, get_badges, get_challenges, 
    create_challenge, complete_challenge, _get_household_xp
)
from src.lifestyle.household_recommendations import generate_household_recommendations

def render_household_dashboard():
    st.set_page_config(page_title="Household Sustainability", page_icon="🏡", layout="wide")
    
    st.title("🏡 Household Sustainability Management")
    st.markdown("Manage your shared household footprint, track individual vs. shared activities, set collective goals, enforce budgets, and earn team rewards!")
    
    # Initialize missing tables lazyly
    if 'hh_db_initialized' not in st.session_state:
        src.lifestyle.household.init_household_db()
        init_activities_db()
        init_goals_db()
        init_budgeting_db()
        init_household_gamification_db()
        st.session_state.hh_db_initialized = True
        
    user_id = st.session_state.get("user_id", 1)  # Fallback to 1 for testing
    
    # Check if user has a household
    user_households = src.lifestyle.household.get_households_for_user(user_id)
    
    if not user_households:
        render_no_household_view(user_id)
        return
        
    hh = user_households[0]
    
    # Run background checks
    check_overdue_goals(hh['id'])
    check_and_generate_alerts(hh['id'])
    
    # Sidebar
    st.sidebar.markdown(f"### 🏠 Active Household:\n**{hh['name']}**")
    st.sidebar.markdown(f"*(Region: {hh['region']})*")
    
    xp_data = _get_household_xp(hh['id'])
    st.sidebar.metric("Household Level", f"Lvl {xp_data['level']}")
    st.sidebar.metric("Total Team XP", xp_data['total_xp'])
    
    unread = get_unread_alerts(hh['id'])
    if unread:
        st.sidebar.warning(f"⚠️ You have {len(unread)} unread budget alerts!")
        if st.sidebar.button("Mark All Read"):
            mark_alerts_read([a['id'] for a in unread])
            st.rerun()
    
    tabs = st.tabs([
        "📊 Dashboard Overview", 
        "📝 Log Activities", 
        "🎯 Goals & Budgets", 
        "🏆 Team Gamification",
        "👥 Members & Settings",
        "🔮 What-If Scenarios"
    ])
    
    with tabs[0]:
        render_dashboard_overview(hh['id'])
        
    with tabs[1]:
        render_log_activities(hh['id'])
        
    with tabs[2]:
        render_goals_and_budgets(hh['id'])
        
    with tabs[3]:
        render_gamification(hh['id'])
        
    with tabs[4]:
        render_members_and_settings(hh['id'])
        
    with tabs[5]:
        render_simulations(hh['id'])

def render_no_household_view(user_id: int):
    st.info("You don't belong to any household yet. Create one or join an existing one!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Create a Household")
        with st.form("create_hh_form"):
            name = st.text_input("Household Name", placeholder="e.g., The Smiths, Apartment 4B")
            region = st.selectbox("Region", ["Global", "US", "UK", "EU"])
            submit = st.form_submit_button("Create")
            if submit:
                if name.strip():
                    hh_id = src.lifestyle.household.create_household(name.strip(), user_id, region=region)
                    if hh_id:
                        st.success("Household created successfully!")
                        st.rerun()
                    else:
                        st.error("Error creating src.lifestyle.household.")
                else:
                    st.warning("Please enter a valid name.")
                    
    with col2:
        st.subheader("Join a Household")
        with st.form("join_hh_form"):
            code = st.text_input("Join Code")
            display_name = st.text_input("Your Display Name")
            submit = st.form_submit_button("Join")
            if submit:
                if code and display_name:
                    success, msg = src.lifestyle.household.join_household(code, user_id, display_name)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please fill in both fields.")

def render_dashboard_overview(household_id: int):
    st.header("Household Overview")
    
    analytics = get_household_analytics_summary(household_id)
    
    # Top KPIs
    c1, c2, c3, c4 = st.columns(4)
    score_data = analytics["score_data"]
    metrics = analytics["metrics"]
    
    c1.metric("Sustainability Score", f"{score_data['score']}/100")
    c2.metric("Total Footprint", f"{metrics['total_footprint_kg']:.1f} kg CO2e")
    c3.metric("Members", metrics["total_members"])
    c4.metric("Goals Complete", f"{metrics['goal_completion_rate']:.0f}%")
    
    if score_data.get("feedback"):
        st.info(f"💡 **Overall Status:** {score_data['feedback']}")
        
    st.markdown("---")
    
    # AI Recommendations
    st.subheader("🤖 Smart Recommendations")
    recs = generate_household_recommendations(household_id)
    for r in recs:
        st.success(r)
        
    st.markdown("---")
    
    # Charts
    col_chart1, col_chart2, col_chart3 = st.columns(3)
    
    from household_data_visualizations import create_household_radar_chart
    
    with col_chart1:
        st.subheader("Category Breakdown")
        cat_data = score_data.get("category_breakdown", {})
        if sum(cat_data.values()) > 0:
            df_cat = pd.DataFrame(list(cat_data.items()), columns=['Category', 'Footprint'])
            fig_cat = px.pie(df_cat, values='Footprint', names='Category', hole=0.4, 
                             color_discrete_sequence=px.colors.sequential.Greens_r)
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.write("No data available to show category breakdown.")
            
    with col_chart2:
        st.subheader("Member Contributions")
        mem_data = analytics["member_breakdown"]["members"]
        if analytics["member_breakdown"]["household_total"] > 0:
            mem_list = []
            for m_id, m_info in mem_data.items():
                mem_list.append({
                    "Member": m_info["name"],
                    "Individual (kg)": m_info["individual"],
                    "Shared Allocated (kg)": m_info["allocated"]
                })
            df_mem = pd.DataFrame(mem_list)
            fig_mem = go.Figure(data=[
                go.Bar(name='Individual', x=df_mem['Member'], y=df_mem['Individual (kg)']),
                go.Bar(name='Shared Allocated', x=df_mem['Member'], y=df_mem['Shared Allocated (kg)'])
            ])
            fig_mem.update_layout(barmode='stack', colorway=['#2ca02c', '#98df8a'])
            st.plotly_chart(fig_mem, use_container_width=True)
        else:
            st.write("No data available to show member contributions.")
            
    with col_chart3:
        st.subheader("Benchmark Radar")
        fig_radar = create_household_radar_chart(household_id)
        st.plotly_chart(fig_radar, use_container_width=True)

def render_log_activities(household_id: int):
    st.header("Activity Log")
    
    members = src.lifestyle.household.get_members(household_id)
    member_opts = {"Shared Household Activity (All Members)": None}
    for m in members:
        member_opts[f"{m['name']} (Individual)"] = m['id']
        
    with st.expander("➕ Log New Activity", expanded=True):
        with st.form("log_activity_form"):
            c1, c2 = st.columns(2)
            category = c1.selectbox("Category", VALID_CATEGORIES)
            member_sel = c2.selectbox("Who did this?", list(member_opts.keys()))
            
            c3, c4, c5 = st.columns(3)
            value = c3.number_input("Value/Amount", min_value=0.0, step=1.0)
            unit = c4.text_input("Unit (e.g., kWh, miles, kg)")
            impact = c5.number_input("Est. CO2e Impact (kg)", min_value=0.0, step=0.1)
            
            activity_date = st.date_input("Date")
            desc = st.text_input("Description (Optional)")
            
            submit = st.form_submit_button("Log Activity")
            if submit:
                if value >= 0 and unit.strip() and impact >= 0:
                    act_id = log_activity(
                        household_id=household_id,
                        category=category,
                        value=value,
                        unit=unit,
                        impact_kg_co2=impact,
                        activity_date=activity_date.strftime("%Y-%m-%d"),
                        description=desc,
                        member_id=member_opts[member_sel]
                    )
                    if act_id:
                        st.success("Activity logged successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to log activity.")
                else:
                    st.warning("Please provide valid inputs for value, unit, and impact.")
                    
    st.markdown("### Recent Activities")
    activities = get_activities(household_id, limit=10)
    
    if not activities:
        st.info("No activities logged yet.")
    else:
        for act in activities:
            with st.container():
                ac1, ac2, ac3 = st.columns([3, 1, 1])
                member_label = act['member_name'] if act['member_id'] else "Shared (Household)"
                ac1.markdown(f"**{act['category']}**: {act['value']} {act['unit']} - *{member_label}*")
                ac1.caption(f"{act['activity_date']} | {act['description']}")
                ac2.markdown(f"**{act['impact_kg_co2']} kg CO2e**")
                if ac3.button("🗑️ Delete", key=f"del_act_{act['id']}"):
                    delete_activity(act['id'])
                    st.rerun()
            st.divider()

def render_goals_and_budgets(household_id: int):
    st.header("Goals & Budgets")
    
    t1, t2 = st.tabs(["🎯 Goals", "💸 Carbon Budgets"])
    
    with t1:
        with st.expander("➕ Set New Goal"):
            with st.form("new_goal_form"):
                title = st.text_input("Goal Title (e.g., Cut power by 10%)")
                c1, c2 = st.columns(2)
                metric = c1.selectbox("Metric Category", VALID_METRICS)
                unit = c2.text_input("Unit (e.g., kWh, %)")
                
                c3, c4 = st.columns(2)
                target = c3.number_input("Target Value", min_value=0.1)
                deadline = c4.date_input("Deadline")
                
                if st.form_submit_button("Create Goal"):
                    if title.strip() and unit.strip():
                        g_id = create_goal(household_id, title, metric, target, unit, deadline=deadline.strftime("%Y-%m-%d"))
                        if g_id:
                            st.success("Goal created!")
                            st.rerun()
                    else:
                        st.warning("Title and Unit are required.")
                        
        st.markdown("### Active Goals")
        active_goals = get_goals(household_id, status="active")
        if not active_goals:
            st.info("No active goals right now.")
        else:
            for g in active_goals:
                st.markdown(f"#### {g['title']}")
                st.caption(f"Category: {g['metric'].title()} | Deadline: {g['deadline']}")
                
                progress = min(1.0, g['current_value'] / g['target_value'] if g['target_value'] > 0 else 0)
                st.progress(progress)
                st.write(f"**{g['current_value']}** / {g['target_value']} {g['unit']} ({progress*100:.1f}%)")
                
                with st.form(f"update_g_{g['id']}"):
                    c1, c2 = st.columns([3, 1])
                    new_val = c1.number_input("Update Current Value", value=float(g['current_value']), step=1.0)
                    if c2.form_submit_button("Update"):
                        update_goal_progress(g['id'], new_val)
                        st.rerun()
                st.divider()
                
    with t2:
        with st.expander("➕ Create Budget Limit"):
            with st.form("new_budget_form"):
                c1, c2 = st.columns(2)
                b_cat = c1.selectbox("Category", ["Overall"] + VALID_CATEGORIES)
                b_period = c2.selectbox("Period", VALID_BUDGET_PERIODS)
                
                c3, c4 = st.columns(2)
                b_limit = c3.number_input("Limit Value", min_value=1.0)
                b_unit = c4.text_input("Unit", value="kg CO2e")
                
                if st.form_submit_button("Set Budget"):
                    set_budget(household_id, b_cat, b_limit, b_unit, b_period)
                    st.success("Budget updated!")
                    st.rerun()
                    
        st.markdown("### Budget Tracking")
        evals = evaluate_budgets(household_id)
        if not evals:
            st.info("No active budgets.")
        else:
            for b_id, data in evals.items():
                b = data['budget']
                stat_color = "red" if data['status'] == 'exceeded' else "orange" if data['status'] == 'warning' else "green"
                
                st.markdown(f"#### {b['category']} ({b['period'].title()}) - <span style='color:{stat_color}'>{data['status'].upper()}</span>", unsafe_allow_html=True)
                st.caption(f"Valid: {data['start_date']} to {data['end_date']}")
                
                st.progress(min(1.0, data['percentage']/100))
                st.write(f"Spent: {data['spent']:.1f} / {b['limit_value']} {b['unit']} ({data['percentage']:.1f}%)")
                
                if st.button("Deactivate", key=f"deact_b_{b_id}"):
                    deactivate_budget(b_id)
                    st.rerun()
                st.divider()

def render_gamification(household_id: int):
    st.header("Team Gamification")
    
    t1, t2 = st.tabs(["🏆 Badges", "⚔️ Challenges"])
    
    with t1:
        badges = get_badges(household_id)
        if not badges:
            st.info("Your household hasn't earned any badges yet. Complete challenges to unlock them!")
        else:
            cols = st.columns(4)
            for i, badge in enumerate(badges):
                with cols[i % 4]:
                    st.markdown(f"<h1 style='text-align:center;'>{badge['icon']}</h1>", unsafe_allow_html=True)
                    st.markdown(f"<h4 style='text-align:center;'>{badge['badge_name']}</h4>", unsafe_allow_html=True)
                    st.caption(f"<div style='text-align:center;'>{badge['description']}<br><br><i>{badge['earned_date']}</i></div>", unsafe_allow_html=True)
                    
    with t2:
        with st.expander("➕ Create Team Challenge"):
            with st.form("new_challenge"):
                title = st.text_input("Title")
                desc = st.text_area("Description")
                xp = st.number_input("XP Reward", min_value=10, step=10)
                if st.form_submit_button("Launch Challenge"):
                    create_challenge(household_id, title, desc, int(xp))
                    st.success("Challenge launched!")
                    st.rerun()
                    
        active_ch = get_challenges(household_id, status="active")
        if not active_ch:
            st.info("No active challenges.")
        else:
            for ch in active_ch:
                with st.container():
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"**{ch['title']}** (🎁 {ch['xp_reward']} XP)")
                    c1.write(ch['description'])
                    if c2.button("Mark Completed", key=f"ch_{ch['id']}"):
                        complete_challenge(ch['id'])
                        st.balloons()
                        st.success(f"Challenge completed! Gained {ch['xp_reward']} XP.")
                        st.rerun()
                st.divider()

def render_members_and_settings(household_id: int):
    st.header("Household Members")
    
    hh = src.lifestyle.household.get_household(household_id)
    members = src.lifestyle.household.get_members(household_id)
    
    # Settings & Invite
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Household Code:** `{hh['join_code']}`\n\nShare this code with others to let them join.")
    with c2:
        st.markdown("**Allocation Method:**")
        st.write(hh['allocation_method'].title())
        
    st.markdown("---")
    
    st.subheader("Manage Members")
    for m in members:
        with st.container():
            mc1, mc2, mc3 = st.columns([2, 1, 1])
            mc1.markdown(f"**{m['name']}** ({m['role']})")
            mc1.caption(f"Weight: {m['weight']}")
            
            with mc2.popover("Edit"):
                new_role = st.selectbox("Role", ["Adult", "Child", "Guest"], index=["Adult", "Child", "Guest"].index(m['role']), key=f"r_{m['id']}")
                new_weight = st.number_input("Weight", value=float(m['weight']), step=0.1, key=f"w_{m['id']}")
                if st.button("Save", key=f"s_{m['id']}"):
                    src.lifestyle.household.update_member(m['id'], weight=new_weight, role=new_role)
                    st.rerun()
                    
            if mc3.button("Remove", key=f"rm_{m['id']}"):
                if len(members) <= 1:
                    st.error("Cannot remove the last member of the src.lifestyle.household.")
                else:
                    src.lifestyle.household.remove_member(m['id'])
                    st.rerun()
        st.divider()

if __name__ == "__main__":
    render_household_dashboard()



def render_simulations(household_id: int):
    st.header("What-If Sustainability Scenarios")
    st.markdown("Explore how major lifestyle changes would project onto your household's baseline carbon footprint.")
    
    from household_scenario_modeling import simulate_scenarios, calculate_payback_period, recommend_top_scenario
    
    scenarios = simulate_scenarios(household_id)
    
    if not scenarios:
        st.info("We need more activity data logged to run meaningful simulations. Start by logging some activities!")
        return
        
    top_scenario = recommend_top_scenario(household_id)
    if top_scenario:
        st.success(f"🌟 **Top Recommendation:** {top_scenario['title']} (reduces footprint by {top_scenario['reduction_kg']:.1f} kg CO2e)")
        
    st.markdown("---")
    
    for sc in scenarios:
        with st.container():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"### {sc['title']}")
            c1.write(sc['description'])
            
            payback = calculate_payback_period(sc['id'], household_id)
            payback_str = f"{payback:.1f} yrs" if payback and payback != float('inf') else "N/A"
            
            c2.metric("Est. Upfront Cost", sc['cost_estimate'])
            c2.metric("Financial Carbon Payback", payback_str)
            
            c3.metric("CO2e Reduction", f"-{sc['reduction_kg']:.1f} kg")
            c3.metric("% of Baseline", f"-{sc['reduction_pct']:.1f}%")
            
        st.divider()
