# ============================================================
# FILE: habit_tracker.py
# EcoBuddy AI+ Eco-Productivity & Habit Tracker
# ============================================================

import os
import sqlite3
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)
DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


def init_habit_db(db_name: str = DB_NAME) -> None:
    """Initialize persistent SQLite table for habit tracking."""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_habits (
                user_id INTEGER PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error(f"Error initializing user_habits DB: {exc}")


def load_user_habits_db(user_id: int, db_name: str = DB_NAME) -> Optional[Dict[str, Any]]:
    """Load habit data from database for a user."""
    init_habit_db(db_name)
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT data_json FROM user_habits WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return json.loads(row[0])
    except Exception as exc:
        logger.error(f"Error loading habits from DB: {exc}")
    return None


def save_user_habits_db(user_id: int, data: Dict[str, Any], db_name: str = DB_NAME) -> bool:
    """Persist habit data to database for a user."""
    init_habit_db(db_name)
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_habits (user_id, data_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                data_json = excluded.data_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, json.dumps(data))
        )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.error(f"Error saving habits to DB: {exc}")
        return False


# ============================================================
# HABIT DATABASE
# ============================================================

class HabitDatabase:
    """Pre-defined sustainable habits with impact metrics"""
    
    HABITS = {
        'transport': [
            {'name': '🚲 Walk/Bike instead of drive', 'carbon_saving': 2.5, 'ease': 4, 'category': 'Transport'},
            {'name': '🚌 Use public transit', 'carbon_saving': 1.8, 'ease': 3, 'category': 'Transport'},
            {'name': '🚗 Carpool to work', 'carbon_saving': 2.0, 'ease': 2, 'category': 'Transport'},
            {'name': '🚶 Walk for short trips', 'carbon_saving': 1.0, 'ease': 5, 'category': 'Transport'}
        ],
        'energy': [
            {'name': '💡 Turn off lights', 'carbon_saving': 0.5, 'ease': 5, 'category': 'Energy'},
            {'name': '🔌 Unplug unused electronics', 'carbon_saving': 0.3, 'ease': 4, 'category': 'Energy'},
            {'name': '👕 Air dry clothes', 'carbon_saving': 1.2, 'ease': 3, 'category': 'Energy'},
            {'name': '🌡️ Set thermostat 2° lower', 'carbon_saving': 0.8, 'ease': 3, 'category': 'Energy'}
        ],
        'food': [
            {'name': '🥗 Meatless Monday', 'carbon_saving': 3.0, 'ease': 3, 'category': 'Food'},
            {'name': '🌾 Eat locally sourced food', 'carbon_saving': 1.5, 'ease': 2, 'category': 'Food'},
            {'name': '🍽️ Zero food waste day', 'carbon_saving': 2.0, 'ease': 3, 'category': 'Food'},
            {'name': '🌱 Plant-based meal', 'carbon_saving': 2.5, 'ease': 3, 'category': 'Food'}
        ],
        'waste': [
            {'name': '♻️ Recycle all recyclables', 'carbon_saving': 1.0, 'ease': 4, 'category': 'Waste'},
            {'name': '🛍️ Reusable shopping bags', 'carbon_saving': 0.4, 'ease': 5, 'category': 'Waste'},
            {'name': '🧑‍🌾 Compost food scraps', 'carbon_saving': 1.8, 'ease': 2, 'category': 'Waste'},
            {'name': '💧 Reusable water bottle', 'carbon_saving': 0.6, 'ease': 5, 'category': 'Waste'}
        ],
        'water': [
            {'name': '🚿 Shorten showers by 2 min', 'carbon_saving': 0.6, 'ease': 4, 'category': 'Water'},
            {'name': '🔧 Fix leaky faucets', 'carbon_saving': 0.4, 'ease': 2, 'category': 'Water'},
            {'name': '🌧️ Use rainwater for plants', 'carbon_saving': 0.3, 'ease': 3, 'category': 'Water'},
            {'name': '🧺 Full loads only', 'carbon_saving': 0.5, 'ease': 4, 'category': 'Water'}
        ]
    }
    
    @staticmethod
    def get_all_habits():
        """Get all habits"""
        habits = []
        for category in HabitDatabase.HABITS.values():
            habits.extend(category)
        return habits
    
    @staticmethod
    def get_habits_by_category(category=None):
        """Get habits by category"""
        if category and category != "All":
            return HabitDatabase.HABITS.get(category.lower(), [])
        return HabitDatabase.get_all_habits()

