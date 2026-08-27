"""
Tests for Notification Scheduler.
"""

import pytest
import os
import sqlite3
from datetime import datetime, timedelta
from src.notifications.scheduler import NotificationScheduler
from src.notifications.dispatcher import NotificationDispatcher
from src.notifications.db import NotificationDB
from database import DB_NAME

@pytest.fixture
def test_setup():
    # We will use the live DB_NAME but in a transactional way if possible
    # Since we can't easily mock the global DB_NAME for the scheduler's direct imports,
    # we'll create a dummy tables in the current test DB if they don't exist.
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_preferences (
            user_id INTEGER PRIMARY KEY,
            weekly_digest_enabled BOOLEAN
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activities (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            title TEXT,
            status TEXT,
            target_date TEXT
        )
    ''')
    conn.commit()
    
    # Insert test data
    cursor.execute("INSERT OR REPLACE INTO notification_preferences (user_id, weekly_digest_enabled) VALUES (999, 1)")
    cursor.execute("INSERT INTO user_activities (user_id, date) VALUES (999, date('now'))")
    
    # Due in 3 days
    due_date = (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO goals (id, user_id, title, status, target_date) VALUES (999, 999, 'Test Goal', 'active', ?)", (due_date,))
    conn.commit()
    
    yield conn
    
    # Cleanup
    cursor.execute("DELETE FROM notification_preferences WHERE user_id = 999")
    cursor.execute("DELETE FROM user_activities WHERE user_id = 999")
    cursor.execute("DELETE FROM goals WHERE id = 999")
    cursor.execute("DELETE FROM notifications WHERE user_id = 999")
    conn.commit()
    conn.close()

def test_generate_weekly_digests(test_setup):
    db = NotificationDB()
    dispatcher = NotificationDispatcher(db=db)
    scheduler = NotificationScheduler(dispatcher=dispatcher)
    
    scheduler.generate_weekly_digests()
    
    # Check if a notification was inserted
    pending = db.get_pending_notifications()
    # Filter for our test user
    test_notifs = [n for n in pending if n.user_id == 999 and n.category == "digest"]
    assert len(test_notifs) == 1
    assert "You logged 1 sustainable activities" in test_notifs[0].message

def test_check_goal_reminders(test_setup):
    db = NotificationDB()
    dispatcher = NotificationDispatcher(db=db)
    scheduler = NotificationScheduler(dispatcher=dispatcher)
    
    scheduler.check_goal_reminders()
    
    pending = db.get_pending_notifications()
    test_notifs = [n for n in pending if n.user_id == 999 and n.category == "goals"]
    assert len(test_notifs) == 1
    assert "Test Goal" in test_notifs[0].message
    assert "3 days" in test_notifs[0].message
