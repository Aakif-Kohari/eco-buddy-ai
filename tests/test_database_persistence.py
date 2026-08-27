"""Comprehensive database persistence and transaction tests.

Verifies data integrity, transactional consistency, constraint enforcement,
and failure recovery across CRUD operations on an isolated test database.
"""

from __future__ import annotations

import os
import sqlite3
import pytest
import uuid
from typing import Generator

from database_connection import (
    create_connection,
    database_connection,
    execute_with_retry,
)
import database as db
from invalidation import invalidate_all_db_caches


@pytest.fixture
def isolated_db(tmp_path) -> Generator[str, None, None]:
    """Provide an isolated, initialized database path for each test."""
    db_file = str(tmp_path / f"test_db_{uuid.uuid4().hex[:8]}.db")
    original_db = db.DB_NAME
    db.DB_NAME = db_file

    try:
        # Initialize schema and run migrations
        success = db.init_db()
        assert success is True, "Database initialization must succeed"
        invalidate_all_db_caches()
        yield db_file
    finally:
        db.DB_NAME = original_db
        invalidate_all_db_caches()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


def test_create_and_retrieve_entity(isolated_db: str):
    """Verify newly created entities can be persisted and retrieved accurately."""
    username = f"user_{uuid.uuid4().hex[:6]}"
    email = f"{username}@test.com"
    password = "SecurePassword123!"

    created = db.create_user(username, email, password, anonymous_leaderboard=False)
    assert created is True

    user = db.get_user_by_username(username)
    assert user is not None
    assert user["username"] == username
    assert user["email"] == email
    assert user["anonymous_leaderboard"] is False

    verified = db.verify_user(username, password)
    assert verified is not None
    assert verified["id"] == user["id"]
    assert verified["username"] == username


def test_update_modifies_only_intended_fields(isolated_db: str):
    """Verify updates modify only the intended fields and leave other fields intact."""
    username = f"user_{uuid.uuid4().hex[:6]}"
    email = f"{username}@test.com"
    password = "SecurePassword123!"

    db.create_user(username, email, password, anonymous_leaderboard=False)
    user_before = db.get_user_by_username(username)
    assert user_before is not None
    user_id = user_before["id"]

    # Update leaderboard preference
    update_res = db.update_user_leaderboard_preference(user_id, True)
    assert update_res is True

    user_after = db.get_user_by_username(username)
    assert user_after is not None
    assert user_after["id"] == user_id
    assert user_after["username"] == username
    assert user_after["email"] == email  # Unchanged
    assert user_after["anonymous_leaderboard"] is True  # Changed


def test_delete_and_undo_assessment_lifecycle(isolated_db: str):
    """Verify deleted records are no longer accessible in active queries and undo/restore work."""
    username = f"user_{uuid.uuid4().hex[:6]}"
    email = f"{username}@test.com"
    password = "SecurePassword123!"
    db.create_user(username, email, password)
    user = db.get_user_by_username(username)
    assert user is not None
    user_id = user["id"]

    # Save assessment
    saved = db.save_assessment(
        user_id=user_id,
        transport="Electric Car",
        distance=50.0,
        electricity=120.0,
        diet="Vegan",
        flights=0,
        footprint=150.5,
        eco_score=85,
    )
    assert saved is True

    assessments = db.get_assessments(user_id)
    assert len(assessments) == 1

    # Undo / delete the assessment
    undo_success, msg, undone_rec = db.undo_last_assessment(user_id)
    assert undo_success is True
    assert undone_rec is not None

    # Verify deleted record is no longer accessible via get_assessments
    assessments_after_delete = db.get_assessments(user_id)
    assert len(assessments_after_delete) == 0

    # Verify restore brings it back
    restore_success, restore_msg, restored_rec = db.restore_last_deleted_assessment(user_id)
    assert restore_success is True
    assert len(db.get_assessments(user_id)) == 1


def test_duplicate_entries_rejected_by_unique_constraints(isolated_db: str):
    """Verify duplicate entries violate defined unique constraints (username/email)."""
    username = "duplicate_test_user"
    email = "duplicate@test.com"
    password = "Password123"

    first_created = db.create_user(username, email, password)
    assert first_created is True

    # Same username, different email
    dup_username = db.create_user(username, "different@test.com", password)
    assert dup_username is False

    # Different username, same email
    dup_email = db.create_user("other_user", email, password)
    assert dup_email is False


def test_referential_integrity_and_foreign_key_constraints(isolated_db: str):
    """Verify related records maintain referential integrity and foreign keys are enforced."""
    with database_connection(isolated_db) as conn:
        fk_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk_enabled == 1

        # Attempt inserting a carbon budget for a non-existent user_id
        non_existent_user_id = 999999
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO carbon_budgets (user_id, budget_type, budget_limit)
                VALUES (?, ?, ?)
                """,
                (non_existent_user_id, "monthly", 500.0),
            )


def test_operations_against_non_existent_records(isolated_db: str):
    """Verify operations against non-existent records return predictable errors or None."""
    non_existent_user = db.get_user_by_username("non_existent_user_xyz")
    assert non_existent_user is None

    verified = db.verify_user("non_existent_user_xyz", "password")
    assert verified is None

    budget = db.get_carbon_budget(999999)
    assert budget is None

    undo_success, msg, undone_rec = db.undo_last_assessment(user_id=999999)
    assert undo_success is False
    assert undone_rec is None
    assert "No assessment found" in msg


def test_transaction_rollback_on_partial_failure(isolated_db: str):
    """Verify failed transactions roll back all intermediate changes atomically."""
    with database_connection(isolated_db) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS test_atomic (id INTEGER PRIMARY KEY, val TEXT)"
        )

    # Multi-step operation where 2nd step fails
    with pytest.raises(ValueError, match="simulated failure"):
        with database_connection(isolated_db) as conn:
            conn.execute("INSERT INTO test_atomic (val) VALUES ('step_1_ok')")
            # Step 2 fails
            raise ValueError("simulated failure")

    # Verify step_1_ok was rolled back
    with database_connection(isolated_db) as conn:
        rows = conn.execute("SELECT * FROM test_atomic").fetchall()
        assert len(rows) == 0


def test_invalid_data_types_and_malformed_payloads(isolated_db: str):
    """Verify constraint checks and malformed payloads are handled appropriately."""
    with database_connection(isolated_db) as conn:
        # Check NOT NULL constraint enforcement on users table
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (NULL, 'test@test.com', 'hash')"
            )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES ('user_null', NULL, 'hash')"
            )


def test_database_connection_failure_handling(tmp_path):
    """Verify database connection errors are properly caught and handled."""
    invalid_path = str(tmp_path / "non_existent_dir" / "nested" / "invalid.db")
    
    # Attempting to create connection with negative timeout
    with pytest.raises(ValueError, match="busy_timeout_ms cannot be negative"):
        create_connection(invalid_path, busy_timeout_ms=-1)

    # execute_with_retry with invalid max_attempts
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        execute_with_retry(lambda: None, max_attempts=0)
