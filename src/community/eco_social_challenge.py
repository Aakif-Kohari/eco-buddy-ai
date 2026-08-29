"""
Eco-Social Community Challenge System
Contributor: Community Developer
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import logging
import json
import time
import random
from collections import defaultdict
import hashlib
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================
# ENUMS AND CONSTANTS
# ============================================================

class ChallengeStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class ChallengeType(Enum):
    INDIVIDUAL = "individual"
    TEAM = "team"
    COMMUNITY = "community"

class ChallengeCategory(Enum):
    ENERGY = "energy"
    WASTE = "waste"
    TRANSPORT = "transport"
    WATER = "water"
    FOOD = "food"
    EDUCATION = "education"

class DifficultyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class NotificationType(Enum):
    CHALLENGE_CREATED = "challenge_created"
    CHALLENGE_STARTED = "challenge_started"
    PROGRESS_UPDATE = "progress_update"
    MILESTONE_REACHED = "milestone_reached"
    CHALLENGE_COMPLETED = "challenge_completed"
    TEAM_INVITATION = "team_invitation"

# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class Challenge:
    """Main challenge data structure"""
    id: str
    title: str
    description: str
    category: ChallengeCategory
    challenge_type: ChallengeType
    difficulty: DifficultyLevel
    status: ChallengeStatus
    created_by: int
    created_at: datetime
    start_date: datetime
    end_date: datetime
    goal_description: str
    goal_value: float
    unit: str
    current_progress: float = 0.0
    participants: List[int] = field(default_factory=list)
    teams: Dict[int, List[int]] = field(default_factory=dict)
    rewards: Dict[str, Any] = field(default_factory=dict)
    milestones: List[Dict] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    image_url: Optional[str] = None

@dataclass
class Team:
    """Team data structure"""
    id: str
    name: str
    description: str
    created_by: int
    created_at: datetime
    members: List[int]
    challenge_id: str
    current_progress: float = 0.0
    points: int = 0
    rank: int = 0

@dataclass
class ChallengeProgress:
    """Individual progress tracking"""
    user_id: int
    challenge_id: str
    progress_value: float
    last_update: datetime
    milestones_completed: List[str]
    time_spent: float
    streak_days: int

@dataclass
class Notification:
    """Notification data structure"""
    id: str
    user_id: int
    type: NotificationType
    message: str
    created_at: datetime
    read: bool
    action_url: str
    metadata: Dict[str, Any]

@dataclass
class SocialShare:
    """Social sharing data"""
    platform: str
    challenge_id: str
    user_id: int
    share_type: str
    created_at: datetime
    engagement_count: int
    share_url: str

# ============================================================
# CHALLENGE ENGINE
# ============================================================

class ChallengeEngine:
    """
    Core challenge management engine with creation, tracking, and completion
    """
    
    def __init__(self):
        self.challenges: Dict[str, Challenge] = {}
        self.progress: Dict[str, ChallengeProgress] = {}
        self.templates = self._initialize_templates()
        self._load_sample_challenges()
    
    def _initialize_templates(self) -> Dict:
        """Initialize pre-defined challenge templates"""
        return {
            "weekly_recycling": {
                "title": "Weekly Recycling Challenge",
                "description": "Reduce waste by properly recycling all recyclable materials for one week",
                "category": ChallengeCategory.WASTE,
                "difficulty": DifficultyLevel.BEGINNER,
                "goal_value": 7,
                "unit": "days",
                "tags": ["recycling", "waste", "beginner"]
            },
            "energy_week": {
                "title": "Energy Reduction Week",
                "description": "Reduce household energy consumption by 15% over one week",
                "category": ChallengeCategory.ENERGY,
                "difficulty": DifficultyLevel.INTERMEDIATE,
                "goal_value": 15,
                "unit": "%",
                "tags": ["energy", "efficiency", "intermediate"]
            },
            "carbon_month": {
                "title": "Carbon Challenge Month",
                "description": "Reduce your carbon footprint by 20% through sustainable choices",
                "category": ChallengeCategory.TRANSPORT,
                "difficulty": DifficultyLevel.ADVANCED,
                "goal_value": 20,
                "unit": "%",
                "tags": ["carbon", "sustainable", "advanced"]
            },
            "water_conservation": {
                "title": "Water Conservation Challenge",
                "description": "Reduce water usage by 30% over two weeks",
                "category": ChallengeCategory.WATER,
                "difficulty": DifficultyLevel.INTERMEDIATE,
                "goal_value": 30,
                "unit": "%",
                "tags": ["water", "conservation", "intermediate"]
            },
            "zero_waste": {
                "title": "Zero Waste Month",
                "description": "Generate less than 1kg of non-recyclable waste per week",
                "category": ChallengeCategory.WASTE,
                "difficulty": DifficultyLevel.EXPERT,
                "goal_value": 4,
                "unit": "weeks",
                "tags": ["zero waste", "expert", "sustainability"]
            }
        }
    
    def _load_sample_challenges(self):
        """Load sample challenges for demo"""
        sample_challenges = [
            Challenge(
                id="ch_001",
                title="30-Day Plastic Free",
                description="Eliminate single-use plastics from your daily routine for 30 days",
                category=ChallengeCategory.WASTE,
                challenge_type=ChallengeType.INDIVIDUAL,
                difficulty=DifficultyLevel.INTERMEDIATE,
                status=ChallengeStatus.ACTIVE,
                created_by=1,
                created_at=datetime.now() - timedelta(days=5),
                start_date=datetime.now() - timedelta(days=5),
                end_date=datetime.now() + timedelta(days=25),
                goal_description="Complete 30 days without single-use plastics",
                goal_value=30,
                unit="days",
                current_progress=16.7,
                participants=[1, 2, 3, 4, 5],
                milestones=[
                    {"value": 7, "description": "One week completed!", "icon": "🌟"},
                    {"value": 14, "description": "Two weeks! Keep going!", "icon": "🎉"},
                    {"value": 21, "description": "Three weeks strong!", "icon": "💪"},
                    {"value": 30, "description": "Challenge complete! Amazing!", "icon": "🏆"}
                ],
                tags=["plastic-free", "sustainable", "30-day"]
            ),
            Challenge(
                id="ch_002",
                title="Green Commuter Challenge",
                description="Use sustainable transportation for 5 days per week",
                category=ChallengeCategory.TRANSPORT,
                challenge_type=ChallengeType.TEAM,
                difficulty=DifficultyLevel.INTERMEDIATE,
                status=ChallengeStatus.ACTIVE,
                created_by=2,
                created_at=datetime.now() - timedelta(days=10),
                start_date=datetime.now() - timedelta(days=10),
                end_date=datetime.now() + timedelta(days=20),
                goal_description="20 days of sustainable commuting",
                goal_value=20,
                unit="days",
                current_progress=50.0,
                participants=[2, 3, 4, 6, 7, 8],
                teams={
                    1: [2, 3, 4],
                    2: [6, 7, 8]
                },
                rewards={"badge": "Green Commuter", "xp": 200},
                milestones=[
                    {"value": 5, "description": "5 days! Great start!", "icon": "🚶"},
                    {"value": 10, "description": "Halfway there!", "icon": "🚲"},
                    {"value": 15, "description": "Almost there!", "icon": "🌿"},
                    {"value": 20, "description": "Amazing achievement!", "icon": "🏆"}
                ],
                tags=["commute", "transport", "green"]
            )
        ]
        
        for challenge in sample_challenges:
            self.challenges[challenge.id] = challenge
    
    def create_challenge(self, data: Dict) -> Challenge:
        """Create a new challenge"""
        challenge_id = hashlib.md5(
            f"{data['title']}_{datetime.now().timestamp()}".encode()
        ).hexdigest()[:8]
        
        challenge = Challenge(
            id=challenge_id,
            title=data['title'],
            description=data['description'],
            category=data['category'],
            challenge_type=data.get('challenge_type', ChallengeType.INDIVIDUAL),
            difficulty=data['difficulty'],
            status=ChallengeStatus.DRAFT,
            created_by=data['created_by'],
            created_at=datetime.now(),
            start_date=data['start_date'],
            end_date=data['end_date'],
            goal_description=data['goal_description'],
            goal_value=data['goal_value'],
            unit=data['unit'],
            milestones=data.get('milestones', []),
            tags=data.get('tags', []),
            image_url=data.get('image_url')
        )
        
        self.challenges[challenge_id] = challenge
        return challenge
    
    def update_progress(self, challenge_id: str, user_id: int, value: float):
        """Update user progress for a challenge"""
        if challenge_id not in self.challenges:
            raise ValueError(f"Challenge {challenge_id} not found")
        
        challenge = self.challenges[challenge_id]
        
        # Update progress
        progress_key = f"{user_id}_{challenge_id}"
        if progress_key not in self.progress:
            self.progress[progress_key] = ChallengeProgress(
                user_id=user_id,
                challenge_id=challenge_id,
                progress_value=0,
                last_update=datetime.now(),
                milestones_completed=[],
                time_spent=0,
                streak_days=0
            )
        
        progress = self.progress[progress_key]
        progress.progress_value = min(value, challenge.goal_value)
        progress.last_update = datetime.now()
        
        # Check milestones
        for milestone in challenge.milestones:
            if (progress.progress_value >= milestone['value'] and 
                milestone['value'] not in progress.milestones_completed):
                progress.milestones_completed.append(milestone['value'])
        
        # Update challenge progress
        all_progress = [p.progress_value for k, p in self.progress.items() 
                       if p.challenge_id == challenge_id]
        if all_progress:
            challenge.current_progress = sum(all_progress) / len(all_progress)
    
    def get_challenge_progress(self, challenge_id: str, user_id: int) -> Optional[ChallengeProgress]:
        """Get user progress for a challenge"""
        progress_key = f"{user_id}_{challenge_id}"
        return self.progress.get(progress_key)
    
    def complete_challenge(self, challenge_id: str):
        """Mark challenge as completed"""
        if challenge_id not in self.challenges:
            raise ValueError(f"Challenge {challenge_id} not found")
        
        challenge = self.challenges[challenge_id]
        challenge.status = ChallengeStatus.COMPLETED
        
        # Award rewards
        self._award_rewards(challenge)
    
    def _award_rewards(self, challenge: Challenge):
        """Award rewards to participants"""
        for user_id in challenge.participants:
            # Award XP
            if 'xp' in challenge.rewards:
                # Add XP to user's gamification profile
                pass
            
            # Award badge
            if 'badge' in challenge.rewards:
                # Add badge to user's achievement showcase
                pass
    
    def get_active_challenges(self) -> List[Challenge]:
        """Get all active challenges"""
        return [c for c in self.challenges.values() 
                if c.status == ChallengeStatus.ACTIVE]
    
    def get_challenge_template(self, template_id: str) -> Dict:
        """Get challenge template by ID"""
        return self.templates.get(template_id, {})
    
    def get_all_templates(self) -> Dict:
        """Get all challenge templates"""
        return self.templates

# ============================================================
# TEAM MANAGEMENT SYSTEM
# ============================================================

class TeamSystem:
    """
    Team creation, management, and collaboration features
    """
    
    def __init__(self):
        self.teams: Dict[str, Team] = {}
        self.team_invites: Dict[str, List[int]] = defaultdict(list)
    
    def create_team(self, name: str, description: str, created_by: int, 
                    challenge_id: str) -> Team:
        """Create a new team"""
        team_id = hashlib.md5(f"{name}_{datetime.now().timestamp()}".encode()).hexdigest()[:8]
        
        team = Team(
            id=team_id,
            name=name,
            description=description,
            created_by=created_by,
            created_at=datetime.now(),
            members=[created_by],
            challenge_id=challenge_id
        )
        
        self.teams[team_id] = team
        return team
    
    def join_team(self, team_id: str, user_id: int):
        """Join a team"""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")
        
        team = self.teams[team_id]
        if user_id not in team.members:
            team.members.append(user_id)
            # Remove invite if exists
            if user_id in self.team_invites.get(team_id, []):
                self.team_invites[team_id].remove(user_id)
    
    def leave_team(self, team_id: str, user_id: int):
        """Leave a team"""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")
        
        team = self.teams[team_id]
        if user_id in team.members:
            team.members.remove(user_id)
    
    def invite_to_team(self, team_id: str, user_id: int):
        """Send team invitation"""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")
        
        self.team_invites[team_id].append(user_id)
    
    def get_team_members(self, team_id: str) -> List[int]:
        """Get team members"""
        if team_id not in self.teams:
            return []
        return self.teams[team_id].members
    
    def get_team_leaderboard(self, challenge_id: str) -> List[Dict]:
        """Get team rankings for a challenge"""
        team_stats = []
        
        for team in self.teams.values():
            if team.challenge_id == challenge_id:
                total_progress = sum(
                    self._get_member_progress(member, challenge_id)
                    for member in team.members
                )
                average_progress = total_progress / len(team.members) if team.members else 0
                
                team_stats.append({
                    'team_id': team.id,
                    'team_name': team.name,
                    'members': len(team.members),
                    'average_progress': average_progress,
                    'rank': 0
                })
        
        # Sort by progress and assign ranks
        team_stats.sort(key=lambda x: x['average_progress'], reverse=True)
        for idx, stat in enumerate(team_stats):
            stat['rank'] = idx + 1
        
        return team_stats
    
    def _get_member_progress(self, user_id: int, challenge_id: str) -> float:
        """Get member's progress in a challenge"""
        # This would connect to challenge engine
        return random.uniform(10, 80)

