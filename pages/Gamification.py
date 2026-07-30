import streamlit as st
import pandas as pd
import time
from database import *
from emissions import *
from recommendations import *
from ocr_utils import *
import os
import tempfile
import uuid
import plotly.graph_objects as go
import plotly.express as px
from report import generate_pdf
import gamification as gf
from marketplace import *
import energy_audit as ea

from styles.theme import apply_theme

user_id = st.session_state.get('user_id')
if not user_id:
    st.warning('Please log in from the main application page.')
    st.stop()
apply_theme()

st.markdown("<div class='section-header'>🎮 Your Eco Journey</div>", unsafe_allow_html=True)

# Header: Level, XP, Streak
total_xp = gf.get_total_xp(user_id)
level = gf.calculate_level(total_xp)
progress = gf.calculate_level_progress(total_xp)
history = get_assessments(user_id)
activities_dates = [row[1] for row in history]
streak = gf.calculate_streak(1, activities_dates)

# Check for newly unlocked cards
new_cards = gf.check_card_eligibility(user_id)
if new_cards:
    for c_id in new_cards:
        card_def = gf.CARDS.get(c_id)
        if card_def:
            st.balloons()
            st.success(f"🎴 New Trading Card Unlocked: {card_def['icon']} {card_def['name']} ({card_def['rarity'].title()})!")

g_col1, g_col2, g_col3 = st.columns(3)
g_col1.metric("Current Level", f"Lvl {level}")
g_col2.metric("Total XP", f"{total_xp} XP")
g_col3.metric("Current Streak", f"{streak} Days 🔥")

st.progress(progress, text=f"Progress to Level {level+1}")

st.markdown("---")

tab_challenges, tab_badges, tab_cards = st.tabs(["🏆 Challenges", "🎖️ Badges", "🃏 Trading Cards"])

with tab_challenges:
    st.markdown("### 🏆 Weekly Challenges")

    user_challenges = gf.get_user_challenges(user_id)
    enrolled_ids = [c['challenge_id'] for c in user_challenges if c['status'] != 'expired']

    def render_challenge_card(ch_id, ch_data, user_challenges, enrolled_ids):
        with st.expander(
            f"{ch_data['title']} ({ch_data['xp']} XP) - {ch_data['category']}"
        ):
            st.write(f"Target: {ch_data['target']} {ch_data['unit']}")

            if ch_id in enrolled_ids:
                status = [
                    c["status"]
                    for c in user_challenges
                    if c["challenge_id"] == ch_id
                ][-1]

                if status == "completed":
                    st.success("Challenge Completed! 🎉")
                else:
                    current_prog = [c["progress_value"] for c in user_challenges if c["challenge_id"] == ch_id][-1]
                    remaining = max(ch_data["target"] - current_prog, 0)

                    st.write(f"Progress: {current_prog} / {ch_data['target']}")

                    prog_val = st.number_input(
                        f"Update Progress for {ch_id}",
                        min_value=0.0,
                        step=1.0,
                        value=0.0,
                        key=f"prog_{ch_id}",
                    )

                    is_valid = True

                    if prog_val <= 0:
                        st.warning("⚠️ Progress must be greater than zero.")
                        is_valid = False
                    elif prog_val > remaining:
                        st.warning(
                            f"⚠️ You can only add up to {remaining} {ch_data['unit']} to complete this challenge."
                        )
                        is_valid = False

                    if st.button(
                        "Update",
                        key=f"btn_prog_{ch_id}",
                        disabled=not is_valid,
                    ):
                        gf.update_challenge_progress(
                            1,
                            ch_id,
                            progress_increment=prog_val,
                        )
                        gf.validate_challenge_progress(1, ch_id)
                        st.success("Progress updated successfully!")
                        st.rerun()
            else:
                if st.button(
                    "Enroll",
                    key=f"enroll_{ch_id}",
                ):
                    gf.enroll_challenge(user_id, ch_id)
                    st.rerun()

    for ch_id, ch_data in gf.CHALLENGES.items():
        render_challenge_card(
            ch_id,
            ch_data,
            user_challenges,
            enrolled_ids,
        )

