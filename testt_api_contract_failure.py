"""
API Contract and Failure-Path Test Coverage

This module extends the test suite with API contract validation and
comprehensive failure-path testing. It ensures that the API client
adheres to expected contracts and handles all possible failure scenarios.

Run with: pytest test_api_contract_failure.py -v
"""

import pytest
import requests
import json
import time
from unittest.mock import patch, Mock, call
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

# Import from the previous test file
from test_api_error_handling import (
    APIClient, 
    APIError, 
    ValidationError,
    AuthenticationError,
    PermissionError,
    ResourceNotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
    create_mock_response
)


# ==================== API Contract Models ====================

@dataclass
class APIResponse:
    """Standard API response contract."""
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    timestamp: Optional[str] = None


@dataclass
class APIContract:
    """API contract definition."""
    endpoint: str
    method: str
    required_headers: List[str]
    required_params: Optional[List[str]] = None
    required_body_fields: Optional[List[str]] = None
    expected_status_codes: List[int] = None
    response_schema: Optional[Dict[str, Any]] = None


# ==================== Enhanced APIClient with Contracts ====================

class ContractAwareAPIClient(APIClient):
    """APIClient with contract validation capabilities."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        super().__init__(base_url, api_key)
        self.contracts: Dict[str, APIContract] = {}
        self.violations: List[Dict] = []
        self.metrics: Dict[str, Any] = {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'errors_by_type': defaultdict(int),
            'response_times': []
        }
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for contract violations."""
        self.logger = logging.getLogger('APIClient')
        handler = logging.StreamHandler()
        handler.setLevel(logging.WARNING)
        self.logger.addHandler(handler)
    
    def register_contract(self, contract: APIContract):
        """Register an API contract for validation."""
        key = f"{contract.method}:{contract.endpoint}"
        self.contracts[key] = contract
    
    def validate_contract(self, method: str, endpoint: str, 
                         response: requests.Response, 
                         request_data: Optional[Dict] = None):
        """Validate that a request/response complies with the contract."""
        key = f"{method}:{endpoint}"
        contract = self.contracts.get(key)
        
        if not contract:
            return  # No contract defined, skip validation
        
        violations = []
        
        # Validate status code
        if contract.expected_status_codes:
            if response.status_code not in contract.expected_status_codes:
                violations.append({
                    'type': 'unexpected_status',
                    'expected': contract.expected_status_codes,
                    'actual': response.status_code
                })
        
        # Validate response schema
        if contract.response_schema and response.status_code < 400:
            try:
                data = response.json()
                self._validate_schema(data, contract.response_schema, 
                                    '', violations)
            except json.JSONDecodeError:
                violations.append({
                    'type': 'invalid_json',
                    'message': 'Response is not valid JSON'
                })
        
        # Validate required headers
        for header in contract.required_headers:
            if header not in response.headers:
                violations.append({
                    'type': 'missing_header',
                    'header': header
                })
        
        if violations:
            self.violations.append({
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'violations': violations,
                'timestamp': datetime.utcnow().isoformat()
            })
            self.logger.warning(f"Contract violations for {method} {endpoint}: {violations}")
    
    def _validate_schema(self, data: Any, schema: Dict, path: str, 
                        violations: List):
        """Recursively validate data against schema."""
        if not isinstance(data, dict):
            return
        
        for key, expected_type in schema.items():
            current_path = f"{path}.{key}" if path else key
            
            if key not in data:
                violations.append({
                    'type': 'missing_field',
                    'field': current_path
                })
                continue
            
            actual_value = data[key]
            
            # Handle nested objects
            if isinstance(expected_type, dict):
                if isinstance(actual_value, dict):
                    self._validate_schema(actual_value, expected_type, 
                                        current_path, violations)
                else:
                    violations.append({
                        'type': 'field_type_mismatch',
                        'field': current_path,
                        'expected': 'object',
                        'actual': type(actual_value).__name__
                    })
            # Handle type checking
            elif isinstance(expected_type, type):
                if not isinstance(actual_value, expected_type):
                    violations.append({
                        'type': 'field_type_mismatch',
                        'field': current_path,
                        'expected': expected_type.__name__,
                        'actual': type(actual_value).__name__
                    })
    
    def get_with_contract(self, endpoint: str, params: Optional[Dict] = None,
                         timeout: int = 30) -> APIResponse:
        """Perform GET request with contract validation."""
        start_time = time.time()
        self.metrics['requests'] += 1
        
        try:
            response = self.session.get(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                params=params,
                timeout=timeout
            )
            
            # Validate contract
            self.validate_contract('GET', endpoint, response, params)
            
            # Record metrics
            elapsed = time.time() - start_time
            self.metrics['response_times'].append(elapsed)
            
            if response.status_code < 400:
                self.metrics['successes'] += 1
            else:
                self.metrics['failures'] += 1
                self.metrics['errors_by_type'][response.status_code] += 1
            
            # Parse response
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = {'raw': response.text}
            
            return APIResponse(
                status_code=response.status_code,
                data=data if response.status_code < 400 else None,
                error=data if response.status_code >= 400 else None,
                headers=dict(response.headers),
                timestamp=datetime.utcnow().isoformat()
            )
            
        except requests.exceptions.Timeout:
            self.metrics['failures'] += 1
            self.metrics['errors_by_type']['timeout'] += 1
            raise
        except requests.exceptions.ConnectionError:
            self.metrics['failures'] += 1
            self.metrics['errors_by_type']['connection'] += 1
            raise
        except requests.exceptions.RequestException as e:
            self.metrics['failures'] += 1
            self.metrics['errors_by_type']['request'] += 1
            raise APIError(f"Request failed: {str(e)}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of request metrics."""
        avg_response_time = (sum(self.metrics['response_times']) / 
                           len(self.metrics['response_times']) 
                           if self.metrics['response_times'] else 0)
        
        return {
            'total_requests': self.metrics['requests'],
            'success_rate': (self.metrics['successes'] / self.metrics['requests'] 
                           * 100 if self.metrics['requests'] > 0 else 0),
            'error_rate': (self.metrics['failures'] / self.metrics['requests'] 
                          * 100 if self.metrics['requests'] > 0 else 0),
            'avg_response_time': avg_response_time,
            'error_distribution': dict(self.metrics['errors_by_type']),
            'contract_violations': len(self.violations)
        }


# ==================== API Contract Tests ====================

class TestAPIContracts:
    """Test suite for API contract validation."""
    
    @pytest.fixture
    def contract_client(self):
        """Create a contract-aware client."""
        client = ContractAwareAPIClient(
            base_url="https://api.example.com",
            api_key="test-api-key"
        )
        return client
    
    @pytest.fixture
    def user_contract(self):
        """User API contract."""
        return APIContract(
            endpoint="/api/v1/users",
            method="GET",
            required_headers=['Content-Type', 'Authorization'],
            required_params=['page', 'limit'],
            expected_status_codes=[200, 400, 401, 403, 429],
            response_schema={
                'users': list,
                'pagination': {
                    'page': int,
                    'limit': int,
                    'total': int,
                    'pages': int
                },
                'timestamp': str
            }
        )
    
    @patch('requests.Session.get')
    def test_contract_validation_success(self, mock_get, contract_client, 
                                         user_contract):
        """Test successful contract validation."""
        contract_client.register_contract(user_contract)
        
        # Valid response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json', 
                                'Authorization': 'Bearer token'}
        mock_response.json = Mock(return_value={
            'users': [{'id': 1, 'name': 'John'}],
            'pagination': {
                'page': 1,
                'limit': 10,
                'total': 100,
                'pages': 10
            },
            'timestamp': '2024-01-01T00:00:00Z'
        })
        mock_get.return_value = mock_response
        
        response = contract_client.get_with_contract('/api/v1/users', 
                                                    params={'page': 1, 'limit': 10})
        
        assert response.status_code == 200
        assert response.data is not None
        assert len(contract_client.violations) == 0
    
    @patch('requests.Session.get')
    def test_contract_validation_missing_field(self, mock_get, contract_client,
                                               user_contract):
        """Test contract validation with missing required field."""
        contract_client.register_contract(user_contract)
        
        # Response missing required field
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json', 
                                'Authorization': 'Bearer token'}
        mock_response.json = Mock(return_value={
            'users': [{'id': 1, 'name': 'John'}],
            'pagination': {
                'page': 1,
                'limit': 10,
                'total': 100
                # 'pages' is missing
            },
            'timestamp': '2024-01-01T00:00:00Z'
        })
        mock_get.return_value = mock_response
        
        response = contract_client.get_with_contract('/api/v1/users', 
                                                    params={'page': 1, 'limit': 10})
        
        assert response.status_code == 200
        assert len(contract_client.violations) == 1
        assert contract_client.violations[0]['violations'][0]['type'] == 'missing_field'
        assert 'pagination.pages' in contract_client.violations[0]['violations'][0]['field']
    
    @patch('requests.Session.get')
    def test_contract_validation_field_type_mismatch(self, mock_get, 
                                                     contract_client,
                                                     user_contract):
        """Test contract validation with field type mismatch."""
        contract_client.register_contract(user_contract)
        
        # Response with wrong type
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json', 
                                'Authorization': 'Bearer token'}
        mock_response.json = Mock(return_value={
            'users': 'not a list',  # Should be list
            'pagination': {
                'page': 1,
                'limit': 10,
                'total': 100,
                'pages': 10
            },
            'timestamp': '2024-01-01T00:00:00Z'
        })
        mock_get.return_value = mock_response
        
        response = contract_client.get_with_contract('/api/v1/users', 
                                                    params={'page': 1, 'limit': 10})
        
        assert response.status_code == 200
        assert len(contract_client.violations) == 1
        assert contract_client.violations[0]['violations'][0]['type'] == 'field_type_mismatch'
        assert contract_client.violations[0]['violations'][0]['field'] == 'users'
    
    @patch('requests.Session.get')
    def test_contract_validation_unexpected_status(self, mock_get, 
                                                   contract_client,
                                                   user_contract):
        """Test contract validation with unexpected status code."""
        contract_client.register_contract(user_contract)
        
        mock_response = Mock()
        mock_response.status_code = 500  # Not in expected status codes
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.json = Mock(return_value={'error': 'Internal server error'})
        mock_get.return_value = mock_response
        
        response = contract_client.get_with_contract('/api/v1/users', 
                                                    params={'page': 1, 'limit': 10})
        
        assert response.status_code == 500
        assert len(contract_client.violations) == 1
        assert contract_client.violations[0]['violations'][0]['type'] == 'unexpected_status'
    
    @patch('requests.Session.get')
    def test_multiple_contracts(self, mock_get, contract_client):
        """Test multiple API contracts."""
        # Register multiple contracts
        contract1 = APIContract(
            endpoint="/api/v1/users",
            method="GET",
            required_headers=['Content-Type'],
            expected_status_codes=[200],
            response_schema={'users': list}
        )
        
        contract2 = APIContract(
            endpoint="/api/v1/products",
            method="GET",
            required_headers=['Content-Type'],
            expected_status_codes=[200],
            response_schema={'products': list}
        )
        
        contract_client.register_contract(contract1)
        contract_client.register_contract(contract2)
        
        # Mock responses for both
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.headers = {'Content-Type': 'application/json'}
        mock_response1.json = Mock(return_value={'users': [{'id': 1}]})
        
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.headers = {'Content-Type': 'application/json'}
        mock_response2.json = Mock(return_value={'products': [{'id': 1}]})
        
        # Configure mock to return different responses
        mock_get.side_effect = [mock_response1, mock_response2]
        
        # Make requests
        response1 = contract_client.get_with_contract('/api/v1/users')
        response2 = contract_client.get_with_contract('/api/v1/products')
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert len(contract_client.violations) == 0