# ============================================================
# SOCIAL SHARING AND ENGAGEMENT
# ============================================================

class SocialSharing:
    """
    Social media integration and achievement sharing
    """
    
    def __init__(self):
        self.shares: List[SocialShare] = []
        self.share_templates = {
            "challenge_start": "🌱 I just joined the {title} challenge on EcoBuddy! Join me in making a difference! #EcoBuddy #Sustainability",
            "milestone": "🎉 I reached {milestone} in the {title} challenge! {emoji} #EcoBuddy #SustainableLiving",
            "challenge_complete": "🏆 I completed the {title} challenge! It was {difficulty} but worth it! #EcoBuddy #ZeroWaste",
            "team_achievement": "🌟 Team {team_name} is crushing the {title} challenge! Join our team! #EcoBuddy #TeamWork"
        }
    
    def generate_share_text(self, share_type: str, data: Dict) -> str:
        """Generate shareable text based on type"""
        template = self.share_templates.get(share_type, "")
        try:
            return template.format(**data)
        except KeyError:
            return template
    
    def create_share(self, platform: str, challenge_id: str, user_id: int, 
                     share_type: str, data: Dict) -> SocialShare:
        """Create a social share"""
        share = SocialShare(
            platform=platform,
            challenge_id=challenge_id,
            user_id=user_id,
            share_type=share_type,
            created_at=datetime.now(),
            engagement_count=0,
            share_url=f"https://ecobuddy.ai/challenge/{challenge_id}"
        )
        self.shares.append(share)
        return share
    
    def get_engagement_stats(self, challenge_id: str) -> Dict:
        """Get sharing engagement statistics"""
        challenge_shares = [s for s in self.shares if s.challenge_id == challenge_id]
        
        return {
            'total_shares': len(challenge_shares),
            'by_platform': defaultdict(int, 
                {s.platform: sum(1 for s2 in challenge_shares if s2.platform == s.platform)
                 for s in challenge_shares}),
            'total_engagement': sum(s.engagement_count for s in challenge_shares)
        }

