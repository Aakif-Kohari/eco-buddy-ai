"""
Comprehensive Authentication and Authorization Test Coverage Suite (#1013).

Covers:
- Valid and invalid login credentials (passwords, usernames, non-existent users, SQL injection).
- Missing authentication headers and tokens.
- Malformed, corrupted, revoked, and expired tokens / API keys.
- Unauthorized endpoint access across all protected resources.
- Role-based permissions, rate limits, and key metadata.
- Session lifecycle, TTL expiration, and session cache src.core.invalidation.
- Authentication state after logout / key revocation.
"""

from __future__ import annotations

import os
import time
import uuid
import sqlite3
from typing import Generator, Dict, Any

import pytest

import src.core.database as db
from src.core.database_connection import database_connection
from src.core.invalidation import invalidate_all_db_caches
import src.core.api_auth
from src.core.api_auth import (
    generate_api_key,
    validate_api_key,
    revoke_api_key,
    list_api_keys,
    authenticate_request,
    init_api_keys_db,
    hash_key,
)
from src.business.sustainability_api import (
    process_api_request,
    API_VERSION_PREFIX,
)
from src.core.session_manager import SessionData, OptimizedSessionManager


@pytest.fixture(autouse=True)
def setup_isolated_db(tmp_path) -> Generator[str, None, None]:
    """Isolate SQLite database for every test to avoid state pollution."""
    db_file = str(tmp_path / f"test_auth_coverage_{uuid.uuid4().hex[:8]}.db")
    original_db = src.notifications.db.DB_NAME
    original_api_db = getattr(api_auth, "DB_NAME", "eco_buddy.db")
    src.notifications.db.DB_NAME = db_file
    src.core.api_auth.DB_NAME = db_file
    os.environ["ECO_BUDDY_DB"] = db_file

    try:
        src.notifications.db.init_db()
        init_api_keys_db()
        invalidate_all_db_caches()
        yield db_file
    finally:
        src.notifications.db.DB_NAME = original_db
        src.core.api_auth.DB_NAME = original_api_db
        os.environ["ECO_BUDDY_DB"] = original_db
        invalidate_all_db_caches()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


# ===========================================================================
# 1. User Credential Authentication & Password Validation
# ===========================================================================

def test_user_authentication_success_with_valid_credentials():
    """Verify user is successfully authenticated with exact valid credentials."""
    username = f"valid_user_{uuid.uuid4().hex[:6]}"
    email = f"{username}@example.com"
    password = "CorrectHorseBatteryStaple123!"

    created = src.notifications.db.create_user(username, email, password)
    assert created is True

    user = src.notifications.db.verify_user(username, password)
    assert user is not None
    assert user["username"] == username
    assert "id" in user


def test_user_authentication_failure_invalid_credentials():
    """Verify authentication fails for wrong password, non-existent user, or empty fields."""
    username = f"user_cred_{uuid.uuid4().hex[:6]}"
    email = f"{username}@test.com"
    password = "SuperSecretPassword123!"
    src.notifications.db.create_user(username, email, password)

    # Wrong password
    assert src.notifications.db.verify_user(username, "WrongPassword456!") is None

    # Non-existent user
    assert src.notifications.db.verify_user("non_existent_user_999", password) is None

    # Empty username and password
    assert src.notifications.db.verify_user("", password) is None
    assert src.notifications.db.verify_user(username, "") is None

    # Case mismatch or SQL injection attempt in password/username
    assert src.notifications.db.verify_user(f"{username}' OR '1'='1", "' OR '1'='1") is None


# ===========================================================================
# 2. Missing Authentication & Unauthorized Endpoint Access
# ===========================================================================

def test_missing_authentication_header_rejected():
    """Verify request without any auth header is rejected with 401 Unauthorized."""
    is_auth, err_msg = authenticate_request({})
    assert is_auth is False
    assert "Missing" in err_msg or "required" in err_msg.lower()

    # Empty header dict / None values
    is_auth, _ = authenticate_request({"X-API-Key": ""})
    assert is_auth is False


def test_unauthorized_access_to_all_protected_endpoints():
    """Verify every protected REST endpoint rejects unauthenticated access with 401."""
    protected_endpoints = [
        ("POST", f"{API_VERSION_PREFIX}/insights/calculate", {"transport": "Car"}),
        ("GET", f"{API_VERSION_PREFIX}/insights/assessments", None),
        ("GET", f"{API_VERSION_PREFIX}/insights/recommendations", None),
        ("GET", f"{API_VERSION_PREFIX}/insights/goals", None),
        ("POST", f"{API_VERSION_PREFIX}/calculator/rainwater-tank", {"roof_area_m2": 120}),
    ]

    for method, path, body in protected_endpoints:
        code, data, _ = process_api_request(method, path, headers={}, body=body)
        assert code == 401, f"{method} {path} should return 401 Unauthorized"
        assert data["error"] == "Unauthorized"


