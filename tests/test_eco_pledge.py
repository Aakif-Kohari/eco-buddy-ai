import pytest
import sqlite3
from src.core import database
from datetime import datetime
from src.community.eco_pledge import (
    create_pledge,
    support_pledge,
    get_public_pledges,
    get_user_pledges,
    verify_pledge_progress,
    complete_pledge
)

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch, tmp_path):
    """Setup a temporary database for testing."""
    test_db = tmp_path / "test_eco_buddy.db"
    monkeypatch.setattr("src.core.database.DB_NAME", str(test_db))
    monkeypatch.setattr("src.community.eco_pledge.DB_NAME", str(test_db))
    
    # Initialize basic tables needed for foreign keys
    with sqlite3.connect(str(test_db)) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
        cursor.execute("INSERT INTO users (id) VALUES ('test_user_1')")
        cursor.execute("INSERT INTO users (id) VALUES ('test_user_2')")
        conn.commit()
    
    # Run migrations
    import migrations.migrate_v12 as m12
    with sqlite3.connect(str(test_db)) as conn:
        m12.migrate(conn)
        
    yield str(test_db)

def test_create_pledge():
    pledge_id = create_pledge(
        user_id="test_user_1",
        title="Test Pledge",
        description="A test pledge",
        template_id="template_1",
        target_metric="test_metric",
        target_value=10.0,
        deadline="2026-12-31"
    )
    assert pledge_id is not None
    
    pledges = get_user_pledges("test_user_1")
    assert len(pledges) == 1
    assert pledges[0]['id'] == pledge_id
    assert pledges[0]['status'] == 'active'

def test_support_pledge():
    pledge_id = create_pledge(
        user_id="test_user_1",
        title="Test Pledge",
        description="A test",
        template_id=None,
        target_metric=None,
        target_value=None,
        deadline="2026-12-31"
    )
    
    # User 2 supports
    assert support_pledge(pledge_id, "test_user_2") is True
    # Supporting again should fail due to UNIQUE constraint
    assert support_pledge(pledge_id, "test_user_2") is False

def test_get_public_pledges():
    # Create multiple pledges
    p1 = create_pledge("test_user_1", "Pledge 1", "", None, None, None, "2026-12-31")
    p2 = create_pledge("test_user_2", "Pledge 2", "", None, None, None, "2026-12-31")
    
    support_pledge(p2, "test_user_1")
    
    public_pledges = get_public_pledges(sort_by='trending')
    assert len(public_pledges) == 2
    # p2 should be first because it has a supporter
    assert public_pledges[0]['id'] == p2
    assert public_pledges[0]['supporters_count'] == 1
    
def test_verify_pledge_progress():
    pledge_id = create_pledge("test_user_1", "Test", "", None, "test", 10.0, "2026-12-31")
    
    # In a real test, we would mock the database connection to return current_value = 10.0
    # For now, verify_pledge_progress just returns the row
    res = verify_pledge_progress(pledge_id)
    assert res['id'] == pledge_id
    assert res['status'] == 'active'

def test_complete_pledge():
    pledge_id = create_pledge("test_user_1", "Test", "", None, "test", 10.0, "2026-12-31")
    assert complete_pledge(pledge_id) is True
    
    res = verify_pledge_progress(pledge_id)
    assert res['status'] == 'completed'
