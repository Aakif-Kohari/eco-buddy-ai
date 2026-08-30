import os
import uuid
import time
import sqlite3
import pytest

from src.core.rate_limiter import CompositeRateLimiter
from src.core.api_auth import init_api_keys_db, generate_api_key
from src.core.database_connection import database_connection

@pytest.fixture
def setup_isolated_db() -> str:
    """Fixture to create and configure an isolated, unique SQLite test database."""
    unique_db_name = f"test_eco_buddy_{uuid.uuid4().hex[:8]}.db"
    
    # Store original and set new env var
    original_db = os.environ.get("ECO_BUDDY_DB")
    os.environ["ECO_BUDDY_DB"] = unique_db_name

    # Need to also patch it in modules where it was imported globally, if needed.
    # But since they do `DB_NAME = os.getenv("ECO_BUDDY_DB", ...)`, modifying os.environ
    # before import is best. But tests run after imports. So we explicitly mock if needed.
    import src.core.rate_limiter as rl
    import src.core.api_auth as auth
    
    rl.DB_NAME = unique_db_name
    auth.DB_NAME = unique_db_name

    # Initialize the tables
    init_api_keys_db()
    
    yield unique_db_name

    # Cleanup
    if os.path.exists(unique_db_name):
        try:
            os.remove(unique_db_name)
        except OSError:
            pass
            
    if original_db is not None:
        os.environ["ECO_BUDDY_DB"] = original_db
    else:
        del os.environ["ECO_BUDDY_DB"]


def test_rate_limiter_allows_under_limit(setup_isolated_db):
    key_info = generate_api_key("Test App", rate_limit=5)
    key_id = key_info["id"]
    
    is_allowed, status, headers = CompositeRateLimiter.check_limit(key_id, rate_limit=5, endpoint="/test")
    
    assert is_allowed is True
    assert status == 200

def test_rate_limiter_blocks_over_limit(setup_isolated_db):
    key_info = generate_api_key("Test App", rate_limit=2)
    key_id = key_info["id"]
    
    # Allowed
    is_allowed1, _, _ = CompositeRateLimiter.check_limit(key_id, rate_limit=2, endpoint="/test")
    # Allowed
    is_allowed2, _, _ = CompositeRateLimiter.check_limit(key_id, rate_limit=2, endpoint="/test")
    # Blocked
    is_allowed3, status3, headers3 = CompositeRateLimiter.check_limit(key_id, rate_limit=2, endpoint="/test")
    
    assert is_allowed1 is True
    assert is_allowed2 is True
    assert is_allowed3 is False
    assert status3 == 429
    assert "Retry-After" in headers3

def test_rate_limiter_zero_limit(setup_isolated_db):
    key_info = generate_api_key("Test App", rate_limit=0)
    key_id = key_info["id"]
    
    is_allowed, status, headers = CompositeRateLimiter.check_limit(key_id, rate_limit=0, endpoint="/test")
    
    assert is_allowed is False
    assert status == 429

def test_rate_limiter_stats(setup_isolated_db):
    key_info = generate_api_key("Test App", rate_limit=10)
    key_id = key_info["id"]
    
    CompositeRateLimiter.check_limit(key_id, rate_limit=10, endpoint="/test1")
    CompositeRateLimiter.check_limit(key_id, rate_limit=10, endpoint="/test2")
    
    stats = CompositeRateLimiter.get_usage_stats(key_id=key_id)
    assert len(stats) == 2
    assert stats[0]["endpoint"] == "/test2"
    assert stats[1]["endpoint"] == "/test1"