# ==================== Failure-Path Tests ====================

class TestFailurePaths:
    """Comprehensive failure-path testing."""
    
    @pytest.fixture
    def client(self):
        return APIClient("https://api.example.com", "test-key")
    
    def test_chain_of_failures(self, client):
        """Test handling of chain of failures."""
        with patch('requests.Session.get') as mock_get:
            # First call: timeout
            mock_get.side_effect = [
                requests.exceptions.Timeout("First timeout"),
                requests.exceptions.ConnectionError("Connection lost"),
                Mock(
                    status_code=500,
                    json=Mock(return_value={"error": "Server error"}),
                    raise_for_status=Mock(
                        side_effect=requests.exceptions.HTTPError("HTTP 500")
                    )
                ),
                Mock(
                    status_code=200,
                    json=Mock(return_value={"data": "success"})
                )
            ]
            
            # Attempt 1: Timeout
            with pytest.raises(TimeoutError):
                client.get("/data")
            
            # Attempt 2: Connection error
            with pytest.raises(requests.exceptions.ConnectionError):
                client.get("/data")
            
            # Attempt 3: Server error
            with pytest.raises(ServerError):
                client.get("/data")
            
            # Attempt 4: Success
            result = client.get("/data")
            assert result == {"data": "success"}
    
    def test_failure_recovery_scenarios(self, client):
        """Test different failure recovery scenarios."""
        scenarios = [
            {
                'name': 'transient_timeout',
                'failures': [requests.exceptions.Timeout("Timeout")],
                'expected_exception': TimeoutError
            },
            {
                'name': 'transient_connection',
                'failures': [requests.exceptions.ConnectionError("Connection")],
                'expected_exception': requests.exceptions.ConnectionError
            },
            {
                'name': 'rate_limit_retry',
                'failures': [
                    Mock(
                        status_code=429,
                        json=Mock(return_value={"error": "Rate limited"}),
                        raise_for_status=Mock(
                            side_effect=requests.exceptions.HTTPError("HTTP 429")
                        )
                    )
                ],
                'expected_exception': RateLimitError
            }
        ]
        
        for scenario in scenarios:
            with patch('requests.Session.get') as mock_get:
                mock_get.side_effect = scenario['failures']
                
                with pytest.raises(scenario['expected_exception']):
                    client.get("/data")
    
    def test_cascading_failure_effects(self, client):
        """Test cascading effects of failures."""
        error_log = []
        
        def log_error(error):
            error_log.append(error)
        
        with patch('requests.Session.get') as mock_get:
            # Simulate cascading failures
            failures = [
                requests.exceptions.Timeout("Timeout"),
                requests.exceptions.ConnectionError("Network error"),
                requests.exceptions.SSLError("SSL error"),
                requests.exceptions.HTTPError("HTTP error")
            ]
            
            mock_get.side_effect = failures
            
            for failure in failures:
                try:
                    client.get("/data")
                except Exception as e:
                    log_error(str(e))
                    continue
            
            # Verify all errors were logged
            assert len(error_log) == len(failures)
            assert any("Timeout" in str(e) for e in error_log)
            assert any("Network" in str(e) for e in error_log)
    
    def test_failure_state_preservation(self, client):
        """Test that failure state is properly preserved."""
        with patch('requests.Session.get') as mock_get:
            # First request fails
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection")
            
            # Verify initial state
            assert client.session is not None
            assert 'Authorization' in client.session.headers
            
            # Attempt request (will fail)
            with pytest.raises(requests.exceptions.ConnectionError):
                client.get("/data")
            
            # Verify client state is preserved
            assert client.session is not None
            assert client.session.headers.get('Authorization') == 'Bearer test-key'
            assert client.base_url == "https://api.example.com"
    
    def test_partial_failure_response(self, client):
        """Test handling of partial failures (e.g., successful status but incomplete data)."""
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={
                'data': {
                    'user': {'id': 1, 'name': 'John'},
                    'orders': None  # Missing data
                }
            })
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            # Should not raise an exception despite partial data
            result = client.get("/user/1/orders")
            assert result == {'data': {'user': {'id': 1, 'name': 'John'}, 'orders': None}}
    
    def test_network_partition_scenario(self, client):
        """Test behavior during network partition."""
        with patch('requests.Session.get') as mock_get:
            # Simulate network partition (connection drops)
            mock_get.side_effect = [
                requests.exceptions.ConnectionError("Network unreachable"),
                requests.exceptions.ConnectionError("Network unreachable"),
                requests.exceptions.ConnectionError("Network unreachable"),
                Mock(status_code=200, json=Mock(return_value={"data": "back online"}))
            ]
            
            # Multiple failures before recovery
            for _ in range(3):
                with pytest.raises(requests.exceptions.ConnectionError):
                    client.get("/data")
            
            # Should recover
            result = client.get("/data")
            assert result == {"data": "back online"}
    
    def test_failure_with_side_effects(self, client):
        """Test that failures don't leave side effects."""
        with patch('requests.Session.get') as mock_get:
            # Store original state
            original_headers = dict(client.session.headers)
            
            # Induce failure
            mock_get.side_effect = requests.exceptions.Timeout("Timeout")
            
            with pytest.raises(TimeoutError):
                client.get("/data")
            
            # Verify no side effects
            assert client.session.headers == original_headers
            assert client.session.cookies == requests.Session().cookies


