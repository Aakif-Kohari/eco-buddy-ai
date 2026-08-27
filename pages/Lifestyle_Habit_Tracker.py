import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from typing import Dict, Any, List

from src.lifestyle.habit_tracker import load_user_habits_db, save_user_habits_db
from styles.theme import apply_theme

CATEGORIES = ["Transportation", "Food", "Energy", "Water", "Waste", "Shopping", "Other"]

class LifestyleTracker:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.data = self._load()
        self._check_daily_rollover()
        
    def _load(self) -> Dict[str, Any]:
        data = load_user_habits_db(self.user_id) or {}
        # We extend the schema if needed
        return {
            'habits': data.get('habits', []), # list of dicts: id, name, category, frequency (daily/weekly), target_days
            'history': data.get('history', {}), # dict: habit_id -> { date_str -> 'completed' | 'skipped' | 'missed' }
            'streaks': data.get('streaks', {}), # dict: habit_id -> current streak
            'best_streaks': data.get('best_streaks', {}),
            'last_active_date': data.get('last_active_date', datetime.now().date().isoformat())
        }
        
    def save(self):
        save_user_habits_db(self.user_id, self.data)
        
    def _check_daily_rollover(self):
        today = datetime.now().date()
        last_active = datetime.fromisoformat(self.data['last_active_date']).date()
        
        if last_active < today:
            days_passed = (today - last_active).days
            
            # Fill missing days with 'missed' for daily habits
            for habit in self.data['habits']:
                if habit.get('frequency', 'daily') == 'daily':
                    h_id = habit['id']
                    if h_id not in self.data['history']:
                        self.data['history'][h_id] = {}
                        
                    for i in range(1, days_passed):
                        missed_date = (last_active + timedelta(days=i)).isoformat()
                        if missed_date not in self.data['history'][h_id]:
                            self.data['history'][h_id][missed_date] = 'missed'
                            self.data['streaks'][h_id] = 0 # Break streak
            
            self.data['last_active_date'] = today.isoformat()
            self.save()

    def add_custom_habit(self, name: str, category: str, frequency: str = 'daily', target_days: int = 7):
        habit_id = f"habit_{len(self.data['habits'])}_{datetime.now().timestamp()}"
        self.data['habits'].append({
            'id': habit_id,
            'name': name,
            'category': category,
            'frequency': frequency,
            'target_days': target_days,
            'created_at': datetime.now().isoformat()
        })
        self.data['history'][habit_id] = {}
        self.data['streaks'][habit_id] = 0
        self.data['best_streaks'][habit_id] = 0
        self.save()

    def remove_habit(self, habit_id: str):
        self.data['habits'] = [h for h in self.data['habits'] if h['id'] != habit_id]
        if habit_id in self.data['history']:
            del self.data['history'][habit_id]
        if habit_id in self.data['streaks']:
            del self.data['streaks'][habit_id]
        if habit_id in self.data['best_streaks']:
            del self.data['best_streaks'][habit_id]
        self.save()

    def update_status(self, habit_id: str, status: str, date_str: str = None):
        """status must be one of: 'completed', 'skipped', 'missed', None"""
        if not date_str:
            date_str = datetime.now().date().isoformat()
            
        if habit_id not in self.data['history']:
            self.data['history'][habit_id] = {}
            
        if status:
            self.data['history'][habit_id][date_str] = status
        else:
            self.data['history'][habit_id].pop(date_str, None)
            
        self._recalculate_streak(habit_id)
        self.save()
        
    def _recalculate_streak(self, habit_id: str):
        history = self.data['history'].get(habit_id, {})
        dates = sorted(history.keys(), reverse=True)
        streak = 0
        
        today = datetime.now().date()
        today_str = today.isoformat()
        yesterday_str = (today - timedelta(days=1)).isoformat()
        
        # Determine if streak is alive
        if history.get(today_str) in ['missed']:
            pass
        elif history.get(today_str) in ['completed']:
            streak += 1
            curr_date = today - timedelta(days=1)
            while True:
                d_str = curr_date.isoformat()
                stat = history.get(d_str)
                if stat == 'completed':
                    streak += 1
                elif stat == 'skipped':
                    pass # Doesn't break streak, but doesn't add
                else:
                    break
                curr_date -= timedelta(days=1)
        elif history.get(yesterday_str) in ['completed', 'skipped']:
            # Streak carries over if not acted on today yet
            curr_date = today - timedelta(days=1)
            while True:
                d_str = curr_date.isoformat()
                stat = history.get(d_str)
                if stat == 'completed':
                    streak += 1
                elif stat == 'skipped':
                    pass
                else:
                    break
                curr_date -= timedelta(days=1)
                
        self.data['streaks'][habit_id] = streak
        if streak > self.data['best_streaks'].get(habit_id, 0):
            self.data['best_streaks'][habit_id] = streak

    def get_stats(self) -> Dict[str, Any]:
        total_actions = 0
        completed_actions = 0
        skipped_actions = 0
        missed_actions = 0
        category_stats = {cat: {'completed': 0, 'total': 0} for cat in CATEGORIES}
        
        for h in self.data['habits']:
            h_id = h['id']
            cat = h['category']
            if cat not in category_stats:
                category_stats[cat] = {'completed': 0, 'total': 0}
                
            for d_str, stat in self.data['history'].get(h_id, {}).items():
                total_actions += 1
                category_stats[cat]['total'] += 1
                if stat == 'completed':
                    completed_actions += 1
                    category_stats[cat]['completed'] += 1
                elif stat == 'skipped':
                    skipped_actions += 1
                elif stat == 'missed':
                    missed_actions += 1
                    
        completion_rate = (completed_actions / total_actions * 100) if total_actions > 0 else 0
        
        # Sustainability Progress Score
        score = min(100, completion_rate * 1.1)
        
        return {
            'total': total_actions,
            'completed': completed_actions,
            'skipped': skipped_actions,
            'missed': missed_actions,
            'completion_rate': completion_rate,
            'score': score,
            'category_stats': category_stats
        }
        
    def generate_recommendations(self) -> List[str]:
        recs = []
        stats = self.get_stats()
        
        # Find weakest category
        cat_stats = stats['category_stats']
        weakest_cat = None
        lowest_rate = 100
        for cat, data in cat_stats.items():
            if data['total'] > 3:
                rate = data['completed'] / data['total'] * 100
                if rate < lowest_rate:
                    lowest_rate = rate
                    weakest_cat = cat
                    
        if weakest_cat:
            recs.append(f"🔍 **Focus Area**: Your completion rate for **{weakest_cat}** habits is currently {lowest_rate:.1f}%. Consider setting easier targets or reviewing your barriers here.")
            
        # Find consistently missed habits
        today = datetime.now().date()
        for h in self.data['habits']:
            h_id = h['id']
            missed_last_3 = True
            for i in range(1, 4):
                d_str = (today - timedelta(days=i)).isoformat()
                if self.data['history'].get(h_id, {}).get(d_str) != 'missed':
                    missed_last_3 = False
                    break
            if missed_last_3:
                recs.append(f"⚠️ **Habit Alert**: You've missed **'{h['name']}'** for the last 3 days. Might be helpful to adjust the frequency or mark it as 'skipped' if you're on a break.")
                
        if not recs:
            recs.append("🌟 Amazing consistency! Keep maintaining your current sustainable lifestyle.")
            
        return recs

