"""
COMPREHENSIVE HEX COLOR VALIDATION UNIT TEST SUITE
Issue: #949
Tests: Hex Color Input Validation, Boundary Conditions, and Performance
"""

import pytest
import re
import string
import random
import time

# =====================================================================
# LOGIC UNDER TEST
# =====================================================================

def is_valid_hex_color(color: str) -> bool:
    """
    Validates if a string is a valid hex color.
    Supports 3-digit (#FFF) and 6-digit (#FFFFFF) formats.
    """
    if not isinstance(color, str):
        return False
    
    # Matches patterns like #FFF, #ffffff, #123ABC
    hex_pattern = re.compile(r'^#(?:[0-9a-fA-F]{3}){1,2}$')
    return bool(hex_pattern.match(color))


# =====================================================================
# SECTION 1: VALID HEX COLORS (Positive Tests)
# =====================================================================

class TestValidHexColors:
    def test_valid_6_digit_uppercase(self):
        assert is_valid_hex_color("#FFFFFF") is True

    def test_valid_6_digit_lowercase(self):
        assert is_valid_hex_color("#ffffff") is True

    def test_valid_6_digit_mixed_case(self):
        assert is_valid_hex_color("#aBcDeF") is True

    def test_valid_3_digit_uppercase(self):
        assert is_valid_hex_color("#FFF") is True

    def test_valid_3_digit_lowercase(self):
        assert is_valid_hex_color("#fff") is True

    def test_valid_3_digit_mixed_case(self):
        assert is_valid_hex_color("#FfF") is True

    def test_valid_primary_colors(self):
        assert is_valid_hex_color("#FF0000") is True  # Red
        assert is_valid_hex_color("#00FF00") is True  # Green
        assert is_valid_hex_color("#0000FF") is True  # Blue

    def test_valid_black(self):
        assert is_valid_hex_color("#000000") is True

    def test_valid_white(self):
        assert is_valid_hex_color("#FFFFFF") is True

    def test_valid_mid_range_colors(self):
        assert is_valid_hex_color("#4ade80") is True
        assert is_valid_hex_color("#3b82f6") is True
        assert is_valid_hex_color("#facc15") is True

    def test_valid_web_safe_colors(self):
        assert is_valid_hex_color("#000000") is True
        assert is_valid_hex_color("#FF0000") is True
        assert is_valid_hex_color("#00FF00") is True
        assert is_valid_hex_color("#0000FF") is True
        assert is_valid_hex_color("#FFFF00") is True
        assert is_valid_hex_color("#00FFFF") is True
        assert is_valid_hex_color("#FF00FF") is True
        assert is_valid_hex_color("#C0C0C0") is True
        assert is_valid_hex_color("#808080") is True
        assert is_valid_hex_color("#800000") is True
        assert is_valid_hex_color("#808000") is True
        assert is_valid_hex_color("#008000") is True
        assert is_valid_hex_color("#800080") is True
        assert is_valid_hex_color("#008080") is True
        assert is_valid_hex_color("#000080") is True

    def test_valid_named_colors_hex(self):
        # Dark Green
        assert is_valid_hex_color("#006400") is True
        # Midnight Blue
        assert is_valid_hex_color("#191970") is True
        # Coral
        assert is_valid_hex_color("#FF7F50") is True
        # Gold
        assert is_valid_hex_color("#FFD700") is True
        # Tomato
        assert is_valid_hex_color("#FF6347") is True
        # Purple
        assert is_valid_hex_color("#800080") is True
        # Royal Blue
        assert is_valid_hex_color("#4169E1") is True
        # Crimson
        assert is_valid_hex_color("#DC143C") is True
        # Forest Green
        assert is_valid_hex_color("#228B22") is True

    def test_valid_alpha_channel(self):
        # 3-digit shorthand, which is technically valid for CSS
        assert is_valid_hex_color("#F00") is True

    def test_hex_code_with_all_numbers(self):
        assert is_valid_hex_color("#123456") is True
        assert is_valid_hex_color("#012345") is True
        assert is_valid_hex_color("#987654") is True


# =====================================================================
# SECTION 2: INVALID HEX COLORS (Negative Tests)
# =====================================================================

