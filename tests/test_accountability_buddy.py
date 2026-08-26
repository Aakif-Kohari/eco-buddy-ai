import pytest
import sqlite3
from src.utils.accountability_buddy import BuddySystem

@pytest.fixture
def buddy_system():
    # Use in-memory db for testing
    db = BuddySystem(db_name=":memory:")
    
    # Initialize schema
    conn = sqlite3.connect(":memory:")
    # We must use the exact same in-memory DB across calls, but sqlite3.connect(":memory:") 
    # creates a new DB each time. So we'll use a temp file or shared URI memory DB.
    pass

# Actually, let's use a temp file to ensure connections see the same DB.
import tempfile
import os

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
    cursor.execute("CREATE TABLE assessments (id INTEGER PRIMARY KEY, user_id INTEGER, total_kg REAL)")
    cursor.execute("""
        CREATE TABLE buddy_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE buddy_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            synergy_score REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE buddy_nudges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Seed users
    cursor.execute("INSERT INTO users (id, username) VALUES (1, 'alice')")
    cursor.execute("INSERT INTO users (id, username) VALUES (2, 'bob')")
    cursor.execute("INSERT INTO users (id, username) VALUES (3, 'charlie')")
    
    # Seed assessments
    cursor.execute("INSERT INTO assessments (user_id, total_kg) VALUES (1, 100.0)")
    cursor.execute("INSERT INTO assessments (user_id, total_kg) VALUES (1, 50.0)")
    cursor.execute("INSERT INTO assessments (user_id, total_kg) VALUES (2, 200.0)")
    
    conn.commit()
    conn.close()
    
    yield path
    os.unlink(path)

@pytest.fixture
def buddy(temp_db):
    return BuddySystem(db_name=temp_db)

def test_get_user_by_username(buddy):
    user = buddy.get_user_by_username("alice")
    assert user is not None
    assert user["id"] == 1
    
    user_none = buddy.get_user_by_username("notfound")
    assert user_none is None

def test_send_buddy_request(buddy):
    # Success
    success, msg = buddy.send_buddy_request(1, 2)
    assert success is True
    
    # Self request
    success, msg = buddy.send_buddy_request(1, 1)
    assert success is False
    assert "yourself" in msg
    
    # Duplicate pending request
    success, msg = buddy.send_buddy_request(1, 2)
    assert success is False
    assert "pending request already exists" in msg

def test_accept_buddy_request(buddy):
    buddy.send_buddy_request(1, 2)
    reqs = buddy.get_pending_requests(2)
    assert len(reqs) == 1
    req_id = reqs[0]["id"]
    
    success, msg = buddy.accept_buddy_request(req_id)
    assert success is True
    
    # Verify they are buddies
    buddies = buddy.get_buddies(1)
    assert len(buddies) == 1
    assert buddies[0]["buddy_name"] == "bob"

def test_reject_buddy_request(buddy):
    buddy.send_buddy_request(1, 2)
    reqs = buddy.get_pending_requests(2)
    req_id = reqs[0]["id"]
    
    success, msg = buddy.reject_buddy_request(req_id)
    assert success is True
    
    buddies = buddy.get_buddies(1)
    assert len(buddies) == 0

def test_remove_buddy(buddy):
    buddy.send_buddy_request(1, 2)
    req_id = buddy.get_pending_requests(2)[0]["id"]
    buddy.accept_buddy_request(req_id)
    
    assert len(buddy.get_buddies(1)) == 1
    
    success, msg = buddy.remove_buddy(1, 2)
    assert success is True
    
    assert len(buddy.get_buddies(1)) == 0

def test_nudge_history_and_synergy(buddy):
    buddy.send_buddy_request(1, 2)
    req_id = buddy.get_pending_requests(2)[0]["id"]
    buddy.accept_buddy_request(req_id)
    
    buddy.send_nudge(1, 2, "Great job!")
    buddy.send_nudge(2, 1, "Thanks!")
    
    history = buddy.get_nudge_history(1, 2)
    assert len(history) == 2
    assert history[0]["message"] in ["Great job!", "Thanks!"]
    
    score = buddy.calculate_synergy_score(1, 2)
    # base 50 + 2 nudges * 5 = 60
    assert score == 60.0

def test_get_buddy_comparison(buddy):
    buddy.send_buddy_request(1, 2)
    req_id = buddy.get_pending_requests(2)[0]["id"]
    buddy.accept_buddy_request(req_id)
    
    buddy.send_nudge(1, 2, "Nudge!")
    
    comp = buddy.get_buddy_comparison(1, 2)
    assert comp["user1"]["total_footprint"] == 150.0  # 100 + 50
    assert comp["user2"]["total_footprint"] == 200.0
    assert comp["synergy_score"] == 55.0  # 50 + 1 * 5