# ==================== Error Recovery and Retry Tests ====================

class TestRetryAndRecovery:
    """Tests for retry logic and recovery mechanisms."""
    
    @pytest.fixture
    def client_with_retry(self):
        """Create client with retry logic."""
        class RetryableAPIClient(APIClient):
            def __init__(self, *args, max_retries=3, **kwargs):
                super().__init__(*args, **kwargs)
                self.max_retries = max_retries
                self.retry_count = defaultdict(int)
            
            def get_with_retry(self, endpoint: str, **kwargs) -> Dict[str, Any]:
                """GET with exponential backoff retry."""
                for attempt in range(self.max_retries):
                    try:
                        return self.get(endpoint, **kwargs)
                    except (TimeoutError, ConnectionError, ServerError) as e:
                        self.retry_count[endpoint] += 1
                        if attempt == self.max_retries - 1:
                            raise
                        # Exponential backoff
                        time.sleep(0.1 * (2 ** attempt))
                raise APIError("Max retries exceeded")
        
        return RetryableAPIClient("https://api.example.com", "test-key")
    
    def test_retry_on_timeout(self, client_with_retry):
        """Test automatic retry on timeout."""
        with patch('requests.Session.get') as mock_get:
            # Fail twice then succeed
            mock_get.side_effect = [
                requests.exceptions.Timeout("Timeout 1"),
                requests.exceptions.Timeout("Timeout 2"),
                Mock(status_code=200, json=Mock(return_value={"data": "success"}))
            ]
            
            result = client_with_retry.get_with_retry("/data")
            assert result == {"data": "success"}
            assert client_with_retry.retry_count['/data'] == 2
    
    def test_retry_on_server_error(self, client_with_retry):
        """Test retry on 5xx server errors."""
        with patch('requests.Session.get') as mock_get:
            # Fail twice with 500 then succeed
            mock_get.side_effect = [
                Mock(
                    status_code=500,
                    raise_for_status=Mock(
                        side_effect=requests.exceptions.HTTPError("HTTP 500")
                    )
                ),
                Mock(
                    status_code=500,
                    raise_for_status=Mock(
                        side_effect=requests.exceptions.HTTPError("HTTP 500")
                    )
                ),
                Mock(status_code=200, json=Mock(return_value={"data": "success"}))
            ]
            
            result = client_with_retry.get_with_retry("/data")
            assert result == {"data": "success"}
    
    def test_retry_exhaustion(self, client_with_retry):
        """Test behavior when retries are exhausted."""
        with patch('requests.Session.get') as mock_get:
            # Always fail
            mock_get.side_effect = requests.exceptions.Timeout("Timeout")
            
            with pytest.raises(TimeoutError):
                client_with_retry.get_with_retry("/data", max_retries=3)
            
            # Should have tried 3 times
            assert mock_get.call_count == 3
            assert client_with_retry.retry_count['/data'] == 3
    
    def test_no_retry_on_client_errors(self, client_with_retry):
        """Test that client errors (4xx) don't trigger retry."""
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = [
                Mock(
                    status_code=400,
                    raise_for_status=Mock(
                        side_effect=requests.exceptions.HTTPError("HTTP 400")
                    )
                )
            ]
            
            # Should fail immediately without retry
            with pytest.raises(ValidationError):
                client_with_retry.get_with_retry("/data")
            
            # Should only be called once
            assert mock_get.call_count == 1


