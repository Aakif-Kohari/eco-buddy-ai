import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.carbon.carbon_credits_market import CarbonCreditsMarketplace
from src.community.gamification_engine import GamificationEngine
from src.utils.user_wallet_service import UserWalletService

st.set_page_config(page_title="Carbon Marketplace & Rewards", layout="wide", page_icon="🛍️")

# Mock User Services Singleton Initialize
@st.cache_resource
def get_services():
    return CarbonCreditsMarketplace(), GamificationEngine(), UserWalletService()

market, gamification, wallet = get_services()
USER = "USR_DEMO_01"

# Automatically update streak & award base XP on load
gamification.update_streak(USER)

st.markdown("""
<style>
    .kpi-card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        border: 1px solid #333;
        color: white;
    }
    .kpi-title { font-size: 14px; color: #a3a3a3; text-transform: uppercase; }
    .kpi-value { font-size: 28px; font-weight: bold; color: #3b82f6; margin-top: 5px; }
    .project-card {
        background-color: #2a2a2a;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 15px;
        border-left: 5px solid #10b981;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛍️ Carbon Marketplace & Eco Rewards")
st.markdown("Neutralize your carbon footprint by purchasing verified offsets, and earn EcoCoins for sustainable actions!")

profile = gamification.get_profile(USER)
balance = wallet.get_balance(USER)
impact = market.get_user_impact(USER)

# Header Metrics
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Eco Level</div><div class='kpi-value'>{profile['level']}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total XP</div><div class='kpi-value'>{profile['xp']}</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>EcoCoins Balance</div><div class='kpi-value' style='color:#fbbf24;'>🪙 {balance}</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Tons Offset</div><div class='kpi-value' style='color:#10b981;'>🌍 {impact['total_offset_tons']}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

t1, t2 = st.tabs(["🌍 Offset Marketplace", "🏆 Achievements & Rewards"])

with t1:
    st.subheader("Verified Offset Projects")
    projects = market.get_available_projects()
    
    for p in projects:
        with st.container():
            st.markdown(f"<div class='project-card'>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"### {p['name']}")
                st.write(f"**Type:** {p['type']} | **Verified By:** {p['verifier']} | ⭐ {p['rating']}/5.0")
            with col2:
                st.markdown(f"### ${p['price_per_ton_usd']:.2f} / ton")
                st.write(f"{p['available_tons']:,.0f} tons left")
            with col3:
                tons_to_buy = st.number_input(f"Tons to buy", min_value=1.0, max_value=float(p['available_tons']), value=1.0, step=0.5, key=f"buy_{p['id']}")
                if st.button("Purchase Offset", key=f"btn_{p['id']}", type="primary"):
                    res = market.purchase_credits(USER, p['id'], tons_to_buy)
                    if res["status"] == "success":
                        st.success(f"Success! {tons_to_buy} tons offset.")
                        # Award a badge and XP for buying an offset!
                        gamification.award_badge(USER, "B02")
                        st.snow()
                    else:
                        st.error(res["message"])
            st.markdown("</div>", unsafe_allow_html=True)

with t2:
    st.subheader("Your Badges")
    badges = profile["badges_earned"]
    
    if not badges:
        st.info("You haven't earned any badges yet. Start logging eco-actions!")
    else:
        bc1, bc2, bc3 = st.columns(3)
        for idx, b_id in enumerate(badges):
            b_info = next((bx for bx in gamification.BADGES if bx["id"] == b_id), None)
            if b_info:
                target_col = [bc1, bc2, bc3][idx % 3]
                with target_col:
                    st.markdown(f"#### 🏅 {b_info['name']}")
                    st.write(b_info['description'])
    
    st.markdown("---")
    st.subheader("Daily Actions (Demo)")
    if st.button("Log public transit commute (+30 XP, +10 EcoCoins)"):
        gamification.award_xp(USER, 30, "Public Transit")
        wallet.mint_coins(USER, 10, "Transit Reward")
        st.toast("Commute Logged!", icon="🚍")
    
    if st.button("Log vegan meal (+15 XP, +5 EcoCoins)"):
        gamification.award_xp(USER, 15, "Vegan Meal")
        wallet.mint_coins(USER, 5, "Diet Reward")
        st.toast("Meal Logged!", icon="🥗")
