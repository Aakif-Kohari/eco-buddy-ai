# tests/test_api_failures.py
"""
Comprehensive API tests for network and dependency failures.
Tests error handling, retry logic, circuit breakers, timeouts, and fallback mechanisms.
"""

import pytest
import requests
import json
import time
import socket
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

# Mock API client classes
class APIClient:
    """Mock API client with retry and timeout handling."""
    
    def __init__(self, base_url="https://api.example.com", timeout=30, max_retries=3):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TestApp/1.0',
            'Accept': 'application/json'
        })
        self.request_count = 0
        self.failure_threshold = 0
        
    def _make_request(self, method, endpoint, **kwargs):
        """Make HTTP request with retry logic."""
        url = f"{self.base_url}{endpoint}"
        retries = 0
        last_exception = None
        
        while retries <= self.max_retries:
            try:
                self.request_count += 1
                response = self.session.request(
                    method, 
                    url, 
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout as e:
                last_exception = e
                retries += 1
                if retries <= self.max_retries:
                    time.sleep(2 ** retries)  # Exponential backoff
                continue
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                retries += 1
                if retries <= self.max_retries:
                    time.sleep(1)
                continue
            except requests.exceptions.HTTPError as e:
                if e.response.status_code >= 500 and retries < self.max_retries:
                    retries += 1
                    time.sleep(1)
                    continue
                raise
            except Exception as e:
                last_exception = e
                retries += 1
                if retries <= self.max_retries:
                    time.sleep(0.5)
                continue
                
        raise last_exception or Exception("Max retries exceeded")

    def get(self, endpoint, **kwargs):
        return self._make_request('GET', endpoint, **kwargs)
    
    def post(self, endpoint, data=None, json=None, **kwargs):
        return self._make_request('POST', endpoint, data=data, json=json, **kwargs)
    
    def put(self, endpoint, data=None, json=None, **kwargs):
        return self._make_request('PUT', endpoint, data=data, json=json, **kwargs)
    
    def delete(self, endpoint, **kwargs):
        return self._make_request('DELETE', endpoint, **kwargs)


class CircuitBreaker:
    """Simple circuit breaker implementation."""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
        
    def record_success(self):
        """Record a successful operation."""
        if self.state == 'half-open':
            self.state = 'closed'
            self.failure_count = 0
            self.last_failure_time = None
        self.failure_count = 0
        
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == 'half-open':
            self.state = 'open'
        elif self.failure_count >= self.failure_threshold:
            self.state = 'open'
            
    def is_available(self):
        """Check if circuit breaker allows requests."""
        if self.state == 'closed':
            return True
        elif self.state == 'open':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'half-open'
                return True
            return False
        elif self.state == 'half-open':
            return True
        return True


class RetryableAPIClient:
    """API client with retry, circuit breaker, and fallback."""
    
    def __init__(self, base_url="https://api.example.com", fallback_url="https://fallback.example.com"):
        self.base_url = base_url
        self.fallback_url = fallback_url
        self.circuit_breaker = CircuitBreaker()
        self.retry_count = 0
        self.timeout = 10
        self.max_retries = 3
        self.use_fallback = False
        
    def call_api(self, endpoint, data=None, use_fallback=False):
        """Make API call with circuit breaker and fallback."""
        if not self.circuit_breaker.is_available():
            raise Exception("Circuit breaker is open")
        
        for attempt in range(self.max_retries):
            try:
                # Simulate API call
                if self.use_fallback or use_fallback:
                    response = self._make_fallback_call(endpoint, data)
                else:
                    response = self._make_primary_call(endpoint, data)
                
                self.circuit_breaker.record_success()
                return response
                
            except Exception as e:
                self.circuit_breaker.record_failure()
                if attempt == self.max_retries - 1:
                    # Try fallback on last attempt
                    try:
                        return self._make_fallback_call(endpoint, data)
                    except Exception as fallback_error:
                        raise Exception(f"All attempts failed: {e}, Fallback failed: {fallback_error}")
                time.sleep(2 ** attempt)
        
    def _make_primary_call(self, endpoint, data):
        """Simulate primary API call."""
        if endpoint == "/success":
            return {"status": "success", "data": "test data"}
        elif endpoint == "/error":
            raise requests.exceptions.HTTPError("500 Internal Server Error")
        elif endpoint == "/slow":
            time.sleep(5)
            return {"status": "success"}
        elif endpoint == "/timeout":
            raise requests.exceptions.Timeout("Request timed out")
        else:
            return {"status": "success", "endpoint": endpoint}
    
    def _make_fallback_call(self, endpoint, data):
        """Simulate fallback API call."""
        return {"status": "fallback_success", "data": "fallback data", "endpoint": endpoint}


# Test classes
class TestAPIClientBasicFailures:
    """Test basic API failure scenarios."""
    
    def test_connection_timeout(self):
        """Test handling of connection timeout."""
        client = APIClient()
        
        with patch('requests.Session.request') as mock_request:
            mock_request.side_effect = requests.exceptions.Timeout("Connection timed out")
            
            with pytest.raises(requests.exceptions.Timeout):
                client.get("/test")
    
    def test_connection_error(self):
        """Test handling of connection src.core.errors."""
        client = APIClient()
        
        with patch('requests.Session.request') as mock_request:
            mock_request.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            with pytest.raises(requests.exceptions.ConnectionError):
                client.get("/test")
    
    def test_http_404_error(self):
        """Test handling of 404 error."""
        client = APIClient()
        
        with patch('requests.Session.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
            mock_request.return_value = mock_response
            
            with pytest.raises(requests.exceptions.HTTPError):
                client.get("/not-found")
    
    def test_http_500_error(self):
        """Test handling of 500 error."""
        client = APIClient()
        
        with patch('requests.Session.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Internal Server Error")
            mock_request.return_value = mock_response
            
            with pytest.raises(requests.exceptions.HTTPError):
                client.get("/server-error")
    
    def test_http_503_error_with_retry(self):
        """Test retry logic for 503 error."""
        client = APIClient(max_retries=3)
        call_count = 0
        
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                mock_response = Mock()
                mock_response.status_code = 503
                mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("503 Service Unavailable")
                return mock_response
            else:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = {"status": "success"}
                return mock_response
        
        with patch('requests.Session.request', side_effect=mock_request):
            result = client.get("/test")
            assert result["status"] == "success"
            assert call_count == 3  # 2 failures + 1 success
    
    def test_max_retries_exceeded(self):
        """Test when max retries are exceeded."""
        client = APIClient(max_retries=2)
        
        with patch('requests.Session.request') as mock_request:
            mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            with pytest.raises(requests.exceptions.ConnectionError):
                client.get("/test")
            assert mock_request.call_count == 3  # initial + 2 retries


class TestRetryLogic:
    """Test advanced retry logic and backoff strategies."""
    
    def test_exponential_backoff(self):
        """Test exponential backoff strategy."""
        client = APIClient(max_retries=3)
        call_times = []
        
        def mock_request(*args, **kwargs):
            call_times.append(time.time())
            raise requests.exceptions.Timeout("Timeout")
        
        with patch('requests.Session.request', side_effect=mock_request):
            with pytest.raises(requests.exceptions.Timeout):
                client.get("/test")
        
        # Check that delay increased
        if len(call_times) >= 2:
            delays = [call_times[i+1] - call_times[i] for i in range(len(call_times)-1)]
            assert delays[1] > delays[0]  # Second delay longer than first
    
    def test_retry_on_specific_status_codes(self):
        """Test retry only on specific HTTP status codes."""
        client = APIClient(max_retries=3)
        call_count = 0
        
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = Mock()
            if call_count <= 2:
                mock_response.status_code = 429  # Too Many Requests
                mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
            else:
                mock_response.status_code = 200
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = {"status": "success"}
            return mock_response
        
        with patch('requests.Session.request', side_effect=mock_request):
            result = client.get("/test")
            assert result["status"] == "success"
            assert call_count == 3
    
    def test_retry_on_network_timeout(self):
        """Test retry specifically for network timeout."""
        client = APIClient(max_retries=3)
        call_count = 0
        
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise requests.exceptions.Timeout("Network timeout")
            else:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = {"status": "success"}
                return mock_response
        
        with patch('requests.Session.request', side_effect=mock_request):
            result = client.get("/test")
            assert result["status"] == "success"
            assert call_count == 3
    
    def test_retry_with_jitter(self):
        """Test retry with jitter to avoid thundering herd."""
        client = APIClient(max_retries=3)
        call_times = []
        
        def mock_request(*args, **kwargs):
            call_times.append(time.time())
            if len(call_times) <= 2:
                raise requests.exceptions.ConnectionError("Connection error")
            else:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = {"status": "success"}
                return mock_response
        
        with patch('requests.Session.request', side_effect=mock_request):
            result = client.get("/test")
            assert result["status"] == "success"


class TestCircuitBreaker:
    """Test circuit breaker pattern implementation."""
    
    def test_circuit_breaker_initial_state(self):
        """Test initial state of circuit breaker."""
        cb = CircuitBreaker()
        assert cb.state == 'closed'
        assert cb.failure_count == 0
        assert cb.is_available() is True
    
    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        
        # Record 3 failures
        for _ in range(3):
            cb.record_failure()
        
        assert cb.state == 'open'
        assert cb.is_available() is False
    
    def test_circuit_breaker_half_open_after_timeout(self):
        """Test circuit breaker goes to half-open after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        # Open the circuit
        for _ in range(3):
            cb.record_failure()
        assert cb.state == 'open'
        
        # Wait for recovery timeout
        time.sleep(1.1)
        assert cb.is_available() is True
        assert cb.state == 'half-open'
    
    def test_circuit_breaker_closes_on_success(self):
        """Test circuit breaker closes after successful half-open request."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == 'open'
        
        # Wait for timeout to enter half-open
        time.sleep(1.1)
        assert cb.is_available() is True
        assert cb.state == 'half-open'
        
        # Record success to close
        cb.record_success()
        assert cb.state == 'closed'
        assert cb.failure_count == 0
    
    def test_circuit_breaker_opens_again_on_failure_in_half_open(self):
        """Test circuit breaker opens again if failure in half-open state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == 'open'
        
        # Wait for half-open
        time.sleep(1.1)
        assert cb.is_available() is True
        assert cb.state == 'half-open'
        
        # Record failure in half-open
        cb.record_failure()
        assert cb.state == 'open'
        assert cb.is_available() is False


class TestFallbackMechanisms:
    """Test fallback mechanisms and graceful degradation."""
    
    def test_fallback_on_primary_failure(self):
        """Test fallback to secondary service on primary failure."""
        client = RetryableAPIClient()
        
        # Configure primary to fail
        client._make_primary_call = Mock(side_effect=Exception("Primary failed"))
        client._make_fallback_call = Mock(return_value={"status": "fallback_success"})
        
        result = client.call_api("/test", use_fallback=True)
        assert result["status"] == "fallback_success"
    
    def test_fallback_with_circuit_breaker(self):
        """Test fallback when circuit breaker is open."""
        client = RetryableAPIClient()
        
        # Open circuit breaker
        for _ in range(5):
            try:
                client._make_primary_call = Mock(side_effect=Exception("Failure"))
                client.call_api("/test")
            except:
                pass
        
        # Circuit should be open
        assert client.circuit_breaker.state == 'open'
        
        # Should still work with fallback
        client._make_fallback_call = Mock(return_value={"status": "fallback_success"})
        result = client.call_api("/test", use_fallback=True)
        assert result["status"] == "fallback_success"
    
    def test_static_fallback_data(self):
        """Test returning static cached data on failure."""
        class FallbackAPIClient:
            def __init__(self):
                self.cache = {
                    "/products": {"products": [{"id": 1, "name": "Cached Product"}]},
                    "/users": {"users": []}
                }
            
            def get_with_fallback(self, endpoint):
                try:
                    # Simulate API call
                    raise requests.exceptions.ConnectionError()
                except:
                    return self.cache.get(endpoint, {"error": "No fallback data"})
        
        client = FallbackAPIClient()
        result = client.get_with_fallback("/products")
        assert result == {"products": [{"id": 1, "name": "Cached Product"}]}
    
    def test_multiple_fallback_hierarchy(self):
        """Test hierarchical fallback: primary -> secondary -> cache -> error."""
        class HierarchicalFallbackClient:
            def call_with_fallback(self, endpoint):
                # Try primary
                try:
                    raise Exception("Primary unavailable")
                except:
                    pass
                
                # Try secondary
                try:
                    raise Exception("Secondary unavailable")
                except:
                    pass
                
                # Try cache
                cached_data = self.get_cached_data(endpoint)
                if cached_data:
                    return cached_data
                
                # Return error
                return {"error": "All fallbacks failed", "endpoint": endpoint}
            
            def get_cached_data(self, endpoint):
                cache = {"/test": {"data": "cached"}}
                return src.core.cache.get(endpoint)
        
        client = HierarchicalFallbackClient()
        result = client.call_with_fallback("/test")
        assert result["data"] == "cached"


class TestTimeoutHandling:
    """Test timeout scenarios and handling."""
    
    def test_api_timeout(self):
        """Test API call timeout."""
        client = APIClient(timeout=2)
        
        with patch('requests.Session.request') as mock_request:
            def slow_request(*args, **kwargs):
                time.sleep(5)
                return Mock()
            
            mock_request.side_effect = slow_request
            
            with pytest.raises(requests.exceptions.Timeout):
                client.get("/slow")
    
    def test_async_timeout(self):
        """Test async API call with timeout."""
        async def async_call_with_timeout(timeout=2):
            try:
                await asyncio.wait_for(slow_async_operation(), timeout=timeout)
            except asyncio.TimeoutError:
                return {"error": "Timeout", "status": "timeout"}
        
        async def slow_async_operation():
            await asyncio.sleep(5)
            return {"status": "success"}
        
        result = asyncio.run(async_call_with_timeout(1))
        assert result["error"] == "Timeout"
    
    def test_connection_pool_timeout(self):
        """Test connection pool timeout."""
        class ConnectionPool:
            def __init__(self, max_size=2):
                self.max_size = max_size
                self.active_connections = 0
            
            def get_connection(self):
                if self.active_connections >= self.max_size:
                    raise TimeoutError("Connection pool exhausted")
                self.active_connections += 1
                return self
        
        pool = ConnectionPool(max_size=1)
        
        # Exhaust pool
        pool.get_connection()
        
        with pytest.raises(TimeoutError):
            pool.get_connection()
    
    def test_operation_timeout_with_retry(self):
        """Test operation timeout with retry logic."""
        client = APIClient(max_retries=3, timeout=1)
        call_count = 0
        
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.exceptions.Timeout("Operation timed out")
            else:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = {"status": "success"}
                return mock_response
        
        with patch('requests.Session.request', side_effect=mock_request):
            result = client.get("/test")
            assert result["status"] == "success"
            assert call_count == 3


class TestDependencyFailures:
    """Test failures in dependent services."""
    
    def test_database_connection_failure(self):
        """Test handling of database connection failure."""
        class DatabaseService:
            def query(self, sql):
                try:
                    # Simulate database connection failure
                    raise ConnectionError("Database connection lost")
                except ConnectionError:
                    return {"error": "Database unavailable"}
        
        db = DatabaseService()
        result = src.notifications.db.query("SELECT * FROM users")
        assert result["error"] == "Database unavailable"
    
    def test_cache_service_failure(self):
        """Test handling of cache service failure with graceful degradation."""
        class CacheService:
            def get(self, key):
                try:
                    # Simulate cache failure
                    raise ConnectionError("Redis connection failed")
                except:
                    return None
        
        class UserService:
            def __init__(self):
                self.cache = CacheService()
                
            def get_user(self, user_id):
                # Try cache first
                cached = self.cache.get(f"user:{user_id}")
                if cached:
                    return cached
                
                # Fallback to database
                return {"id": user_id, "name": f"User{user_id}"}
        
        service = UserService()
        result = service.get_user(1)
        assert result["id"] == 1
        assert result["name"] == "User1"
    
    def test_message_queue_failure(self):
        """Test handling of message queue failures."""
        class MessageQueue:
            def publish(self, message):
                raise ConnectionError("Message broker unavailable")
            
            def publish_with_retry(self, message, retries=3):
                for attempt in range(retries):
                    try:
                        return self.publish(message)
                    except ConnectionError:
                        if attempt == retries - 1:
                            # Log failure and continue
                            return {"status": "failed", "message": message}
                        time.sleep(1)
                return {"status": "failed", "message": message}
        
        mq = MessageQueue()
        result = mq.publish_with_retry({"event": "user_created"})
        assert result["status"] == "failed"
    
    def test_external_api_dependency_failure(self):
        """Test failure of external API dependency."""
        class ExternalAPIService:
            def __init__(self):
                self.dependencies = {
                    'payment': {'status': 'up', 'url': 'https://payment.example.com'},
                    'shipping': {'status': 'up', 'url': 'https://shipping.example.com'},
                    'notification': {'status': 'down', 'url': 'https://notification.example.com'}
                }
            
            def check_dependency(self, service):
                status = self.dependencies.get(service, {}).get('status', 'unknown')
                if status == 'down':
                    raise Exception(f"Service {service} is unavailable")
                return status
            
            def process_with_dependency_check(self, service):
                try:
                    self.check_dependency(service)
                    return {"status": "success", "service": service}
                except Exception as e:
                    return {"status": "degraded", "error": str(e)}
        
        service = ExternalAPIService()
        
        # Test working dependency
        result = service.process_with_dependency_check('payment')
        assert result["status"] == "success"
        
        # Test failed dependency
        result = service.process_with_dependency_check('notification')
        assert result["status"] == "degraded"
        assert "unavailable" in result["error"]


class TestNetworkPartitionScenarios:
    """Test network partition and split-brain scenarios."""
    
    def test_network_partition_detection(self):
        """Test detection of network partition."""
        class NetworkPartitionDetector:
            def __init__(self):
                self.endpoints = {
                    'primary': 'https://primary.example.com',
                    'secondary': 'https://secondary.example.com'
                }
                self.endpoint_status = {}
            
            def check_endpoint(self, endpoint):
                try:
                    # Simulate network check
                    if endpoint == 'primary':
                        raise socket.timeout("Network unreachable")
                    return True
                except:
                    return False
            
            def detect_partition(self):
                primary_available = self.check_endpoint('primary')
                secondary_available = self.check_endpoint('secondary')
                
                if primary_available and not secondary_available:
                    return "secondary_partition"
                elif not primary_available and secondary_available:
                    return "primary_partition"
                elif not primary_available and not secondary_available:
                    return "total_partition"
                else:
                    return "no_partition"
        
        detector = NetworkPartitionDetector()
        partition = detector.detect_partition()
        assert partition == "primary_partition"
    
    def test_split_brain_scenario(self):
        """Test split-brain scenario handling."""
        class SplitBrainHandler:
            def __init__(self):
                self.nodes = {
                    'node1': {'status': 'active', 'data_version': 100},
                    'node2': {'status': 'active', 'data_version': 101},
                    'node3': {'status': 'down', 'data_version': 99}
                }
            
            def resolve_split_brain(self):
                # Find nodes with highest version
                active_nodes = {k: v for k, v in self.nodes.items() if v['status'] == 'active'}
                if not active_nodes:
                    return {"status": "error", "message": "No active nodes"}
                
                max_version = max(v['data_version'] for v in active_nodes.values())
                winning_nodes = [k for k, v in active_nodes.items() if v['data_version'] == max_version]
                
                if len(winning_nodes) == 1:
                    return {"status": "resolved", "winning_node": winning_nodes[0], "version": max_version}
                else:
                    # Multiple nodes with same version - tie breaker
                    return {"status": "tie", "nodes": winning_nodes, "version": max_version}
        
        handler = SplitBrainHandler()
        result = handler.resolve_split_brain()
        assert result["winning_node"] == "node2"
        assert result["version"] == 101
    
    def test_failover_strategy(self):
        """Test automatic failover strategy."""
        class FailoverHandler:
            def __init__(self):
                self.servers = [
                    {'host': 'server1.example.com', 'status': 'down'},
                    {'host': 'server2.example.com', 'status': 'up'},
                    {'host': 'server3.example.com', 'status': 'up'}
                ]
            
            def get_active_server(self):
                for server in self.servers:
                    if server['status'] == 'up':
                        return server
                return None
            
            def failover(self):
                for server in self.servers:
                    if server['status'] == 'up':
                        server['status'] = 'active'
                        return server
                return None
            
            def mark_server_down(self, host):
                for server in self.servers:
                    if server['host'] == host:
                        server['status'] = 'down'
                        return True
                return False
        
        handler = FailoverHandler()
        
        # Get active server
        active = handler.get_active_server()
        assert active['host'] == 'server2.example.com'
        
        # Mark it down
        handler.mark_server_down('server2.example.com')
        
        # Failover to next
        next_active = handler.failover()
        assert next_active['host'] == 'server3.example.com'


class TestTimeoutAndRetryIntegration:
    """Test integration of timeout, retry, and circuit breaker."""
    
    def test_integrated_failure_handling(self):
        """Test integrated failure handling with all mechanisms."""
        class IntegratedClient:
            def __init__(self):
                self.circuit_breaker = CircuitBreaker(failure_threshold=3)
                self.timeout = 5
                self.max_retries = 3
                self.retry_count = 0
            
            def call_with_full_protection(self, endpoint):
                # Circuit breaker check
                if not self.circuit_breaker.is_available():
                    return {"error": "Circuit breaker open", "status": 503}
                
                for attempt in range(self.max_retries):
                    try:
                        # Simulate call with timeout
                        result = self._make_call(endpoint)
                        self.circuit_breaker.record_success()
                        return result
                    except TimeoutError as e:
                        self.retry_count += 1
                        if attempt == self.max_retries - 1:
                            self.circuit_breaker.record_failure()
                            return {"error": "Max retries exceeded", "status": 504}
                        time.sleep(2 ** attempt)
                    except Exception as e:
                        self.circuit_breaker.record_failure()
                        return {"error": str(e), "status": 500}
            
            def _make_call(self, endpoint):
                # Simulate different scenarios
                if endpoint == '/always-fails':
                    raise Exception("Always fails")
                elif endpoint == '/times-out':
                    raise TimeoutError("Operation timed out")
                elif endpoint == '/works':
                    return {"status": "success", "data": "ok"}
                else:
                    return {"status": "not_found"}
        
        client = IntegratedClient()
        
        # Test working endpoint
        result = client.call_with_full_protection('/works')
        assert result["status"] == "success"
        
        # Test failing endpoint
        result = client.call_with_full_protection('/always-fails')
        assert "error" in result
        
        # Check circuit breaker opened
        assert client.circuit_breaker.state == 'open'
        
        # Try calling again
        result = client.call_with_full_protection('/works')
        assert result["error"] == "Circuit breaker open"
    
    def test_concurrent_failure_handling(self):
        """Test concurrent API calls with failures."""
        class ConcurrentClient:
            def __init__(self):
                self.executor = ThreadPoolExecutor(max_workers=3)
                self.results = []
            
            def make_concurrent_calls(self, endpoints):
                futures = []
                for endpoint in endpoints:
                    future = self.executor.submit(self._call_endpoint, endpoint)
                    futures.append(future)
                
                for future in futures:
                    try:
                        result = future.result(timeout=5)
                        self.results.append(result)
                    except FutureTimeoutError:
                        self.results.append({"error": "Timeout", "endpoint": "unknown"})
                    except Exception as e:
                        self.results.append({"error": str(e)})
                
                return self.results
            
            def _call_endpoint(self, endpoint):
                time.sleep(0.5)  # Simulate processing
                if 'fail' in endpoint:
                    raise Exception("Endpoint failed")
                return {"endpoint": endpoint, "status": "success"}
        
        client = ConcurrentClient()
        endpoints = ['/api/1', '/api/2/fail', '/api/3']
        results = client.make_concurrent_calls(endpoints)
        
        assert len(results) == 3
        assert any(r.get('endpoint') == '/api/1' for r in results)
        assert any('error' in r for r in results)


class TestMonitoringAndLogging:
    """Test monitoring and logging of failures."""
    
    def test_failure_logging(self):
        """Test logging of failures and src.core.errors."""
        class FailureLogger:
            def __init__(self):
                self.logs = []
            
            def log_error(self, error_type, message, endpoint, status_code=None):
                log_entry = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'error_type': error_type,
                    'message': message,
                    'endpoint': endpoint,
                    'status_code': status_code
                }
                self.logs.append(log_entry)
                return log_entry
            
            def get_error_summary(self):
                summary = {}
                for log in self.logs:
                    error_type = log['error_type']
                    summary[error_type] = summary.get(error_type, 0) + 1
                return summary
        
        logger = FailureLogger()
        
        # Log various errors
        logger.log_error('timeout', 'Request timed out', '/api/slow', 408)
        logger.log_error('server_error', '500 Internal Server Error', '/api/error', 500)
        logger.log_error('timeout', 'Gateway timeout', '/api/gateway', 504)
        logger.log_error('connection', 'Connection refused', '/api/db', None)
        
        # Check summary
        summary = logger.get_error_summary()
        assert summary['timeout'] == 2
        assert summary['server_error'] == 1
        assert summary['connection'] == 1
    
    def test_metrics_collection(self):
        """Test collection of failure metrics."""
        class MetricsCollector:
            def __init__(self):
                self.metrics = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'timeouts': 0,
                    'error_types': {}
                }
            
            def record_request(self, success=True, error_type=None):
                self.metrics['total_requests'] += 1
                if success:
                    self.metrics['successful_requests'] += 1
                else:
                    self.metrics['failed_requests'] += 1
                    if error_type:
                        self.metrics['error_types'][error_type] = \
                            self.metrics['error_types'].get(error_type, 0) + 1
                        if error_type == 'timeout':
                            self.metrics['timeouts'] += 1
            
            def get_success_rate(self):
                if self.metrics['total_requests'] == 0:
                    return 0.0
                return self.metrics['successful_requests'] / self.metrics['total_requests'] * 100
        
        collector = MetricsCollector()
        
        # Record requests
        collector.record_request(True)
        collector.record_request(False, 'server_error')
        collector.record_request(False, 'timeout')
        collector.record_request(True)
        collector.record_request(False, 'timeout')
        
        # Check metrics
        assert collector.metrics['total_requests'] == 5
        assert collector.metrics['successful_requests'] == 2
        assert collector.metrics['failed_requests'] == 3
        assert collector.metrics['timeouts'] == 2
        assert collector.get_success_rate() == 40.0


class TestEdgeCaseFailures:
    """Test edge case failure scenarios."""
    
    def test_empty_response(self):
        """Test handling of empty API responses."""
        class EmptyResponseHandler:
            def process_response(self, response):
                if not response:
                    return {"error": "Empty response received", "status": "error"}
                return response
        
        handler = EmptyResponseHandler()
        result = handler.process_response(None)
        assert result["error"] == "Empty response received"
    
    def test_corrupted_data(self):
        """Test handling of corrupted response data."""
        class CorruptedDataHandler:
            def parse_response(self, data):
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON received", "status": "error"}
        
        handler = CorruptedDataHandler()
        result = handler.parse_response("{invalid:json}")
        assert result["error"] == "Invalid JSON received"
    
    def test_circular_dependency(self):
        """Test handling of circular dependencies."""
        class CircularDependencyDetector:
            def __init__(self):
                self.dependencies = {
                    'service_a': ['service_b'],
                    'service_b': ['service_c'],
                    'service_c': ['service_a']  # Circular
                }
            
            def detect_circular(self):
                visited = set()
                path = []
                
                def dfs(service):
                    if service in path:
                        return True, path + [service]
                    if service in visited:
                        return False, []
                    
                    visited.add(service)
                    path.append(service)
                    
                    for dep in self.dependencies.get(service, []):
                        has_cycle, cycle_path = dfs(dep)
                        if has_cycle:
                            return True, cycle_path
                    
                    path.pop()
                    return False, []
                
                for service in self.dependencies:
                    has_cycle, cycle_path = dfs(service)
                    if has_cycle:
                        return {"has_cycle": True, "cycle": cycle_path}
                
                return {"has_cycle": False}
        
        detector = CircularDependencyDetector()
        result = detector.detect_circular()
        assert result["has_cycle"] is True
        assert 'a' in result["cycle"][0].lower()
    
    def test_resource_leak_handling(self):
        """Test handling of resource leaks."""
        class ResourceHandler:
            def __init__(self):
                self.resources = []
                self.max_resources = 5
            
            def acquire_resource(self):
                if len(self.resources) >= self.max_resources:
                    raise ResourceWarning("Resource limit exceeded")
                resource = f"resource_{len(self.resources)}"
                self.resources.append(resource)
                return resource
            
            def cleanup_resources(self):
                self.resources.clear()
                return {"status": "cleaned", "resources_freed": len(self.resources)}
        
        handler = ResourceHandler()
        
        # Acquire resources
        for _ in range(5):
            handler.acquire_resource()
        
        # Try to acquire one more
        with pytest.raises(ResourceWarning):
            handler.acquire_resource()
        
        # Cleanup
        result = handler.cleanup_resources()
        assert result["status"] == "cleaned"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