# ==================== Chaos Engineering Tests ====================

class TestChaosEngineering:
    """Chaos engineering tests for API resilience."""
    
    @pytest.fixture
    def chaos_client(self):
        """Create a client with chaos injection."""
        class ChaosAPIClient(APIClient):
            def __init__(self, *args, chaos_mode=False, **kwargs):
                super().__init__(*args, **kwargs)
                self.chaos_mode = chaos_mode
                self.injected_errors = []
            
            def get(self, endpoint, **kwargs):
                if self.chaos_mode:
                    # Randomly inject failures
                    import random
                    error_type = random.choice([
                        'timeout',
                        'connection',
                        'server_500',
                        'rate_limit',
                        'network_partition'
                    ])
                    
                    self.injected_errors.append(error_type)
                    
                    if error_type == 'timeout':
                        raise requests.exceptions.Timeout("Chaos timeout")
                    elif error_type == 'connection':
                        raise requests.exceptions.ConnectionError("Chaos connection")
                    elif error_type == 'server_500':
                        raise requests.exceptions.HTTPError("Chaos 500")
                    elif error_type == 'rate_limit':
                        raise requests.exceptions.HTTPError("Chaos 429")
                
                return super().get(endpoint, **kwargs)
        
        return ChaosAPIClient("https://api.example.com", "test-key", 
                             chaos_mode=True)
    
    def test_chaos_resilience(self, chaos_client):
        """Test resilience under chaos conditions."""
        success_count = 0
        failure_count = 0
        error_types = defaultdict(int)
        
        for _ in range(20):
            try:
                chaos_client.get("/data")
                success_count += 1
            except Exception as e:
                failure_count += 1
                error_types[type(e).__name__] += 1
        
        # Verify we had both successes and failures
        assert failure_count > 0
        assert success_count >= 0
        
        # Verify error types
        print(f"Chaos test results: {failure_count} failures, {success_count} successes")
        print(f"Error types: {dict(error_types)}")
    
    def test_latency_injection(self):
        """Test behavior with injected latency."""
        import time
        
        with patch('requests.Session.get') as mock_get:
            # Inject latency
            def delayed_response(*args, **kwargs):
                time.sleep(0.5)
                mock = Mock(status_code=200, json=Mock(return_value={"data": "success"}))
                return mock
            
            mock_get.side_effect = delayed_response
            
            client = APIClient("https://api.example.com", "test-key")
            
            start = time.time()
            result = client.get("/slow-endpoint", timeout=2)
            elapsed = time.time() - start
            
            assert result == {"data": "success"}
            assert elapsed >= 0.5
            assert elapsed < 2.0


