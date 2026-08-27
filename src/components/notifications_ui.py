"""
Notification UI Components.

Reusable UI widgets for Streamlit, such as the notification bell, 
dropdowns, and preference forms.
"""

import streamlit as st
import datetime
from src.notifications.db import NotificationDB
from src.notifications.models import NotificationPreference

def render_notification_bell(user_id: int):
    """
    Renders a bell icon in the sidebar or main content indicating unread counts.
    """
    db = NotificationDB()
    unread = db.get_user_history(user_id, limit=100, unread_only=True)
    count = len(unread)
    
    if count > 0:
        st.sidebar.markdown(f"### 🔔 Notifications ({count})")
        with st.sidebar.expander("Recent Updates", expanded=False):
            for notif in unread[:3]:
                st.markdown(f"**{notif.icon} {notif.title}**")
                st.caption(notif.message)
            if count > 3:
                st.caption(f"+ {count - 3} more...")
            if st.button("Mark All Read", key="bell_mark_read"):
                db.mark_all_read(user_id)
                st.rerun()
    else:
        st.sidebar.markdown("### 🔕 No new notifications")

def render_preferences_form(user_id: int):
    """
    Renders the form to edit notification preferences.
    """
    db = NotificationDB()
    pref = db.get_preferences(user_id)
    
    st.subheader("Notification Preferences")
    
    with st.form("notification_prefs_form"):
        col1, col2 = st.columns(2)
        with col1:
            email_en = st.checkbox("Email Notifications", value=pref.email_enabled)
            in_app_en = st.checkbox("In-App Notifications", value=pref.in_app_enabled)
            weekly_dig = st.checkbox("Weekly Digest", value=pref.weekly_digest_enabled)
        
        with col2:
            st.markdown("**Quiet Hours**")
            start_time = st.time_input("Start Time", value=pref.quiet_hours_start or datetime.time(22, 0))
            end_time = st.time_input("End Time", value=pref.quiet_hours_end or datetime.time(8, 0))
            tz = st.selectbox("Timezone", ["UTC", "US/Pacific", "US/Eastern", "Europe/London", "Asia/Tokyo"], index=0)
            
        st.markdown("**Categories**")
        categories = ["goals", "challenges", "digest", "general", "system"]
        # Invert logic: UI shows what you WANT to receive, DB stores what you OPT OUT of
        selections = {}
        for cat in categories:
            selections[cat] = st.checkbox(cat.title(), value=(cat not in pref.opted_out_categories))
            
        submitted = st.form_submit_button("Save Preferences")
        if submitted:
            opt_outs = [c for c, val in selections.items() if not val]
            new_pref = NotificationPreference(
                user_id=user_id,
                email_enabled=email_en,
                in_app_enabled=in_app_en,
                quiet_hours_start=start_time,
                quiet_hours_end=end_time,
                timezone=tz,
                opted_out_categories=opt_outs,
                weekly_digest_enabled=weekly_dig
            )
            if db.save_preferences(new_pref):
                st.success("Preferences saved successfully!")
                st.rerun()
            else:
                st.error("Failed to save preferences.")
