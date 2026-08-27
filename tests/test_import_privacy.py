"""Tests for PII redaction."""

import pytest
from src.data.data_import_privacy_filter import PrivacyFilter

class TestPrivacyFilter:
    
    def test_email_redaction(self):
        f = PrivacyFilter()
        text = "Receipt from john.doe@example.com for dinner"
        assert f._redact_text(text) == "Receipt from [REDACTED EMAIL] for dinner"
        
    def test_phone_redaction(self):
        f = PrivacyFilter()
        assert f._redact_text("Call me at 555-123-4567") == "Call me at [REDACTED PHONE]"
        assert f._redact_text("Phone: (800) 555-0199") == "Phone: [REDACTED PHONE]"
        
    def test_ssn_cc_redaction(self):
        f = PrivacyFilter()
        assert f._redact_text("ID: 123-45-6789") == "ID: [REDACTED SSN]"
        assert f._redact_text("Paid with 4111 1111 1111 1111") == "Paid with [REDACTED CREDIT_CARD]"
        
    def test_account_redaction(self):
        f = PrivacyFilter()
        assert f._redact_text("Meter: XG9938294") == "[REDACTED METER_NUMBER]"
        assert f._redact_text("Acct: 99382104") == "[REDACTED ACCOUNT_NUMBER]"
        
    def test_sanitize_records(self):
        f = PrivacyFilter()
        records = [
            {
                "activity": "Flight booked by alice@test.com",
                "value": 100,
                "_warnings": ["Meter: AB123456 not found"]
            }
        ]
        
        safe = f.sanitize_records(records)
        assert safe[0]["activity"] == "Flight booked by [REDACTED EMAIL]"
        assert safe[0]["value"] == 100
        assert safe[0]["_warnings"][0] == "[REDACTED METER_NUMBER] not found"