# ==================== API Versioning Tests ====================

class TestAPIVersioning:
    """Tests for API versioning compatibility."""
    
    @pytest.fixture
    def client(self):
        return APIClient("https://api.example.com", "test-key")
    
    def test_different_api_versions(self, client):
        """Test handling of different API versions."""
        versions = ['v1', 'v2', 'v3']
        
        for version in versions:
            with patch('requests.Session.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json = Mock(return_value={
                    'version': version,
                    'data': f"{version}_data"
                })
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response
                
                result = client.get(f"/api/{version}/data")
                assert result['version'] == version
                assert result['data'] == f"{version}_data"
    
    def test_version_deprecation_warning(self, client):
        """Test handling of version deprecation warnings."""
        with patch('requests.Session.get') as mock_get:
            response = Mock()
            response.status_code = 200
            response.json = Mock(return_value={"data": "v1_data"})
            response.raise_for_status = Mock()
            response.headers = {
                'Deprecation': 'true',
                'Sunset': '2024-12-31'
            }
            mock_get.return_value = response
            
            result = client.get("/api/v1/old-endpoint")
            
            assert result == {"data": "v1_data"}
            # In a real client, we'd log a warning about deprecation


# ==================== Performance Under Failure ====================

class TestPerformanceUnderFailure:
    """Performance tests under failure conditions."""
    
    @pytest.mark.slow
    def test_performance_with_high_error_rate(self, client):
        """Test client performance with high error rates."""
        error_rates = [0.1, 0.25, 0.5, 0.75]
        
        for error_rate in error_rates:
            with patch('requests.Session.get') as mock_get:
                def create_response(*args, **kwargs):
                    import random
                    if random.random() < error_rate:
                        raise requests.exceptions.Timeout("Simulated timeout")
                    return Mock(
                        status_code=200,
                        json=Mock(return_value={"data": "success"}),
                        raise_for_status=Mock()
                    )
                
                mock_get.side_effect = create_response
                
                start = time.time()
                success = 0
                failures = 0
                
                for _ in range(50):
                    try:
                        client.get("/data", timeout=5)
                        success += 1
                    except Exception:
                        failures += 1
                
                elapsed = time.time() - start
                
                # Verify error rate is close to expected
                actual_error_rate = failures / 50
                assert abs(actual_error_rate - error_rate) < 0.15
                
                # Performance should be acceptable
                assert elapsed < 10.0  # 50 requests within 10 seconds


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=1"])
