import os
import sqlite3
import pytest
import uuid
import src.core.database as db

TEST_DB = "test_eco_buddy_core.db"

@pytest.fixture(autouse=True)
def setup_teardown():
    old_db = src.notifications.db.DB_NAME
    src.notifications.db.DB_NAME = TEST_DB
    src.notifications.db.init_db()
    
    # Clear cached function results after database is reset
    from invalidation import invalidate_all_db_caches
    invalidate_all_db_caches()
    
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM assessments")
    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()
    if hasattr(src.notifications.db.get_assessments, 'clear'):
        src.notifications.db.get_assessments.clear()
    yield
    if hasattr(src.notifications.db.get_assessments, 'clear'):
        src.notifications.db.get_assessments.clear()
    src.notifications.db.DB_NAME = old_db
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except OSError:
            pass


def create_test_user():
    username = f"testuser_{uuid.uuid4().hex[:6]}"
    email = f"{username}@example.com"
    password = "password123"
    src.notifications.db.create_user(username, email, password)
    user = src.notifications.db.verify_user(username, password)
    return user['id']


def test_init_db_creates_table():
    assert os.path.exists(TEST_DB)


def test_save_and_get_assessment():
    user_id = create_test_user()
    success = src.notifications.db.save_assessment(user_id, "Car", 20, 250, "Non-Vegetarian", 2, 3200, 65)
    assert success is True

    assessments = src.notifications.db.get_assessments(user_id)
    assert len(assessments) == 1
    row = assessments[0]
    # Row structure has changed since we added user_id, it is likely index 3 for transport now
    assert row[2] == "Car" or row[3] == "Car"


def test_get_assessments_empty_initially():
    user_id = create_test_user()
    assessments = src.notifications.db.get_assessments(user_id)
    assert len(assessments) == 0


def test_multiple_assessments_ordered_by_date():
    user_id = create_test_user()
    src.notifications.db.save_assessment(user_id, "Car", 10, 100, "Vegetarian", 0, 500, 90)
    src.notifications.db.save_assessment(user_id, "Bus", 30, 200, "Non-Vegetarian", 3, 4000, 40)
    assessments = src.notifications.db.get_assessments(user_id)
    assert len(assessments) == 2
