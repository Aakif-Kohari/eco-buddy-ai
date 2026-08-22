"""
Tests for invalid user input across the application.

Covers:
- Extremely long strings
- Special characters
- Unicode characters
- Whitespace-only values
- Unexpected data types
- Empty input
"""

import pytest
from unittest.mock import patch

from llm_parser import parse_quick_log


class TestInvalidUserInput:
    """Validate that malformed user input is handled safely."""

    def test_empty_string(self):
        """Empty input should not crash the application."""
        result = parse_quick_log("")

        assert result is not None

    def test_whitespace_only_input(self):
        """Whitespace-only input should be handled safely."""
        result = parse_quick_log("     ")

        assert result is not None

    def test_extremely_long_input(self):
        """Extremely long input should be rejected or safely processed."""
        long_input = "a" * 10000

        result = parse_quick_log(long_input)

        assert result is not None

    @pytest.mark.parametrize(
        "input_value",
        [
            "!@#$%^&*()",
            "<script>alert('test')</script>",
            "' OR '1'='1",
            "\"; DROP TABLE users; --",
            "`rm -rf /`",
        ],
    )
    def test_special_characters(self, input_value):
        """Special characters must not cause an application crash."""
        result = parse_quick_log(input_value)

        assert result is not None

    @pytest.mark.parametrize(
        "input_value",
        [
            "😀🌍🚀",
            "こんにちは",
            "नमस्ते",
            "你好",
            "مرحبا",
            "éñüç",
        ],
    )
    def test_unicode_input(self, input_value):
        """Unicode input should be handled safely."""
        result = parse_quick_log(input_value)

        assert result is not None

    @pytest.mark.parametrize(
        "input_value",
        [
            None,
            12345,
            3.14159,
            [],
            {},
            True,
        ],
    )
    def test_unexpected_data_types(self, input_value):
        """Unexpected data types should not cause an unhandled crash."""
        try:
            result = parse_quick_log(input_value)
            assert result is not None
        except (TypeError, ValueError):
            # Validation errors are acceptable for invalid data types.
            pass

    def test_mixed_malformed_input(self):
        """Mixed special, Unicode, whitespace and long content."""
        malformed_input = (
            "   "
            + "🚀" * 100
            + "<script>alert('x')</script>"
            + "!@#$%^&*()"
            + "   "
        )

        result = parse_quick_log(malformed_input)

        assert result is not None