import pytest
import sqlite3
import os
import json
from src.utils.data_retention_engine import DataRetentionEngine

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_eco_buddy.db"
    
    # Create a dummy table for testing
    c = sqlite3.connect(db_path)
    c.executescript("""
        CREATE TABLE eco_journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            content TEXT
        );
        INSERT INTO eco_journal_entries (user_id, entry_date, content) VALUES (1, '2023-01-01', 'Old entry');
        INSERT INTO eco_journal_entries (user_id, entry_date, content) VALUES (1, '2026-01-01', 'New entry');
        INSERT INTO eco_journal_entries (user_id, entry_date, content) VALUES (2, '2023-01-01', 'Other user old entry');
    """)
    c.commit()
    c.close()
    
    engine = DataRetentionEngine(db_path=str(db_path))
    # Add a policy for the test
    engine.set_policy('eco_journal_entries', 'Logs', 365, 'delete')
    yield engine
    
def test_compute_stale_rows(test_db):
    stale_info = test_db.compute_stale_rows()
    assert stale_info['total_stale_rows'] == 2 # 2 entries from 2023
    
def test_run_cleanup(test_db):
    test_db.run_cleanup()
    c = test_db._conn()
    count = c.execute("SELECT COUNT(*) as cnt FROM eco_journal_entries").fetchone()['cnt']
    c.close()
    assert count == 1 # Only 2026 entry remains
    
    logs = test_db.get_audit_logs()
    assert len(logs) > 0
    assert logs[0]['rows_affected'] == 2

def test_purge_user_data(test_db):
    manifest = test_db.purge_user_data(user_id=1)
    assert 'eco_journal_entries' in manifest['deleted_records']
    assert manifest['deleted_records']['eco_journal_entries'] == 2 # Both old and new
    
    c = test_db._conn()
    count = c.execute("SELECT COUNT(*) as cnt FROM eco_journal_entries").fetchone()['cnt']
    c.close()
    assert count == 1 # User 2's entry remains
