# ============================================================
# FILE: waste_manager.py
# EcoBuddy AI+ Smart Waste Management System
# ============================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import json

# ============================================================
# WASTE CATEGORIES & RECYCLING GUIDES
# ============================================================

class WasteCategories:
    """Waste categorization and recycling information"""
    
    CATEGORIES = {
        "plastic": {
            "name": "Plastic",
            "emoji": "🫙",
            "recyclable": True,
            "decomposition_years": 450,
            "recycling_tips": [
                "Rinse containers before recycling",
                "Remove labels and caps",
                "Check recycling symbol numbers 1-7",
                "Crush bottles to save space"
            ],
            "alternatives": [
                "Reusable water bottles",
                "Glass containers",
                "Bamboo utensils",
                "Cloth shopping bags"
            ]
        },
        "paper": {
            "name": "Paper",
            "emoji": "📄",
            "recyclable": True,
            "decomposition_years": 2,
            "recycling_tips": [
                "Remove plastic windows from envelopes",
                "Keep paper clean and dry",
                "Shred sensitive documents",
                "Recycle newspaper separately"
            ],
            "alternatives": [
                "Digital documents",
                "Reusable notebooks",
                "Cloth napkins",
                "Email instead of paper mail"
            ]
        },
        "glass": {
            "name": "Glass",
            "emoji": "🍾",
            "recyclable": True,
            "decomposition_years": 1000000,
            "recycling_tips": [
                "Rinse thoroughly",
                "Remove lids and corks",
                "Don't break glass",
                "Separate by color if required"
            ],
            "alternatives": [
                "Reusable glass jars",
                "Stainless steel containers",
                "Bamboo containers",
                "Silicone food storage"
            ]
        },
        "metal": {
            "name": "Metal",
            "emoji": "🥫",
            "recyclable": True,
            "decomposition_years": 200,
            "recycling_tips": [
                "Rinse food containers",
                "Remove plastic labels",
                "Crush cans to save space",
                "Separate aluminum from steel"
            ],
            "alternatives": [
                "Reusable containers",
                "Stainless steel water bottles",
                "Cast iron cookware",
                "Bamboo cutlery"
            ]
        },
        "organic": {
            "name": "Organic Waste",
            "emoji": "🧑‍🌾",
            "recyclable": True,
            "decomposition_years": 0.5,
            "recycling_tips": [
                "Start a compost bin",
                "Layer green and brown materials",
                "Turn compost regularly",
                "Use compost for gardening"
            ],
            "alternatives": [
                "Home composting",
                "Community garden",
                "Worm farming",
                "Bokashi bins"
            ]
        },
        "electronic": {
            "name": "E-Waste",
            "emoji": "💻",
            "recyclable": True,
            "decomposition_years": 1000,
            "recycling_tips": [
                "Find certified e-waste recyclers",
                "Remove batteries separately",
                "Wipe personal data",
                "Donate working electronics"
            ],
            "alternatives": [
                "Repair instead of replace",
                "Upgrade existing devices",
                "Donate to schools",
                "Buy refurbished"
            ]
        },
        "hazardous": {
            "name": "Hazardous Waste",
            "emoji": "☣️",
            "recyclable": False,
            "decomposition_years": "Indefinite",
            "recycling_tips": [
                "Never dispose in regular trash",
                "Find designated collection points",
                "Store safely at home",
                "Contact local waste authority"
            ],
            "alternatives": [
                "Eco-friendly cleaners",
                "Natural pest control",
                "Water-based paints",
                "LED bulbs instead of CFL"
            ]
        }
    }
    
    @staticmethod
    def get_category_by_key(key):
        """Get category by key"""
        return WasteCategories.CATEGORIES.get(key)
    
    @staticmethod
    def get_all_categories():
        """Get all categories"""
        return WasteCategories.CATEGORIES

# ============================================================
# WASTE TRACKER
# ============================================================

