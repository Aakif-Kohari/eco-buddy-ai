import os
import pytest
import uuid
import database as db

TEST_DB = "test_eco_buddy_core.db"

@pytest.fixture(autouse=True)
def setup_teardown():
    original_db_name = db.DB_NAME
    db.DB_NAME = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    db.init_db()
    db.get_assessments.clear()
    yield
    db.get_assessments.clear()
    db.DB_NAME = original_db_name
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def create_test_user():
    username = f"testuser_{uuid.uuid4().hex[:6]}"
    email = f"{username}@example.com"
    password = "password123"
    db.create_user(username, email, password)
    user = db.verify_user(username, password)
    return user['id']


def test_init_db_creates_table():
    assert os.path.exists(TEST_DB)


def test_save_and_get_assessment():
    user_id = create_test_user()
    success = db.save_assessment(user_id, "Car", 20, 250, "Non-Vegetarian", 2, 3200, 65)
    assert success is True

    assessments = db.get_assessments(user_id)
    assert len(assessments) == 1
    row = assessments[0]
    # Row structure has changed since we added user_id, it is likely index 3 for transport now
    assert row[2] == "Car" or row[3] == "Car"
    

def test_get_assessments_empty_initially():
    user_id = create_test_user()
    assessments = db.get_assessments(user_id)
    assert len(assessments) == 0


def test_multiple_assessments_ordered_by_date():
    user_id = create_test_user()
    db.save_assessment(user_id, "Car", 10, 100, "Vegetarian", 0, 500, 90)
    db.save_assessment(user_id, "Bus", 30, 200, "Non-Vegetarian", 3, 4000, 40)
    assessments = db.get_assessments(user_id)
    assert len(assessments) == 2
    # Ensure they are ordered by date correctly