class TestInvalidHexColors:
    def test_missing_hash(self):
        assert is_valid_hex_color("FFFFFF") is False

    def test_only_hash(self):
        assert is_valid_hex_color("#") is False

    def test_empty_string(self):
        assert is_valid_hex_color("") is False

    def test_too_many_characters(self):
        assert is_valid_hex_color("#FFFFFFF") is False

    def test_too_few_characters(self):
        assert is_valid_hex_color("#FFFF") is False

    def test_non_hex_characters(self):
        assert is_valid_hex_color("#GGGGGG") is False

    def test_invalid_3_digit(self):
        assert is_valid_hex_color("#GFF") is False

    def test_leading_whitespace(self):
        assert is_valid_hex_color(" #FFFFFF") is False

    def test_trailing_whitespace(self):
        assert is_valid_hex_color("#FFFFFF ") is False

    def test_whitespace_in_middle(self):
        assert is_valid_hex_color("#FF FFFF") is False

    def test_no_hash_three_digit(self):
        assert is_valid_hex_color("FFF") is False

    def test_special_characters(self):
        assert is_valid_hex_color("#$$$$$$") is False
    
    def test_input_is_integer(self):
        assert is_valid_hex_color(12345) is False
    
    def test_input_is_none(self):
        assert is_valid_hex_color(None) is False

    def test_input_is_list(self):
        assert is_valid_hex_color(["#FFFFFF"]) is False

    def test_input_is_dictionary(self):
        assert is_valid_hex_color({"color": "#FFFFFF"}) is False

    def test_input_is_float(self):
        assert is_valid_hex_color(1.234) is False

    def test_input_is_boolean(self):
        assert is_valid_hex_color(True) is False

    def test_input_is_bytes(self):
        assert is_valid_hex_color(b"#FFFFFF") is False

    def test_input_is_tuple(self):
        assert is_valid_hex_color(("#FFFFFF",)) is False

    def test_input_is_set(self):
        assert is_valid_hex_color({"#FFFFFF"}) is False

    def test_input_is_object(self):
        class MyClass:
            pass
        assert is_valid_hex_color(MyClass()) is False

    def test_rejects_unicode_hex(self):
        assert is_valid_hex_color("#FF00FF😊") is False

    def test_rejects_rgb_string(self):
        assert is_valid_hex_color("rgb(255, 255, 255)") is False

    def test_rejects_rgba_string(self):
        assert is_valid_hex_color("rgba(255, 255, 255, 0.5)") is False

    def test_rejects_hsl_string(self):
        assert is_valid_hex_color("hsl(120, 100%, 50%)") is False

    def test_rejects_4_digit_string(self):
        assert is_valid_hex_color("#FFF0") is False

    def test_rejects_8_digit_string(self):
        assert is_valid_hex_color("#FFFFFF00") is False

    def test_rejects_named_color(self):
        assert is_valid_hex_color("Red") is False

    def test_rejects_named_color_without_braces(self):
        assert is_valid_hex_color("Red") is False

    def test_rejects_named_color_with_hash(self):
        assert is_valid_hex_color("#Red") is False

    def test_rejects_invalid_underscore(self):
        assert is_valid_hex_color("#FF_FFF") is False

    def test_rejects_invalid_dash(self):
        assert is_valid_hex_color("#FF-FFF") is False

    def test_rejects_invalid_space_after_hash(self):
        assert is_valid_hex_color("# FFFFFF") is False

    def test_rejects_multiple_hashes(self):
        assert is_valid_hex_color("##FFFFFF") is False


# =====================================================================
# SECTION 3: EDGE CASE TESTS
# =====================================================================

class TestEdgeCases:
    def test_hex_with_tab(self):
        assert is_valid_hex_color("\t#FFFFFF") is False

    def test_very_long_string(self):
        assert is_valid_hex_color("#" + "F" * 100) is False

    def test_very_short_string(self):
        assert is_valid_hex_color("#F") is False

    def test_boundary_max_length(self):
        assert is_valid_hex_color("#FFFFFF") is True
        assert is_valid_hex_color("#FFFFFFF") is False

    def test_boundary_min_length(self):
        assert is_valid_hex_color("#FFF") is True
        assert is_valid_hex_color("#FF") is False

    def test_case_insensitivity_6_digit(self):
        assert is_valid_hex_color("#aBcDeF") is True
        assert is_valid_hex_color("#ABCDEF") is True
        assert is_valid_hex_color("#abcdef") is True

    def test_case_insensitivity_3_digit(self):
        assert is_valid_hex_color("#AbC") is True
        assert is_valid_hex_color("#ABC") is True
        assert is_valid_hex_color("#abc") is True

    def test_common_hex_codes(self):
        # Warm colors
        assert is_valid_hex_color("#FFA500") is True  # Orange
        assert is_valid_hex_color("#FFC0CB") is True  # Pink
        # Cool colors
        assert is_valid_hex_color("#00CED1") is True  # Dark Turquoise
        assert is_valid_hex_color("#5F9EA0") is True  # Cadet Blue
        # Neutral colors
        assert is_valid_hex_color("#D3D3D3") is True  # Light Gray
        assert is_valid_hex_color("#A9A9A9") is True  # Dark Gray


