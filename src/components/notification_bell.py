"""
Notification Bell Component for EcoBuddy AI
Renders a notification bell icon with unread count and dropdown menu.
"""

import streamlit as st
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def render_notification_bell(user_id: Optional[int] = None) -> None:
    """
    Render the notification bell icon with unread count.
    
    Args:
        user_id: User ID for fetching notifications
    """
    if not user_id:
        return
    
    try:
        from src.lib.notification_manager import (
            get_notification_manager,
            get_unread_count,
            get_user_notifications,
            mark_as_read,
            mark_all_as_read,
            dismiss_notification
        )
        
        manager = get_notification_manager()
        unread_count = get_unread_count(user_id)
        
        # Custom CSS for notification bell
        st.markdown("""
        <style>
            .notification-bell {
                position: relative;
                display: inline-block;
                cursor: pointer;
                font-size: 24px;
                padding: 8px 12px;
                border-radius: 50%;
                transition: background 0.3s;
            }
            .notification-bell:hover {
                background: rgba(74, 222, 128, 0.1);
            }
            .notification-badge {
                position: absolute;
                top: 0;
                right: 0;
                background: #ef4444;
                color: white;
                border-radius: 50%;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: bold;
                min-width: 18px;
                text-align: center;
                animation: pulse 2s infinite;
            }
            .notification-dropdown {
                position: absolute;
                right: 0;
                top: 50px;
                width: 380px;
                max-height: 500px;
                overflow-y: auto;
                background: rgba(15, 23, 42, 0.95);
                border: 1px solid rgba(74, 222, 128, 0.2);
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
                z-index: 1000;
                padding: 12px;
                backdrop-filter: blur(10px);
            }
            .notification-item {
                padding: 12px 14px;
                border-radius: 8px;
                margin-bottom: 8px;
                transition: background 0.2s;
                border-left: 3px solid transparent;
                cursor: pointer;
            }
            .notification-item:hover {
                background: rgba(74, 222, 128, 0.08);
            }
            .notification-item.unread {
                border-left-color: #4ade80;
                background: rgba(74, 222, 128, 0.05);
            }
            .notification-item .title {
                font-weight: 600;
                color: #e5e7eb;
                font-size: 14px;
            }
            .notification-item .message {
                color: #94a3b8;
                font-size: 13px;
                margin-top: 4px;
                line-height: 1.4;
            }
            .notification-item .time {
                color: #64748b;
                font-size: 11px;
                margin-top: 6px;
            }
            .notification-item .actions {
                margin-top: 8px;
                display: flex;
                gap: 8px;
            }
            .notification-item .actions button {
                background: rgba(74, 222, 128, 0.15);
                border: none;
                color: #4ade80;
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 12px;
                cursor: pointer;
                transition: background 0.2s;
            }
            .notification-item .actions button:hover {
                background: rgba(74, 222, 128, 0.25);
            }
            .notification-empty {
                color: #94a3b8;
                text-align: center;
                padding: 30px 20px;
                font-size: 14px;
            }
            .notification-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding-bottom: 10px;
                border-bottom: 1px solid rgba(74, 222, 128, 0.1);
                margin-bottom: 10px;
            }
            .notification-header h4 {
                color: #e5e7eb;
                margin: 0;
                font-size: 16px;
            }
            .notification-header button {
                background: none;
                border: none;
                color: #4ade80;
                font-size: 13px;
                cursor: pointer;
            }
            .notification-header button:hover {
                text-decoration: underline;
            }
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
            }
            .notification-footer {
                padding-top: 10px;
                border-top: 1px solid rgba(74, 222, 128, 0.1);
                text-align: center;
                margin-top: 10px;
            }
            .notification-footer button {
                background: none;
                border: none;
                color: #64748b;
                font-size: 13px;
                cursor: pointer;
                transition: color 0.2s;
            }
            .notification-footer button:hover {
                color: #4ade80;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Bell icon with badge
        bell_html = f"""
        <div class="notification-bell" id="notification-bell">
            🔔
            {f'<span class="notification-badge">{unread_count}</span>' if unread_count > 0 else ''}
        </div>
        """
        
        st.markdown(bell_html, unsafe_allow_html=True)
        
        # Dropdown toggle (using session state)
        if 'show_notifications' not in st.session_state:
            st.session_state.show_notifications = False
        
        # Check if bell was clicked (via JavaScript)
        st.markdown("""
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const bell = document.getElementById('notification-bell');
                if (bell) {
                    bell.addEventListener('click', function() {
                        const event = new CustomEvent('streamlit-toggle-notifications');
                        document.dispatchEvent(event);
                    });
                }
            });
        </script>
        """, unsafe_allow_html=True)
        
        # Toggle button (workaround for Streamlit)
        if st.button("🔔", key="notification_bell_toggle", help="Toggle notifications"):
            st.session_state.show_notifications = not st.session_state.show_notifications
            st.rerun()
        
        # Show notification dropdown
        if st.session_state.show_notifications:
            _render_notification_dropdown(user_id, manager)
        
    except ImportError as e:
        logger.warning(f"Notification module not available: {e}")
    except Exception as e:
        logger.error(f"Failed to render notification bell: {e}")


def _render_notification_dropdown(user_id: int, manager) -> None:
    """Render the notification dropdown content."""
    try:
        notifications = get_user_notifications(user_id, include_read=False, limit=20)
        
        st.markdown('<div class="notification-dropdown">', unsafe_allow_html=True)
        
        # Header
        st.markdown("""
        <div class="notification-header">
            <h4>🔔 Notifications</h4>
            <button id="mark_all_read">Mark all read</button>
        </div>
        """, unsafe_allow_html=True)
        
        # Mark all read button
        if st.button("Mark all read", key="mark_all_read_btn", use_container_width=True):
            mark_all_as_read(user_id)
            st.rerun()
        
        if not notifications:
            st.markdown("""
            <div class="notification-empty">
                🎉 You're all caught up!<br>
                <span style="font-size: 12px; color: #64748b;">No new notifications</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            for notif in notifications[:10]:
                priority_class = "unread" if not notif.read else ""
                priority_color = {
                    0: "#ef4444",  # CRITICAL
                    1: "#f59e0b",  # HIGH
                    2: "#3b82f6",  # MEDIUM
                    3: "#8b5cf6",  # LOW
                    4: "#64748b"   # INFO
                }.get(notif.priority.value, "#64748b")
                
                time_ago = _time_ago(notif.created_at)
                
                st.markdown(f"""
                <div class="notification-item {priority_class}" style="border-left-color: {priority_color};">
                    <div class="title">{notif.title}</div>
                    <div class="message">{notif.message}</div>
                    <div class="time">{time_ago}</div>
                    <div class="actions">
                        {f'<button onclick="window.location.href=\'{notif.action_url}\'" style="background: rgba(74,222,128,0.15); border: none; color: #4ade80; padding: 4px 12px; border-radius: 6px; font-size: 12px; cursor: pointer;">{notif.action_label}</button>' if notif.action_url and notif.action_label else ''}
                        <button onclick="mark_read('{notif.id}')">Mark read</button>
                        <button onclick="dismiss('{notif.id}')">Dismiss</button>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Mark read button for individual notification
                if st.button(f"✅ Read", key=f"mark_read_{notif.id}"):
                    mark_as_read(user_id, notif.id)
                    st.rerun()
            
            if len(notifications) > 10:
                st.markdown(f"""
                <div class="notification-footer">
                    <button>View all {len(notifications)} notifications</button>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
    except Exception as e:
        logger.error(f"Failed to render notification dropdown: {e}")
        st.error("Failed to load notifications")


def _time_ago(dt: datetime) -> str:
    """Format time ago string."""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds // 3600 > 0:
        return f"{diff.seconds // 3600}h ago"
    elif diff.seconds // 60 > 0:
        return f"{diff.seconds // 60}m ago"
    else:
        return "Just now"


def render_notification_settings(user_id: int) -> None:
    """
    Render notification settings UI.
    
    Args:
        user_id: User ID
    """
    try:
        from src.lib.notification_manager import get_notification_manager
        
        manager = get_notification_manager()
        prefs = manager.get_preferences(user_id)
        
        st.markdown("### 🔔 Notification Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            email_enabled = st.checkbox(
                "📧 Email Notifications",
                value=prefs.email_enabled,
                help="Receive notifications via email"
            )
            
            push_enabled = st.checkbox(
                "📱 Push Notifications",
                value=prefs.push_enabled,
                help="Receive push notifications on mobile"
            )
            
            in_app_enabled = st.checkbox(
                "💬 In-App Notifications",
                value=prefs.in_app_enabled,
                help="Receive notifications within the app"
            )
        
        with col2:
            digest_enabled = st.checkbox(
                "📊 Weekly Digest",
                value=prefs.digest_enabled,
                help="Receive weekly progress digest"
            )
            
            email_frequency = st.selectbox(
                "📅 Email Frequency",
                options=["daily", "weekly", "monthly"],
                index=["daily", "weekly", "monthly"].index(prefs.email_frequency),
                help="How often to send email notifications"
            )
            
            reminder_interval = st.number_input(
                "📆 Reminder Interval (days)",
                min_value=1,
                max_value=30,
                value=prefs.reminder_interval_days,
                help="Days between assessment reminders"
            )
        
        # Quiet hours
        st.markdown("### 🌙 Quiet Hours")
        col3, col4 = st.columns(2)
        
        with col3:
            quiet_start = st.number_input(
                "Start (hour)",
                min_value=0,
                max_value=23,
                value=prefs.quiet_hours_start,
                help="Quiet hours start (24h format)"
            )
        
        with col4:
            quiet_end = st.number_input(
                "End (hour)",
                min_value=0,
                max_value=23,
                value=prefs.quiet_hours_end,
                help="Quiet hours end (24h format)"
            )
        
        # Notification types
        st.markdown("### 📋 Notification Types")
        
        type_options = [
            "alert", "reminder", "achievement", "progress",
            "tip", "challenge", "social", "system", "budget", "streak"
        ]
        
        enabled_types = st.multiselect(
            "Enabled Notification Types",
            options=type_options,
            default=prefs.enabled_types,
            help="Select which types of notifications you want to receive"
        )
        
        # Save button
        if st.button("💾 Save Preferences", use_container_width=True):
            manager.update_preferences(
                user_id,
                email_enabled=email_enabled,
                push_enabled=push_enabled,
                in_app_enabled=in_app_enabled,
                digest_enabled=digest_enabled,
                email_frequency=email_frequency,
                reminder_interval_days=reminder_interval,
                quiet_hours_start=quiet_start,
                quiet_hours_end=quiet_end,
                enabled_types=enabled_types
            )
            st.success("✅ Notification preferences saved!")
            st.rerun()
            
    except Exception as e:
        logger.error(f"Failed to render notification settings: {e}")
        st.error("Failed to load notification settings")