class WasteTracker:
    """Track personal waste production"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.records = self._load_records()
    
    def _load_records(self):
        """Load waste records from session"""
        if "waste_records" not in st.session_state:
            st.session_state.waste_records = {}
        return st.session_state.waste_records.get(self.user_id, [])
    
    def save(self):
        """Save waste records"""
        st.session_state.waste_records[self.user_id] = self.records
    
    def add_record(self, category, weight_kg, date=None):
        """Add a waste record"""
        if date is None:
            date = datetime.now().isoformat()
        
        record = {
            "id": len(self.records) + 1,
            "category": category,
            "weight_kg": weight_kg,
            "date": date,
            "timestamp": datetime.now().isoformat()
        }
        self.records.append(record)
        self.save()
        return record
    
    def get_summary(self):
        """Get waste summary statistics"""
        if not self.records:
            return {
                "total_weight": 0,
                "total_items": 0,
                "categories": {},
                "recyclable_percentage": 0,
                "avg_weight": 0
            }
        
        df = pd.DataFrame(self.records)
        total_weight = df['weight_kg'].sum()
        total_items = len(df)
        avg_weight = total_weight / total_items
        
        # Category breakdown
        category_breakdown = df.groupby('category')['weight_kg'].sum().to_dict()
        
        # Recyclable percentage
        recyclable_categories = [k for k, v in WasteCategories.CATEGORIES.items() if v['recyclable']]
        recyclable_weight = df[df['category'].isin(recyclable_categories)]['weight_kg'].sum()
        recyclable_percentage = (recyclable_weight / total_weight * 100) if total_weight > 0 else 0
        
        return {
            "total_weight": total_weight,
            "total_items": total_items,
            "categories": category_breakdown,
            "recyclable_percentage": recyclable_percentage,
            "avg_weight": avg_weight
        }
    
    def get_trend(self, days=30):
        """Get waste trend over time"""
        if not self.records:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.records)
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Filter last N days
        cutoff = datetime.now().date() - timedelta(days=days)
        df = df[df['date'] >= cutoff]
        
        # Daily totals
        daily_totals = df.groupby('date')['weight_kg'].sum().reset_index()
        return daily_totals

# ============================================================
# COMPOSTING CALCULATOR
# ============================================================

class CompostingCalculator:
    """Calculate composting benefits"""
    
    @staticmethod
    def calculate_benefits(organic_weight_kg):
        """Calculate composting benefits"""
        # CO2 saved per kg of organic waste composted
        co2_saved_kg = organic_weight_kg * 0.5  # Approximate
        
        # Methane avoided (methane is 25x more potent than CO2)
        methane_avoided_kg = organic_weight_kg * 0.1
        
        # Co2 equivalent of methane avoided
        methane_co2_equivalent = methane_avoided_kg * 25
        
        # Total CO2 equivalent saved
        total_co2_saved = co2_saved_kg + methane_co2_equivalent
        
        # Compost produced (approx 30% of input)
        compost_produced_kg = organic_weight_kg * 0.3
        
        # Fertilizer value (approx $0.50 per kg of compost)
        fertilizer_value = compost_produced_kg * 0.50
        
        # Trees equivalent (22kg CO2 per tree per year)
        trees_equivalent = total_co2_saved / 22
        
        return {
            "organic_waste_kg": organic_weight_kg,
            "co2_saved_kg": total_co2_saved,
            "compost_produced_kg": compost_produced_kg,
            "fertilizer_value_usd": fertilizer_value,
            "trees_equivalent": trees_equivalent,
            "methane_avoided_kg": methane_avoided_kg
        }

# ============================================================
# WASTE REDUCTION CHALLENGES
# ============================================================

class WasteReductionChallenges:
    """Waste reduction challenges for users"""
    
    CHALLENGES = [
        {
            "id": "wr1",
            "title": "Zero Plastic Day",
            "description": "Avoid all single-use plastic for one day",
            "target": "0 kg",
            "difficulty": "Medium",
            "days": 1
        },
        {
            "id": "wr2",
            "title": "Compost Starter",
            "description": "Start composting your organic waste",
            "target": "5 kg",
            "difficulty": "Easy",
            "days": 7
        },
        {
            "id": "wr3",
            "title": "Recycling Champion",
            "description": "Recycle 80% of your waste for a week",
            "target": "80%",
            "difficulty": "Medium",
            "days": 7
        },
        {
            "id": "wr4",
            "title": "Waste Free Week",
            "description": "Produce less than 1kg of waste in a week",
            "target": "1 kg",
            "difficulty": "Hard",
            "days": 7
        },
        {
            "id": "wr5",
            "title": "Upcycling Master",
            "description": "Upcycle 3 items instead of throwing them away",
            "target": "3 items",
            "difficulty": "Easy",
            "days": 14
        }
    ]
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.completed = self._load_completed()
    
    def _load_completed(self):
        """Load completed challenges"""
        if "waste_challenges" not in st.session_state:
            st.session_state.waste_challenges = {}
        return st.session_state.waste_challenges.get(self.user_id, [])
    
    def save(self):
        """Save challenges"""
        st.session_state.waste_challenges[self.user_id] = self.completed
    
    def complete_challenge(self, challenge_id):
        """Complete a challenge"""
        if challenge_id not in self.completed:
            self.completed.append(challenge_id)
            self.save()
            return True
        return False
    
    def get_progress(self):
        """Get challenge progress"""
        total = len(self.CHALLENGES)
        completed = len(self.completed)
        return {
            "total": total,
            "completed": completed,
            "progress": (completed / total * 100) if total > 0 else 0
        }

# ============================================================
# SMART WASTE RECOMMENDER
# ============================================================

class SmartWasteRecommender:
    """Recommend waste reduction strategies"""
    
    @staticmethod
    def get_recommendations(waste_data):
        """Get personalized waste reduction recommendations"""
        recommendations = []
        
        total_weight = waste_data.get("total_weight", 0)
        categories = waste_data.get("categories", {})
        
        # Check for high plastic usage
        if categories.get("plastic", 0) > 5:
            recommendations.append({
                "priority": "High",
                "title": "Reduce Plastic Usage",
                "action": "Switch to reusable alternatives for single-use plastics",
                "impact": "Can reduce plastic waste by 70%"
            })
        
        # Check for high organic waste
        if categories.get("organic", 0) > 10:
            recommendations.append({
                "priority": "High",
                "title": "Start Composting",
                "action": "Set up a home compost bin for organic waste",
                "impact": "Can reduce waste by 30% and create fertilizer"
            })
        
        # Check for high paper waste
        if categories.get("paper", 0) > 5:
            recommendations.append({
                "priority": "Medium",
                "title": "Go Digital",
                "action": "Switch to digital documents and online billing",
                "impact": "Can reduce paper waste by 80%"
            })
        
        # Check recycling rate
        recyclable_percentage = waste_data.get("recyclable_percentage", 0)
        if recyclable_percentage < 50:
            recommendations.append({
                "priority": "High",
                "title": "Improve Recycling",
                "action": "Learn proper recycling techniques for your area",
                "impact": "Can increase recycling rate by 40%"
            })
        
        return recommendations

# ============================================================
# RENDER FUNCTIONS
# ============================================================

def render_waste_manager():
    """Render the complete waste manager interface"""
    st.markdown("<div class='section-header'>♻️ Smart Waste Manager</div>", unsafe_allow_html=True)
    
    user_id = st.session_state.get("user_id", 1)
    
    # Initialize tracker
    if "waste_tracker" not in st.session_state:
        st.session_state.waste_tracker = WasteTracker(user_id)
    
    if "waste_challenges" not in st.session_state:
        st.session_state.waste_challenges = WasteReductionChallenges(user_id)
    
    tracker = st.session_state.waste_tracker
    challenges = st.session_state.waste_challenges
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Track Waste",
        "♻️ Recycling Guide",
        "🧑‍🌾 Composting",
        "🎯 Challenges"
    ])
    
    with tab1:
        render_waste_tracking(tracker)
    
    with tab2:
        render_recycling_guide()
    
    with tab3:
        render_composting_calculator()
    
    with tab4:
        render_waste_challenges(challenges)

def render_waste_tracking(tracker):
    """Render waste tracking interface"""
    st.markdown("### 📊 Track Your Waste")
    
    # Add new record
    with st.expander("➕ Add Waste Record", expanded=False):
        with st.form("waste_record_form"):
            col1, col2 = st.columns(2)
            with col1:
                category = st.selectbox(
                    "Waste Category",
                    list(WasteCategories.CATEGORIES.keys()),
                    format_func=lambda x: WasteCategories.CATEGORIES[x]['name']
                )
                weight = st.number_input("Weight (kg)", min_value=0.01, value=1.0, step=0.1)
            with col2:
                date = st.date_input("Date", datetime.now())
            
            if st.form_submit_button("Add Record"):
                tracker.add_record(category, weight, date.isoformat())
                st.success("✅ Waste record added!")
                st.rerun()
    
    # Display summary
    summary = tracker.get_summary()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Waste", f"{summary['total_weight']:.1f} kg")
    col2.metric("Records", f"{summary['total_items']}")
    col3.metric("Recyclable", f"{summary['recyclable_percentage']:.0f}%")
    col4.metric("Avg per Record", f"{summary['avg_weight']:.2f} kg")
    
    # Category breakdown chart
    if summary['categories']:
        st.markdown("### 📊 Waste Breakdown")
        
        # Donut chart
        categories = summary['categories']
        fig = go.Figure(data=[go.Pie(
            labels=[WasteCategories.CATEGORIES[k]['name'] for k in categories.keys()],
            values=list(categories.values()),
            hole=0.4,
            marker=dict(colors=['#4ade80', '#fbbf24', '#f87171', '#60a5fa', '#a78bfa', '#f472b6'])
        )])
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    # Trend chart
    trend_data = tracker.get_trend()
    if not trend_data.empty:
        st.markdown("### 📈 Waste Trend")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_data['date'],
            y=trend_data['weight_kg'],
            mode='lines+markers',
            fill='tozeroy',
            name='Waste'
        ))
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    # Recommendations
    if summary['total_weight'] > 0:
        st.markdown("### 💡 Smart Recommendations")
        recommendations = SmartWasteRecommender.get_recommendations(summary)
        
        for rec in recommendations:
            color = "#ef4444" if rec['priority'] == "High" else "#fbbf24"
            st.markdown(f"""
            <div class='card' style='border-left: 4px solid {color};'>
                <div style='display: flex; align-items: start; gap: 12px;'>
                    <div style='font-size: 24px;'>{'🔴' if rec['priority'] == 'High' else '🟡'}</div>
                    <div>
                        <div style='font-weight: 700;'>{rec['title']}</div>
                        <div style='color: #6b7280; font-size: 14px;'>{rec['action']}</div>
                        <div style='color: #4ade80; font-size: 13px; margin-top: 4px;'>Impact: {rec['impact']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

def render_recycling_guide():
    """Render recycling guide"""
    st.markdown("### ♻️ Recycling Guide")
    
    # Search bar
    search = st.text_input("🔍 Search by category", placeholder="e.g., plastic, glass...")
    
    # Display categories
    categories = WasteCategories.get_all_categories()
    
    for key, category in categories.items():
        if search and search.lower() not in category['name'].lower() and search.lower() not in key:
            continue
            
        with st.expander(f"{category['emoji']} {category['name']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**♻️ Recycling Information**")
                st.write(f"Recyclable: {'✅ Yes' if category['recyclable'] else '❌ No'}")
                st.write(f"Decomposition: {category['decomposition_years']} years")
                
                st.markdown("**💡 Recycling Tips:**")
                for tip in category['recycling_tips']:
                    st.write(f"• {tip}")
            
            with col2:
                st.markdown("**🌿 Eco-Friendly Alternatives:**")
                for alt in category['alternatives']:
                    st.write(f"• {alt}")

def render_composting_calculator():
    """Render composting calculator"""
    st.markdown("### 🧑‍🌾 Composting Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Enter your organic waste amount**")
        organic_waste = st.number_input("Organic waste per week (kg)", min_value=0.0, value=5.0, step=0.5)
        
        if st.button("Calculate Benefits", use_container_width=True):
            benefits = CompostingCalculator.calculate_benefits(organic_waste)
            
            # Display results
            st.markdown("---")
            st.markdown("### 📊 Your Composting Impact")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("CO₂ Saved", f"{benefits['co2_saved_kg']:.1f} kg")
            col2.metric("Compost Produced", f"{benefits['compost_produced_kg']:.1f} kg")
            col3.metric("Trees Equivalent", f"{benefits['trees_equivalent']:.1f}")
            
            st.markdown(f"""
            <div style='padding: 15px; border-radius: 10px; background: #f0fdf4; border-left: 4px solid #4ade80;'>
                <p style='margin: 0; font-size: 15px;'>
                    🌱 By composting {organic_waste} kg of organic waste per week, 
                    you're saving <strong>{benefits['co2_saved_kg']:.1f} kg of CO₂</strong> equivalent 
                    and creating <strong>{benefits['compost_produced_kg']:.1f} kg</strong> of nutrient-rich compost!
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 🌱 Composting Tips")
        
        tips = [
            "Start with a small bin and gradually increase",
            "Balance green (food scraps) and brown (leaves) materials",
            "Keep compost moist but not wet",
            "Turn your compost every 2-3 weeks",
            "Add worms for faster decomposition",
            "Use compost in your garden or houseplants"
        ]
        
        for i, tip in enumerate(tips, 1):
            st.write(f"{i}. {tip}")

def render_waste_challenges(challenges):
    """Render waste reduction challenges"""
    st.markdown("### 🎯 Waste Reduction Challenges")
    
    # Progress
    progress = challenges.get_progress()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Challenges", progress['total'])
    col2.metric("Completed", progress['completed'])
    col3.metric("Progress", f"{progress['progress']:.0f}%")
    
    st.progress(progress['progress'] / 100)
    
    # Display challenges
    for challenge in WasteReductionChallenges.CHALLENGES:
        with st.container():
            is_completed = challenge['id'] in challenges.completed
            
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                status = "✅" if is_completed else "⬜"
                st.markdown(f"{status} **{challenge['title']}**")
                st.caption(challenge['description'])
                st.caption(f"🎯 Target: {challenge['target']} • {challenge['difficulty']} • {challenge['days']} days")
            
            with col2:
                st.markdown(f"<div style='text-align: center; margin-top: 15px;'>", unsafe_allow_html=True)
                if not is_completed:
                    if st.button("Complete", key=f"complete_waste_{challenge['id']}"):
                        challenges.complete_challenge(challenge['id'])
                        st.success("🎉 Challenge completed!")
                        st.rerun()
                else:
                    st.markdown("✅ **Done!**")
                st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("---")

# ============================================================
# INTEGRATION
# ============================================================

def render_waste_hub():
    """Render the complete waste hub"""
    render_waste_manager()

# ============================================================
# SAMPLE USAGE
# ============================================================

"""
# Add to app.py:

# Import
from waste_manager import render_waste_hub

# Add as a new tab
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "🌍 Carbon Footprint",
    "⚡ Home Energy Audit",
    "🎮 Gamification",
    "🗺️ Route Planning & Offsets",
    "🏆 Community Leaderboard",
    "🔮 Future Self",
    "🌿 Sustainability Hub",
    "🌍 Eco-Social",
    "📖 Eco-Stories",
    "♻️ Waste Manager"  # NEW
])

with tab10:
    render_waste_hub()
"""