import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

from database import DB_NAME, get_assessments

st.set_page_config(page_title="Sustainability Planner", page_icon="🗺️", layout="wide")

# ==========================================
# DATABASE SETUP FOR PLANNER
# ==========================================
def init_planner_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS action_roadmap (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_id TEXT NOT NULL,
            status TEXT DEFAULT 'Active',
            added_date DATE NOT NULL,
            completed_date DATE
        )
    ''')
    conn.commit()
    conn.close()

def get_user_roadmap(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('''
        SELECT id, action_id, status, added_date, completed_date
        FROM action_roadmap
        WHERE user_id = ?
    ''', conn, params=(user_id,))
    conn.close()
    return df

def update_action_status(record_id: int, new_status: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if new_status == 'Completed':
        cursor.execute("UPDATE action_roadmap SET status=?, completed_date=? WHERE id=?", (new_status, date.today().isoformat(), record_id))
    else:
        cursor.execute("UPDATE action_roadmap SET status=?, completed_date=NULL WHERE id=?", (new_status, record_id))
    conn.commit()
    conn.close()

def add_action_to_roadmap(user_id: int, action_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM action_roadmap WHERE user_id=? AND action_id=?", (user_id, action_id))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO action_roadmap (user_id, action_id, status, added_date) VALUES (?, ?, 'Active', ?)", 
                       (user_id, action_id, date.today().isoformat()))
    conn.commit()
    conn.close()

def remove_action(record_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM action_roadmap WHERE id=?", (record_id,))
    conn.commit()
    conn.close()

init_planner_db()

# ==========================================
# ACTION MASTER CATALOG
# ==========================================
ACTIONS_CATALOG = [
    {"id": "a1", "category": "Energy", "title": "Switch to LED Bulbs", "difficulty": "Easy", "impact": 50, "savings": 15, "freq": "One-time"},
    {"id": "a2", "category": "Energy", "title": "Install Programmable Thermostat", "difficulty": "Medium", "impact": 350, "savings": 100, "freq": "One-time"},
    {"id": "a3", "category": "Transportation", "title": "Bike to Work", "difficulty": "Hard", "impact": 400, "savings": 80, "freq": "Weekly"},
    {"id": "a4", "category": "Transportation", "title": "Carpool to Office", "difficulty": "Medium", "impact": 200, "savings": 40, "freq": "Weekly"},
    {"id": "a5", "category": "Food", "title": "Meatless Mondays", "difficulty": "Easy", "impact": 150, "savings": 20, "freq": "Weekly"},
    {"id": "a6", "category": "Food", "title": "Start a Compost Bin", "difficulty": "Medium", "impact": 120, "savings": 0, "freq": "Daily"},
    {"id": "a7", "category": "Water", "title": "Install Low-Flow Showerhead", "difficulty": "Medium", "impact": 80, "savings": 40, "freq": "One-time"},
    {"id": "a8", "category": "Water", "title": "Fix Leaky Faucets", "difficulty": "Easy", "impact": 30, "savings": 10, "freq": "One-time"},
    {"id": "a9", "category": "Waste", "title": "Use Reusable Shopping Bags", "difficulty": "Easy", "impact": 20, "savings": 5, "freq": "Daily"},
    {"id": "a10", "category": "Waste", "title": "Bulk Buying", "difficulty": "Medium", "impact": 90, "savings": 50, "freq": "Monthly"},
    {"id": "a11", "category": "Lifestyle", "title": "Buy Second-Hand Clothes", "difficulty": "Medium", "impact": 180, "savings": 120, "freq": "Monthly"},
    {"id": "a12", "category": "Lifestyle", "title": "Zero-Waste Bathroom", "difficulty": "Hard", "impact": 100, "savings": 30, "freq": "One-time"}
]

df_catalog = pd.DataFrame(ACTIONS_CATALOG)
# Add an "effort" score for prioritization (Easy=1, Medium=2, Hard=3)
effort_map = {"Easy": 1, "Medium": 2, "Hard": 3}
df_catalog['effort'] = df_catalog['difficulty'].map(effort_map)
df_catalog['roi'] = df_catalog['impact'] / df_catalog['effort']
df_catalog = df_catalog.sort_values('roi', ascending=False)

# ==========================================
# UI RENDERING
# ==========================================
st.title("🗺️ Personal Sustainability Planner")
st.write("Plan, track, and execute your personal sustainability roadmap.")

user_id = st.session_state.get('user_id', 1)
roadmap_df = get_user_roadmap(user_id)

# Merge roadmap with catalog
if not roadmap_df.empty:
    user_actions = pd.merge(roadmap_df, df_catalog, left_on='action_id', right_on='id', how='left')
else:
    user_actions = pd.DataFrame(columns=['id_x', 'action_id', 'status', 'added_date', 'completed_date'] + list(df_catalog.columns))

# ------------------------------------------
# OVERVIEW & PROGRESS
# ------------------------------------------
active_actions = user_actions[user_actions['status'] == 'Active']
completed_actions = user_actions[user_actions['status'] == 'Completed']

total_planned_impact = active_actions['impact'].sum() if not active_actions.empty else 0
total_achieved_impact = completed_actions['impact'].sum() if not completed_actions.empty else 0
total_financial_savings = completed_actions['savings'].sum() if not completed_actions.empty else 0

total_all = len(user_actions)
pct_complete = (len(completed_actions) / total_all) if total_all > 0 else 0.0

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Active Actions", len(active_actions))
col_m2.metric("Completed Actions", len(completed_actions))
col_m3.metric("Achieved Impact", f"{total_achieved_impact:.0f} kg CO₂/yr")
col_m4.metric("Financial Savings", f"${total_financial_savings:.0f}/yr")

st.progress(pct_complete, text=f"Roadmap Completion: {int(pct_complete*100)}%")

st.divider()

# ------------------------------------------
# NEXT BEST ACTION
# ------------------------------------------
st.subheader("🌟 Next Best Action")
# Find the highest ROI action not yet in the user's roadmap
user_action_ids = user_actions['action_id'].tolist() if not user_actions.empty else []
available_actions = df_catalog[~df_catalog['id'].isin(user_action_ids)]

if not available_actions.empty:
    nba = available_actions.iloc[0]
    with st.container(border=True):
        st.markdown(f"### {nba['title']} (Highly Recommended)")
        st.markdown(f"**Category:** {nba['category']} | **Difficulty:** {nba['difficulty']} | **Frequency:** {nba['freq']}")
        st.write(f"Estimated Impact: **{nba['impact']} kg CO₂/yr** | Savings: **${nba['savings']}/yr**")
        if st.button("➕ Add to Roadmap", key="add_nba"):
            add_action_to_roadmap(user_id, nba['id'])
            st.rerun()
else:
    st.success("You have added all available actions to your roadmap! Outstanding commitment!")

st.divider()

# ------------------------------------------
# ACTION ROADMAP (TABS)
# ------------------------------------------
st.subheader("🗺️ Your Action Roadmap")
tab_active, tab_completed, tab_discover = st.tabs(["🚀 Active Actions", "✅ Completed", "🔍 Discover New"])

with tab_active:
    if not active_actions.empty:
        for idx, row in active_actions.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"#### {row['title']}")
                    st.caption(f"{row['category']} • {row['difficulty']} • {row['impact']} kg CO₂/yr")
                with c2:
                    if st.button("Mark Complete", key=f"comp_{row['id_x']}", use_container_width=True):
                        update_action_status(row['id_x'], "Completed")
                        st.toast(f"Great job completing: {row['title']}!")
                        st.rerun()
                    if st.button("Drop", key=f"drop_{row['id_x']}", type="tertiary", use_container_width=True):
                        remove_action(row['id_x'])
                        st.rerun()
    else:
        st.info("You don't have any active actions. Check the 'Discover New' tab!")

with tab_completed:
    if not completed_actions.empty:
        for idx, row in completed_actions.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"#### {row['title']}")
                    st.caption(f"Completed on: {row['completed_date']} • Impact: {row['impact']} kg CO₂/yr")
                with c2:
                    if st.button("Reactivate", key=f"reac_{row['id_x']}", use_container_width=True):
                        update_action_status(row['id_x'], "Active")
                        st.rerun()
    else:
        st.info("No completed actions yet. You can do it!")

with tab_discover:
    col_f1, col_f2 = st.columns(2)
    cat_filter = col_f1.selectbox("Filter by Category", ["All"] + list(df_catalog['category'].unique()))
    diff_filter = col_f2.selectbox("Filter by Difficulty", ["All", "Easy", "Medium", "Hard"])
    
    filtered_df = available_actions.copy()
    if cat_filter != "All":
        filtered_df = filtered_df[filtered_df['category'] == cat_filter]
    if diff_filter != "All":
        filtered_df = filtered_df[filtered_df['difficulty'] == diff_filter]
        
    if not filtered_df.empty:
        for idx, row in filtered_df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"#### {row['title']}")
                    st.caption(f"{row['category']} • {row['difficulty']} • {row['impact']} kg CO₂/yr • Savings: ${row['savings']}/yr")
                with c2:
                    if st.button("Add", key=f"add_{row['id']}", use_container_width=True):
                        add_action_to_roadmap(user_id, row['id'])
                        st.toast("Action added to roadmap!")
                        st.rerun()
    else:
        st.write("No actions match your filters or you've added them all.")

st.divider()

# ------------------------------------------
# WHAT-IF IMPACT ANALYSIS
# ------------------------------------------
st.subheader("🔮 What-If Impact Analysis")
st.write("See how completing your active actions will reduce your baseline carbon footprint.")

assessments = get_assessments(user_id)
baseline_footprint = assessments[0][8] if assessments and len(assessments) > 0 else 8000.0  # fallback

if not active_actions.empty:
    projected_footprint = max(0, baseline_footprint - total_planned_impact)
    
    fig = go.Figure(data=[
        go.Bar(name='Current Baseline', x=['Footprint (kg CO₂/yr)'], y=[baseline_footprint], marker_color='#ef4444'),
        go.Bar(name='Projected (If Active Actions Completed)', x=['Footprint (kg CO₂/yr)'], y=[projected_footprint], marker_color='#22c55e')
    ])
    fig.update_layout(barmode='group', template="plotly_dark", margin=dict(t=30, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)
    
    st.info(f"Completing your active actions will reduce your footprint by **{total_planned_impact} kg CO₂/yr** ({(total_planned_impact/baseline_footprint*100):.1f}% reduction).")
else:
    st.info("Add some active actions to your roadmap to see your projected impact!")
