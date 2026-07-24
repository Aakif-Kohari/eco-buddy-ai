import os
import pytest
import database as db

TEST_DB = "test_eco_buddy_core.db"


@pytest.fixture(autouse=True)
def setup_teardown():
    db.DB_NAME = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    db.init_db()
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_init_db_creates_table():
    assert os.path.exists(TEST_DB)


def test_save_and_get_assessment():
    success = db.save_assessment("Car", 20, 250, "Non-Vegetarian", 2, 3200, 65)
    assert success is True

    assessments = db.get_assessments()
    assert len(assessments) == 1
    row = assessments[0]
    assert row[2] == "Car"
    assert row[3] == 20
    assert row[4] == 250
    assert row[5] == "Non-Vegetarian"
    assert row[6] == 2
    assert row[7] == 3200
    assert row[8] == 65


def test_get_assessments_empty_initially():
    assessments = db.get_assessments()
    assert len(assessments) == 0


def test_multiple_assessments_ordered_by_date():
    db.save_assessment("Car", 10, 100, "Vegetarian", 0, 500, 90)
    db.save_assessment("Bus", 30, 200, "Non-Vegetarian", 3, 4000, 40)
    assessments = db.get_assessments()
    assert len(assessments) == 2
    assert assessments[0][7] >= assessments[1][7]
