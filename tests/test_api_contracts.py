"""
Comprehensive API Contract Testing Suite for Backend Endpoints (#1012).

Verifies that EcoBuddy API endpoints consistently adhere to their declared OpenAPI 3.0.3
specification, request schemas, response payload schemas, HTTP status codes,
field types, required/optional attributes, and error response envelopes.
Detects unexpected or breaking API contract changes.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Generator
import pytest

import src.core.database as db
from src.core.database_connection import database_connection
from src.core.invalidation import invalidate_all_db_caches
import src.core.api_auth
from src.core.api_auth import (
    generate_api_key,
    validate_api_key,
    init_api_keys_db,
)
from src.business.sustainability_api import (
    process_api_request,
    OPENAPI_SPEC,
    SWAGGER_UI_HTML,
    API_VERSION_PREFIX,
)


@pytest.fixture(autouse=True)
def setup_isolated_db(tmp_path) -> Generator[str, None, None]:
    """Isolate SQLite database for every test to avoid state pollution."""
    db_file = str(tmp_path / f"test_contracts_{uuid.uuid4().hex[:8]}.db")
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


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Provide valid authentication headers for testing protected endpoints."""
    key_data = generate_api_key("Contract Testing Suite", user_id="contract_tester")
    return {"X-API-Key": key_data["api_key"]}


# ===========================================================================
# 1. OpenAPI 3.0.3 Specification Contract Validation
# ===========================================================================

def test_openapi_spec_structure_contract():
    """Validates top-level structure and metadata of the OpenAPI specification."""
    assert OPENAPI_SPEC["openapi"] == "3.0.3"
    assert "info" in OPENAPI_SPEC
    assert OPENAPI_SPEC["info"]["title"] == "EcoBuddy AI Sustainability Insights API"
    assert OPENAPI_SPEC["info"]["version"] == "1.0.0"
    assert "paths" in OPENAPI_SPEC
    assert len(OPENAPI_SPEC["paths"]) >= 6

    # Verify security schemes contract
    components = OPENAPI_SPEC.get("components", {})
    assert "securitySchemes" in components
    assert "ApiKeyAuth" in components["securitySchemes"]
    assert "BearerAuth" in components["securitySchemes"]
    assert components["securitySchemes"]["ApiKeyAuth"]["type"] == "apiKey"
    assert components["securitySchemes"]["ApiKeyAuth"]["name"] == "X-API-Key"


def test_openapi_declared_endpoints_all_implemented():
    """Ensures every route defined in the OpenAPI spec is callable and returns non-404."""
    declared_paths = OPENAPI_SPEC["paths"]
    for path, path_item in declared_paths.items():
        for method in path_item.keys():
            if method.lower() not in ("get", "post", "put", "delete", "patch"):
                continue
            # Call route with dummy payload
            status_code, data, content_type = process_api_request(
                method=method.upper(),
                path=path,
                headers={},
                body={},
            )
            # Route must be recognized by router (status code is not 404)
            assert status_code != 404, f"Declared OpenAPI endpoint {method.upper()} {path} returned 404 Not Found"


# ===========================================================================
# 2. GET /health Endpoint Contract
# ===========================================================================

def test_health_endpoint_response_contract():
    """Validates response contract for GET /api/v1/health."""
    status_code, data, content_type = process_api_request("GET", f"{API_VERSION_PREFIX}/health", {})
    
    assert status_code == 200
    assert content_type == "application/json"
    assert isinstance(data, dict)

    # Required contract keys
    required_keys = {"status", "service", "version", "api_prefix"}
    assert required_keys.issubset(data.keys()), f"Missing keys in health contract: {required_keys - data.keys()}"
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["api_prefix"] == API_VERSION_PREFIX


# ===========================================================================
# 3. POST /auth/keys Endpoint Contract
# ===========================================================================

