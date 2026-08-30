"""
Eco Quests Page for EcoBuddy AI
Displays daily, weekly, monthly quests and progress tracking.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional

from src.lib.gamification_v2 import (
    get_gamification_v2,
    get_user_level,
    get_user_coins,
    get_gamification_stats,
    accept_quest,
    update_quest_progress
)
from src.lib.quest_manager import get_quest_manager, get_user_quests
from src.lib.achievement_tracker import get_achievement_tracker, get_unlocked_achievements


def render_eco_quests(user_id: Optional[int] = None):
    """Render the eco quests page."""
    
    if not user_id:
        st.warning("Please log in to access quests.")
        return
    
    st.markdown("""
    <style>
        .quest-card {
            background: rgba(15, 23, 42, 0.8);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(74, 222, 128, 0.2);
            margin-bottom: 16px;
            transition: all 0.3s ease;
        }
        .quest-card:hover {
            border-color: rgba(74, 222, 128, 0.5);
            transform: translateY(-2px);
        }
        .quest-card.completed {
            border-color: rgba(74, 222, 128, 0.5);
            background: rgba(74, 222, 128, 0.05);
        }
        .quest-title {
            font-size: 17px;
            font-weight: 700;
            color: #e5e7eb;
        }
        .quest-description {
            color: #94a3b8;
            font-size: 14px;
            margin-top: 4px;
        }
        .quest-meta {
            display: flex;
            gap: 12px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        .quest-meta-item {
            background: rgba(74, 222, 128, 0.1);
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            color: #4ade80;
        }
        .quest-meta-item.xp {
            background: rgba(251, 191, 36, 0.15);
            color: #fbbf24;
        }
        .quest-meta-item.coins {
            background: rgba(251, 191, 36, 0.15);
            color: #fbbf24;
        }
        .level-progress {
            background: rgba(15, 23, 42, 0.6);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 20px;
            border: 1px solid rgba(74, 222, 128, 0.15);
        }
        .level-title {
            font-size: 24px;
            font-weight: 800;
            color: #4ade80;
        }
        .level-rank {
            font-size: 16px;
            color: #94a3b8;
        }
        .achievement-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin: 2px;
        }
        .badge-bronze { background: rgba(205, 127, 50, 0.3); color: #cd7f32; }
        .badge-silver { background: rgba(192, 192, 192, 0.3); color: #c0c0c0; }
        .badge-gold { background: rgba(255, 215, 0, 0.3); color: #ffd700; }
        .badge-platinum { background: rgba(229, 228, 226, 0.3); color: #e5e4e2; }
        .badge-diamond { background: rgba(185, 242, 255, 0.3); color: #b9f2ff; }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0f172a, #1a2e1a); padding: 30px 40px; border-radius: 20px; margin-bottom: 30px; border: 1px solid rgba(74, 222, 128, 0.2);">
        <h1 style="color: #4ade80; font-size: 36px; font-weight: 800; margin: 0;">🎮 Eco Quests</h1>
        <p style="color: #94a3b8; font-size: 16px; margin-top: 8px;">Complete quests, earn XP and coins, and level up your eco journey!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # User stats
    stats = get_gamification_stats(user_id)
    level = get_user_level(user_id)
    coins = get_user_coins(user_id)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Level", stats.get('level', 1))
    with col2:
        st.metric("XP", f"{stats.get('xp', 0)}/{stats.get('xp_to_next', 100)}")
    with col3:
        st.metric("Coins", f"🪙 {coins}")
    with col4:
        st.metric("Rank", stats.get('rank', 'Novice'))
    with col5:
        st.metric("Active Quests", stats.get('active_quests', 0))
    
    # Level progress
    if level:
        progress_pct = (level.xp / level.xp_to_next) * 100 if level.xp_to_next > 0 else 0
        st.markdown(f"""
        <div class="level-progress">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span class="level-title">Level {level.level}</span>
                    <span class="level-rank"> - {level.rank}</span>
                </div>
                <div style="text-align: right;">
                    <div style="color: #94a3b8; font-size: 14px;">{level.xp} / {level.xp_to_next} XP</div>
                    <div style="width: 200px; height: 6px; background: rgba(74, 222, 128, 0.15); border-radius: 10px; overflow: hidden; margin-top: 4px;">
                        <div style="width: {progress_pct:.1f}%; height: 100%; background: linear-gradient(90deg, #4ade80, #22c55e); border-radius: 10px;"></div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔥 Available Quests",
        "📊 My Quests",
        "🏅 Achievements",
        "🪙 Shop"
    ])
    
    with tab1:
        render_available_quests(user_id)
    
    with tab2:
        render_my_quests(user_id)
    
    with tab3:
        render_achievements(user_id)
    
    with tab4:
        render_shop(user_id)


def render_available_quests(user_id: int):
    """Render available quests."""
    st.markdown("### 🔥 Available Quests")
    
    gamification = get_gamification_v2()
    quests = gamification.get_available_quests(user_id)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.selectbox(
            "Quest Type",
            options=["All", "Daily", "Weekly", "Monthly", "Special", "Story", "Boss"],
            key="quest_type_filter"
        )
    with col2:
        filter_difficulty = st.selectbox(
            "Difficulty",
            options=["All", "Easy", "Medium", "Hard", "Epic", "Legendary"],
            key="quest_difficulty_filter"
        )
    with col3:
        filter_category = st.selectbox(
            "Category",
            options=["All", "assessment", "footprint", "transport", "diet", "energy", "waste", "story", "special"],
            key="quest_category_filter"
        )
    
    # Apply filters
    if filter_type != "All":
        quests = [q for q in quests if q.type.value == filter_type.lower()]
    if filter_difficulty != "All":
        quests = [q for q in quests if q.difficulty.value == filter_difficulty.lower()]
    if filter_category != "All":
        quests = [q for q in quests if q.category == filter_category]
    
    if not quests:
        st.info("No quests available. Check back later for new quests!")
        return
    
    for quest in quests:
        difficulty_colors = {
            'easy': '#4ade80',
            'medium': '#fbbf24',
            'hard': '#f97316',
            'epic': '#ef4444',
            'legendary': '#8b5cf6'
        }
        color = difficulty_colors.get(quest.difficulty.value, '#94a3b8')
        
        st.markdown(f"""
        <div class="quest-card">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="flex: 1;">
                    <div class="quest-title">{quest.icon} {quest.title}</div>
                    <div class="quest-description">{quest.description}</div>
                    <div class="quest-meta">
                        <span class="quest-meta-item">📂 {quest.type.value.title()}</span>
                        <span class="quest-meta-item" style="border-left: 2px solid {color}; color: {color};">{quest.difficulty.value.title()}</span>
                        <span class="quest-meta-item">🏷️ {quest.category}</span>
                        <span class="quest-meta-item xp">⭐ {quest.xp_reward} XP</span>
                        <span class="quest-meta-item coins">🪙 {quest.coin_reward} coins</span>
                        <span class="quest-meta-item">⏰ {quest.duration_days} days</span>
                    </div>
                </div>
                <div>
                    {f'<span style="background: rgba(59, 130, 246, 0.2); padding: 4px 12px; border-radius: 12px; font-size: 12px; color: #60a5fa;">🔒 Prereq</span>' if quest.prerequisites else ''}
                </div>
            </div>
            <button onclick="window.location.href='?accept={quest.id}'" style="margin-top: 12px; background: linear-gradient(135deg, #4ade80, #22c55e); border: none; color: #0f172a; padding: 8px 24px; border-radius: 8px; font-weight: 600; cursor: pointer;">
                Accept Quest
            </button>
        </div>
        """, unsafe_allow_html=True)
        
        # Handle accept
        query_params = st.query_params
        if query_params.get('accept') == quest.id:
            if accept_quest(user_id, quest.id):
                st.success(f"✅ Quest '{quest.title}' accepted!")
                st.rerun()
            else:
                st.error("Failed to accept quest.")


def render_my_quests(user_id: int):
    """Render user's active quests."""
    st.markdown("### 📊 My Quests")
    
    gamification = get_gamification_v2()
    active_quests = gamification.get_active_quests(user_id)
    completed_quests = gamification.get_completed_quests(user_id)
    
    if not active_quests and not completed_quests:
        st.info("You haven't accepted any quests yet. Check the Available Quests tab!")
        return
    
    # Active quests
    if active_quests:
        st.markdown("#### 🔥 In Progress")
        for user_quest in active_quests:
            quest = gamification.get_quest(user_quest.quest_id)
            if not quest:
                continue
            
            st.markdown(f"""
            <div class="quest-card">
                <div class="quest-title">{quest.icon} {quest.title}</div>
                <div class="quest-description">{quest.description}</div>
                <div style="margin-top: 10px;">
                    <div style="display: flex; justify-content: space-between; font-size: 13px; color: #94a3b8;">
                        <span>Progress</span>
                        <span>{user_quest.progress:.1f}%</span>
                    </div>
                    <div style="width: 100%; height: 8px; background: rgba(74, 222, 128, 0.15); border-radius: 10px; overflow: hidden; margin-top: 4px;">
                        <div style="width: {user_quest.progress:.1f}%; height: 100%; background: linear-gradient(90deg, #4ade80, #22c55e); border-radius: 10px;"></div>
                    </div>
                </div>
                <div class="quest-meta">
                    <span class="quest-meta-item">⭐ {quest.xp_reward} XP</span>
                    <span class="quest-meta-item">🪙 {quest.coin_reward} coins</span>
                    <span class="quest-meta-item">⏰ {max(0, (user_quest.expired_at - datetime.now()).days)} days left</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Completed quests
    if completed_quests:
        st.markdown("#### ✅ Completed")
        for user_quest in completed_quests[:5]:
            quest = gamification.get_quest(user_quest.quest_id)
            if not quest:
                continue
            
            st.markdown(f"""
            <div class="quest-card completed">
                <div class="quest-title">✅ {quest.icon} {quest.title}</div>
                <div class="quest-description">{quest.description}</div>
                <div class="quest-meta">
                    <span class="quest-meta-item">⭐ +{quest.xp_reward} XP</span>
                    <span class="quest-meta-item">🪙 +{quest.coin_reward} coins</span>
                    <span class="quest-meta-item" style="color: #4ade80;">Completed!</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_achievements(user_id: int):
    """Render user achievements."""
    st.markdown("### 🏅 Achievements")
    
    tracker = get_achievement_tracker()
    unlocked = get_unlocked_achievements(user_id)
    stats = tracker.get_achievement_stats(user_id)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Achievements", stats.get('total', 0))
    with col2:
        st.metric("Unlocked", stats.get('unlocked', 0))
    with col3:
        st.metric("Completion Rate", f"{stats.get('completion_rate', 0):.1f}%")
    
    st.markdown("---")
    
    if unlocked:
        st.markdown("#### 🏆 Unlocked Achievements")
        
        # Group by tier
        tier_order = ['diamond', 'platinum', 'gold', 'silver', 'bronze']
        for tier in tier_order:
            tier_achievements = []
            for ua in unlocked:
                achievement = tracker.get_achievement(ua.achievement_id)
                if achievement and achievement.tier.value == tier:
                    tier_achievements.append(achievement)
            
            if tier_achievements:
                st.markdown(f"##### {tier.title()} Tier")
                cols = st.columns(3)
                for i, achievement in enumerate(tier_achievements[:6]):
                    with cols[i % 3]:
                        st.markdown(f"""
                        <div style="background: rgba(15, 23, 42, 0.6); padding: 12px; border-radius: 10px; text-align: center; border: 1px solid rgba(74, 222, 128, 0.1); margin-bottom: 8px;">
                            <div style="font-size: 28px;">{achievement.icon}</div>
                            <div style="font-weight: 600; color: #e5e7eb; font-size: 13px;">{achievement.name}</div>
                            <div style="color: #94a3b8; font-size: 11px;">{achievement.description[:30]}...</div>
                            <div style="font-size: 11px; color: #4ade80; margin-top: 4px;">+{achievement.points} pts</div>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.info("Complete quests and challenges to unlock achievements!")


def render_shop(user_id: int):
    """Render the shop."""
    st.markdown("### 🪙 Eco Shop")
    
    coins = get_user_coins(user_id)
    st.metric("Your Coins", f"🪙 {coins}")
    
    st.markdown("---")
    
    # Shop items
    items = [
        {"id": "badge_1", "name": "Eco Badge", "icon": "🏅", "price": 50, "description": "Show off your eco commitment"},
        {"id": "badge_2", "name": "Green Badge", "icon": "🌿", "price": 100, "description": "Display your green lifestyle"},
        {"id": "title_1", "name": "Eco Warrior Title", "icon": "⚔️", "price": 150, "description": "Earn the Eco Warrior title"},
        {"id": "title_2", "name": "Green Guardian Title", "icon": "🛡️", "price": 250, "description": "Earn the Green Guardian title"},
        {"id": "theme_1", "name": "Dark Theme", "icon": "🌙", "price": 200, "description": "Unlock the dark theme"},
        {"id": "theme_2", "name": "Nature Theme", "icon": "🌳", "price": 300, "description": "Unlock the nature theme"},
        {"id": "avatar_1", "name": "Eco Avatar", "icon": "🧑‍🌾", "price": 400, "description": "Special eco avatar frame"},
        {"id": "avatar_2", "name": "Forest Avatar", "icon": "🌲", "price": 500, "description": "Forest-themed avatar frame"},
    ]
    
    cols = st.columns(3)
    for i, item in enumerate(items):
        with cols[i % 3]:
            st.markdown(f"""
            <div style="background: rgba(15, 23, 42, 0.6); padding: 16px; border-radius: 12px; text-align: center; border: 1px solid rgba(74, 222, 128, 0.15); margin-bottom: 12px;">
                <div style="font-size: 36px;">{item['icon']}</div>
                <div style="font-weight: 700; color: #e5e7eb; font-size: 14px;">{item['name']}</div>
                <div style="color: #94a3b8; font-size: 12px;">{item['description']}</div>
                <div style="margin-top: 8px; color: #fbbf24; font-weight: 600;">🪙 {item['price']}</div>
                <button onclick="window.location.href='?buy={item['id']}'" style="margin-top: 8px; background: rgba(74, 222, 128, 0.15); border: 1px solid rgba(74, 222, 128, 0.3); color: #4ade80; padding: 4px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px;">
                    Buy
                </button>
            </div>
            """, unsafe_allow_html=True)
            
            # Handle buy
            query_params = st.query_params
            if query_params.get('buy') == item['id']:
                if coins >= item['price']:
                    st.success(f"🎉 You purchased {item['name']}!")
                    # Deduct coins (in a real app, this would be persisted)
                    st.rerun()
                else:
                    st.error(f"❌ Not enough coins! Need {item['price']} coins.")


def main():
    """Main entry point."""
    user_id = st.session_state.get('user_id')
    render_eco_quests(user_id)


if __name__ == "__main__":
    main()