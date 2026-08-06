# ============================================================
# FILE: story_generator.py
# EcoBuddy AI+ Impact Story Generator
# ============================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import json
import time

# ============================================================
# STORY GENERATOR
# ============================================================

class ImpactStoryGenerator:
    """Generate personalized environmental impact stories"""
    
    STORY_TEMPLATES = {
        "tree": {
            "title": "🌳 The Forest You're Saving",
            "template": "Every year, your sustainable choices help save {trees} trees. Over your lifetime, that's like creating a forest of {lifetime_trees} trees! This forest would cover an area of {area} square kilometers, providing habitat for countless species."
        },
        "ocean": {
            "title": "🌊 Protecting Our Oceans",
            "template": "Your plastic reduction efforts prevent {bottles} plastic bottles from entering the ocean. That's enough to fill {bathtubs} bathtubs! These actions help protect marine life and keep our oceans clean."
        },
        "energy": {
            "title": "⚡ Powering the Future",
            "template": "The energy you save each year could power {homes} homes for a full year. Over your lifetime, that's enough energy to power {lifetime_homes} homes, dramatically reducing our reliance on fossil fuels."
        },
        "water": {
            "title": "💧 Water Conservation Hero",
            "template": "You're saving {water_liters} liters of water annually. This is enough to fill {swimming_pools} swimming pools! Your water conservation efforts are helping preserve this precious resource for future generations."
        },
        "community": {
            "title": "👥 Community Impact",
            "template": "Your sustainable lifestyle inspires {people_inspired} people to make eco-friendly changes. That's like starting a movement! Together, your community is making a {impact} difference."
        }
    }
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.stories = self._load_stories()
    
    def _load_stories(self):
        """Load generated stories from session"""
        if "impact_stories" not in st.session_state:
            st.session_state.impact_stories = {}
        return st.session_state.impact_stories.get(self.user_id, [])
    
    def save(self):
        """Save stories to session"""
        st.session_state.impact_stories[self.user_id] = self.stories
    
    def generate_story(self, footprint_data):
        """Generate a personalized impact story"""
        total_footprint = footprint_data.get("total", 0)
        eco_score = footprint_data.get("eco_score", 50)
        
        # Calculate metrics
        trees_saved = max(1, int(total_footprint / 22))  # 22kg per tree
        lifetime_trees = trees_saved * 30  # 30 years of impact
        area_km2 = lifetime_trees * 0.000001  # Approximate area per tree
        
        # Energy savings
        energy_saved = int(total_footprint / 2)  # Approximate conversion
        homes_powered = max(1, int(energy_saved / 1000))
        lifetime_homes = homes_powered * 30
        
        # Water savings (liters)
        water_saved = int(total_footprint * 4)  # 4L per kg CO2
        swimming_pools = max(1, int(water_saved / 100000))  # 100k L per pool
        
        # Plastic bottles saved
        bottles_saved = int(total_footprint * 50)  # Approximate conversion
        bathtubs = max(1, int(bottles_saved / 100))  # 100 bottles per bathtub
        
        # Community impact
        people_inspired = max(1, int(eco_score / 2))
        impact_levels = ["small", "significant", "enormous", "revolutionary"]
        impact = random.choice(impact_levels[:max(1, int(eco_score / 25))])
        
        # Create story variations
        stories = []
        
        # Tree story
        stories.append({
            "type": "tree",
            "title": self.STORY_TEMPLATES["tree"]["title"],
            "content": self.STORY_TEMPLATES["tree"]["template"].format(
                trees=trees_saved,
                lifetime_trees=lifetime_trees,
                area=area_km2
            ),
            "emoji": "🌳",
            "value": trees_saved,
            "unit": "trees"
        })
        
        # Ocean story
        stories.append({
            "type": "ocean",
            "title": self.STORY_TEMPLATES["ocean"]["title"],
            "content": self.STORY_TEMPLATES["ocean"]["template"].format(
                bottles=bottles_saved,
                bathtubs=bathtubs
            ),
            "emoji": "🌊",
            "value": bottles_saved,
            "unit": "bottles"
        })
        
        # Energy story
        stories.append({
            "type": "energy",
            "title": self.STORY_TEMPLATES["energy"]["title"],
            "content": self.STORY_TEMPLATES["energy"]["template"].format(
                homes=homes_powered,
                lifetime_homes=lifetime_homes
            ),
            "emoji": "⚡",
            "value": homes_powered,
            "unit": "homes"
        })
        
        # Water story
        stories.append({
            "type": "water",
            "title": self.STORY_TEMPLATES["water"]["title"],
            "content": self.STORY_TEMPLATES["water"]["template"].format(
                water_liters=water_saved,
                swimming_pools=swimming_pools
            ),
            "emoji": "💧",
            "value": water_saved,
            "unit": "liters"
        })
        
        # Community story
        stories.append({
            "type": "community",
            "title": self.STORY_TEMPLATES["community"]["title"],
            "content": self.STORY_TEMPLATES["community"]["template"].format(
                people_inspired=people_inspired,
                impact=impact
            ),
            "emoji": "👥",
            "value": people_inspired,
            "unit": "people"
        })
        
        # Store with timestamp
        story_bundle = {
            "timestamp": datetime.now().isoformat(),
            "stories": stories,
            "metrics": {
                "total_footprint": total_footprint,
                "eco_score": eco_score,
                "trees_saved": trees_saved,
                "energy_saved": energy_saved,
                "water_saved": water_saved
            }
        }
        
        self.stories.append(story_bundle)
        self.save()
        
        return story_bundle
    
    def get_latest_story(self):
        """Get the most recent story"""
        if self.stories:
            return self.stories[-1]
        return None

