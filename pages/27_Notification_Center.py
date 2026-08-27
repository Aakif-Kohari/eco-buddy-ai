import streamlit as st
import pandas as pd
from datetime import datetime

from src.components.notifications_ui import render_preferences_form
from src.notifications.db import NotificationDB

st.set_page_config(page_title="Notification Center", page_icon="🔔", layout="wide")

st.title("🔔 Notification Center")
st.markdown("Manage your alerts, reminders, and sustainability digests.")

# In a real app, user_id comes from session. We mock it here.
user_id = st.session_state.get("user_id", 1)

db = NotificationDB()

tab_inbox, tab_history, tab_prefs = st.tabs(["📥 Inbox", "📜 History", "⚙️ Preferences"])

with tab_inbox:
    st.subheader("Unread Notifications")
    
    unread = src.notifications.db.get_user_history(user_id, limit=50, unread_only=True)
    
    if not unread:
        st.info("You're all caught up! No unread notifications.")
    else:
        if st.button("Mark All as Read"):
            src.notifications.db.mark_all_read(user_id)
            st.rerun()
            
        for notif in unread:
            with st.container(border=True):
                col1, col2 = st.columns([1, 10])
                with col1:
                    st.title(notif.icon)
                with col2:
                    st.markdown(f"**{notif.title}**")
                    st.markdown(notif.message)
                    st.caption(f"{notif.category.title()} • {notif.created_at.strftime('%Y-%m-%d %H:%M')} UTC")
                    
                    if st.button("Mark Read", key=f"read_{notif.id}"):
                        src.notifications.db.update_notification_status(notif.id, "read")
                        st.rerun()

with tab_history:
    st.subheader("Notification History")
    history = src.notifications.db.get_user_history(user_id, limit=100, unread_only=False)
    
    if not history:
        st.write("No notification history found.")
    else:
        # Convert to DataFrame for a nice table view
        data = []
        for h in history:
            data.append({
                "Date": h.created_at.strftime('%Y-%m-%d %H:%M'),
                "Category": h.category.title(),
                "Title": h.title,
                "Status": h.status.title()
            })
            
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

with tab_prefs:
    render_preferences_form(user_id)
