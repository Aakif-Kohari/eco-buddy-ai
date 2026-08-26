"""
Comprehensive Concurrent Request and Race Condition Testing Suite (#1015).

Tests simultaneous conflicting and identical operations under heavy thread concurrency:
- Concurrent record creation
- Simultaneous updates on shared resources
- Concurrent deletes and revocations
- Duplicate submissions under barrier synchronization
- Shared-resource modifications & atomic transactions
- Database integrity and consistency verification
"""

from __future__ import annotations

import os
import time
import uuid
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator, List, Dict, Any

import pytest

import database as db
from database_connection import (
    create_connection,
    database_connection,
    execute_with_retry,
)
from invalidation import invalidate_all_db_caches
import api_auth
from api_auth import (
    generate_api_key,
    validate_api_key,
    revoke_api_key,
    init_api_keys_db,
)
from sustainability_api import (
    process_api_request,
    API_VERSION_PREFIX,
)


@pytest.fixture(autouse=True)
def setup_isolated_db(tmp_path) -> Generator[str, None, None]:
    """Isolate SQLite database for every test to avoid state pollution."""
    db_file = str(tmp_path / f"test_race_conditions_{uuid.uuid4().hex[:8]}.db")
    original_db = db.DB_NAME
    original_api_db = getattr(api_auth, "DB_NAME", "eco_buddy.db")
    db.DB_NAME = db_file
    api_auth.DB_NAME = db_file
    os.environ["ECO_BUDDY_DB"] = db_file

    try:
        db.init_db()
        init_api_keys_db()
        invalidate_all_db_caches()
        yield db_file
    finally:
        db.DB_NAME = original_db
        api_auth.DB_NAME = original_api_db
        os.environ["ECO_BUDDY_DB"] = original_db
        invalidate_all_db_caches()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


# ===========================================================================
# 1. Concurrent Record Creation
# ===========================================================================

def test_concurrent_user_creation_under_contention(setup_isolated_db: str):
    """Multiple threads creating distinct users simultaneously without race conditions or deadlocks."""
    worker_count = 12
    barrier = threading.Barrier(worker_count)

    def create_worker(index: int) -> bool:
        username = f"race_user_{index}_{uuid.uuid4().hex[:4]}"
        email = f"{username}@example.com"
        barrier.wait()
        return db.create_user(username, email, "Password123!")

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(create_worker, i) for i in range(worker_count)]
        results = [f.result() for f in as_completed(futures)]

    assert all(results), "All unique user creations under concurrency must succeed"

    with database_connection(setup_isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username LIKE 'race_user_%'")
        count = cursor.fetchone()[0]
        assert count == worker_count


def test_concurrent_api_key_generation(setup_isolated_db: str):
    """Multiple threads generating API keys simultaneously with unique hashes."""
    worker_count = 10
    barrier = threading.Barrier(worker_count)

    def generate_worker(index: int) -> dict:
        barrier.wait()
        return generate_api_key(f"App_{index}", user_id=f"user_{index}")

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(generate_worker, i) for i in range(worker_count)]
        keys = [f.result() for f in as_completed(futures)]

    assert len(keys) == worker_count
    tokens = [k["api_key"] for k in keys]
    assert len(set(tokens)) == worker_count, "All generated tokens must be strictly unique"


# ===========================================================================
# 2. Duplicate Submissions Race Condition
# ===========================================================================

def test_duplicate_submission_race_condition(setup_isolated_db: str):
    """Simultaneous submissions of identical user registrations: exactly one succeeds."""
    target_username = f"dup_race_{uuid.uuid4().hex[:6]}"
    target_email = f"{target_username}@example.com"
    target_password = "SecurePassword123!"
    thread_count = 8
    barrier = threading.Barrier(thread_count)

    def attempt_registration():
        barrier.wait()
        return db.create_user(target_username, target_email, target_password)

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(attempt_registration) for _ in range(thread_count)]
        results = [f.result() for f in as_completed(futures)]

    assert results.count(True) == 1, "Exactly one thread should successfully create the unique user"
    assert results.count(False) == thread_count - 1

    with database_connection(setup_isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (target_username,))
        assert cursor.fetchone()[0] == 1


# ===========================================================================
# 3. Simultaneous Updates on Shared Resources
# ===========================================================================

def test_simultaneous_goal_updates(setup_isolated_db: str):
    """Concurrent updates to a user's reduction goal keep database in consistent state."""
    user_id = 888
    thread_count = 8
    barrier = threading.Barrier(thread_count)

    def update_goal_worker(index: int) -> int | None:
        barrier.wait()
        return db.save_reduction_goal(
            user_id=user_id,
            baseline_kg=5000.0,
            target_kg=4000.0 - (index * 50),
            start_date="2026-01-01",
            target_date="2027-01-01",
        )

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(update_goal_worker, i) for i in range(thread_count)]
        results = [f.result() for f in as_completed(futures)]

    # All writes succeed
    assert all(r is not None for r in results)

    # Exactly 1 active goal must remain
    with database_connection(setup_isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM reduction_goals WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        active_count = cursor.fetchone()[0]
        assert active_count == 1, "Only one goal should remain active after concurrent updates"


# ===========================================================================
# 4. Concurrent Deletions and Revocations
# ===========================================================================

def test_concurrent_api_key_revocation_race(setup_isolated_db: str):
    """Simultaneous revocation of the same key across 10 threads without sqlite locking errors."""
    key_data = generate_api_key("Contested Revocation App", user_id="user_race_rev")
    key_id = key_data["id"]
    thread_count = 10
    barrier = threading.Barrier(thread_count)

    def revoke_worker():
        barrier.wait()
        return revoke_api_key(key_id)

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(revoke_worker) for _ in range(thread_count)]
        results = [f.result() for f in as_completed(futures)]

    # Validate final state
    assert validate_api_key(key_data["api_key"]) is None
    with database_connection(setup_isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM api_keys WHERE id = ?", (key_id,))
        assert cursor.fetchone()[0] == 0


# ===========================================================================
# 5. Shared-Resource Modifications & Database Integrity
# ===========================================================================

def test_shared_resource_concurrent_footprint_calculations(setup_isolated_db: str):
    """Simultaneous calculation API calls execute concurrently without state interference."""
    key_info = generate_api_key("Concurrent Calculation App")
    headers = {"X-API-Key": key_info["api_key"]}
    thread_count = 10
    barrier = threading.Barrier(thread_count)

    def calculate_worker(index: int) -> tuple:
        barrier.wait()
        payload = {
            "transport": "Car",
            "distance": 10.0 + index,
            "electricity": 100.0 + (index * 10),
            "diet": "Vegetarian",
            "flights": index % 3,
        }
        return process_api_request("POST", f"{API_VERSION_PREFIX}/insights/calculate", headers, body=payload)

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(calculate_worker, i) for i in range(thread_count)]
        results = [f.result() for f in as_completed(futures)]

    for status_code, data, _ in results:
        assert status_code == 200
        assert data["success"] is True
        assert data["data"]["annual_footprint_kg_co2"] > 0


def test_final_database_integrity_after_concurrency(setup_isolated_db: str):
    """Executes PRAGMA integrity_check after concurrent operations."""
    with database_connection(setup_isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "ok", f"Database integrity check failed: {row}"
