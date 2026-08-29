"""
Community Challenges Page for EcoBuddy AI
Displays and manages community challenges, teams, and leaderboards.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional

from src.lib.challenge_manager import (
    get_challenge_manager,
    get_challenge,
    get_active_challenges,
    join_challenge,
    update_challenge_progress,
    ChallengeStatus,
    ChallengeType,
    ChallengeCategory
)
from src.lib.team_manager import (
    get_team_manager,
    create_team,
    join_team,
    get_user_teams,
    TeamRole
)
from src.lib.leaderboard_engine import (
    get_leaderboard_engine,
    get_individual_leaderboard,
    get_team_leaderboard,
    LeaderboardPeriod
)


def render_community_challenges(user_id: Optional[int] = None):
    """Render the community challenges page."""
    
    if not user_id:
        st.warning("Please log in to participate in community challenges.")
        return
    
    st.markdown("""
    <style>
        .challenge-card {
            background: rgba(15, 23, 42, 0.8);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(74, 222, 128, 0.2);
            margin-bottom: 16px;
            transition: all 0.3s ease;
        }
        .challenge-card:hover {
            border-color: rgba(74, 222, 128, 0.5);
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
        }
        .challenge-title {
            font-size: 18px;
            font-weight: 700;
            color: #e5e7eb;
        }
        .challenge-description {
            color: #94a3b8;
            font-size: 14px;
            margin-top: 4px;
        }
        .challenge-meta {
            display: flex;
            gap: 16px;
            margin-top: 12px;
            flex-wrap: wrap;
        }
        .challenge-meta-item {
            background: rgba(74, 222, 128, 0.1);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            color: #4ade80;
        }
        .progress-container {
            margin-top: 12px;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(74, 222, 128, 0.15);
            border-radius: 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4ade80, #22c55e);
            border-radius: 10px;
            transition: width 0.5s ease;
        }
        .team-card {
            background: rgba(15, 23, 42, 0.6);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(74, 222, 128, 0.15);
            margin-bottom: 12px;
        }
        .team-card:hover {
            border-color: rgba(74, 222, 128, 0.3);
        }
        .leaderboard-entry {
            display: flex;
            align-items: center;
            padding: 10px 16px;
            border-radius: 10px;
            margin-bottom: 6px;
            transition: background 0.2s;
        }
        .leaderboard-entry:hover {
            background: rgba(74, 222, 128, 0.05);
        }
        .leaderboard-entry .rank {
            font-weight: 700;
            font-size: 16px;
            min-width: 40px;
            color: #4ade80;
        }
        .leaderboard-entry .name {
            flex: 1;
            color: #e5e7eb;
        }
        .leaderboard-entry .score {
            font-weight: 600;
            color: #fbbf24;
        }
        .leaderboard-entry.top-1 .rank { color: #fbbf24; font-size: 20px; }
        .leaderboard-entry.top-2 .rank { color: #94a3b8; font-size: 18px; }
        .leaderboard-entry.top-3 .rank { color: #d97706; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0f172a, #1a2e1a); padding: 30px 40px; border-radius: 20px; margin-bottom: 30px; border: 1px solid rgba(74, 222, 128, 0.2);">
        <h1 style="color: #4ade80; font-size: 36px; font-weight: 800; margin: 0;">🏆 Community Challenges</h1>
        <p style="color: #94a3b8; font-size: 16px; margin-top: 8px;">Join challenges, form teams, and compete with the community to make a positive environmental impact!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔥 Active Challenges",
        "👥 My Teams",
        "🏅 Leaderboards",
        "📊 My Progress"
    ])
    
    with tab1:
        render_active_challenges(user_id)
    
    with tab2:
        render_my_teams(user_id)
    
    with tab3:
        render_leaderboards()
    
    with tab4:
        render_my_progress(user_id)


def render_active_challenges(user_id: int):
    """Render active challenges section."""
    
    st.markdown("### 🔥 Active Challenges")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.selectbox(
            "Challenge Type",
            options=["All", "Individual", "Team", "Community", "Weekly", "Monthly", "Special"],
            key="challenge_type_filter"
        )
    with col2:
        filter_category = st.selectbox(
            "Category",
            options=["All", "Footprint", "Energy", "Transport", "Diet", "Waste", "Water", "Community", "Education"],
            key="challenge_category_filter"
        )
    with col3:
        show_joined = st.checkbox("Show only my challenges", key="show_joined_only")
    
    # Get challenges
    manager = get_challenge_manager()
    challenges = manager.get_active_challenges()
    
    # Apply filters
    if filter_type != "All":
        challenges = [c for c in challenges if c.type.value == filter_type.lower()]
    if filter_category != "All":
        challenges = [c for c in challenges if c.category.value == filter_category.lower()]
    if show_joined:
        user_challenges = manager.get_user_challenges(user_id)
        user_challenge_ids = [c.id for c in user_challenges]
        challenges = [c for c in challenges if c.id in user_challenge_ids]
    
    if not challenges:
        st.info("No active challenges match your filters. Check back soon for new challenges!")
        return
    
    for challenge in challenges:
        is_joined = user_id in challenge.participants
        user_progress = manager.get_user_progress(user_id, challenge.id)
        
        with st.container():
            st.markdown(f"""
            <div class="challenge-card">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex: 1;">
                        <div class="challenge-title">🏆 {challenge.title}</div>
                        <div class="challenge-description">{challenge.description}</div>
                        <div class="challenge-meta">
                            <span class="challenge-meta-item">📂 {challenge.type.value.title()}</span>
                            <span class="challenge-meta-item">🏷️ {challenge.category.value.title()}</span>
                            <span class="challenge-meta-item">👥 {len(challenge.participants)} participants</span>
                            <span class="challenge-meta-item">⏰ {(challenge.end_date - datetime.now()).days} days left</span>
                            <span class="challenge-meta-item">🎯 {challenge.target_value} {challenge.target_metric}</span>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        {f'<span style="background: rgba(74, 222, 128, 0.2); padding: 4px 12px; border-radius: 12px; font-size: 12px; color: #4ade80;">✅ Joined</span>' if is_joined else ''}
                    </div>
                </div>
                {f'''
                <div class="progress-container">
                    <div style="display: flex; justify-content: space-between; font-size: 13px; color: #94a3b8;">
                        <span>Progress</span>
                        <span>{user_progress.progress_value:.1f} / {challenge.target_value}</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {min((user_progress.progress_value / challenge.target_value) * 100, 100):.1f}%;"></div>
                    </div>
                </div>
                ''' if user_progress else ''}
                <div style="margin-top: 12px; display: flex; gap: 8px;">
                    {f'''
                    <button onclick="window.location.href='?join={challenge.id}'" style="background: linear-gradient(135deg, #4ade80, #22c55e); border: none; color: #0f172a; padding: 8px 20px; border-radius: 8px; font-weight: 600; cursor: pointer;">
                        Join Challenge
                    </button>
                    ''' if not is_joined else f'''
                    <button onclick="window.location.href='?progress={challenge.id}'" style="background: rgba(74, 222, 128, 0.15); border: 1px solid rgba(74, 222, 128, 0.3); color: #4ade80; padding: 8px 20px; border-radius: 8px; font-weight: 600; cursor: pointer;">
                        Update Progress
                    </button>
                    <button onclick="window.location.href='?leaderboard={challenge.id}'" style="background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #60a5fa; padding: 8px 20px; border-radius: 8px; font-weight: 600; cursor: pointer;">
                        View Leaderboard
                    </button>
                    '''}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Handle button actions
            query_params = st.query_params
            if query_params.get('join') == challenge.id:
                if join_challenge(challenge.id, user_id):
                    st.success(f"🎉 You've joined {challenge.title}!")
                    st.rerun()
                else:
                    st.error("Failed to join challenge.")
            
            if query_params.get('progress') == challenge.id:
                with st.expander("📝 Update Progress", expanded=True):
                    new_progress = st.number_input(
                        f"Current progress ({challenge.target_metric})",
                        min_value=0.0,
                        max_value=challenge.target_value,
                        value=user_progress.progress_value if user_progress else 0.0,
                        step=1.0,
                        key=f"progress_{challenge.id}"
                    )
                    if st.button("Update Progress", key=f"update_{challenge.id}"):
                        if update_challenge_progress(challenge.id, user_id, new_progress):
                            st.success("✅ Progress updated!")
                            st.rerun()
                        else:
                            st.error("Failed to update progress.")


def render_my_teams(user_id: int):
    """Render user's teams section."""
    
    st.markdown("### 👥 My Teams")
    
    manager = get_team_manager()
    teams = manager.get_user_teams(user_id)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if teams:
            for team in teams:
                is_captain = team.members.get(user_id, {}).role == TeamRole.CAPTAIN if user_id in team.members else False
                
                st.markdown(f"""
                <div class="team-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: 700; color: #e5e7eb; font-size: 16px;">{team.name}</div>
                            <div style="color: #94a3b8; font-size: 13px;">{team.description}</div>
                            <div style="display: flex; gap: 12px; margin-top: 8px; font-size: 12px; color: #64748b;">
                                <span>👥 {len(team.members)}/{team.max_members} members</span>
                                {f'<span style="color: #fbbf24;">👑 Captain</span>' if is_captain else ''}
                            </div>
                        </div>
                        <div>
                            <span style="background: rgba(74, 222, 128, 0.15); padding: 4px 12px; border-radius: 12px; font-size: 12px; color: #4ade80;">{team.status.value}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("You haven't joined any teams yet. Create one or join an existing team!")
    
    with col2:
        st.markdown("### 🚀 Create Team")
        with st.form("create_team_form"):
            team_name = st.text_input("Team Name", max_chars=50)
            team_description = st.text_area("Description", max_chars=200)
            max_members = st.number_input("Max Members", min_value=2, max_value=20, value=10)
            is_private = st.checkbox("Private Team")
            
            if st.form_submit_button("Create Team", use_container_width=True):
                if team_name and team_description:
                    team = create_team(
                        name=team_name,
                        description=team_description,
                        created_by=user_id,
                        max_members=max_members,
                        is_private=is_private
                    )
                    st.success(f"✅ Team '{team_name}' created successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in all fields.")


def render_leaderboards():
    """Render leaderboards section."""
    
    st.markdown("### 🏅 Leaderboards")
    
    leaderboard_tabs = st.tabs(["🏆 Individual", "👥 Teams"])
    
    with leaderboard_tabs[0]:
        col1, col2 = st.columns([2, 1])
        with col1:
            period = st.selectbox(
                "Time Period",
                options=[p.value for p in LeaderboardPeriod],
                key="lb_period"
            )
        with col2:
            limit = st.selectbox("Show", [10, 25, 50, 100], key="lb_limit")
        
        entries = get_individual_leaderboard(
            period=LeaderboardPeriod(period),
            limit=limit
        )
        
        if entries:
            for entry in entries:
                top_class = "top-1" if entry.rank == 1 else "top-2" if entry.rank == 2 else "top-3" if entry.rank == 3 else ""
                medal = "🥇" if entry.rank == 1 else "🥈" if entry.rank == 2 else "🥉" if entry.rank == 3 else f"#{entry.rank}"
                
                st.markdown(f"""
                <div class="leaderboard-entry {top_class}">
                    <div class="rank">{medal}</div>
                    <div class="name">{entry.username}</div>
                    <div class="score">{entry.score:.1f} pts</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No leaderboard data available.")
    
    with leaderboard_tabs[1]:
        col1, col2 = st.columns([2, 1])
        with col1:
            period = st.selectbox(
                "Time Period",
                options=[p.value for p in LeaderboardPeriod],
                key="lb_period_team"
            )
        with col2:
            limit = st.selectbox("Show", [10, 25, 50, 100], key="lb_limit_team")
        
        entries = get_team_leaderboard(
            period=LeaderboardPeriod(period),
            limit=limit
        )
        
        if entries:
            for entry in entries:
                medal = "🥇" if entry.rank == 1 else "🥈" if entry.rank == 2 else "🥉" if entry.rank == 3 else f"#{entry.rank}"
                
                st.markdown(f"""
                <div class="leaderboard-entry">
                    <div class="rank">{medal}</div>
                    <div class="name">{entry.team_name}</div>
                    <div class="score">{entry.score:.1f} pts</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No team leaderboard data available.")


def render_my_progress(user_id: int):
    """Render user's challenge progress section."""
    
    st.markdown("### 📊 My Challenge Progress")
    
    manager = get_challenge_manager()
    challenges = manager.get_user_challenges(user_id)
    
    if not challenges:
        st.info("You haven't joined any challenges yet. Join one to start tracking your progress!")
        return
    
    # Progress overview
    total_challenges = len(challenges)
    completed = sum(1 for c in challenges if user_id in c.completed_by)
    in_progress = total_challenges - completed
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Challenges", total_challenges)
    with col2:
        st.metric("Completed", completed)
    with col3:
        st.metric("In Progress", in_progress)
    
    st.markdown("---")
    
    # Detailed progress
    for challenge in challenges:
        progress = manager.get_user_progress(user_id, challenge.id)
        if progress:
            percentage = (progress.progress_value / challenge.target_value) * 100 if challenge.target_value > 0 else 0
            status = "✅ Completed" if progress.completed else f"⏳ {percentage:.1f}%"
            
            st.markdown(f"""
            <div class="challenge-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div class="challenge-title">{challenge.title}</div>
                        <div class="challenge-description">{challenge.description}</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: {'#4ade80' if progress.completed else '#fbbf24'}; font-weight: 600;">{status}</span>
                    </div>
                </div>
                <div class="progress-container">
                    <div style="display: flex; justify-content: space-between; font-size: 13px; color: #94a3b8;">
                        <span>{progress.progress_value:.1f} / {challenge.target_value} {challenge.target_metric}</span>
                        <span>{percentage:.1f}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {min(percentage, 100):.1f}%;"></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)


def main():
    """Main entry point for the community challenges page."""
    user_id = st.session_state.get('user_id')
    render_community_challenges(user_id)


if __name__ == "__main__":
    main()