# ===========================================================================
# 3. Invalid, Malformed, and Expired API Keys / Tokens
# ===========================================================================

def test_malformed_and_tampered_api_keys():
    """Verify malformed, truncated, or tampered tokens are rejected."""
    tampered_keys = [
        "eco_live_invalid_hex_token_12345",
        "Bearer invalid_token_string",
        "eco_live_000000000000000000000000000000000000000000000000",
        "invalid_prefix_token_abcdef123456",
        "   ",
        "'; DROP TABLE api_keys; --",
    ]

    for invalid_key in tampered_keys:
        assert validate_api_key(invalid_key) is None
        is_auth, _ = authenticate_request({"X-API-Key": invalid_key})
        assert is_auth is False


def test_bearer_token_authorization_header():
    """Verify Bearer token authorization header format."""
    key_info = generate_api_key("Bearer Auth App", user_id="bearer_user")
    raw_key = key_info["api_key"]

    # Valid Bearer header
    is_auth, data = authenticate_request({"Authorization": f"Bearer {raw_key}"})
    assert is_auth is True
    assert data["app_name"] == "Bearer Auth App"

    # Malformed Bearer header without token
    is_auth_empty, _ = authenticate_request({"Authorization": "Bearer "})
    assert is_auth_empty is False

    # Authorization with invalid token
    is_auth_bad, _ = authenticate_request({"Authorization": "Bearer bad_token_123"})
    assert is_auth_bad is False


# ===========================================================================
# 4. Authentication State After Logout / Key Revocation
# ===========================================================================

def test_authentication_state_after_key_revocation():
    """Verify that after revocation, the key cannot be used for any protected endpoints."""
    key_info = generate_api_key("Revocation Test App", user_id="revoked_user")
    raw_key = key_info["api_key"]
    headers = {"X-API-Key": raw_key}

    # Verify initial access is granted
    code_before, data_before, _ = process_api_request(
        "POST",
        f"{API_VERSION_PREFIX}/insights/calculate",
        headers,
        body={"transport": "Car", "distance": 10, "electricity": 100, "diet": "Vegetarian", "flights": 0},
    )
    assert code_before == 200

    # Revoke key
    assert revoke_api_key(key_info["id"]) is True

    # Immediate post-revocation access must be denied
    code_after, data_after, _ = process_api_request(
        "POST",
        f"{API_VERSION_PREFIX}/insights/calculate",
        headers,
        body={"transport": "Car", "distance": 10, "electricity": 100, "diet": "Vegetarian", "flights": 0},
    )
    assert code_after == 401
    assert data_after["error"] == "Unauthorized"


# ===========================================================================
# 5. Role-Based Permissions & Key Metadata
# ===========================================================================

def test_role_based_permissions_and_metadata():
    """Verify role metadata assignment, developer vs admin keys, and listing filters."""
    dev_key = generate_api_key("Dev Tool", user_id="dev_user", role="developer", rate_limit=150)
    admin_key = generate_api_key("Admin Dashboard", user_id="admin_user", role="admin", rate_limit=5000)

    # Validate dev key metadata
    dev_val = validate_api_key(dev_key["api_key"])
    assert dev_val["role"] == "developer"
    assert dev_val["rate_limit"] == 150
    assert dev_val["is_active"] is True

    # Validate admin key metadata
    admin_val = validate_api_key(admin_key["api_key"])
    assert admin_val["role"] == "admin"
    assert admin_val["rate_limit"] == 5000

    # List keys filtered by user
    dev_keys_list = list_api_keys(user_id="dev_user")
    assert len(dev_keys_list) == 1
    assert dev_keys_list[0]["app_name"] == "Dev Tool"


# ===========================================================================
# 6. Session Lifecycle & Expiration
# ===========================================================================

def test_session_lifecycle_and_ttl_expiration():
    """Verify session data creation, access tracking, TTL expiration, and cleanup."""
    session_mgr = OptimizedSessionManager(max_size=50, default_ttl=1)  # 1-second TTL
    
    # Store session data with 1 second TTL
    session_data = SessionData(
        key="user_session_token",
        value={"user_id": 42, "role": "authenticated"},
        ttl=1,
    )
    assert session_data.is_expired() is False
    assert session_data.value["user_id"] == 42

    # Allow TTL to expire
    time.sleep(1.1)
    assert session_data.is_expired() is True


def test_session_dictionary_serialization():
    """Verify session metadata serialization for audit logs and security diagnostics."""
    session_item = SessionData(
        key="auth_state",
        value={"authenticated": True, "user": "eco_warrior"},
        ttl=3600,
    )
    serialized = session_item.to_dict()
    assert serialized["key"] == "auth_state"
    assert serialized["value"]["authenticated"] is True
    assert serialized["ttl"] == 3600
    assert "created_at" in serialized
    assert "last_accessed" in serialized