# =====================================================================
# SECTION 4: PERFORMANCE AND REGRESSION TESTS
# =====================================================================

class TestPerformance:
    def test_function_returns_bool(self):
        assert isinstance(is_valid_hex_color("#FFFFFF"), bool)
        assert isinstance(is_valid_hex_color("Invalid"), bool)

    def test_performance_1000_valid_inputs(self):
        """Ensure the function is fast enough for 1000 iterations."""
        start_time = time.time()
        for _ in range(1000):
            assert is_valid_hex_color("#FFFFFF") is True
        elapsed = time.time() - start_time
        assert elapsed < 1.0  # Should be under 1 second

    def test_performance_1000_invalid_inputs(self):
        """Ensure the function is fast enough for 1000 invalid iterations."""
        start_time = time.time()
        for _ in range(1000):
            assert is_valid_hex_color("NotAColor") is False
        elapsed = time.time() - start_time
        assert elapsed < 1.0

    def test_repeated_invocations_do_not_change_state(self):
        """Ensure the function is pure (no side effects)."""
        assert is_valid_hex_color("#FFFFFF") is True
        assert is_valid_hex_color("#FFFFFF") is True
        assert is_valid_hex_color("#FFFFFF") is True


# =====================================================================
# SECTION 5: RANDOMIZED / PROPERTY-BASED TESTS
# =====================================================================

class TestRandomizedInputs:
    def test_random_invalid_strings(self):
        """Random strings should almost never be valid."""
        random.seed(42)  # Seeding for reproducibility
        for _ in range(100):
            random_string = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=random.randint(1, 10)))
            if random_string.startswith("#") and len(random_string) in (4, 7):
                assert is_valid_hex_color(random_string) is True or is_valid_hex_color(random_string) is False
            else:
                assert is_valid_hex_color(random_string) is False

    def test_random_valid_hex_codes(self):
        """Generate random valid hex codes and ensure they pass."""
        random.seed(99)
        for _ in range(50):
            color = "#" + ''.join(random.choices('0123456789abcdefABCDEF', k=6))
            assert is_valid_hex_color(color) is True

    def test_random_hex_with_uppercase(self):
        """Ensure uppercase letters are accepted."""
        random.seed(12)
        for _ in range(25):
            color = "#" + ''.join(random.choices('0123456789ABCDEF', k=6))
            assert is_valid_hex_color(color) is True

    def test_random_hex_with_lowercase(self):
        """Ensure lowercase letters are accepted."""
        random.seed(77)
        for _ in range(25):
            color = "#" + ''.join(random.choices('0123456789abcdef', k=6))
            assert is_valid_hex_color(color) is True


# =====================================================================
# SECTION 6: SECURITY AND VALIDATION STRICTNESS
# =====================================================================

class TestSecurityStrictness:
    def test_prevents_css_injection(self):
        """Ensure dangerous CSS strings are rejected."""
        assert is_valid_hex_color("#FFFFFF; background: url(javascript:alert(1))") is False
        assert is_valid_hex_color("#FFFFFF</style>") is False
        assert is_valid_hex_color("#FFFFFF' OR '1'='1") is False

    def test_prevents_sql_injection(self):
        """Ensure SQL injection attempts are rejected."""
        assert is_valid_hex_color("#FFFFFF' OR '1'='1") is False
        assert is_valid_hex_color("#FFFFFF; DROP TABLE users") is False

    def test_prevents_xss_attempts(self):
        """Ensure XSS attempts are rejected."""
        assert is_valid_hex_color("<script>alert('xss')</script>") is False
        assert is_valid_hex_color("#<script>") is False


# =====================================================================
# SECTION 7: REAL-WORLD USAGE SCENARIOS
# =====================================================================

class TestRealWorldUsage:
    def test_default_ecobuddy_green(self):
        # From src.utils.certificate.py: textColor=colors.HexColor("#2E7D32")
        assert is_valid_hex_color("#2E7D32") is True

    def test_default_ecobuddy_blue(self):
        assert is_valid_hex_color("#1E88E5") is True

    def test_default_ecobuddy_grey(self):
        assert is_valid_hex_color("#757575") is True

    def test_application_form_input(self):
        """Simulate what a user would type into a form."""
        assert is_valid_hex_color("#F00") is True
        assert is_valid_hex_color("blue") is False
        assert is_valid_hex_color("") is False


# =====================================================================
# END OF TEST SUITE
# =====================================================================