def render_lifestyle_tracker():
    apply_theme()
    st.title("🌱 Sustainable Lifestyle Progress")
    st.markdown("Track your eco-habits, monitor your sustainability score, and achieve your personal lifestyle src.utils.goals.")
    
    user_id = st.session_state.get('user_id', 1)
    tracker = LifestyleTracker(user_id)
    
    tab_track, tab_progress, tab_manage = st.tabs([
        "✅ Daily Tracker", 
        "📈 Progress & Stats", 
        "⚙️ Manage Habits"
    ])
    
    today_str = datetime.now().date().isoformat()
    
    with tab_track:
        st.subheader("Today's Habits")
        
        if not tracker.data['habits']:
            st.info("You haven't set up any habits yet. Go to **Manage Habits** to get started!")
        else:
            for habit in tracker.data['habits']:
                h_id = habit['id']
                current_status = tracker.data['history'].get(h_id, {}).get(today_str)
                
                with st.container():
                    col_name, col_streak, col_actions = st.columns([2, 1, 3])
                    with col_name:
                        st.markdown(f"**{habit['name']}**")
                        st.caption(habit['category'])
                    with col_streak:
                        st.markdown(f"🔥 {tracker.data['streaks'].get(h_id, 0)}")
                    with col_actions:
                        # Status buttons
                        ca1, ca2, ca3 = st.columns(3)
                        
                        btn_comp_style = "primary" if current_status == "completed" else "secondary"
                        if ca1.button("✅ Done", key=f"comp_{h_id}", type=btn_comp_style, use_container_width=True):
                            tracker.update_status(h_id, "completed")
                            st.rerun()
                            
                        btn_skip_style = "primary" if current_status == "skipped" else "secondary"
                        if ca2.button("⏭️ Skip", key=f"skip_{h_id}", type=btn_skip_style, use_container_width=True):
                            tracker.update_status(h_id, "skipped")
                            st.rerun()
                            
                        btn_miss_style = "primary" if current_status == "missed" else "secondary"
                        if ca3.button("❌ Missed", key=f"miss_{h_id}", type=btn_miss_style, use_container_width=True):
                            tracker.update_status(h_id, "missed")
                            st.rerun()
                    st.divider()
                    
    with tab_progress:
        st.subheader("📊 Analytics & Consistency")
        stats = tracker.get_stats()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sustainability Score", f"{stats['score']:.0f}/100")
        c2.metric("Completion Rate", f"{stats['completion_rate']:.1f}%")
        c3.metric("Total Completed", stats['completed'])
        c4.metric("Total Skips/Misses", stats['skipped'] + stats['missed'])
        
        st.markdown("---")
        ch1, ch2 = st.columns(2)
        
        with ch1:
            st.markdown("#### Progress by Category")
            cat_data = []
            for cat, cstats in stats['category_stats'].items():
                if cstats['total'] > 0:
                    cat_data.append({
                        "Category": cat,
                        "Rate": (cstats['completed'] / cstats['total']) * 100
                    })
            if cat_data:
                df_cat = pd.DataFrame(cat_data)
                fig_cat = px.bar(df_cat, x="Category", y="Rate", title="Completion % by Category", color="Category")
                fig_cat.update_layout(yaxis_range=[0,100], showlegend=False, margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info("Not enough data to show category stats.")
                
        with ch2:
            st.markdown("#### Habit Streaks")
            streak_data = []
            for h in tracker.data['habits']:
                h_id = h['id']
                streak_data.append({
                    "Habit": h['name'],
                    "Current": tracker.data['streaks'].get(h_id, 0),
                    "Best": tracker.data['best_streaks'].get(h_id, 0)
                })
            if streak_data:
                df_streak = pd.DataFrame(streak_data)
                fig_streak = go.Figure(data=[
                    go.Bar(name='Current Streak', x=df_streak['Habit'], y=df_streak['Current']),
                    go.Bar(name='Best Streak', x=df_streak['Habit'], y=df_streak['Best'])
                ])
                fig_streak.update_layout(barmode='group', title="Streaks Overview", margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig_streak, use_container_width=True)
            else:
                st.info("No streak data available.")
                
        st.markdown("#### 💡 AI Lifestyle Recommendations")
        for rec in tracker.generate_recommendations():
            st.info(rec)
            
    with tab_manage:
        st.subheader("⚙️ Manage Your Lifestyle Habits")
        
        with st.expander("➕ Create New Habit", expanded=True):
            with st.form("new_habit_form"):
                nh_name = st.text_input("Habit Name", placeholder="e.g., Meatless Monday, Turn off lights")
                nh_cat = st.selectbox("Category", CATEGORIES)
                nh_freq = st.selectbox("Frequency Target", ["daily", "weekly"])
                nh_submit = st.form_submit_button("Add Habit")
                
                if nh_submit:
                    if nh_name.strip():
                        tracker.add_custom_habit(nh_name.strip(), nh_cat, nh_freq)
                        st.success(f"Added {nh_name}!")
                        st.rerun()
                    else:
                        st.error("Please enter a habit name.")
                        
        st.markdown("### Active Habits")
        for habit in tracker.data['habits']:
            h_id = habit['id']
            hc1, hc2 = st.columns([4, 1])
            with hc1:
                st.markdown(f"**{habit['name']}** ({habit['category']}) - {habit['frequency']}")
            with hc2:
                if st.button("🗑️ Remove", key=f"del_{h_id}"):
                    tracker.remove_habit(h_id)
                    st.rerun()

if __name__ == "__main__":
    render_lifestyle_tracker()