# ============================================================
# HABIT TRACKER
# ============================================================

class HabitTracker:
    """Track user habits and streaks with automatic daily reset and persistence"""
    
    def __init__(self, user_id: int, db_name: str = DB_NAME):
        self.user_id = user_id
        self.db_name = db_name
        self.data = self._load_data()
        self._refresh_daily_status()
    
    def _load_data(self) -> Dict[str, Any]:
        """Load habit data from DB with fallback to session or defaults."""
        db_data = load_user_habits_db(self.user_id, self.db_name)
        if db_data:
            return db_data

        if hasattr(st, "session_state") and "habit_data" in st.session_state:
            session_data = st.session_state.habit_data.get(self.user_id)
            if session_data:
                return session_data

        return {
            'active_habits': [],
            'completed_today': [],
            'history': {},
            'streaks': {},
            'best_streaks': {},
            'last_completed': {},
            'last_active_date': datetime.now().date().isoformat()
        }
    
    def _refresh_daily_status(self) -> None:
        """Clear completed_today if a new day has arrived and check streak continuity."""
        today = datetime.now().date()
        last_date_str = self.data.get('last_active_date')
        if last_date_str:
            try:
                last_date = datetime.fromisoformat(last_date_str).date()
                if today > last_date:
                    self.data['completed_today'] = []
                    self.data['last_active_date'] = today.isoformat()
                    # Check for broken streaks
                    for habit, last_ts in self.data.get('last_completed', {}).items():
                        try:
                            last_c_date = datetime.fromisoformat(last_ts).date()
                            if (today - last_c_date).days > 1:
                                self.data['streaks'][habit] = 0
                        except Exception:
                            pass
                    self.save()
            except Exception:
                self.data['last_active_date'] = today.isoformat()
        else:
            self.data['last_active_date'] = today.isoformat()

    def save(self) -> None:
        """Save habit data to session and DB."""
        if hasattr(st, "session_state"):
            if "habit_data" not in st.session_state:
                st.session_state.habit_data = {}
            st.session_state.habit_data[self.user_id] = self.data
            st.session_state.habit_data_updated = True
        save_user_habits_db(self.user_id, self.data, self.db_name)
    
    def add_habit(self, habit_name: str) -> bool:
        """Add a habit to tracking"""
        if habit_name not in self.data['active_habits']:
            self.data['active_habits'].append(habit_name)
            self.data.setdefault('streaks', {})[habit_name] = 0
            self.data.setdefault('best_streaks', {})[habit_name] = 0
            self.data.setdefault('history', {})[habit_name] = []
            self.save()
            return True
        return False
    
    def complete_habit(self, habit_name: str, completion_date: Optional[str] = None) -> bool:
        """Mark a habit as completed for today or custom date"""
        today_date = datetime.fromisoformat(completion_date).date() if completion_date else datetime.now().date()
        today = today_date.isoformat()
        
        today_habits = self.data.get('completed_today', [])
        
        if habit_name not in today_habits:
            today_habits.append(habit_name)
            self.data['completed_today'] = today_habits
            
            # Update streak
            last_completed = self.data.get('last_completed', {}).get(habit_name)
            if last_completed:
                try:
                    last_date = datetime.fromisoformat(last_completed).date()
                    day_diff = (today_date - last_date).days
                    
                    if day_diff == 1:
                        self.data['streaks'][habit_name] = self.data['streaks'].get(habit_name, 0) + 1
                    elif day_diff > 1:
                        self.data['streaks'][habit_name] = 1
                except Exception:
                    self.data['streaks'][habit_name] = 1
            else:
                self.data['streaks'][habit_name] = 1
            
            current_streak = self.data['streaks'].get(habit_name, 1)
            if current_streak > self.data.get('best_streaks', {}).get(habit_name, 0):
                self.data.setdefault('best_streaks', {})[habit_name] = current_streak
            
            self.data.setdefault('history', {}).setdefault(habit_name, []).append({
                'date': today,
                'streak': current_streak
            })
            
            self.data.setdefault('last_completed', {})[habit_name] = datetime.now().isoformat()
            self.save()
            return True
        return False
    
    def remove_habit(self, habit_name: str) -> bool:
        """Remove a habit from active tracking."""
        if habit_name in self.data.get('active_habits', []):
            self.data['active_habits'].remove(habit_name)
            self.save()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get habit statistics"""
        total_habits = len(self.data['active_habits'])
        completed_today = len(self.data.get('completed_today', []))
        
        total_streak = sum(self.data.get('streaks', {}).values()) if self.data.get('streaks') else 0
        avg_streak = total_streak / total_habits if total_habits > 0 else 0
        
        best_habit = None
        if self.data.get('streaks'):
            valid_streaks = {k: v for k, v in self.data['streaks'].items() if k in self.data['active_habits']}
            if valid_streaks:
                best_habit = max(valid_streaks.items(), key=lambda x: x[1])[0]

        return {
            'total_habits': total_habits,
            'completed_today': completed_today,
            'completion_rate': (completed_today / total_habits * 100) if total_habits > 0 else 0,
            'total_streak': total_streak,
            'avg_streak': avg_streak,
            'best_habit': best_habit
        }
    
    def get_streak_level(self, habit_name: str) -> Dict[str, str]:
        """Get streak level for a habit"""
        streak = self.data.get('streaks', {}).get(habit_name, 0)
        if streak == 0:
            return {"emoji": "🌱", "label": "Seed", "description": "Just starting"}
        elif streak < 7:
            return {"emoji": "🌿", "label": "Sprout", "description": "Building momentum"}
        elif streak < 30:
            return {"emoji": "🌳", "label": "Tree", "description": "Strong habit forming"}
        elif streak < 100:
            return {"emoji": "🌲", "label": "Forest", "description": "Dedicated commitment"}
        else:
            return {"emoji": "🏆", "label": "Eco Champion", "description": "Master of sustainability"}

# ============================================================
# HABIT RECOMMENDER
# ============================================================

class HabitRecommender:
    """Recommend habits based on user profile"""
    
    @staticmethod
    def recommend_habits(user_id: int) -> List[Dict[str, Any]]:
        """Personalized habit recommendations"""
        all_habits = HabitDatabase.get_all_habits()
        
        tracker = HabitTracker(user_id)
        active = tracker.data['active_habits']
        
        available = [h.copy() for h in all_habits if h['name'] not in active]
        
        for habit in available:
            carbon_score = (habit['carbon_saving'] / 3.0) * 40.0
            ease_score = (habit['ease'] / 5.0) * 30.0
            variety_score = random.random() * 30.0
            habit['score'] = carbon_score + ease_score + variety_score
        
        available.sort(key=lambda x: x['score'], reverse=True)
        return available[:5]

# ============================================================
# CARBON SAVINGS CALCULATOR
# ============================================================

class CarbonSavingsCalculator:
    """Calculate carbon savings from habit completion"""
    
    @staticmethod
    def calculate_savings(habits: List[str]) -> Dict[str, Any]:
        """Calculate total carbon saved"""
        total_carbon = 0.0
        habit_data = {}
        
        all_habits = HabitDatabase.get_all_habits()
        for habit in habits:
            habit_info = next((h for h in all_habits if h['name'] == habit), None)
            if habit_info:
                saving = habit_info['carbon_saving']
                total_carbon += saving
                habit_data[habit] = saving
        
        return {
            'total_carbon': total_carbon,
            'habit_data': habit_data,
            'trees_equivalent': total_carbon / 22.0,
            'cars_equivalent': total_carbon / 5000.0
        }

# ============================================================
# RENDER FUNCTIONS
# ============================================================

def render_habit_tracker():
    """Render the complete habit tracker"""
    st.markdown("<div class='section-header'>🌱 Eco-Productivity & Habit Tracker</div>", unsafe_allow_html=True)
    
    user_id = st.session_state.get('user_id', 1)
    
    if "habit_tracker" not in st.session_state or st.session_state.habit_tracker.user_id != user_id:
        st.session_state.habit_tracker = HabitTracker(user_id)
    
    tracker = st.session_state.habit_tracker
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Today's Habits",
        "📊 Progress",
        "💡 Recommendations",
        "📈 Impact"
    ])
    
    with tab1:
        render_daily_habits(tracker)
    
    with tab2:
        render_progress(tracker)
    
    with tab3:
        render_recommendations(tracker)
    
    with tab4:
        render_impact(tracker)


def render_daily_habits(tracker: HabitTracker):
    """Render daily habits"""
    st.markdown("### 📋 Today's Eco-Habits")
    
    stats = tracker.get_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Habits", stats['total_habits'])
    col2.metric("Completed Today", f"{stats['completed_today']}/{stats['total_habits']}")
    col3.metric("Completion Rate", f"{stats['completion_rate']:.0f}%")
    col4.metric("Total Streak", f"{stats['total_streak']} days")
    
    st.progress(stats['completion_rate'] / 100.0)
    st.markdown("---")
    
    with st.expander("➕ Add New Habit", expanded=False):
        all_habits = HabitDatabase.get_all_habits()
        active_names = tracker.data['active_habits']
        available = [h for h in all_habits if h['name'] not in active_names]
        
        if available:
            habit_options = [h['name'] for h in available]
            selected_habit = st.selectbox("Choose a habit to add", habit_options)
            
            if st.button("Add Habit", use_container_width=True):
                tracker.add_habit(selected_habit)
                st.success(f"✅ Added {selected_habit}!")
                st.rerun()
        else:
            st.info("🎉 You're already tracking all available habits!")
    
    st.markdown("#### Your Habits")
    active_habits = tracker.data['active_habits']
    completed_today = tracker.data.get('completed_today', [])
    
    if active_habits:
        for habit in active_habits:
            is_completed = habit in completed_today
            streak_info = tracker.get_streak_level(habit)
            streak_value = tracker.data['streaks'].get(habit, 0)
            
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    status_icon = "✅" if is_completed else "⬜"
                    st.markdown(f"{status_icon} **{habit}**")
                    st.caption(f"{streak_info['emoji']} {streak_info['label']} - {streak_value} day streak")
                
                with col2:
                    st.caption(f"{streak_info['description']}")
                
                with col3:
                    if not is_completed:
                        if st.button("✅ Complete", key=f"complete_{habit}"):
                            tracker.complete_habit(habit)
                            st.success(f"🌟 Great job! {habit} completed!")
                            st.rerun()
                    else:
                        st.success("✅ Done")
                
                with col4:
                    if st.button("🗑️ Remove", key=f"remove_{habit}"):
                        tracker.remove_habit(habit)
                        st.rerun()
    else:
        st.info("🌱 No habits added yet. Add your first sustainable habit above!")
    
    st.markdown("---")
    st.markdown("### 💪 Daily Motivation")
    
    if stats['completion_rate'] == 100:
        st.success("🌟 Perfect day! You've completed all your habits!")
        st.balloons()
    elif stats['completion_rate'] >= 50:
        st.info("🌿 Great progress! Keep going!")
    else:
        st.info("🌱 Every step counts. Start with one habit today!")


def render_progress(tracker: HabitTracker):
    """Render progress visualization"""
    st.markdown("### 📊 Habit Progress")
    
    st.markdown("#### 🔥 Streak Overview")
    if tracker.data.get('streaks'):
        habits = list(tracker.data['streaks'].keys())
        streaks = [tracker.data['streaks'].get(h, 0) for h in habits]
        best_streaks = [tracker.data.get('best_streaks', {}).get(h, 0) for h in habits]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=habits,
            y=streaks,
            name='Current Streak',
            marker_color='#4ade80'
        ))
        fig.add_trace(go.Bar(
            x=habits,
            y=best_streaks,
            name='Best Streak',
            marker_color='#fbbf24',
            opacity=0.7
        ))
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=20, b=0),
            barmode='group',
            yaxis_title='Days'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Start completing habits to see your streaks!")
    
    st.markdown("#### 📅 Habit Completion History")
    if tracker.data.get('history'):
        rows = []
        for habit, history in tracker.data['history'].items():
            for entry in history[-30:]:
                rows.append({
                    'Date': pd.to_datetime(entry['date']),
                    'Completed': 1,
                    'Habit': habit
                })
        
        if rows:
            df = pd.DataFrame(rows)
            fig = px.density_heatmap(
                df,
                x='Date',
                y='Habit',
                z='Completed',
                color_continuous_scale='Greens',
                title="Habit Completion Pattern"
            )
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("#### 🏆 Milestone Achievements")
    milestones = []
    for habit, streak in tracker.data.get('streaks', {}).items():
        if streak >= 30:
            milestones.append(f"🌟 {habit} - 30+ day streak!")
        elif streak >= 7:
            milestones.append(f"🌿 {habit} - 7+ day streak!")
    
    if milestones:
        for milestone in milestones:
            st.success(milestone)
    else:
        st.info("💪 Complete habits for 7 days to start earning milestones!")


def render_recommendations(tracker: HabitTracker):
    """Render habit recommendations"""
    st.markdown("### 💡 Habit Recommendations")
    recommendations = HabitRecommender.recommend_habits(tracker.user_id)
    
    if recommendations:
        st.markdown("#### 🌱 Suggested Habits for You")
        for habit in recommendations:
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"**{habit['name']}**")
                    st.caption(f"Category: {habit['category']}")
                with col2:
                    st.metric("Carbon Saving", f"{habit['carbon_saving']} kg/day")
                with col3:
                    if st.button("➕ Add", key=f"rec_{habit['name']}"):
                        tracker.add_habit(habit['name'])
                        st.success(f"✅ Added {habit['name']}!")
                        st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 Recommendation Breakdown")
        
        scores_df = pd.DataFrame([
            {
                "Habit": h['name'],
                "Carbon Score": (h['carbon_saving'] / 3.0) * 40.0,
                "Ease Score": (h['ease'] / 5.0) * 30.0,
                "Total": h['score']
            }
            for h in recommendations
        ])
        
        fig = go.Figure()
        for col in ['Carbon Score', 'Ease Score']:
            if col in scores_df.columns:
                fig.add_trace(go.Bar(
                    x=scores_df['Habit'],
                    y=scores_df[col],
                    name=col
                ))
        fig.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=20, b=0),
            barmode='stack',
            yaxis_title='Score'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("🎉 You're already tracking all available habits!")


def render_impact(tracker: HabitTracker):
    """Render environmental impact"""
    st.markdown("### 📈 Environmental Impact")
    completed_today = tracker.data.get('completed_today', [])
    
    if completed_today:
        savings = CarbonSavingsCalculator.calculate_savings(completed_today)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("CO₂ Saved Today", f"{savings['total_carbon']:.1f} kg")
        col2.metric("Trees Equivalent", f"{savings['trees_equivalent']:.1f}")
        col3.metric("Cars Equivalent", f"{savings['cars_equivalent']:.2f}")
        col4.metric("Habits Completed", len(completed_today))
        
        if savings['habit_data']:
            st.markdown("#### Breakdown by Habit")
            fig = go.Figure(data=[go.Pie(
                labels=list(savings['habit_data'].keys()),
                values=list(savings['habit_data'].values()),
                hole=0.3,
                marker=dict(colors=['#4ade80', '#fbbf24', '#60a5fa', '#a78bfa', '#f87171'])
            )])
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        
        daily_avg = savings['total_carbon']
        annual_projection = daily_avg * 365
        
        st.markdown("#### 📊 Projected Annual Impact")
        col1, col2 = st.columns(2)
        col1.metric("Annual CO₂ Saved", f"{annual_projection:.0f} kg")
        col2.metric("Annual Trees Equivalent", f"{annual_projection / 22:.1f}")
        
        st.progress(min(annual_projection / 5000.0, 1.0))
        if annual_projection > 1000:
            st.success("🌟 Excellent! You're making a significant environmental impact!")
        elif annual_projection > 500:
            st.info("🌿 Good progress! Keep building your sustainable habits!")
        else:
            st.info("🌱 Every habit counts. Add more habits to increase your impact!")
    else:
        st.info("📋 Complete some habits today to see your environmental impact!")


def render_habit_hub():
    """Render the complete habit hub"""
    render_habit_tracker()