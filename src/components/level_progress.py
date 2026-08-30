"""
Level Progress Component for EcoBuddy AI
Renders level progress bar and stats in the sidebar.
"""

import streamlit as st
from typing import Optional

from src.lib.gamification_v2 import get_user_level, get_user_coins, get_gamification_stats


def render_level_progress(user_id: Optional[int] = None):
    """
    Render level progress widget.
    
    Args:
        user_id: User ID
    """
    if not user_id:
        return
    
    stats = get_gamification_stats(user_id)
    level = get_user_level(user_id)
    coins = get_user_coins(user_id)
    
    if not level:
        return
    
    progress_pct = (level.xp / level.xp_to_next) * 100 if level.xp_to_next > 0 else 0
    
    st.markdown("""
    <style>
        .level-widget {
            background: rgba(15, 23, 42, 0.6);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(74, 222, 128, 0.15);
        }
        .level-number {
            font-size: 28px;
            font-weight: 800;
            color: #4ade80;
        }
        .level-rank {
            font-size: 13px;
            color: #94a3b8;
        }
        .level-stats {
            display: flex;
            gap: 16px;
            margin-top: 8px;
        }
        .level-stat {
            font-size: 13px;
            color: #94a3b8;
        }
        .level-stat span {
            color: #e5e7eb;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="level-widget">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span class="level-number">Lv. {level.level}</span>
                <span class="level-rank"> - {level.rank}</span>
            </div>
            <div style="text-align: right;">
                <div style="color: #fbbf24; font-weight: 600;">🪙 {coins}</div>
            </div>
        </div>
        <div style="margin-top: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8;">
                <span>XP: {level.xp}</span>
                <span>{level.xp_to_next} to next level</span>
            </div>
            <div style="width: 100%; height: 6px; background: rgba(74, 222, 128, 0.15); border-radius: 10px; overflow: hidden; margin-top: 4px;">
                <div style="width: {progress_pct:.1f}%; height: 100%; background: linear-gradient(90deg, #4ade80, #22c55e); border-radius: 10px;"></div>
            </div>
        </div>
        <div class="level-stats">
            <div class="level-stat">🏆 <span>{stats.get('completed_quests', 0)}</span> quests</div>
            <div class="level-stat">🎯 <span>{stats.get('active_quests', 0)}</span> active</div>
            <div class="level-stat">⭐ <span>{stats.get('total_xp', 0)}</span> total XP</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_quick_quests(user_id: Optional[int] = None):
    """
    Render quick quest widget showing active quests.
    
    Args:
        user_id: User ID
    """
    if not user_id:
        return
    
    try:
        from src.lib.gamification_v2 import get_gamification_v2
        
        gamification = get_gamification_v2()
        active_quests = gamification.get_active_quests(user_id)
        
        st.markdown("### 📋 Active Quests")
        
        if active_quests:
            for quest in active_quests[:3]:
                q = gamification.get_quest(quest.quest_id)
                if q:
                    st.markdown(f"""
                    <div style="background: rgba(74, 222, 128, 0.05); padding: 6px 12px; border-radius: 6px; margin-bottom: 4px; border-left: 3px solid #4ade80;">
                        <div style="display: flex; justify-content: space-between; font-size: 13px;">
                            <span style="color: #e5e7eb;">{q.icon} {q.title[:20]}...</span>
                            <span style="color: #94a3b8; font-size: 11px;">{quest.progress:.0f}%</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            if len(active_quests) > 3:
                st.caption(f"... and {len(active_quests) - 3} more quests")
        else:
            st.caption("No active quests. Check the Quests page!")
            
    except Exception as e:
        st.caption("Quests unavailable")


def render_gamification_widgets(user_id: Optional[int] = None):
    """
    Render all gamification widgets together.
    
    Args:
        user_id: User ID
    """
    render_level_progress(user_id)
    st.markdown("---")
    render_quick_quests(user_id)