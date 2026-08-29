"""
Team Widget for EcoBuddy AI
Renders team information and quick actions in the sidebar.
"""

import streamlit as st
from typing import Optional

from src.lib.team_manager import get_team_manager, get_user_teams
from src.lib.challenge_manager import get_challenge_manager


def render_team_widget(user_id: Optional[int] = None):
    """
    Render the team widget in the sidebar.
    
    Args:
        user_id: User ID
    """
    if not user_id:
        return
    
    st.markdown("### 👥 Teams")
    
    team_manager = get_team_manager()
    teams = team_manager.get_user_teams(user_id)
    
    if teams:
        for team in teams[:3]:  # Show top 3 teams
            st.markdown(f"""
            <div style="background: rgba(74, 222, 128, 0.05); padding: 8px 12px; border-radius: 8px; margin-bottom: 6px; border-left: 3px solid #4ade80;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 600; color: #e5e7eb; font-size: 13px;">{team.name}</span>
                    <span style="font-size: 11px; color: #94a3b8;">👥 {len(team.members)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if len(teams) > 3:
            st.caption(f"... and {len(teams) - 3} more teams")
    else:
        st.caption("No teams yet. Create or join one!")
    
    # Quick actions
    st.markdown("---")
    st.markdown("### 🚀 Quick Actions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏆 Challenges", use_container_width=True):
            st.switch_page("pages/11_Community_Challenges.py")
    with col2:
        if st.button("👥 Teams", use_container_width=True):
            st.switch_page("pages/11_Community_Challenges.py")


def render_team_leaderboard_widget(limit: int = 5):
    """
    Render team leaderboard widget.
    
    Args:
        limit: Number of teams to show
    """
    st.markdown("### 🏆 Top Teams")
    
    try:
        from src.lib.leaderboard_engine import get_team_leaderboard, LeaderboardPeriod
        
        entries = get_team_leaderboard(period=LeaderboardPeriod.ALL_TIME, limit=limit)
        
        if entries:
            for entry in entries:
                medal = "🥇" if entry.rank == 1 else "🥈" if entry.rank == 2 else "🥉" if entry.rank == 3 else f"#{entry.rank}"
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; padding: 4px 8px; border-radius: 4px; margin-bottom: 2px;">
                    <span style="font-size: 13px;">{medal} {entry.team_name}</span>
                    <span style="font-size: 12px; color: #fbbf24;">{entry.score:.1f}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No teams on the leaderboard yet.")
            
    except Exception as e:
        st.caption("Leaderboard unavailable")


def render_challenge_widget(user_id: Optional[int] = None):
    """
    Render challenge widget showing active challenges.
    
    Args:
        user_id: User ID
    """
    st.markdown("### 🔥 Active Challenges")
    
    try:
        challenge_manager = get_challenge_manager()
        challenges = challenge_manager.get_active_challenges()
        
        if challenges:
            for challenge in challenges[:3]:
                is_joined = user_id in challenge.participants if user_id else False
                status = "✅" if is_joined else "🔓"
                
                st.markdown(f"""
                <div style="background: rgba(59, 130, 246, 0.05); padding: 8px 12px; border-radius: 8px; margin-bottom: 6px; border-left: 3px solid #3b82f6;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 500; color: #e5e7eb; font-size: 13px;">{status} {challenge.title[:20]}...</span>
                        <span style="font-size: 11px; color: #94a3b8;">{(challenge.end_date - datetime.now()).days}d</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            if len(challenges) > 3:
                st.caption(f"... and {len(challenges) - 3} more challenges")
        else:
            st.caption("No active challenges right now.")
            
    except Exception as e:
        st.caption("Challenge feed unavailable")


def render_community_widgets(user_id: Optional[int] = None):
    """
    Render all community widgets together.
    
    Args:
        user_id: User ID
    """
    render_team_widget(user_id)
    st.markdown("---")
    render_team_leaderboard_widget()
    st.markdown("---")
    render_challenge_widget(user_id)