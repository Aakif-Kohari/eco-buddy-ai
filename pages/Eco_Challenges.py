import streamlit as st
import sqlite3
import pandas as pd
import random
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go

from src.core.database import DB_NAME, add_xp

st.set_page_config(page_title="Eco Challenges", page_icon="🎯", layout="wide")

# ==========================================
# DATABASE SETUP
# ==========================================
def init_eco_challenges_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eco_challenges_tracker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            challenge_id TEXT NOT NULL,
            category TEXT,
            difficulty TEXT,
            points INTEGER,
            completed_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_completed_today(user_id: int, today_str: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT challenge_id FROM eco_challenges_tracker
        WHERE user_id = ? AND completed_date = ?
    ''', (user_id, today_str))
    completed = [row[0] for row in cursor.fetchall()]
    conn.close()
    return completed

def get_user_history(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('''
        SELECT challenge_id, category, difficulty, points, completed_date
        FROM eco_challenges_tracker
        WHERE user_id = ?
        ORDER BY completed_date DESC
    ''', conn, params=(user_id,))
    conn.close()
    return df

def complete_challenge(user_id: int, challenge: dict, today_str: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO eco_challenges_tracker (user_id, challenge_id, category, difficulty, points, completed_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, challenge['id'], challenge['category'], challenge['difficulty'], challenge['points'], today_str))
    conn.commit()
    conn.close()
    try:
        add_xp(user_id, challenge['points'])
    except Exception:
        pass

init_eco_challenges_db()

# ==========================================
# CHALLENGES REPOSITORY
# ==========================================
CHALLENGES_DB = [
    {"id": "c1", "category": "Transportation", "difficulty": "Easy", "title": "Walk or Bike", "desc": "Walk or bike for a trip under 2km instead of driving.", "points": 10, "impact": "Saves ~0.5 kg CO₂"},
    {"id": "c2", "category": "Transportation", "difficulty": "Medium", "title": "Public Transit Day", "desc": "Take public transit for your daily commute.", "points": 20, "impact": "Saves ~2.5 kg CO₂"},
    {"id": "c3", "category": "Transportation", "difficulty": "Hard", "title": "Car-free Day", "desc": "Do not use a personal car for the entire day.", "points": 50, "impact": "Saves ~5.0 kg CO₂"},
    
    {"id": "c4", "category": "Food", "difficulty": "Easy", "title": "Meatless Meal", "desc": "Eat at least one fully plant-based meal today.", "points": 10, "impact": "Saves ~1.5 kg CO₂ & 500L Water"},
    {"id": "c5", "category": "Food", "difficulty": "Medium", "title": "Local Produce", "desc": "Buy and consume only locally sourced vegetables for the day.", "points": 20, "impact": "Reduces transport emissions"},
    {"id": "c6", "category": "Food", "difficulty": "Hard", "title": "Zero Food Waste", "desc": "Finish all meals with absolutely zero food waste today.", "points": 50, "impact": "Saves ~1.0 kg CO₂"},

    {"id": "c7", "category": "Energy", "difficulty": "Easy", "title": "Lights Out", "desc": "Turn off lights in rooms you aren't using.", "points": 10, "impact": "Saves ~0.1 kWh"},
    {"id": "c8", "category": "Energy", "difficulty": "Medium", "title": "Unplug Phantom Loads", "desc": "Unplug 5 devices when not in use.", "points": 20, "impact": "Saves ~0.5 kWh"},
    {"id": "c9", "category": "Energy", "difficulty": "Hard", "title": "No AC/Heater", "desc": "Go the whole day without using central heating or AC.", "points": 50, "impact": "Saves ~3.0 kWh"},

    {"id": "c10", "category": "Water", "difficulty": "Easy", "title": "Shorter Shower", "desc": "Keep your shower under 5 minutes.", "points": 10, "impact": "Saves ~20L Water"},
    {"id": "c11", "category": "Water", "difficulty": "Medium", "title": "Cold Wash", "desc": "Wash a load of laundry using cold water only.", "points": 20, "impact": "Saves Energy & Water"},
    {"id": "c12", "category": "Water", "difficulty": "Hard", "title": "Water Tracking", "desc": "Limit total personal water usage to under 100L today.", "points": 50, "impact": "Saves ~50L Water"},

    {"id": "c13", "category": "Waste", "difficulty": "Easy", "title": "Reusable Bag", "desc": "Use a reusable bag for all shopping today.", "points": 10, "impact": "Saves plastic waste"},
    {"id": "c14", "category": "Waste", "difficulty": "Medium", "title": "No Single-Use", "desc": "Refuse all single-use plastics today (cups, straws, etc).", "points": 20, "impact": "Prevents landfill waste"},
    {"id": "c15", "category": "Waste", "difficulty": "Hard", "title": "Compost Everything", "desc": "Compost all organic waste generated today.", "points": 50, "impact": "Reduces methane emissions"}
]

# Generate daily selection based on current date
today_str = date.today().isoformat()
random.seed(today_str)
daily_challenges = []
categories = ["Transportation", "Food", "Energy", "Water", "Waste"]

for cat in categories:
    cat_challenges = [c for c in CHALLENGES_DB if c["category"] == cat]
    daily_challenges.append(random.choice(cat_challenges))

# ==========================================
# UI RENDERING
# ==========================================
user_id = st.session_state.get('user_id', 1)
df_history = get_user_history(user_id)
completed_today = get_completed_today(user_id, today_str)

st.title("🎯 Eco Challenges & Action Tracker")
st.write("Complete daily sustainability challenges to build green habits, earn points, and reduce your environmental footprint!")

# Calculate stats
total_points = df_history['points'].sum() if not df_history.empty else 0
total_completed = len(df_history)

# Calculate Streak
streak = 0
if not df_history.empty:
    df_history['completed_date'] = pd.to_datetime(df_history['completed_date']).dt.date
    unique_dates = sorted(df_history['completed_date'].unique(), reverse=True)
    
    current_date = date.today()
    if unique_dates and (unique_dates[0] == current_date or unique_dates[0] == current_date - timedelta(days=1)):
        streak = 1
        check_date = unique_dates[0]
        for d in unique_dates[1:]:
            if d == check_date - timedelta(days=1):
                streak += 1
                check_date = d
            else:
                break

st.header("📊 Your Progress")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Streak", f"🔥 {streak} Days")
col2.metric("Total Points", f"⭐ {total_points}")
col3.metric("Challenges Completed", f"✅ {total_completed}")

# Weekly Completion %
week_start = date.today() - timedelta(days=7)
if not df_history.empty:
    week_completed = df_history[df_history['completed_date'] >= week_start]
    weekly_count = len(week_completed)
    pct = min(100, int((weekly_count / (7 * len(categories))) * 100)) 
else:
    pct = 0
col4.metric("Weekly Goal", f"{pct}%")
st.progress(pct / 100.0)

st.divider()

st.header(f"📅 Today's Challenges ({today_str})")
st.write("Choose your challenges for today. You can only complete each challenge once per day.")

# Category Filter
cat_filter = st.selectbox("Filter by Category:", ["All"] + categories)

for challenge in daily_challenges:
    if cat_filter != "All" and challenge["category"] != cat_filter:
        continue
        
    is_completed = challenge["id"] in completed_today
    
    diff_color = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}[challenge["difficulty"]]
    
    with st.container(border=True):
        col_c1, col_c2 = st.columns([4, 1])
        with col_c1:
            st.markdown(f"#### {challenge['title']} {diff_color}")
            st.markdown(f"**Category:** {challenge['category']} | **Difficulty:** {challenge['difficulty']} | **Reward:** {challenge['points']} pts")
            st.write(challenge["desc"])
            st.caption(f"🌍 **Impact:** {challenge['impact']}")
        
        with col_c2:
            st.write("") # spacing
            st.write("")
            if is_completed:
                st.button("✅ Completed", key=f"btn_{challenge['id']}", disabled=True, use_container_width=True)
            else:
                if st.button("Mark Complete", key=f"btn_{challenge['id']}", use_container_width=True):
                    complete_challenge(user_id, challenge, today_str)
                    st.toast(f"Challenge completed! +{challenge['points']} points")
                    st.rerun()

st.divider()

# ==========================================
# ACHIEVEMENTS & IMPACT SUMMARY
# ==========================================
st.header("🏆 Milestones & Impact")

col_m1, col_m2 = st.columns(2)

with col_m1:
    st.subheader("Achievements")
    milestones = [
        {"name": "Eco Novice", "req": 5, "icon": "🌱"},
        {"name": "Green Warrior", "req": 20, "icon": "🌿"},
        {"name": "Planet Savior", "req": 50, "icon": "🌳"},
        {"name": "Climate Champion", "req": 100, "icon": "🌎"}
    ]
    
    next_milestone = None
    for m in milestones:
        if total_completed >= m["req"]:
            st.success(f"{m['icon']} **{m['name']}** (Unlocked - {m['req']} challenges)")
        else:
            if not next_milestone:
                next_milestone = m
            st.markdown(f"🔒 **{m['name']}** (Requires {m['req']} challenges)")
            
    if next_milestone:
        st.write(f"**Progress to next milestone:** {total_completed} / {next_milestone['req']}")
        st.progress(min(1.0, total_completed / next_milestone['req']))

with col_m2:
    st.subheader("Completion by Category")
    if not df_history.empty:
        cat_counts = df_history['category'].value_counts().reset_index()
        cat_counts.columns = ['Category', 'Count']
        fig = px.pie(cat_counts, names='Category', values='Count', hole=0.4, title="Your Focus Areas", color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Complete some challenges to see your category breakdown!")

st.divider()

# History
st.header("📜 Recent History")
if not df_history.empty:
    st.dataframe(
        df_history[['completed_date', 'category', 'difficulty', 'points']].head(10),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No challenges completed yet. Start today!")
