"""
API Error Handling Tests

This module contains comprehensive tests for API error handling scenarios,
including validation errors, authentication failures, rate limiting,
server errors, and network issues.

Run with: pytest test_api_error_handling.py -v
"""

import pytest
import requests
import json
from unittest.mock import patch, Mock
from requests.exceptions import (
    Timeout,
    ConnectionError,
    HTTPError,
    RequestException
)
from typing import Dict, Any, Optional


class APIClient:
    """
    A simple API client for demonstration and testing purposes.
    This simulates a real API client with proper error handling.
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'API-Test-Client/1.0',
            'Accept': 'application/json'
        })
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle HTTP response with proper error checking."""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                error_data = response.json() if response.text else {}
                raise ValidationError(error_data.get('message', 'Bad request'), 
                                    status_code=400, 
                                    details=error_data)
            elif response.status_code == 401:
                raise AuthenticationError('Authentication failed', status_code=401)
            elif response.status_code == 403:
                raise PermissionError('Insufficient permissions', status_code=403)
            elif response.status_code == 404:
                raise ResourceNotFoundError('Resource not found', status_code=404)
            elif response.status_code == 429:
                raise RateLimitError('Rate limit exceeded', status_code=429)
            elif response.status_code >= 500:
                raise ServerError('Server error occurred', status_code=response.status_code)
            else:
                raise APIError(f'HTTP error {response.status_code}', 
                             status_code=response.status_code)
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return {'data': response.text}
    
    def get(self, endpoint: str, params: Optional[Dict] = None, 
            timeout: int = 30) -> Dict[str, Any]:
        """Perform GET request with error handling."""
        try:
            response = self.session.get(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                params=params,
                timeout=timeout
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise TimeoutError(f'Request timed out after {timeout} seconds')
        except requests.exceptions.ConnectionError:
            raise ConnectionError('Failed to connect to the server')
        except requests.exceptions.RequestException as e:
            raise APIError(f'Request failed: {str(e)}')
    
    def post(self, endpoint: str, data: Optional[Dict] = None,
             json_data: Optional[Dict] = None, timeout: int = 30) -> Dict[str, Any]:
        """Perform POST request with error handling."""
        try:
            response = self.session.post(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                data=data,
                json=json_data,
                timeout=timeout
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise TimeoutError(f'Request timed out after {timeout} seconds')
        except requests.exceptions.ConnectionError:
            raise ConnectionError('Failed to connect to the server')
        except requests.exceptions.RequestException as e:
            raise APIError(f'Request failed: {str(e)}')


# Custom Exceptions
class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 details: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(APIError):
    """Exception for validation errors (400)."""
    pass


class AuthenticationError(APIError):
    """Exception for authentication errors (401)."""
    pass


class PermissionError(APIError):
    """Exception for permission errors (403)."""
    pass


class ResourceNotFoundError(APIError):
    """Exception for resource not found errors (404)."""
    pass


class RateLimitError(APIError):
    """Exception for rate limit errors (429)."""
    pass


class ServerError(APIError):
    """Exception for server errors (5xx)."""
    pass


class TimeoutError(APIError):
    """Exception for timeout errors."""
    pass


# ==================== Test Cases ====================

class TestAPIErrorHandling:
    """Test suite for API error handling."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return APIClient(base_url="https://api.example.com", 
                        api_key="test-api-key")
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock response object."""
        def _mock_response(status_code=200, json_data=None, text=""):
            mock = Mock(spec=requests.Response)
            mock.status_code = status_code
            mock.text = json.dumps(json_data) if json_data else text
            mock.json = Mock(return_value=json_data if json_data else {})
            mock.raise_for_status = Mock()
            if status_code >= 400:
                mock.raise_for_status.side_effect = requests.exceptions.HTTPError(
                    f"HTTP Error {status_code}",
                    response=mock
                )
            return mock
        return _mock_response
    
    # ==================== HTTP Error Tests ====================
    
    @patch('requests.Session.get')
    def test_400_validation_error(self, mock_get, client, mock_response):
        """Test handling of 400 Bad Request errors."""
        error_data = {
            "message": "Invalid email format",
            "details": {"field": "email", "error": "must be valid email"}
        }
        mock_get.return_value = mock_response(
            status_code=400, 
            json_data=error_data
        )
        
        with pytest.raises(ValidationError) as exc_info:
            client.get("/users/1")
        
        assert exc_info.value.status_code == 400
        assert "Invalid email format" in str(exc_info.value)
        assert exc_info.value.details == error_data
    
    @patch('requests.Session.get')
    def test_401_authentication_error(self, mock_get, client, mock_response):
        """Test handling of 401 Unauthorized errors."""
        mock_get.return_value = mock_response(status_code=401)
        
        with pytest.raises(AuthenticationError) as exc_info:
            client.get("/protected-resource")
        
        assert exc_info.value.status_code == 401
        assert "Authentication failed" in str(exc_info.value)
    
    @patch('requests.Session.get')
    def test_403_permission_error(self, mock_get, client, mock_response):
        """Test handling of 403 Forbidden errors."""
        mock_get.return_value = mock_response(status_code=403)
        
        with pytest.raises(PermissionError) as exc_info:
            client.get("/admin/users")
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in str(exc_info.value)
    
    @patch('requests.Session.get')
    def test_404_not_found_error(self, mock_get, client, mock_response):
        """Test handling of 404 Not Found errors."""
        mock_get.return_value = mock_response(status_code=404)
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            client.get("/non-existent-resource")
        
        assert exc_info.value.status_code == 404
        assert "Resource not found" in str(exc_info.value)
    
    @patch('requests.Session.get')
    def test_429_rate_limit_error(self, mock_get, client, mock_response):
        """Test handling of 429 Too Many Requests errors."""
        mock_get.return_value = mock_response(status_code=429)
        
        with pytest.raises(RateLimitError) as exc_info:
            client.get("/data")
        
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in str(exc_info.value)
    
    @patch('requests.Session.get')
    def test_500_server_error(self, mock_get, client, mock_response):
        """Test handling of 500 Internal Server Error."""
        mock_get.return_value = mock_response(status_code=500)
        
        with pytest.raises(ServerError) as exc_info:
            client.get("/data")
        
        assert exc_info.value.status_code == 500
        assert "Server error occurred" in str(exc_info.value)
    
    @patch('requests.Session.get')
    def test_502_bad_gateway(self, mock_get, client, mock_response):
        """Test handling of 502 Bad Gateway."""
        mock_get.return_value = mock_response(status_code=502)
        
        with pytest.raises(ServerError) as exc_info:
            client.get("/data")
        
        assert exc_info.value.status_code == 502
        assert "Server error occurred" in str(exc_info.value)
    
    # ==================== Network Error Tests ====================
    
    @patch('requests.Session.get')
    def test_timeout_error(self, mock_get, client):
        """Test handling of request timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        with pytest.raises(TimeoutError) as exc_info:
            client.get("/slow-endpoint", timeout=5)
        
        assert "timed out after 5 seconds" in str(exc_info.value)
    
    @patch('requests.Session.get')
    def test_connection_error(self, mock_get, client):
        """Test handling of connection errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Failed to establish connection"
        )
        
        with pytest.raises(requests.exceptions.ConnectionError) as exc_info:
            client.get("/data")
        
        assert "Failed to connect" in str(exc_info.value)
    
    @patch('requests.Session.get')
    def test_ssl_error(self, mock_get, client):
        """Test handling of SSL certificate errors."""
        mock_get.side_effect = requests.exceptions.SSLError(
            "SSL certificate verification failed"
        )
        
        with pytest.raises(requests.exceptions.SSLError):
            client.get("/secure-data")
    
    @patch('requests.Session.get')
    def test_request_exception(self, mock_get, client):
        """Test handling of general request exceptions."""
        mock_get.side_effect = requests.exceptions.RequestException(
            "Generic request failure"
        )
        
        with pytest.raises(APIError) as exc_info:
            client.get("/data")
        
        assert "Request failed" in str(exc_info.value)
    
    # ==================== POST Request Error Tests ====================
    
    @patch('requests.Session.post')
    def test_post_validation_error(self, mock_post, client, mock_response):
        """Test handling of POST request validation errors."""
        error_data = {"message": "Missing required fields"}
        mock_post.return_value = mock_response(status_code=400, json_data=error_data)
        
        with pytest.raises(ValidationError) as exc_info:
            client.post("/users", json_data={"name": "John"})
        
        assert exc_info.value.status_code == 400
        assert "Missing required fields" in str(exc_info.value)
    
    @patch('requests.Session.post')
    def test_post_timeout(self, mock_post, client):
        """Test POST request timeout handling."""
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        with pytest.raises(TimeoutError) as exc_info:
            client.post("/users", json_data={"name": "John"}, timeout=10)
        
        assert "timed out after 10 seconds" in str(exc_info.value)
    
    @patch('requests.Session.post')
    def test_post_connection_error(self, mock_post, client):
        """Test POST request connection error handling."""
        mock_post.side_effect = requests.exceptions.ConnectionError(
            "Failed to connect"
        )
        
        with pytest.raises(requests.exceptions.ConnectionError):
            client.post("/users", json_data={"name": "John"})
    
    # ==================== Response Parsing Tests ====================
    
    @patch('requests.Session.get')
    def test_non_json_response(self, mock_get, client, mock_response):
        """Test handling of non-JSON responses."""
        mock_get.return_value = mock_response(
            status_code=200, 
            text="<html><body>Not JSON</body></html>"
        )
        # Mock the json method to raise JSONDecodeError
        mock_get.return_value.json.side_effect = json.JSONDecodeError(
            "Expecting value", 
            "<html><body>Not JSON</body></html>", 
            0
        )
        
        result = client.get("/html-page")
        assert result == {"data": "<html><body>Not JSON</body></html>"}
    
    @patch('requests.Session.get')
    def test_empty_response(self, mock_get, client, mock_response):
        """Test handling of empty responses."""
        mock_get.return_value = mock_response(status_code=200, text="")
        mock_get.return_value.json.side_effect = json.JSONDecodeError(
            "Expecting value", 
            "", 
            0
        )
        
        result = client.get("/empty")
        assert result == {"data": ""}
    
    # ==================== Edge Cases Tests ====================
    
    @patch('requests.Session.get')
    def test_malformed_json_in_error_response(self, mock_get, client, mock_response):
        """Test handling of malformed JSON in error responses."""
        mock_get.return_value = mock_response(
            status_code=400,
            text="This is not JSON"
        )
        # Mock raise_for_status to raise HTTPError
        mock_get.return_value.raise_for_status.side_effect = \
            requests.exceptions.HTTPError(
                "HTTP Error 400",
                response=mock_get.return_value
            )
        
        with pytest.raises(ValidationError) as exc_info:
            client.get("/invalid-data")
        
        assert exc_info.value.status_code == 400
        assert "Bad request" in str(exc_info.value)
    
    @patch('requests.Session.get')
    def test_authentication_header_presence(self, mock_get, client):
        """Test that authentication headers are properly set."""
        client.get("/data")
        
        # Verify the Authorization header was included
        headers = mock_get.call_args[1].get('headers', {})
        assert 'Authorization' in client.session.headers
        assert client.session.headers['Authorization'] == 'Bearer test-api-key'
    
    @patch('requests.Session.get')
    def test_url_construction(self, mock_get, client):
        """Test that URLs are properly constructed."""
        client.get("/api/v1/users")
        
        # Verify the full URL was constructed correctly
        url = mock_get.call_args[0][0]
        assert url == "https://api.example.com/api/v1/users"
    
    @patch('requests.Session.get')
    def test_retry_on_connection_error(self, mock_get, client):
        """Test retry logic for connection errors (mock implementation)."""
        # Simulate two failures then success
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.ConnectionError("Connection failed again"),
            Mock(status_code=200, json=Mock(return_value={"data": "success"}))
        ]
        
        # This would typically include retry logic in a real client
        # For this test, we'll just verify the client doesn't handle it
        with pytest.raises(requests.exceptions.ConnectionError):
            client.get("/retry-endpoint")
    
    # ==================== Integration-Style Tests ====================
    
    def test_successful_response_after_error(self, client):
        """Test that the client can recover after an error."""
        # This is a more integrated test that doesn't use mocks
        # but tests the error handling logic directly
        
        with patch('requests.Session.get') as mock_get:
            # First request fails
            mock_get.side_effect = [
                requests.exceptions.Timeout("Timeout"),
                Mock(
                    status_code=200,
                    json=Mock(return_value={"data": "success"})
                )
            ]
            
            # First call should raise TimeoutError
            with pytest.raises(TimeoutError):
                client.get("/data", timeout=5)
            
            # Second call should succeed (in a real client with retry logic)
            # Here we're testing the error handling, not retry logic
            # So we just verify the second call would work
            result = client.get("/data")
            assert result == {"data": "success"}
    
    def test_error_context_preservation(self, client):
        """Test that error context (status code, details) is preserved."""
        error_data = {
            "message": "Invalid input",
            "details": {
                "errors": [
                    {"field": "email", "error": "required"},
                    {"field": "age", "error": "must be positive"}
                ]
            }
        }
        
        with patch('requests.Session.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=400,
                json=Mock(return_value=error_data)
            )
            mock_get.return_value.raise_for_status.side_effect = \
                requests.exceptions.HTTPError("HTTP Error 400")
            mock_get.return_value.text = json.dumps(error_data)
            
            with pytest.raises(ValidationError) as exc_info:
                client.get("/invalid-data")
            
            # Verify all context is preserved
            assert exc_info.value.status_code == 400
            assert exc_info.value.details == error_data
            assert "Invalid input" in str(exc_info.value)
    
    def test_custom_timeout_values(self, client):
        """Test that custom timeout values are passed correctly."""
        with patch('requests.Session.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={})
            )
            
            client.get("/data", timeout=60)
            
            # Verify timeout was passed correctly
            assert mock_get.call_args[1]['timeout'] == 60