# ============================================================
# TIMELINE GENERATOR
# ============================================================

class EcoTimelineGenerator:
    """Generate environmental impact timeline"""
    
    MILESTONES = [
        {"days": 1, "title": "🌱 First Step", "description": "Started your sustainability journey"},
        {"days": 7, "title": "🌿 One Week Green", "description": "Completed your first week of sustainable living"},
        {"days": 30, "title": "🌳 One Month Eco", "description": "One month of making a difference"},
        {"days": 90, "title": "🌍 Quarter Impact", "description": "Three months of positive change"},
        {"days": 180, "title": "🌟 Half Year Green", "description": "Six months of sustainable choices"},
        {"days": 365, "title": "🎉 One Year Eco", "description": "A full year of environmental impact!"}
    ]
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.history = self._load_history()
    
    def _load_history(self):
        """Load history from session"""
        if "eco_timeline" not in st.session_state:
            st.session_state.eco_timeline = {}
        return st.session_state.eco_timeline.get(self.user_id, [])
    
    def save(self):
        """Save timeline"""
        st.session_state.eco_timeline[self.user_id] = self.history
    
    def add_milestone(self, milestone_type, achievement):
        """Add a milestone to timeline"""
        milestone = {
            "type": milestone_type,
            "achievement": achievement,
            "timestamp": datetime.now().isoformat(),
            "days": len(self.history)
        }
        self.history.append(milestone)
        self.save()
        return milestone
    
    def get_timeline(self):
        """Get full timeline"""
        return self.history
    
    def get_milestone_progress(self, start_date):
        """Calculate milestone progress"""
        days_active = (datetime.now() - start_date).days
        
        milestones_reached = []
        for milestone in self.MILESTONES:
            if days_active >= milestone["days"]:
                milestones_reached.append(milestone)
        
        return {
            "total_milestones": len(self.MILESTONES),
            "reached": len(milestones_reached),
            "days_active": days_active,
            "next_milestone": self.MILESTONES[len(milestones_reached)] if len(milestones_reached) < len(self.MILESTONES) else None,
            "progress": (len(milestones_reached) / len(self.MILESTONES)) * 100
        }

# ============================================================
# SHAREABLE CARDS
# ============================================================

