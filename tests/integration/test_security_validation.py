import pytest
import html
import re

# --- Simulated Sanitization & Validation Engine ---
class SecurityGuard:
    """Core request parsing infrastructure for verifying input safety."""
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 100) -> str:
        if text is None:
            raise ValueError("Input cannot be null.")
        if not isinstance(text, str):
            raise TypeError("Input must be a string sequence.")
            
        # Oversized Request Prevention
        if len(text) > max_length:
            raise ValueError(f"Input exceeds maximum allowed length of {max_length} characters.")
            
        # Empty input validation
        if not text.strip():
            raise ValueError("Input text field cannot be empty.")

        # XSS & HTML Payload Mitigation: Escape characters safely
        sanitized = html.escape(text)
        
        # Block overt Script-like payloads explicitly
        if "<script>" in text.lower() or "javascript:" in text.lower():
            raise ValueError("Unsafe script execution signatures detected.")
            
        # SQL-like Payload Mitigation: Block destructive patterns
        sql_patterns = [r"\bunion\b", r"\bselect\b", r"\bdrop\b", r"--", r"\binsert\b", r"\bor\b"]
        if any(re.search(pattern, text.lower()) for pattern in sql_patterns):
            raise ValueError("Potential SQL injection signature rejected.")
            
        return sanitized

# --- Security Testing Suite ---

# 1 & 2. Empty Input and Null Values
@pytest.mark.parametrize("empty_input, expected_exception", [
    (None, ValueError),
    ("", ValueError),
    ("   ", ValueError)
])
def test_empty_and_null_inputs(empty_input, expected_exception):
    """Scenarios: Rejection of null objects, blank strings, or whitespace tokens."""
    with pytest.raises(expected_exception):
        SecurityGuard.sanitize_text(empty_input)


# 3. Boundary-Length & 10. Oversized Requests
@pytest.mark.parametrize("text_input, should_allow", [
    ("A" * 100, True),   # Exact maximum edge
    ("A" * 101, False),  # Immediate overflow boundary
])
def test_boundary_lengths_and_overflow(text_input, should_allow):
    """Scenarios: Validation of buffer boundaries and rejection of oversized parameters."""
    if should_allow:
        assert len(SecurityGuard.sanitize_text(text_input)) == 100
    else:
        with pytest.raises(ValueError, match="Input exceeds maximum allowed length"):
            SecurityGuard.sanitize_text(text_input)


# 4 & 5. Unicode and Special Characters
def test_unicode_and_special_character_normalization():
    """Scenarios: Safe normalization of multi-byte Unicode strings and punctuation marks."""
    unicode_payload = "🌿_EcoBuddy_🎯_漢字_@%#!"
    result = SecurityGuard.sanitize_text(unicode_payload)
    assert result == unicode_payload  # Verified safe structural content passes directly


# 6 & 7. HTML and Script-like Payloads (XSS Prevention)
@pytest.mark.parametrize("malicious_html, expect_raise", [
    ("<p>Hello</p>", False), # Standard harmless tag gets escaped safely
    ("<script>alert('xss')</script>", True), # Active scripts get blocked entirely
    ("javascript:void(0)", True)
])
def test_xss_and_html_payload_mitigation(malicious_html, expect_raise):
    """Scenarios: Escaping of markup text or immediate blocking of active code layers."""
    if expect_raise:
        with pytest.raises(ValueError, match="Unsafe script execution signatures"):
            SecurityGuard.sanitize_text(malicious_html)
    else:
        escaped_result = SecurityGuard.sanitize_text(malicious_html)
        assert "&lt;p&gt;" in escaped_result


# 8. SQL-like Payloads
@pytest.mark.parametrize("sql_payload", [
    ("1' OR '1'='1"),
    ("SELECT * FROM users; --"),
    ("DROP TABLE carbon_logs;")
])
def test_sql_injection_signatures_rejection(sql_payload):
    """Scenario: Checking detection blocks against structural relational database attack scripts."""
    with pytest.raises(ValueError, match="Potential SQL injection signature"):
        SecurityGuard.sanitize_text(sql_payload)


# 9. Unexpected Data Types
@pytest.mark.parametrize("wrong_type", [42, True, ["string_inside_list"], {"key": "val"}])
def test_unexpected_payload_data_types(wrong_type):
    """Scenario: Structural verification ensures non-string parameters are systematically blocked."""
    with pytest.raises(TypeError, match="Input must be a string sequence"):
        SecurityGuard.sanitize_text(wrong_type)
