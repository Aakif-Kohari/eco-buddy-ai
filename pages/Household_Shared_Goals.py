import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.database import get_user_assessments
from src.lifestyle.household import get_households_for_user, get_members
from src.utils.goals import GOAL_ACTIVE, build_pathway, pathway_to_series
from src.utils.collaborative_goals import (
    GOAL_PENDING,
    get_goals_for_household,
    get_votes_for_goal,
    propose_goal,
    vote_on_proposal,
    get_allocations_for_goal,
    evaluate_household_progress,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🤝 Household Shared Goals</div>",
    unsafe_allow_html=True,
)
st.markdown("Set a collective footprint reduction goal and achieve it together as a household.")

households = get_households_for_user(user_id)
if not households:
    st.info("You must be part of a household to use shared goals. Go to the Household page to create or join one.")
    st.stop()

household_labels = {f"{h['name']} ({h['join_code']})": h for h in households}
selected_label = st.selectbox("Household", list(household_labels))
household = household_labels[selected_label]
household_id = household["id"]

members = get_members(household_id)

st.markdown("---")

# Fetch goals
goals = get_goals_for_household(household_id)
pending_goals = [g for g in goals if g["status"] == GOAL_PENDING]
active_goals = [g for g in goals if g["status"] == GOAL_ACTIVE]

tab_dashboard, tab_proposals = st.tabs(["Dashboard", "Proposals"])

with tab_proposals:
    st.subheader("Propose a New Goal")
    with st.form("propose_goal_form"):
        col1, col2 = st.columns(2)
        baseline_kg = col1.number_input("Household Baseline (kg CO₂/year)", min_value=1.0, value=15000.0, step=100.0)
        target_kg = col2.number_input("Target Footprint (kg CO₂/year)", min_value=1.0, value=10000.0, step=100.0)
        
        start_date = st.date_input("Start Date", value=datetime.date.today())
        target_date = st.date_input("Target Date", value=datetime.date.today() + datetime.timedelta(days=365))
        
        strategy = st.selectbox("Allocation Strategy", ["proportional", "fair-share"], help="'proportional' divides the burden by occupancy weight. 'fair-share' splits it equally.")
        
        if st.form_submit_button("Propose Goal", use_container_width=True):
            if target_kg >= baseline_kg:
                st.error("Target must be lower than the baseline.")
            elif target_date <= start_date:
                st.error("Target date must be in the future.")
            else:
                goal_id = propose_goal(household_id, user_id, baseline_kg, target_kg, start_date, target_date, strategy)
                if goal_id:
                    st.success("Goal proposed successfully!")
                    st.rerun()
                else:
                    st.error("Failed to propose goal.")
                    
    if pending_goals:
        st.subheader("Pending Proposals")
        for pg in pending_goals:
            with st.expander(f"Goal: Reduce from {pg['baseline_kg']} to {pg['target_kg']} by {pg['target_date']}"):
                votes = get_votes_for_goal(pg["id"])
                approvals = sum(1 for v in votes if v["vote"] == "approve")
                
                voters = [m for m in members if m["user_id"] is not None]
                total_eligible = len(voters) if voters else len(members)
                
                st.write(f"**Strategy**: {pg['allocation_strategy']}")
                st.write(f"**Approvals**: {approvals} / {total_eligible}")
                
                # Has user voted?
                user_vote = next((v for v in votes if v["user_id"] == user_id), None)
                if user_vote:
                    st.write(f"You voted to **{user_vote['vote']}** this proposal.")
                else:
                    col1, col2 = st.columns(2)
                    if col1.button("Approve", key=f"approve_{pg['id']}"):
                        vote_on_proposal(pg["id"], user_id, "approve")
                        st.rerun()
                    if col2.button("Reject", key=f"reject_{pg['id']}"):
                        vote_on_proposal(pg["id"], user_id, "reject")
                        st.rerun()
    else:
        st.info("No pending proposals.")


with tab_dashboard:
    if not active_goals:
        st.info("No active goals. Propose a new goal in the Proposals tab.")
    else:
        goal = active_goals[0] # Just show the most recent active goal
        
        st.subheader("Active Shared Goal")
        st.write(f"**Goal**: Reach {goal['target_kg']} kg CO₂/year by {goal['target_date']} (from {goal['baseline_kg']} kg)")
        
        # Aggregate assessments
        household_assessments = []
        for m in members:
            if m["user_id"] is not None:
                member_assessments = get_user_assessments(m["user_id"])
                # We need to map assessment format to what evaluate_progress expects
                # get_user_assessments returns Assessment objects
                for a in member_assessments:
                    household_assessments.append({
                        "date": a.created_at.date() if isinstance(a.created_at, datetime.datetime) else a.created_at,
                        "footprint": a.score,
                        "user_id": a.user_id
                    })
        
        # We need to group assessments by date and sum them for the household
        # Simple heuristic: sum assessments that occurred in the same month
        # For a real implementation we'd interpolate or fill forward
        # Let's group by date directly (assuming they assess together, or we just sum them all)
        aggregated = []
        if household_assessments:
            df = pd.DataFrame(household_assessments)
            df['date'] = pd.to_datetime(df['date']).dt.date
            # Simple group by date. For actual accuracy, missing member data on a date should be backfilled
            grouped = df.groupby('date')['footprint'].sum().reset_index()
            aggregated = grouped.to_dict('records')
            
        progress = evaluate_household_progress(goal, aggregated)
        
        st.markdown(f"**Status**: <span style='color:{progress['status_color']}'>{progress['status_label']}</span>", unsafe_allow_html=True)
        st.progress(progress["percent_complete"] / 100.0)
        
        # Trajectory chart
        pathway = build_pathway(goal)
        dates, expected_footprints = pathway_to_series(pathway)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=expected_footprints, mode='lines', name='Ideal Pathway', line=dict(dash='dash', color='blue')))
        
        if aggregated:
            actual_dates = [a['date'] for a in aggregated]
            actual_footprints = [a['footprint'] for a in aggregated]
            fig.add_trace(go.Scatter(x=actual_dates, y=actual_footprints, mode='lines+markers', name='Actual Household Footprint', line=dict(color='green')))
            
        fig.update_layout(title="Household Trajectory", xaxis_title="Date", yaxis_title="Footprint (kg CO₂)")
        st.plotly_chart(fig, use_container_width=True)
        
        # Allocations
        st.subheader("Member Allocations")
        allocations = get_allocations_for_goal(goal["id"])
        
        if allocations:
            data = []
            for m in members:
                allocated_target = allocations.get(m["id"], 0.0)
                
                # Fetch latest actual footprint for this member
                latest_actual = 0.0
                if m["user_id"] is not None:
                    ma = get_user_assessments(m["user_id"])
                    if ma:
                        latest_actual = sorted(ma, key=lambda x: x.created_at)[-1].score
                
                variance = latest_actual - allocated_target
                
                data.append({
                    "Member": m["name"],
                    "Allocated Target": allocated_target,
                    "Actual Footprint": latest_actual,
                    "Variance": variance
                })
                
            df_alloc = pd.DataFrame(data)
            st.dataframe(df_alloc, use_container_width=True)
            
            # Stacked bar chart of Actual vs Target
            fig2 = go.Figure(data=[
                go.Bar(name='Allocated Target', x=df_alloc['Member'], y=df_alloc['Allocated Target']),
                go.Bar(name='Actual Footprint', x=df_alloc['Member'], y=df_alloc['Actual Footprint'])
            ])
            fig2.update_layout(barmode='group', title="Member Contributions vs Allocations", yaxis_title="kg CO₂")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No allocations found for this goal.")
