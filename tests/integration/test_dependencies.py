import pytest
import requests
from unittest.mock import patch

# --- Simulated Client Layer ---
class CarbonRegistryClient:
    """External API Client interacting with third-party emission factor registries."""
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get_emission_factor(self, activity_type: str) -> dict:
        try:
            response = requests.get(f"{self.base_url}/v1/factors/{activity_type}", timeout=2.0)
            if response.status_code == 404:
                raise ValueError("Factor not found.")
            if response.status_code >= 500:
                raise RuntimeError("External Registry Server Error.")
            response.raise_for_status()
            
            data = response.json()
            if not data:
                raise ValueError("Empty response received.")
            if "factor" not in data:
                raise KeyError("Malformed payload structure.")
                
            return data
        except requests.exceptions.Timeout:
            raise TimeoutError("Registry request timed out.")
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Registry server unreachable.")

# --- Mocking Tests Suite ---

BASE_URL = "https://carbonregistry.internal"

@patch("requests.get")
def test_successful_dependency_response(mock_get):
    """Scenario 1: Successful deterministic 200 OK dependency response."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"activity": "flight", "factor": 0.24, "unit": "kg/km"}
    
    client = CarbonRegistryClient(BASE_URL)
    result = client.get_emission_factor("flight")
    
    assert result["factor"] == 0.24


@patch("requests.get")
def test_dependency_timeout(mock_get):
    """Scenario 2: Remote registry timeout scenario."""
    mock_get.side_effect = requests.exceptions.Timeout("Connection timed out.")
    client = CarbonRegistryClient(BASE_URL)
    
    with pytest.raises(TimeoutError, match="Registry request timed out"):
        client.get_emission_factor("flight")


@patch("requests.get")
def test_connection_failure(mock_get):
    """Scenario 3: Complete socket connection drop out."""
    mock_get.side_effect = requests.exceptions.ConnectionError("Failed to establish a new connection.")
    client = CarbonRegistryClient(BASE_URL)
    
    with pytest.raises(ConnectionError, match="Registry server unreachable"):
        client.get_emission_factor("flight")


@patch("requests.get")
def test_http_4xx_response(mock_get):
    """Scenario 4: Client-side HTTP 404 Missing payload error state."""
    mock_get.return_value.status_code = 404
    client = CarbonRegistryClient(BASE_URL)
    
    with pytest.raises(ValueError, match="Factor not found"):
        client.get_emission_factor("unknown_activity")


@patch("requests.get")
def test_http_5xx_response(mock_get):
    """Scenario 5: Remote server-side HTTP 500 crash event."""
    mock_get.return_value.status_code = 500
    client = CarbonRegistryClient(BASE_URL)
    
    with pytest.raises(RuntimeError, match="External Registry Server Error"):
        client.get_emission_factor("flight")


@patch("requests.get")
def test_malformed_dependency_response(mock_get):
    """Scenario 6 & 8: API responds with data lacking expected keys or dictionary formats."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"broken_field": "corrupted_val"} # Missing 'factor'
    client = CarbonRegistryClient(BASE_URL)
    
    with pytest.raises(KeyError, match="Malformed payload structure"):
        client.get_emission_factor("flight")


@patch("requests.get")
def test_empty_response(mock_get):
    """Scenario 7: Payload returns empty structures completely."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {}
    client = CarbonRegistryClient(BASE_URL)
    
    with pytest.raises(ValueError, match="Empty response received"):
        client.get_emission_factor("flight")
