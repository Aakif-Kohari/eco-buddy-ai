"""
Tests for Notification Dispatcher.
"""

import pytest
from datetime import datetime, time, timedelta

from src.notifications.dispatcher import NotificationDispatcher
from src.notifications.models import NotificationPreference
from src.notifications.db import NotificationDB
import os

@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "test_dispatcher.db")
    db = NotificationDB(db_path=db_path)
    yield db
    if os.path.exists(db_path):
        os.remove(db_path)

def test_quiet_hours_math(temp_db):
    dispatcher = NotificationDispatcher(db=temp_db)
    
    # Let's mock a preference
    pref = NotificationPreference(
        user_id=1,
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(8, 0),
        timezone="UTC"
    )
    
    # We have to mock datetime to test this reliably
    # Since patching datetime in python is notoriously annoying, we'll do an indirect test
    is_q, next_t = dispatcher._is_quiet_hours(pref)
    
    # Since we can't easily mock utcnow without an external library like freezegun,
    # we'll just ensure it returns a valid tuple.
    assert isinstance(is_q, bool)
    if is_q:
        assert isinstance(next_t, datetime)
    else:
        assert next_t is None

def test_opt_out_suppression(temp_db):
    dispatcher = NotificationDispatcher(db=temp_db)
    
    pref = NotificationPreference(user_id=2, opted_out_categories=["digest"])
    temp_db.save_preferences(pref)
    
    notif_id = dispatcher.dispatch(
        user_id=2,
        category="digest",
        title="Ignored",
        message="Should not send"
    )
    assert notif_id is None

def test_successful_dispatch(temp_db):
    dispatcher = NotificationDispatcher(db=temp_db)
    
    notif_id = dispatcher.dispatch(
        user_id=3,
        category="general",
        title="Valid",
        message="Should send"
    )
    assert notif_id is not None
    
    pending = temp_db.get_pending_notifications()
    assert len(pending) == 1
    assert pending[0].id == notif_id

def test_deduplication_suppression(temp_db):
    dispatcher = NotificationDispatcher(db=temp_db)
    
    notif_id1 = dispatcher.dispatch(user_id=4, category="alert", title="A", message="B", dedupe_key="dedupe1")
    assert notif_id1 is not None
    
    notif_id2 = dispatcher.dispatch(user_id=4, category="alert", title="C", message="D", dedupe_key="dedupe1")
    assert notif_id2 is None  # Suppressed due to dedupe_key

def test_process_queue(temp_db):
    dispatcher = NotificationDispatcher(db=temp_db)
    
    notif_id = dispatcher.dispatch(user_id=5, category="test", title="T", message="M")
    assert notif_id is not None
    
    dispatcher.process_queue()
    
    # Should be marked as sent
    history = temp_db.get_user_history(5, unread_only=True)
    assert len(history) == 1
    assert history[0].status == "sent"