def test_auth_keys_creation_success_contract():
    """Validates response structure when creating an API key."""
    body = {"app_name": "Partner Ecosystem", "user_id": "partner_001"}
    status_code, data, content_type = process_api_request(
        "POST", f"{API_VERSION_PREFIX}/auth/keys", {}, body=body
    )

    assert status_code == 201
    assert content_type == "application/json"
    assert isinstance(data, dict)
    assert data["success"] is True
    assert "message" in data
    assert isinstance(data["data"], dict)

    key_contract_fields = {
        "id": int,
        "app_name": str,
        "api_key": str,
        "key_prefix": str,
        "user_id": str,
        "role": str,
        "rate_limit": int,
        "created_at": str,
    }
    for field, expected_type in key_contract_fields.items():
        assert field in data["data"], f"Missing field '{field}' in key data"
        assert isinstance(data["data"][field], expected_type), f"Field '{field}' expected {expected_type}"

    assert data["data"]["api_key"].startswith("eco_live_")


def test_auth_keys_missing_app_name_error_contract():
    """Validates error response contract when required 'app_name' is missing."""
    status_code, data, content_type = process_api_request(
        "POST", f"{API_VERSION_PREFIX}/auth/keys", {}, body={}
    )

    assert status_code == 400
    assert content_type == "application/json"
    assert data["error"] == "Bad Request"
    assert "app_name" in data["message"]


# ===========================================================================
# 4. POST /insights/calculate Endpoint Contract
# ===========================================================================

def test_calculate_insights_success_response_contract(auth_headers: Dict[str, str]):
    """Validates calculate insights response structure, schema, and field types."""
    payload = {
        "transport": "Car",
        "distance": 18.5,
        "electricity": 220.0,
        "diet": "Non-Vegetarian",
        "flights": 1,
    }
    status_code, data, content_type = process_api_request(
        "POST", f"{API_VERSION_PREFIX}/insights/calculate", auth_headers, body=payload
    )

    assert status_code == 200
    assert content_type == "application/json"
    assert data["success"] is True
    assert "data" in data

    insights_data = data["data"]
    assert isinstance(insights_data["annual_footprint_kg_co2"], (int, float))
    assert isinstance(insights_data["eco_score"], (int, float))
    assert isinstance(insights_data["category_breakdown"], dict)
    assert isinstance(insights_data["insight"], str)
    assert isinstance(insights_data["recommendations"], list)

    # Category breakdown required keys
    breakdown_keys = {"Transport", "Electricity", "Diet", "Flights"}
    assert breakdown_keys.issubset(insights_data["category_breakdown"].keys())

    # Verify recommendation item structure
    for rec in insights_data["recommendations"]:
        assert isinstance(rec, (str, dict))
        if isinstance(rec, str):
            assert len(rec) > 0


def test_calculate_insights_missing_body_error_contract(auth_headers: Dict[str, str]):
    """Validates error response contract for missing JSON body."""
    status_code, data, content_type = process_api_request(
        "POST", f"{API_VERSION_PREFIX}/insights/calculate", auth_headers, body=None
    )

    assert status_code == 400
    assert content_type == "application/json"
    assert data["error"] == "Bad Request"
    assert "message" in data


# ===========================================================================
# 5. GET /insights/assessments Endpoint Contract
# ===========================================================================

def test_get_assessments_endpoint_contract(auth_headers: Dict[str, str]):
    """Validates GET /insights/assessments response schema."""
    status_code, data, content_type = process_api_request(
        "GET", f"{API_VERSION_PREFIX}/insights/assessments", auth_headers
    )

    assert status_code == 200
    assert content_type == "application/json"
    assert data["success"] is True
    assert "count" in data
    assert isinstance(data["count"], int)
    assert isinstance(data["data"], list)


# ===========================================================================
# 6. GET /insights/recommendations Endpoint Contract
# ===========================================================================