class ShareableCard:
    """Generate shareable social media cards"""
    
    @staticmethod
    def generate_impact_card(footprint, eco_score, story):
        """Generate a shareable impact card"""
        if eco_score >= 80:
            emoji = "🌟"
            level = "Eco Champion"
            color = "#4ade80"
        elif eco_score >= 60:
            emoji = "🌿"
            level = "Green Guardian"
            color = "#fbbf24"
        else:
            emoji = "🌱"
            level = "Eco Learner"
            color = "#f87171"
        
        card_html = f"""
        <div style='
            background: linear-gradient(135deg, #0f172a, #1e293b);
            border: 2px solid {color};
            border-radius: 16px;
            padding: 30px;
            max-width: 500px;
            margin: 0 auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        '>
            <div style='text-align: center;'>
                <div style='font-size: 48px;'>{emoji}</div>
                <h2 style='color: {color}; margin: 10px 0 5px;'>{level}</h2>
                <p style='color: #94a3b8; font-size: 14px;'>My Eco Impact</p>
            </div>
            
            <div style='
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin: 20px 0;
            '>
                <div style='
                    background: rgba(255,255,255,0.05);
                    border-radius: 10px;
                    padding: 15px;
                    text-align: center;
                '>
                    <div style='font-size: 24px; font-weight: 700; color: {color};'>
                        {footprint:.0f}
                    </div>
                    <div style='color: #94a3b8; font-size: 12px;'>kg CO₂ Saved</div>
                </div>
                
                <div style='
                    background: rgba(255,255,255,0.05);
                    border-radius: 10px;
                    padding: 15px;
                    text-align: center;
                '>
                    <div style='font-size: 24px; font-weight: 700; color: {color};'>
                        {eco_score}
                    </div>
                    <div style='color: #94a3b8; font-size: 12px;'>Eco Score</div>
                </div>
            </div>
            
            <div style='
                background: rgba(255,255,255,0.05);
                border-radius: 10px;
                padding: 15px;
                margin: 15px 0;
                font-size: 14px;
                color: #e5e7eb;
                text-align: center;
                border-left: 3px solid {color};
            '>
                "{story}"
            </div>
            
            <div style='
                text-align: center;
                font-size: 12px;
                color: #64748b;
                margin-top: 15px;
                border-top: 1px solid rgba(255,255,255,0.1);
                padding-top: 15px;
            '>
                🌍 EcoBuddy AI+ • {datetime.now().strftime("%B %Y")}
            </div>
        </div>
        """
        
        return card_html
    
    @staticmethod
    def render_shareable(card_html):
        """Render the shareable card in Streamlit"""
        st.markdown(card_html, unsafe_allow_html=True)
        
        # Share buttons (mock)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("📱 Share on Twitter", use_container_width=True)
        with col2:
            st.button("📘 Share on Facebook", use_container_width=True)
        with col3:
            st.button("📤 Download Image", use_container_width=True)

# ============================================================
# RENDER FUNCTIONS
# ============================================================

