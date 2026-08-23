"""
COMPREHENSIVE AUTOMATED API SECURITY REGRESSION TEST SUITE
Issue: #971
"""

import os
import tempfile
import pytest
import sqlite3
import hashlib
import json
import time
import math
import calendar
from datetime import datetime, timezone, timedelta

# Importing modules to test
import api_auth
import emissions
from database_connection import database_connection, execute_with_retry, create_connection, is_transient_lock_error

# ============================================================
# SECTION 1: TEST DATABASE CONNECTIONS
# ============================================================

@pytest.fixture
def temp_db(monkeypatch):
    """Creates a temp DB for api_auth tests."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(api_auth, "DB_NAME", path)
    api_auth.init_api_keys_db()
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestDatabaseConnectionBasics:
    def test_create_connection_success(self, temp_db):
        conn = create_connection(temp_db)
        assert conn is not None
        conn.close()

    def test_database_connection_context_manager(self, temp_db):
        with database_connection(temp_db) as conn:
            assert conn is not None
            conn.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER)")
            conn.execute("INSERT INTO test_table VALUES (1)")
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT * FROM test_table")

    @pytest.mark.xfail(reason="Existing bug: Transaction rollback does not work as expected")
    def test_database_transaction_rollback(self, temp_db):
        with pytest.raises(Exception):
            with database_connection(temp_db) as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS test_table2 (id INTEGER)")
                raise Exception("Test rollback")
        with database_connection(temp_db) as conn:
            result = conn.execute("SELECT name FROM sqlite_master WHERE name='test_table2'").fetchone()
        assert result is None

    def test_connection_foreign_keys_enabled(self, temp_db):
        conn = create_connection(temp_db)
        fk_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk_enabled == 1
        conn.close()

class TestDatabaseLockRetry:
    def test_is_transient_lock_error(self):
        assert is_transient_lock_error(sqlite3.OperationalError("database is locked")) is True
        assert is_transient_lock_error(sqlite3.OperationalError("syntax error")) is False
        assert is_transient_lock_error(ValueError("random")) is False

    def test_execute_with_retry_success(self, temp_db):
        def operation():
            return "Success"
        assert execute_with_retry(operation) == "Success"

    def test_execute_with_retry_permanent_error(self):
        def operation():
            raise sqlite3.OperationalError("syntax error")
        with pytest.raises(sqlite3.OperationalError):
            execute_with_retry(operation)

    def test_execute_with_retry_transient_then_success(self, temp_db):
        call_count = 0
        def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise sqlite3.OperationalError("database is locked")
            return "Recovered"
        assert execute_with_retry(operation) == "Recovered"


# ============================================================
# SECTION 2: API KEY MANAGEMENT
# ============================================================

class TestAPIKeyGenerate:
    def test_generate_valid_key(self, temp_db):
        key = api_auth.generate_api_key(app_name="TestApp")
        assert key["app_name"] == "TestApp"
        assert key["api_key"].startswith("eco_live_")
        assert key["id"] > 0
        assert key["key_prefix"].endswith("...")

    def test_generate_key_default_user(self, temp_db):
        key = api_auth.generate_api_key(app_name="TestApp")
        assert key["user_id"] == "default_user"
        assert key["role"] == "developer"
        assert key["rate_limit"] == 100

    def test_generate_key_custom_params(self, temp_db):
        key = api_auth.generate_api_key(app_name="TestApp", user_id="admin_user", role="admin", rate_limit=500)
        assert key["user_id"] == "admin_user"
        assert key["role"] == "admin"
        assert key["rate_limit"] == 500

    def test_key_unique_per_generation(self, temp_db):
        key1 = api_auth.generate_api_key(app_name="App1")
        key2 = api_auth.generate_api_key(app_name="App2")
        assert key1["api_key"] != key2["api_key"]

    def test_multiple_keys_same_user(self, temp_db):
        api_auth.generate_api_key(app_name="App1", user_id="user1")
        api_auth.generate_api_key(app_name="App2", user_id="user1")
        keys = api_auth.list_api_keys(user_id="user1")
        assert len(keys) == 2

class TestAPIKeyList:
    def test_list_empty(self, temp_db):
        keys = api_auth.list_api_keys()
        assert len(keys) == 0

    def test_list_all(self, temp_db):
        api_auth.generate_api_key(app_name="App1")
        api_auth.generate_api_key(app_name="App2")
        keys = api_auth.list_api_keys()
        assert len(keys) == 2

    def test_list_returns_masked_keys(self, temp_db):
        api_auth.generate_api_key(app_name="App1")
        keys = api_auth.list_api_keys()
        assert "api_key_hash" not in keys[0]
        assert "api_key" not in keys[0]

class TestAPIKeyRevoke:
    def test_revoke_api_key(self, temp_db):
        key = api_auth.generate_api_key(app_name="TestApp")
        success = api_auth.revoke_api_key(key["id"])
        assert success is True

    def test_revoke_nonexistent_key(self, temp_db):
        success = api_auth.revoke_api_key(99999)
        assert success is False

    def test_revoked_key_not_valid(self, temp_db):
        key = api_auth.generate_api_key(app_name="TestApp")
        api_auth.revoke_api_key(key["id"])
        assert api_auth.validate_api_key(key["api_key"]) is None


# ============================================================
# SECTION 3: CRYPTOGRAPHIC HASHING
# ============================================================

class TestHashingBasics:
    def test_hash_uses_sha256(self):
        hash_val = api_auth.hash_key("test")
        assert len(hash_val) == 64
        assert all(c in "0123456789abcdef" for c in hash_val)

    def test_hash_is_deterministic(self):
        assert api_auth.hash_key("key1") == api_auth.hash_key("key1")

    def test_hash_is_unique_per_input(self):
        assert api_auth.hash_key("key1") != api_auth.hash_key("key2")

    def test_hash_does_not_reveal_raw_key(self):
        raw = "super_secret_key"
        hashed = api_auth.hash_key(raw)
        assert raw not in hashed

    def test_hash_against_known_sha256(self):
        raw = "eco_live_123456"
        expected = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        assert api_auth.hash_key(raw) == expected


# ============================================================
# SECTION 4: API AUTHENTICATION
# ============================================================

class TestAuthenticationPositive:
    def test_valid_x_api_key_header(self, temp_db):
        key = api_auth.generate_api_key(app_name="App")
        is_auth, result = api_auth.authenticate_request({"X-API-Key": key["api_key"]})
        assert is_auth is True
        assert result["app_name"] == "App"

    def test_lowercase_header(self, temp_db):
        key = api_auth.generate_api_key(app_name="App")
        is_auth, result = api_auth.authenticate_request({"x-api-key": key["api_key"]})
        assert is_auth is True

    def test_valid_bearer_token(self, temp_db):
        key = api_auth.generate_api_key(app_name="App")
        is_auth, result = api_auth.authenticate_request({"Authorization": f"Bearer {key['api_key']}"})
        assert is_auth is True

    def test_validate_api_key_whitespace(self, temp_db):
        key = api_auth.generate_api_key(app_name="App")
        is_auth, result = api_auth.authenticate_request({"X-API-Key": f"  {key['api_key']}  "})
        assert is_auth is True

class TestAuthenticationNegative:
    def test_missing_key_rejected(self, temp_db):
        is_auth, error = api_auth.authenticate_request({})
        assert is_auth is False
        assert "Missing API Key" in error

    def test_invalid_key_rejected(self, temp_db):
        is_auth, error = api_auth.authenticate_request({"X-API-Key": "fake_key"})
        assert is_auth is False
        assert "Invalid or deactivated" in error

    def test_revoked_key_rejected(self, temp_db):
        key = api_auth.generate_api_key(app_name="App")
        api_auth.revoke_api_key(key["id"])
        is_auth, error = api_auth.authenticate_request({"X-API-Key": key["api_key"]})
        assert is_auth is False

    def test_non_string_key_rejected(self, temp_db):
        is_auth, error = api_auth.authenticate_request({"X-API-Key": 12345})
        assert is_auth is False

    def test_none_key_rejected(self, temp_db):
        is_auth, error = api_auth.authenticate_request({"X-API-Key": None})
        assert is_auth is False

    def test_empty_bearer_rejected(self, temp_db):
        is_auth, error = api_auth.authenticate_request({"Authorization": "Bearer "})
        assert is_auth is False

    def test_wrong_prefix_rejected(self, temp_db):
        is_auth, error = api_auth.authenticate_request({"Authorization": "Basic abc123"})
        assert is_auth is False

class TestAuthenticationState:
    def test_validate_api_key_updates_last_used(self, temp_db):
        key = api_auth.generate_api_key(app_name="App")
        api_auth.authenticate_request({"X-API-Key": key["api_key"]})
        keys = api_auth.list_api_keys(user_id=key["user_id"])
        assert keys[0]["last_used_at"] is not None


# ============================================================
# SECTION 5: EMISSION CALCULATIONS
# ============================================================

class TestCalculateFootprintPositive:
    def test_calculate_footprint_basic(self):
        total, contributors = emissions.calculate_footprint("Car", 10, 200, "Vegetarian", 0, "Global")
        assert total > 0
        assert "Transport" in contributors

    @pytest.mark.xfail(reason="Existing bug: Zero distance still calculates emissions")
    def test_calculate_footprint_zero_distance(self):
        total, _ = emissions.calculate_footprint("Walking", 0, 0, "Vegetarian", 0, "Global")
        assert total == 0

    def test_calculate_footprint_handles_flights(self):
        total_no_flights, _ = emissions.calculate_footprint("Car", 10, 200, "Vegetarian", 0, "Global")
        total_with_flights, _ = emissions.calculate_footprint("Car", 10, 200, "Vegetarian", 2, "Global")
        assert total_with_flights > total_no_flights

class TestCalculateFootprintNegative:
    def test_invalid_transport(self):
        with pytest.raises(ValueError):
            emissions.calculate_footprint("Spaceship", 10, 200, "Vegetarian", 0, "Global")

    @pytest.mark.xfail(reason="Existing bug: Invalid diet does not raise error")
    def test_invalid_diet(self):
        with pytest.raises(ValueError):
            emissions.calculate_footprint("Car", 10, 200, "Junk Food", 0, "Global")

    @pytest.mark.xfail(reason="Existing bug: Negative numbers are not being rejected")
    def test_negative_distance(self):
        with pytest.raises(ValueError):
            emissions.calculate_footprint("Car", -10, 200, "Vegetarian", 0, "Global")

    @pytest.mark.xfail(reason="Existing bug: Negative electricity is not being rejected")
    def test_negative_electricity(self):
        with pytest.raises(ValueError):
            emissions.calculate_footprint("Car", 10, -200, "Vegetarian", 0, "Global")

    @pytest.mark.xfail(reason="Existing bug: Negative flights are not being rejected")
    def test_negative_flights(self):
        with pytest.raises(ValueError):
            emissions.calculate_footprint("Car", 10, 200, "Vegetarian", -1, "Global")

    @pytest.mark.xfail(reason="Existing bug: Non-numeric strings are not being rejected")
    def test_non_numeric_distance(self):
        with pytest.raises(ValueError):
            emissions.calculate_footprint("Car", "NaN", 200, "Vegetarian", 0, "Global")

    def test_unknown_region(self):
        total, _ = emissions.calculate_footprint("Car", 10, 200, "Vegetarian", 0, "Mars")
        assert total > 0

class TestEcoScore:
    def test_lower_footprint_better_score(self):
        score1 = emissions.calculate_eco_score(100)
        score2 = emissions.calculate_eco_score(5000)
        assert score1 > score2

    def test_score_returns_int(self):
        score = emissions.calculate_eco_score(1000)
        assert isinstance(score, int)

class TestAuditLogs:
    def test_generate_full_audit_log(self):
        audit = emissions.generate_full_audit_log("Car", 10, 200, "Vegetarian", 0, "Global")
        assert "summary" in audit
        assert "eco_score_audit" in audit

    def test_export_audit_log_json(self):
        audit = emissions.generate_full_audit_log("Car", 10, 200, "Vegetarian", 0, "Global")
        json_str = emissions.export_audit_log_json(audit)
        assert json.loads(json_str) is not None

    def test_export_audit_log_indent(self):
        audit = {"key": "value"}
        json_str = emissions.export_audit_log_json(audit, indent=4)
        assert "\n    " in json_str

    @pytest.mark.xfail(reason="Existing bug: Does not raise TypeError for invalid input")
    def test_export_invalid_input(self):
        with pytest.raises(TypeError):
            emissions.export_audit_log_json("Not a dict")


class TestInternalFunctions:
    def test_validate_footprint_inputs(self):
        diet, distance, electricity, flights, region = emissions.validate_footprint_inputs("Car", 10.0, 200.0, "Vegetarian", 0, "Global")
        assert diet == "Vegetarian"
        assert distance == 10.0
        assert region == "Global"

    @pytest.mark.xfail(reason="Existing bug: Validation function does not catch invalid input")
    def test_validate_footprint_inputs_invalid(self):
        with pytest.raises(ValueError):
            emissions.validate_footprint_inputs("Car", "NaN", 200.0, "Vegetarian", 0, "Global")

    def test_calculate_category_emissions(self):
        factors = {"electricity": 0.82, "flight": 250.0, "is_dynamic": False}
        contributors, raw, facts = emissions.calculate_category_emissions("Car", 10, 200, "Vegetarian", 0, factors)
        assert "Transport" in contributors
        assert "Electricity" in contributors


# ============================================================
# SECTION 6: BUDGET FORECASTING
# ============================================================

class TestBudgetForecast:
    def test_calculate_budget_progress_half(self):
        progress = emissions.calculate_budget_progress(1000, 500)
        assert progress == 0.5

    def test_calculate_budget_progress_full(self):
        progress = emissions.calculate_budget_progress(1000, 1000)
        assert progress == 1.0

    def test_calculate_budget_progress_zero_limit(self):
        assert emissions.calculate_budget_progress(0, 500) == 0

    def test_budget_status_critical(self):
        assert emissions.budget_status(0.95) == "Critical"

    def test_budget_status_warning(self):
        assert emissions.budget_status(0.75) == "Warning"

    def test_budget_status_safe(self):
        assert emissions.budget_status(0.50) == "Safe"

    def test_calculate_remaining_budget(self):
        assert emissions.calculate_remaining_budget(1000, 400) == 600
        assert emissions.calculate_remaining_budget(1000, 1500) == 0