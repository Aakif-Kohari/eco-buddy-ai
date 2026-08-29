"""
Pledge Stories – Streamlit Page
================================
Transform pledge data into compelling environmental narratives.
Generate shareable story cards, monthly eco-journals, and
multi-chapter journey stories.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from src.community.pledge_story_engine import (
    init_story_tables,
    generate_weekly_story,
    generate_milestone_story,
    generate_streak_story,
    generate_impact_story,
    generate_prediction_story,
    generate_journey_beginning_story,
    generate_full_journey_story,
    generate_monthly_journal,
    generate_impact_narrative,
    get_user_stories,
    get_user_journals,
    favorite_story,
    unfavorite_story,
    get_favorites,
    export_stories_json,
    story_to_dict,
    journal_to_dict,
    STORY_THEMES,
)
from src.utils.green_pledge_tracker import (
    init_pledge_tables,
    current_week_start,
    current_week_end,
    get_user_pledge_stats,
    PLEDGE_CATEGORIES,
)

st.set_page_config(page_title="Pledge Stories", page_icon="📖", layout="wide")

# Initialise tables
init_pledge_tables()
init_story_tables()

# ── Auth gate ────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("🔒 Please sign in to view Pledge Stories.")
    st.stop()

# ── Page header ──────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:10px 0 4px;'>
    <h1 style='margin:0;font-size:2.4rem;'>📖 Pledge Stories</h1>
    <p style='color:#6b7280;margin-top:4px;font-size:1.05rem;'>
        Your sustainability journey, told as a story. Generate shareable narratives and eco-journals.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────────────
tab_generate, tab_stories, tab_journal, tab_journey, tab_impact, tab_export = st.tabs([
    "✨ Generate",
    "📚 My Stories",
    "📗 Eco-Journal",
    "🗺️ Journey Story",
    "🌍 Impact Narrative",
    "📦 Export",
])

# =====================================================================
# TAB: Generate
# =====================================================================
with tab_generate:
    st.subheader("✨ Generate Story Cards")

    username = st.text_input("Your display name", value="Eco Warrior", key="story_username")

    story_types = st.multiselect(
        "Story types to generate",
        ["Weekly Summary", "Milestone Celebration", "Streak Narrative",
         "CO₂ Impact", "Prediction", "Journey Beginning"],
        default=["Weekly Summary", "CO₂ Impact"],
        key="story_types",
    )

    if st.button("🚀 Generate Stories", use_container_width=True):
        generated: list = []
        type_map = {
            "Weekly Summary": ("weekly", generate_weekly_story),
            "Milestone Celebration": ("milestone", generate_milestone_story),
            "Streak Narrative": ("streak", generate_streak_story),
            "CO₂ Impact": ("impact", generate_impact_story),
            "Prediction": ("prediction", generate_prediction_story),
            "Journey Beginning": ("beginning", generate_journey_beginning_story),
        }

        for stype in story_types:
            if stype in type_map:
                _, func = type_map[stype]
                result = func(user_id, username)
                if result is not None:
                    generated.append(result)

        if generated:
            st.success(f"✅ Generated {len(generated)} story card(s)!")
            st.rerun()
        else:
            st.warning("No stories could be generated. Try completing some pledges first!")

    # Preview of available themes
    st.divider()
    st.markdown("#### 🎨 Story Themes")
    theme_cols = st.columns(len(STORY_THEMES))
    for i, (theme_key, theme_data) in enumerate(STORY_THEMES.items()):
        with theme_cols[i]:
            st.markdown(f"""
            <div style='text-align:center;padding:12px;border-radius:12px;
                        border:2px solid {theme_data["color_primary"]}40;
                        background:linear-gradient(135deg,{theme_data["color_primary"]}10,#fff);'>
                <div style='font-size:2rem;'>{theme_data["icon"]}</div>
                <div style='font-weight:600;font-size:0.85rem;'>{theme_data["title"]}</div>
            </div>
            """, unsafe_allow_html=True)

# =====================================================================
# TAB: My Stories
# =====================================================================
with tab_stories:
    st.subheader("📚 My Story Collection")

    stories = get_user_stories(user_id, limit=20)
    favorites = get_favorites(user_id)

    if not stories:
        st.info("No stories yet! Head to **Generate** to create your first story card.")
    else:
        # Filter
        filter_type = st.selectbox(
            "Filter by type",
            ["All", "Weekly Summary", "Milestone Celebration", "Streak Narrative",
             "CO₂ Impact", "Prediction", "Journey Beginning"],
            key="story_filter",
        )
        type_filter_map = {
            "Weekly Summary": "weekly_summary",
            "Milestone Celebration": "milestone_celebration",
            "Streak Narrative": "streak_narrative",
            "CO₂ Impact": "co2_impact",
            "Prediction": "prediction_story",
            "Journey Beginning": "journey_beginning",
        }

        filtered = stories
        if filter_type != "All":
            filtered = [s for s in stories if s.story_type == type_filter_map.get(filter_type, "")]

        for story in filtered:
            is_fav = story.story_id in favorites
            fav_icon = "⭐" if is_fav else "☆"

            # Story card
            st.markdown(f"""
            <div style='border:2px solid {story.color_primary}40;border-radius:20px;padding:24px;
                        background:linear-gradient(135deg,{story.color_primary}08,{story.color_secondary}08,#fff);
                        margin-bottom:14px;'>
                <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                    <div>
                        <span style='font-size:0.75rem;color:{story.color_primary};font-weight:600;'>
                            {story.story_type.replace('_', ' ').title()}
                        </span>
                        <h3 style='margin:4px 0;'>{story.title}</h3>
                    </div>
                    <div style='text-align:right;'>
                        <div style='font-size:2rem;font-weight:800;color:{story.color_primary};'>
                            {story.headline_stat}
                        </div>
                        <div style='font-size:0.75rem;color:#6b7280;'>{story.stat_unit}</div>
                    </div>
                </div>
                <p style='color:#4b5563;margin:12px 0;font-size:0.95rem;line-height:1.6;'>
                    {story.narrative}
                </p>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <span style='font-size:0.75rem;color:#9ca3af;'>{story.created_at[:10]}</span>
                    <span style='font-size:0.75rem;color:#9ca3af;'>{story.icon} {story.theme.title()}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Actions
            col1, col2 = st.columns([1, 4])
            with col1:
                if is_fav:
                    if st.button(f"⭐ Unfavorite", key=f"unfav_{story.story_id}"):
                        unfavorite_story(user_id, story.story_id)
                        st.rerun()
                else:
                    if st.button(f"☆ Favorite", key=f"fav_{story.story_id}"):
                        favorite_story(user_id, story.story_id)
                        st.rerun()
            with col2:
                if story.share_text:
                    st.text_input(
                        "Share text",
                        value=story.share_text,
                        key=f"share_{story.story_id}",
                        label_visibility="collapsed",
                    )

        # Stats
        st.divider()
        st.markdown(f"#### 📊 Story Stats: {len(stories)} stories · {len(favorites)} favorites")

# =====================================================================
# TAB: Eco-Journal
# =====================================================================
with tab_journal:
    st.subheader("📗 Monthly Eco-Journal")

    col1, col2 = st.columns([2, 1])
    with col1:
        journal_username = st.text_input("Display name", value="Eco Warrior", key="journal_username")
    with col2:
        if st.button("📝 Generate Monthly Journal", use_container_width=True):
            entry = generate_monthly_journal(user_id, journal_username)
            st.success(f"✅ Journal entry for {entry.month} created!")
            st.rerun()

    journals = get_user_journals(user_id, limit=12)

    if not journals:
        st.info("No journal entries yet. Generate your first monthly journal above!")
    else:
        for entry in journals:
            # Journal card
            st.markdown(f"""
            <div style='border:1px solid #d1fae5;border-radius:20px;padding:24px;
                        background:linear-gradient(135deg,#f0fdf4,#ecfdf5,#fff);
                        margin-bottom:16px;'>
                <h3 style='margin:0 0 8px;'>{entry.title}</h3>
                <p style='color:#4b5563;margin:0 0 12px;line-height:1.6;'>{entry.narrative}</p>
            </div>
            """, unsafe_allow_html=True)

            # Highlights
            if entry.highlights:
                st.markdown("**✨ Highlights:**")
                for h in entry.highlights:
                    st.markdown(f"- {h}")

            # Stats summary
            if entry.stats_summary:
                stats = entry.stats_summary
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("🌍 CO₂ Saved", f"{stats.get('total_co2_kg', 0):.1f} kg")
                c2.metric("⭐ XP Earned", f"{stats.get('total_xp', 0)}")
                c3.metric("📅 Check-ins", f"{stats.get('total_checkins', 0)}")
                c4.metric("✅ Completed", f"{stats.get('total_completed', 0)}")

            # Best moment & challenge
            if entry.best_moment:
                st.markdown(f"**🌟 Best Moment:** {entry.best_moment}")
            if entry.challenge_faced:
                st.markdown(f"**💪 Challenge:** {entry.challenge_faced}")
            if entry.next_month_goal:
                st.markdown(f"**🎯 Next Month Goal:** {entry.next_month_goal}")

            st.divider()

# =====================================================================
# TAB: Journey Story
# =====================================================================
with tab_journey:
    st.subheader("🗺️ Your Complete Journey Story")

    if st.button("📖 Generate Journey Story", use_container_width=True):
        scenes = generate_full_journey_story(user_id, "Eco Warrior")
        st.session_state["journey_scenes"] = scenes

    if "journey_scenes" in st.session_state:
        scenes = st.session_state["journey_scenes"]

        if not scenes:
            st.info("Start your pledge journey to unlock your story!")
        else:
            st.markdown(f"### 📖 {len(scenes)}-Chapter Story")

            mood_styles = {
                "hopeful": ("🌱", "#22c55e", "#f0fdf4"),
                "triumphant": ("🏆", "#f59e0b", "#fffbeb"),
                "reflective": ("🔮", "#a855f7", "#faf5ff"),
                "inspiring": ("⚡", "#3b82f6", "#eff6ff"),
                "urgent": ("🚨", "#ef4444", "#fef2f2"),
            }

            for i, scene in enumerate(scenes):
                emoji, color, bg = mood_styles.get(scene.mood, ("📖", "#6b7280", "#f9fafb"))

                st.markdown(f"""
                <div style='border:1px solid {color}30;border-radius:16px;padding:22px;
                            background:linear-gradient(135deg,{bg},#fff);margin-bottom:16px;
                            border-left:4px solid {color};'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <h3 style='margin:0;'>{scene.title}</h3>
                        <span style='font-size:1.5rem;'>{scene.icon or emoji}</span>
                    </div>
                    <p style='color:#4b5563;margin:10px 0 0;line-height:1.6;'>
                        {scene.narrative}
                    </p>
                    {f"<div style='margin-top:10px;background:{color}10;border-radius:8px;padding:8px 14px;display:inline-block;'><span style='font-weight:700;color:{color};'>{scene.stat_highlight}</span></div>" if scene.stat_highlight else ""}
                </div>
                """, unsafe_allow_html=True)

            # Journey summary
            st.divider()
            stats = get_user_pledge_stats(user_id)
            c1, c2, c3 = st.columns(3)
            c1.metric("📖 Chapters", len(scenes))
            c2.metric("🌍 CO₂ Saved", f"{stats.total_co2_saved_kg:.1f} kg")
            c3.metric("✅ Pledges Completed", stats.total_pledges_completed)

# =====================================================================
# TAB: Impact Narrative
# =====================================================================
with tab_impact:
    st.subheader("🌍 Your Impact Narrative")

    narrative = generate_impact_narrative(user_id, "Eco Warrior")

    # Headline card
    tone_colors = {
        "inspiring": "#3b82f6",
        "encouraging": "#22c55e",
        "celebratory": "#f59e0b",
        "urgent": "#ef4444",
        "triumphant": "#a855f7",
    }
    color = tone_colors.get(narrative.tone, "#6b7280")

    st.markdown(f"""
    <div style='border:2px solid {color}40;border-radius:20px;padding:32px;
                background:linear-gradient(135deg,{color}08,{color}04,#fff);
                text-align:center;'>
        <h2 style='margin:0 0 8px;color:{color};'>{narrative.headline}</h2>
        <p style='color:#4b5563;margin:0 0 16px;font-size:1.1rem;line-height:1.6;
                  max-width:700px;margin-left:auto;margin-right:auto;'>
            {narrative.body}
        </p>
        <div style='background:{color}10;border-radius:12px;padding:14px 24px;
                    display:inline-block;margin-bottom:16px;'>
            <span style='font-weight:700;color:{color};font-size:1.05rem;'>
                🌿 {narrative.equivalent}
            </span>
        </div>
        {f"<p style='color:{color};font-weight:600;margin:0;'>→ {narrative.call_to_action}</p>" if narrative.call_to_action else ""}
    </div>
    """, unsafe_allow_html=True)

    # Additional context
    st.divider()
    stats = get_user_pledge_stats(user_id)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌍 Total CO₂", f"{stats.total_co2_saved_kg:.1f} kg")
    c2.metric("✅ Completed", stats.total_pledges_completed)
    c3.metric("🔥 Streak", f"{stats.current_streak} wks")
    c4.metric("🌱 Level", stats.level)

    # Tone explanation
    st.markdown(f"""
    <div style='background:#f9fafb;border-radius:12px;padding:14px;margin-top:12px;'>
        <span style='font-size:0.85rem;color:#6b7280;'>
            📝 Narrative tone: <strong>{narrative.tone.title()}</strong>
            — automatically selected based on your progress.
        </span>
    </div>
    """, unsafe_allow_html=True)

# =====================================================================
# TAB: Export
# =====================================================================
with tab_export:
    st.subheader("📦 Export Stories")

    stories = get_user_stories(user_id, limit=100)
    journals = get_user_journals(user_id, limit=12)

    st.markdown(f"""
    **Your collection:**
    - 📚 {len(stories)} story cards
    - 📗 {len(journals)} journal entries
    - ⭐ {len(get_favorites(user_id))} favorites
    """)

    if stories or journals:
        json_data = export_stories_json(user_id)
        st.download_button(
            label="📥 Download All Stories as JSON",
            data=json_data,
            file_name="my_pledge_stories.json",
            mime="application/json",
            use_container_width=True,
        )

        st.markdown("#### Preview")
        with st.expander("JSON Preview"):
            st.json(json_data)
    else:
        st.info("No stories to export yet. Generate some first!")
