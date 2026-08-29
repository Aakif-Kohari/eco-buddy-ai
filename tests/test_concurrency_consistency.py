"""Concurrency and data consistency tests.

Tests concurrent record creation, concurrent updates, simultaneous deletions,
duplicate submissions, conflicting updates, and transaction collisions to verify
data integrity and consistency under concurrent thread operations.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator

import pytest

from src.core.database_connection import (
    create_connection,
    database_connection,
    execute_with_retry,
)
import src.core.database as db
from src.core.invalidation import invalidate_all_db_caches


@pytest.fixture
def isolated_db(tmp_path) -> Generator[str, None, None]:
    """Provide an isolated, initialized database path for each test."""
    db_file = str(tmp_path / f"test_concurrency_{uuid.uuid4().hex[:8]}.db")
    original_db = src.notifications.db.DB_NAME
    src.notifications.db.DB_NAME = db_file

    try:
        success = src.notifications.db.init_db()
        assert success is True, "Database initialization must succeed"
        invalidate_all_db_caches()
        yield db_file
    finally:
        src.notifications.db.DB_NAME = original_db
        invalidate_all_db_caches()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


def test_concurrent_record_creation(isolated_db: str):
    """Verify concurrent creation of distinct user records creates exact number without corruption."""
    num_workers = 10
    created_usernames = []

    def create_single_user(index: int) -> bool:
        uname = f"concurrent_user_{index}_{uuid.uuid4().hex[:4]}"
        email = f"{uname}@test.com"
        created_usernames.append(uname)
        return src.notifications.db.create_user(uname, email, "Password123!")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_single_user, i) for i in range(num_workers)]
        results = [f.result() for f in as_completed(futures)]

    assert all(results), "All unique user creations should succeed"

    with database_connection(isolated_db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE username LIKE 'concurrent_user_%'"
        ).fetchone()[0]
        assert count == num_workers


def test_concurrent_duplicate_submissions(isolated_db: str):
    """Verify simultaneous submissions of duplicate records only allow one to succeed."""
    target_username = f"race_user_{uuid.uuid4().hex[:6]}"
    target_email = f"{target_username}@test.com"
    num_threads = 8

    def try_create():
        return src.notifications.db.create_user(target_username, target_email, "Password123!")

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(try_create) for _ in range(num_threads)]
        results = [f.result() for f in as_completed(futures)]

    # Exactly 1 success, others fail due to UNIQUE constraint
    successes = sum(1 for r in results if r is True)
    assert successes == 1, f"Expected exactly 1 success, got {successes}"

    with database_connection(isolated_db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE username = ?",
            (target_username,),
        ).fetchone()[0]
        assert count == 1


def test_concurrent_conflicting_updates(isolated_db: str):
    """Verify concurrent updates to a shared user preference execute safely without state corruption."""
    uname = f"update_user_{uuid.uuid4().hex[:6]}"
    email = f"{uname}@test.com"
    src.notifications.db.create_user(uname, email, "Password123!", anonymous_leaderboard=False)
    user = src.notifications.db.get_user_by_username(uname)
    assert user is not None
    user_id = user["id"]

    num_threads = 10

    def toggle_preference(idx: int) -> bool:
        new_val = (idx % 2 == 0)
        return src.notifications.db.update_user_leaderboard_preference(user_id, new_val)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(toggle_preference, i) for i in range(num_threads)]
        results = [f.result() for f in as_completed(futures)]

    assert all(results)
    final_user = src.notifications.db.get_user_by_username(uname)
    assert final_user is not None
    assert isinstance(final_user["anonymous_leaderboard"], bool)


def test_concurrent_assessments_creation_and_activity_logging(isolated_db: str):
    """Verify concurrent assessment creations log and persist accurately across multiple threads."""
    uname = f"assess_user_{uuid.uuid4().hex[:6]}"
    email = f"{uname}@test.com"
    src.notifications.db.create_user(uname, email, "Password123!")
    user = src.notifications.db.get_user_by_username(uname)
    assert user is not None
    user_id = user["id"]

    num_assessments = 8

    def insert_task(idx: int) -> bool:
        return src.notifications.db.save_assessment(
            user_id=user_id,
            transport="Train",
            distance=15.0 + idx,
            electricity=30.0 + idx,
            diet="Vegan",
            flights=0,
            footprint=10.0 + idx,
            eco_score=90,
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(insert_task, i) for i in range(num_assessments)]
        results = [f.result() for f in as_completed(futures)]

    assert all(results), "All concurrent assessments should be saved successfully"

    # Invalidate cache to read fresh state from isolated DB
    invalidate_all_db_caches()
    assessments = src.notifications.db.get_assessments(user_id)
    assert len(assessments) == num_assessments


def test_concurrent_transactions_atomic_counters(isolated_db: str):
    """Verify concurrent transactions with atomic SQL increments resolve without data corruption."""
    with database_connection(isolated_db) as conn:
        conn.execute("CREATE TABLE counter (id INTEGER PRIMARY KEY, val INTEGER)")
        conn.execute("INSERT INTO counter (id, val) VALUES (1, 0)")

    def increment():
        def _txn():
            with database_connection(isolated_db, busy_timeout_ms=5000) as conn:
                conn.execute("UPDATE counter SET val = val + 1 WHERE id = 1")
        execute_with_retry(_txn, max_attempts=5)
        return True

    num_threads = 10
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(increment) for _ in range(num_threads)]
        results = [f.result() for f in as_completed(futures)]

    assert all(results)
    with database_connection(isolated_db) as conn:
        final_val = conn.execute("SELECT val FROM counter WHERE id = 1").fetchone()[0]
        assert final_val == num_threads