# ============================================================
# NOTIFICATION SYSTEM
# ============================================================

class NotificationSystem:
    """
    Automated notification and reminder system
    """
    
    def __init__(self):
        self.notifications: Dict[int, List[Notification]] = defaultdict(list)
        self.notification_counter = 0
    
    def create_notification(self, user_id: int, type: NotificationType, 
                           message: str, action_url: str = "", 
                           metadata: Dict = None) -> Notification:
        """Create a new notification"""
        notification = Notification(
            id=f"notif_{self.notification_counter}",
            user_id=user_id,
            type=type,
            message=message,
            created_at=datetime.now(),
            read=False,
            action_url=action_url,
            metadata=metadata or {}
        )
        self.notification_counter += 1
        self.notifications[user_id].append(notification)
        return notification
    
    def get_unread_count(self, user_id: int) -> int:
        """Get unread notification count"""
        return sum(1 for n in self.notifications.get(user_id, []) if not n.read)
    
    def mark_as_read(self, user_id: int, notification_id: str):
        """Mark a notification as read"""
        for notification in self.notifications.get(user_id, []):
            if notification.id == notification_id:
                notification.read = True
                break
    
    def get_notifications(self, user_id: int, limit: int = 20) -> List[Notification]:
        """Get notifications for a user"""
        user_notifications = self.notifications.get(user_id, [])
        return sorted(user_notifications, key=lambda x: x.created_at, reverse=True)[:limit]

