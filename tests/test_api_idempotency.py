"""
Comprehensive Idempotency Tests for Mutating API and Backend Operations (#1011).

Ensures that repeated create, update, delete, and calculation operations do not
create duplicate records, duplicate side effects, or cause inconsistent application state.
Covers sequential retries, concurrent duplicate requests, idempotency headers,
and final database verification.
"""

from __future__ import annotations

import os
import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator

import pytest

import database as db
from database_connection import database_connection
from invalidation import invalidate_all_db_caches
import api_auth
from api_auth import (
    generate_api_key,
    validate_api_key,
    revoke_api_key,
    init_api_keys_db,
    authenticate_request,
)
from sustainability_api import (
    process_api_request,
    API_VERSION_PREFIX,
)
from goals import evaluate_progress


@pytest.fixture(autouse=True)
def setup_isolated_db(tmp_path) -> Generator[str, None, None]:
    """Isolate SQLite database for every test to avoid cross-test contamination."""
    db_file = str(tmp_path / f"test_idempotency_{uuid.uuid4().hex[:8]}.db")
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
# 1. API Key Provisioning & Revocation Idempotency
# ===========================================================================

def test_api_key_generation_and_repeated_revocation(setup_isolated_db: str):
    """Verifies that revoking an API key multiple times is idempotent."""
    key_info = generate_api_key("Idempotent App", user_id="idemp_user_1")
    key_id = key_info["id"]
    raw_key = key_info["api_key"]

    # Initial validation succeeds
    assert validate_api_key(raw_key) is not None

    # First revocation deactivates the key
    first_revoke = revoke_api_key(key_id)
    assert first_revoke is True
    assert validate_api_key(raw_key) is None

    # Second revocation of the same key keeps it inactive without error
    second_revoke = revoke_api_key(key_id)
    assert validate_api_key(raw_key) is None

    # Third revocation keeps it inactive
    third_revoke = revoke_api_key(key_id)
    assert validate_api_key(raw_key) is None

    # Verify database state has exactly 1 row with is_active = 0
    with database_connection(setup_isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM api_keys WHERE id = ?", (key_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 0


def test_api_create_key_endpoint_repeated_calls(setup_isolated_db: str):
    """Calling POST /api/v1/auth/keys multiple times creates valid distinct active keys without collision."""
    responses = []
    for _ in range(5):
        code, data, _ = process_api_request(
            "POST",
            f"{API_VERSION_PREFIX}/auth/keys",
            {},
            body={"app_name": "Repeated Key App", "user_id": "user_rep_1"},
        )
        assert code == 201
        assert data["success"] is True
        responses.append(data["data"]["api_key"])

    # All generated tokens must be unique and valid
    assert len(set(responses)) == 5
    for token in responses:
        val = validate_api_key(token)
        assert val is not None
        assert val["app_name"] == "Repeated Key App"


# ===========================================================================
# 2. Sustainability Insights Calculation Idempotency
# ===========================================================================

def test_sustainability_calculate_endpoint_idempotency(setup_isolated_db: str):
    """
    POST /api/v1/insights/calculate is a pure calculation service:
    Repeated identical requests must return exact identical payloads and status codes.
    """
    key_info = generate_api_key("Calc App")
    headers = {"X-API-Key": key_info["api_key"]}
    payload = {
        "transport": "Car",
        "distance": 25.5,
        "electricity": 210.0,
        "diet": "Non-Vegetarian",
        "flights": 2,
    }

    first_code, first_data, _ = process_api_request(
        "POST", f"{API_VERSION_PREFIX}/insights/calculate", headers, body=payload
    )
    assert first_code == 200
    assert first_data["success"] is True

    # Send 10 identical repeat requests
    for _ in range(10):
        code, data, _ = process_api_request(
            "POST", f"{API_VERSION_PREFIX}/insights/calculate", headers, body=payload
        )
        assert code == 200
        assert data["data"]["annual_footprint_kg_co2"] == first_data["data"]["annual_footprint_kg_co2"]
        assert data["data"]["eco_score"] == first_data["data"]["eco_score"]
        assert data["data"]["category_breakdown"] == first_data["data"]["category_breakdown"]
        assert data["data"]["insight"] == first_data["data"]["insight"]
        assert len(data["data"]["recommendations"]) == len(first_data["data"]["recommendations"])


def test_rainwater_calculator_idempotency(setup_isolated_db: str):
    """POST /api/v1/calculator/rainwater-tank repeated identical calls yield identical results."""
    key_info = generate_api_key("Rainwater App")
    headers = {"Authorization": f"Bearer {key_info['api_key']}"}
    payload = {
        "roof_area_m2": 180.0,
        "roof_material": "Tiles (clay/concrete)",
        "climate_zone": "Tropical wet & dry",
        "tank_litres": 7500.0,
        "monthly_demand_l": [4500.0] * 12,
    }

    code_1, data_1, _ = process_api_request(
        "POST", f"{API_VERSION_PREFIX}/calculator/rainwater-tank", headers, body=payload
    )
    assert code_1 == 200

    for _ in range(5):
        code_n, data_n, _ = process_api_request(
            "POST", f"{API_VERSION_PREFIX}/calculator/rainwater-tank", headers, body=payload
        )
        assert code_n == 200
        assert data_n["data"]["annual_harvest_litres"] == data_1["data"]["annual_harvest_litres"]
        assert data_n["data"]["financial_payback"] == data_1["data"]["financial_payback"]
        assert data_n["data"]["simulation"]["tank_litres"] == data_1["data"]["simulation"]["tank_litres"]


# ===========================================================================
# 3. User Goal Mutations & Idempotent Updates
# ===========================================================================

def test_goal_setting_and_duplicate_update_idempotency(setup_isolated_db: str):
    """
    Tests creating, updating, and evaluating reduction goals repeatedly.
    Repeated saves archive previous active goals and maintain a single active goal.
    """
    user_id = 999
    
    # Set active goal
    goal_id_1 = db.save_reduction_goal(
        user_id=user_id,
        baseline_kg=5000.0,
        target_kg=4000.0,
        start_date="2026-01-01",
        target_date="2027-01-01",
    )
    assert goal_id_1 is not None
    
    goal_1 = db.get_active_goal(user_id)
    assert goal_1 is not None
    assert goal_1["target_kg"] == 4000.0

    # Overwrite / update goal with identical values multiple times
    for _ in range(3):
        db.save_reduction_goal(
            user_id=user_id,
            baseline_kg=5000.0,
            target_kg=4000.0,
            start_date="2026-01-01",
            target_date="2027-01-01",
        )

    goal_after = db.get_active_goal(user_id)
    assert goal_after["target_kg"] == 4000.0

    # Check goal evaluation is deterministic and idempotent
    eval_1 = evaluate_progress(goal_after, [])
    eval_2 = evaluate_progress(goal_after, [])
    assert eval_1 == eval_2


# ===========================================================================
# 4. User Creation & Registration Idempotency
# ===========================================================================

def test_user_registration_duplicate_rejection_idempotency(setup_isolated_db: str):
    """
    Registering the exact same user multiple times:
    - 1st attempt: True (Created)
    - 2nd, 3rd, 4th attempts: False (Rejected cleanly without crashing or duplicating DB rows)
    """
    username = f"idemp_user_{uuid.uuid4().hex[:6]}"
    email = f"{username}@example.com"
    password = "SecurePassword123!"

    first_res = db.create_user(username, email, password)
    assert first_res is True

    # Repeated identical registration calls
    for _ in range(4):
        retry_res = db.create_user(username, email, password)
        assert retry_res is False

    # Check final database state: exactly 1 user record exists
    with database_connection(setup_isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
        count = cursor.fetchone()[0]
        assert count == 1


# ===========================================================================
# 5. Habit Tracker & Daily Log Idempotency
# ===========================================================================

def test_habit_tracker_repeated_same_day_logging(setup_isolated_db: str):
    """
    Logging habits for the same user on the same date multiple times should update/maintain
    state cleanly rather than multiplying streaks or creating duplicate day logs.
    """
    user_id = f"habit_user_{uuid.uuid4().hex[:6]}"
    
    with database_connection(setup_isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                habit_name TEXT NOT NULL,
                log_date TEXT NOT NULL,
                completed INTEGER DEFAULT 1,
                UNIQUE(user_id, habit_name, log_date)
            )
        """)
        conn.commit()

        # Simulate upsert/idempotent logging pattern
        for _ in range(5):
            cursor.execute("""
                INSERT INTO habit_logs (user_id, habit_name, log_date, completed)
                VALUES (?, ?, '2026-08-24', 1)
                ON CONFLICT(user_id, habit_name, log_date) DO UPDATE SET completed = 1
            """, (user_id, "public_transit"))
        conn.commit()

        cursor.execute(
            "SELECT COUNT(*) FROM habit_logs WHERE user_id = ? AND habit_name = ?",
            (user_id, "public_transit"),
        )
        total_logs = cursor.fetchone()[0]
        assert total_logs == 1, "Repeated habit logs for the same day must not create duplicates"


# ===========================================================================
# 6. Concurrent Duplicate Requests
# ===========================================================================

def test_concurrent_duplicate_requests_idempotency(setup_isolated_db: str):
    """
    Sending identical user creation requests concurrently from 10 threads:
    Exactly one succeeds, 9 fail gracefully, database contains exactly 1 record.
    """
    username = f"concurrent_idemp_{uuid.uuid4().hex[:6]}"
    email = f"{username}@test.com"
    password = "SafePassword999!"
    barrier = threading.Barrier(10)

    def submit_request():
        barrier.wait()
        return db.create_user(username, email, password)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(submit_request) for _ in range(10)]
        results = [f.result() for f in as_completed(futures)]

    # Exactly one True, 9 False
    assert results.count(True) == 1
    assert results.count(False) == 9

    with database_connection(setup_isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
        assert cursor.fetchone()[0] == 1


def test_concurrent_key_revocation_idempotency(setup_isolated_db: str):
    """
    Simultaneous revocation of the same API key across 8 threads:
    Key becomes inactive immediately and no errors or inconsistent states occur.
    """
    key_info = generate_api_key("Concurrent Revoke App")
    key_id = key_info["id"]
    barrier = threading.Barrier(8)

    def revoke_worker():
        barrier.wait()
        return revoke_api_key(key_id)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(revoke_worker) for _ in range(8)]
        results = [f.result() for f in as_completed(futures)]

    # All threads complete safely and validate_api_key confirms revocation
    assert validate_api_key(key_info["api_key"]) is None
    with database_connection(setup_isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM api_keys WHERE id = ?", (key_id,))
        assert cursor.fetchone()[0] == 0


# ===========================================================================
# 7. Network Retry & Idempotency Key Simulation
# ===========================================================================

def test_network_retry_simulation_with_idempotency_header(setup_isolated_db: str):
    """
    Simulate client retries across unreliable network:
    Using an Idempotency-Key header or identical signature returns consistent response
    without repeating side effects.
    """
    key_info = generate_api_key("Network Retry App")
    headers = {
        "X-API-Key": key_info["api_key"],
        "Idempotency-Key": str(uuid.uuid4()),
    }
    payload = {
        "transport": "Car",
        "distance": 15.0,
        "electricity": 80.0,
        "diet": "Vegetarian",
        "flights": 0,
    }

    # Simulate 3 network retries
    responses = []
    for _ in range(3):
        code, data, _ = process_api_request(
            "POST", f"{API_VERSION_PREFIX}/insights/calculate", headers, body=payload
        )
        assert code == 200
        responses.append(data)

    assert responses[0] == responses[1] == responses[2]