# ==================== Parameterized Tests ====================

class TestErrorScenarios:
    """Parameterized tests for various error scenarios."""
    
    @pytest.mark.parametrize("status_code,expected_exception", [
        (400, ValidationError),
        (401, AuthenticationError),
        (403, PermissionError),
        (404, ResourceNotFoundError),
        (429, RateLimitError),
        (500, ServerError),
        (502, ServerError),
        (503, ServerError),
    ])
    def test_http_error_mapping(self, status_code, expected_exception, client):
        """Test that HTTP status codes map to the correct exceptions."""
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock(
                status_code=status_code,
                text=json.dumps({"message": f"Error {status_code}"})
            )
            mock_response.json = Mock(return_value={"message": f"Error {status_code}"})
            mock_response.raise_for_status.side_effect = \
                requests.exceptions.HTTPError(f"HTTP Error {status_code}", 
                                             response=mock_response)
            
            with pytest.raises(expected_exception):
                client.get("/test-endpoint")
    
    @pytest.mark.parametrize("timeout_value", [1, 5, 10, 30, 60])
    def test_timeout_values(self, timeout_value, client):
        """Test different timeout values are properly handled."""
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Timeout")
            
            with pytest.raises(TimeoutError) as exc_info:
                client.get("/data", timeout=timeout_value)
            
            assert str(timeout_value) in str(exc_info.value)
    
    @pytest.mark.parametrize("error_message,expected_substring", [
        ("Connection refused", "Failed to connect"),
        ("Network is unreachable", "Failed to connect"),
        ("Host is down", "Failed to connect"),
        ("Connection reset", "Failed to connect"),
    ])
    def test_connection_error_messages(self, error_message, expected_substring, 
                                       client):
        """Test various connection error messages."""
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError(
                error_message
            )
            
            with pytest.raises(requests.exceptions.ConnectionError) as exc_info:
                client.get("/data")
            
            # The error message should contain the original error
            assert error_message in str(exc_info.value) or \
                   expected_substring in str(exc_info.value)


# ==================== Performance Test ====================

class TestErrorPerformance:
    """Performance tests for error handling."""
    
    @pytest.mark.slow
    def test_error_handling_overhead(self, client):
        """Test that error handling doesn't add significant overhead."""
        import time
        
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Timeout")
            
            start_time = time.time()
            
            # Perform many error operations
            for _ in range(100):
                try:
                    client.get("/data", timeout=5)
                except TimeoutError:
                    pass
            
            duration = time.time() - start_time
            
            # The error handling should be reasonably fast
            # (< 0.5 seconds for 100 operations is acceptable)
            assert duration < 0.5


# ==================== Helper Functions ====================

def create_mock_response(status_code: int, json_data: Optional[Dict] = None,
                        text: str = "") -> Mock:
    """Helper to create mock responses for testing."""
    mock = Mock(spec=requests.Response)
    mock.status_code = status_code
    mock.text = text if text else json.dumps(json_data) if json_data else ""
    mock.json = Mock(return_value=json_data if json_data else {})
    mock.raise_for_status = Mock()
    if status_code >= 400:
        mock.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"HTTP Error {status_code}", response=mock
        )
    return mock


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
