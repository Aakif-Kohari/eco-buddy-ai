import pytest
from api_auth import generate_api_key, validate_api_key, revoke_api_key, list_api_keys, authenticate_request, init_api_keys_db
from sustainability_api import process_api_request, OPENAPI_SPEC, SWAGGER_UI_HTML


def setup_module(module):
    """Ensure API keys DB table is initialized before tests run."""
    init_api_keys_db()


def test_generate_and_validate_api_key():
    key_info = generate_api_key("Test Service App", user_id="test_user_1")
    assert key_info["app_name"] == "Test Service App"
    assert key_info["api_key"].startswith("eco_live_")
    assert key_info["key_prefix"].startswith("eco_live_")

    # Validate raw key
    validated = validate_api_key(key_info["api_key"])
    assert validated is not None
    assert validated["app_name"] == "Test Service App"
    assert validated["user_id"] == "test_user_1"

    # Revoke key
    revoked = revoke_api_key(key_info["id"])
    assert revoked is True

    # Validate after revocation
    assert validate_api_key(key_info["api_key"]) is None


def test_authenticate_request_headers():
    key_info = generate_api_key("Auth Header Test", user_id="test_user_2")
    raw_key = key_info["api_key"]

    # X-API-Key header
    is_auth, res = authenticate_request({"X-API-Key": raw_key})
    assert is_auth is True
    assert res["app_name"] == "Auth Header Test"

    # Bearer authorization header
    is_auth_b, res_b = authenticate_request({"Authorization": f"Bearer {raw_key}"})
    assert is_auth_b is True
    assert res_b["app_name"] == "Auth Header Test"

    # Invalid header
    is_auth_inv, res_inv = authenticate_request({"X-API-Key": "invalid_key_value"})
    assert is_auth_inv is False
    assert "Invalid" in res_inv

    # Missing header
    is_auth_m, res_m = authenticate_request({})
    assert is_auth_m is False
    assert "Missing" in res_m


def test_api_health_endpoint():
    code, data, content_type = process_api_request("GET", "/api/v1/health", {})
    assert code == 200
    assert data["status"] == "healthy"
    assert content_type == "application/json"


def test_api_openapi_spec():
    code, data, content_type = process_api_request("GET", "/api/v1/openapi.json", {})
    assert code == 200
    assert data["openapi"] == "3.0.3"
    assert "/api/v1/insights/calculate" in data["paths"]


def test_api_swagger_ui_docs():
    code, data, content_type = process_api_request("GET", "/docs", {})
    assert code == 200
    assert "SwaggerUIBundle" in data
    assert content_type == "text/html"


def test_api_calculate_insights_unauthorized():
    code, data, _ = process_api_request("POST", "/api/v1/insights/calculate", {}, body={})
    assert code == 401
    assert data["error"] == "Unauthorized"


def test_api_calculate_insights_success():
    key_info = generate_api_key("Calc Test App")
    headers = {"X-API-Key": key_info["api_key"]}
    body = {
        "transport": "Car",
        "distance": 20.0,
        "electricity": 300.0,
        "diet": "Non-Vegetarian",
        "flights": 3
    }
    code, data, _ = process_api_request("POST", "/api/v1/insights/calculate", headers, body=body)
    assert code == 200
    assert data["success"] is True
    assert "annual_footprint_kg_co2" in data["data"]
    assert "eco_score" in data["data"]
    assert "recommendations" in data["data"]


def test_api_create_key_endpoint():
    code, data, _ = process_api_request("POST", "/api/v1/auth/keys", {}, body={"app_name": "API Provision App"})
    assert code == 201
    assert data["success"] is True
    assert "api_key" in data["data"]