with tab_badges:
    st.markdown("### 🎖️ Achievement Badges")

    unlocked = gf.get_unlocked_badges(user_id)
    unlocked_ids = [b['badge_id'] for b in unlocked]

    cols = st.columns(len(gf.BADGES))
    for i, (b_id, b_data) in enumerate(gf.BADGES.items()):
        with cols[i % len(cols)]:
            if b_id in unlocked_ids:
                st.markdown(f"**✅ {b_data['name']}**")
                st.caption(b_data['desc'])
                if st.button("Share Card", key=f"share_{b_id}"):
                    file_path = gf.generate_achievement_card(1, b_id, f"badge_{b_id}.png")
                    if file_path:
                        with open(file_path, "rb") as f:
                            st.download_button("Download Card", f, file_name=f"badge_{b_id}.png", key=f"dl_{b_id}")
            else:
                st.markdown(f"**🔒 {b_data['name']}**")
                st.caption(b_data['desc'])

with tab_cards:
    st.markdown("### 🃏 Eco Achievement Trading Cards")

    unlocked_cards = gf.get_unlocked_cards(user_id)
    unlocked_card_ids = [c['card_id'] for c in unlocked_cards]

    st.markdown(
        f"<p style='color: #888;'>Collected {len(unlocked_card_ids)} / {len(gf.CARDS)} cards</p>",
        unsafe_allow_html=True
    )

    progress_pct = len(unlocked_card_ids) / len(gf.CARDS) if gf.CARDS else 0
    st.progress(progress_pct)

    st.markdown("---")

    # Filter by rarity
    rarity_filter = st.selectbox(
        "Filter by rarity",
        ["All", "Common", "Uncommon", "Rare", "Legendary"],
    )

    filtered_cards = list(gf.CARDS.items())
    if rarity_filter != "All":
        rarity_key = rarity_filter.lower()
        filtered_cards = [(k, v) for k, v in filtered_cards if v['rarity'] == rarity_key]

    # Display cards in a grid (3 per row)
    card_cols = st.columns(3)
    for idx, (c_id, c_def) in enumerate(filtered_cards):
        rarity = gf.CARD_RARITIES[c_def['rarity']]
        is_unlocked = c_id in unlocked_card_ids

        with card_cols[idx % 3]:
            bg_color = f"rgb{rarity['color_bg']}"
            accent_color = f"rgb{rarity['color_accent']}"
            text_color = f"rgb{rarity['color_text']}"

            if is_unlocked:
                st.markdown(f"""
                <div style="
                    background: {bg_color};
                    border: 3px solid {accent_color};
                    border-radius: 16px;
                    padding: 18px;
                    margin-bottom: 16px;
                    text-align: center;
                    min-height: 240px;
                ">
                    <div style="
                        background: {accent_color};
                        color: white;
                        border-radius: 10px;
                        padding: 4px 12px;
                        display: inline-block;
                        font-size: 13px;
                        font-weight: bold;
                        margin-bottom: 8px;
                    ">{rarity['label']}</div>
                    <div style="font-size: 42px; margin: 8px 0;">{c_def['icon']}</div>
                    <div style="font-size: 18px; font-weight: bold; color: {text_color};">{c_def['name']}</div>
                    <div style="font-size: 13px; color: #555; margin-top: 6px;">{c_def['desc']}</div>
                </div>
                """, unsafe_allow_html=True)

                dl_key = f"dl_card_{c_id}"
                if st.button(f"📥 Download Card", key=dl_key):
                    file_path = gf.generate_trading_card(user_id, c_id, f"trading_card_{c_id}.png")
                    if file_path:
                        with open(file_path, "rb") as f:
                            st.download_button(
                                "Save PNG",
                                f,
                                file_name=f"EcoBuddy_Card_{c_def['name'].replace(' ', '_')}.png",
                                key=f"save_{c_id}"
                            )

                share_key = f"share_card_{c_id}"
                if st.button(f"🔄 Re-unlock check", key=share_key):
                    gf.check_card_eligibility(user_id)
                    st.rerun()
            else:
                st.markdown(f"""
                <div style="
                    background: #f0f0f0;
                    border: 3px dashed #ccc;
                    border-radius: 16px;
                    padding: 18px;
                    margin-bottom: 16px;
                    text-align: center;
                    min-height: 240px;
                    opacity: 0.7;
                ">
                    <div style="
                        background: #ccc;
                        color: #888;
                        border-radius: 10px;
                        padding: 4px 12px;
                        display: inline-block;
                        font-size: 13px;
                        font-weight: bold;
                        margin-bottom: 8px;
                    ">{rarity['label']}</div>
                    <div style="font-size: 42px; margin: 8px 0;">🔒</div>
                    <div style="font-size: 18px; font-weight: bold; color: #888;">???</div>
                    <div style="font-size: 13px; color: #aaa; margin-top: 6px;">{c_def['condition']}</div>
                </div>
                """, unsafe_allow_html=True)


