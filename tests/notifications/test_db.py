"""
Tests for Notification Database Engine.
"""

import pytest
import os
import sqlite3
from src.notifications.db import NotificationDB
from src.notifications.models import NotificationPreference, NotificationPayload

@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "test_notifications.db")
    db = NotificationDB(db_path=db_path)
    yield db
    if os.path.exists(db_path):
        os.remove(db_path)

def test_init_tables(temp_db):
    conn = temp_db._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    assert "notification_preferences" in tables
    assert "notifications" in tables
    conn.close()

def test_preferences_crud(temp_db):
    # Get defaults
    pref = temp_db.get_preferences(99)
    assert pref.user_id == 99
    assert pref.email_enabled is True
    
    # Update
    pref.email_enabled = False
    pref.opted_out_categories = ["system"]
    assert temp_db.save_preferences(pref) is True
    
    # Reload
    loaded = temp_db.get_preferences(99)
    assert loaded.email_enabled is False
    assert "system" in loaded.opted_out_categories

def test_notifications_crud(temp_db):
    payload = NotificationPayload(user_id=1, title="Hello", category="general")
    assert temp_db.insert_notification(payload) is True
    
    pending = temp_db.get_pending_notifications()
    assert len(pending) == 1
    assert pending[0].id == payload.id
    
    # Update status
    assert temp_db.update_notification_status(payload.id, "sent") is True
    
    pending_after = temp_db.get_pending_notifications()
    assert len(pending_after) == 0
    
    # Check history
    history = temp_db.get_user_history(1)
    assert len(history) == 1
    assert history[0].status == "sent"
    
def test_mark_all_read(temp_db):
    p1 = NotificationPayload(user_id=2, status="sent")
    p2 = NotificationPayload(user_id=2, status="sent")
    p3 = NotificationPayload(user_id=2, status="read") # Already read
    
    temp_db.insert_notification(p1)
    temp_db.insert_notification(p2)
    temp_db.insert_notification(p3)
    
    assert temp_db.mark_all_read(2) is True
    
    unread = temp_db.get_user_history(2, unread_only=True)
    assert len(unread) == 0

def test_deduplication(temp_db):
    p1 = NotificationPayload(user_id=3, title="Alert", dedupe_key="alert_123")
    temp_db.insert_notification(p1)
    
    # Should exist
    assert temp_db.check_dedupe_exists(3, "alert_123", window_hours=24) is True
    # Different key shouldn't exist
    assert temp_db.check_dedupe_exists(3, "alert_456", window_hours=24) is False
    # Different user shouldn't exist
    assert temp_db.check_dedupe_exists(4, "alert_123", window_hours=24) is False
