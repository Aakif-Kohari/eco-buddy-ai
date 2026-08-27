"""
Green Rewards Marketplace — Card Components
==============================================
Reusable Streamlit cards for rewards display, points dashboard, daily actions.
"""

import streamlit as st
from typing import Dict, Any, List, Optional

REWARDS_CSS = """
<style>
    .reward-card{background:linear-gradient(145deg,rgba(255,255,255,0.95),rgba(240,255,240,0.85));border:1px solid rgba(34,197,94,0.18);border-radius:16px;padding:20px;margin-bottom:12px;box-shadow:0 6px 24px rgba(0,0,0,0.05);transition:transform 0.2s;position:relative;overflow:hidden;}
    .reward-card:hover{transform:translateY(-3px);box-shadow:0 12px 36px rgba(34,197,94,0.12);}
    .reward-card.featured{border:2px solid rgba(34,197,94,0.3);background:linear-gradient(145deg,rgba(240,255,240,0.95),rgba(220,252,231,0.8));}
    .reward-card.featured::before{content:'⭐ Featured';position:absolute;top:12px;right:-24px;background:#22c55e;color:#fff;font-size:10px;font-weight:700;padding:3px 30px;transform:rotate(45deg);}
    .reward-icon{font-size:36px;}
    .reward-cost{display:inline-flex;align-items:center;gap:4px;padding:4px 12px;border-radius:20px;background:linear-gradient(135deg,rgba(34,197,94,0.15),rgba(34,197,94,0.05));font-size:13px;font-weight:700;color:#16a34a;}
    .points-display{text-align:center;padding:24px;background:linear-gradient(135deg,rgba(34,197,94,0.08),rgba(59,130,246,0.05));border-radius:16px;border:1px solid rgba(34,197,94,0.15);}
    .points-big{font-size:48px;font-weight:900;color:#16a34a;line-height:1;}
    .level-badge{display:inline-flex;align-items:center;gap:6px;padding:6px 16px;border-radius:24px;font-size:14px;font-weight:700;color:#fff;}
    .level-progress{width:100%;height:8px;border-radius:999px;background:rgba(0,0,0,0.06);overflow:hidden;margin:8px 0;}
    .level-fill{height:100%;border-radius:inherit;background:linear-gradient(90deg,#22c55e,#86efac);}
    .action-pill{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-radius:12px;border:1px solid rgba(0,0,0,0.06);margin-bottom:6px;background:rgba(255,255,255,0.6);transition:background 0.15s;}
    .action-pill:hover{background:rgba(34,197,94,0.06);}
    .action-pill.done{opacity:0.5;border-color:rgba(34,197,94,0.3);background:rgba(34,197,94,0.04);}
    .tx-row{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;border-radius:8px;margin-bottom:4px;font-size:13px;}
    .tx-earn{color:#16a34a;}
    .tx-spend{color:#ef4444;}
    @media(prefers-color-scheme:dark){
        .reward-card{background:linear-gradient(145deg,rgba(15,23,42,0.92),rgba(10,30,15,0.75));border-color:rgba(74,222,128,0.18);}
        .reward-card.featured{background:linear-gradient(145deg,rgba(13,36,25,0.8),rgba(10,30,15,0.6));}
        .points-big{color:#86efac;}
        .action-pill{background:rgba(30,41,59,0.7);border-color:rgba(148,163,184,0.12);}
        .tx-row{color:#e2e8f0;}
    }
</style>
"""

def inject_css():
    st.markdown(REWARDS_CSS, unsafe_allow_html=True)

def render_points_display(stats: Dict[str, Any]):
    level_info = stats.get("level_info", {})
    icon = level_info.get("icon", "🌱")
    color = level_info.get("color", "#22c55e")
    title = stats.get("title", "Eco Beginner")
    level = stats.get("level", 1)
    points = stats.get("points", 0)
    progress = stats.get("progress", 0)
    next_pts = stats.get("next_level_pts")
    st.markdown(f"""
    <div class="points-display">
        <div class="points-big">{points}</div>
        <div style="font-size:14px;color:#6b7280;font-weight:600;margin-top:4px;">Green Points</div>
        <div style="margin-top:12px;">
            <span class="level-badge" style="background:{color};">{icon} Level {level} — {title}</span>
        </div>
        {f"""<div class="level-progress" style="margin-top:12px;">
            <div class="level-fill" style="width:{progress}%;"></div>
        </div>
        <div style="font-size:11px;color:#9ca3af;">{stats.get('total_earned',0)} / {next_pts} pts to next level ({progress:.0f}%)</div>""" if next_pts else '<div style="font-size:12px;color:#f59e0b;margin-top:8px;">👑 Max Level Reached!</div>'}
    </div>""", unsafe_allow_html=True)

def render_reward_card(reward: Dict[str, Any], user_points: int = 0, can_afford: bool = False):
    featured = "featured" if reward.get("featured") else ""
    st.markdown(f"""
    <div class="reward-card {featured}">
        <div style="display:flex;gap:14px;align-items:flex-start;">
            <div class="reward-icon">{reward.get('icon','🎁')}</div>
            <div style="flex:1;">
                <div style="font-size:16px;font-weight:800;">{reward.get('title','Reward')}</div>
                <div style="font-size:13px;color:#6b7280;margin:4px 0;">{reward.get('description','')}</div>
                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                    <span class="reward-cost">🪙 {reward.get('points_cost',0)} pts</span>
                    <span style="font-size:11px;color:#6b7280;">{reward.get('partner_name','')}</span>
                    <span style="font-size:11px;color:#6b7280;">Stock: {reward.get('stock',0)}</span>
                    {f'<span style="font-size:11px;color:#22c55e;font-weight:600;">{reward.get("discount_pct",0)}% OFF</span>' if reward.get('discount_pct',0) > 0 else ''}
                </div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

def render_daily_action(action_name: str, category: str, points: int, done: bool = False):
    cat_icons = {"transport":"🚗","diet":"🥗","waste":"♻️","water":"💧","energy":"⚡","nature":"🌳","community":"🤝","learning":"📚","wellness":"🧘"}
    icon = cat_icons.get(category, "📋")
    cls = "done" if done else ""
    btn_label = "✅ Done" if done else "Collect"
    return {"name": action_name, "category": category, "points": points, "icon": icon, "cls": cls, "done": done}

def render_transaction_row(tx: Dict[str, Any]):
    pts = tx.get("points", 0)
    cls = "tx-earn" if pts > 0 else "tx-spend"
    sign = "+" if pts > 0 else ""
    st.markdown(f"""
    <div class="tx-row">
        <div><span style="font-weight:600;">{tx.get('description','')}</span></div>
        <div><span class="{cls}" style="font-weight:700;">{sign}{pts} pts</span></div>
    </div>""", unsafe_allow_html=True)

def render_leaderboard_row(rank: int, name: str, points: int, level: int, is_user: bool = False):
    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
    highlight = "border:2px solid #22c55e;" if is_user else ""
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-radius:10px;margin-bottom:4px;background:rgba(255,255,255,0.6);border:1px solid rgba(0,0,0,0.06);{highlight}">
        <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-size:18px;min-width:28px;text-align:center;">{medal}</span>
            <span style="font-weight:700;">{name}</span>
            <span style="font-size:11px;color:#6b7280;">Lv.{level}</span>
        </div>
        <span style="font-weight:800;color:#16a34a;">{points} pts</span>
    </div>""", unsafe_allow_html=True)