# ============================================================
# MAIN UI COMPONENT
# ============================================================

class EcoSocialChallengeUI:
    """
    Complete UI for the eco-social challenge system
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.challenge_engine = ChallengeEngine()
        self.team_system = TeamSystem()
        self.social_sharing = SocialSharing()
        self.notification_system = NotificationSystem()
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = "challenges"
        if 'selected_challenge' not in st.session_state:
            st.session_state.selected_challenge = None
        if 'show_create_challenge' not in st.session_state:
            st.session_state.show_create_challenge = False
    
    def render(self):
        """Render the complete UI"""
        st.markdown("""
        <style>
        .challenge-header {
            background: linear-gradient(135deg, #1a2e1a, #0f172a);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            border: 1px solid rgba(74, 222, 128, 0.3);
        }
        .challenge-header h2 {
            color: #4ade80;
            margin: 0;
        }
        .challenge-header p {
            color: #94a3b8;
            margin: 5px 0 0 0;
        }
        .challenge-card {
            background: #0f172a;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid rgba(74, 222, 128, 0.15);
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }
        .challenge-card:hover {
            border-color: #4ade80;
            transform: translateY(-2px);
        }
        .progress-bar-custom {
            height: 8px;
            background: rgba(74, 222, 128, 0.2);
            border-radius: 4px;
            overflow: hidden;
        }
        .progress-fill-custom {
            height: 100%;
            background: linear-gradient(90deg, #4ade80, #86efac);
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        .badge-category {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 5px;
        }
        .team-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            background: rgba(96, 165, 250, 0.2);
            color: #60a5fa;
        }
        .notification-badge {
            background: #ef4444;
            color: white;
            border-radius: 50%;
            padding: 2px 8px;
            font-size: 12px;
            margin-left: 5px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown("""
        <div class="challenge-header">
            <h2>🌍 Community Challenges</h2>
            <p>Join eco-challenges, compete with teams, and make a real impact together</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Main tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "🏆 Challenges",
            "👥 Teams",
            "📊 Leaderboard",
            "🔔 Notifications"
        ])
        
        with tab1:
            self._render_challenges_tab()
        
        with tab2:
            self._render_teams_tab()
        
        with tab3:
            self._render_leaderboard()
        
        with tab4:
            self._render_notifications()
    
    def _render_challenges_tab(self):
        """Render the challenges tab"""
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("➕ Create Challenge", use_container_width=True):
                st.session_state.show_create_challenge = not st.session_state.show_create_challenge
        
        with col1:
            # Filters
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            with filter_col1:
                category_filter = st.selectbox(
                    "Category",
                    ["All"] + [c.value.capitalize() for c in ChallengeCategory]
                )
            with filter_col2:
                difficulty_filter = st.selectbox(
                    "Difficulty",
                    ["All"] + [d.value.capitalize() for d in DifficultyLevel]
                )
            with filter_col3:
                status_filter = st.selectbox(
                    "Status",
                    ["All", "Active", "Upcoming", "Completed"]
                )
        
        # Show create challenge form
        if st.session_state.show_create_challenge:
            self._render_create_challenge_form()
        
        # Get challenges
        challenges = self.challenge_engine.get_active_challenges()
        
        # Apply filters
        if category_filter != "All":
            challenges = [c for c in challenges if c.category.value.capitalize() == category_filter]
        if difficulty_filter != "All":
            challenges = [c for c in challenges if c.difficulty.value.capitalize() == difficulty_filter]
        if status_filter != "All":
            challenges = [c for c in challenges if c.status.value.capitalize() == status_filter]
        
        # Display challenges
        if challenges:
            for challenge in challenges:
                self._render_challenge_card(challenge)
        else:
            st.info("No challenges available. Create one or check back later!")
    
    def _render_challenge_card(self, challenge: Challenge):
        """Render individual challenge card"""
        category_colors = {
            ChallengeCategory.ENERGY: "#fbbf24",
            ChallengeCategory.WASTE: "#4ade80",
            ChallengeCategory.TRANSPORT: "#60a5fa",
            ChallengeCategory.WATER: "#34d399",
            ChallengeCategory.FOOD: "#f472b6",
            ChallengeCategory.EDUCATION: "#a78bfa"
        }
        
        color = category_colors.get(challenge.category, "#94a3b8")
        
        with st.container():
            st.markdown(f"""
            <div class="challenge-card">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h3 style="color: #4ade80; margin: 0;">{challenge.title}</h3>
                        <p style="color: #94a3b8; margin: 5px 0;">{challenge.description}</p>
                    </div>
                    <div style="text-align: right;">
                        <span class="badge-category" style="background: {color}20; color: {color};">
                            {challenge.category.value.upper()}
                        </span>
                        <span class="badge-category" style="background: rgba(148, 163, 184, 0.2); color: #94a3b8;">
                            {challenge.difficulty.value.upper()}
                        </span>
                    </div>
                </div>
                
                <div style="margin: 10px 0;">
                    <div style="display: flex; justify-content: space-between; font-size: 13px; color: #94a3b8;">
                        <span>🎯 Goal: {challenge.goal_description}</span>
                        <span>⏱️ {challenge.start_date.strftime('%d %b')} - {challenge.end_date.strftime('%d %b %Y')}</span>
                    </div>
                    <div style="margin-top: 5px;">
                        <div class="progress-bar-custom">
                            <div class="progress-fill-custom" style="width: {challenge.current_progress}%;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8; margin-top: 3px;">
                            <span>{challenge.current_progress:.1f}% complete</span>
                            <span>{len(challenge.participants)} participants</span>
                        </div>
                    </div>
                </div>
                
                <div style="display: flex; gap: 8px; margin-top: 10px;">
                    {self._render_tags(challenge.tags)}
                </div>
                
                <div style="margin-top: 12px; display: flex; gap: 10px;">
                    <button style="background: #4ade80; color: #0f172a; border: none; padding: 6px 16px; border-radius: 8px; cursor: pointer; font-weight: 600;">
                        Join Challenge
                    </button>
                    <button style="background: transparent; color: #94a3b8; border: 1px solid #94a3b8; padding: 6px 16px; border-radius: 8px; cursor: pointer;">
                        Details
                    </button>
                    <button style="background: transparent; color: #60a5fa; border: 1px solid #60a5fa; padding: 6px 16px; border-radius: 8px; cursor: pointer;">
                        Share
                    </button>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_tags(self, tags: List[str]) -> str:
        """Render tags as HTML"""
        if not tags:
            return ""
        return "".join([
            f'<span style="background: rgba(74, 222, 128, 0.1); color: #4ade80; padding: 2px 10px; border-radius: 12px; font-size: 11px;">#{tag}</span>'
            for tag in tags
        ])
    
    def _render_create_challenge_form(self):
        """Render challenge creation form"""
        with st.expander("📝 Create New Challenge", expanded=True):
            with st.form("create_challenge_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    title = st.text_input("Challenge Title", placeholder="e.g., 30-Day Plastic Free")
                    description = st.text_area("Description", placeholder="Describe your challenge...")
                    category = st.selectbox("Category", [c.value.capitalize() for c in ChallengeCategory])
                    difficulty = st.selectbox("Difficulty", [d.value.capitalize() for d in DifficultyLevel])
                
                with col2:
                    start_date = st.date_input("Start Date", value=datetime.now())
                    end_date = st.date_input("End Date", value=datetime.now() + timedelta(days=30))
                    goal_value = st.number_input("Goal Value", min_value=1, value=30)
                    unit = st.text_input("Unit", placeholder="days, kg, %", value="days")
                    challenge_type = st.selectbox("Challenge Type", ["Individual", "Team", "Community"])
                
                tags = st.text_input("Tags (comma separated)", placeholder="sustainable, zero-waste, recycling")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.form_submit_button("✅ Create Challenge", use_container_width=True):
                        # Create challenge
                        challenge_data = {
                            'title': title,
                            'description': description,
                            'category': ChallengeCategory(category.lower()),
                            'difficulty': DifficultyLevel(difficulty.lower()),
                            'challenge_type': ChallengeType(challenge_type.lower()),
                            'created_by': self.user_id,
                            'start_date': start_date,
                            'end_date': end_date,
                            'goal_description': f"Complete {goal_value} {unit}",
                            'goal_value': goal_value,
                            'unit': unit,
                            'tags': [t.strip() for t in tags.split(',') if t.strip()],
                            'milestones': [
                                {"value": goal_value * 0.25, "description": "25% Complete", "icon": "🌟"},
                                {"value": goal_value * 0.5, "description": "Halfway There!", "icon": "🎉"},
                                {"value": goal_value * 0.75, "description": "Almost Done!", "icon": "💪"},
                                {"value": goal_value, "description": "Complete!", "icon": "🏆"}
                            ]
                        }
                        
                        challenge = self.challenge_engine.create_challenge(challenge_data)
                        st.success(f"✅ Challenge '{title}' created successfully!")
                        st.session_state.show_create_challenge = False
                        time.sleep(1)
                        st.rerun()
                
                with col_btn2:
                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                        st.session_state.show_create_challenge = False
                        st.rerun()
    
    def _render_teams_tab(self):
        """Render teams tab"""
        st.subheader("👥 Teams")
        
        col1, col2 = st.columns([2, 1])
        
        with col2:
            if st.button("➕ Create Team", use_container_width=True):
                st.session_state.show_create_team = True
        
        with col1:
            # Team filters
            team_filter = st.selectbox("Filter by Challenge", ["All", "30-Day Plastic Free", "Green Commuter"])
        
        # Create team form
        if st.session_state.get('show_create_team', False):
            with st.expander("📝 Create New Team", expanded=True):
                with st.form("create_team_form"):
                    team_name = st.text_input("Team Name", placeholder="e.g., Eco Warriors")
                    team_description = st.text_area("Team Description", placeholder="Describe your team...")
                    challenge_select = st.selectbox("Select Challenge", ["30-Day Plastic Free", "Green Commuter"])
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.form_submit_button("✅ Create Team", use_container_width=True):
                            # Create team
                            team = self.team_system.create_team(
                                name=team_name,
                                description=team_description,
                                created_by=self.user_id,
                                challenge_id="ch_001"  # Example challenge ID
                            )
                            st.success(f"✅ Team '{team_name}' created successfully!")
                            st.session_state.show_create_team = False
                            st.rerun()
                    
                    with col_btn2:
                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                            st.session_state.show_create_team = False
                            st.rerun()
        
        # Display teams
        st.markdown("### 🏅 Active Teams")
        
        teams = [
            {"name": "Eco Warriors", "members": 5, "progress": 78, "rank": 1},
            {"name": "Green Avengers", "members": 4, "progress": 65, "rank": 2},
            {"name": "Sustainability Squad", "members": 6, "progress": 52, "rank": 3}
        ]
        
        for team in teams:
            st.markdown(f"""
            <div class="challenge-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="color: #4ade80; margin: 0;">👥 {team['name']}</h4>
                        <p style="color: #94a3b8; margin: 5px 0;">Members: {team['members']} | Rank: #{team['rank']}</p>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 20px; font-weight: 700; color: #4ade80;">{team['progress']}%</div>
                    </div>
                </div>
                <div class="progress-bar-custom">
                    <div class="progress-fill-custom" style="width: {team['progress']}%;"></div>
                </div>
                <div style="margin-top: 10px; display: flex; gap: 8px;">
                    <span class="team-badge">🔥 Active</span>
                    <span class="team-badge">📈 +12% this week</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_leaderboard(self):
        """Render leaderboard tab"""
        st.subheader("🏆 Community Leaderboard")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            challenge_filter = st.selectbox("Challenge", ["All", "30-Day Plastic Free", "Green Commuter"])
        with col2:
            period_filter = st.selectbox("Period", ["This Week", "This Month", "All Time"])
        with col3:
            team_filter = st.selectbox("View", ["Individual", "Teams"])
        
        # Leaderboard data
        if team_filter == "Teams":
            leaderboard_data = [
                {"rank": 1, "name": "Eco Warriors", "score": 1245, "members": 5, "badge": "🥇"},
                {"rank": 2, "name": "Green Avengers", "score": 1080, "members": 4, "badge": "🥈"},
                {"rank": 3, "name": "Sustainability Squad", "score": 890, "members": 6, "badge": "🥉"},
                {"rank": 4, "name": "Climate Champions", "score": 765, "members": 3, "badge": "🏅"},
                {"rank": 5, "name": "Zero Waste Heroes", "score": 620, "members": 4, "badge": "🏅"}
            ]
        else:
            leaderboard_data = [
                {"rank": 1, "name": "Sarah Green", "score": 580, "level": 12, "badge": "🥇"},
                {"rank": 2, "name": "Mike Earth", "score": 520, "level": 10, "badge": "🥈"},
                {"rank": 3, "name": "Emma Forest", "score": 490, "level": 9, "badge": "🥉"},
                {"rank": 4, "name": "Alex Green", "score": 460, "level": 8, "badge": "🏅"},
                {"rank": 5, "name": "Lisa Planet", "score": 430, "level": 8, "badge": "🏅"}
            ]
        
        # Display leaderboard
        for entry in leaderboard_data:
            rank_color = {
                "🥇": "#ffd700",
                "🥈": "#c0c0c0",
                "🥉": "#cd7f32",
                "🏅": "#94a3b8"
            }.get(entry['badge'], "#94a3b8")
            
            st.markdown(f"""
            <div style="background: #0f172a; padding: 12px 20px; border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span style="font-size: 24px;">{entry['badge']}</span>
                    <span style="font-weight: 600; color: #e5e7eb;">#{entry['rank']}</span>
                    <span style="color: #4ade80; font-weight: 600;">{entry['name']}</span>
                    {f'<span style="color: #94a3b8; font-size: 13px;">👥 {entry["members"]} members</span>' if "members" in entry else f'<span style="color: #94a3b8; font-size: 13px;">Level {entry["level"]}</span>'}
                </div>
                <div style="font-weight: 700; color: #4ade80; font-size: 18px;">
                    {entry['score']} pts
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Stats summary
        st.markdown("---")
        st.markdown("### 📊 Leaderboard Stats")
        
        stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
        with stats_col1:
            st.metric("Total Participants", "156", delta="+12")
        with stats_col2:
            st.metric("Active Challenges", "8", delta="+2")
        with stats_col3:
            st.metric("Total Points", "42,580", delta="+3,240")
        with stats_col4:
            st.metric("New This Week", "18", delta="+6")
    
    def _render_notifications(self):
        """Render notifications tab"""
        st.subheader("🔔 Notifications")
        
        # Notification filters
        col1, col2 = st.columns(2)
        with col1:
            filter_type = st.selectbox("Filter", ["All", "Unread", "Read"])
        with col2:
            st.markdown("&nbsp;")
            if st.button("📌 Mark All as Read", use_container_width=True):
                st.success("All notifications marked as read!")
        
        # Sample notifications
        notifications = [
            {"icon": "🏆", "title": "Challenge Completed!", "message": "You completed the 30-Day Plastic Free challenge!", "time": "2 hours ago", "read": False},
            {"icon": "🎯", "title": "Milestone Reached", "message": "You're halfway through the Green Commuter challenge!", "time": "5 hours ago", "read": False},
            {"icon": "👥", "title": "Team Invitation", "message": "Eco Warriors invited you to join their team", "time": "1 day ago", "read": True},
            {"icon": "🌟", "title": "New Challenge Available", "message": "Zero Waste Month challenge is now open!", "time": "2 days ago", "read": True},
            {"icon": "📊", "title": "Weekly Progress Report", "message": "You're in the top 10% of participants this week!", "time": "3 days ago", "read": True}
        ]
        
        # Apply filter
        if filter_type == "Unread":
            notifications = [n for n in notifications if not n['read']]
        elif filter_type == "Read":
            notifications = [n for n in notifications if n['read']]
        
        # Display notifications
        for notif in notifications:
            bg_color = "#1a2e2a" if not notif['read'] else "#0f172a"
            border_color = "#4ade80" if not notif['read'] else "transparent"
            
            st.markdown(f"""
            <div style="background: {bg_color}; padding: 15px 20px; border-radius: 10px; margin-bottom: 10px; border-left: 3px solid {border_color};">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="display: flex; gap: 12px;">
                        <span style="font-size: 24px;">{notif['icon']}</span>
                        <div>
                            <div style="font-weight: 600; color: #e5e7eb;">{notif['title']}</div>
                            <div style="color: #94a3b8; font-size: 14px;">{notif['message']}</div>
                            <div style="color: #64748b; font-size: 12px; margin-top: 4px;">{notif['time']}</div>
                        </div>
                    </div>
                    {f'<span style="background: #4ade80; color: #0f172a; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 600;">NEW</span>' if not notif['read'] else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if not notifications:
            st.info("No notifications to display.")

# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_eco_social_hub():
    """Main entry point for eco-social challenge system"""
    user_id = st.session_state.get('user_id', 1)
    
    # Initialize UI
    ui = EcoSocialChallengeUI(user_id)
    ui.render()

# ============================================================
# DATABASE HELPERS
# ============================================================

def init_challenge_db():
    """Initialize challenge database tables"""
    if 'challenge_db' not in st.session_state:
        st.session_state.challenge_db = {
            'challenges': [],
            'teams': [],
            'progress': [],
            'notifications': [],
            'shares': []
        }

def get_user_challenges(user_id: int) -> List[Dict]:
    """Get challenges for a user"""
    challenges = []
    if 'challenge_db' in st.session_state:
        for challenge in st.session_state.challenge_db['challenges']:
            if user_id in challenge.get('participants', []):
                challenges.append(challenge)
    return challenges

# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    st.set_page_config(page_title="Eco-Social Challenges", layout="wide")
    render_eco_social_hub()
