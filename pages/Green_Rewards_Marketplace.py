"""
Page: Green Rewards Marketplace
==================================
Earn green points through daily eco actions, level up, and redeem rewards
from partner brands. Track your journey and climb the leaderboard.
"""

import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Green Rewards Marketplace", page_icon="🪙", layout="wide")

from green_rewards_service import (
    earn_points, redeem_reward, get_user_dashboard, get_category_rewards,
    LEVEL_CONFIG, DAILY_ACTIONS,
)
from green_rewards_cards import (
    inject_css, render_points_display, render_reward_card,
    render_daily_action, render_transaction_row, render_leaderboard_row,
)
from green_rewards_charts import (
    render_points_history_chart, render_level_progress_gauge,
    render_category_bar, render_category_donut, render_leaderboard_chart,
)
from green_rewards_db import get_leaderboard

inject_css()

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("🔐 Please log in to use Green Rewards Marketplace.")
    st.stop()

st.markdown("""
<div style="text-align:center;padding:20px 0 12px;background:linear-gradient(135deg,rgba(34,197,94,0.08),rgba(59,130,246,0.04));border-radius:16px;margin-bottom:20px;">
    <span style="font-size:36px;">🪙</span>
    <h1 style="margin:6px 0 2px;font-size:28px;font-weight:900;">Green Rewards Marketplace</h1>
    <p style="color:#6b7280;font-size:14px;">Earn points for eco actions, level up, and redeem rewards from partner brands.</p>
</div>""", unsafe_allow_html=True)

dashboard = get_user_dashboard(user_id)

# ── Points + Level Display ─────────────────────────────────────────────
render_points_display(dashboard)

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────
tab_daily, tab_rewards, tab_history, tab_leaderboard = st.tabs([
    "☀️ Daily Actions", "🎁 Redeem Rewards", "📊 My Points", "🏆 Leaderboard"
])

# ── Daily Actions ──────────────────────────────────────────────────────
with tab_daily:
    st.subheader("☀️ Today's Eco Actions")
    st.caption("Complete eco-friendly actions to earn green points. Each action can be logged once per day.")
    today_done = dashboard.get("today_actions", [])
    all_actions = dashboard.get("all_daily_actions", [])
    for name, category, points in all_actions:
        done = name in today_done
        action = render_daily_action(name, category, points, done)
        cols = st.columns([5, 2])
        with cols[0]:
            st.markdown(f"{action['icon']} **{name}** — {category.title()}")
        with cols[1]:
            if done:
                st.success(f"✅ +{points} pts")
            else:
                if st.button(f"+{points} pts", key=f"act_{name[:20]}"):
                    result = earn_points(user_id, name, category, points)
                    if result["success"]:
                        st.success(f"🎉 Earned {result['points_earned']} pts!")
                        st.rerun()
                    else:
                        st.warning(result["error"])

    # Category chart
    today_actions = [a for a in all_actions if a[0] in today_done]
    if today_actions:
        fig_cat = render_category_bar([{"action_category": a[1]} for a in today_actions])
        st.plotly_chart(fig_cat, use_container_width=True)

# ── Rewards ────────────────────────────────────────────────────────────
with tab_rewards:
    st.subheader("🎁 Available Rewards")
    categories = ["all", "shopping", "food", "nature", "transport", "waste", "education", "offsets", "digital", "travel"]
    selected_cat = st.selectbox("Category", categories, format_func=lambda x: x.title())
    rewards = get_category_rewards(None) if selected_cat == "all" else get_category_rewards(selected_cat)

    if not rewards:
        st.info("No rewards available in this category.")
    else:
        user_points = dashboard.get("points", 0)
        for reward in rewards:
            can_afford = user_points >= reward.get("points_cost", 0)
            render_reward_card(reward, user_points, can_afford)
            if can_afford:
                if st.button(f"🪙 Redeem ({reward['points_cost']} pts)", key=f"redeem_{reward['id']}"):
                    result = redeem_reward(user_id, reward["id"])
                    if result["success"]:
                        st.success(f"🎉 Redeemed! Coupon: `{result['coupon_code']}`")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(result["error"])
            else:
                needed = reward.get("points_cost", 0) - user_points
                st.caption(f"Need {needed} more points")
            st.markdown("---")

# ── My Points ──────────────────────────────────────────────────────────
with tab_history:
    st.subheader("📊 Points Dashboard")

    col_gauge, col_history = st.columns([1, 2])
    with col_gauge:
        fig_gauge = render_level_progress_gauge(
            dashboard.get("progress", 0), dashboard.get("level", 1))
        st.plotly_chart(fig_gauge, use_container_width=True)
    with col_history:
        transactions = dashboard.get("transactions", [])
        if transactions:
            fig_hist = render_points_history_chart(transactions)
            st.plotly_chart(fig_hist, use_container_width=True)

    col_tx, col_src = st.columns([1, 1])
    with col_tx:
        st.markdown("**📜 Recent Transactions**")
        transactions = dashboard.get("transactions", [])
        for tx in transactions[:10]:
            render_transaction_row(tx)
        if not transactions:
            st.caption("No transactions yet.")
    with col_src:
        if transactions:
            fig_src = render_category_donut(transactions)
            st.plotly_chart(fig_src, use_container_width=True)

    # Redemptions
    redemptions = dashboard.get("redemptions", [])
    if redemptions:
        st.markdown("---")
        st.subheader("🎟️ My Redemptions")
        for r in redemptions:
            st.markdown(f"**{r.get('reward_icon','')} {r.get('reward_title','')}** — `{r.get('coupon_code','')}` ({r.get('redeemed_at','')[:10]})")

# ── Leaderboard ────────────────────────────────────────────────────────
with tab_leaderboard:
    st.subheader("🏆 Green Champions Leaderboard")
    leaderboard = get_leaderboard(limit=25)
    if leaderboard:
        fig_lb = render_leaderboard_chart(leaderboard)
        st.plotly_chart(fig_lb, use_container_width=True)
        for rank, entry in enumerate(leaderboard, 1):
            is_me = entry.get("user_id") == user_id
            render_leaderboard_row(
                rank, entry.get("username", f"User-{entry['user_id']}"),
                entry.get("total_points", 0), entry.get("level", 1), is_user=is_me)
    else:
        st.info("No leaderboard data yet. Be the first to earn points!")

st.markdown("---")
st.markdown("""
<div style="text-align:center;padding:14px;color:#9ca3af;font-size:13px;">
    🪙 Green Rewards Marketplace — Earn, level up, redeem · Powered by EcoBuddy AI
</div>""", unsafe_allow_html=True)