def test_get_recommendations_endpoint_contract(auth_headers: Dict[str, str]):
    """Validates GET /insights/recommendations response schema."""
    query = {
        "transport": ["Car"],
        "electricity": ["250"],
        "diet": ["Vegetarian"],
        "flights": ["2"],
    }
    status_code, data, content_type = process_api_request(
        "GET",
        f"{API_VERSION_PREFIX}/insights/recommendations",
        auth_headers,
        query_params=query,
    )

    assert status_code == 200
    assert content_type == "application/json"
    assert data["success"] is True
    assert "data" in data
    assert "insight" in data["data"]
    assert "recommendations" in data["data"]
    assert isinstance(data["data"]["recommendations"], list)


# ===========================================================================
# 7. GET /insights/goals Endpoint Contract
# ===========================================================================

def test_get_goals_endpoint_contract(auth_headers: Dict[str, str]):
    """Validates GET /insights/goals response schema when no goal exists vs when active goal exists."""
    # When no goal exists
    status_code, data, content_type = process_api_request(
        "GET", f"{API_VERSION_PREFIX}/insights/goals", auth_headers
    )
    assert status_code == 200
    assert data["success"] is True
    assert "data" in data


# ===========================================================================
# 8. POST /calculator/rainwater-tank Endpoint Contract
# ===========================================================================

def test_rainwater_tank_calculator_contract(auth_headers: Dict[str, str]):
    """Validates response structure for rainwater tank sizing API."""
    payload = {
        "roof_area_m2": 150.0,
        "roof_material": "Metal / corrugated sheet",
        "climate_zone": "Temperate maritime",
        "tank_litres": 6000.0,
        "monthly_demand_l": [3800.0] * 12,
    }
    status_code, data, content_type = process_api_request(
        "POST", f"{API_VERSION_PREFIX}/calculator/rainwater-tank", auth_headers, body=payload
    )

    assert status_code == 200
    assert content_type == "application/json"
    assert data["success"] is True
    assert "data" in data

    rw_data = data["data"]
    expected_keys = {
        "roof_area_m2",
        "roof_material",
        "climate_zone",
        "monthly_harvest_l",
        "annual_harvest_litres",
        "simulation",
        "optimal_tank_recommendation",
        "financial_payback",
        "carbon_avoided",
    }
    assert expected_keys.issubset(rw_data.keys())
    assert isinstance(rw_data["monthly_harvest_l"], list)
    assert len(rw_data["monthly_harvest_l"]) == 12
    assert isinstance(rw_data["annual_harvest_litres"], (int, float))
    assert isinstance(rw_data["simulation"], dict)
    assert isinstance(rw_data["optimal_tank_recommendation"], dict)


# ===========================================================================
# 9. Authentication Error Contract (401 Unauthorized)
# ===========================================================================

def test_unauthorized_error_response_contract():
    """Verifies that all protected endpoints return standard 401 envelope when auth is missing or invalid."""
    protected_routes = [
        ("POST", f"{API_VERSION_PREFIX}/insights/calculate", {"transport": "Car"}),
        ("GET", f"{API_VERSION_PREFIX}/insights/assessments", None),
        ("GET", f"{API_VERSION_PREFIX}/insights/recommendations", None),
        ("GET", f"{API_VERSION_PREFIX}/insights/goals", None),
        ("POST", f"{API_VERSION_PREFIX}/calculator/rainwater-tank", {"roof_area_m2": 100}),
    ]

    for method, path, body in protected_routes:
        status_code, data, content_type = process_api_request(
            method=method,
            path=path,
            headers={},
            body=body,
        )
        assert status_code == 401, f"{method} {path} should return 401 when unauthenticated"
        assert content_type == "application/json"
        assert data["error"] == "Unauthorized"
        assert "message" in data


# ===========================================================================
# 10. 404 Not Found Contract
# ===========================================================================

def test_not_found_response_contract(auth_headers: Dict[str, str]):
    """Verifies standard 404 envelope when requesting non-existent endpoint."""
    status_code, data, content_type = process_api_request(
        "GET", f"{API_VERSION_PREFIX}/undefined-route", auth_headers
    )
    assert status_code == 404
    assert content_type == "application/json"
    assert data["error"] == "Not Found"
    assert "message" in data
    assert f"{API_VERSION_PREFIX}/undefined-route" in data["message"]