def render_impact_stories():
    """Render the impact stories section"""
    st.markdown("<div class='section-header'>📖 Your Impact Stories</div>", unsafe_allow_html=True)
    
    user_id = st.session_state.get("user_id", 1)
    
    # Initialize story generator
    if "story_gen" not in st.session_state:
        st.session_state.story_gen = ImpactStoryGenerator(user_id)
    
    story_gen = st.session_state.story_gen
    
    # Get assessment data
    history = get_assessments(user_id) if 'get_assessments' in globals() else []
    if history:
        latest = history[0]
        footprint_data = {
            "total": latest[7],
            "eco_score": latest[8]
        }
        
        # Generate new story button
        if st.button("✨ Generate New Impact Story", use_container_width=True):
            with st.spinner("Crafting your impact story..."):
                time.sleep(1)
                story_gen.generate_story(footprint_data)
                st.rerun()
        
        # Display latest story
        latest_story = story_gen.get_latest_story()
        if latest_story:
            st.markdown("### 🌟 Your Environmental Impact")
            
            # Display each story in a card
            for story in latest_story["stories"]:
                with st.container():
                    st.markdown(f"""
                    <div class='card-highlight'>
                        <div style='display: flex; align-items: center; gap: 15px;'>
                            <div style='font-size: 40px;'>{story['emoji']}</div>
                            <div>
                                <h4 style='margin: 0; color: #4ade80;'>{story['title']}</h4>
                                <p style='margin: 8px 0 0 0; color: #374151; font-size: 15px; line-height: 1.7;'>{story['content']}</p>
                                <div style='margin-top: 10px;'>
                                    <span style='background: rgba(74,222,128,0.15); padding: 4px 12px; border-radius: 20px; font-size: 13px; color: #4ade80;'>
                                        {story['value']} {story['unit']}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Generate shareable card
            st.markdown("---")
            st.markdown("### 📱 Share Your Impact")
            
            first_story = latest_story["stories"][0]
            card_html = ShareableCard.generate_impact_card(
                latest_story["metrics"]["total_footprint"],
                latest_story["metrics"]["eco_score"],
                first_story["content"][:100] + "..."
            )
            ShareableCard.render_shareable(card_html)
            
        else:
            st.info("Click 'Generate New Impact Story' to see your environmental impact in a whole new way!")
    else:
        st.warning("Complete a carbon footprint assessment first to generate your impact stories!")

def render_eco_timeline():
    """Render the eco-timeline"""
    st.markdown("### 🕒 Your Eco Journey Timeline")
    
    user_id = st.session_state.get("user_id", 1)
    
    if "timeline" not in st.session_state:
        st.session_state.timeline = EcoTimelineGenerator(user_id)
    
    timeline = st.session_state.timeline
    
    # Get first assessment date
    history = get_assessments(user_id) if 'get_assessments' in globals() else []
    if history:
        start_date = datetime.strptime(history[-1][1], "%Y-%m-%d %H:%M:%S")
        progress = timeline.get_milestone_progress(start_date)
        
        # Display progress
        col1, col2, col3 = st.columns(3)
        col1.metric("Days Active", f"{progress['days_active']} days")
        col2.metric("Milestones", f"{progress['reached']}/{progress['total_milestones']}")
        col3.metric("Progress", f"{progress['progress']:.0f}%")
        
        st.progress(progress['progress'] / 100)
        
        # Display milestones
        st.markdown("### 🏆 Your Milestones")
        
        # Show reached milestones
        for milestone in EcoTimelineGenerator.MILESTONES:
            if progress['days_active'] >= milestone['days']:
                st.success(f"✅ {milestone['title']} - {milestone['description']}")
            else:
                remaining = milestone['days'] - progress['days_active']
                st.info(f"⏳ {milestone['title']} - {remaining} days to go")
        
        # Timeline visualization
        st.markdown("### 📊 Journey Visualization")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[m["days"] for m in EcoTimelineGenerator.MILESTONES],
            y=[1] * len(EcoTimelineGenerator.MILESTONES),
            mode="markers+text",
            marker=dict(
                size=[20 if progress['days_active'] >= m["days"] else 15 for m in EcoTimelineGenerator.MILESTONES],
                color=["#4ade80" if progress['days_active'] >= m["days"] else "#64748b" for m in EcoTimelineGenerator.MILESTONES],
                symbol="star"
            ),
            text=[m["title"].split()[1] if len(m["title"].split()) > 1 else "✓" for m in EcoTimelineGenerator.MILESTONES],
            textposition="top center"
        ))
        fig.update_layout(
            height=200,
            showlegend=False,
            xaxis_title="Days",
            yaxis_title="",
            yaxis_showticklabels=False,
            margin=dict(l=0, r=0, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.info("Start your eco-journey by completing your first assessment!")

# ============================================================
# INTEGRATION
# ============================================================

def render_story_hub():
    """Render the complete story hub"""
    st.markdown("<div class='section-header'>📖 Eco-Story Hub</div>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📖 Impact Stories", "🕒 Eco Timeline"])
    
    with tab1:
        render_impact_stories()
    
    with tab2:
        render_eco_timeline()

# ============================================================
# SAMPLE USAGE
# ============================================================

"""
# Add to app.py:

# Import
from story_generator import render_story_hub

# Add as a new tab
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🌍 Carbon Footprint",
    "⚡ Home Energy Audit",
    "🎮 Gamification",
    "🗺️ Route Planning & Offsets",
    "🏆 Community Leaderboard",
    "🔮 Future Self",
    "🌿 Sustainability Hub",
    "🌍 Eco-Social",
    "📖 Eco-Stories"  # NEW
])

with tab9:
    render_story_hub()
"""