"""
Email Digest UI Component for EcoBuddy AI
Provides UI for managing weekly eco-tips email digest settings.
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from src.lib.email_service import get_email_service, EmailConfig
from src.lib.eco_tips_digest import EcoTipsDigestGenerator, UserPreferences


def render_email_digest_settings(user_id: int) -> None:
    """
    Render email digest settings panel.
    """
    st.markdown("### 📧 Weekly Eco-Tips Digest Settings")
    
    # Check if email is configured
    service = get_email_service()
    
    if not service.config.sender_email:
        st.warning("⚠️ Email service is not configured. Please set SMTP_USERNAME and SMTP_PASSWORD in environment variables.")
        return
    
    # Toggle email digest
    col1, col2 = st.columns(2)
    
    with col1:
        digest_enabled = st.toggle(
            "📬 Enable Weekly Digest",
            value=st.session_state.get("digest_enabled", True),
            key="digest_enabled",
            help="Receive weekly eco-tips email digest"
        )
        st.session_state["digest_enabled"] = digest_enabled
    
    with col2:
        if digest_enabled:
            st.success("✅ Weekly digest is enabled")
        else:
            st.info("⏸️ Weekly digest is disabled")
    
    if not digest_enabled:
        return
    
    st.divider()
    
    # Digest preferences
    st.markdown("### ⚙️ Digest Preferences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        frequency = st.selectbox(
            "📅 Frequency",
            options=["weekly", "biweekly", "monthly"],
            index=0,
            key="digest_frequency",
            help="How often to receive the digest"
        )
    
    with col2:
        tips_per_week = st.slider(
            "💡 Number of Tips",
            min_value=3,
            max_value=10,
            value=5,
            step=1,
            key="tips_per_week",
            help="Number of eco-tips per digest"
        )
    
    # Category preferences
    st.markdown("### 🏷️ Preferred Categories")
    categories = [
        "energy", "water", "waste", "transport", "food", "offset"
    ]
    
    category_labels = {
        "energy": "⚡ Energy",
        "water": "💧 Water",
        "waste": "♻️ Waste",
        "transport": "🚗 Transport",
        "food": "🥗 Food",
        "offset": "🌳 Offset"
    }
    
    cols = st.columns(3)
    selected_categories = []
    
    for idx, category in enumerate(categories):
        col_idx = idx % 3
        with cols[col_idx]:
            if st.checkbox(
                category_labels.get(category, category),
                value=True,
                key=f"digest_cat_{category}"
            ):
                selected_categories.append(category)
    
    # Save preferences
    if st.button("💾 Save Digest Preferences", type="primary", use_container_width=True):
        preferences = UserPreferences(
            frequency=frequency,
            categories=selected_categories,
            tips_per_week=tips_per_week
        )
        st.session_state["digest_preferences"] = preferences
        st.success("✅ Digest preferences saved successfully!")
        st.toast("🎉 Preferences updated!")
    
    st.divider()
    
    # Preview digest
    st.markdown("### 👀 Preview Digest")
    
    if st.button("📧 Send Test Digest", type="secondary", use_container_width=True):
        with st.spinner("Generating test digest..."):
            # Get user data
            user_data = {
                "email": st.session_state.get("user_email", "test@example.com"),
                "name": st.session_state.get("username", "Test User"),
                "eco_score": 75,
                "total_footprint": 3500,
                "streak_days": 12,
                "total_assessments": 8,
                "contributors": {
                    "Transport": 1200,
                    "Electricity": 800,
                    "Food": 600,
                    "Waste": 400
                }
            }
            
            # Generate digest
            generator = EcoTipsDigestGenerator()
            preferences = st.session_state.get("digest_preferences", UserPreferences())
            digest = generator.generate_digest(user_data, preferences)
            
            # Send email
            if st.session_state.get("user_email"):
                success, message = service.send_weekly_digest(digest)
                if success:
                    st.success("✅ Test digest sent successfully!")
                    st.toast("📧 Check your inbox!")
                else:
                    st.error(f"❌ Failed to send test digest: {message}")
            else:
                st.info("📧 Please set your email in profile to receive test digest.")
                st.caption("Showing preview below:")
                
                # Show preview
                st.markdown("### 📧 Digest Preview")
                st.info(f"**To:** {digest.user_email}")
                st.info(f"**Week:** {digest.week_start} - {digest.week_end}")
                st.info(f"**Eco Score:** {digest.eco_score}")
                st.info(f"**Tips:** {len(digest.tips)} tips this week")


def render_digest_history() -> None:
    """
    Render digest history.
    """
    st.markdown("### 📊 Digest History")
    
    # Sample data - in production, this would come from database
    history_data = [
        {"date": "2026-08-18", "tips": 5, "sent": True},
        {"date": "2026-08-11", "tips": 5, "sent": True},
        {"date": "2026-08-04", "tips": 4, "sent": True},
        {"date": "2026-07-28", "tips": 6, "sent": False},
        {"date": "2026-07-21", "tips": 5, "sent": True},
    ]
    
    df = pd.DataFrame(history_data)
    df["status"] = df["sent"].apply(lambda x: "✅ Sent" if x else "⏳ Pending")
    
    st.dataframe(
        df[["date", "tips", "status"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "date": "📅 Date",
            "tips": "💡 Tips",
            "status": "📬 Status"
        }
    )


def render_email_digest_ui(user_id: int) -> None:
    """
    Main email digest UI.
    """
    tab1, tab2 = st.tabs(["⚙️ Settings", "📊 History"])
    
    with tab1:
        render_email_digest_settings(user_id)
    
    with tab2:
        render_digest_history()


def render_email_digest_sidebar() -> None:
    """
    Render email digest status in sidebar.
    """
    with st.sidebar.expander("📧 Weekly Digest", expanded=False):
        if st.session_state.get("digest_enabled", False):
            st.success("🟢 Enabled")
            st.caption("Next digest: Weekly")
        else:
            st.warning("⚪ Disabled")
            st.caption("Enable in Settings")
        
        if st.button("📧 Send Now", use_container_width=True):
            st.info("⏳ Sending digest...")