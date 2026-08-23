"""
Automated Regression Test Suite for Fixed Bugs
Single file implementation with all necessary components
"""

import os
import sys
import json
import time
import logging
import hashlib
import random
import string
import pytest
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================
# CONFIGURATION
# ============================================

class TestConfig:
    """Configuration settings for regression tests"""
    
    # Base paths
    BASE_DIR = Path(__file__).parent
    TEST_DATA_DIR = BASE_DIR / "test_data"
    REPORTS_DIR = BASE_DIR / "test_reports"
    SCREENSHOTS_DIR = BASE_DIR / "screenshots"
    LOGS_DIR = BASE_DIR / "test_logs"
    
    # Test execution settings
    PARALLEL_EXECUTION = False
    MAX_WORKERS = 4
    RETRY_COUNT = 2
    RETRY_DELAY = 5  # seconds
    
    # Reporting
    GENERATE_HTML_REPORT = True
    GENERATE_XML_REPORT = True
    REPORT_NAME = "regression_test_report"
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = LOGS_DIR / "regression_tests.log"
    
    # API Settings
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    API_TIMEOUT = 30
    API_RETRY = 3
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories if they don't exist"""
        directories = [
            cls.TEST_DATA_DIR,
            cls.REPORTS_DIR,
            cls.SCREENSHOTS_DIR,
            cls.LOGS_DIR
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

# ============================================
# LOGGING SETUP
# ============================================

# Configure logging
TestConfig.create_directories()
logging.basicConfig(
    level=TestConfig.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(TestConfig.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# TEST HELPERS
# ============================================

class TestHelpers:
    """Helper methods for test operations"""
    
    @staticmethod
    def generate_unique_id(prefix: str = "") -> str:
        """Generate unique identifier"""
        timestamp = int(time.time() * 1000)
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{prefix}_{timestamp}_{random_suffix}"
    
    @staticmethod
    def generate_test_email() -> str:
        """Generate unique test email"""
        return f"test_{TestHelpers.generate_unique_id()}@example.com"
    
    @staticmethod
    def generate_test_phone() -> str:
        """Generate test phone number"""
        return f"+1{''.join(random.choices(string.digits, k=10))}"
    
    @staticmethod
    def calculate_hash(data: Any) -> str:
        """Calculate hash of data for verification"""
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True)
        return hashlib.md5(str(data).encode()).hexdigest()
    
    @staticmethod
    def wait_for_condition(condition_func, timeout: int = 30, interval: int = 1):
        """Wait for a condition to be true"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        return False
    
    @staticmethod
    def compare_json_structures(expected: Dict, actual: Dict, 
                                ignore_keys: List[str] = None) -> bool:
        """Compare JSON structures with option to ignore keys"""
        if ignore_keys is None:
            ignore_keys = []
        
        def clean_data(data):
            if isinstance(data, dict):
                return {k: clean_data(v) for k, v in data.items() 
                       if k not in ignore_keys}
            elif isinstance(data, list):
                return [clean_data(item) for item in data]
            return data
        
        cleaned_expected = clean_data(expected)
        cleaned_actual = clean_data(actual)
        
        return cleaned_expected == cleaned_actual
    
    @staticmethod
    def create_mock_response(status_code: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create mock response for testing"""
        return {
            "status_code": status_code,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def extract_value_from_path(data: Dict, path: str) -> Any:
        """Extract value from nested dict using dot notation"""
        keys = path.split('.')
        current = data
        for key in keys:
            if key in current:
                current = current[key]
            else:
                return None
        return current
    
    @staticmethod
    def generate_test_data_suite(test_type: str) -> Dict[str, Any]:
        """Generate comprehensive test data suite"""
        data_suites = {
            "user": {
                "valid": {
                    "username": "testuser",
                    "email": TestHelpers.generate_test_email(),
                    "password": "Test@123456",
                    "age": 25,
                    "phone": TestHelpers.generate_test_phone()
                },
                "invalid": {
                    "username": "",
                    "email": "invalid-email",
                    "password": "123",
                    "age": -5,
                    "phone": "123"
                },
                "edge": {
                    "username": "a" * 50,
                    "email": "test@example.com",
                    "password": "A" * 100,
                    "age": 0,
                    "phone": "+" + "1" * 15
                }
            },
            "order": {
                "valid": {
                    "items": [
                        {"id": 1, "quantity": 2, "price": 10.99},
                        {"id": 2, "quantity": 1, "price": 25.50}
                    ],
                    "shipping_address": "123 Test St, Test City, TC 12345",
                    "payment_method": "credit_card"
                },
                "invalid": {
                    "items": [],
                    "shipping_address": "",
                    "payment_method": "invalid_method"
                },
                "edge": {
                    "items": [{"id": 1, "quantity": 9999, "price": 0.01}],
                    "shipping_address": "x" * 1000,
                    "payment_method": "crypto"
                }
            }
        }
        
        return data_suites.get(test_type, {})

# ============================================
# TEST BASE CLASS
# ============================================

class TestBase:
    """Base class for all regression tests"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, request):
        """Setup method that runs before each test"""
        self.test_name = request.node.name
        self.test_start_time = datetime.now()
        self.test_data = {}
        self.verification_results = []
        self.screenshots = []
        
        logger.info(f"Starting test: {self.test_name}")
        TestConfig.create_directories()
        
        yield
        
        # Teardown
        test_duration = (datetime.now() - self.test_start_time).total_seconds()
        logger.info(f"Completed test: {self.test_name} (Duration: {test_duration:.2f}s)")
        
        # Save test artifacts if needed
        self._save_test_artifacts()
    
    def _save_test_artifacts(self):
        """Save test artifacts like screenshots, logs, etc."""
        if hasattr(self, 'screenshots') and self.screenshots:
            screenshot_dir = TestConfig.SCREENSHOTS_DIR / self.test_name
            screenshot_dir.mkdir(exist_ok=True)
            for idx, screenshot in enumerate(self.screenshots):
                file_path = screenshot_dir / f"screenshot_{idx}.png"
                # In real implementation, save screenshot
                logger.info(f"Screenshot saved: {file_path}")
    
    def verify_response(self, response: requests.Response, 
                        expected_status: int = 200,
                        expected_data: Optional[Dict] = None) -> bool:
        """Verify API response status and data"""
        try:
            # Check status code
            assert response.status_code == expected_status, \
                f"Expected status {expected_status}, got {response.status_code}"
            
            # Check response data
            if expected_data:
                response_data = response.json()
                for key, value in expected_data.items():
                    assert response_data.get(key) == value, \
                        f"Expected {key}={value}, got {response_data.get(key)}"
            
            logger.info(f"Verification passed for {response.url}")
            return True
            
        except AssertionError as e:
            logger.error(f"Verification failed: {str(e)}")
            self.verification_results.append({
                'test': self.test_name,
                'status': 'failed',
                'error': str(e)
            })
            raise
        except Exception as e:
            logger.error(f"Unexpected error during verification: {str(e)}")
            raise
    
    def create_test_data(self, data_type: str, **kwargs) -> Dict[str, Any]:
        """Create test data for different scenarios"""
        test_data_file = TestConfig.TEST_DATA_DIR / f"{data_type}.json"
        
        if test_data_file.exists():
            with open(test_data_file, 'r') as f:
                template = json.load(f)
            
            # Override with provided kwargs
            for key, value in kwargs.items():
                if key in template:
                    template[key] = value
            
            return template
        else:
            logger.warning(f"Test data template not found: {data_type}")
            return kwargs
    
    def assert_equals(self, actual: Any, expected: Any, message: str = ""):
        """Custom assertion with logging"""
        try:
            assert actual == expected, f"{message} Expected {expected}, got {actual}"
            logger.debug(f"Assertion passed: {actual} == {expected}")
        except AssertionError as e:
            logger.error(f"Assertion failed: {str(e)}")
            raise
    
    def assert_true(self, condition: bool, message: str = ""):
        """Custom assertion for true condition"""
        try:
            assert condition, f"{message} Condition is False"
            logger.debug(f"Assertion passed: {condition}")
        except AssertionError as e:
            logger.error(f"Assertion failed: {str(e)}")
            raise

# ============================================
# FIXED BUGS TEST SUITE
# ============================================

class TestFixedBugs(TestBase):
    """Test suite for verifying fixed bugs don't regress"""
    
    @pytest.fixture
    def api_client(self):
        """Fixture for API client"""
        session = requests.Session()
        session.base_url = TestConfig.API_BASE_URL
        session.timeout = TestConfig.API_TIMEOUT
        return session
    
    @pytest.mark.regression
    @pytest.mark.bug_fix
    def test_fixed_bug_123_profile_update(self, api_client):
        """
        BUG-123: Profile update with special characters
        Verify that special characters are properly sanitized
        """
        logger.info("Testing fixed bug: BUG-123")
        
        # Test data
        test_payload = {
            "user_id": 1,
            "name": "<script>alert('xss')</script>",
            "bio": "Test & Special < > \" ' characters",
            "email": "test@example.com"
        }
        
        # Execute test scenario
        response = self._execute_request(
            api_client,
            "/api/users/1/profile",
            "POST",
            test_payload
        )
        
        # Verify response
        self.verify_response(response, expected_status=200)
        
        # Bug-specific verification
        data = response.json()
        assert "profile_updated" in data
        assert data["profile_updated"] is True
        
        # Verify sanitization
        if "sanitized_data" in data:
            sanitized = data["sanitized_data"]
            assert "<script>" not in str(sanitized)
            assert "&lt;" in str(sanitized) or "&gt;" in str(sanitized)
        
        logger.info("BUG-123 regression test passed")
    
    @pytest.mark.regression
    @pytest.mark.bug_fix
    def test_fixed_bug_456_account_deletion(self, api_client):
        """
        BUG-456: Account deletion with dependencies
        Verify that all associated data is properly removed
        """
        logger.info("Testing fixed bug: BUG-456")
        
        # Test data
        test_payload = {
            "user_id": 2,
            "delete_associated_data": True,
            "reason": "Testing account deletion"
        }
        
        # Execute test scenario
        response = self._execute_request(
            api_client,
            "/api/users/2/delete",
            "DELETE",
            test_payload
        )
        
        # Verify response
        self.verify_response(response, expected_status=200)
        
        # Bug-specific verification
        data = response.json()
        assert "deleted" in data
        assert data["deleted"] is True
        assert "associated_data_removed" in data
        assert data["associated_data_removed"] is True
        
        # Verify deletion timestamp
        if "deleted_at" in data:
            deleted_time = datetime.fromisoformat(data["deleted_at"])
            assert datetime.now() - deleted_time < timedelta(minutes=5)
        
        logger.info("BUG-456 regression test passed")
    
    @pytest.mark.regression
    @pytest.mark.bug_fix
    def test_fixed_bug_789_order_creation(self, api_client):
        """
        BUG-789: Order creation with edge cases
        Verify order total calculation and status
        """
        logger.info("Testing fixed bug: BUG-789")
        
        # Test data
        test_payload = {
            "items": [
                {"id": 1, "quantity": 2, "price": 10.99},
                {"id": 2, "quantity": 1, "price": 25.50}
            ],
            "shipping_address": "123 Test St, Test City, TC 12345",
            "payment_method": "credit_card"
        }
        
        # Execute test scenario
        response = self._execute_request(
            api_client,
            "/api/orders",
            "POST",
            test_payload
        )
        
        # Verify response
        self.verify_response(response, expected_status=200)
        
        # Bug-specific verification
        data = response.json()
        assert "order_id" in data
        assert "status" in data
        assert data["status"] in ["pending", "confirmed"]
        
        # Verify order total calculation
        if "total" in data:
            assert data["total"] >= 0
            # Check for floating point precision
            assert abs(data["total"] - round(data["total"], 2)) < 0.001
        
        logger.info("BUG-789 regression test passed")
    
    @pytest.mark.regression
    @pytest.mark.bug_fix
    @pytest.mark.edge_cases
    def test_edge_cases_for_fixed_bugs(self, api_client):
        """
        Test edge cases around fixed bugs
        Ensures fixes handle boundary conditions properly
        """
        edge_cases = [
            {"test": "empty_input", "payload": {}},
            {"test": "max_length", "payload": {"data": "x" * 10000}},
            {"test": "special_chars", "payload": {"data": "!@#$%^&*()_+"}},
            {"test": "unicode", "payload": {"data": "😀🎉🚀💻"}}
        ]
        
        for edge_case in edge_cases:
            logger.info(f"Testing edge case: {edge_case['test']}")
            response = self._execute_request(
                api_client,
                "/api/test-edge-cases",
                "POST",
                edge_case["payload"]
            )
            
            # Should handle edge cases gracefully
            assert response.status_code in [200, 400]
            if response.status_code == 400:
                error_data = response.json()
                assert "error" in error_data
                assert "message" in error_data
            else:
                self.verify_response(response, expected_status=200)
    
    def _execute_request(self, client, endpoint: str, method: str, 
                         payload: Dict[str, Any]) -> requests.Response:
        """Execute HTTP request with retry logic"""
        url = f"{TestConfig.API_BASE_URL}{endpoint}"
        
        for attempt in range(TestConfig.RETRY_COUNT + 1):
            try:
                if method.upper() == "GET":
                    response = client.get(url, params=payload)
                elif method.upper() == "POST":
                    response = client.post(url, json=payload)
                elif method.upper() == "PUT":
                    response = client.put(url, json=payload)
                elif method.upper() == "DELETE":
                    response = client.delete(url, json=payload)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                logger.info(f"Executed {method} request to {endpoint}")
                return response
                
            except requests.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {str(e)}")
                if attempt < TestConfig.RETRY_COUNT:
                    time.sleep(TestConfig.RETRY_DELAY)
                    continue
                raise
        
        raise Exception(f"Request failed after {TestConfig.RETRY_COUNT} retries")

# ============================================
# TEST SUITE RUNNER
# ============================================

class TestSuiteRunner:
    """Main orchestrator for running regression test suites"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.test_results = []
        self.failed_tests = []
        self.passed_tests = []
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all regression tests"""
        logger.info("=" * 80)
        logger.info("STARTING REGRESSION TEST SUITE EXECUTION")
        logger.info("=" * 80)
        
        self.start_time = datetime.now()
        
        try:
            # Prepare test arguments
            test_args = [
                "-v",
                "--tb=short",
                "--maxfail=5",
                "--strict-markers",
                "-m", "regression",  # Only run regression tests
                __file__  # Run tests from this file
            ]
            
            # Add reporting options
            if TestConfig.GENERATE_HTML_REPORT:
                report_path = TestConfig.REPORTS_DIR / f"{TestConfig.REPORT_NAME}.html"
                test_args.extend(["--html", str(report_path)])
            
            if TestConfig.GENERATE_XML_REPORT:
                xml_path = TestConfig.REPORTS_DIR / f"{TestConfig.REPORT_NAME}.xml"
                test_args.extend(["--junitxml", str(xml_path)])
            
            # Run tests
            exit_code = pytest.main(test_args)
            
            # Record results
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            
            result_summary = {
                "status": "PASSED" if exit_code == 0 else "FAILED",
                "exit_code": exit_code,
                "duration": duration,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat()
            }
            
            logger.info("=" * 80)
            logger.info("REGRESSION TEST SUITE COMPLETED")
            logger.info(f"Status: {result_summary['status']}")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info("=" * 80)
            
            # Generate summary report
            self._generate_summary_report(result_summary)
            
            return result_summary
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {str(e)}")
            return {
                "status": "ERROR",
                "error": str(e),
                "duration": (datetime.now() - self.start_time).total_seconds()
            }
    
    def run_parallel_tests(self, test_files: List[str]) -> Dict[str, Any]:
        """Run tests in parallel"""
        if not TestConfig.PARALLEL_EXECUTION:
            return self.run_all_tests()
        
        logger.info(f"Running parallel tests with {TestConfig.MAX_WORKERS} workers")
        results = {}
        
        with ThreadPoolExecutor(max_workers=TestConfig.MAX_WORKERS) as executor:
            future_to_test = {
                executor.submit(self._run_test_file, file): file 
                for file in test_files
            }
            
            for future in as_completed(future_to_test):
                test_file = future_to_test[future]
                try:
                    results[test_file] = future.result()
                except Exception as e:
                    logger.error(f"Test {test_file} failed: {str(e)}")
                    results[test_file] = {"status": "ERROR", "error": str(e)}
        
        return self._aggregate_results(results)
    
    def _run_test_file(self, test_file: str) -> Dict[str, Any]:
        """Run a single test file"""
        logger.info(f"Running test file: {test_file}")
        try:
            test_args = ["-v", test_file, "--tb=short"]
            exit_code = pytest.main(test_args)
            return {
                "file": test_file,
                "status": "PASSED" if exit_code == 0 else "FAILED",
                "exit_code": exit_code
            }
        except Exception as e:
            logger.error(f"Error running {test_file}: {str(e)}")
            raise
    
    def _aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from parallel execution"""
        total = len(results)
        passed = sum(1 for r in results.values() if r.get("status") == "PASSED")
        failed = sum(1 for r in results.values() if r.get("status") == "FAILED")
        errors = sum(1 for r in results.values() if r.get("status") == "ERROR")
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "details": results
        }
    
    def _generate_summary_report(self, result_summary: Dict[str, Any]):
        """Generate a summary report in JSON format"""
        report_path = TestConfig.REPORTS_DIR / "summary_report.json"
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": result_summary,
            "environment": {
                "python_version": sys.version,
                "api_base_url": TestConfig.API_BASE_URL
            }
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Summary report generated: {report_path}")

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    """
    Main entry point for running the regression test suite
    """
    
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Run regression test suite for fixed bugs")
    parser.add_argument("--parallel", action="store_true", 
                       help="Run tests in parallel")
    parser.add_argument("--workers", type=int, default=4,
                       help="Number of parallel workers (default: 4)")
    parser.add_argument("--api-url", type=str,
                       help="Override API base URL")
    parser.add_argument("--log-level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level (default: INFO)")
    parser.add_argument("--test-file", type=str,
                       help="Run specific test file")
    
    args = parser.parse_args()
    
    # Update configuration
    TestConfig.PARALLEL_EXECUTION = args.parallel
    TestConfig.MAX_WORKERS = args.workers
    if args.api_url:
        TestConfig.API_BASE_URL = args.api_url
    TestConfig.LOG_LEVEL = args.log_level
    
    # Create runner and execute
    runner = TestSuiteRunner()
    
    if args.test_file:
        # Run specific test file
        result = runner._run_test_file(args.test_file)
        logger.info(f"Test file result: {result}")
    elif args.parallel:
        # Run parallel tests
        test_files = ["test_fixed_bugs.py", "test_edge_cases.py"]
        result = runner.run_parallel_tests(test_files)
        logger.info(f"Parallel test results: {result}")
    else:
        # Run all tests
        result = runner.run_all_tests()
        logger.info(f"Test suite result: {result}")
    
    # Exit with appropriate code
    if result.get("status") == "PASSED":
        sys.exit(0)
    else:
        sys.exit(1)
