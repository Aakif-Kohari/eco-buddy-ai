import pytest
import sqlite3
import os
import threading

# Set up test database BEFORE importing modules that use it
TEST_DB = "test_eco_credits.db"
os.environ["ECO_BUDDY_DB"] = TEST_DB

from eco_credits_ledger import mint_credits, transfer_credits, get_balance, verify_ledger_integrity
from database import init_db
import database
import eco_credits_ledger
from database_connection import database_connection

database.DB_NAME = TEST_DB
eco_credits_ledger.DB_NAME = TEST_DB

@pytest.fixture(autouse=True)
def setup_teardown():
    # Remove existing db if it exists
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    success = init_db()
    if not success:
        raise RuntimeError("init_db failed!")
    
    yield
    
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_minting_and_balance():
    assert get_balance("user1") == 0.0
    
    success = mint_credits("user1", 100.5, {"filename": "bill.pdf", "surplus": 100.5})
    assert success
    assert get_balance("user1") == 100.5
    
    assert verify_ledger_integrity()

def test_transfer():
    mint_credits("alice", 50.0, {})
    assert get_balance("alice") == 50.0
    
    # Successful transfer
    success = transfer_credits("alice", "bob", 20.0)
    assert success
    assert get_balance("alice") == 30.0
    assert get_balance("bob") == 20.0
    
    # Insufficient funds
    success = transfer_credits("alice", "bob", 50.0)
    assert not success
    assert get_balance("alice") == 30.0
    assert get_balance("bob") == 20.0
    
    assert verify_ledger_integrity()

def test_concurrency():
    mint_credits("charlie", 1000.0, {})
    
    def worker():
        for _ in range(50):
            transfer_credits("charlie", "dave", 1.0)
            
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert get_balance("charlie") == 500.0
    assert get_balance("dave") == 500.0
    assert verify_ledger_integrity()

def test_ledger_tampering():
    mint_credits("eve", 100.0, {})
    
    assert verify_ledger_integrity()
    
    # Tamper with the database manually
    with database_connection(TEST_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE eco_ledger_transactions SET amount = 200.0 WHERE id = 1")
        conn.commit()
        
    # The integrity check should now fail because the hash no longer matches the modified amount
    assert not verify_ledger_integrity()
